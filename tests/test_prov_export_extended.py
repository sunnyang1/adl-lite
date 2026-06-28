"""Extended tests for prov_export module — behaviors 22-28."""

from __future__ import annotations

from rdflib import PROV, RDF, Graph, Literal

from adl_lite.models import Event, EventChain, EventType
from adl_lite.prov_export import ADL, to_prov_o, to_rdfstar, validate_turtle


def _make_chain_with_events(
    concept_id: str = "test-concept",
    events: list[Event] | None = None,
) -> EventChain:
    """Helper: build a chain with events."""
    chain = EventChain(concept_id=concept_id)
    if events:
        for e in events:
            chain.append(e)
    return chain


def _make_register_event(
    concept_id: str = "test-concept",
    actor: str = "discoverer",
    timestamp: str = "2024-01-15T09:00:00+00:00",
    payload: dict | None = None,
) -> Event:
    return Event(
        concept_id=concept_id,
        event_type=EventType.REGISTER,
        actor=actor,
        timestamp=timestamp,
        payload=payload or {},
    )


def _make_validate_event(
    concept_id: str = "test-concept",
    actor: str = "validator-1",
    timestamp: str = "2024-01-16T10:00:00+00:00",
    payload: dict | None = None,
) -> Event:
    return Event(
        concept_id=concept_id,
        event_type=EventType.VALIDATE,
        actor=actor,
        timestamp=timestamp,
        payload=payload or {"confidence": 0.91},
    )


# ---------------------------------------------------------------------------
# Behavior 22: to_prov_o generates valid Turtle (parseable by rdflib)
# ---------------------------------------------------------------------------


class TestToProvOValidTurtle:
    """to_prov_o produces Turtle that rdflib can parse."""

    def test_valid_turtle_single_event(self):
        """Chain with one event produces parseable Turtle."""
        chain = _make_chain_with_events(
            concept_id="test-concept",
            events=[_make_register_event()],
        )
        ttl = to_prov_o(chain)
        assert validate_turtle(ttl)

        # Can parse with rdflib
        g = Graph()
        g.parse(data=ttl, format="turtle")
        assert len(g) > 0

    def test_valid_turtle_multiple_events(self):
        """Chain with multiple events produces parseable Turtle."""
        chain = _make_chain_with_events(
            concept_id="test-concept",
            events=[
                _make_register_event(),
                _make_validate_event(),
            ],
        )
        ttl = to_prov_o(chain)
        assert validate_turtle(ttl)

    def test_valid_turtle_empty_chain(self):
        """Empty chain produces parseable Turtle."""
        chain = EventChain(concept_id="empty-concept")
        ttl = to_prov_o(chain)
        assert validate_turtle(ttl)


# ---------------------------------------------------------------------------
# Behavior 23: to_prov_o includes concept as prov:Entity with ADL namespace attrs
# ---------------------------------------------------------------------------


class TestToProvOConceptEntity:
    """Concept is exported as prov:Entity with ADL-specific attributes."""

    def test_concept_is_entity(self):
        """Concept URI is typed as prov:Entity."""
        chain = _make_chain_with_events(
            concept_id="my-concept",
            events=[_make_register_event(concept_id="my-concept")],
        )
        ttl = to_prov_o(chain)
        g = Graph()
        g.parse(data=ttl, format="turtle")
        concept = ADL["my-concept"]
        assert (concept, RDF.type, PROV.Entity) in g

    def test_concept_has_adl_namespace_attrs(self):
        """Concept has adl:conceptId and adl:status attributes."""
        chain = _make_chain_with_events(
            concept_id="my-concept",
            events=[_make_register_event(concept_id="my-concept")],
        )
        ttl = to_prov_o(chain)
        g = Graph()
        g.parse(data=ttl, format="turtle")
        concept = ADL["my-concept"]
        # adl:conceptId
        assert (concept, ADL.conceptId, Literal("my-concept")) in g
        # adl:status
        status_vals = list(g.objects(concept, ADL.status))
        assert len(status_vals) > 0


# ---------------------------------------------------------------------------
# Behavior 24: to_prov_o includes events as prov:Activity with wasInformedBy links
# ---------------------------------------------------------------------------


class TestToProvOEventActivities:
    """Events are exported as prov:Activity with wasInformedBy links."""

    def test_event_is_activity(self):
        """Event URI is typed as prov:Activity."""
        chain = _make_chain_with_events(
            concept_id="test-evt",
            events=[_make_register_event(concept_id="test-evt")],
        )
        ttl = to_prov_o(chain)
        g = Graph()
        g.parse(data=ttl, format="turtle")
        evt = ADL["evt-test-evt-register-000"]
        assert (evt, RDF.type, PROV.Activity) in g

    def test_was_informed_by_links(self):
        """Second event has wasInformedBy link to first event."""
        chain = _make_chain_with_events(
            concept_id="test-evt",
            events=[
                _make_register_event(concept_id="test-evt"),
                _make_validate_event(concept_id="test-evt"),
            ],
        )
        ttl = to_prov_o(chain)
        g = Graph()
        g.parse(data=ttl, format="turtle")
        evt1 = ADL["evt-test-evt-register-000"]
        evt2 = ADL["evt-test-evt-validate-001"]
        assert (evt2, PROV.wasInformedBy, evt1) in g


