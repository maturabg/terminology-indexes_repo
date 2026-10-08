```sh
❯ tree -a -I '.venv|.git'
.
├── AGENTS.md
├── builders
│   ├── build_sqlite.py
│   ├── common.py
│   ├── manifest.py
│   ├── package.py
│   ├── __pycache__
│   │   └── common.cpython-313.pyc
│   ├── python_glossary.py
│   └── validate.py
├── dist
│   ├── indexes.sqlite
│   ├── manifest.json
│   ├── SHA256SUMS
│   └── terminology-indexes-2026.10.08.sqlite.zst
├── .github
│   └── workflows
│       ├── .gitkeep
│       └── update-indexes.yml
├── .gitignore
├── indexes
│   ├── .gitkeep
│   └── python_glossary.jsonl
├── LICENSES
│   └── .gitkeep
├── manifests
│   ├── .gitkeep
│   └── snapshot.json
├── pyproject.toml
├── README.md
├── schema
│   └── candidate.schema.json
├── sources
│   └── .gitkeep
├── TODO.md
└── uv.lock

11 directories, 26 files

```

- за python използвай uv
- поддържай `tree` тук актуално
