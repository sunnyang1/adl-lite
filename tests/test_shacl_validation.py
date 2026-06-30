"""
Tests for adl_lite.shacl_validation — SHACL validation over PROV-O export.
"""

from __future__ import annotations

from adl_lite.models import (
    ADLActionBlock,
    ADLDocument,
    ADLFrontMatter,
    ADLRelationBlock,
    ADLType,
    DiscoveryStatus,
    Event,
    EventChain,
    EventType,
    ProvisionalNames,
)
from adl_lite.prov_export import to_prov_o
from adl_lite.shacl_validation import validate_adl_document, validate_adl_rdf
from adl_lite.validator import ADLValidator


class TestShaclValidation:
    """Validate SHACL shapes over auto-generated PROV-O."""

    def test_valid_chain_conforms(self):
        chain = EventChain(concept_id="shacl-ok")
        chain.append(
            Event(
                concept_id="shacl-ok",
                event_type=EventType.REGISTER,
                actor="discoverer",
                timestamp="2024-01-15T09:00:00+00:00",
            )
        )
        chain.append(
            Event(
                concept_id="shacl-ok",
                event_type=EventType.VALIDATE,
                actor="reviewer",
                timestamp="2024-01-15T14:30:00+00:00",
                payload={"confidence": 0.85},
            )
        )
        ttl = to_prov_o(chain)
        conforms, report = validate_adl_rdf(ttl)
        assert conforms, f"Valid chain should conform. Report:\n{report}"

    def test_missing_timestamp_still_conforms(self):
        # timestamp is sh:maxCount 1 but not sh:minCount 1
        chain = EventChain(concept_id="shacl-no-ts")
        chain.append(
            Event(
                concept_id="shacl-no-ts",
                event_type=EventType.REGISTER,
                actor="system",
            )
        )
        ttl = to_prov_o(chain)
        conforms, report = validate_adl_rdf(ttl)
        assert conforms, f"Missing timestamp should still conform. Report:\n{report}"

    def test_malformed_event_hash_fails(self):
        # Manually inject an invalid hash into the turtle
        chain = EventChain(concept_id="shacl-bad-hash")
        chain.append(
            Event(
                concept_id="shacl-bad-hash",
                event_type=EventType.REGISTER,
                actor="system",
                timestamp="2024-01-15T09:00:00+00:00",
            )
        )
        ttl = to_prov_o(chain)
        # Corrupt the hash literal
        bad_ttl = ttl.replace('adl:eventHash "', 'adl:eventHash "INVALID_')
        conforms, report = validate_adl_rdf(bad_ttl)
        assert not conforms, "Invalid hash pattern should fail SHACL validation"
        assert "pattern" in report.lower() or "eventHash" in report


class TestRuntimeShaclValidation:
    """Runtime SHACL validation on ADLDocument instances (Phase 2)."""

    def _make_doc(self, relations=None, action_blocks=None):
        return ADLDocument(
            front_matter=ADLFrontMatter(
                adl_type=ADLType.CONCEPT,
                adl_id="shacl-doc",
                status=DiscoveryStatus.VALIDATED,
                confidence=0.85,
                scope="public",
                provisional_names=ProvisionalNames(en="shacl-doc"),
            ),
            markdown_body="A test concept.",
            adl_blocks=relations or [],
            action_blocks=action_blocks or [],
        )

    def test_valid_document_conforms(self):
        doc = self._make_doc(
            relations=[
                ADLRelationBlock(
                    source="shacl-doc",
                    relation="related-to",
                    target="other-concept",
                    confidence=0.9,
                )
            ],
            action_blocks=[
                ADLActionBlock(
                    action="calibrate",
                    actor="reviewer",
                    reasoning="Calibration",
                    params={"observed_accuracy": 0.8},
                )
            ],
        )
        conforms, report = validate_adl_document(doc)
        assert conforms, f"Valid document should conform. Report:\n{report}"

    def test_relation_confidence_out_of_range_fails(self):
        relation = ADLRelationBlock(
            source="shacl-doc",
            relation="related-to",
            target="other-concept",
            confidence=0.9,
        )
        relation.confidence = 1.5  # bypass Pydantic validation for SHACL test
        doc = self._make_doc(relations=[relation])
        conforms, report = validate_adl_document(doc)
        assert not conforms, "Relation confidence outside [0,1] should fail"
        assert "confidence" in report.lower()

    def test_calibrate_event_missing_observed_accuracy_fails(self):
        doc = self._make_doc(
            action_blocks=[
                ADLActionBlock(
                    action="calibrate",
                    actor="reviewer",
                    reasoning="Calibration",
                    params={},
                )
            ]
        )
        conforms, report = validate_adl_document(doc)
        assert not conforms, "CALIBRATE event without observedAccuracy should fail"
        assert "observedAccuracy" in report or "CalibrateEvent" in report

    def test_calibrate_event_invalid_observed_accuracy_fails(self):
        doc = self._make_doc(
            action_blocks=[
                ADLActionBlock(
                    action="calibrate",
                    actor="reviewer",
                    reasoning="Calibration",
                    params={"observed_accuracy": 1.5},
                )
            ]
        )
        conforms, report = validate_adl_document(doc)
        assert not conforms, "CALIBRATE event with invalid observedAccuracy should fail"


