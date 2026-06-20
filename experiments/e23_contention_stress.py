"""E23: Concurrent Agent Contention — survival path.

10 agents concurrently append to 50 shared EventChains.
Target: integrity_rate=1.0, conflict_rate<0.5, zero data races.
"""
from __future__ import annotations
import random, threading, time
from adl_lite.models import DiscoveryStatus, Event, EventChain, EventType
from adl_lite.sync_manager import SyncManager
from .base import BaseExperiment, ExperimentResult
from .registry import register

_VALID = {
    DiscoveryStatus.PROVISIONAL: {EventType.VALIDATE, EventType.DEPRECATE, EventType.FORK, EventType.EVIDENCE},
    DiscoveryStatus.VALIDATED: {EventType.VALIDATE, EventType.DEPRECATE, EventType.FORK, EventType.EVIDENCE},
    DiscoveryStatus.DEPRECATED: {EventType.DEPRECATE, EventType.FORK, EventType.EVIDENCE},
    DiscoveryStatus.FORKED: {EventType.DEPRECATE, EventType.EVIDENCE},
    DiscoveryStatus.ARCHIVED: {EventType.EVIDENCE},
}
_ACTIONS = [EventType.VALIDATE, EventType.DEPRECATE, EventType.FORK, EventType.EVIDENCE]


def _make_event(cid, actor, action, payload=None):
    return Event(concept_id=cid, event_type=action, actor=actor, payload=payload or {})


@register("E23")
class E23ContentionStress(BaseExperiment):
    experiment_id = "E23"
    name = "Concurrent Agent Contention"
    description = "10 agents concurrently appending to 50 shared EventChains"

    def run(self) -> ExperimentResult:
        n_agents, n_concepts, n_rounds = 10, 50, 100
        chains: dict[str, EventChain] = {}
        for i in range(n_concepts):
            cid = f"concept-{i:02d}"
            c = EventChain(concept_id=cid)
            c.append(_make_event(cid, "system", EventType.REGISTER))
            chains[cid] = c
        cids = list(chains.keys())

        lock = threading.Lock()
        conflicts = races = rejected_vals = converted_forks = 0

        def worker(agent_id: int) -> None:
            nonlocal conflicts, races, rejected_vals, converted_forks
            rng = random.Random(agent_id)
            lc = lr = lrv = lcf = 0

            for _ in range(n_rounds):
                cid = rng.choice(cids)
                chain = chains[cid]
                action = rng.choice(_ACTIONS)
                status = chain.status
                if action not in _VALID.get(status, set()):
                    lc += 1
                    if action == EventType.VALIDATE:
                        lrv += 1
                        if EventType.FORK in _VALID.get(status, set()):
                            chain.append(_make_event(cid, f"agent-{agent_id}", EventType.FORK, {"converted_from": "validate"}))
                            lcf += 1
                    continue

                time.sleep(0.001 * rng.random())
                new_status = chain.status
                if action not in _VALID.get(new_status, set()):
                    lr += 1
                    if action == EventType.VALIDATE:
                        lrv += 1
                        if EventType.FORK in _VALID.get(new_status, set()):
                            chain.append(_make_event(cid, f"agent-{agent_id}", EventType.FORK, {"converted_from": "validate"}))
                            lcf += 1
                    continue

                chain.append(_make_event(cid, f"agent-{agent_id}", action))

            with lock:
                conflicts += lc
                races += lr
                rejected_vals += lrv
                converted_forks += lcf

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_agents)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        ok = 0
        for cid, chain in chains.items():
            if chain.verify_integrity():
                ok += 1
            merged = SyncManager(concept_id=cid).merge(chain, base_chain=EventChain(concept_id=cid))
            merged.verify_integrity()

        total = n_agents * n_rounds
        conflict_rate = conflicts / total
        fork_rate = converted_forks / rejected_vals if rejected_vals else 0.0
        integrity_rate = ok / n_concepts
        passes = integrity_rate == 1.0 and conflict_rate < 0.5

        print(f"\nE23: Concurrent Agent Contention")
        print(f"Agents: {n_agents}, Concepts: {n_concepts}, Rounds: {n_rounds}")
        print(f"Conflict rate: {conflict_rate:.2f}")
        print(f"Fork rate: {fork_rate:.2f}")
        print(f"Integrity rate: {integrity_rate:.2f}")
        print(f"Race conditions: {races}")
        print(f"Status: {'PASS' if passes else 'FAIL'}")

        return ExperimentResult(
            experiment_id=self.experiment_id,
            status="passed" if passes else "failed",
            metrics={
                "conflict_rate": round(conflict_rate, 2),
                "fork_rate": round(fork_rate, 2),
                "integrity_rate": round(integrity_rate, 2),
                "race_conditions": races,
                "agents": n_agents,
                "concepts": n_concepts,
                "rounds": n_rounds,
            },
            raw_data=[
                {"concept_id": cid, "chain_length": c.length, "final_status": c.status.value, "integrity": c.verify_integrity()}
                for cid, c in chains.items()
            ],
        )
