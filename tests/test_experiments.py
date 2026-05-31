"""Experiment harness smoke tests."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

# Import experiment modules to trigger @register decorators
import experiments.e1_chain_integrity  # noqa: F401
import experiments.e2_status_derivation  # noqa: F401
import experiments.e4_precondition  # noqa: F401
from experiments.harness import ScriptedHarness, run_scripted_sim
from experiments.registry import instantiate, list_all

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


class TestExperimentRegistry:
    def test_all_experiments_registered(self):
        items = list_all()
        ids = {item["id"] for item in items}
        # At minimum E1, E2, E4 are always imported
        assert ids >= {"E1", "E2", "E4"}
        assert all(item["name"] for item in items)

    def test_instantiate_runs(self):
        # E1, E2, E4 are self-contained (no data files needed)
        for eid in ["E1", "E2", "E4"]:
            exp = instantiate(eid)
            assert exp is not None, f"Could not instantiate {eid}"
            result = exp._run_wrapper()
            assert result.status in ("passed", "partial"), f"{eid} failed: {result.errors}"
