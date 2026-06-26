"""
Tests for RDF-star / SPARQL-star export (FW8).
"""

from adl_lite.models import (
    ADLDocument,
    ADLFrontMatter,
    ADLType,
    DiscoveryStatus,
    Event,
    EventType,
)
from adl_lite.rdfstar_export import (
    document_to_rdfstar_turtle,
    event_to_rdfstar_triple,
    sparqlstar_query_template,
)


def _make_sample_doc() -> ADLDocument:
    fm = ADLFrontMatter(
        adl_type=ADLType.DISCOVERY,
        adl_id="disc-test",
        status=DiscoveryStatus.VALIDATED,
        confidence=0.85,
        validators=["agent_1"],
        domain="aml",
        scope="public",
    )
    return ADLDocument(front_matter=fm, markdown_body="")


# ---------------------------------------------------------------------------
# RDF-star triple tests
# ---------------------------------------------------------------------------


def test_rdfstar_validate_event():
    event = Event(
        concept_id="disc-test",
        event_type=EventType.VALIDATE,
        actor="agent_1",
        payload={"confidence": 0.85},
    )
    triple = event_to_rdfstar_triple(event)
    assert "<<adl:disc-test adl:hasStatus adl:status/validated>>" in triple
    assert 'adl:hasActor "agent_1"' in triple
    assert "adl:hasConfidence 0.85" in triple


def test_rdfstar_register_event():
    event = Event(
        concept_id="disc-test",
        event_type=EventType.REGISTER,
        actor="agent_1",
        payload={},
    )
    triple = event_to_rdfstar_triple(event)
    assert "<<adl:disc-test rdf:type adl:discovery>>" in triple
    assert 'adl:hasActor "agent_1"' in triple


def test_rdfstar_deprecate_event():
    event = Event(
        concept_id="disc-test",
        event_type=EventType.DEPRECATE,
        actor="agent_1",
        payload={},
    )
    triple = event_to_rdfstar_triple(event)
    assert "<<adl:disc-test adl:hasStatus adl:status/deprecated>>" in triple


def test_rdfstar_archive_event():
    event = Event(
        concept_id="disc-test",
        event_type=EventType.ARCHIVE,
        actor="agent_1",
        payload={},
    )
    triple = event_to_rdfstar_triple(event)
    assert "<<adl:disc-test adl:hasStatus adl:status/archived>>" in triple


# ---------------------------------------------------------------------------
# Document export tests
# ---------------------------------------------------------------------------


def test_rdfstar_document_export_has_prefixes():
    doc = _make_sample_doc()
    turtle = document_to_rdfstar_turtle(doc)
    assert "@prefix adl:" in turtle
    assert "@prefix rdf:" in turtle
    assert "@prefix xsd:" in turtle


def test_rdfstar_document_export_has_concept():
    doc = _make_sample_doc()
    turtle = document_to_rdfstar_turtle(doc)
    assert "adl:disc-test a adl:discovery" in turtle


def test_rdfstar_document_export_has_event():
    doc = _make_sample_doc()
    turtle = document_to_rdfstar_turtle(doc)
    assert "<<adl:disc-test adl:hasStatus adl:status/validated>>" in turtle
    assert 'adl:hasActor "agent_1"' in turtle


def test_rdfstar_document_export_skips_snapshot():
    doc = _make_sample_doc()
    turtle = document_to_rdfstar_turtle(doc)
    # Synthetic SNAPSHOT events should not appear in RDF-star export
    assert "adl:hasEventType adl:eventType/snapshot" not in turtle


# ---------------------------------------------------------------------------
# SPARQL-star query tests
# ---------------------------------------------------------------------------


def test_sparqlstar_validate_query():
    query = sparqlstar_query_template("disc-test", event_type=EventType.VALIDATE)
    assert "SELECT ?actor ?confidence ?timestamp" in query
    assert "<<adl:disc-test adl:hasStatus adl:status/validated>>" in query


def test_sparqlstar_register_query():
    query = sparqlstar_query_template("disc-test", event_type=EventType.REGISTER)
    assert "<<adl:disc-test rdf:type adl:discovery>>" in query


def test_sparqlstar_generic_query():
    query = sparqlstar_query_template("disc-test")
    assert "<<adl:disc-test ?p ?o>>" in query
