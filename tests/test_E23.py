"""Tests for E23 Concurrent Agent Contention experiment."""

from __future__ import annotations

import experiments.e23_contention_stress  # noqa: F401
from experiments.e23_contention_stress import E23ContentionStress
from experiments.registry import instantiate


class TestE23ContentionStress:
    def test_registered(self):
        exp = instantiate("E23")
        assert exp is not None
        assert isinstance(exp, E23ContentionStress)

    def test_experiment_runs_and_passes(self):
        exp = E23ContentionStress()
        result = exp._run_wrapper()
        assert result.status == "passed"
        assert result.experiment_id == "E23"
        assert result.duration_ms > 0

    def test_metrics(self):
        exp = E23ContentionStress()
        result = exp.run()
        assert "conflict_rate" in result.metrics
        assert "fork_rate" in result.metrics
        assert "integrity_rate" in result.metrics
        assert "race_conditions" in result.metrics
        assert result.metrics["integrity_rate"] == 1.0
        assert result.metrics["conflict_rate"] < 0.5
        assert result.metrics["agents"] == 10
        assert result.metrics["concepts"] == 50
        assert result.metrics["rounds"] == 100

    def test_raw_data_has_50_rows(self):
        exp = E23ContentionStress()
        result = exp.run()
        assert len(result.raw_data) == 50
        for row in result.raw_data:
            assert "concept_id" in row
            assert "chain_length" in row
            assert "final_status" in row
            assert "integrity" in row
            assert row["integrity"] is True

    def test_no_race_corruption(self):
        exp = E23ContentionStress()
        result = exp.run()
        # All chains must pass integrity
        assert all(row["integrity"] for row in result.raw_data)
        # Integrity rate metric
        assert result.metrics["integrity_rate"] == 1.0