# ---------------------------------------------------------------------------
# Behavior 25: to_prov_o generates genesis event with previousEventHash="genesis"
# ---------------------------------------------------------------------------


class TestToProvOGenesisEvent:
    """First event has adl:previousEventHash = "genesis"."""

    def test_genesis_previous_event_hash(self):
        """First (genesis) event should have previousEventHash="genesis"."""
        chain = _make_chain_with_events(
            concept_id="genesis-test",
            events=[_make_register_event(concept_id="genesis-test")],
        )
        ttl = to_prov_o(chain)
        g = Graph()
        g.parse(data=ttl, format="turtle")
        evt = ADL["evt-genesis-test-register-000"]
        # The genesis event should have adl:previousEventHash "genesis"
        hash_vals = list(g.objects(evt, ADL.previousEventHash))
        assert len(hash_vals) > 0
        assert any(str(v) == "genesis" for v in hash_vals)


# ---------------------------------------------------------------------------
# Behavior 26: validate_turtle returns True for valid Turtle, False for invalid
# ---------------------------------------------------------------------------


class TestValidateTurtle:
    """validate_turtle correctly validates Turtle strings."""

    def test_valid_turtle_returns_true(self):
        """Valid Turtle string returns True."""
        valid_ttl = """
        @prefix ex: <http://example.org/> .
        ex:thing ex:name "hello" .
        """
        assert validate_turtle(valid_ttl) is True

    def test_invalid_turtle_returns_false(self):
        """Invalid Turtle string returns False."""
        invalid_ttl = "this is not turtle at all {{{"
        assert validate_turtle(invalid_ttl) is False

    def test_empty_string_is_valid(self):
        """Empty string is technically valid Turtle (empty graph)."""
        assert validate_turtle("") is True

    def test_prov_export_output_is_valid(self):
        """Output from to_prov_o passes validation."""
        chain = _make_chain_with_events(
            concept_id="validation-test",
            events=[_make_register_event(concept_id="validation-test")],
        )
        ttl = to_prov_o(chain)
        assert validate_turtle(ttl) is True


# ---------------------------------------------------------------------------
# Behavior 27: to_rdfstar generates RDF-star Turtle with quoted triples
# ---------------------------------------------------------------------------


class TestToRdfstarQuotedTriples:
    """to_rdfstar produces RDF-star Turtle with quoted triples for relations."""

    def test_rdfstar_with_relations(self):
        """Chain with relations in payload produces quoted triples."""
        chain = _make_chain_with_events(
            concept_id="rdfstar-test",
            events=[
                _make_register_event(
                    concept_id="rdfstar-test",
                    payload={
                        "relations": [
                            {
                                "source": "concept-a",
                                "relation": "isomorphic-to",
                                "target": "concept-b",
                                "confidence": 0.9,
                            }
                        ],
                    },
                ),
            ],
        )
        ttl = to_rdfstar(chain)
        # Should contain << quoted triple syntax
        assert "<< " in ttl or "<<<" in ttl
        # Should mention the relation predicate
        assert "isomorphic_to" in ttl or "isomorphic-to" in ttl

    def test_rdfstar_output_starts_with_valid_prov(self):
        """to_rdfstar output starts with valid PROV-O (base export)."""
        chain = _make_chain_with_events(
            concept_id="rdfstar-prov-test",
            events=[_make_register_event(concept_id="rdfstar-prov-test")],
        )
        ttl = to_rdfstar(chain)
        # The first part should be the PROV-O base
        assert "prov:Entity" in ttl


# ---------------------------------------------------------------------------
# Behavior 28: to_rdfstar generates chain without relations — only base PROV-O
# ---------------------------------------------------------------------------


class TestToRdfstarNoRelations:
    """Chain without relations produces only base PROV-O in RDF-star export."""

    def test_no_relations_only_base_prov(self):
        """Chain without relation payloads produces base PROV-O without quoted triples."""
        chain = _make_chain_with_events(
            concept_id="no-relations-test",
            events=[_make_register_event(concept_id="no-relations-test")],
        )
        ttl = to_rdfstar(chain)
        # Should have PROV-O base content
        assert "prov:Entity" in ttl
        assert "prov:Activity" in ttl
        # Should NOT contain quoted triples for relations
        # The "quoted triples" section header exists but no actual << triples
        # if no relations are found
        lines = ttl.split("\n")
        quoted_triple_lines = [line for line in lines if line.strip().startswith("<<")]
        assert len(quoted_triple_lines) == 0
