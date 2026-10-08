"""Генерира manifests/snapshot.json от наличните indexes/*.jsonl.

Употреба: uv run builders/manifest.py [--snapshot YYYY.MM.DD]
По подразбиране snapshot е днешната дата (UTC).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime

from common import INDEXES_DIR, ROOT, SCHEMA_PATH, utc_now

MANIFEST_PATH = ROOT / "manifests" / "snapshot.json"
SCHEMA_VERSION = 1


def sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", default=datetime.now(UTC).strftime("%Y.%m.%d"))
    args = parser.parse_args(argv)

    sources = []
    for path in sorted(INDEXES_DIR.glob("*.jsonl")):
        with path.open(encoding="utf-8") as f:
            rows = [json.loads(line) for line in f]
        if not rows:
            print(f"{path.name}: empty, skipped", file=sys.stderr)
            continue
        first = rows[0]
        sources.append(
            {
                "source": path.stem,
                "file": path.relative_to(ROOT).as_posix(),
                "records": len(rows),
                "sha256": sha256(path),
                "source_version": first["source_version"],
                "retrieved_at": first["retrieved_at"],
                "license": first["license"],
                "content_policy": first["content_policy"],
            }
        )

    manifest = {
        "snapshot": args.snapshot,
        "schema_version": SCHEMA_VERSION,
        "schema_sha256": sha256(SCHEMA_PATH),
        "generated_at": utc_now(),
        "sources": sources,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"snapshot {args.snapshot}: {len(sources)} source(s) -> {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
