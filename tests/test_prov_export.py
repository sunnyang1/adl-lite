"""
Tests for adl_lite.prov_export — PROV-O auto-generation from EventChain.
"""

from __future__ import annotations

from rdflib import PROV, RDF, Graph

from adl_lite.models import Event, EventChain, EventType
from adl_lite.prov_export import ADL, to_prov_o, validate_turtle


class TestProvExport:
    """Validate PROV-O export preserves chain structure and passes syntax checks."""

    def test_empty_chain_produces_valid_turtle(self):
        chain = EventChain(concept_id="test-empty")
        ttl = to_prov_o(chain)
        assert validate_turtle(ttl)
        assert "prov:Entity" in ttl
        assert "test-empty" in ttl

    def test_single_event_has_activity_and_agent(self):
        chain = EventChain(concept_id="test-single")
        chain.append(
            Event(
                concept_id="test-single",
                event_type=EventType.REGISTER,
                actor="discoverer",
                timestamp="2024-01-15T09:00:00+00:00",
            )
        )
        ttl = to_prov_o(chain)
        assert validate_turtle(ttl)

        g = Graph()
        g.parse(data=ttl, format="turtle")

        # Concept is an Entity
        concept = ADL["test-single"]
        assert (concept, RDF.type, PROV.Entity) in g

        # Event is an Activity
        evt = ADL["evt-test-single-register-000"]
        assert (evt, RDF.type, PROV.Activity) in g
        assert (evt, RDF.type, ADL.RegisterEvent) in g

        # Actor is an Agent
        actor = ADL["actor-discoverer"]
        assert (actor, RDF.type, PROV.Agent) in g

        # Event wasAssociatedWith actor
        assert (evt, PROV.wasAssociatedWith, actor) in g

        # Event has timestamp
        assert any(
            str(o).startswith("2024-01-15")
            for _, _, o in g.triples((evt, PROV.startedAtTime, None))
        )

    def test_chain_linkage_via_was_informed_by(self):
        chain = EventChain(concept_id="test-link")
        chain.append(Event(concept_id="test-link", event_type=EventType.REGISTER, actor="a"))
        chain.append(Event(concept_id="test-link", event_type=EventType.VALIDATE, actor="b"))
        ttl = to_prov_o(chain)
        assert validate_turtle(ttl)

        g = Graph()
        g.parse(data=ttl, format="turtle")

        evt0 = ADL["evt-test-link-register-000"]
        evt1 = ADL["evt-test-link-validate-001"]

        # Causal link
        assert (evt1, PROV.wasInformedBy, evt0) in g

        # Genesis marker on first event
        assert any(
            str(o) == "genesis" for _, _, o in g.triples((evt0, ADL.previousEventHash, None))
        )

        # Non-genesis on second event
        assert any(
            str(o) != "genesis" for _, _, o in g.triples((evt1, ADL.previousEventHash, None))
        )

    def test_payload_serialization(self):
        chain = EventChain(concept_id="test-payload")
        chain.append(
            Event(
                concept_id="test-payload",
                event_type=EventType.VALIDATE,
                actor="reviewer",
                payload={"confidence": 0.85, "flags": ["ok"]},
            )
        )
        ttl = to_prov_o(chain)
        assert validate_turtle(ttl)
        assert '"confidence"' in ttl or "confidence" in ttl

    def test_concept_generated_by_all_events(self):
        chain = EventChain(concept_id="test-gen")
        for i in range(3):
            chain.append(
                Event(
                    concept_id="test-gen",
                    event_type=EventType.REGISTER if i == 0 else EventType.VALIDATE,
                    actor=f"agent_{i}",
                )
            )
        ttl = to_prov_o(chain)
        g = Graph()
        g.parse(data=ttl, format="turtle")

        concept = ADL["test-gen"]
        generated_by = list(g.objects(concept, PROV.wasGeneratedBy))
        assert len(generated_by) == 3

    def test_all_event_types_typed(self):
        chain = EventChain(concept_id="test-types")
        for et in [EventType.REGISTER, EventType.VALIDATE, EventType.FORK]:
            chain.append(Event(concept_id="test-types", event_type=et, actor="system"))
        ttl = to_prov_o(chain)
        g = Graph()
        g.parse(data=ttl, format="turtle")

        for idx, et in enumerate([EventType.REGISTER, EventType.VALIDATE, EventType.FORK]):
            evt = ADL[f"evt-test-types-{et.value}-{idx:03d}"]
            assert (evt, RDF.type, ADL[f"{et.value.capitalize()}Event"]) in g
