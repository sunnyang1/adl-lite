"""Tests for E20: L2 Template Compliance Effectiveness."""

from __future__ import annotations

import experiments.e20_template_effectiveness  # noqa: F401
from experiments.e20_template_effectiveness import E20TemplateEffectiveness
from experiments.registry import instantiate


class TestE20:
    def test_experiment_registered(self):
        exp = instantiate("E20")
        assert exp is not None
        assert exp.experiment_id == "E20"

    def test_runs_without_error(self):
        exp = instantiate("E20")
        result = exp._run_wrapper()
        assert result.status in ("passed", "partial"), f"E20 failed: {result.errors}"
        assert result.metrics["effectiveness"] >= 0.10
        assert 0.0 <= result.metrics["bad_transition_rate_off"] <= 1.0
        assert 0.0 <= result.metrics["bad_transition_prevention_on"] <= 1.0

    def test_plausible_numbers(self):
        exp = E20TemplateEffectiveness()
        result = exp.run()
        assert result.metrics["total_rounds"] == 20
        assert result.metrics["agents"] == 5
        assert result.metrics["concepts"] == 3
        assert result.metrics["effectiveness"] >= 0.10
