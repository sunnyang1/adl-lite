"""
Tests for adl_lite.jsonld_export — JSON-LD contract tests.

Covers the @context / @type structure, front-matter field mapping, event-chain
serialization, and round-trip stability of key fields.
"""

from __future__ import annotations

import json
from typing import Any

from adl_lite.jsonld_export import (
    ADL_CONTEXT,
    document_to_jsonld,
    export_jsonld,
    export_jsonld_compact,
)
from adl_lite.models import (
    ADLActionBlock,
    ADLDocument,
    ADLFrontMatter,
    ADLType,
    DiscoveryStatus,
    MechanismType,
    ProvisionalNames,
)

ADL_NS = "http://adl-lite.org/ontology/"


def _make_doc(**overrides: Any) -> ADLDocument:
    """Build a sample ADLDocument; keyword overrides patch front-matter fields."""
    fm_fields: dict[str, Any] = {
        "adl_type": ADLType.DISCOVERY,
        "adl_id": "jsonld-test",
        "status": DiscoveryStatus.VALIDATED,
        "confidence": 0.85,
        "validators": ["agent_1", "agent_2"],
        "domain": "aml",
        "scope": "public",
    }
    fm_fields.update(overrides)
    return ADLDocument(front_matter=ADLFrontMatter(**fm_fields), markdown_body="# Test")


# ---------------------------------------------------------------------------
# @context structure
# ---------------------------------------------------------------------------


class TestContext:
    def test_context_vocab_and_prefixes(self):
        ctx = ADL_CONTEXT
        assert ctx["@vocab"] == ADL_NS
        assert ctx["adl"] == ADL_NS
        for prefix in ("rdf", "rdfs", "xsd", "owl"):
            assert prefix in ctx

    def test_context_field_mappings(self):
        assert ADL_CONTEXT["status"] == {"@id": "adl:hasStatus", "@type": "@id"}
        assert ADL_CONTEXT["confidence"] == {"@id": "adl:hasConfidence", "@type": "xsd:float"}
        assert ADL_CONTEXT["validators"] == {"@id": "adl:validatedBy", "@type": "@id"}
        assert ADL_CONTEXT["domain"] == "adl:hasDomain"
        assert ADL_CONTEXT["scope"] == "adl:hasScope"
        assert ADL_CONTEXT["timestamp"]["@type"] == "xsd:dateTime"

    def test_export_embeds_context(self):
        result = document_to_jsonld(_make_doc())
        assert result["@context"] is ADL_CONTEXT


# ---------------------------------------------------------------------------
# Document-level structure & front-matter mapping
# ---------------------------------------------------------------------------


class TestDocumentMapping:
    def test_id_and_type(self):
        result = document_to_jsonld(_make_doc())
        assert result["@id"] == f"{ADL_NS}jsonld-test"
        assert result["@type"] == "adl:discovery"

    def test_status_is_uri_reference(self):
        result = document_to_jsonld(_make_doc())
        assert result["status"] == {"@id": f"{ADL_NS}status/validated"}

    def test_confidence_domain_scope(self):
        result = document_to_jsonld(_make_doc())
        assert result["confidence"] == 0.85
        assert result["domain"] == "aml"
        assert result["scope"] == "public"

    def test_validators_mapped_as_agent_uris(self):
        result = document_to_jsonld(_make_doc())
        assert result["validators"] == [
            {"@id": f"{ADL_NS}agent/agent_1"},
            {"@id": f"{ADL_NS}agent/agent_2"},
        ]

    def test_optional_fields_absent_by_default(self):
        result = document_to_jsonld(_make_doc(validators=[], domain=""))
        assert "validators" not in result
        assert "mechanism" not in result
        assert "novelty" not in result
        assert "provisional_name_zh" not in result
        assert "provisional_name_en" not in result
        # domain is still emitted (empty string is a stored value)
        assert result["domain"] == ""

    def test_optional_fields_present(self):
        doc = _make_doc(
            mechanism=MechanismType.ANALOGICAL_TRANSFER,
            novelty=0.7,
            provisional_names=ProvisionalNames(zh="资本回流陷阱", en="capital-reflux"),
        )
        result = document_to_jsonld(doc)
        assert result["mechanism"] == "analogical_transfer"
        assert result["novelty"] == 0.7
        assert result["provisional_name_zh"] == "资本回流陷阱"
        assert result["provisional_name_en"] == "capital-reflux"


