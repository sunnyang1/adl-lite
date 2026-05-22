"""Experiment harness smoke tests."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from experiments.harness import ScriptedHarness, run_scripted_sim
from experiments.run_all import run_all


class TestScriptedHarness:
    def test_run_produces_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "run.jsonl"
            out = run_scripted_sim(log_path=log)
            lines = out.read_text().strip().splitlines()
            assert len(lines) >= 8
            first = json.loads(lines[0])
            assert "role" in first
            assert "action" in first

    def test_harness_roles_present(self):
        harness = ScriptedHarness()
        harness.run_scripted_scenario()
        roles = {e.role for e in harness.events}
        assert roles >= {"discoverer", "reviewer", "skeptic", "merger", "librarian"}
        harness.close()


class TestRunAll:
    def test_run_all_returns_all_rqs(self):
        summary = run_all()
        assert "rq1_ambiguity" in summary
        assert "rq2_consensus" in summary
        assert "rq3_retrieval" in summary
        assert "rq4_leakage" in summary
        assert summary["rq4_leakage"]["adl_leaks"] == 0
