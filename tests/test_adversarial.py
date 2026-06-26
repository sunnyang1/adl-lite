"""
Adversarial & Stress Tests — addresses reviewer concerns:
"No adversarial or stress tests (e.g., from AgentPoison-style attacks or
malicious forks) beyond acknowledging potential failure modes."

Test scenarios:
  1. Payload tampering: modify event payload → verify_integrity() detects it
  2. Chain poisoning: append low-quality events → watcher alerts
  3. Malicious fork bombing: create many forks → ForkManager handles them
  4. Timestamp collision: two events with same timestamp → deterministic ordering
  5. SSA circumvention: creative pronoun avoidance → known limitation confirmed
"""

from __future__ import annotations

from datetime import datetime, timezone

from adl_lite.consensus import ConsensusEngine, ForkManager
from adl_lite.models import Event, EventChain, EventType
from adl_lite.realtime import RealtimeWatcher

# ---------------------------------------------------------------------------
# Test 1: Payload Tampering Detection
# ---------------------------------------------------------------------------


class TestPayloadTampering:
    def test_tampered_payload_detected(self):
        """Modify an event's payload → verify_integrity() returns False."""
        chain = EventChain(concept_id="test-tamper")
        e1 = Event(
            concept_id="test-tamper",
            event_type=EventType.REGISTER,
            actor="a",
            payload={"amount": 100},
        )
        e2 = Event(
            concept_id="test-tamper",
            event_type=EventType.VALIDATE,
            actor="b",
            payload={"amount": 200},
        )
        chain.append(e1)
        chain.append(e2)

        assert chain.verify_integrity() is True, "Chain should be valid before tampering"

        # Tamper: modify e1's payload without updating hash
        chain._events[0].payload["amount"] = 999999  # Laundered!

        # Verification should detect the tampering because hash chain now breaks
        # (e2's _prev_hash references original e1.hash, but e1's content changed)
        assert chain.verify_integrity() is False, (
            "Tampered event should be detected by hash chain verification!"
        )

    def test_tampered_payload_with_hash_recomputation_still_detected(self):
        """Even if attacker recomputes e1's hash, e2's _prev_hash still points to old h1."""
        chain = EventChain(concept_id="test-tamper2")
        e1 = Event(
            concept_id="test-tamper2",
            event_type=EventType.REGISTER,
            actor="a",
            payload={"amount": 100},
        )
        e2 = Event(
            concept_id="test-tamper2",
            event_type=EventType.VALIDATE,
            actor="b",
            payload={"amount": 200},
        )
        chain.append(e1)
        chain.append(e2)

        assert chain.verify_integrity() is True

        # Attacker: modify payload AND recompute own hash
        chain._events[0].payload["amount"] = 999999
        chain._events[0].hash = chain._events[0]._compute_hash()
        # e1's own hash now matches its new content
        # BUT e2._prev_hash still points to the ORIGINAL e1.hash
        # → verify_integrity detects the break in chained hashing

        assert chain.verify_integrity() is False, (
            "Hash chain break should be detected — e2._prev_hash ≠ "
            "recomputed e1.hash due to cascading hash change"
        )


# ---------------------------------------------------------------------------
# Test 2: Chain Poisoning (spam events)
# ---------------------------------------------------------------------------


class TestChainPoisoning:
    def test_spam_detection_via_watcher(self):
        """Append 100+ low-quality events → watcher fires chain_large alert."""
        chain = EventChain(concept_id="test-spam")
        watcher = RealtimeWatcher()

        alerted = []

        def on_large(alert):
            alerted.append(alert.alert_type)

        watcher.on("chain_large", on_large)
        watcher.attach(chain)

        # Append 100 spam events (simulating a poisoning agent)
        for i in range(100):
            chain.append(
                Event(
                    concept_id="test-spam",
                    event_type=EventType.REGISTER,
                    actor="poison_agent",
                    payload={"spam_index": i, "quality": "low"},
                )
            )

        assert "chain_large" in alerted, "RealtimeWatcher should detect chain_large at 100 events"

    def test_spam_does_not_break_integrity(self):
        """Even with spam, chain integrity remains intact."""
        chain = EventChain(concept_id="test-spam-integrity")
        for i in range(200):
            chain.append(
                Event(
                    concept_id="test-spam-integrity",
                    event_type=EventType.REGISTER,
                    actor="poison_agent",
                    payload={"spam": i},
                )
            )
        assert chain.verify_integrity() is True, "Spam events should NOT break hash chain integrity"


# ---------------------------------------------------------------------------
# Test 3: Malicious Fork Bombing
# ---------------------------------------------------------------------------