# ---------------------------------------------------------------------------
# Event-chain serialization
# ---------------------------------------------------------------------------


class TestEventSerialization:
    def test_events_present_and_typed(self):
        doc = _make_doc()
        result = document_to_jsonld(doc)
        events = result["events"]
        # VALIDATED doc synthesizes SNAPSHOT + VALIDATE events.
        assert len(events) == len(doc.event_chain.events) >= 2
        for event in events:
            assert event["@id"].startswith(f"{ADL_NS}event/")
            assert event["@type"] == "adl:Event"
            assert event["adl:belongsTo"] == {"@id": f"{ADL_NS}jsonld-test"}
            assert event["actor"]
            assert event["timestamp"]
            assert event["event_type"]["@id"].startswith(f"{ADL_NS}event/")

    def test_event_type_uris(self):
        result = document_to_jsonld(_make_doc())
        type_uris = {e["event_type"]["@id"] for e in result["events"]}
        assert f"{ADL_NS}event/snapshot" in type_uris
        assert f"{ADL_NS}event/validate" in type_uris

    def test_action_block_event_carries_reasoning_and_payload(self):
        doc = _make_doc()
        doc.action_blocks.append(
            ADLActionBlock(
                action="validate",
                actor="agent_3",
                reasoning="cross-domain check passed",
                params={"confidence_boost": 0.1},
            )
        )
        result = document_to_jsonld(doc)
        action_events = [e for e in result["events"] if e["actor"] == "agent_3"]
        assert len(action_events) == 1
        event = action_events[0]
        assert event["reasoning"] == "cross-domain check passed"
        assert event["payload"]["action"] == "validate"
        assert event["payload"]["params"] == {"confidence_boost": 0.1}


# ---------------------------------------------------------------------------
# String exports & round-trip stability
# ---------------------------------------------------------------------------


class TestStringExports:
    @staticmethod
    def _normalize_events(payload: dict) -> dict:
        """Strip per-generation event ids/timestamps for cross-call comparison.

        ``document_to_jsonld`` rebuilds the synthetic event chain on every
        call, minting fresh event ids and timestamps; everything else is
        deterministic.
        """
        events = [
            {k: v for k, v in e.items() if k not in ("@id", "timestamp")} for e in payload["events"]
        ]
        return {**payload, "events": events}

    def test_export_jsonld_is_valid_indented_json(self):
        doc = _make_doc()
        text = export_jsonld(doc)
        assert "\n" in text  # default indent=2
        parsed = json.loads(text)
        assert parsed["@id"] == f"{ADL_NS}jsonld-test"
        assert parsed["@type"] == "adl:discovery"
        assert len(parsed["events"]) == len(doc.event_chain.events)

    def test_export_jsonld_preserves_unicode(self):
        doc = _make_doc(provisional_names=ProvisionalNames(zh="资本回流陷阱"))
        assert "资本回流陷阱" in export_jsonld(doc)

    def test_export_jsonld_compact_single_line(self):
        doc = _make_doc()
        compact = export_jsonld_compact(doc)
        assert "\n" not in compact
        # Compact and indented serializations carry identical content
        # (modulo per-generation event ids/timestamps).
        assert self._normalize_events(json.loads(compact)) == self._normalize_events(
            json.loads(export_jsonld(doc))
        )

    def test_roundtrip_key_fields(self):
        """json.loads(export_jsonld(doc)) preserves all key contract fields."""
        doc = _make_doc(
            mechanism=MechanismType.ISOMORPHIC_MAPPING,
            novelty=0.3,
            provisional_names=ProvisionalNames(en="jsonld-test"),
        )
        parsed = json.loads(export_jsonld(doc))
        assert parsed["@id"] == f"{ADL_NS}jsonld-test"
        assert parsed["@type"] == "adl:discovery"
        assert parsed["status"] == {"@id": f"{ADL_NS}status/validated"}
        assert parsed["confidence"] == 0.85
        assert parsed["domain"] == "aml"
        assert parsed["scope"] == "public"
        assert parsed["mechanism"] == "isomorphic_mapping"
        assert parsed["novelty"] == 0.3
        assert parsed["provisional_name_en"] == "jsonld-test"
        assert [v["@id"] for v in parsed["validators"]] == [
            f"{ADL_NS}agent/agent_1",
            f"{ADL_NS}agent/agent_2",
        ]
        assert len(parsed["events"]) == len(doc.event_chain.events)
