"""
Direct unit tests for adl_lite.cli internal functions.

These tests improve code-coverage metrics by calling CLI handler functions
directly (in-process) rather than via subprocess.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from adl_lite import cli

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
CAPITAL = EXAMPLES / "capital_reflux_trap.md"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
INVALID = FIXTURES / "invalid_pronoun.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ns(**kwargs) -> argparse.Namespace:
    """Build an argparse.Namespace with default None for missing keys."""
    return argparse.Namespace(**kwargs)


# ---------------------------------------------------------------------------
# parse
# ---------------------------------------------------------------------------


class TestCliParse:
    def test_parse_text(self, capsys):
        args = _ns(file=str(CAPITAL), output="text")
        rc = cli._cmd_parse(args)
        assert rc == 0
        captured = capsys.readouterr()
        assert "disc-capital-trap" in captured.out

    def test_parse_json(self, capsys):
        args = _ns(file=str(CAPITAL), output="json")
        rc = cli._cmd_parse(args)
        assert rc == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["front_matter"]["adl_id"] == "disc-capital-trap"

    def test_parse_missing_file(self, capsys):
        args = _ns(file="/nonexistent/path/file.md", output="text")
        rc = cli._cmd_parse(args)
        assert rc == 1
        captured = capsys.readouterr()
        assert "No such file" in captured.err or "not found" in captured.err.lower()


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


class TestCliValidate:
    def test_validate_ok(self, capsys):
        args = _ns(files=[str(CAPITAL)], strict=False, shacl=None, no_shacl=None)
        rc = cli._cmd_validate(args)
        assert rc == 0
        captured = capsys.readouterr()
        assert "OK" in captured.out

    def test_validate_multiple_files(self, capsys):
        paths = sorted(EXAMPLES.glob("*.md"))
        args = _ns(files=[str(p) for p in paths], strict=False, shacl=None, no_shacl=None)
        rc = cli._cmd_validate(args)
        assert rc == 0

    def test_validate_fail(self, capsys):
        args = _ns(files=[str(INVALID)], strict=False, shacl=None, no_shacl=None)
        rc = cli._cmd_validate(args)
        assert rc == 1
        captured = capsys.readouterr()
        assert "FAIL" in captured.err or "pronoun" in captured.err.lower()

    def test_validate_strict_unknown_predicate(self, capsys):
        invalid_pred = FIXTURES / "invalid_predicate.md"
        args = _ns(files=[str(invalid_pred)], strict=True, shacl=None, no_shacl=None)
        rc = cli._cmd_validate(args)
        assert rc == 1
        captured = capsys.readouterr()
        assert "Unknown relation predicate" in captured.err or "similar" in captured.err


# ---------------------------------------------------------------------------
# store / related
# ---------------------------------------------------------------------------


class TestCliStoreRelated:
    def test_store_and_related(self, tmp_path: Path, capsys):
        db = tmp_path / "test.db"
        args_store = _ns(file=str(CAPITAL), db=str(db))
        rc = cli._cmd_store(args_store)
        assert rc == 0

        args_related = _ns(adl_id="disc-capital-trap", db=str(db), depth=2)
        rc = cli._cmd_related(args_related)
        assert rc == 0
        captured = capsys.readouterr()
        assert captured.out.strip() != ""

    def test_store_missing_file(self, capsys):
        args = _ns(file="/nonexistent.md", db="/tmp/fake.db")
        rc = cli._cmd_store(args)
        assert rc == 1

    def test_related_empty_db(self, capsys):
        db = Path("/tmp/nonexistent_related.db")
        # Ensure it doesn't exist
        if db.exists():
            db.unlink()
        args = _ns(adl_id="x", db=str(db), depth=1)
        rc = cli._cmd_related(args)
        assert rc == 0
        captured = capsys.readouterr()
        assert "no related capabilities for x (depth=1)" in captured.out


# ---------------------------------------------------------------------------
# consensus
# ---------------------------------------------------------------------------


class TestCliConsensus:
    def test_register_by_path(self, tmp_path: Path, capsys):
        state = tmp_path / "consensus.json"
        args = _ns(file=str(CAPITAL), adl_id=None, state=str(state))
        rc = cli._cmd_consensus_register(args)
        assert rc == 0
        assert state.exists()

    def test_register_by_adl_id(self, tmp_path: Path, capsys):
        state = tmp_path / "consensus2.json"
        args = _ns(file=None, adl_id="stub-concept", state=str(state))
        rc = cli._cmd_consensus_register(args)
        assert rc == 0
        assert state.exists()
        # Verify the stub was written
        data = json.loads(state.read_text())
        assert "stub-concept" in data["chains"]

    def test_register_neither_path_nor_id(self, capsys):
        args = _ns(file=None, adl_id=None, state="/tmp/fake.json")
        rc = cli._cmd_consensus_register(args)
        assert rc == 1
        captured = capsys.readouterr()
        assert "requires --file or --adl-id" in captured.err

    def test_transition_and_verify(self, tmp_path: Path, capsys):
        state = tmp_path / "consensus3.json"
        # Register first
        cli._cmd_consensus_register(_ns(file=str(CAPITAL), adl_id=None, state=str(state)))

        args_trans = _ns(
            adl_id="disc-capital-trap",
            to="validated",
            actor="agent_reviewer",
            reason="test approval",
            state=str(state),
        )
        rc = cli._cmd_consensus_transition(args_trans)
        assert rc == 0

        args_verify = _ns(adl_id="disc-capital-trap", state=str(state))
        rc = cli._cmd_consensus_verify(args_verify)
        assert rc == 0
        captured = capsys.readouterr()
        assert "chain OK" in captured.out

    def test_transition_unregistered(self, tmp_path: Path, capsys):
        state = tmp_path / "consensus4.json"
        args = _ns(
            adl_id="unregistered-id",
            to="validated",
            actor="agent_reviewer",
            reason="test",
            state=str(state),
        )
        rc = cli._cmd_consensus_transition(args)
        assert rc == 1
        captured = capsys.readouterr()
        assert "not registered" in captured.err


# ---------------------------------------------------------------------------
# ontology
# ---------------------------------------------------------------------------


class TestCliOntology:
    def test_ontology_validate_yaml_only(self, capsys):
        args = _ns(files=[], strict=False, ontology=None, examples=False, aml=False)
        rc = cli._cmd_ontology_validate(args)
        assert rc == 0
        captured = capsys.readouterr()
        assert "predicates:" in captured.out

    def test_ontology_validate_with_files(self, capsys):
        args = _ns(files=[str(CAPITAL)], strict=False, ontology=None, examples=False, aml=False)
        rc = cli._cmd_ontology_validate(args)
        assert rc == 0

    def test_ontology_validate_strict_fail(self, capsys):
        invalid = FIXTURES / "invalid_isomorphic_no_mapping.md"
        args = _ns(files=[str(invalid)], strict=False, ontology=None, examples=False, aml=False)
        rc = cli._cmd_ontology_validate(args)
        assert rc == 1
        captured = capsys.readouterr()
        assert "mapping_type" in captured.err

    def test_ontology_query(self, capsys):
        args = _ns(
            ontology=None,
            predicate=None,
            from_status=None,
            to_status=None,
            json=False,
        )
        rc = cli._cmd_ontology_query(args)
        assert rc == 0
        # Query with no filters on empty DB returns empty list
        captured = capsys.readouterr()
        assert "ontology:" in captured.out

    def test_ontology_query_json(self, capsys):
        args = _ns(
            ontology=None,
            predicate=None,
            from_status=None,
            to_status=None,
            json=True,
        )
        rc = cli._cmd_ontology_query(args)
        assert rc == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, dict)
        assert "path" in data
