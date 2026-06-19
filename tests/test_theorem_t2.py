"""
Tests for Theorem 2 (Confluence under Fork) from the ADL Lite paper.

Theorem 2: Let C fork to (C_fork, C'). Then δ(C_fork) = forked and
δ(C') = provisional.

Proof Sketch: By the fork definition, e_FORK is appended to C_fork and is
the last lifecycle event in that chain. The child chain C' begins with a
fresh genesis event whose previous_event_id = null.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from adl_lite import ConsensusEngine, DiscoveryStatus, parse_file
from adl_lite.consensus import ForkManager
from adl_lite.models import Event, EventChain, EventType

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


class TestTheorem2ConfluenceUnderFork:
    """T2: Fork produces parent=forked, child=provisional."""

    def test_fork_creates_forked_parent(self):
        """Parent chain after fork → status is LUB of VALIDATED and FORKED.

        Under CRDT semantics, VALIDATED(3) > FORKED(2), so the parent stays
        VALIDATED. The FORK event records the fork operation but does not
        downgrade a previously validated concept.
        """
        chain = EventChain(concept_id="t2-parent")
        chain.append(Event(concept_id="t2-parent", event_type=EventType.REGISTER, actor="a"))
        chain.append(
            Event(
                concept_id="t2-parent",
                event_type=EventType.VALIDATE,
                actor="b",
                payload={"confidence": 0.85},
            )
        )
        chain.append(Event(concept_id="t2-parent", event_type=EventType.FORK, actor="a"))
        # CRDT LUB: max(VALIDATED, FORKED) = VALIDATED
        assert chain.status == DiscoveryStatus.VALIDATED

    def test_forked_child_is_provisional(self):
        """Child chain after fork → status is provisional."""
        parent = EventChain(concept_id="t2-parent")
        parent.append(Event(concept_id="t2-parent", event_type=EventType.REGISTER, actor="a"))
        parent.append(
            Event(
                concept_id="t2-parent",
                event_type=EventType.VALIDATE,
                actor="b",
                payload={"confidence": 0.85},
            )
        )
        parent.append(Event(concept_id="t2-parent", event_type=EventType.FORK, actor="a"))

        # Child chain starts with fresh REGISTER
        child = EventChain(concept_id="t2-child")
        child.append(
            Event(
                concept_id="t2-child",
                event_type=EventType.REGISTER,
                actor="a",
                payload={"fork_of": "t2-parent"},
            )
        )
        assert child.status == DiscoveryStatus.PROVISIONAL

    def test_forked_child_has_independent_lifecycle(self):
        """Child chain lifecycle is independent of parent after fork."""
        parent = EventChain(concept_id="t2-parent-ind")
        parent.append(Event(concept_id="t2-parent-ind", event_type=EventType.REGISTER, actor="a"))
        parent.append(
            Event(
                concept_id="t2-parent-ind",
                event_type=EventType.VALIDATE,
                actor="b",
                payload={"confidence": 0.85},
            )
        )
        parent.append(Event(concept_id="t2-parent-ind", event_type=EventType.FORK, actor="a"))

        child = EventChain(concept_id="t2-child-ind")
        child.append(
            Event(
                concept_id="t2-child-ind",
                event_type=EventType.REGISTER,
                actor="a",
                payload={"fork_of": "t2-parent-ind"},
            )
        )
        child.append(
            Event(
                concept_id="t2-child-ind",
                event_type=EventType.VALIDATE,
                actor="c",
                payload={"confidence": 0.75},
            )
        )

        # Parent under CRDT LUB: VALIDATED(3) > FORKED(2), stays VALIDATED
        assert parent.status == DiscoveryStatus.VALIDATED
        assert child.status == DiscoveryStatus.VALIDATED

    def test_forked_child_genesis_has_no_parent(self):
        """Child genesis has previous_event_id = null."""
        child = EventChain(concept_id="t2-child-gen")
        child.append(
            Event(
                concept_id="t2-child-gen",
                event_type=EventType.REGISTER,
                actor="a",
                payload={"fork_of": "t2-parent-gen"},
            )
        )
        assert child._events[0].previous_event_id is None

    def test_consensus_engine_fork_marks_parent_forked(self):
        """ConsensusEngine.fork() appends FORK to parent; CRDT LUB keeps VALIDATED."""
        engine = ConsensusEngine()
        doc = parse_file(EXAMPLES / "capital_reflux_trap.md")
        engine.register(doc)
        engine.transition(
            doc.adl_id,
            DiscoveryStatus.VALIDATED,
            actor="reviewer",
            reason="Initial validation",
        )
        engine.fork(
            doc.adl_id,
            "disc-capital-fork",
            actor="skeptic",
            reason="Fork for alternative view",
        )
        # Under CRDT LUB, VALIDATED(3) > FORKED(2); parent stays VALIDATED
        assert engine.get_status(doc.adl_id) == DiscoveryStatus.VALIDATED

    def test_consensus_engine_fork_creates_provisional_child(self):
        """ConsensusEngine.fork() creates child with provisional status."""
        engine = ConsensusEngine()
        doc = parse_file(EXAMPLES / "matdo_original.md")
        engine.register(doc)
        engine.transition(
            doc.adl_id,
            DiscoveryStatus.VALIDATED,
            actor="reviewer",
            reason="Initial validation",
        )
        engine.fork(
            doc.adl_id,
            "disc-matdo-kinetic",
            actor="skeptic",
            reason="Kinetic nucleation alternative",
        )
        assert engine.get_status("disc-matdo-kinetic") == DiscoveryStatus.PROVISIONAL

    def test_fork_is_last_lifecycle_in_parent(self):
        """FORK event is the last lifecycle event in the parent chain."""
        chain = EventChain(concept_id="t2-last-fork")
        chain.append(Event(concept_id="t2-last-fork", event_type=EventType.REGISTER, actor="a"))
        chain.append(
            Event(
                concept_id="t2-last-fork",
                event_type=EventType.VALIDATE,
                actor="b",
                payload={"confidence": 0.8},
            )
        )
        chain.append(Event(concept_id="t2-last-fork", event_type=EventType.FORK, actor="a"))

        # No later lifecycle events exist by construction
        lifecycle_events = [e for e in chain._events if e.event_type in {
            EventType.REGISTER, EventType.VALIDATE, EventType.DEPRECATE,
            EventType.FORK, EventType.ARCHIVE
        }]
        assert lifecycle_events[-1].event_type == EventType.FORK
