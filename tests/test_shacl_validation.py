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
