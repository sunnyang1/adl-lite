"""
Tests for adl_lite.shacl_validation — SHACL validation over PROV-O export.
"""

from __future__ import annotations

from adl_lite.models import Event, EventChain, EventType
from adl_lite.prov_export import to_prov_o
from adl_lite.shacl_validation import validate_adl_rdf


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
