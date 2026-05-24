"""Experiment harness smoke tests."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from experiments.harness import ScriptedHarness, run_scripted_sim
from experiments.run_all import run_all

FIXTURES = Path(__file__).resolve().parent / "fixtures"


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

    def test_harness_strict_ontology_logs_predicate_failures(self, tmp_path: Path):
        bad = tmp_path / "bad.md"
        bad.write_text(
            (FIXTURES / "invalid_predicate.md").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        harness = ScriptedHarness(strict_ontology=True)
        harness.reviewer_validate_and_transition(bad)
        validate_events = [e for e in harness.events if e.action == "validate"]
        assert validate_events
        last = validate_events[-1]
        assert last.detail.get("strict_ontology") is True
        assert last.detail.get("ok") is False
        assert last.detail.get("ontology_errors")
        harness.close()


class TestRunAll:
    def test_run_all_returns_all_rqs(self):
        summary = run_all()
        assert "rq1_ambiguity" in summary
        assert "rq2_consensus" in summary
        assert "rq3_retrieval" in summary
        assert "rq4_leakage" in summary
        assert summary["rq4_leakage"]["adl_leaks"] == 0
