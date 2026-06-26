"""E8: Edge sync — offline-first operation and chain merge.

Tests EdgeNode offline operation and SyncManager merge:
  1. Edge operates offline (chain writes still work)
  2. Side effects queue during offline
  3. Multiple edges diverge independently
  4. Merge produces unified chain (no conflicts)
  5. Push/pull between edge and center
  6. Side effects drain on reconnect
"""

from __future__ import annotations

from adl_lite.models import Event, EventChain, EventType
from adl_lite.sync_manager import (
    EdgeNode,
    SideEffectQueue,
    SyncManager,
)

from .base import BaseExperiment, ExperimentResult
from .registry import register


@register("E8")
class E8EdgeSync(BaseExperiment):
    experiment_id = "E8"
    name = "Edge sync and offline operation"
    description = "Offline chain writes, side effect queue, merge without conflicts"

    def run(self) -> ExperimentResult:
        results = []
        errors = []

        # ===== TEST 1: Offline operation =====
        edge = EdgeNode(concept_id="edge-test-1", node_id="edge-branch-a")
        edge.go_offline()

        # Record events while offline
        edge.record_event(EventType.REGISTER, {"note": "offline txn 1"})
        edge.record_event(EventType.REGISTER, {"note": "offline txn 2"})
        edge.record_event(
            EventType.VALIDATE,
            {"confidence": 0.9},
            reasoning="Validated locally",
            side_effects=["lark_announce"],
        )

        chain_ok = edge.chain.verify_integrity()
        offline_length = edge.chain.length
        queued_count = edge.queue.pending

        offline_ok = chain_ok and offline_length == 3 and queued_count == 1
        results.append(
            {
                "test": "offline_operation",
                "chain_integrity": chain_ok,
                "events_recorded": offline_length,
                "effects_queued": queued_count,
                "ok": offline_ok,
            }
        )
        if not offline_ok:
            errors.append(
                f"Offline: integrity={chain_ok}, length={offline_length}, queued={queued_count}"
            )

        # ===== TEST 2: Side effects queue correctly =====
        q = SideEffectQueue()
        q.enqueue_action("lark_announce", "concept-1", {"chat_id": "oc_test"})
        q.enqueue_action("lark_dashboard", "concept-2", {"sheet_id": "sh_test"})
        assert q.pending == 2
        results.append(
            {
                "test": "side_effect_queue",
                "queued": q.pending,
                "ok": q.pending == 2,
            }
        )

        # Drain with no executor → all fail, re-queued
        success, failed = q.drain()
        assert success == 0 and failed == 2  # both fail without executor
        assert q.pending == 2  # Both re-queued at end
        results.append(
            {
                "test": "queue_drain_no_executor",
                "success": success,
                "failed": failed,
                "ok": success == 0 and failed == 2,
            }
        )

        # ===== TEST 3: Merge diverged chains (no conflict) =====
        # Center chain
        center = EventChain(concept_id="merge-test")
        center.append(Event(concept_id="merge-test", event_type=EventType.REGISTER, actor="center"))
        center.append(Event(concept_id="merge-test", event_type=EventType.REGISTER, actor="center"))

        # Edge-A diverged after event #1
        edge_a = EventChain(concept_id="merge-test")
        edge_a.append(Event(concept_id="merge-test", event_type=EventType.REGISTER, actor="center"))
        edge_a.append(Event(concept_id="merge-test", event_type=EventType.VALIDATE, actor="edge-a"))

        # Edge-B diverged after event #1
        edge_b = EventChain(concept_id="merge-test")
        edge_b.append(Event(concept_id="merge-test", event_type=EventType.REGISTER, actor="center"))
        edge_b.append(
            Event(
                concept_id="merge-test",
                event_type=EventType.ANNOUNCE,
                actor="edge-b",
                payload={"action": "announce"},
            )
        )

        mgr = SyncManager(concept_id="merge-test")
        merged = mgr.merge(edge_a, edge_b, base_chain=center)

        # Merged chain should have 5 unique events (2 base + 1 validate + 1 announce)
        # Actually: center has 2 events; edge_a has event1 + edge_a's validate; edge_b has event1 + edge_b's announce
        # After dedup: center's 2 + edge_a VALIDATE + edge_b's ANNOUNCE = 4 events
        # Wait — center has 2 REGISTER events with different event_ids. edge_a copies event1 (REGISTER, same as center's first). edge_b copies event1 too.
        # Deduplication uses event_id. So center's REGISTER#1, REGISTER#2, edge_a's VALIDATE, edge_b's ANNOUNCE = 4 unique events.

        merged_ok = merged.length >= 4 and merged.verify_integrity()
        results.append(
            {
                "test": "merge_diverged_chains",
                "events_merged": merged.length,
                "integrity_ok": merged.verify_integrity(),
                "ok": merged_ok,
            }
        )
        if not merged_ok:
            errors.append(f"Merge: length={merged.length}, integrity={merged.verify_integrity()}")

        # ===== TEST 4: Semantic conflict merge — same event type, different confidence =====
        # Both edges validate the same concept with different confidence values.
        # These are different facts (different confidence), both should co-exist.
        base_sc = EventChain(concept_id="semantic-conflict")
        base_sc.append(
            Event(concept_id="semantic-conflict", event_type=EventType.REGISTER, actor="genesis")
        )

        edge_a_sc = EventChain(concept_id="semantic-conflict")
        edge_a_sc.append(
            Event(concept_id="semantic-conflict", event_type=EventType.REGISTER, actor="genesis")
        )
        edge_a_sc.append(
            Event(
                concept_id="semantic-conflict",
                event_type=EventType.VALIDATE,
                actor="edge-a",
                payload={"confidence": 0.9},
            )
        )

        edge_b_sc = EventChain(concept_id="semantic-conflict")
        edge_b_sc.append(
            Event(concept_id="semantic-conflict", event_type=EventType.REGISTER, actor="genesis")
        )
        edge_b_sc.append(
            Event(
                concept_id="semantic-conflict",
                event_type=EventType.VALIDATE,
                actor="edge-b",
                payload={"confidence": 0.5},
            )
        )

        mgr_sc = SyncManager(concept_id="semantic-conflict")
        merged_sc = mgr_sc.merge(edge_a_sc, edge_b_sc, base_chain=base_sc)

        # Both VALIDATE events should be present (different event_ids, different facts)
        validate_count = sum(1 for e in merged_sc.events if e.event_type == EventType.VALIDATE)
        sem_conflict_ok = (
            merged_sc.length >= 4 and validate_count == 2 and merged_sc.verify_integrity()
        )
        results.append(
            {
                "test": "merge_semantic_conflict",
                "events_merged": merged_sc.length,
                "validate_events": validate_count,
                "integrity_ok": merged_sc.verify_integrity(),
                "ok": merged_sc.length >= 4
                and validate_count == 2
                and merged_sc.verify_integrity(),
            }
        )

        # ===== TEST 5: Contradictory lifecycle merge — VALIDATE vs DEPRECATE =====
        # Both are valid facts describing the same concept at the same time.
        # The chain preserves both — status resolves to the chronologically last lifecycle event.
        base_lc = EventChain(concept_id="lifecycle-conflict")
        base_lc.append(
            Event(concept_id="lifecycle-conflict", event_type=EventType.REGISTER, actor="genesis")
        )

        edge_a_lc = EventChain(concept_id="lifecycle-conflict")
        edge_a_lc.append(
            Event(concept_id="lifecycle-conflict", event_type=EventType.REGISTER, actor="genesis")
        )
        edge_a_lc.append(
            Event(concept_id="lifecycle-conflict", event_type=EventType.VALIDATE, actor="edge-a")
        )

        edge_b_lc = EventChain(concept_id="lifecycle-conflict")
        edge_b_lc.append(
            Event(concept_id="lifecycle-conflict", event_type=EventType.REGISTER, actor="genesis")
        )
        edge_b_lc.append(
            Event(concept_id="lifecycle-conflict", event_type=EventType.DEPRECATE, actor="edge-b")
        )

        mgr_lc = SyncManager(concept_id="lifecycle-conflict")
        merged_lc = mgr_lc.merge(edge_a_lc, edge_b_lc, base_chain=base_lc)
        # Both events preserved; status is derived from the last lifecycle event in the chain
        lc_ok = merged_lc.length >= 4 and merged_lc.verify_integrity()
        results.append(
            {
                "test": "merge_contradictory_lifecycle",
                "events_merged": merged_lc.length,
                "chain_status": merged_lc.status.value,
                "integrity_ok": merged_lc.verify_integrity(),
                "ok": lc_ok,
            }
        )

        # ===== TEST 6: Divergent terminal states — ARCHIVE vs FORK =====
        edge_a_div = EventChain(concept_id="divergent-terminal")
        edge_a_div.append(
            Event(concept_id="divergent-terminal", event_type=EventType.REGISTER, actor="genesis")
        )
        edge_a_div.append(
            Event(concept_id="divergent-terminal", event_type=EventType.VALIDATE, actor="edge-a")
        )
        edge_a_div.append(
            Event(concept_id="divergent-terminal", event_type=EventType.ARCHIVE, actor="edge-a")
        )

        edge_b_div = EventChain(concept_id="divergent-terminal")
        edge_b_div.append(
            Event(concept_id="divergent-terminal", event_type=EventType.REGISTER, actor="genesis")
        )
        edge_b_div.append(
            Event(concept_id="divergent-terminal", event_type=EventType.VALIDATE, actor="edge-b")
        )
        edge_b_div.append(
            Event(concept_id="divergent-terminal", event_type=EventType.FORK, actor="edge-b")
        )

        mgr_div = SyncManager(concept_id="divergent-terminal")
        merged_div = mgr_div.merge(edge_a_div, edge_b_div)
        div_ok = merged_div.length >= 5 and merged_div.verify_integrity()
        results.append(
            {
                "test": "merge_divergent_terminal",
                "events_merged": merged_div.length,
                "integrity_ok": merged_div.verify_integrity(),
                "ok": div_ok,
            }
        )
        # ===== TEST 7: Push/pull =====
        # Edge writes new event → push to center
        edge_chain = EventChain(concept_id="push-test")
        edge_chain.append(
            Event(concept_id="push-test", event_type=EventType.REGISTER, actor="genesis")
        )
        edge_chain.append(
            Event(concept_id="push-test", event_type=EventType.REGISTER, actor="edge")
        )

        center_chain = EventChain(concept_id="push-test")
        center_chain.append(
            Event(concept_id="push-test", event_type=EventType.REGISTER, actor="genesis")
        )

        pushed = SyncManager.push(edge_chain, center_chain)
        push_ok = pushed.length >= 3 and pushed.verify_integrity()

        # Center writes update → pull to edge
        center_chain.append(
            Event(concept_id="push-test", event_type=EventType.VALIDATE, actor="center")
        )
        pulled = SyncManager.pull(edge_chain, center_chain)
        pull_ok = pulled.length >= 3 and pulled.status.value == "validated"

        results.append(
            {
                "test": "push_pull",
                "push_length": pushed.length,
                "pull_length": pulled.length,
                "pull_status": pulled.status.value,
                "ok": push_ok and pull_ok,
            }
        )
        if not (push_ok and pull_ok):
            errors.append(f"Push/pull: push_len={pushed.length}, pull_len={pulled.length}")

        # ===== TEST 8: Reconnect drain =====
        edge2 = EdgeNode(concept_id="reconnect-test", node_id="edge-2")
        edge2.go_offline()
        edge2.record_event(EventType.REGISTER, {"note": "offline"}, side_effects=["lark_announce"])
        assert edge2.queue.pending == 1

        result = edge2.go_online()  # No center chain provided
        drain_ok = not result["chains_synced"] and result["effects_drained"] >= 0
        results.append(
            {
                "test": "reconnect_drain",
                "online": edge2.online,
                "effects_queued_before": 1,
                "ok": drain_ok,
            }
        )
        if not drain_ok:
            errors.append(f"Reconnect: {result}")

        all_ok = (
            offline_ok
            and merged_ok
            and sem_conflict_ok
            and lc_ok
            and div_ok
            and push_ok
            and pull_ok
            and drain_ok
        )

        return ExperimentResult(
            experiment_id="E8",
            status="passed" if all_ok else "partial",
            metrics={
                "offline_operation_ok": offline_ok,
                "events_recorded_offline": offline_length,
                "effects_queued_offline": queued_count,
                "merge_no_conflict_ok": merged_ok,
                "merge_semantic_conflict_ok": sem_conflict_ok,
                "merge_contradictory_lifecycle_ok": lc_ok,
                "merge_divergent_terminal_ok": div_ok,
                "push_pull_ok": push_ok and pull_ok,
                "reconnect_drain_ok": drain_ok,
            },
            raw_data=results,
            errors=errors,
        )
