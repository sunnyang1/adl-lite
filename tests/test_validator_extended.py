"""
Extended tests for adl_lite.validator — SHACL graceful degradation,
front matter range checks, discovery/mechanism, formal seal strict,
scope validation, relation edge cases, and governance resolver exceptions.

Covers uncovered lines: 256-257, 261-262, 304, 306, 310, 313-314, 297,
331, 333, 340, 353-354, 240-241.
"""

from __future__ import annotations

import sys
from unittest.mock import patch

from adl_lite.models import (
    ADLDocument,
    ADLFrontMatter,
    ADLRelationBlock,
    ADLType,
    DiscoveryStatus,
    ProvisionalNames,
)
from adl_lite.validator import ADLValidator

# ---------------------------------------------------------------------------
# SHACL graceful degradation tests
# ---------------------------------------------------------------------------


class TestShaclGracefulDegradation:
    """Tests for SHACL import error and general exception handling."""

    def test_shacl_import_error_graceful(self):
        """Mock adl_lite.shacl_validation to raise ImportError when imported.
        Call validate_shacl on a document, verify it returns a graceful
        degradation message instead of crashing. Covers lines 256-257."""
        doc = ADLDocument(
            front_matter=ADLFrontMatter(
                adl_type=ADLType.CONCEPT,
                adl_id="shacl-import-test",
                status=DiscoveryStatus.PROVISIONAL,
                confidence=0.5,
                scope="public",
                provisional_names=ProvisionalNames(en="shacl-import-test"),
            ),
            markdown_body="Test body.",
        )

        validator = ADLValidator(shacl=True)

        # Patch the import that happens in _validate_shacl:
        #   from .shacl_validation import validate_adl_document
        # We make shacl_validation a module that raises ImportError
        with patch.dict(sys.modules, {"adl_lite.shacl_validation": None}):
            errors = validator.validate_document(doc)

        # Should contain a graceful SHACL unavailable message
        assert any("SHACL validation unavailable" in e for e in errors)

    def test_shacl_general_exception(self):
        """Mock adl_lite.shacl_validation.validate_adl_document to raise
        an unexpected RuntimeError. Verify the validator catches the exception
        and returns appropriate error info. Covers lines 261-262."""
        doc = ADLDocument(
            front_matter=ADLFrontMatter(
                adl_type=ADLType.CONCEPT,
                adl_id="shacl-exc-test",
                status=DiscoveryStatus.PROVISIONAL,
                confidence=0.5,
                scope="public",
                provisional_names=ProvisionalNames(en="shacl-exc-test"),
            ),
            markdown_body="Test body.",
        )

        validator = ADLValidator(shacl=True)

        # Patch validate_adl_document to raise RuntimeError
        with patch(
            "adl_lite.shacl_validation.validate_adl_document",
            side_effect=RuntimeError("Unexpected SHACL failure"),
        ):
            errors = validator.validate_document(doc)

        # Should contain a SHACL validation error message
        assert any("SHACL validation error" in e for e in errors)
        assert any("RuntimeError" in e or "Unexpected" in e for e in errors)


# ---------------------------------------------------------------------------
# Front matter validation tests
# ---------------------------------------------------------------------------


