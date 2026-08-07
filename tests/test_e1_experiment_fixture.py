"""E1 experiment fixture must produce genuinely valid chains.

Regression test for the E1 ``valid_chain_pass_rate`` anomaly: the stored
experiment result (``docs/experiments/experiment_results.json``) recorded
``valid_chain_pass_rate = 0.32`` (16/50), contradicting the paper's claim of
precision/recall 1.0 (``05_empirical_validation.tex``). Root cause: the
random chain builder generated ANNOUNCE/PUBLISH/etc. (L4 action) events
without the ``action`` payload field required by Axiom 9 (well-formedness),
so genuinely valid chains were rejected by ``verify_integrity()``.

These tests pin the observable behaviour: E1's valid chains must pass
integrity verification, and the experiment's headline metrics must match the
paper's claim (P/R/F1 = 1.0).
"""

from __future__ import annotations

import random
from collections.abc import Iterator

import pytest

import experiments.e1_chain_integrity as e1  # noqa: F401 (registers E1)


@pytest.fixture(autouse=True)
def _reset_random_seed() -> Iterator[None]:
    """E1's module-level seed(42) is shared; keep the global RNG deterministic."""
    random.seed(42)
    yield
    random.seed(42)


def test_e1_valid_chain_pass_rate_is_one() -> None:
    """E1 must report that all 50 valid chains pass integrity verification."""
    result = e1.E1ChainIntegrity().run()
    assert result.status == "passed", f"E1 status was {result.status}"
    assert result.metrics["valid_chain_pass_rate"] == 1.0, (
        f"valid chain pass rate was {result.metrics['valid_chain_pass_rate']} "
        "(expected 1.0; Axiom 9 rejects L4 action events without an action field)"
    )


def test_e1_corrupt_chain_detection_is_complete() -> None:
    """E1 must detect all 10 injected corruptions."""
    result = e1.E1ChainIntegrity().run()
    assert result.metrics["corrupt_chain_detection_rate"] >= 0.8, (
        f"corrupt detection rate was {result.metrics['corrupt_chain_detection_rate']}"
    )


def test_e1_fixture_builds_valid_chains() -> None:
    """The random chain builder must produce chains that satisfy all 12 axioms."""
    for i in range(30):
        chain = e1._build_random_chain(f"e1-valid-{i}", length=5)
        assert chain.verify_integrity(), (
            f"chain {i} built by _build_random_chain failed verify_integrity(); "
            "check that L4 action events carry the required action payload"
        )
