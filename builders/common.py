"""Общи помощни функции за builders/*.py."""

from __future__ import annotations

import json
import re
import unicodedata
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEXES_DIR = ROOT / "indexes"
SCHEMA_PATH = ROOT / "schema" / "candidate.schema.json"

USER_AGENT = "terminology-indexes/0.1 (+https://github.com/maturabg/terminology-indexes_repo)"


@dataclass(frozen=True)
class Download:
    body: bytes
    etag: str | None
    last_modified: str | None
    retrieved_at: str


def utc_now() -> str:
    """RFC 3339 timestamp в UTC, със секундна точност."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fetch(url: str, timeout: float = 60) -> Download:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return Download(
            body=resp.read(),
            etag=resp.headers.get("ETag"),
            last_modified=resp.headers.get("Last-Modified"),
            retrieved_at=utc_now(),
        )


_WS = re.compile(r"\s+")


def normalize_term(term: str) -> str:
    """NFKC + casefold + сбити интервали."""
    return _WS.sub(" ", unicodedata.normalize("NFKC", term).casefold()).strip()


def write_jsonl(source: str, candidates: list[dict]) -> Path:
    """Записва indexes/<source>.jsonl, стабилно сортиран по candidate_id."""
    path = INDEXES_DIR / f"{source}.jsonl"
    rows = sorted(candidates, key=lambda c: c["candidate_id"])
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return path
