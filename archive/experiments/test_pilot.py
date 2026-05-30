"""In-package smoke tests for experiments (pytest experiments/ -v)."""

from experiments.run_all import run_all


def test_pilot_summary():
    summary = run_all()
    assert summary["rq4_leakage"]["adl_leaks"] == 0
