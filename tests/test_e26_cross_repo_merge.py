"""E26 cross-repository CRDT merge must produce zero integrity failures.

Regression test for the E26 experiment (``experiments/e26_cross_repo_merge.py``),
which was previously a paper claim with no script or stored result. The paper
(``05_empirical_validation.tex`` §5.4) reports 100 merges with zero integrity
failures and delta/gamma consistency (Theorem 9, CRDT LUB semantics).
"""

from __future__ import annotations

import pytest

from experiments.e26_cross_repo_merge import E26CrossRepositoryMerge

pytestmark = pytest.mark.slow


def test_e26_runs_with_zero_integrity_failures() -> None:
    result = E26CrossRepositoryMerge().run()
    assert result.status == "passed", f"E26 status was {result.status}"
    assert result.metrics["integrity_failures"] == 0
    assert result.metrics["delta_gamma_mismatch"] == 0
    assert result.metrics["integrity_rate"] == 1.0


def test_e26_scale_matches_paper_claim() -> None:
    """Paper claims 100 merges; the registered experiment must execute >= that."""
    result = E26CrossRepositoryMerge().run()
    assert result.metrics["merges"] >= 100
    assert result.metrics["total_events"] >= 20_000, (
        "E26 total events must be at least the originally claimed 20,000"
    )
