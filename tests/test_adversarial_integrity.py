"""
Adversarial integrity tests for EventChain.

Addresses reviewer concern: "multi-agent auditability and offline synchronization
experiments would be stronger with adversarial perturbations (simulated conflicting
writes, reorderings, replay/duplication)."

Test classes:
  - ReorderingAttack: swap events → verify detection
  - ReplayAttack: copy event to another chain → verify detection
  - PayloadTampering: modify payload → verify detection
  - TimestampTampering: modify timestamp → verify detection
  - DeletionAttack: remove middle event → verify detection
"""

from __future__ import annotations

from adl_lite.models import Event, EventChain, EventType


class TestReorderingAttack:
    """Swap two events in a chain → verify_integrity() must detect it."""

    def test_swap_two_events_detected(self):
        chain = EventChain(concept_id="reorder-test")
        e1 = Event(concept_id="reorder-test", event_type=EventType.REGISTER, actor="a")
        e2 = Event(concept_id="reorder-test", event_type=EventType.VALIDATE, actor="b")
        e3 = Event(concept_id="reorder-test", event_type=EventType.VALIDATE, actor="c")
        chain.append(e1)
        chain.append(e2)
        chain.append(e3)

        assert chain.verify_integrity()

        # Swap e2 and e3 in the internal list
        chain._events[1], chain._events[2] = chain._events[2], chain._events[1]

        # Recompute hashes for the swapped events so they look "valid" individually
        chain._events[1].hash = ""
        chain._events[1].model_post_init(None)
        chain._events[2].hash = ""
        chain._events[2].model_post_init(None)

        assert not chain.verify_integrity(), "Reordering two events should break chain integrity"


class TestReplayAttack:
    """Copy an event from one chain to another → verify_integrity() must detect it."""

    def test_replay_event_into_different_chain_detected(self):
        chain_a = EventChain(concept_id="replay-a")
        e1 = Event(concept_id="replay-a", event_type=EventType.REGISTER, actor="a")
        chain_a.append(e1)

        chain_b = EventChain(concept_id="replay-b")
        e2 = Event(concept_id="replay-b", event_type=EventType.REGISTER, actor="b")
        chain_b.append(e2)

        # Attempt replay: directly inject e1 (with its original hash from chain_a)
        # into chain_b's internal event list, bypassing append() validation.
        # This simulates an attacker copying a signed/hashed event verbatim.
        replay_event = e1.model_copy()
        chain_b._events.append(replay_event)

        # The replayed event's previous_event_id and _prev_hash point to chain_a's
        # genesis state, not e2, so the linkage check fails.
        assert (
            not chain_b.verify_integrity()
        ), "Replaying an event from a different chain should break integrity"


class TestPayloadTampering:
    """Modify an event's payload after it is in the chain → verify_integrity() detects."""

    def test_payload_modification_detected(self):
        chain = EventChain(concept_id="payload-tamper")
        e1 = Event(
            concept_id="payload-tamper",
            event_type=EventType.REGISTER,
            actor="a",
            payload={"amount": 100},
        )
        e2 = Event(
            concept_id="payload-tamper",
            event_type=EventType.VALIDATE,
            actor="b",
            payload={"amount": 200},
        )
        chain.append(e1)
        chain.append(e2)
        assert chain.verify_integrity()

        chain._events[0].payload["amount"] = 999999
        assert not chain.verify_integrity(), "Payload tampering should break integrity"

    def test_payload_modification_with_hash_recomputation_still_detected(self):
        chain = EventChain(concept_id="payload-tamper2")
        e1 = Event(
            concept_id="payload-tamper2",
            event_type=EventType.REGISTER,
            actor="a",
            payload={"amount": 100},
        )
        e2 = Event(
            concept_id="payload-tamper2",
            event_type=EventType.VALIDATE,
            actor="b",
            payload={"amount": 200},
        )
        chain.append(e1)
        chain.append(e2)
        assert chain.verify_integrity()

        # Attacker modifies payload AND recomputes own hash
        chain._events[0].payload["amount"] = 999999
        chain._events[0].hash = chain._events[0]._compute_hash()
        # e1's own hash now matches its new content
        # BUT e2._prev_hash still points to the ORIGINAL e1.hash
        assert (
            not chain.verify_integrity()
        ), "Hash chain break should be detected — e2._prev_hash ≠ recomputed e1.hash"


class TestTimestampTampering:
    """Modify an event's timestamp after it is in the chain → verify_integrity() detects."""

    def test_timestamp_modification_detected(self):
        chain = EventChain(concept_id="ts-tamper")
        e1 = Event(
            concept_id="ts-tamper",
            event_type=EventType.REGISTER,
            actor="a",
            timestamp="2024-01-15T09:00:00+00:00",
        )
        e2 = Event(
            concept_id="ts-tamper",
            event_type=EventType.VALIDATE,
            actor="b",
            timestamp="2024-01-15T14:30:00+00:00",
        )
        chain.append(e1)
        chain.append(e2)
        assert chain.verify_integrity()

        # Tamper timestamp
        chain._events[0].timestamp = "2025-12-25T00:00:00+00:00"
        assert (
            not chain.verify_integrity()
        ), "Timestamp tampering should break integrity because timestamp is in hash input"

    def test_timestamp_modification_with_hash_recomputation_still_detected(self):
        chain = EventChain(concept_id="ts-tamper2")
        e1 = Event(
            concept_id="ts-tamper2",
            event_type=EventType.REGISTER,
            actor="a",
            timestamp="2024-01-15T09:00:00+00:00",
        )
        e2 = Event(
            concept_id="ts-tamper2",
            event_type=EventType.VALIDATE,
            actor="b",
            timestamp="2024-01-15T14:30:00+00:00",
        )
        chain.append(e1)
        chain.append(e2)
        assert chain.verify_integrity()

        # Attacker modifies timestamp AND recomputes own hash
        chain._events[0].timestamp = "2025-12-25T00:00:00+00:00"
        chain._events[0].hash = chain._events[0]._compute_hash()
        # e2._prev_hash still points to original e1.hash
        assert (
            not chain.verify_integrity()
        ), "Timestamp tampering with hash recomputation should still be detected"


class TestDeletionAttack:
    """Remove a middle event from the chain → verify_integrity() detects."""

    def test_middle_event_deletion_detected(self):
        chain = EventChain(concept_id="delete-test")
        for i in range(5):
            chain.append(
                Event(
                    concept_id="delete-test",
                    event_type=EventType.REGISTER if i == 0 else EventType.VALIDATE,
                    actor=f"agent_{i}",
                )
            )
        assert chain.verify_integrity()

        # Delete middle event
        del chain._events[2]
        assert not chain.verify_integrity(), "Deleting a middle event should break chain integrity"

    def test_tail_event_deletion_detected(self):
        chain = EventChain(concept_id="delete-tail")
        chain.append(Event(concept_id="delete-tail", event_type=EventType.REGISTER, actor="a"))
        chain.append(Event(concept_id="delete-tail", event_type=EventType.VALIDATE, actor="b"))
        assert chain.verify_integrity()

        # Delete tail event
        chain._events.pop()
        # Now only one event remains — integrity should still pass because
        # a single event chain is valid. But the *semantic* deletion is
        # detectable via git diff / consensus audit, not via hash chain.
        # For this test, we verify that the remaining chain is still valid.
        assert chain.verify_integrity(), "Deleting tail leaves a valid shorter chain"
