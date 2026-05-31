# ADL Lite — Code Review Standards & Process

> **Version:** 1.0  
> **Last Updated:** 2026-05-31  
> **Scope:** All ADL Lite source code, tests, and configuration  
> **Audience:** Contributors, reviewers, and maintainers

---

## 1. Baseline Assessment (2026-05-31)

| Metric | Current State | Target |
|--------|:------------:|:------:|
| Tests passing | 112/112 (100%) | ✅ Maintain |
| Lint (ruff) | All checks pass | ✅ Maintain |
| Type check (mypy) | Configured, not running in CI | 🔲 Integrate into CI |
| Test coverage | 63% (2802 stmts, 1034 missed) | 🔲 ≥ 80% |
| CLI coverage | 63% (cli.py: 928 lines) | 🔲 ≥ 75% |
| Pre-commit hooks | Not configured | 🔲 Set up |
| CI/CD pipeline | Not visible | 🔲 GitHub Actions |

### Coverage Hotspots (files needing urgent attention)

| Module | Coverage | Priority | Gap |
|--------|:-------:|:--------:|-----|
| `action_executor.py` | 38% | 🔴 P0 | Core execution path — untested precondition validation, side-effect dispatch |
| `tools.py` | 29% | 🔴 P0 | Agent-facing wrappers — all tool functions under-tested |
| `data_importer.py` | 0% | 🟡 P1 | CSV/JSON import — no tests at all |
| `realtime.py` | 0% | 🟡 P1 | New module, no tests |
| `sync_manager.py` | 0% | 🟡 P1 | New module, no tests |
| `lark/listen.py` | 69% | 🟡 P1 | Feedback ingestion — gaps in poll/auto-transition |
| `lark/namespace.py` | 64% | 🟡 P1 | Scope mapping logic |
| `memory.py` | 60% | 🟡 P1 | Graph traversal fallback path, cascade filter |

---

## 2. Review Categories & Severity

### 🔴 Blocker (P0) — Must Fix Before Merge

Triggered when:
- **Security vulnerability**: SQL injection, unsafe eval, untrusted file reads, scope bypass
- **Data corruption**: Thread-unsafe writes without locks, chain integrity violation, hash mismatch
- **API contract break**: Changing public model fields, removing exported symbols without deprecation
- **Test regression**: Any previously passing test now fails
- **Missing error handling on critical path**: Uncaught exceptions in parse/store/consensus operations
- **Logic error in event chain**: Incorrect status derivation, broken `previous_event_id` linking

### 🟡 Warning (P1) — Should Fix Before Merge

Triggered when:
- **Missing unit tests** for new or modified public methods (minimum: happy path + one edge case)
- **Undocumented public API**: New public functions/classes without docstrings (Google-style for Python)
- **Mutating derived state**: Directly setting `front_matter.status` instead of using `EventChain.append()`
- **Thread safety**: Shared mutable state without `threading.Lock()` or `threading.RLock()`
- **Performance regression**: N+1 SQL queries, unnecessary document re-parsing, hot-path allocations
- **Import cycle**: New circular dependency between modules
- **Breaking ontology registry**: Adding predicates/actions without updating `adl_core_ontology.yaml`

### 💭 Suggestion (P2) — Nice to Improve

Triggered when:
- **Naming mismatch**: Variable names inconsistent with project conventions
- **Type annotation gap**: Missing type hints on public functions
- **Redundant code**: Duplicate logic between modules without extraction
- **Comment quality**: Code comments that describe *what* instead of *why*
- **Test readability**: Overly complex test fixtures, no `pytest.mark.parametrize` where applicable
- **Logging**: Missing structured logging for long-running operations

---

## 3. File-Type Specific Checklist

### 3.1 Pydantic Models (`models.py` and any file defining `BaseModel`)

```
[ ] All Fields have `description=` parameters
[ ] All Enums have docstrings
[ ] Field validators use @field_validator, not __init__ overrides  
[ ] Default values are immutable (list, dict → use default_factory)
[ ] model_post_init used correctly (not __init__)
[ ] `__all__` in __init__.py updated if new public model
[ ] New models don't break `ADLDocument.model_dump_json()` roundtrip
```

### 3.2 Parser Code (`parser.py`, `_extract_*`, regex patterns)

```
[ ] ADLParseError raised with descriptive message (not generic Exception)
[ ] Forward-compatible: unknown block types return None (not raise)
[ ] Unicode: Chinese pronouns handled in forbidden lists
[ ] Wiki-link regex tested with CJK text
[ ] Inline YAML parsing handles empty values, quoted values, nested params
[ ] Path.exists() check before read_text() in parse_file
```

