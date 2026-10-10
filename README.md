# Learning 101

A collection of Python learning exercises covering RDFLib, RDF graph querying, and a small Sudoku solver. The `thesis-demo` scripts form a paper-to-RDF workflow; they expect input papers and generated data to be supplied locally.

## Run

Create a Python environment and install the demo dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r thesis-demo/requirements.txt
```

Run individual examples with `python rdflib_intro.py`, `python rdflib_query.py`, or inspect the Jupyter notebook. Sudoku code is under `sudoku/` with tests in `tests/`.

The thesis demo scripts are numbered by workflow stage and should be run in order after placing papers and source data under `thesis-demo/papers/` and `thesis-demo/data/`.
