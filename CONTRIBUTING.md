# Contributing

Thanks for considering a contribution. The project is small on purpose: three transformations, their inverses and instructions, a pipeline for nested data, three integration helpers and a CLI.

## Set up

Requires Python 3.11 or newer. With [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/basitalisandhu/spotlighting
cd spotlighting
uv venv && uv pip install -e ".[dev]"
uv run pytest -q
```

Without uv:

```bash
python3 -m venv .venv && . .venv/bin/activate
python3 -m pip install -e ".[dev]"
python3 -m pytest -q
```

## Before you open a pull request

```bash
make check          # ruff check, ruff format --check, pytest
make demo           # regenerate docs/demo.svg when the demo output changes
```

CI runs the same commands on Python 3.11 and 3.12 and fails if `docs/demo.svg` is out of date.

## Rules for changes

- Every mode must round-trip: `unmark(spotlight(text, mode))` equals `text` for any string, including the empty string. Add a test for any new edge case.
- Instruction text must describe exactly what the transformation does. If you change a transformation, change its instruction and its test in `tests/test_instructions.py`.
- Claims in the README about the paper or a vendor's documentation must quote or paraphrase the source and link it. No numbers that are not in the source.
- Test inputs are neutral sentences. Do not add attack strings anywhere in the repository; `tests/forbidden.txt` lists phrases the test suite rejects.

## Style

- `ruff` formats and lints; line length 100.
- Standard library only. A pull request that adds a runtime dependency will be asked to remove it.
- No model names or vendor model identifiers in code, docs or tests.
- Plain language, no em dashes, no claims that cannot be checked against a source or a test.
- Deterministic output: no randomness, no timestamps.

## Reporting security issues

See [SECURITY.md](SECURITY.md).