### 3.3 Validator (`validator.py`)

```
[ ] New pronoun patterns added to _FORBIDDEN_PRONOUNS or regex sets
[ ] Scope format checked against _SCOPE_PATTERN
[ ] Strict mode: all predicates validated against ontology registry
[ ] Error messages are human-readable (not raw exception traces)
[ ] No false positives for complementizer "that" (e.g., "shows that X")
[ ] CJK pronoun detection covers expected patterns
```

### 3.4 Action Executor (`action_executor.py`)

```
[ ] New side effects implement SideEffect Protocol
[ ] SideEffect.execute() catches exceptions and returns SideEffectResult(False, ...)
[ ] Action definitions loaded from ontology._data (not hardcoded)
[ ] execute_pending returns {action_block_id → [ExecutionEntry]} (not raises)
[ ] triggers_transition uses EventChain.append() → refresh_snapshot() (not direct mutation)
[ ] Precondition check covers all Comparator types
[ ] Missing required_params returns FAILED (not throws)
```

### 3.5 CLI Module (`cli.py`)

```
[ ] New subcommands use set_defaults(func=_cmd_xxx)
[ ] Error handling: print to stderr, return non-zero exit code
[ ] JSON output uses json.dumps(..., indent=2) consistently
[ ] File argument accepts both string and Path
[ ] --help text is clear and complete
[ ] Subparser tree not deeper than 3 levels
```

### 3.6 Tests (`tests/`)

```
[ ] Test file name matches module: test_<module>.py
[ ] Uses pytest fixtures from conftest.py, not ad-hoc setup
[ ] Covers: happy path, error path, edge case, boundary value
[ ] Uses @pytest.mark.parametrize for combinatorial checks
[ ] Pydantic model tests verify both field defaults and validation
[ ] Consensus tests verify thread safety (concurrent append/transition)
[ ] Integration tests: parse → validate → store → query → consensus
[ ] No test depends on execution order or shared mutable state
```

### 3.7 Memory Layer (`memory.py`)

```
[ ] SQL queries use parameterized placeholders (?, ?, ?), never f-strings
[ ] LIKE queries escape wildcards (% and _)
[ ] Thread safety: all state-modifying methods use self._lock
[ ] WarmIndex close() called explicitly or via context manager
[ ] Graph fallback works when NetworkX not installed (HAS_NETWORKX guard)
[ ] Cascade filter escape covers LIKE injection vectors
```

---

## 4. PR Review Process

### 4.1 Before Opening a PR (Author Checklist)

```
[ ] ruff check adl_lite/ — zero warnings
[ ] pytest tests/ -v — all tests pass
[ ] New public functions/classes have docstrings
[ ] __init__.py __all__ updated if new exports
[ ] adl_core_ontology.yaml updated if new predicates/actions/scopes
[ ] Self-review: read diff, check for debugging artifacts (print, breakpoint)
[ ] Commit messages follow: "module: imperative description"
```

### 4.2 PR Size Limits

| Change Type | Max Lines | Review Turnaround |
|------------|:---------:|:-----------------:|
| Hotfix | < 50 | Same day |
| Feature | < 500 | 1-2 business days |
| Refactor | < 800 | 2-3 business days |
| Large (> 800) | Split into stacked PRs | N/A |

### 4.3 Reviewer Workflow

1. **Read the PR description** — understand intent before seeing code
2. **Check tests first** — if tests are missing/low quality, flag as 🟡 P1 and continue
3. **Core logic review** — correctness, security, event-first philosophy compliance
4. **Edge cases** — empty input, null values, concurrent access, large inputs
5. **Style & tooling** — ruff, mypy, coverage should pass; if not, flag
6. **Leave review** — use 🔴/🟡/💭 markers; each comment must explain *why* and *suggest alternative*

### 4.4 Review Comment Template

```
🔴 **Data Integrity: Event hash not recomputed after mutation**
File: `adl_lite/models.py`, line 189

**Why:** When `previous_event_id` is set after `model_post_init`, the hash 
still reflects the old `previous_event_id`. This breaks chain integrity.

**What happens:** `chain.verify_integrity()` returns False even when the 
chain is structurally correct.

**Suggestion:**
- Call `event.model_post_init(None)` after setting `previous_event_id` 
  to force hash recomputation (already done in `EventChain.append`, 
  but verify it's comprehensive).
- Add a test: append 3 events, verify_integrity() → True.
```

