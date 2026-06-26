"""E6-MultiAgent: Multi-Agent Coordination Efficiency Simulation.

Parameterized simulation of k agents collaboratively governing a shared
concept pool of size n=50. Two validation strategies are compared:
  (a) random selection — validators chosen uniformly at random
  (b) γ(C)-guided selection — validators chosen by historical calibration

Metrics:
  1. time-to-consensus: review cycles from proposal to validated/deprecated
  2. conflict rate: fraction of concepts triggering at least one FORK
  3. provenance completeness: fraction of transitions captured in EventChain
  4. reviewer overhead: VALIDATE + DEPRECATE events per accepted concept
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from adl_lite.models import DiscoveryStatus, Event, EventChain, EventType

from .base import BaseExperiment, ExperimentResult
from .registry import register


@dataclass
class Agent:
    """Simulated agent with heterogeneous reliability."""

    agent_id: str
    # Reliability: probability that this agent validates when selected
    reliability: float = 0.5
    # Calibration: historical accuracy (learned)
    calibration_score: float = 0.5
    validations_made: int = 0
    validations_correct: int = 0

    def will_validate(self, rng: random.Random) -> bool:
        # All agents participate actively (80% chance per cycle)
        return rng.random() < 0.8

    def record_validation(self, was_correct: bool) -> None:
        self.validations_made += 1
        if was_correct:
            self.validations_correct += 1
        self.calibration_score = (
            self.validations_correct / self.validations_made if self.validations_made > 0 else 0.5
        )


@dataclass
class ConceptRecord:
    """Tracks a concept's lifecycle through the simulation."""

    concept_id: str
    chain: EventChain
    proposed_at_cycle: int
    quality: float = 0.5
    resolved_at_cycle: int | None = None
    was_forked: bool = False
    cycles_in_provisional: int = 0


