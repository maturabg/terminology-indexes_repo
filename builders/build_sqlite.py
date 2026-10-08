"""Строи dist/indexes.sqlite от indexes/*.jsonl и manifests/snapshot.json.

Таблици:
  meta               ключ/стойност: snapshot, schema_version, generated_at, manifest (JSON);
  sources            по един ред на source от manifest-а;
  candidates         по един ред на кандидат; aliases е JSON масив;
  candidate_aliases  (candidate_rowid, alias, normalized_alias) за точно търсене по alias;
  candidates_fts     FTS5 върху term, normalized_term, aliases, definition_excerpt
                     (rowid = candidates.rowid).

Преди build-а се проверява, че sha256 и броят записи на всеки JSONL съвпадат с
manifest-а — т.е. базата съответства точно на описания snapshot.

Употреба: uv run builders/build_sqlite.py [--out dist/indexes.sqlite]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

from common import ROOT, normalize_term

MANIFEST_PATH = ROOT / "manifests" / "snapshot.json"
DEFAULT_OUT = ROOT / "dist" / "indexes.sqlite"

DDL = """
CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE sources (
    source         TEXT PRIMARY KEY,
    records        INTEGER NOT NULL,
    sha256         TEXT NOT NULL,
    source_version TEXT NOT NULL,
    retrieved_at   TEXT NOT NULL,
    license        TEXT NOT NULL,
    content_policy TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE candidates (
    rowid              INTEGER PRIMARY KEY,
    candidate_id       TEXT NOT NULL UNIQUE,
    source             TEXT NOT NULL REFERENCES sources(source),
    term               TEXT NOT NULL,
    normalized_term    TEXT NOT NULL,
    aliases            TEXT NOT NULL DEFAULT '[]',
    title              TEXT,
    url                TEXT NOT NULL,
    fragment           TEXT,
    definition_excerpt TEXT,
    source_version     TEXT NOT NULL,
    retrieved_at       TEXT NOT NULL,
    license            TEXT NOT NULL,
    attribution        TEXT,
    content_policy     TEXT NOT NULL
);
CREATE INDEX candidates_normalized_term ON candidates(normalized_term);
CREATE INDEX candidates_source ON candidates(source);

CREATE TABLE candidate_aliases (
    candidate_rowid  INTEGER NOT NULL REFERENCES candidates(rowid),
    alias            TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    PRIMARY KEY (candidate_rowid, alias)
) WITHOUT ROWID;
CREATE INDEX candidate_aliases_normalized ON candidate_aliases(normalized_alias);

CREATE VIRTUAL TABLE candidates_fts USING fts5(
    term,
    normalized_term,
    aliases,
    definition_excerpt,
    tokenize = 'unicode61 remove_diacritics 2'
);
"""

COLUMNS = (
    "candidate_id",
    "source",
    "term",
    "normalized_term",
    "aliases",
    "title",
    "url",
    "fragment",
    "definition_excerpt",
    "source_version",
    "retrieved_at",
    "license",
    "attribution",
    "content_policy",
)


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def check_against_manifest(manifest: dict) -> list[str]:
    errors = []
    for src in manifest["sources"]:
        path = ROOT / src["file"]
        if not path.exists():
            errors.append(f"{src['file']}: missing")
            continue
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != src["sha256"]:
            errors.append(f"{src['file']}: sha256 differs from manifest (re-run manifest.py)")
        if data.count(b"\n") != src["records"]:
            errors.append(f"{src['file']}: record count differs from manifest")
    return errors


def build(manifest: dict, out: Path) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.unlink(missing_ok=True)

    con = sqlite3.connect(out)
    try:
        con.executescript(DDL)
        con.executemany(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            [
                ("snapshot", manifest["snapshot"]),
                ("schema_version", str(manifest["schema_version"])),
                ("schema_sha256", manifest["schema_sha256"]),
                ("generated_at", manifest["generated_at"]),
                ("manifest", json.dumps(manifest, ensure_ascii=False, sort_keys=True)),
            ],
        )
        con.executemany(
            "INSERT INTO sources VALUES (:source, :records, :sha256, :source_version,"
            " :retrieved_at, :license, :content_policy)",
            manifest["sources"],
        )

        total = 0
        placeholders = ", ".join("?" * len(COLUMNS))
        for src in sorted(manifest["sources"], key=lambda s: s["source"]):
            with (ROOT / src["file"]).open(encoding="utf-8") as f:
                for line in f:
                    row = json.loads(line)
                    aliases = row.get("aliases", [])
                    values = [
                        json.dumps(aliases, ensure_ascii=False) if c == "aliases" else row.get(c)
                        for c in COLUMNS
                    ]
                    cur = con.execute(
                        f"INSERT INTO candidates ({', '.join(COLUMNS)}) VALUES ({placeholders})",
                        values,
                    )
                    rowid = cur.lastrowid
                    con.executemany(
                        "INSERT INTO candidate_aliases VALUES (?, ?, ?)",
                        [(rowid, a, normalize_term(a)) for a in aliases],
                    )
                    con.execute(
                        "INSERT INTO candidates_fts (rowid, term, normalized_term, aliases,"
                        " definition_excerpt) VALUES (?, ?, ?, ?, ?)",
                        (
                            rowid,
                            row["term"],
                            row["normalized_term"],
                            "\n".join(aliases),
                            row.get("definition_excerpt"),
                        ),
                    )
                    total += 1

        con.execute("INSERT INTO candidates_fts (candidates_fts) VALUES ('optimize')")
        con.execute(f"PRAGMA user_version = {int(manifest['schema_version'])}")
        con.commit()
        con.execute("VACUUM")
        if (res := con.execute("PRAGMA integrity_check").fetchone()[0]) != "ok":
            raise RuntimeError(f"integrity_check: {res}")
    finally:
        con.close()
    return total


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    manifest = load_manifest()
    if errors := check_against_manifest(manifest):
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    if not manifest["sources"]:
        print("manifest has no sources", file=sys.stderr)
        return 1

    total = build(manifest, args.out)
    print(f"snapshot {manifest['snapshot']}: {total} candidates -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
