"""
Tests for adl_lite.validator — SSA semantic validation and Phase 2 governance.
"""

from __future__ import annotations

from adl_lite.models import (
    ADLDocument,
    ADLFrontMatter,
    ADLRelationBlock,
    ADLType,
    DiscoveryStatus,
    ProvisionalNames,
)
from adl_lite.validator import ADLValidator


class TestRelationGovernance:
    """L3 relation Invariant 2 and predicate semantics."""

    def _doc_with_relations(
        self, status: DiscoveryStatus, *relations: ADLRelationBlock
    ) -> ADLDocument:
        return ADLDocument(
            front_matter=ADLFrontMatter(
                adl_type=ADLType.CONCEPT,
                adl_id="rel-test",
                status=status,
                confidence=0.8,
                scope="public",
                provisional_names=ProvisionalNames(en="rel-test"),
            ),
            markdown_body="A test concept.",
            adl_blocks=list(relations),
        )

    def test_valid_relation_passes(self):
        doc = self._doc_with_relations(
            DiscoveryStatus.VALIDATED,
            ADLRelationBlock(source="rel-test", relation="related-to", target="other"),
        )
        errors = ADLValidator().validate_document(doc)
        assert not any("Invariant 2" in e for e in errors)

    def test_archived_source_violates_invariant(self):
        doc = self._doc_with_relations(
            DiscoveryStatus.ARCHIVED,
            ADLRelationBlock(source="rel-test", relation="related-to", target="other"),
        )
        errors = ADLValidator().validate_document(doc)
        assert any("Invariant 2" in e for e in errors)

    def test_dual_deprecated_violates_invariant(self):
        doc = self._doc_with_relations(
            DiscoveryStatus.DEPRECATED,
            ADLRelationBlock(source="rel-test", relation="related-to", target="also-deprecated"),
        )
        # Provide a status resolver so the target is also deprecated.
        errors = ADLValidator(
            status_resolver=lambda _cid: DiscoveryStatus.DEPRECATED
        ).validate_document(doc)
        assert any("Invariant 2" in e for e in errors)

    def test_strict_requires_mapping_type_for_isomorphic(self):
        doc = self._doc_with_relations(
            DiscoveryStatus.VALIDATED,
            ADLRelationBlock(source="rel-test", relation="isomorphic-to", target="other"),
        )
        errors = ADLValidator(strict=True).validate_document(doc)
        assert any("mapping_type" in e.lower() for e in errors)

    def test_strict_allows_valid_mapping_type(self):
        doc = self._doc_with_relations(
            DiscoveryStatus.VALIDATED,
            ADLRelationBlock(
                source="rel-test",
                relation="isomorphic-to",
                target="other",
                mapping_type="topological",
            ),
        )
        errors = ADLValidator(strict=True).validate_document(doc)
        assert not any("mapping_type" in e.lower() for e in errors)

    def test_strict_rejects_self_referential_transitive(self):
        doc = self._doc_with_relations(
            DiscoveryStatus.VALIDATED,
            ADLRelationBlock(
                source="rel-test",
                relation="specialisation-of",
                target="rel-test",
                mapping_type="ontological",
            ),
        )
        errors = ADLValidator(strict=True).validate_document(doc)
        assert any("self-referential" in e.lower() for e in errors)

    def test_status_resolver_for_external_targets(self):
        doc = self._doc_with_relations(
            DiscoveryStatus.VALIDATED,
            ADLRelationBlock(source="rel-test", relation="related-to", target="external"),
        )
        resolver_calls = []

        def resolver(cid: str) -> DiscoveryStatus:
            resolver_calls.append(cid)
            return DiscoveryStatus.PROVISIONAL

        ADLValidator(status_resolver=resolver).validate_document(doc)
        assert "external" in resolver_calls


class TestShaclOptIn:
    """Runtime SHACL validation is disabled by default and opt-in."""

    def _make_doc(self) -> ADLDocument:
        return ADLDocument(
            front_matter=ADLFrontMatter(
                adl_type=ADLType.CONCEPT,
                adl_id="shacl-test",
                status=DiscoveryStatus.PROVISIONAL,
                confidence=0.0,
                scope="public",
                provisional_names=ProvisionalNames(en="shacl-test"),
            ),
            markdown_body="Test body.",
        )

    def test_shacl_disabled_by_default(self):
        doc = self._make_doc()
        # Should complete quickly without invoking pyshacl.
        errors = ADLValidator().validate_document(doc)
        assert errors == []

    def test_shacl_enabled_valid_doc(self):
        doc = self._make_doc()
        errors = ADLValidator(shacl=True).validate_document(doc)
        assert errors == []

    def test_shacl_enabled_invalid_relation(self):
        doc = ADLDocument(
            front_matter=ADLFrontMatter(
                adl_type=ADLType.CONCEPT,
                adl_id="shacl-test",
                status=DiscoveryStatus.PROVISIONAL,
                confidence=0.0,
                scope="public",
            ),
            markdown_body="Test body.",
            adl_blocks=[],
        )
        relation = ADLRelationBlock(
            source="shacl-test",
            relation="related-to",
            target="other",
            confidence=0.9,
        )
        relation.confidence = 1.5  # bypass Pydantic validation for SHACL test
        doc.adl_blocks = [relation]
        errors = ADLValidator(shacl=True).validate_document(doc)
        assert errors
        assert any("SHACL" in e for e in errors)
