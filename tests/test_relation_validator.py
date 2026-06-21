"""
Tests for L3 Relation Reconciliation Validator (Invariant 2).

Paper §4.2: "valid(r) ↔ S(C1) ∉ {archived} ∧ S(C2) ∉ {archived}
              ∧ ¬(S(C1)=deprecated ∧ S(C2)=deprecated)"
"""

from __future__ import annotations

from adl_lite import (
    ADLRelationBlock,
    DiscoveryStatus,
    EventChain,
    RelationValidator,
)


class TestRelationValidator:
    """Test suite for Invariant 2 — L3 Relation Reconciliation."""

    def test_valid_both_validated(self) -> None:
        """Relation between two validated concepts is valid."""
        validator = RelationValidator()
        rel = ADLRelationBlock(source="concept-a", relation="isomorphic-to", target="concept-b")
        assert validator.valid(rel, DiscoveryStatus.VALIDATED, DiscoveryStatus.VALIDATED)

    def test_valid_one_deprecated(self) -> None:
        """Relation with one deprecated endpoint is valid."""
        validator = RelationValidator()
        rel = ADLRelationBlock(source="concept-a", relation="related-to", target="concept-b")
        assert validator.valid(rel, DiscoveryStatus.VALIDATED, DiscoveryStatus.DEPRECATED)
        assert validator.valid(rel, DiscoveryStatus.DEPRECATED, DiscoveryStatus.VALIDATED)

    def test_invalid_both_deprecated(self) -> None:
        """Relation between two deprecated concepts is invalid."""
        validator = RelationValidator()
        rel = ADLRelationBlock(source="concept-a", relation="isomorphic-to", target="concept-b")
        assert not validator.valid(rel, DiscoveryStatus.DEPRECATED, DiscoveryStatus.DEPRECATED)

    def test_invalid_source_archived(self) -> None:
        """Relation with archived source is invalid."""
        validator = RelationValidator()
        rel = ADLRelationBlock(source="concept-a", relation="related-to", target="concept-b")
        assert not validator.valid(rel, DiscoveryStatus.ARCHIVED, DiscoveryStatus.VALIDATED)

    def test_invalid_target_archived(self) -> None:
        """Relation with archived target is invalid."""
        validator = RelationValidator()
        rel = ADLRelationBlock(source="concept-a", relation="related-to", target="concept-b")
        assert not validator.valid(rel, DiscoveryStatus.VALIDATED, DiscoveryStatus.ARCHIVED)

    def test_invalid_both_archived(self) -> None:
        """Relation between two archived concepts is invalid."""
        validator = RelationValidator()
        rel = ADLRelationBlock(source="concept-a", relation="isomorphic-to", target="concept-b")
        assert not validator.valid(rel, DiscoveryStatus.ARCHIVED, DiscoveryStatus.ARCHIVED)

    def test_filter_valid_relations(self) -> None:
        """Filter a list of relations, keeping only valid ones."""
        validator = RelationValidator()
        relations = [
            ADLRelationBlock(source="a", relation="isomorphic-to", target="b"),
            ADLRelationBlock(source="c", relation="related-to", target="d"),
            ADLRelationBlock(source="e", relation="analogical-to", target="f"),
        ]
        status_lookup = {
            "a": DiscoveryStatus.VALIDATED,
            "b": DiscoveryStatus.VALIDATED,
            "c": DiscoveryStatus.VALIDATED,
            "d": DiscoveryStatus.DEPRECATED,
            "e": DiscoveryStatus.DEPRECATED,
            "f": DiscoveryStatus.DEPRECATED,
        }
        valid = validator.filter_valid_relations(relations, status_lookup)
        assert len(valid) == 2
        assert valid[0].source == "a"
        assert valid[1].source == "c"

    def test_fork_inheritance_isomorphic(self) -> None:
        """Fork inherits isomorphic-to relations."""
        validator = RelationValidator()
        parent = EventChain(concept_id="parent-concept")
        parent_relations = [
            ADLRelationBlock(source="parent-concept", relation="isomorphic-to", target="other"),
        ]
        inherited = validator.inherit_relations(parent, "child-concept", parent_relations)
        assert len(inherited) == 1
        assert inherited[0].source == "child-concept"
        assert inherited[0].relation == "isomorphic-to"
        assert inherited[0].target == "other"

    def test_fork_inheritance_specialisation(self) -> None:
        """Fork inherits specialisation-of relations."""
        validator = RelationValidator()
        parent = EventChain(concept_id="parent-concept")
        parent_relations = [
            ADLRelationBlock(source="other", relation="specialisation-of", target="parent-concept"),
        ]
        inherited = validator.inherit_relations(parent, "child-concept", parent_relations)
        assert len(inherited) == 1
        assert inherited[0].target == "child-concept"
        assert inherited[0].relation == "specialisation-of"

    def test_fork_no_analogical_inheritance(self) -> None:
        """Fork does NOT inherit analogical-to relations."""
        validator = RelationValidator()
        parent = EventChain(concept_id="parent-concept")
        parent_relations = [
            ADLRelationBlock(source="parent-concept", relation="analogical-to", target="other"),
        ]
        inherited = validator.inherit_relations(parent, "child-concept", parent_relations)
        assert len(inherited) == 0

    def test_check_invariant_violations(self) -> None:
        """Detect and report invariant violations."""
        validator = RelationValidator()
        relations = [
            ADLRelationBlock(source="a", relation="isomorphic-to", target="b"),
            ADLRelationBlock(source="c", relation="related-to", target="d"),
        ]
        status_lookup = {
            "a": DiscoveryStatus.VALIDATED,
            "b": DiscoveryStatus.VALIDATED,
            "c": DiscoveryStatus.DEPRECATED,
            "d": DiscoveryStatus.DEPRECATED,
        }
        violations = validator.check_invariant_violations(relations, status_lookup)
        assert len(violations) == 1
        assert "c" in violations[0]
        assert "d" in violations[0]

    def test_inheritance_mixed_predicates(self) -> None:
        """Fork inherits only the allowed predicates."""
        validator = RelationValidator()
        parent = EventChain(concept_id="parent-concept")
        parent_relations = [
            ADLRelationBlock(source="parent-concept", relation="isomorphic-to", target="a"),
            ADLRelationBlock(source="parent-concept", relation="specialisation-of", target="b"),
            ADLRelationBlock(source="parent-concept", relation="analogical-to", target="c"),
            ADLRelationBlock(source="parent-concept", relation="related-to", target="d"),
        ]
        inherited = validator.inherit_relations(parent, "child-concept", parent_relations)
        assert len(inherited) == 2
        preds = {r.relation for r in inherited}
        assert "isomorphic-to" in preds
        assert "specialisation-of" in preds
        assert "analogical-to" not in preds
        assert "related-to" not in preds
