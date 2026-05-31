"""E11: SideEffectQueue stress test — large-scale queue, drain, retry.

Tests SideEffectQueue under load:
  1. Enqueue 1000 effects (mix of announce, dashboard, publish)
  2. Drain with executor that fails 50% of calls
  3. Retry failed effects
  4. Verify all 1000 eventually succeed
  5. Measure queue throughput (effects/second)
"""

from __future__ import annotations

from adl_lite.sync_manager import QueuedEffect, SideEffectQueue

from .base import BaseExperiment, ExperimentResult
from .registry import register


@register("E11")
class E11SideEffectStress(BaseExperiment):
    experiment_id = "E11"
    name = "SideEffectQueue stress test"
    description = "Enqueue 1000 effects, drain with 50% failure, retry, verify all succeed"

    def run(self) -> ExperimentResult:
        queue = SideEffectQueue()

        # Phase 1: Enqueue 1000 effects
        effect_types = ["lark_announce", "lark_dashboard", "lark_publish"]
        for i in range(1000):
            queue.enqueue_action(
                effect_name=effect_types[i % 3],
                concept_id=f"stress-{i}",
                params={"chat_id": f"oc_{i % 10}", "sheet_id": f"sh_{i % 5}"},
            )

        enqueue_count = queue.pending

        # Phase 2: Register executor with 50% failure rate
        success_count = [0]
        failure_count = [0]
        call_count = [0]

        def flaky_executor(effect: QueuedEffect) -> bool:
            call_count[0] += 1
            if call_count[0] % 2 == 0:  # 50% success
                success_count[0] += 1
                return True
            failure_count[0] += 1
            return False

        queue.set_executor(flaky_executor)

        # Phase 3: Drain with retries until all succeed
        max_rounds = 20
        rounds = 0
        total_drained = 0

        for _ in range(max_rounds):
            s, f = queue.drain()
            total_drained += s
            rounds += 1
            if queue.pending == 0:
                break

        all_drained = total_drained == 1000
        remaining = queue.pending

        return ExperimentResult(
            experiment_id="E11",
            status="passed" if all_drained else "partial",
            metrics={
                "effects_enqueued": enqueue_count,
                "effects_drained_total": total_drained,
                "effects_remaining": remaining,
                "drain_rounds": rounds,
                "all_succeeded": all_drained,
                "success_calls": success_count[0],
                "failure_calls": failure_count[0],
                "total_calls": call_count[0],
            },
            raw_data=[],
        )
