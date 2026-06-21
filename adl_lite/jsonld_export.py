"""
JSON-LD Export for ADL Lite.

Exports EventChain data to JSON-LD format for linked-data interoperability.
Used for integration with semantic-web APIs, graph databases, and knowledge graphs.

Paper §6.2: "JSON-LD export is available for integration with Neo4j and
semantic-web APIs."
"""

from __future__ import annotations

import json
from typing import Any

from .models import ADLDocument, DiscoveryStatus, EventType

ADL_CONTEXT = {
    "@vocab": "http://adl-lite.org/ontology/",
    "adl": "http://adl-lite.org/ontology/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "status": {
        "@id": "adl:hasStatus",
        "@type": "@id",
    },
    "confidence": {
        "@id": "adl:hasConfidence",
        "@type": "xsd:float",
    },
    "validators": {
        "@id": "adl:validatedBy",
        "@type": "@id",
    },
    "domain": "adl:hasDomain",
    "scope": "adl:hasScope",
    "events": {
        "@id": "adl:hasEvent",
        "@type": "@id",
    },
    "actor": "adl:hasActor",
    "timestamp": {
        "@id": "adl:hasTimestamp",
        "@type": "xsd:dateTime",
    },
    "event_type": {
        "@id": "adl:hasEventType",
        "@type": "@id",
    },
}


def _status_to_uri(status: DiscoveryStatus) -> str:
    """Map ADL status to URI."""
    return f"http://adl-lite.org/ontology/status/{status.value}"


def _event_type_to_uri(event_type: EventType) -> str:
    """Map ADL event type to URI."""
    return f"http://adl-lite.org/ontology/event/{event_type.value}"


def document_to_jsonld(doc: ADLDocument) -> dict[str, Any]:
    """
    Convert an ADLDocument to JSON-LD.

    Returns a JSON-LD dict that can be serialized with json.dumps().
    """
    concept_uri = f"http://adl-lite.org/ontology/{doc.adl_id}"

    events = []
    for event in doc.event_chain.events:
        event_obj: dict[str, Any] = {
            "@id": f"http://adl-lite.org/ontology/event/{event.event_id}",
            "@type": "adl:Event",
            "adl:belongsTo": {"@id": concept_uri},
            "actor": event.actor,
            "timestamp": event.timestamp,
            "event_type": {"@id": _event_type_to_uri(event.event_type)},
        }
        if event.reasoning:
            event_obj["reasoning"] = event.reasoning
        if event.payload:
            event_obj["payload"] = event.payload
        events.append(event_obj)

    result: dict[str, Any] = {
        "@context": ADL_CONTEXT,
        "@id": concept_uri,
        "@type": f"adl:{doc.front_matter.adl_type.value}",
        "status": {"@id": _status_to_uri(doc.front_matter.status)},
        "confidence": doc.front_matter.confidence,
        "domain": doc.front_matter.domain,
        "scope": doc.front_matter.scope,
        "events": events,
    }

    if doc.front_matter.validators:
        result["validators"] = [
            {"@id": f"http://adl-lite.org/ontology/agent/{v}"} for v in doc.front_matter.validators
        ]

    if doc.front_matter.mechanism:
        result["mechanism"] = doc.front_matter.mechanism.value

    if doc.front_matter.novelty:
        result["novelty"] = doc.front_matter.novelty

    if doc.front_matter.provisional_names.zh:
        result["provisional_name_zh"] = doc.front_matter.provisional_names.zh
    if doc.front_matter.provisional_names.en:
        result["provisional_name_en"] = doc.front_matter.provisional_names.en

    return result


def export_jsonld(doc: ADLDocument, indent: int = 2) -> str:
    """
    Export an ADLDocument to JSON-LD string.

    Args:
        doc: The ADLDocument to export
        indent: JSON indentation level

    Returns:
        JSON-LD serialization as a string
    """
    return json.dumps(document_to_jsonld(doc), indent=indent, ensure_ascii=False)


def export_jsonld_compact(doc: ADLDocument) -> str:
    """Export to compact JSON-LD (single line, no indentation)."""
    return json.dumps(document_to_jsonld(doc), separators=(",", ":"), ensure_ascii=False)
