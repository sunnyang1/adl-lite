## Description

<!-- What does this PR do? Why is it needed? -->

## Type of Change

- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change (API contract change)
- [ ] Documentation / tooling only
- [ ] Refactor (no behavior change)

## ADL-Specific Checklist

- [ ] Event-first: status/confidence derived from EventChain, not stored
- [ ] Thread safety: shared mutable state protected by Lock/RLock
- [ ] Ontology: new predicates/actions registered in `adl_core_ontology.yaml`
- [ ] Public API: `__init__.py` `__all__` updated for new exports
- [ ] Pydantic: field defaults use `default_factory`, not mutable values

## Quality Gate

- [ ] `ruff check adl_lite/` — zero warnings
- [ ] `pytest tests/ -v` — all tests pass
- [ ] New code has docstrings (Google-style)
- [ ] New/modified public methods have unit tests
- [ ] Self-review of diff completed (no debug artifacts)

## Coverage Impact

<!-- Check after running: pytest tests/ --cov=adl_lite --cov-report=term-missing -->

| Module | Coverage Before | Coverage After |
|--------|:--------------:|:--------------:|
| | | |

## Related Issues

<!-- Link to issues: closes #123, related to #456 -->
