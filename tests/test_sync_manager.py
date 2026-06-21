"""
Tests for adl_lite.sync_manager — Edge Sync & Offline-First Operations.

Covers:
    - QueuedEffect: creation, default timestamp
    - SideEffectQueue: enqueue, enqueue_action, pending, queued, drain (success/failure/no-executor), clear
    - SyncManager: merge (base_chain + edges), diff, push, pull, verify_both
    - EdgeNode: record_event (online/offline), go_offline/go_online, _try_effect
"""

from __future__ import annotations

import pytest

from adl_lite.models import Event, EventChain, EventType
from adl_lite.sync_manager import (
    EdgeNode,
    QueuedEffect,
    SideEffectQueue,
    SyncManager,
)

# ---------------------------------------------------------------------------
# QueuedEffect
# ---------------------------------------------------------------------------


class TestQueuedEffect:
    def test_create(self):
        qe = QueuedEffect("test_effect", "c1", {"key": "value"})
        assert qe.effect_name == "test_effect"
        assert qe.concept_id == "c1"
        assert qe.params == {"key": "value"}
        assert qe.created_at is not None

    def test_explicit_timestamp(self):
        qe = QueuedEffect("test", "c1", {}, created_at="2024-01-01T00:00:00Z")
        assert qe.created_at == "2024-01-01T00:00:00Z"


# ---------------------------------------------------------------------------
# SideEffectQueue
# ---------------------------------------------------------------------------


class TestSideEffectQueue:
    @pytest.fixture
    def queue(self) -> SideEffectQueue:
        return SideEffectQueue()

    def test_enqueue(self, queue: SideEffectQueue):
        qe = QueuedEffect("test_effect", "c1", {"key": "val"})
        queue.enqueue(qe)
        assert queue.pending == 1
        assert len(queue.queued) == 1

    def test_enqueue_action(self, queue: SideEffectQueue):
        queue.enqueue_action("test_effect", "c2", {"key": "val"})
        assert queue.pending == 1
        assert queue.queued[0].effect_name == "test_effect"
        assert queue.queued[0].concept_id == "c2"

    def test_pending_zero_initially(self, queue: SideEffectQueue):
        assert queue.pending == 0

    def test_queued_returns_copy(self, queue: SideEffectQueue):
        queue.enqueue_action("test", "c1", {})
        q = queue.queued
        q.clear()
        assert queue.pending == 1  # original unchanged

    def test_drain_with_executor_all_success(self, queue: SideEffectQueue):
        calls = []

        def executor(effect: QueuedEffect) -> bool:
            calls.append(effect.effect_name)
            return True

        queue.set_executor(executor)
        queue.enqueue_action("fx_a", "c1", {})
        queue.enqueue_action("fx_b", "c1", {})
        success, failed = queue.drain()
        assert success == 2
        assert failed == 0
        assert calls == ["fx_a", "fx_b"]
        assert queue.pending == 0

    def test_drain_with_executor_mixed(self, queue: SideEffectQueue):
        def executor(effect: QueuedEffect) -> bool:
            return effect.effect_name == "good"

        queue.set_executor(executor)
        queue.enqueue_action("good", "c1", {})
        queue.enqueue_action("bad", "c1", {})
        success, failed = queue.drain()
        assert success == 1
        assert failed == 1
        # failed effect is re-queued
        assert queue.pending == 1
        assert queue.queued[0].effect_name == "bad"

    def test_drain_no_executor_all_fail(self, queue: SideEffectQueue):
        queue.enqueue_action("fx", "c1", {})
        success, failed = queue.drain()
        assert success == 0
        assert failed == 1
        assert queue.pending == 1  # re-queued

    def test_clear(self, queue: SideEffectQueue):
        queue.enqueue_action("fx", "c1", {})
        queue.clear()
        assert queue.pending == 0


# ---------------------------------------------------------------------------
# SyncManager — merge / diff / push / pull / verify
# ---------------------------------------------------------------------------


