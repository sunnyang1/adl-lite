# Contributing to ADL Lite

Thanks for your interest in ADL Lite! This project is an open, event-first
capability registry for LLM agent ecosystems. Contributions of all kinds are
welcome: code, docs, ontology predicates, experiments, formal specs, and
well-written issues.

By contributing, you agree that your work is licensed under the
[MIT License](LICENSE).

---

## What You Can Contribute

| Area | Examples |
|------|----------|
| **Core code** | parser, models, validator, consensus, action executor, memory |
| **Interfaces** | CLI commands, REST API (`adl_lite/api.py`), MCP tools (`adl_lite/mcp_server.py`) |
| **Semantic web** | OWL 2 DL import/export, RDF-star, JSON-LD, SHACL, PROV-O |
| **Trust & formal** | DID resolution, key registry, Merkle anchors, TLA+ specs, Coq proofs |
| **Experiments** | New `E##` experiments under `experiments/` |
| **Docs** | README, runbooks in `docs/`, examples in `examples/` |

---

## Development Setup

Prerequisites: **Python 3.10+**, `git`.

```bash
# 1. Clone and enter the repository
git clone https://github.com/sunnyang1/adl-lite.git
cd adl-lite

# 2. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install in editable mode with dev tooling
pip install -e ".[dev]"

# 4. Install pre-commit hooks (ruff + mypy run on every commit)
pre-commit install
```

The `[dev]` extra installs `pytest`, `pytest-cov`, `pytest-asyncio`,
`pytest-benchmark`, `ruff`, `mypy`, `rdflib`, `pyshacl`, `mcp`, `numpy`, and
`hypothesis`. Install additional extras only if your change touches them
(e.g. `pip install -e ".[embeddings]"` for vector-index work).

---

## Development Workflow

1. **Create a topic branch** from `main`:

   ```bash
   git checkout -b feat/your-short-description
   ```

   Suggested prefixes: `feat/`, `fix/`, `docs/`, `refactor/`, `perf/`, `test/`.

2. **Make your change.** Keep commits small and focused. Commit messages follow
   conventional style, e.g. `feat(cli): add verify-batch command`.

3. **Run the quality gates locally** (all are enforced in CI):

   ```bash
   # Lint + auto-fix (matches pre-commit hook)
   ruff check adl_lite/ tests/

   # Formatting
   ruff format --check adl_lite/ tests/        # --check only verifies
   ruff format adl_lite/ tests/                # applies formatting

   # Type check
   mypy adl_lite/ --ignore-missing-imports

   # Fast test suite (excludes slow tests; ~25 s)
   pytest tests/ -m "not slow" -v

   # Full suite with coverage
   pytest tests/ -v --cov=adl_lite --cov-report=term-missing
   ```

4. **Push and open a pull request** against `main`. In the PR description,
   explain the problem, the fix, and how you verified it. Link any related
   issue. Add a `CHANGELOG.md` entry under `[Unreleased]` if the change is
   user-visible.

---

## Code Style

- **Python target**: 3.10 (`py310`). Use standard-library-friendly, typed code.
- **Line length**: 100 characters (ruff `line-length = 100`).
- **Lint rules**: `E, F, W, I, N, UP, B, C4` with `E501, N999, B008` ignored.
- **Formatting**: ruff-format is the only formatter.
- **Type hints**: encouraged but not mandatory (`disallow_untyped_defs = false`).
- **Docstrings & comments**: English. User-facing CLI output may be bilingual
  (Chinese/English).
- **Import contract**: `import adl_lite` must work with core dependencies
  only. If your module pulls a heavy optional dependency (`numpy`, `rdflib`,
  `pyshacl`, `faiss`, `sentence-transformers`), import it lazily and register
  any public symbols in `_LAZY_ATTRS` in `adl_lite/__init__.py` (PEP 562)
  so users get an actionable `pip install adl-lite[...]` error instead of a
  broken import.

---

## Testing

- New features must ship with tests. Test files live in `tests/` and match
  `test_<module>.py`; extended suites use `test_<module>_extended.py`.
- The project currently has **1881 tests** with **86% coverage** across 20+
  modules — keep the trend upward.
- Mark genuinely long-running tests with `@pytest.mark.slow` so
  `pytest tests/ -m "not slow"` stays fast. Slow tests run in CI on `main`
  only.
- Property-based tests use `hypothesis` (already a dev dependency).
- If you touch concurrency or `asyncio` code, note that pytest is configured
  with `asyncio_mode = "auto"` and `--strict-markers`.

---

## Experiments

Experiments live under `experiments/` and are registered in
`experiments/runner.py` (current: E1–E35). To add one:

1. Create `experiments/eNN_your_name.py` exporting a `main()` (or `run()`) function.
2. Register it in `experiments/runner.py` with a title and optional metadata.
3. Import optional heavy dependencies lazily — the runner must degrade
   gracefully when an extra (e.g. `pygit2` for E19) is absent.
4. Add a short section to `docs/` describing the experiment and its results.

Run experiments with `python -m experiments.runner list`, or reproduce the
paper pipeline with `./reproduce.sh quick` (E1–E4 + E24, ~30 s).

---

## CI / CD

`.github/workflows/ci.yml` runs on every push and PR to `main`:

- **lint**: `ruff check` + `ruff format --check` + `mypy` (Python 3.13).
- **test-fast**: `pytest tests/ -m "not slow"` on Python 3.10, 3.11, 3.12, 3.13
  with coverage upload.
- **test-slow** and **benchmark**: on `main` pushes only.
- **release**: publishing to PyPI is triggered by `v*` tag pushes (maintainers).

The PR must pass lint + test-fast on at least one Python version before merge.

---

## Getting Help

- **Issues**: report bugs, missing features, or documentation gaps via GitHub issues.
- **Style/design questions**: open a discussion in the issue tracker before large
  refactors, so reviewers know your intent.
- **Scope**: keep PRs focused. If a change spans multiple modules, consider
  splitting it into reviewable commits.

Happy building!