class TestFrontMatterValidation:
    """Tests for front matter confidence/novelty range, mechanism, and formal seal."""

    def _make_doc_with_fm(self, fm: ADLFrontMatter) -> ADLDocument:
        """Helper to create an ADLDocument with a given front matter."""
        return ADLDocument(
            front_matter=fm,
            markdown_body="Test body.",
        )

    def test_front_matter_confidence_out_of_range(self):
        """Create an event with confidence=1.5 (outside valid 0-1 range).
        Call validate_event_chain equivalent (validate_document).
        Verify it reports a validation error for confidence. Covers line 304."""
        # Pydantic enforces ge=0.0, le=1.0, so we need to bypass it
        fm = ADLFrontMatter(
            adl_type=ADLType.CONCEPT,
            adl_id="conf-test",
            status=DiscoveryStatus.PROVISIONAL,
            confidence=0.5,
            scope="public",
            provisional_names=ProvisionalNames(en="conf-test"),
        )
        # Bypass Pydantic validation by directly setting confidence
        object.__setattr__(fm, "confidence", 1.5)

        doc = self._make_doc_with_fm(fm)
        errors = ADLValidator().validate_document(doc)
        assert any("confidence must be in [0, 1]" in e for e in errors)
        assert any("1.5" in e for e in errors)

    def test_front_matter_novelty_out_of_range(self):
        """Create an event with novelty=-0.5 (outside valid 0-1 range).
        Verify validation catches this. Covers line 306."""
        fm = ADLFrontMatter(
            adl_type=ADLType.CONCEPT,
            adl_id="nov-test",
            status=DiscoveryStatus.PROVISIONAL,
            confidence=0.5,
            scope="public",
            provisional_names=ProvisionalNames(en="nov-test"),
            novelty=0.0,
        )
        # Bypass Pydantic validation
        object.__setattr__(fm, "novelty", -0.5)

        doc = self._make_doc_with_fm(fm)
        errors = ADLValidator().validate_document(doc)
        assert any("novelty must be in [0, 1]" in e for e in errors)
        assert any("-0.5" in e for e in errors)

    def test_discovery_without_mechanism(self):
        """Create a discovery event missing the mechanism field.
        Verify validation fails with appropriate error. Covers line 310."""
        fm = ADLFrontMatter(
            adl_type=ADLType.DISCOVERY,
            adl_id="disc-test",
            status=DiscoveryStatus.PROVISIONAL,
            confidence=0.5,
            scope="public",
            provisional_names=ProvisionalNames(en="disc-test"),
            # mechanism is None by default — this is the violation
        )

        doc = self._make_doc_with_fm(fm)
        errors = ADLValidator().validate_document(doc)
        assert any("mechanism" in e for e in errors)

    def test_formal_seal_strict_no_validators(self):
        """Create a formal_seal event in strict mode with no validators.
        Verify validation failure. Covers lines 313-314."""
        fm = ADLFrontMatter(
            adl_type=ADLType.FORMAL_SEAL,
            adl_id="seal-test",
            status=DiscoveryStatus.PROVISIONAL,
            confidence=0.5,
            scope="public",
            provisional_names=ProvisionalNames(en="seal-test"),
            validators=[],  # No validators
        )

        doc = self._make_doc_with_fm(fm)
        validator = ADLValidator(strict=True)
        errors = validator.validate_document(doc)
        assert any("Formal seal requires at least one validator" in e for e in errors)

    def test_scope_validation_failure(self):
        """Create an event with an invalid scope string.
        Verify validation catches scope error. Covers line 297."""
        fm = ADLFrontMatter(
            adl_type=ADLType.CONCEPT,
            adl_id="scope-test",
            status=DiscoveryStatus.PROVISIONAL,
            confidence=0.5,
            scope="public",
            provisional_names=ProvisionalNames(en="scope-test"),
        )
        # Bypass Pydantic scope validator
        object.__setattr__(fm, "scope", "invalid_prefix/test")

        doc = self._make_doc_with_fm(fm)
        errors = ADLValidator().validate_document(doc)
        assert any("Invalid scope format" in e for e in errors)
        assert any("invalid_prefix/test" in e for e in errors)


# ---------------------------------------------------------------------------
# Relation block validation tests
# ---------------------------------------------------------------------------