class TestSyncManager:
    @pytest.fixture
    def sm(self) -> SyncManager:
        return SyncManager("sync-concept")

    def _make_chain(self, concept_id: str, events_data: list[tuple[str, str]]) -> EventChain:
        """Helper: build a chain from (event_type, actor) tuples."""
        from datetime import datetime, timezone

        chain = EventChain(concept_id=concept_id)
        for i, (etype, actor) in enumerate(events_data):
            event = Event(
                concept_id=concept_id,
                event_type=EventType(etype),
                actor=actor,
                timestamp=datetime(2024, 1, i + 1, tzinfo=timezone.utc).isoformat(),
            )
            chain.append(event)
        return chain

    def test_merge_no_divergence(self, sm: SyncManager):
        base = self._make_chain("sync-concept", [("register", "sys")])
        merged = sm.merge(base)
        assert merged.concept_id == "sync-concept"
        assert merged.length == 1

    def test_merge_with_base_and_edges(self, sm: SyncManager):
        base = self._make_chain("sync-concept", [("register", "sys")])
        edge1 = self._make_chain("sync-concept", [("validate", "agent1")])
        edge2 = self._make_chain("sync-concept", [("deprecate", "agent2")])

        merged = sm.merge(edge1, edge2, base_chain=base)
        # base: 1, edge1: 1, edge2: 1 = 3 events
        assert merged.length == 3

    def test_merge_deduplicates_by_event_id(self, sm: SyncManager):
        chain = self._make_chain("sync-concept", [("register", "sys")])
        # Same chain twice
        merged = sm.merge(chain, chain)
        assert merged.length == 1  # deduplicated

    def test_merge_sorted_by_timestamp(self, sm: SyncManager):
        from datetime import datetime, timezone

        chain = EventChain(concept_id="sync-concept")
        e1 = Event(
            concept_id="sync-concept",
            event_type=EventType.REGISTER,
            actor="a",
            timestamp=datetime(2024, 1, 3, tzinfo=timezone.utc).isoformat(),
        )
        e2 = Event(
            concept_id="sync-concept",
            event_type=EventType.VALIDATE,
            actor="b",
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat(),
        )
        chain.append(e2)
        chain.append(e1)

        merged = sm.merge(chain)
        events = merged.events
        # Should be sorted by timestamp
        assert events[0].event_type == EventType.VALIDATE
        assert events[1].event_type == EventType.REGISTER

    def test_diff_finds_new_events(self, sm: SyncManager):
        # Build a shared base chain, then extend for edge
        from datetime import datetime, timezone

        base = EventChain(concept_id="sync-concept")
        base_event = Event(
            concept_id="sync-concept",
            event_type=EventType.REGISTER,
            actor="sys",
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat(),
        )
        base.append(base_event)

        # Clone base into center (same events, deterministic after base_event)
        center = EventChain(concept_id="sync-concept")
        for e in base.events:
            center.append(e)

        # Edge = base + one new event
        edge = EventChain(concept_id="sync-concept")
        for e in base.events:
            edge.append(e)
        edge.append(
            Event(
                concept_id="sync-concept",
                event_type=EventType.VALIDATE,
                actor="edge_agent",
                timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc).isoformat(),
            )
        )

        new = SyncManager.diff(center, edge)
        assert len(new) == 1
        assert new[0].event_type == EventType.VALIDATE
        assert new[0].actor == "edge_agent"

    def test_diff_empty(self, sm: SyncManager):
        chain = self._make_chain("sync-concept", [("register", "sys")])
        new = SyncManager.diff(chain, chain)
        assert new == []

    def test_push(self, sm: SyncManager):
        from datetime import datetime, timezone

        base = EventChain(concept_id="sync-concept")
        base.append(
            Event(
                concept_id="sync-concept",
                event_type=EventType.REGISTER,
                actor="sys",
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat(),
            )
        )

        center = EventChain(concept_id="sync-concept")
        for e in base.events:
            center.append(e)

        edge = EventChain(concept_id="sync-concept")
        for e in base.events:
            edge.append(e)
        edge.append(
            Event(
                concept_id="sync-concept",
                event_type=EventType.VALIDATE,
                actor="edge1",
                timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc).isoformat(),
            )
        )

        updated = SyncManager.push(edge, center)
        assert updated.length == 2
        assert any(e.event_type == EventType.VALIDATE for e in updated.events)

    def test_pull(self, sm: SyncManager):
        from datetime import datetime, timezone

        base = EventChain(concept_id="sync-concept")
        base.append(
            Event(
                concept_id="sync-concept",
                event_type=EventType.REGISTER,
                actor="sys",
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat(),
            )
        )

        center = EventChain(concept_id="sync-concept")
        for e in base.events:
            center.append(e)
        center.append(
            Event(
                concept_id="sync-concept",
                event_type=EventType.VALIDATE,
                actor="center1",
                timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc).isoformat(),
            )
        )

        edge = EventChain(concept_id="sync-concept")
        for e in base.events:
            edge.append(e)

        updated = SyncManager.pull(edge, center)
        assert updated.length == 2
        assert any(e.event_type == EventType.VALIDATE for e in updated.events)

    def test_verify_both(self, sm: SyncManager):
        from datetime import datetime, timezone

        c1 = EventChain(concept_id="sync-concept")
        c1.append(
            Event(
                concept_id="sync-concept",
                event_type=EventType.REGISTER,
                actor="sys",
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat(),
            )
        )

        c2 = EventChain(concept_id="sync-concept")
        for e in c1.events:
            c2.append(e)
        c2.append(
            Event(
                concept_id="sync-concept",
                event_type=EventType.VALIDATE,
                actor="x",
                timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc).isoformat(),
            )
        )

        ok1, ok2 = SyncManager.verify_both(c1, c2)
        assert ok1 is True
        assert ok2 is True

    def test_merge_empty_all(self, sm: SyncManager):
        merged = sm.merge()
        assert merged.length == 0
        assert merged.concept_id == "sync-concept"


