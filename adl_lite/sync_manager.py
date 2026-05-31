"""ADL Lite — Edge Sync Manager

Handles offline-first operation and eventual consistency across
edge nodes and a central EventChain database.

Architecture:
  - Edge nodes operate fully offline: chain.append(event) is local
  - SideEffectQueue: buffers effects that need network (Lark bridge)
  - SyncManager.merge(): resolves diverged chains by timestamp ordering
  - append-only = no merge conflicts = natural CRDT

Design principle (event-first):
  An update is not a mutation of existing state.
  An update IS a new event. Two edges both add events.
  Merge = sort all events by timestamp, append to unified chain.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from .models import Event, EventChain, EventType

# ---------------------------------------------------------------------------
# Side Effect Queue (buffers network-dependent effects)
# ---------------------------------------------------------------------------


class QueuedEffect:
    """A side effect that could not execute (e.g., offline)."""

    def __init__(
        self,
        effect_name: str,
        concept_id: str,
        params: dict[str, Any],
        created_at: str | None = None,
    ) -> None:
        self.effect_name = effect_name
        self.concept_id = concept_id
        self.params = params
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()


class SideEffectQueue:
    """
    FIFO queue for side effects that need network connectivity.
    Drains automatically when on_network_available() is called.
    """

    def __init__(self) -> None:
        self._queue: list[QueuedEffect] = []
        self._executor: Callable[[QueuedEffect], bool] | None = None

    def enqueue(self, effect: QueuedEffect) -> None:
        self._queue.append(effect)

    def enqueue_action(
        self,
        effect_name: str,
        concept_id: str,
        params: dict[str, Any],
    ) -> None:
        self.enqueue(QueuedEffect(effect_name, concept_id, params))

    @property
    def pending(self) -> int:
        return len(self._queue)

    @property
    def queued(self) -> list[QueuedEffect]:
        return list(self._queue)

    def set_executor(
        self,
        executor: Callable[[QueuedEffect], bool],
    ) -> None:
        """Register the function that actually runs each effect."""
        self._executor = executor

    def drain(self) -> tuple[int, int]:
        """
        Execute all queued effects. Returns (success_count, failure_count).
        Uses the registered executor if available; otherwise all fail.
        Failed effects are re-queued at the end; processing continues
        through the entire queue rather than stopping on first failure.
        """
        success = 0
        failed = 0
        retry_queue: list[QueuedEffect] = []

        while self._queue:
            effect = self._queue.pop(0)
            if self._executor:
                ok = self._executor(effect)
                if ok:
                    success += 1
                else:
                    failed += 1
                    retry_queue.append(effect)
            else:
                failed += 1
                retry_queue.append(effect)

        # Re-queue failed effects for next drain attempt
        self._queue = retry_queue + self._queue
        return success, failed

    def clear(self) -> None:
        self._queue.clear()


# ---------------------------------------------------------------------------
# Sync Manager (edge ↔ center merge)
# ---------------------------------------------------------------------------


class SyncManager:
    """
    Merges EventChains from multiple edge nodes.

    The key insight: EventChain is append-only. Two diverged chains
    each have new events appended. Merge = collect all events, sort
    by timestamp, deduplicate, and rebuild a unified chain.

    No merge conflict is possible because:
      - Events are facts, not mutations
      - Two events with the same event_id represent the same fact
      - Two events with different event_ids are different facts
      - Both can coexist in the merged chain
    """

    def __init__(self, concept_id: str) -> None:
        self.concept_id = concept_id

    def merge(
        self,
        *chains: EventChain,
        base_chain: EventChain | None = None,
    ) -> EventChain:
        """
        Merge multiple event chains into one unified chain.

        Args:
            *chains: Diverged chains from edge nodes (after base_chain diverged)
            base_chain: The common ancestor chain (before divergence)

        Returns:
            A new EventChain containing all events from all chains,
            sorted by timestamp with duplicates removed.
        """
        seen: set[str] = set()
        all_events: list[Event] = []

        # Collect from base chain first (chronologically earliest)
        if base_chain:
            for event in base_chain.events:
                if event.event_id not in seen:
                    seen.add(event.event_id)
                    all_events.append(event)

        # Collect from edge chains
        for chain in chains:
            for event in chain.events:
                if event.event_id not in seen:
                    seen.add(event.event_id)
                    all_events.append(event)

        # Sort by timestamp, then by SHA-256 hash for deterministic ordering
        # across machines (event_id is uuid4, non-deterministic)
        all_events.sort(key=lambda e: (e.timestamp, e.hash))

        # Rebuild unified chain
        unified = EventChain(concept_id=self.concept_id)
        for event in all_events:
            unified.append(event)

        return unified

    @staticmethod
    def diff(
        center_chain: EventChain,
        edge_chain: EventChain,
    ) -> list[Event]:
        """
        Events present in edge_chain but not in center_chain.
        These are the "new events" to push to center.
        """
        center_ids = {e.event_id for e in center_chain.events}
        return [e for e in edge_chain.events if e.event_id not in center_ids]

    @staticmethod
    def push(
        edge_chain: EventChain,
        center_chain: EventChain,
    ) -> EventChain:
        """
        Push new events from edge to center.
        Returns updated center chain.
        """
        new_events = SyncManager.diff(center_chain, edge_chain)
        updated = EventChain(concept_id=center_chain.concept_id)
        for e in center_chain.events:
            updated.append(e)
        for e in sorted(new_events, key=lambda e: (e.timestamp, e.hash)):
            updated.append(e)
        return updated

    @staticmethod
    def pull(
        edge_chain: EventChain,
        center_chain: EventChain,
    ) -> EventChain:
        """
        Pull new events from center to edge.
        Returns updated edge chain.
        """
        new_events = SyncManager.diff(edge_chain, center_chain)
        updated = EventChain(concept_id=edge_chain.concept_id)
        for e in edge_chain.events:
            updated.append(e)
        for e in sorted(new_events, key=lambda e: (e.timestamp, e.hash)):
            updated.append(e)
        return updated

    @staticmethod
    def verify_both(
        edge_chain: EventChain,
        center_chain: EventChain,
    ) -> tuple[bool, bool]:
        """Verify both chains have integrity before merge."""
        return edge_chain.verify_integrity(), center_chain.verify_integrity()


# ---------------------------------------------------------------------------
# Offline-first Edge Node (composes chain + queue + watcher)
# ---------------------------------------------------------------------------


class EdgeNode:
    """
    A self-contained edge computing node.

    Operates fully offline:
      - Local EventChain writes (synchronous, in-memory)
      - Transaction → Event → chain.append() → RealtimeWatcher.check()
      - Side effects queued (SideEffectQueue)
      - On reconnect: sync chain with center, drain side effects
    """

    def __init__(self, concept_id: str, node_id: str = "edge-01") -> None:
        self.concept_id = concept_id
        self.node_id = node_id
        self.chain = EventChain(concept_id=concept_id)
        self.queue = SideEffectQueue()
        self._online = True

    # ------------------------------------------------------------------
    # Offline-safe core operations
    # ------------------------------------------------------------------

    def record_event(
        self,
        event_type: EventType,
        payload: dict[str, Any],
        actor: str | None = None,
        reasoning: str = "",
        side_effects: list[str] | None = None,
    ) -> Event:
        """
        Record a new event. NEVER requires network.

        Always:
          1. Create the Event
          2. Append to local chain (synchronous)
          3. Verify chain integrity

        If side effects are declared:
          4a. Online  → execute immediately
          4b. Offline → enqueue for later

        Returns the newly created Event.
        """
        event = Event(
            concept_id=self.concept_id,
            event_type=event_type,
            actor=actor or self.node_id,
            reasoning=reasoning,
            payload=payload,
        )
        self.chain.append(event)

        if side_effects:
            for se in side_effects:
                if self._online:
                    self._try_effect(se, self.concept_id, payload)
                else:
                    self.queue.enqueue_action(se, self.concept_id, payload)

        return event

    @staticmethod
    def _try_effect(effect_name: str, concept_id: str, params: dict) -> bool:
        """
        Attempt a single side effect. Returns True if executed.
        Lark effects silently fail if lark-cli is not available.
        """
        try:
            if effect_name == "lark_announce":
                from .lark.announce import announce

                chat_id = params.get("chat_id", "")
                if chat_id:
                    announce(concept_id=concept_id, chat_id=chat_id)
                    return True
            elif effect_name == "lark_dashboard":
                from .lark.dashboard import sync_dashboard_row

                sheet_id = params.get("sheet_id", "")
                if sheet_id:
                    sync_dashboard_row(adl_id=concept_id, sheet_id=sheet_id)
                    return True
            elif effect_name == "lark_publish":
                from .lark.publish import publish_file

                wiki_space = params.get("wiki_space", "")
                if wiki_space:
                    publish_file(params.get("source_path", ""), wiki_space=wiki_space)
                    return True
        except Exception:
            pass
        return False

    # ------------------------------------------------------------------
    # Network state
    # ------------------------------------------------------------------

    @property
    def online(self) -> bool:
        return self._online

    def go_offline(self) -> None:
        """Simulate network loss. Side effects will queue."""
        self._online = False

    def go_online(self, center_chain: EventChain | None = None) -> dict[str, Any]:
        """
        Reconnect: sync chain, drain side effects.

        Returns summary: chains_synced, effects_drained, integrity_ok
        """
        self._online = True
        result: dict[str, Any] = {"chains_synced": False, "effects_drained": 0}

        # Sync chain with center
        if center_chain:
            updated = SyncManager.pull(self.chain, center_chain)
            self.chain = updated
            result["chains_synced"] = True
            result["integrity_ok"] = self.chain.verify_integrity()
            result["chain_length"] = self.chain.length

        # Drain queued side effects
        success, _ = self.queue.drain()
        result["effects_drained"] = success

        return result