class TestRelationBlockValidation:
    """Tests for relation block source/target emptiness and ADL URI validation."""

    def _make_doc_with_relations(
        self, status: DiscoveryStatus, *relations: ADLRelationBlock
    ) -> ADLDocument:
        return ADLDocument(
            front_matter=ADLFrontMatter(
                adl_type=ADLType.CONCEPT,
                adl_id="rel-val-test",
                status=status,
                confidence=0.8,
                scope="public",
                provisional_names=ProvisionalNames(en="rel-val-test"),
            ),
            markdown_body="A test concept.",
            adl_blocks=list(relations),
        )

    def test_relation_empty_source(self):
        """Create a relation block with empty source string.
        Verify validation failure. Covers line 331."""
        # We need to bypass Pydantic's pronoun validator which checks source/target
        # Create a relation and then manually set source to empty
        rel = ADLRelationBlock(
            source="nonempty-source",
            relation="related-to",
            target="some-target",
        )
        # Bypass Pydantic validation by setting source to whitespace-only
        object.__setattr__(rel, "source", "   ")

        doc = self._make_doc_with_relations(DiscoveryStatus.VALIDATED, rel)
        errors = ADLValidator().validate_document(doc)
        assert any("'source' must not be empty" in e for e in errors)

    def test_relation_empty_target(self):
        """Create a relation block with empty target string.
        Verify validation failure. Covers line 333."""
        rel = ADLRelationBlock(
            source="some-source",
            relation="related-to",
            target="nonempty-target",
        )
        # Bypass Pydantic validation by setting target to empty
        object.__setattr__(rel, "target", "")

        doc = self._make_doc_with_relations(DiscoveryStatus.VALIDATED, rel)
        errors = ADLValidator().validate_document(doc)
        assert any("'target' must not be empty" in e for e in errors)

    def test_relation_invalid_adl_uri(self):
        """Create a relation with a malformed ADL URI.
        Verify validation failure. Covers line 340."""
        rel = ADLRelationBlock(
            source="some-source",
            relation="related-to",
            target="adl://invalid-scope/some-id",
        )

        doc = self._make_doc_with_relations(DiscoveryStatus.VALIDATED, rel)
        errors = ADLValidator().validate_document(doc)
        assert any("Invalid ADL URI scheme" in e for e in errors)

    def test_strict_mapping_type_invalid(self):
        """In strict mode, validate with an invalid mapping_type.
        Verify validation failure. Covers lines 353-354."""
        rel = ADLRelationBlock(
            source="rel-val-test",
            relation="isomorphic-to",
            target="other-concept",
            mapping_type="not-a-real-type",
        )

        doc = self._make_doc_with_relations(DiscoveryStatus.VALIDATED, rel)
        validator = ADLValidator(strict=True)
        errors = validator.validate_document(doc)
        assert any("Invalid mapping_type" in e for e in errors)
        assert any("not-a-real-type" in e for e in errors)


# ---------------------------------------------------------------------------
# Relation governance resolver exception tests
# ---------------------------------------------------------------------------


class TestRelationGovernanceResolver:
    """Tests for _validate_relation_governance with resolver exceptions. Covers lines 240-241."""

    def test_relation_governance_status_resolver_exception(self):
        """Pass a status_resolver callback that raises an exception.
        Verify _validate_relation_governance handles the error gracefully
        by defaulting to PROVISIONAL. Covers lines 240-241."""
        doc = ADLDocument(
            front_matter=ADLFrontMatter(
                adl_type=ADLType.CONCEPT,
                adl_id="resolver-exc-test",
                status=DiscoveryStatus.VALIDATED,
                confidence=0.8,
                scope="public",
                provisional_names=ProvisionalNames(en="resolver-exc-test"),
            ),
            markdown_body="Test body.",
            adl_blocks=[
                ADLRelationBlock(
                    source="resolver-exc-test",
                    relation="related-to",
                    target="external-concept",
                ),
            ],
        )

        def broken_resolver(cid: str) -> DiscoveryStatus:
            raise RuntimeError("Resolver crashed")

        validator = ADLValidator(status_resolver=broken_resolver)
        errors = validator.validate_document(doc)

        # The resolver exception should be caught; the external concept
        # should default to PROVISIONAL, and the relation should still
        # pass (since PROVISIONAL is not archived/deprecated)
        # The key thing is that no crash occurs and validation completes
        assert isinstance(errors, list)
        # The relation should not trigger an Invariant 2 violation
        # because the external concept defaults to PROVISIONAL
        assert not any("Invariant 2" in e for e in errors)
