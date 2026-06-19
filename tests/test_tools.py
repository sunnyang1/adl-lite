"""
Tests for adl_lite.tools — agent-facing tool wrappers.

Covers:
    - adl_parse: parse file, returns summary dict
    - adl_validate: valid file, invalid file, nonexistent file
    - adl_store: store document into ADLMemory
    - adl_query_related: graph traversal from stored doc
    - adl_consensus_register: register by file, by adl_id
    - adl_consensus_transition: transition status, invalid transition
    - adl_ontology_query: predicate filter, transition check
    - adl_consensus_verify: verify chain, unregistered concept
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from adl_lite.exceptions import ADLConsensusError
from adl_lite.parser import ADLParseError
from adl_lite.tools import (
    adl_consensus_register,
    adl_consensus_transition,
    adl_consensus_verify,
    adl_ontology_query,
    adl_parse,
    adl_query_related,
    adl_store,
    adl_validate,
)

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
CAPITAL_TRAP = EXAMPLES_DIR / "capital_reflux_trap.md"


# ---------------------------------------------------------------------------
# adl_parse
# ---------------------------------------------------------------------------


class TestAdlParse:
    def test_parse_valid_file(self):
        result = adl_parse(CAPITAL_TRAP)
        assert isinstance(result, dict)
        assert "front_matter" in result
        fm = result["front_matter"]
        assert "adl_type" in fm
        assert "adl_id" in fm
        assert "_summary" in result
        summary = result["_summary"]
        assert summary["adl_id"] == fm["adl_id"]
        assert "concept_name" in summary
        assert "relations" in summary
        assert "evidence" in summary
        assert "wiki_links" in summary

    def test_returns_json_serializable(self):
        result = adl_parse(CAPITAL_TRAP)
        # Should not raise
        json.dumps(result)

    def test_parse_nonexistent_file(self):
        with pytest.raises((ADLParseError, OSError)):
            adl_parse("/nonexistent/path.md")

    def test_path_as_string(self):
        result = adl_parse(str(CAPITAL_TRAP))
        assert result["front_matter"]["adl_id"] is not None


# ---------------------------------------------------------------------------
# adl_validate
# ---------------------------------------------------------------------------


class TestAdlValidate:
    def test_valid_file_ok(self):
        result = adl_validate(CAPITAL_TRAP)
        assert result["ok"] is True
        assert result["errors"] == []
        assert str(CAPITAL_TRAP) == result["path"]

    def test_nonexistent_file(self):
        result = adl_validate("/nonexistent/file.md")
        assert result["ok"] is False
        assert len(result["errors"]) == 1
        assert "parse error" in result["errors"][0]

    def test_invalid_adl_file(self, tmp_path: Path):
        """A file with missing required YAML fields."""
        bad_file = tmp_path / "bad.md"
        bad_file.write_text("---\nadl_type: concept\n---\n# No adl_id\n")
        result = adl_validate(bad_file)
        # Should fail validation (missing adl_id or other required field)
        # Pydantic validation may raise ValueError which is caught
        assert result["ok"] is False


# ---------------------------------------------------------------------------
# adl_store
# ---------------------------------------------------------------------------


class TestAdlStore:
    def test_store_to_memory_db(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        result = adl_store(CAPITAL_TRAP, db_path)
        assert result["stored"] is not None
        assert str(db_path) == result["db"]
        assert db_path.exists()

    def test_store_to_in_memory_db(self):
        result = adl_store(CAPITAL_TRAP, ":memory:")
        assert result["stored"] is not None
        assert result["db"] == ":memory:"

    def test_store_nonexistent_file(self):
        with pytest.raises((ADLParseError, OSError)):
            adl_store("/nonexistent/path.md", ":memory:")


# ---------------------------------------------------------------------------
# adl_query_related
# ---------------------------------------------------------------------------


class TestAdlQueryRelated:
    def test_query_empty_db(self, tmp_path: Path):
        db_path = tmp_path / "empty.db"
        results = adl_query_related("test-concept", db_path)
        assert results == []

    def test_query_after_store(self, tmp_path: Path):
        db_path = tmp_path / "has_data.db"
        store_result = adl_store(CAPITAL_TRAP, db_path)
        adl_id = store_result["stored"]
        results = adl_query_related(adl_id, db_path, depth=2)
        # capital_reflux_trap has relations in its L3 blocks
        assert isinstance(results, list)

    def test_query_custom_depth(self, tmp_path: Path):
        db_path = tmp_path / "depth_test.db"
        store_result = adl_store(CAPITAL_TRAP, db_path)
        adl_id = store_result["stored"]
        r1 = adl_query_related(adl_id, db_path, depth=1)
        r2 = adl_query_related(adl_id, db_path, depth=3)
        # Both should return without error
        assert isinstance(r1, list)
        assert isinstance(r2, list)


# ---------------------------------------------------------------------------
# adl_consensus_register
# ---------------------------------------------------------------------------


class TestAdlConsensusRegister:
    def test_register_by_path(self, tmp_path: Path):
        state_path = tmp_path / "consensus.json"
        result = adl_consensus_register(path=CAPITAL_TRAP, state=state_path)
        assert result["registered"] is not None
        assert state_path.exists()

    def test_register_by_adl_id(self, tmp_path: Path):
        state_path = tmp_path / "consensus2.json"
        result = adl_consensus_register(adl_id="test-stub-concept", state=state_path)
        assert result["registered"] == "test-stub-concept"
        assert state_path.exists()

    def test_register_duplicate_idempotent(self, tmp_path: Path):
        state_path = tmp_path / "consensus3.json"
        r1 = adl_consensus_register(adl_id="idem-concept", state=state_path)
        r2 = adl_consensus_register(adl_id="idem-concept", state=state_path)
        assert r1["registered"] == r2["registered"]

    def test_register_needs_path_or_id(self, tmp_path: Path):
        state_path = tmp_path / "consensus4.json"
        with pytest.raises(ValueError, match="requires path or adl_id"):
            adl_consensus_register(path=None, adl_id=None, state=state_path)

    def test_register_default_state(self, tmp_path: Path):
        """When state is not specified, it uses default path based on db_path=None."""
        # Switch to tmp_path as working dir to not pollute project root
        import os

        orig_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = adl_consensus_register(adl_id="default-state-concept")
            assert result["registered"] == "default-state-concept"
            assert (tmp_path / "adl_consensus.json").exists()
        finally:
            os.chdir(orig_cwd)


# ---------------------------------------------------------------------------
# adl_consensus_transition
# ---------------------------------------------------------------------------


class TestAdlConsensusTransition:
    def test_transition_valid(self, tmp_path: Path):
        state_path = tmp_path / "trans.json"
        adl_consensus_register(adl_id="trans-concept", state=state_path)
        result = adl_consensus_transition(
            "trans-concept",
            "validated",
            actor="agent_1",
            reason="test transition",
            state=state_path,
        )
        assert result["adl_id"] == "trans-concept"
        assert result["event_type"] == "validate"
        assert result["actor"] == "agent_1"
        assert "hash" in result
        assert "timestamp" in result

    def test_transition_unregistered(self, tmp_path: Path):
        state_path = tmp_path / "trans2.json"
        with pytest.raises(ADLConsensusError):
            adl_consensus_transition(
                "nonexistent",
                "validated",
                actor="agent_1",
                state=state_path,
            )

    def test_transition_with_discovery_status_enum(self, tmp_path: Path):
        from adl_lite.models import DiscoveryStatus

        state_path = tmp_path / "trans3.json"
        adl_consensus_register(adl_id="enum-concept", state=state_path)
        result = adl_consensus_transition(
            "enum-concept",
            DiscoveryStatus.VALIDATED,
            actor="agent_2",
            state=state_path,
        )
        assert result["event_type"] == "validate"


# ---------------------------------------------------------------------------
# adl_consensus_verify
# ---------------------------------------------------------------------------


class TestAdlConsensusVerify:
    def test_verify_registered(self, tmp_path: Path):
        state_path = tmp_path / "verify.json"
        adl_consensus_register(adl_id="verify-concept", state=state_path)
        result = adl_consensus_verify("verify-concept", state=state_path)
        assert result["ok"] is True
        assert result["adl_id"] == "verify-concept"
        assert "status" in result

    def test_verify_unregistered(self, tmp_path: Path):
        state_path = tmp_path / "verify2.json"
        result = adl_consensus_verify("no-such-concept", state=state_path)
        assert result["ok"] is False
        assert result["adl_id"] == "no-such-concept"
        assert result["error"] == "not registered"


# ---------------------------------------------------------------------------
# adl_ontology_query
# ---------------------------------------------------------------------------


class TestAdlOntologyQuery:
    def test_query_default_ontology(self):
        result = adl_ontology_query()
        assert "version" in result
        assert "predicates" in result
        assert "classes" in result
        assert "scope_prefixes" in result
        assert "mapping_types" in result
        assert "allowed_transitions" in result

    def test_query_predicate_filter(self):
        result = adl_ontology_query(predicate="isomorphic-to")
        assert "isomorphic-to" in result["predicates"]
        assert "allowed_mapping_types" in result

    def test_query_unknown_predicate(self):
        result = adl_ontology_query(predicate="nonexistent-relation")
        assert result["predicates"] == []
        assert "predicate_valid" in result
        assert result["predicate_valid"] is False

    def test_query_transition_check(self):
        result = adl_ontology_query(
            from_status="provisional",
            to_status="validated",
        )
        assert result.get("is_valid_transition") is True

    def test_query_invalid_transition(self):
        result = adl_ontology_query(
            from_status="validated",
            to_status="provisional",
        )
        assert result.get("is_valid_transition") is False
