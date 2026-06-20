#!/usr/bin/env python3
"""
CRDT Behavior Demo — v0.3.5 (LUB/G-Counter) vs v0.3.0 (LWW)

Run this script to see the concrete differences between the old
last-write-wins semantics and the new CRDT semantics.

Usage:
    python examples/crdt_behavior_demo.py
"""

from adl_lite import Event, EventChain, EventType


def demo_1_confidence_never_decreases():
    """G-Counter: max over all VALIDATE events."""
    print("=" * 60)
    print("Demo 1: Confidence never decreases (G-Counter)")
    print("=" * 60)

    chain = EventChain(concept_id="demo-confidence")
    chain.append(Event(concept_id="demo-confidence", event_type=EventType.REGISTER, actor="init"))

    chain.append(
        Event(
            concept_id="demo-confidence",
            event_type=EventType.VALIDATE,
            actor="validator_1",
            payload={"confidence": 0.9},
        )
    )
    print(f"  After VALIDATE(0.9) → confidence = {chain.confidence}")

    chain.append(
        Event(
            concept_id="demo-confidence",
            event_type=EventType.VALIDATE,
            actor="validator_2",
            payload={"confidence": 0.5},
        )
    )
    print(f"  After VALIDATE(0.5) → confidence = {chain.confidence}")
    print(f"  → Old LWW would give 0.5; CRDT gives 0.9 (max)")
    assert chain.confidence == 0.9


def demo_2_status_never_regresses():
    """LUB: once deprecated, always deprecated."""
    print("\n" + "=" * 60)
    print("Demo 2: Status never regresses (LUB)")
    print("=" * 60)

    chain = EventChain(concept_id="demo-status")
    chain.append(Event(concept_id="demo-status", event_type=EventType.REGISTER, actor="init"))

    chain.append(Event(concept_id="demo-status", event_type=EventType.VALIDATE, actor="reviewer"))
    print(f"  After VALIDATE      → status = {chain.status.value}")

    chain.append(Event(concept_id="demo-status", event_type=EventType.DEPRECATE, actor="admin"))
    print(f"  After DEPRECATE     → status = {chain.status.value}")

    chain.append(Event(concept_id="demo-status", event_type=EventType.VALIDATE, actor="new_reviewer"))
    print(f"  After VALIDATE again → status = {chain.status.value}")
    print(f"  → Old LWW would give 'validated'; CRDT gives 'deprecated'")
    assert chain.status.value == "deprecated"


def demo_3_archive_dominates_all():
    """ARCHIVE is the top of the lattice."""
    print("\n" + "=" * 60)
    print("Demo 3: ARCHIVE dominates everything")
    print("=" * 60)

    chain = EventChain(concept_id="demo-archive")
    chain.append(Event(concept_id="demo-archive", event_type=EventType.REGISTER, actor="init"))
    chain.append(Event(concept_id="demo-archive", event_type=EventType.VALIDATE, actor="a"))
    chain.append(Event(concept_id="demo-archive", event_type=EventType.ARCHIVE, actor="admin"))
    print(f"  After VALIDATE → ARCHIVE → status = {chain.status.value}")

    chain.append(Event(concept_id="demo-archive", event_type=EventType.VALIDATE, actor="b"))
    print(f"  After another VALIDATE → status = {chain.status.value}")
    print(f"  → Once archived, nothing can change it back")
    assert chain.status.value == "archived"


def demo_4_fork_parent_stays_validated():
    """FORK event does NOT downgrade the parent chain."""
    print("\n" + "=" * 60)
    print("Demo 4: Fork parent stays validated")
    print("=" * 60)

    chain = EventChain(concept_id="demo-fork")
    chain.append(Event(concept_id="demo-fork", event_type=EventType.REGISTER, actor="init"))
    chain.append(Event(concept_id="demo-fork", event_type=EventType.VALIDATE, actor="reviewer"))
    print(f"  Parent after VALIDATE → status = {chain.status.value}")

    chain.append(
        Event(
            concept_id="demo-fork",
            event_type=EventType.FORK,
            actor="discoverer",
            payload={"fork_of": "demo-fork", "new_concept_id": "demo-fork-v2"},
        )
    )
    print(f"  Parent after FORK     → status = {chain.status.value}")
    print(f"  → Parent stays 'validated'; fork gets its own chain")
    assert chain.status.value == "validated"


