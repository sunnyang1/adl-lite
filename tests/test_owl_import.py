"""
Tests for OWL 2 DL bidirectional import (FW1).
"""

import pytest

from adl_lite.models import ADLDocument, ADLFrontMatter, ADLType, DiscoveryStatus, Event, EventChain, EventType
from adl_lite.owl_export import document_to_owl_turtle, document_to_owl_rdfxml
from adl_lite.owl_import import parse_owl_turtle, parse_owl_rdfxml


def _make_sample_doc() -> ADLDocument:
    """Build a sample ADLDocument with two events for round-trip testing."""
    chain = EventChain(concept_id="disc-test")
    chain.append(
        Event(
            concept_id="disc-test",
            event_type=EventType.VALIDATE,
            actor="agent_1",
            payload={"confidence": 0.85},
        )
    )
    chain.append(
        Event(
            concept_id="disc-test",
            event_type=EventType.VALIDATE,
            actor="agent_2",
            payload={"confidence": 0.75},
        )
    )
    fm = ADLFrontMatter(
        adl_type=ADLType.DISCOVERY,
        adl_id="disc-test",
        status=DiscoveryStatus.VALIDATED,
        confidence=0.85,
        validators=["agent_1", "agent_2"],
        domain="aml",
        scope="public",
    )
    return ADLDocument(front_matter=fm, markdown_body="", event_chain=chain)


# ---------------------------------------------------------------------------
# Turtle round-trip tests
# ---------------------------------------------------------------------------


def test_owl_turtle_roundtrip_concept_id():
    doc = _make_sample_doc()
    turtle = document_to_owl_turtle(doc)
    imported = parse_owl_turtle(turtle)
    assert imported.adl_id == "disc-test"


def test_owl_turtle_roundtrip_type():
    doc = _make_sample_doc()
    turtle = document_to_owl_turtle(doc)
    imported = parse_owl_turtle(turtle)
    assert imported.front_matter.adl_type == ADLType.DISCOVERY


def test_owl_turtle_roundtrip_status():
    doc = _make_sample_doc()
    turtle = document_to_owl_turtle(doc)
    imported = parse_owl_turtle(turtle)
    assert imported.front_matter.status == DiscoveryStatus.VALIDATED


def test_owl_turtle_roundtrip_confidence():
    doc = _make_sample_doc()
    turtle = document_to_owl_turtle(doc)
    imported = parse_owl_turtle(turtle)
    assert imported.front_matter.confidence == pytest.approx(0.85)


def test_owl_turtle_roundtrip_validators():
    doc = _make_sample_doc()
    turtle = document_to_owl_turtle(doc)
    imported = parse_owl_turtle(turtle)
    assert set(imported.front_matter.validators) == {"agent_1", "agent_2"}


def test_owl_turtle_roundtrip_events():
    doc = _make_sample_doc()
    turtle = document_to_owl_turtle(doc)
    imported = parse_owl_turtle(turtle)
    # ADLDocument.event_chain is synthetic: SNAPSHOT + VALIDATE from front_matter
    assert len(imported.event_chain.events) == 2
    actors = {e.actor for e in imported.event_chain.events}
    assert actors == {"parser", "agent_2"}


def test_owl_turtle_roundtrip_domain():
    doc = _make_sample_doc()
    turtle = document_to_owl_turtle(doc)
    imported = parse_owl_turtle(turtle)
    assert imported.front_matter.domain == "aml"


# ---------------------------------------------------------------------------
# RDF/XML round-trip tests
# ---------------------------------------------------------------------------


def test_owl_rdfxml_roundtrip_concept_id():
    doc = _make_sample_doc()
    rdfxml = document_to_owl_rdfxml(doc)
    imported = parse_owl_rdfxml(rdfxml)
    assert imported.adl_id == "disc-test"


def test_owl_rdfxml_roundtrip_status():
    doc = _make_sample_doc()
    rdfxml = document_to_owl_rdfxml(doc)
    imported = parse_owl_rdfxml(rdfxml)
    assert imported.front_matter.status == DiscoveryStatus.VALIDATED


def test_owl_rdfxml_roundtrip_events():
    doc = _make_sample_doc()
    rdfxml = document_to_owl_rdfxml(doc)
    imported = parse_owl_rdfxml(rdfxml)
    assert len(imported.event_chain.events) == 2
    actors = {e.actor for e in imported.event_chain.events}
    assert actors == {"parser", "agent_2"}


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_owl_turtle_parse_empty():
    with pytest.raises(ValueError, match="Could not find concept"):
        parse_owl_turtle("")


def test_owl_rdfxml_parse_empty():
    with pytest.raises(ValueError, match="Could not find concept"):
        parse_owl_rdfxml('<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"></rdf:RDF>')


# ---------------------------------------------------------------------------
# Bidirectional integrity: export → import → verify
# ---------------------------------------------------------------------------


def test_owl_turtle_roundtrip_chain_integrity():
    doc = _make_sample_doc()
    turtle = document_to_owl_turtle(doc)
    imported = parse_owl_turtle(turtle)
    assert imported.event_chain.verify_integrity()


def test_owl_rdfxml_roundtrip_chain_integrity():
    doc = _make_sample_doc()
    rdfxml = document_to_owl_rdfxml(doc)
    imported = parse_owl_rdfxml(rdfxml)
    assert imported.event_chain.verify_integrity()
