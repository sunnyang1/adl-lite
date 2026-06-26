"""E28: 10K concurrent-agent contention.

10,000 logical agents append events to a shared pool of EventChains.  This
exercises the Phase 3 split-lock design under high contention and verifies
that integrity holds with zero data races.
"""

from __future__ import annotations

import random
import time
from concurrent.futures import ThreadPoolExecutor

from adl_lite.models import Event, EventChain, EventType

from .base import BaseExperiment, ExperimentResult
from .registry import register


@register("E28")
class E28TenKConcurrency(BaseExperiment):
    experiment_id = "E28"
    name = "10K Concurrent Agent Contention"
    description = (
        "10,000 logical agents concurrently append to shared EventChains; "
        "measures throughput and integrity under split-lock contention."
    )

    N_CHAINS = 100
    N_AGENTS = 10_000
    EVENTS_PER_AGENT = 10
    MAX_WORKERS = 512
    TARGET_INTEGRITY_RATE = 1.0
    TARGET_THROUGHPUT_EPS = 10_000.0

    def run(self) -> ExperimentResult:
        random.seed(42)
        cids = [f"concept-{i:03d}" for i in range(self.N_CHAINS)]
        chains: dict[str, EventChain] = {}
        for cid in cids:
            c = EventChain(concept_id=cid)
            c.append(
                Event(
                    concept_id=cid,
                    event_type=EventType.REGISTER,
                    actor="system",
                    reasoning="genesis",
                )
            )
            chains[cid] = c

        errors: list[str] = []

        def worker(agent_id: int) -> None:
            rng = random.Random(agent_id)
            for _ in range(self.EVENTS_PER_AGENT):
                cid = rng.choice(cids)
                chain = chains[cid]
                try:
                    chain.append(
                        Event(
                            concept_id=cid,
                            event_type=EventType.EVIDENCE,
                            actor=f"agent-{agent_id}",
                            reasoning=f"agent-{agent_id} evidence",
                            payload={"seq": rng.randint(0, 2**30)},
                        )
                    )
                except Exception as exc:  # pragma: no cover
                    errors.append(str(exc))

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            list(executor.map(worker, range(self.N_AGENTS)))
        t1 = time.perf_counter()

        duration = t1 - t0
        total_events = self.N_AGENTS * self.EVENTS_PER_AGENT
        throughput_eps = total_events / duration if duration > 0 else 0.0

        ok_count = 0
        lengths: list[int] = []
        for _cid, chain in chains.items():
            lengths.append(len(chain))
            if chain.verify_integrity():
                ok_count += 1

        integrity_rate = ok_count / self.N_CHAINS
        min_len = min(lengths)
        max_len = max(lengths)
        expected = 1 + (total_events // self.N_CHAINS)
        # Allow ±20% scheduling variance across shared chains.
        distribution_ok = min_len >= int(expected * 0.8) and max_len <= int(expected * 1.2)

        passes = (
            integrity_rate >= self.TARGET_INTEGRITY_RATE
            and throughput_eps >= self.TARGET_THROUGHPUT_EPS
            and distribution_ok
            and not errors
        )

        print("\nE28: 10K Concurrent Agent Contention")
        print(
            f"Agents: {self.N_AGENTS}, Chains: {self.N_CHAINS}, Events/agent: {self.EVENTS_PER_AGENT}"
        )
        print(f"Duration: {duration:.3f} s")
        print(f"Throughput: {throughput_eps:,.0f} events/s")
        print(f"Integrity rate: {integrity_rate:.2f}")
        print(f"Chain length range: {min_len} - {max_len}")
        print(f"Status: {'PASS' if passes else 'PARTIAL' if integrity_rate == 1.0 else 'FAIL'}")

        return ExperimentResult(
            experiment_id=self.experiment_id,
            status="passed" if passes else "partial" if integrity_rate == 1.0 else "failed",
            metrics={
                "agents": self.N_AGENTS,
                "chains": self.N_CHAINS,
                "events_per_agent": self.EVENTS_PER_AGENT,
                "total_events": total_events,
                "duration_s": round(duration, 3),
                "throughput_eps": round(throughput_eps, 0),
                "integrity_rate": round(integrity_rate, 2),
                "min_chain_length": min_len,
                "max_chain_length": max_len,
                "distribution_ok": distribution_ok,
                "worker_errors": len(errors),
            },
            raw_data=[
                {
                    "concept_id": cid,
                    "chain_length": len(c),
                    "integrity": c.verify_integrity(),
                }
                for cid, c in chains.items()
            ],
            errors=errors[:10],
        )