def demo_5_snapshot_counts_in_max():
    """SNAPSHOT confidence is also considered in the G-Counter max."""
    print("\n" + "=" * 60)
    print("Demo 5: SNAPSHOT confidence counts in max")
    print("=" * 60)

    chain = EventChain(concept_id="demo-snapshot")
    chain.append(Event(concept_id="demo-snapshot", event_type=EventType.REGISTER, actor="init"))

    chain.append(
        Event(
            concept_id="demo-snapshot",
            event_type=EventType.VALIDATE,
            actor="a",
            payload={"confidence": 0.7},
        )
    )
    print(f"  After VALIDATE(0.7)  → confidence = {chain.confidence}")

    chain.append(
        Event(
            concept_id="demo-snapshot",
            event_type=EventType.SNAPSHOT,
            actor="system",
            payload={"confidence": 0.85},
        )
    )
    print(f"  After SNAPSHOT(0.85) → confidence = {chain.confidence}")

    chain.append(
        Event(
            concept_id="demo-snapshot",
            event_type=EventType.VALIDATE,
            actor="b",
            payload={"confidence": 0.6},
        )
    )
    print(f"  After VALIDATE(0.6)  → confidence = {chain.confidence}")
    print(f"  → max(0.7, 0.85, 0.6) = 0.85")
    assert chain.confidence == 0.85


def demo_6_merge_two_chains():
    """Merging two chains takes the LUB of both."""
    print("\n" + "=" * 60)
    print("Demo 6: Merge two chains (LUB + G-Counter)")
    print("=" * 60)

    from adl_lite import merge_event_chains

    chain_a = EventChain(concept_id="merge-demo")
    chain_a.append(Event(concept_id="merge-demo", event_type=EventType.REGISTER, actor="init"))
    chain_a.append(
        Event(
            concept_id="merge-demo",
            event_type=EventType.VALIDATE,
            actor="a",
            payload={"confidence": 0.85},
        )
    )

    chain_b = EventChain(concept_id="merge-demo")
    chain_b.append(Event(concept_id="merge-demo", event_type=EventType.REGISTER, actor="init"))
    chain_b.append(
        Event(
            concept_id="merge-demo",
            event_type=EventType.VALIDATE,
            actor="b",
            payload={"confidence": 0.75},
        )
    )
    chain_b.append(Event(concept_id="merge-demo", event_type=EventType.DEPRECATE, actor="admin"))

    merged = merge_event_chains(chain_a, chain_b)
    print(f"  Chain A: validated, confidence 0.85")
    print(f"  Chain B: deprecated, confidence 0.75")
    print(f"  Merged  : {merged.status.value}, confidence {merged.confidence}")
    print(f"  → LUB(VALIDATED, DEPRECATED) = DEPRECATED")
    print(f"  → max(0.85, 0.75) = 0.85")
    assert merged.status.value == "deprecated"
    assert merged.confidence == 0.85


if __name__ == "__main__":
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " ADL Lite CRDT Behavior Demo ".center(58) + "║")
    print("║" + " v0.3.5 — LUB/G-Counter semantics ".center(58) + "║")
    print("╚" + "═" * 58 + "╝")

    demo_1_confidence_never_decreases()
    demo_2_status_never_regresses()
    demo_3_archive_dominates_all()
    demo_4_fork_parent_stays_validated()
    demo_5_snapshot_counts_in_max()
    demo_6_merge_two_chains()

    print("\n" + "=" * 60)
    print("All demos passed! ✓")
    print("=" * 60 + "\n")
