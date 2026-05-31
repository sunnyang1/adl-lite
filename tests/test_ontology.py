"""Tests for adl_core_ontology.yaml and OntologyManager (Milestone 2a)."""

from __future__ import annotations

from pathlib import Path

import pytest

from adl_lite.consensus import ConsensusEngine
from adl_lite.models import DiscoveryStatus
from adl_lite.ontology import OntologyManager, default_ontology
from adl_lite.parser import parse_file
from adl_lite.validator import ADLValidator

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
EXAMPLES = ROOT / "examples"
AML = ROOT / "data" / "aml" / "concepts"
INVALID_PREDICATE = FIXTURES / "invalid_predicate.md"
INVALID_ISOMORPHIC = FIXTURES / "invalid_isomorphic_no_mapping.md"


class TestOntologyYAML:
    def test_yaml_loads_required_keys(self):
        mgr = OntologyManager()
        data_keys = {"classes", "predicates", "status_transitions", "scopes", "mapping_types"}
        assert data_keys <= set(mgr._data.keys())  # noqa: SLF001 — registry smoke test
        assert len(mgr.list_predicates()) >= 8
        assert mgr.scope_prefixes() == ["public", "private", "user", "shared"]

    def test_default_ontology_singleton(self):
        assert default_ontology().path == OntologyManager().path

    def test_all_example_predicates_registered(self):
        mgr = OntologyManager()
        for path in EXAMPLES.glob("*.md"):
            doc = parse_file(path)
            for rel in doc.relations:
                assert mgr.validate_predicate(
                    rel.relation
                ), f"{path.name}: unknown predicate {rel.relation!r}"

    @pytest.mark.skipif(not AML.is_dir(), reason="AML corpus not present")
    def test_all_aml_predicates_registered(self):
        mgr = OntologyManager()
        for path in AML.glob("*.md"):
            doc = parse_file(path)
            for rel in doc.relations:
                assert mgr.validate_predicate(
                    rel.relation
                ), f"{path.name}: unknown predicate {rel.relation!r}"


class TestOntologyTransitions:
    def test_transitions_match_consensus_engine(self):
        mgr = OntologyManager()
        engine = ConsensusEngine()
        for status in DiscoveryStatus:
            yaml_targets = set(mgr.allowed_transitions(status.value))
            for target in DiscoveryStatus:
                engine_ok = engine._is_valid_transition(status, target)  # noqa: SLF001
                yaml_ok = target.value in yaml_targets
                assert (
                    engine_ok == yaml_ok
                ), f"{status.value} -> {target.value}: engine={engine_ok}, yaml={yaml_ok}"


class TestOntologyManagerAPI:
    def test_is_valid_transition_matches_yaml(self):
        mgr = OntologyManager()
        assert mgr.is_valid_transition("provisional", "validated")
        assert not mgr.is_valid_transition("archived", "validated")

    def test_allowed_mapping_types_for_isomorphic(self):
        mgr = OntologyManager()
        allowed = mgr.allowed_mapping_types("isomorphic-to")
        assert "topological" in allowed
        assert mgr.validate_mapping_type("isomorphic-to", "topological")
        assert not mgr.validate_mapping_type("isomorphic-to", "not-a-type")


class TestStrictPredicateValidation:
    def test_unknown_predicate_fails_strict(self):
        doc = parse_file(INVALID_PREDICATE)
        errors = ADLValidator(strict=True).validate_document(doc)
        assert any("Unknown relation predicate" in e for e in errors)
        assert any("similar" in e for e in errors)

    def test_unknown_predicate_passes_default(self):
        doc = parse_file(INVALID_PREDICATE)
        errors = ADLValidator(strict=False).validate_document(doc)
        assert not any("Unknown relation predicate" in e for e in errors)

    def test_validate_predicate_api(self):
        mgr = OntologyManager()
        assert mgr.validate_predicate("isomorphic-to")
        assert not mgr.validate_predicate("similar")

    def test_isomorphic_without_mapping_fails_strict(self):
        doc = parse_file(INVALID_ISOMORPHIC)
        errors = ADLValidator(strict=True).validate_document(doc)
        assert any("requires 'mapping_type'" in e for e in errors)

    def test_isomorphic_without_mapping_passes_default(self):
        doc = parse_file(INVALID_ISOMORPHIC)
        errors = ADLValidator(strict=False).validate_document(doc)
        assert not any("mapping_type" in e for e in errors)
