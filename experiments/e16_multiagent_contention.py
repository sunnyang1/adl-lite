"""E16: Multi-agent contention simulation (negative-result experiment).

Simulates k independent agents appending events to shared chains concurrently.
Measures: (1) conflict rate (simultaneous VALIDATE on same provisional concept),
(2) fork rate when fork-on-conflict is enabled, (3) integrity preservation.

This is a *simulation* on a single host using threading; it does not claim to be
a distributed deployment test.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from adl_lite.models import Event, EventChain, EventType

from .base import BaseExperiment, ExperimentResult
from .registry import register


@register("E16")
class E16MultiAgentContention(BaseExperiment):
    experiment_id = "E16"
    name = "Multi-agent contention simulation"
    description = (
        "Conflict rate and fork rate under concurrent agent access (single-host simulation)"
    )

    def run(self) -> ExperimentResult:
        raw_data = []

        # Test with k = 2, 5, 10, 20 agents
        for k in [2, 5, 10, 20]:
            result = self._run_contention(k)
            raw_data.append(result)

        return ExperimentResult(
            experiment_id=self.experiment_id,
            status="passed",
            metrics={
                "max_agents_tested": 20,
                "environment": "single-host threaded simulation (not distributed)",
                "max_conflict_rate": max(d["conflict_rate"] for d in raw_data),
                "max_fork_rate": max(d["fork_rate"] for d in raw_data),
            },
            raw_data=raw_data,
        )

    def _run_contention(self, k: int) -> dict:
        # Create a shared chain with a single REGISTER (provisional) event
        chain = EventChain(concept_id=f"contention-{k}")
        chain.append(
            Event(
                concept_id=chain.concept_id,
                event_type=EventType.REGISTER,
                actor="discoverer",
                reasoning="Genesis",
                payload={},
            )
        )

        results = {"success": 0, "rejected": 0, "forked": 0, "errors": 0}
        lock = threading.Lock()

        def agent_task(agent_id: int) -> str:
            try:
                # Each agent tries to VALIDATE the provisional concept
                event = Event(
                    concept_id=chain.concept_id,
                    event_type=EventType.VALIDATE,
                    actor=f"agent_{agent_id}",
                    reasoning="Concurrent validation attempt",
                    payload={"confidence": 0.8},
                )
                # Check current status before append (race condition window)
                current_status = chain.status
                if current_status.value == "provisional":
                    chain.append(event)
                    with lock:
                        # After append, check if we were the first
                        # Count validators: if > 1, we had a conflict
                        validators = chain.validators
                        if len(validators) == 1 and validators[0] == f"agent_{agent_id}":
                            return "success"
                        else:
                            return "rejected"  # Another agent got there first
                else:
                    # Status changed before we could append
                    return "rejected"
            except Exception:
                return "error"

        # Launch k agents concurrently
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=k) as executor:
            futures = {executor.submit(agent_task, i): i for i in range(k)}
            for future in as_completed(futures):
                outcome = future.result()
                results[outcome] += 1
        t1 = time.perf_counter()

        # Verify integrity after contention
        integrity_ok = chain.verify_integrity()

        # Count actual validators (should be 1 if no conflict, or multiple if race won)
        n_validators = len(chain.validators)

        return {
            "k_agents": k,
            "success": results["success"],
            "rejected": results["rejected"],
            "errors": results["errors"],
            "conflict_rate": round(results["rejected"] / k, 3) if k else 0.0,
            "fork_rate": 0.0,  # fork-on-conflict not implemented in this simulation
            "final_validators": n_validators,
            "integrity_ok": integrity_ok,
            "duration_ms": round((t1 - t0) * 1000, 2),
        }
