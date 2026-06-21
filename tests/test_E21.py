"""Tests for E21 100k Event Stress Test experiment."""

from __future__ import annotations

import experiments.e21_100k_stress  # noqa: F401
from experiments.e21_100k_stress import E21_100kStress
from experiments.registry import instantiate


class TestE21_100kStress:
    def test_experiment_registered(self):
        exp = instantiate("E21")
        assert exp is not None
        assert isinstance(exp, E21_100kStress)

    def test_experiment_runs_and_produces_numbers(self):
        exp = E21_100kStress()
        result = exp._run_wrapper()
        assert result.status in ("passed", "partial", "failed")
        assert "verify_time_s" in result.metrics
        assert "memory_peak_mb" in result.metrics
        assert "append_latency_ms" in result.metrics
        assert "total_time_s" in result.metrics
        assert result.metrics["n_events"] in (50_000, 100_000)
        assert result.metrics["integrity_ok"] is True
        assert result.duration_ms > 0

    def test_metrics_are_positive(self):
        exp = E21_100kStress()
        result = exp.run()
        assert result.metrics["verify_time_s"] >= 0
        assert result.metrics["memory_peak_mb"] >= 0
        assert result.metrics["append_latency_ms"] > 0
        assert result.metrics["total_time_s"] > 0

    def test_raw_data_has_one_row(self):
        exp = E21_100kStress()
        result = exp.run()
        assert len(result.raw_data) == 1
        row = result.raw_data[0]
        assert "n_events" in row
        assert "verify_time_s" in row
        assert "memory_peak_mb" in row