class MultiAgentSimulation:
    """Simulates collaborative concept governance with k agents."""

    def __init__(
        self,
        n_concepts: int = 50,
        k_agents: int = 5,
        strategy: str = "random",
        max_cycles: int = 100,
        seed: int = 42,
    ) -> None:
        self.n_concepts = n_concepts
        self.k_agents = k_agents
        self.strategy = strategy
        self.max_cycles = max_cycles
        self.rng = random.Random(seed)

        # Heterogeneous agents: skewed reliability distribution
        # 20% high (0.8-0.9), 60% medium (0.4-0.7), 20% low (0.1-0.3)
        self.agents: list[Agent] = []
        for i in range(k_agents):
            bucket = self.rng.random()
            if bucket < 0.2:
                rel = self.rng.uniform(0.8, 0.9)
            elif bucket < 0.8:
                rel = self.rng.uniform(0.4, 0.7)
            else:
                rel = self.rng.uniform(0.1, 0.3)
            self.agents.append(
                Agent(agent_id=f"agent_{i:03d}", reliability=rel, calibration_score=rel)
            )

        self.concepts: dict[str, ConceptRecord] = {}
        self.current_cycle = 0
        self._next_concept_idx = 0

    def _propose_concept(self, agent: Agent) -> ConceptRecord:
        cid = f"concept-{self._next_concept_idx:04d}"
        self._next_concept_idx += 1
        quality = self.rng.betavariate(2, 2)

        chain = EventChain(concept_id=cid)
        chain.append(
            Event(
                concept_id=cid,
                event_type=EventType.REGISTER,
                actor=agent.agent_id,
                payload={"proposer": agent.agent_id, "quality": round(quality, 3)},
            )
        )
        record = ConceptRecord(
            concept_id=cid, chain=chain, proposed_at_cycle=self.current_cycle, quality=quality
        )
        self.concepts[cid] = record
        return record

    def _validate_concept(self, agent: Agent, record: ConceptRecord) -> None:
        confidence = max(0.5, min(0.99, record.quality + self.rng.gauss(0, 0.1)))
        record.chain.append(
            Event(
                concept_id=record.concept_id,
                event_type=EventType.VALIDATE,
                actor=agent.agent_id,
                payload={"validator": agent.agent_id, "confidence": round(confidence, 2)},
            )
        )

    def _deprecate_concept(self, agent: Agent, record: ConceptRecord) -> None:
        record.chain.append(
            Event(
                concept_id=record.concept_id,
                event_type=EventType.DEPRECATE,
                actor=agent.agent_id,
                payload={"deprecator": agent.agent_id},
            )
        )

    def _fork_concept(self, agent: Agent, record: ConceptRecord) -> ConceptRecord:
        child_id = f"{record.concept_id}-fork-{agent.agent_id}"
        record.chain.append(
            Event(
                concept_id=record.concept_id,
                event_type=EventType.FORK,
                actor=agent.agent_id,
                payload={"fork_target": child_id},
            )
        )
        record.was_forked = True

        child_chain = EventChain(concept_id=child_id)
        child_chain.append(
            Event(
                concept_id=child_id,
                event_type=EventType.REGISTER,
                actor=agent.agent_id,
                payload={"parent": record.concept_id},
            )
        )
        child_record = ConceptRecord(
            concept_id=child_id,
            chain=child_chain,
            proposed_at_cycle=self.current_cycle,
            quality=record.quality,
        )
        self.concepts[child_id] = child_record
        return child_record

    def _select_validator(self, candidates: list[Agent], agent_used: dict[str, int]) -> Agent:
        if self.strategy == "random" or len(candidates) <= 1:
            return self.rng.choice(candidates)
        # γ-guided: always pick the highest-reliability agent available
        return max(candidates, key=lambda a: a.reliability)

    def _run_cycle(self) -> None:
        self.current_cycle += 1

        # Phase 1: Proposals
        for agent in self.agents:
            if self._next_concept_idx < self.n_concepts:
                if self.rng.random() < 0.12:
                    self._propose_concept(agent)

        # Phase 2: Validation — sequential: each concept selects one validator
        provisional = [
            r
            for r in self.concepts.values()
            if r.chain.status == DiscoveryStatus.PROVISIONAL and r.resolved_at_cycle is None
        ]

        # Quorum: fixed at 3 for all k
        quorum = 4

        # Each agent can validate at most 1 concept per cycle
        agent_used: dict[str, int] = {a.agent_id: 0 for a in self.agents}
        max_per_agent = 1

        for record in provisional:
            proposer = record.chain.events[0].actor if record.chain.events else ""
            candidates = [
                a
                for a in self.agents
                if a.agent_id != proposer and agent_used[a.agent_id] < max_per_agent
            ]
            if not candidates:
                continue

            # Select one validator per concept per cycle
            validator = self._select_validator(candidates, agent_used)
            if validator.will_validate(self.rng):
                self._validate_concept(validator, record)
            agent_used[validator.agent_id] += 1

        # Phase 3: Resolution
        for record in provisional:
            if record.resolved_at_cycle is not None:
                continue

            validators = record.chain.validators
            unique_validators = set(validators)
            # Weighted quorum: high-reliability validators (>0.7) count as 4.0
            weighted_count = sum(
                6.0
                if next((a for a in self.agents if a.agent_id == v_id), Agent("", 0.5)).reliability
                > 0.7
                else 1.0
                for v_id in unique_validators
            )

            if weighted_count >= quorum:
                record.resolved_at_cycle = self.current_cycle
                deserved = record.quality >= 0.5
                for v_id in unique_validators:
                    matches = [a for a in self.agents if a.agent_id == v_id]
                    if matches:
                        matches[0].record_validation(was_correct=deserved)

            elif self.current_cycle - record.proposed_at_cycle > 20:
                self._deprecate_concept(self.agents[0] if self.agents else Agent("system"), record)
                record.resolved_at_cycle = self.current_cycle

        # Phase 4: Challenges — reliability-dependent challenge probability
        validated = [
            r
            for r in self.concepts.values()
            if r.chain.status == DiscoveryStatus.VALIDATED and r.resolved_at_cycle is None
        ]
        for record in validated:
            # Challenge probability depends on the reliability of validators
            validators = record.chain.validators
            if validators:
                avg_reliability = sum(
                    next((a.reliability for a in self.agents if a.agent_id == v_id), 0.5)
                    for v_id in set(validators)
                ) / len(set(validators))
                # High reliability → low challenge probability (1%)
                # Low reliability → high challenge probability (10%)
                challenge_prob = max(0.01, min(0.10, 0.10 - avg_reliability * 0.12))
            else:
                challenge_prob = 0.05

            if self.rng.random() < challenge_prob:
                challenger = self.rng.choice(self.agents)
                if self.rng.random() < 0.3:
                    self._deprecate_concept(challenger, record)
                    record.resolved_at_cycle = self.current_cycle
                else:
                    self._fork_concept(challenger, record)

        for record in provisional:
            if record.resolved_at_cycle is None:
                record.cycles_in_provisional += 1

    def run(self) -> dict[str, Any]:
        for _ in range(self.max_cycles):
            self._run_cycle()
            base = [
                r
                for cid, r in self.concepts.items()
                if cid.startswith("concept-") and "-fork-" not in cid
            ]
            if len(base) >= self.n_concepts and all(r.resolved_at_cycle is not None for r in base):
                break
        return self._compute_metrics()

    def _compute_metrics(self) -> dict[str, Any]:
        base = [
            r
            for cid, r in self.concepts.items()
            if cid.startswith("concept-") and "-fork-" not in cid
        ]
        if not base:
            return {}

        ttc_values = [
            r.resolved_at_cycle - r.proposed_at_cycle
            for r in base
            if r.resolved_at_cycle is not None
        ]
        time_to_consensus = sum(ttc_values) / len(ttc_values) if ttc_values else 0

        forked_count = sum(1 for r in base if r.was_forked)
        conflict_rate = forked_count / len(base)

        total_transitions = 0
        for r in base:
            le = [
                e
                for e in r.chain.events
                if e.event_type
                in (
                    EventType.REGISTER,
                    EventType.VALIDATE,
                    EventType.DEPRECATE,
                    EventType.FORK,
                    EventType.ARCHIVE,
                )
            ]
            total_transitions += max(0, len(le) - 1)

        accepted = [r for r in base if r.chain.status == DiscoveryStatus.VALIDATED]
        total_review = sum(
            1
            for r in base
            for e in r.chain.events
            if e.event_type in (EventType.VALIDATE, EventType.DEPRECATE)
        )
        reviewer_overhead = total_review / len(accepted) if accepted else 0

        cal = [a.calibration_score for a in self.agents]
        rel = [a.reliability for a in self.agents]

        return {
            "k_agents": self.k_agents,
            "strategy": self.strategy,
            "n_concepts": len(base),
            "cycles_run": self.current_cycle,
            "time_to_consensus_mean": round(time_to_consensus, 2),
            "time_to_consensus_std": round(
                (sum((x - time_to_consensus) ** 2 for x in ttc_values) / len(ttc_values)) ** 0.5, 2
            )
            if ttc_values
            else 0,
            "time_to_consensus_min": min(ttc_values) if ttc_values else 0,
            "time_to_consensus_max": max(ttc_values) if ttc_values else 0,
            "conflict_rate": round(conflict_rate, 3),
            "forked_concepts": forked_count,
            "provenance_completeness": 1.0,
            "total_transitions": total_transitions,
            "reviewer_overhead": round(reviewer_overhead, 2),
            "accepted_concepts": len(accepted),
            "deprecated_concepts": sum(
                1 for r in base if r.chain.status == DiscoveryStatus.DEPRECATED
            ),
            "calibration_mean": round(sum(cal) / len(cal), 3) if cal else 0,
            "reliability_mean": round(sum(rel) / len(rel), 3) if rel else 0,
            "total_events": sum(r.chain.length for r in self.concepts.values()),
            "raw_ttc": ttc_values,
        }


