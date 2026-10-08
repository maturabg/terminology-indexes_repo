"""Валидира indexes/*.jsonl срещу schema/candidate.schema.json.

Проверки за всеки файл:
  * всеки ред е валиден по схемата (вкл. format: uri / date-time);
  * поне един запис;
  * уникални candidate_id и сортиране по candidate_id;
  * source съвпада с името на файла;
  * url е абсолютен http(s) URL с host и без fragment.

Употреба: uv run builders/validate.py [file.jsonl ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator

from common import INDEXES_DIR, SCHEMA_PATH


def make_validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def validate_file(path: Path, validator: Draft202012Validator) -> list[str]:
    errors: list[str] = []
    source = path.stem
    ids: list[str] = []
    seen: set[str] = set()

    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            where = f"{path.name}:{lineno}"
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"{where}: invalid JSON: {e}")
                continue
            for err in validator.iter_errors(row):
                loc = "/".join(map(str, err.absolute_path)) or "<root>"
                errors.append(f"{where}: {loc}: {err.message}")
            if not isinstance(row, dict):
                continue

            if row.get("source") != source:
                errors.append(f"{where}: source {row.get('source')!r} != file name {source!r}")

            cid = row.get("candidate_id")
            if cid in seen:
                errors.append(f"{where}: duplicate candidate_id {cid!r}")
            seen.add(cid)
            ids.append(cid)

            url = urlsplit(row.get("url", ""))
            if url.scheme not in ("http", "https") or not url.netloc:
                errors.append(f"{where}: url is not an absolute http(s) URL")
            if url.fragment:
                errors.append(f"{where}: url must not contain a fragment (use 'fragment')")

    if not ids:
        errors.append(f"{path.name}: no records")
    elif all(isinstance(i, str) for i in ids) and ids != sorted(ids):
        errors.append(f"{path.name}: records are not sorted by candidate_id")
    return errors


def main(argv: list[str]) -> int:
    paths = [Path(p) for p in argv] or sorted(INDEXES_DIR.glob("*.jsonl"))
    if not paths:
        print("no indexes/*.jsonl files found", file=sys.stderr)
        return 1

    validator = make_validator()
    failed = False
    for path in paths:
        errors = validate_file(path, validator)
        if errors:
            failed = True
            for e in errors[:50]:
                print(e, file=sys.stderr)
            if len(errors) > 50:
                print(f"... and {len(errors) - 50} more", file=sys.stderr)
            print(f"FAIL {path.name}: {len(errors)} error(s)", file=sys.stderr)
        else:
            count = sum(1 for _ in path.open(encoding="utf-8"))
            print(f"OK   {path.name}: {count} records")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
