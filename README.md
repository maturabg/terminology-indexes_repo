# Terminology indexes

Helper repo that indexes tech term sources for searching

## Локален build

```sh
uv run builders/python_glossary.py   # -> indexes/python_glossary.jsonl
uv run builders/validate.py          # валидация на indexes/*.jsonl спрямо schema/
uv run builders/manifest.py          # -> manifests/snapshot.json
```