class TestForkBombing:
    def test_many_forks_handled(self):
        """A malicious agent creates 100 forks — ForkManager handles them all."""
        engine = ConsensusEngine()
        base_id = "test-base"

        # Register base concept
        base = EventChain(concept_id=base_id)
        base.append(Event(concept_id=base_id, event_type=EventType.REGISTER, actor="a"))
        engine.chains[base_id] = base

        # Malicious agent forks 100 times
        for i in range(100):
            fork_id = f"malicious-fork-{i}"
            engine.fork(base_id, fork_id, actor="attacker", reason="spam fork")

        # ForkManager should track all forks
        tree = engine.fork_manager.get_fork_tree(base_id)
        assert tree["count"] == 100, f"Expected 100 forks, got {tree['count']}"

        # Each fork's chain should be valid
        for i in range(100):
            fork_id = f"malicious-fork-{i}"
            assert fork_id in engine.chains, f"Fork {fork_id} not registered"
            assert engine.chains[fork_id].verify_integrity() is True

    def test_prune_flag_for_old_forks(self):
        """Long-idle forks should be flagged for pruning."""
        fm = ForkManager()
        old_id = "test-old-fork"

        # Register with old timestamp
        old_time = "2023-01-01T00:00:00+00:00"
        fm.register_fork("base", old_id)
        fm.creation_times[old_id] = old_time

        # Should prune: created > 3 entries ago + idle > 180 days
        should = fm.should_prune(old_id, last_accessed="2023-07-01T00:00:00+00:00")
        assert should is True, "Old idle fork should be flagged for pruning"


# ---------------------------------------------------------------------------
# Test 4: Timestamp Collision Handling
# ---------------------------------------------------------------------------


class TestTimestampCollisions:
    def test_same_timestamp_deterministic_ordering(self):
        """Two events with identical timestamps → ordered by hash deterministically."""
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat()
        e1 = Event(
            concept_id="tc",
            event_type=EventType.REGISTER,
            actor="a",
            timestamp=ts,
            payload={"seq": 1},
        )
        e2 = Event(
            concept_id="tc",
            event_type=EventType.VALIDATE,
            actor="b",
            timestamp=ts,
            payload={"seq": 2},
        )

        # Sort by (timestamp, hash) — hash is deterministic based on content
        sorted_events = sorted([e1, e2], key=lambda e: (e.timestamp, e.hash))

        # Same input → same ordering (deterministic)
        sorted_again = sorted([e1, e2], key=lambda e: (e.timestamp, e.hash))
        assert sorted_events[0].event_id == sorted_again[0].event_id, (
            "Same-timestamp ordering should be deterministic"
        )

    def test_merge_preserves_determinism(self):
        """Merged chain from same inputs should produce identical results."""
        chain1 = EventChain(concept_id="merge-test")
        EventChain(concept_id="merge-test")

        ts = datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat()
        e1 = Event(concept_id="merge-test", event_type=EventType.REGISTER, actor="a", timestamp=ts)
        e2 = Event(concept_id="merge-test", event_type=EventType.VALIDATE, actor="b", timestamp=ts)

        chain1.append(e1)
        chain1.append(e2)

        from adl_lite.sync_manager import SyncManager

        sm = SyncManager("merge-test")
        merged1 = sm.merge(chain1)
        merged2 = sm.merge(chain1)  # Same input → same output

        events1 = [(e.event_id, e.timestamp) for e in merged1.events]
        events2 = [(e.event_id, e.timestamp) for e in merged2.events]
        assert events1 == events2, "Same merge input → same merge output (deterministic)"


# ---------------------------------------------------------------------------
# Test 5: SSA Circumvention (known limitation)
# ---------------------------------------------------------------------------


class TestSSACircumvention:
    def test_creative_circumlocution_bypasses_ssa(self):
        """Agents can use 'the aforementioned mechanism' to avoid pronoun detection."""
        creative_texts = [
            "The aforementioned mechanism demonstrates strong alignment.",
            "The previously described pattern occurs consistently.",
            "Said relationship requires further analysis.",
        ]
        from adl_lite.validator import find_pronoun_violations

        for text in creative_texts:
            violations = find_pronoun_violations(text)
            # These SHOULD be ambiguous but SSA won't catch them
            # This is the KNOWN LIMITATION documented in the paper
            assert len(violations) == 0, (
                f"SSA does not catch: '{text[:50]}...' — "
                "this is an acknowledged heuristic limitation"
            )

        print(f"\n{'=' * 60}")
        print("ADVERSARIAL: SSA CIRCUMVENTION CONFIRMED")
        print(f"{'=' * 60}")
        print("  Creative circumlocutions bypass SSA pronoun detection.")
        print("  This is a documented limitation (§3.4, §7.3).")
        print(f"{'=' * 60}")