---

## 5. ADL-Specific Guidelines

### 5.1 Event-First Philosophy Compliance

> *"Status and confidence are COMPUTED from the chain, NOT stored."*

**Violation (🔴 Blocker):**
```python
# ❌ Direct mutation — bypasses chain integrity
doc.front_matter.status = DiscoveryStatus.VALIDATED
```

**Correct (✅):**
```python
# ✅ Append event — chain derives status
chain.append(Event(
    concept_id=doc.adl_id,
    event_type=EventType.VALIDATE,
    actor="reviewer",
    payload={"confidence": 0.85},
))
doc.refresh_snapshot(chain)
```

### 5.2 Thread Safety

Any class that has mutable shared state MUST use `threading.Lock()` or `threading.RLock()`.

**Pattern to follow (from `EventChain`):**
```python
class MyClass:
    def __init__(self):
        self._data: list = []
        self._lock = threading.Lock()

    def append(self, item):
        with self._lock:
            self._data.append(item)

    @property
    def items(self):
        with self._lock:
            return list(self._data)  # Return copy, not reference
```

### 5.3 Ontology Registry Changes

Any change to `adl_core_ontology.yaml` must:
1. Be reflected in `ADLType`, `EventType`, `MechanismType`, or `EvidenceType` enums if new types
2. Have corresponding `PreconditionRule` checks if new action preconditions
3. Be listed in `validator.py` strict-mode checks if new predicates
4. Be documented in AGENTS.md ontology section

### 5.4 Error Handling Patterns

| Context | Pattern |
|---------|---------|
| CLI commands | `print(msg, file=sys.stderr)` + `return 1` |
| Library API | Raise typed exception (`ADLParseError`, `ValueError`, `KeyError`) |
| Action executor | `action.exec_status = FAILED` + append `ExecutionEntry(result="failure")` |
| Side effects | `except Exception → SideEffectResult(False, f"...")` |
| Memory layer | Let SQLite exceptions propagate; HotIndex `pop(key, None)` silently |

---

## 6. Tooling Setup

### 6.1 Pre-commit Configuration (Recommended: `.pre-commit-config.yaml`)

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0
    hooks:
      - id: mypy
        args: [--ignore-missing-imports]
        additional_dependencies: [pydantic>=2.0, types-PyYAML]
```

### 6.2 CI/CD Pipeline (Recommended: GitHub Actions)

```yaml
name: CI
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/ruff-action@v1
  
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - run: pip install -e ".[dev]"
      - run: pytest tests/ -v --cov=adl_lite --cov-fail-under=80
```

---

## 7. Review Cadence & Ownership

| Role | Responsibility |
|------|---------------|
| **Author** | Self-review checklist, test coverage, documentation |
| **Reviewer** | 🔴 blocker check, 🟡 suggestion review, approve only when P0/P1 resolved |
| **Maintainer** | Final merge decision, version bump, CHANGELOG entry |

### Merge Rules

- **1 approval minimum** for hotfixes (< 50 lines)
- **2 approvals** for feature PRs (≥ 50 lines)
- **All CI checks green** before merge (once CI is set up)
- **No merge to main with 🔴 blockers unresolved**

---

## 8. Improvement Roadmap

| Priority | Action | Expected Impact |
|:--------:|--------|----------------|
| 🔴 P0 | Add tests for `action_executor.py` (38% → 75%+) | Catch side-effect dispatch bugs before production |
| 🔴 P0 | Add tests for `tools.py` agent wrappers (29% → 75%+) | Ensure agent-facing API is reliable |
| 🔴 P0 | Set up pre-commit hooks (ruff + mypy) | Prevent lint violations at commit time |
| 🟡 P1 | Add CI/CD pipeline (GitHub Actions) | Automated quality gate on every PR |
| 🟡 P1 | Test `data_importer.py`, `realtime.py`, `sync_manager.py` | Close 0% coverage gaps |
| 🟡 P1 | Refactor `cli.py` (928 lines → split by command group) | Improve maintainability, testability |
| 🟡 P1 | Add integration tests: parse→validate→store→consensus e2e | Catch cross-module regressions |
| 💭 P2 | Setup `pytest-cov --cov-fail-under=80` in CI | Hard coverage gate |
| 💭 P2 | Add `doctest` examples to public API modules | Ensure docs stay accurate |

---

*This document is a living standard. Propose changes via PR to `docs/CODE_REVIEW_STANDARDS.md` with the same review process it describes.*
