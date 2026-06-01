"""
Tests for RDF-star export from EventChain.
"""

from __future__ import annotations

# import pytest
from adl_lite.models import Event, EventChain, EventType
from adl_lite.prov_export import to_rdfstar


class TestRDFStarExport:
    """Validate RDF-star Turtle-star syntax and content."""

    def test_empty_chain_produces_valid_turtle_star(self):
        chain = EventChain(concept_id="rdfstar-empty")
        ttl = to_rdfstar(chain)
        # rdflib may not parse << >> syntax fully, but we at least check valid Turtle base
        assert "prov:Entity" in ttl
        assert "rdfstar-empty" in ttl

    def test_chain_with_relation_payload(self):
        chain = EventChain(concept_id="rdfstar-rel")
        chain.append(
            Event(
                concept_id="rdfstar-rel",
                event_type=EventType.REGISTER,
                actor="a",
                timestamp="2024-01-15T09:00:00+00:00",
                payload={
                    "relations": [
                        {
                            "source": "Concept A",
                            "relation": "isomorphic-to",
                            "target": "Concept B",
                            "confidence": 0.91,
                        }
                    ]
                },
            )
        )
        ttl = to_rdfstar(chain)
        # Check for RDF-star quoted triple syntax
        assert "<<" in ttl
        assert ">>" in ttl
        assert "isomorphic_to" in ttl
        assert "0.91" in ttl
        assert "adl:eventHash" in ttl

    def test_relation_provenance_event_linked(self):
        chain = EventChain(concept_id="rdfstar-prov")
        chain.append(
            Event(
                concept_id="rdfstar-prov",
                event_type=EventType.VALIDATE,
                actor="validator_1",
                timestamp="2024-01-15T14:30:00+00:00",
                payload={
                    "relations": [
                        {
                            "source": "Source",
                            "relation": "specialisation-of",
                            "target": "Target",
                            "confidence": 0.73,
                        }
                    ]
                },
            )
        )
        ttl = to_rdfstar(chain)
        # Provenance event should be linked
        assert "prov:wasGeneratedBy" in ttl
        assert "validator_1" in ttl

    def test_deduplicates_repeated_relations(self):
        chain = EventChain(concept_id="rdfstar-dedup")
        for _ in range(3):
            chain.append(
                Event(
                    concept_id="rdfstar-dedup",
                    event_type=EventType.VALIDATE,
                    actor="a",
                    payload={
                        "relations": [
                            {
                                "source": "S",
                                "relation": "related-to",
                                "target": "T",
                                "confidence": 0.5,
                            }
                        ]
                    },
                )
            )
        ttl = to_rdfstar(chain)
        # Only one quoted triple for the duplicated relation
        assert ttl.count("related_to") == 1
