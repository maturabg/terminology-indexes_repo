# Terminology indexes

Helper repo that indexes tech term sources for searching

## Локален build

```sh
uv run builders/python_glossary.py   # -> indexes/python_glossary.jsonl
uv run builders/validate.py          # валидация на indexes/*.jsonl спрямо schema/
uv run builders/manifest.py          # -> manifests/snapshot.json
uv run builders/build_sqlite.py      # -> dist/indexes.sqlite (FTS5)
uv run builders/package.py           # -> dist/{terminology-indexes-<snapshot>.sqlite.zst,manifest.json,SHA256SUMS}
```

## Release

Workflow `.github/workflows/update-indexes.yml` изпълнява горните стъпки и създава
GitHub Release с tag = snapshot (`YYYY.MM.DD[.N]`) и assets `manifest.json`,
`terminology-indexes-<snapshot>.sqlite.zst`, `SHA256SUMS`.

Тригери:

* ръчно — Actions → update-indexes → Run workflow (по желание с `snapshot`);
* push на tag, напр. `git tag 2026.10.08 && git push origin 2026.10.08`.

Проверка на свален release: `sha256sum -c SHA256SUMS && zstd -d terminology-indexes-*.sqlite.zst`.

Repo-то трябва да е с включени immutable releases
(Settings → General → Releases → *Enable release immutability*).

## SQLite схема

* `meta(key, value)` — `snapshot`, `schema_version`, `schema_sha256`, `generated_at`, `manifest`;
* `sources` — по един ред на source от manifest-а;
* `candidates` — един ред на кандидат (колоните от `schema/candidate.schema.json`, `aliases` е JSON масив);
* `candidate_aliases(candidate_rowid, alias, normalized_alias)` — точно търсене по alias;
* `candidates_fts` — FTS5 върху `term`, `normalized_term`, `aliases`, `definition_excerpt`; `rowid` = `candidates.rowid`.

```sql
SELECT c.term, c.url, c.fragment
FROM candidates_fts f JOIN candidates c ON c.rowid = f.rowid
WHERE candidates_fts MATCH 'generator' ORDER BY rank LIMIT 10;
```
