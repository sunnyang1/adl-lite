"""Tests for E20b Calibration Baseline experiment."""

from __future__ import annotations

import experiments.e20b_calibration_baseline  # noqa: F401
from experiments.e20b_calibration_baseline import E20bCalibrationBaseline
from experiments.registry import instantiate


class TestE20bCalibrationBaseline:
    def test_experiment_registered(self):
        exp = instantiate("E20b")
        assert exp is not None
        assert isinstance(exp, E20bCalibrationBaseline)

    def test_experiment_runs_and_passes(self):
        exp = E20bCalibrationBaseline()
        result = exp._run_wrapper()
        assert result.status in ("passed", "partial")
        assert "ece_raw" in result.metrics
        assert "ece_cal" in result.metrics
        assert result.metrics["ece_cal"] < result.metrics["ece_raw"]
        assert result.metrics["n_min_mitigated"] is False  # same accuracy, same value → no reduction
        assert result.metrics["collusion_gamma_raw"] == 0.99
        assert result.metrics["collusion_gamma_cal"] == 0.99
        # Mixed scenario: calibration mitigates when validators differ
        assert result.metrics["mixed_gamma_cal"] < result.metrics["mixed_gamma_raw"]

    def test_ece_reduction_positive(self):
        exp = E20bCalibrationBaseline()
        result = exp.run()
        assert result.metrics["ece_reduction"] > 1.0

    def test_raw_data_has_20_concepts(self):
        exp = E20bCalibrationBaseline()
        result = exp.run()
        assert len(result.raw_data) == 20
        for row in result.raw_data:
            assert "concept_id" in row
            assert "ground_truth" in row
            assert "gamma_raw" in row
            assert "gamma_cal" in row
