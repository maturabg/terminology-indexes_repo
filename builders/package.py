"""Подготвя release assets в dist/:

  terminology-indexes-<snapshot>.sqlite.zst   компресиран dist/indexes.sqlite;
  manifest.json                               копие на manifests/snapshot.json;
  SHA256SUMS                                  във формата на `sha256sum -c`.

Употреба: uv run builders/package.py [--level 19]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys

import zstandard

from common import ROOT

DIST = ROOT / "dist"
SQLITE_PATH = DIST / "indexes.sqlite"
MANIFEST_PATH = ROOT / "manifests" / "snapshot.json"


def sha256(path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", type=int, default=19)
    args = parser.parse_args(argv)

    if not SQLITE_PATH.exists():
        print(f"{SQLITE_PATH} missing (run build_sqlite.py)", file=sys.stderr)
        return 1
    snapshot = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["snapshot"]

    for old in DIST.glob("terminology-indexes-*.sqlite.zst"):
        old.unlink()
    zst_path = DIST / f"terminology-indexes-{snapshot}.sqlite.zst"
    cctx = zstandard.ZstdCompressor(level=args.level, write_checksum=True, write_content_size=True)
    with SQLITE_PATH.open("rb") as src, zst_path.open("wb") as dst:
        cctx.copy_stream(src, dst, size=SQLITE_PATH.stat().st_size)

    manifest_out = DIST / "manifest.json"
    shutil.copyfile(MANIFEST_PATH, manifest_out)

    assets = sorted([manifest_out, zst_path], key=lambda p: p.name)
    sums = "".join(f"{sha256(p)}  {p.name}\n" for p in assets)
    (DIST / "SHA256SUMS").write_text(sums, encoding="utf-8")

    print(f"{zst_path.name}: {SQLITE_PATH.stat().st_size} -> {zst_path.stat().st_size} bytes")
    print(sums, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
