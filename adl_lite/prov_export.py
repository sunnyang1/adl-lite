"""
Auto-generated PROV-O export for ADL Lite EventChains.

Maps:
  - Concept           → prov:Entity
  - Event             → prov:Activity + adl:{EventType}Event
  - Actor             → prov:Agent
  - Event hash        → adl:eventHash (literal)
  - Prev-event link   → prov:wasInformedBy
  - Timestamp         → prov:startedAtTime
  - Payload           → adl:payload (JSON literal)

Example usage:
    from adl_lite.prov_export import to_prov_o
    from adl_lite.models import EventChain
    turtle = to_prov_o(chain)
"""

from __future__ import annotations

import json
from typing import Any

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import PROV, RDF, RDFS, XSD

from .models import Event, EventChain, EventType

# Namespaces
ADL = Namespace("https://adl-lite.org/ns/")


def _event_uri(concept_id: str, event_index: int, event_type: EventType) -> URIRef:
    """Generate a stable URI for an event."""
    return ADL[f"evt-{concept_id}-{event_type.value}-{event_index:03d}"]


def _actor_uri(actor: str) -> URIRef:
    """Generate a URI for an actor."""
    safe = actor.replace(" ", "_").replace("/", "_")
    return ADL[f"actor-{safe}"]


def _concept_uri(concept_id: str) -> URIRef:
    """Generate a URI for a concept."""
    return ADL[concept_id]


def _payload_to_literal(payload: dict[str, Any]) -> Literal:
    """Serialize payload to a JSON literal."""
    return Literal(json.dumps(payload, sort_keys=True, default=str), datatype=XSD.string)


def to_prov_o(chain: EventChain) -> str:
    """
    Export an EventChain to W3C PROV-O Turtle serialization.

    Returns syntactically valid Turtle that can be loaded by rdflib
    or any standard RDF toolkit.
    """
    g = Graph()
    g.bind("prov", PROV)
    g.bind("adl", ADL)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)

    concept_id = chain.concept_id
    concept = _concept_uri(concept_id)

    # Concept entity
    g.add((concept, RDF.type, PROV.Entity))
    g.add((concept, RDFS.label, Literal(concept_id)))
    g.add((concept, ADL.conceptId, Literal(concept_id)))
    g.add((concept, ADL.status, Literal(chain.status.value)))
    g.add((concept, ADL.confidence, Literal(chain.confidence, datatype=XSD.float)))

    # Collect validator agents
    validators = chain.validators
    for validator in validators:
        actor = _actor_uri(validator)
        g.add((actor, RDF.type, PROV.Agent))
        g.add((actor, RDFS.label, Literal(validator)))

    # Events as Activities
    for idx, event in enumerate(chain.events):
        evt_uri = _event_uri(concept_id, idx, event.event_type)
        actor = _actor_uri(event.actor)

        # Event typing
        g.add((evt_uri, RDF.type, PROV.Activity))
        g.add((evt_uri, RDF.type, ADL[f"{event.event_type.value.capitalize()}Event"]))
        g.add((evt_uri, RDFS.label, Literal(f"{event.event_type.value} {concept_id}")))

        # PROV associations
        g.add((evt_uri, PROV.wasAssociatedWith, actor))
        if event.timestamp:
            g.add((evt_uri, PROV.startedAtTime, Literal(event.timestamp, datatype=XSD.dateTime)))

        # ADL-specific crypto metadata
        g.add((evt_uri, ADL.eventType, Literal(event.event_type.value)))
        g.add((evt_uri, ADL.eventIndex, Literal(idx, datatype=XSD.integer)))
        g.add((evt_uri, ADL.eventHash, Literal(event.hash)))
        g.add((evt_uri, ADL.eventId, Literal(event.event_id)))

        # Payload (if non-empty)
        if event.payload:
            g.add((evt_uri, ADL.payload, _payload_to_literal(event.payload)))

        # Causal linkage: prov:wasInformedBy previous event
        if idx > 0:
            prev_event = chain.events[idx - 1]
            prev_uri = _event_uri(concept_id, idx - 1, prev_event.event_type)
            g.add((evt_uri, PROV.wasInformedBy, prev_uri))
            g.add((evt_uri, ADL.previousEventHash, Literal(prev_event.hash)))
        else:
            g.add((evt_uri, ADL.previousEventHash, Literal("genesis")))

        # Concept wasGeneratedBy this event
        g.add((concept, PROV.wasGeneratedBy, evt_uri))

        # Ensure actor is typed
        if (actor, RDF.type, PROV.Agent) not in g:
            g.add((actor, RDF.type, PROV.Agent))
            g.add((actor, RDFS.label, Literal(event.actor)))

    return g.serialize(format="turtle")


def to_rdfstar(chain: EventChain) -> str:
    """
    Export an EventChain to RDF-star Turtle serialization.

    Maps L3 relation blocks to quoted triples with event-provenance annotations:
      << :source :relation :target >> prov:wasGeneratedBy :event ;
          adl:eventHash "sha256..." ;
          adl:confidence 0.91 .

    Returns syntactically valid Turtle-star (RDF 1.2) as a string.
    """
    from .parser import parse_text
    from .models import ADLRelationBlock

    # Build PROV-O base first
    prov_ttl = to_prov_o(chain)

    # We need the original document to extract relation blocks.
    # For now, annotate any relations found in the chain's payload
    # with the most recent VALIDATE event (or REGISTER if no VALIDATE).
    provenance_event = None
    for idx in range(len(chain.events) - 1, -1, -1):
        if chain.events[idx].event_type in (EventType.VALIDATE, EventType.REGISTER):
            provenance_event = _event_uri(chain.concept_id, idx, chain.events[idx].event_type)
            break

    lines = [prov_ttl.strip()]
    lines.append("")
    lines.append("# RDF-star quoted triples for L3 relation assertions")
    lines.append("")

    # Extract relations from event payloads (best-effort)
    seen_relations: set[str] = set()
    for idx, event in enumerate(chain.events):
        rels = event.payload.get("relations", [])
        if not isinstance(rels, list):
            continue
        for rel in rels:
            if not isinstance(rel, dict):
                continue
            source = rel.get("source", "")
            relation = rel.get("relation", "")
            target = rel.get("target", "")
            confidence = rel.get("confidence", 1.0)
            if not (source and relation and target):
                continue
            key = f"{source}|{relation}|{target}"
            if key in seen_relations:
                continue
            seen_relations.add(key)

            src_uri = _concept_uri(source.replace(" ", "_").lower())
            tgt_uri = (
                URIRef(target)
                if target.startswith("http")
                else _concept_uri(target.replace(" ", "_").lower())
            )
            rel_pred = ADL[relation.replace("-", "_")]

            lines.append(
                f"<< <{src_uri}> <{rel_pred}> <{tgt_uri}> >> " f"adl:confidence {confidence} ;"
            )
            if provenance_event:
                lines.append(f"    prov:wasGeneratedBy <{provenance_event}> ;")
            evt_hash = chain.events[idx].hash if idx < len(chain.events) else ""
            if evt_hash:
                lines.append(f'    adl:eventHash "{evt_hash}" ;')
            lines.append(f'    adl:relationPredicate "{relation}" .')
            lines.append("")

    return "\n".join(lines)


def validate_turtle(turtle_str: str) -> bool:
    """
    Parse Turtle string with rdflib to verify syntactic validity.

    Returns True if parse succeeds, False otherwise.
    """
    try:
        g = Graph()
        g.parse(data=turtle_str, format="turtle")
        return True
    except Exception:
        return False