class TestShaclDefaultOn:
    """SHACL auto-detection in ADLValidator (T02)."""

    def test_auto_detect_enabled(self):
        """When pyshacl is importable, ADLValidator(shacl=None) sets shacl=True."""
        validator = ADLValidator(shacl=None)
        assert validator.shacl is True

    def test_auto_detect_disabled(self):
        """When shacl=False is passed explicitly, ADLValidator disables SHACL."""
        validator = ADLValidator(shacl=False)
        assert validator.shacl is False
        # Validation should still work without SHACL
        doc = self._make_concept_doc()
        errors = validator.validate_document(doc)
        # No SHACL-related errors returned
        assert not any("SHACL" in e for e in errors)

    @staticmethod
    def _make_concept_doc() -> ADLDocument:
        return ADLDocument(
            front_matter=ADLFrontMatter(
                adl_type=ADLType.CONCEPT,
                adl_id="test-concept",
                status=DiscoveryStatus.PROVISIONAL,
                confidence=0.5,
                scope="public",
                provisional_names=ProvisionalNames(en="test-concept"),
            ),
            markdown_body="A test concept.",
        )


class TestForkShapeValidation:
    """ForkShape SHACL validation (T03)."""

    def _make_doc(self, action_blocks=None):
        return ADLDocument(
            front_matter=ADLFrontMatter(
                adl_type=ADLType.CONCEPT,
                adl_id="fork-doc",
                status=DiscoveryStatus.VALIDATED,
                confidence=0.85,
                scope="public",
                provisional_names=ProvisionalNames(en="fork-doc"),
            ),
            markdown_body="A fork test concept.",
            adl_blocks=[],
            action_blocks=action_blocks or [],
        )

    def test_fork_event_with_source_target_conforms(self):
        """FORK event with both source_concept_id and target_concept_id should conform."""
        doc = self._make_doc(
            action_blocks=[
                ADLActionBlock(
                    action="fork",
                    actor="system",
                    reasoning="Forking concept",
                    params={
                        "source_concept_id": "concept-a",
                        "target_concept_id": "concept-b",
                    },
                )
            ]
        )
        conforms, report = validate_adl_document(doc)
        assert conforms, f"Fork with source+target should conform. Report:\n{report}"

    def test_fork_event_missing_source_fails(self):
        """FORK event without source_concept_id should NOT conform."""
        doc = self._make_doc(
            action_blocks=[
                ADLActionBlock(
                    action="fork",
                    actor="system",
                    reasoning="Forking concept",
                    params={
                        "target_concept_id": "concept-b",
                    },
                )
            ]
        )
        conforms, report = validate_adl_document(doc)
        assert not conforms, "Fork without source_concept_id should fail"
        assert "sourceConceptId" in report

    def test_fork_event_missing_target_fails(self):
        """FORK event without target_concept_id should NOT conform."""
        doc = self._make_doc(
            action_blocks=[
                ADLActionBlock(
                    action="fork",
                    actor="system",
                    reasoning="Forking concept",
                    params={
                        "source_concept_id": "concept-a",
                    },
                )
            ]
        )
        conforms, report = validate_adl_document(doc)
        assert not conforms, "Fork without target_concept_id should fail"
        assert "targetConceptId" in report


class TestCliShaclFlags:
    """CLI --shacl/--no-shacl flags and standalone 'adl-lite shacl' subcommand (T04)."""

    def test_cli_validate_shacl_flag(self):
        """ADLValidator(shacl=True) enables SHACL validation."""
        validator = ADLValidator(shacl=True)
        assert validator.shacl is True

    def test_cli_validate_no_shacl_flag(self):
        """ADLValidator(shacl=False) disables SHACL validation."""
        validator = ADLValidator(shacl=False)
        assert validator.shacl is False

    def test_standalone_shacl_command_ok(self):
        """The standalone shacl subcommand works with a valid file via _cmd_shacl."""
        import tempfile
        from argparse import Namespace
        from pathlib import Path

        from adl_lite.cli import _cmd_shacl

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""---
adl_id: shacl-cli-test
adl_type: concept
status: validated
confidence: 0.85
scope: public
names: { "en": "SHACL CLI Test" }
---
# SHACL CLI Test
""")
            tmp_path = f.name

        try:
            ns = Namespace(files=[tmp_path])
            ret = _cmd_shacl(ns)
            assert ret == 0
        finally:
            Path(tmp_path).unlink(missing_ok=True)
