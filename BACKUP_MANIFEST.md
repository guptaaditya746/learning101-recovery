# Backup manifest

This clean source snapshot omits the previous Git history because it contained generated graph and research data. The original project and its seven commits were left unchanged.

Excluded from the public snapshot:

- `thesis-demo/data/`: chunks and graph patches derived from research material.
- `thesis-demo/graph/`: generated RDF graphs.
- `thesis-demo/papers/`: downloaded research papers.
- `thesis-demo/parsed/`: extracted paper text.
- `SWE-agent/`: nested third-party checkout; preserve it from its own upstream.
- `mini-swe-agent/` and `sudoku-run/`: separate projects handled independently.
- `.venv/`, Aider caches/history, notebook cell outputs, Slurm logs, and other generated files.

The original cluster directory was not changed. Back up any excluded data or generated outputs separately if they are needed.