# ---------------------------------------------------------------------------
# EdgeNode
# ---------------------------------------------------------------------------


class TestEdgeNode:
    @pytest.fixture
    def node(self) -> EdgeNode:
        return EdgeNode("edge-concept", node_id="test-edge")

    def test_init_state(self, node: EdgeNode):
        assert node.concept_id == "edge-concept"
        assert node.node_id == "test-edge"
        assert node.online is True
        assert node.chain.length == 0
        assert node.queue.pending == 0

    def test_record_event_online(self, node: EdgeNode):
        event = node.record_event(
            EventType.REGISTER,
            payload={"amount": 100},
            actor="actor_1",
            reasoning="test",
        )
        assert event.concept_id == "edge-concept"
        assert event.event_type == EventType.REGISTER
        assert node.chain.length == 1

    def test_record_event_online_with_side_effects(self, node: EdgeNode):
        # Side effects try to execute but fail silently (no registered effects)
        event = node.record_event(
            EventType.REGISTER,
            payload={"key": "val"},
            side_effects=["unknown_effect"],
        )
        assert event is not None
        assert node.chain.length == 1

    def test_record_event_default_actor(self, node: EdgeNode):
        event = node.record_event(EventType.REGISTER, payload={})
        assert event.actor == "test-edge"

    def test_go_offline_queues_effects(self, node: EdgeNode):
        node.go_offline()
        assert node.online is False

        node.record_event(
            EventType.REGISTER,
            payload={"amount": 100},
            side_effects=["test_effect"],
        )
        # Effect should be queued
        assert node.queue.pending == 1
        assert node.queue.queued[0].effect_name == "test_effect"

    def test_go_online_without_center(self, node: EdgeNode):
        node.go_offline()
        result = node.go_online()
        assert result["chains_synced"] is False
        assert result["effects_drained"] == 0

    def test_go_online_with_center(self, node: EdgeNode):
        # Record events offline, then sync
        node.go_offline()
        node.record_event(EventType.REGISTER, payload={"amount": 100})

        # Build a center chain that's ahead (with a future timestamp to maintain monotonicity)
        center = EventChain(concept_id="edge-concept")

        from datetime import datetime, timedelta, timezone

        center.append(
            Event(
                concept_id="edge-concept",
                event_type=EventType.VALIDATE,
                actor="center_agent",
                timestamp=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            )
        )

        result = node.go_online(center)
        assert result["chains_synced"] is True
        assert result["integrity_ok"] is True
        assert result["chain_length"] > 0

    def test_try_effect_unknown(self):
        """Unknown effect name should return False."""
        result = EdgeNode._try_effect("unknown_effect", "c1", {})
        assert result is False
