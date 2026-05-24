"""Tests for adl_ontology_query tool (Milestone 2c)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from adl_lite.ontology import OntologyManager
from adl_lite.tools import adl_ontology_query

ROOT = Path(__file__).resolve().parents[1]


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "adl_lite.cli", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


class TestAdlOntologyQuery:
    def test_returns_registry_fields(self):
        data = adl_ontology_query()
        assert data["version"]
        assert Path(data["path"]).is_file()
        assert len(data["predicates"]) >= 8
        assert data["scope_prefixes"] == ["public", "private", "user", "shared"]
        assert "topological" in data["mapping_types"]
        assert "provisional" in data["allowed_transitions"]

    def test_matches_ontology_manager(self):
        mgr = OntologyManager()
        data = adl_ontology_query()
        assert data["predicates"] == mgr.list_predicates()
        assert data["allowed_transitions"] == mgr.status_transition_graph()
        assert data["mapping_types"] == mgr.list_mapping_types()

    def test_predicate_filter(self):
        data = adl_ontology_query(predicate="isomorphic-to")
        assert data["predicates"] == ["isomorphic-to"]
        assert data["predicate_valid"] is True
        assert "topological" in data["allowed_mapping_types"]

    def test_unknown_predicate_filter(self):
        data = adl_ontology_query(predicate="similar")
        assert data["predicates"] == []
        assert data["predicate_valid"] is False

    def test_from_status_filter(self):
        data = adl_ontology_query(from_status="forked")
        assert set(data["allowed_transitions"].keys()) == {"forked"}
        assert "validated" in data["allowed_transitions"]["forked"]

    def test_transition_check(self):
        data = adl_ontology_query(from_status="forked", to_status="validated")
        assert data["is_valid_transition"] is True
        data_bad = adl_ontology_query(from_status="archived", to_status="validated")
        assert data_bad["is_valid_transition"] is False

    def test_json_serializable(self):
        data = adl_ontology_query(from_status="provisional", to_status="validated")
        json.dumps(data)


class TestOntologyQueryCLI:
    def test_query_text_output(self):
        proc = _run_cli("ontology", "query")
        assert proc.returncode == 0, proc.stderr
        assert "predicates" in proc.stdout
        assert "status_transitions:" in proc.stdout

    def test_query_json_output(self):
        proc = _run_cli(
            "ontology",
            "query",
            "--json",
            "--from-status",
            "forked",
            "--to-status",
            "validated",
        )
        assert proc.returncode == 0, proc.stderr
        data = json.loads(proc.stdout)
        assert data["is_valid_transition"] is True

    def test_query_predicate_filter(self):
        proc = _run_cli("ontology", "query", "--predicate", "isomorphic-to")
        assert proc.returncode == 0, proc.stderr
        assert "isomorphic-to" in proc.stdout
        assert "allowed_mapping_types" in proc.stdout