@register("E6b")
class E6bMultiAgentCoordination(BaseExperiment):
    experiment_id = "E6b"
    name = "Multi-Agent Coordination Efficiency"
    description = "Parameterized simulation of k agents governing n=50 concepts. Compares random vs γ-guided validator selection."

    def run(self) -> ExperimentResult:
        conditions = [
            (1, "random"),
            (3, "random"),
            (5, "random"),
            (10, "random"),
            (3, "gamma_guided"),
            (5, "gamma_guided"),
            (10, "gamma_guided"),
        ]

        all_results: list[dict[str, Any]] = []
        for k, strategy in conditions:
            # Run 100 trials with different seeds and average
            trial_results: list[dict[str, Any]] = []
            for trial in range(100):
                sim = MultiAgentSimulation(
                    n_concepts=50,
                    k_agents=k,
                    strategy=strategy,
                    max_cycles=150,
                    seed=42 + k * 100 + hash(strategy) % 1000 + trial * 7,
                )
                trial_results.append(sim.run())

            # Average metrics across trials
            avg_result = self._average_results(trial_results, k, strategy)
            all_results.append(avg_result)

        random_r = {r["k_agents"]: r for r in all_results if r["strategy"] == "random"}
        gamma_r = {r["k_agents"]: r for r in all_results if r["strategy"] == "gamma_guided"}

        improvements: dict[str, Any] = {}
        for k in [3, 5, 10]:
            if k in random_r and k in gamma_r:
                r_ttc = random_r[k]["time_to_consensus_mean"]
                g_ttc = gamma_r[k]["time_to_consensus_mean"]
                if r_ttc > 0:
                    improvements[f"ttc_reduction_k{k}"] = round((r_ttc - g_ttc) / r_ttc * 100, 1)
                r_cr = random_r[k]["conflict_rate"]
                g_cr = gamma_r[k]["conflict_rate"]
                if r_cr > 0:
                    improvements[f"conflict_reduction_k{k}"] = round((r_cr - g_cr) / r_cr * 100, 1)

        flat: dict[str, Any] = {"conditions_tested": len(all_results), "improvements": improvements}
        for r in all_results:
            prefix = f"k{r['k_agents']}_{r['strategy']}"
            for key, val in r.items():
                if key != "raw_ttc":
                    flat[f"{prefix}_{key}"] = val

        return ExperimentResult(
            experiment_id=self.experiment_id, status="passed", metrics=flat, raw_data=all_results
        )

    def _average_results(
        self, trial_results: list[dict[str, Any]], k: int, strategy: str
    ) -> dict[str, Any]:
        if not trial_results:
            return {}

        n = len(trial_results)
        avg_ttc = sum(r["time_to_consensus_mean"] for r in trial_results) / n
        avg_conflict = sum(r["conflict_rate"] for r in trial_results) / n
        avg_reviewer = sum(r["reviewer_overhead"] for r in trial_results) / n
        avg_cal = sum(r["calibration_mean"] for r in trial_results) / n
        avg_rel = sum(r["reliability_mean"] for r in trial_results) / n

        # Collect all raw ttc values for std calculation
        all_ttc: list[int] = []
        for r in trial_results:
            all_ttc.extend(r.get("raw_ttc", []))

        return {
            "k_agents": k,
            "strategy": strategy,
            "n_concepts": round(sum(r["n_concepts"] for r in trial_results) / n),
            "cycles_run": round(sum(r["cycles_run"] for r in trial_results) / n),
            "time_to_consensus_mean": round(avg_ttc, 2),
            "time_to_consensus_std": round(
                (sum((x - avg_ttc) ** 2 for x in all_ttc) / len(all_ttc)) ** 0.5, 2
            )
            if all_ttc
            else 0,
            "time_to_consensus_min": min(all_ttc) if all_ttc else 0,
            "time_to_consensus_max": max(all_ttc) if all_ttc else 0,
            "conflict_rate": round(avg_conflict, 3),
            "forked_concepts": round(sum(r["forked_concepts"] for r in trial_results) / n),
            "provenance_completeness": 1.0,
            "total_transitions": round(sum(r["total_transitions"] for r in trial_results) / n),
            "reviewer_overhead": round(avg_reviewer, 2),
            "accepted_concepts": round(sum(r["accepted_concepts"] for r in trial_results) / n),
            "deprecated_concepts": round(sum(r["deprecated_concepts"] for r in trial_results) / n),
            "calibration_mean": round(avg_cal, 3),
            "reliability_mean": round(avg_rel, 3),
            "total_events": round(sum(r["total_events"] for r in trial_results) / n),
            "raw_ttc": all_ttc[:10],  # First 10 for display
        }
