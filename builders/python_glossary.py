"""Builder за речника (glossary) на Python документацията.

Източник: Sphinx inventory (objects.inv) на docs.python.org. Взимат се само
записите от роля std:term. Термини, сочещи към един и същ anchor, се
обединяват в един кандидат; останалите изписвания стават aliases.

Inventory-то съдържа само имена и URL-и, без текст на дефинициите, затова
content_policy е metadata_only.
"""

from __future__ import annotations

import hashlib
import re
import sys
import zlib
from collections import defaultdict
from urllib.parse import urldefrag

from common import fetch, normalize_term, write_jsonl

SOURCE = "python_glossary"
BASE_URL = "https://docs.python.org/3/"
INVENTORY_URL = BASE_URL + "objects.inv"
LICENSE = "PSF-2.0"
ATTRIBUTION = "Python documentation, © Python Software Foundation"

# Формат на ред от inventory v2 (същият regex като в sphinx.util.inventory).
_LINE = re.compile(r"(.+?)\s+(\S+)\s+(-?\d+)\s+?(\S*)\s+(.*)")


def parse_inventory(data: bytes) -> tuple[dict[str, str], list[tuple[str, str, str, str]]]:
    """Връща (header, [(name, domain:role, uri, dispname), ...])."""
    header: dict[str, str] = {}
    pos = 0
    for _ in range(4):
        end = data.index(b"\n", pos)
        line = data[pos:end].decode("utf-8")
        pos = end + 1
        if ":" in line:
            key, _, value = line.lstrip("# ").partition(":")
            header[key.strip()] = value.strip()
    if not data.startswith(b"# Sphinx inventory version 2"):
        raise ValueError("unsupported inventory format")

    entries = []
    for line in zlib.decompress(data[pos:]).decode("utf-8").splitlines():
        m = _LINE.match(line.rstrip())
        if not m:
            continue
        name, role, _prio, uri, dispname = m.groups()
        if uri.endswith("$"):
            uri = uri[:-1] + name
        if dispname == "-":
            dispname = name
        entries.append((name, role, uri, dispname))
    return header, entries


def pick_primary(terms: list[str], fragment: str) -> str:
    """Основният термин е този, от който Sphinx е генерирал anchor-а."""
    for t in terms:
        if fragment == "term-" + re.sub(r"\s+", "-", t):
            return t
    return terms[0]


def build() -> list[dict]:
    dl = fetch(INVENTORY_URL)
    header, entries = parse_inventory(dl.body)
    version = header.get("Version", "unknown")
    source_version = f"{version} (sha256:{hashlib.sha256(dl.body).hexdigest()[:12]})"

    doc_titles = {name: disp for name, role, _uri, disp in entries if role == "std:doc"}

    groups: dict[str, list[str]] = defaultdict(list)
    for name, role, uri, dispname in entries:
        if role == "std:term":
            groups[uri].append(dispname)

    candidates = []
    for uri, terms in groups.items():
        page, fragment = urldefrag(uri)
        terms = sorted(set(terms))
        primary = pick_primary(terms, fragment)
        doc = page.removesuffix(".html")
        candidates.append(
            {
                "source": SOURCE,
                "candidate_id": f"{SOURCE}:{normalize_term(primary)}",
                "term": primary,
                "normalized_term": normalize_term(primary),
                "aliases": [t for t in terms if t != primary],
                "title": doc_titles.get(doc),
                "url": BASE_URL + page,
                "fragment": fragment or None,
                "definition_excerpt": None,
                "source_version": source_version,
                "retrieved_at": dl.retrieved_at,
                "license": LICENSE,
                "attribution": ATTRIBUTION,
                "content_policy": "metadata_only",
            }
        )
    return candidates


def main() -> int:
    candidates = build()
    path = write_jsonl(SOURCE, candidates)
    print(f"{SOURCE}: {len(candidates)} candidates -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
