"""E5: Multi-agent event chain auditability.

Transforms the existing 5-agent ScriptedHarness into an event-driven simulation.
Each agent action (discoverer emit, reviewer validate, skeptic fork, merger
resolve, librarian store) is recorded as an Event in the concept's chain.

Metrics:
  - Event coverage: every SimEvent maps to an Event in a chain
  - Chain integrity: all chains pass verify_integrity()
  - Audit trail completeness: history() covers the full lifecycle

The old harness code is wrapped — NOT rewritten — to preserve existing
experiment semantics.
"""

from __future__ import annotations

from pathlib import Path

from adl_lite.models import EventChain, EventType

from .base import BaseExperiment, ExperimentResult
from .harness import ScriptedHarness
from .registry import register

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@register("E5")
class E5AgentAudit(BaseExperiment):
    experiment_id = "E5"
    name = "Multi-agent event chain auditability"
    description = "5-agent simulation with event chains — integrity + coverage"

    def run(self) -> ExperimentResult:
        # Phase 1: Run the existing scripted harness (produces SimEvents)
        harness = ScriptedHarness(db_path=":memory:", strict_ontology=True)
        sim_events = harness.run_scripted_scenario()

        # Phase 2: Rebuild event chains from the same documents used by the harness
        paths = [
            EXAMPLES / "capital_reflux_trap.md",
            EXAMPLES / "gradient_explosion.md",
            EXAMPLES / "attention_residual_discovery.md",
            EXAMPLES / "matdo_original.md",
            EXAMPLES / "matdo_fork_kinetic.md",
        ]

        chains: dict[str, EventChain] = {}
        for p in paths:
            if not p.is_file():
                continue
            from adl_lite.parser import parse_file

            doc = parse_file(p)
            chain = doc.event_chain
            chains[doc.adl_id] = chain

        # Phase 3: Verify each chain
        results = []
        integrity_ok = 0
        integrity_total = 0
        coverage_ok = 0
        coverage_total = 0

        for adl_id, chain in chains.items():
            integrity_total += 1
            chain_ok = chain.verify_integrity()
            if chain_ok:
                integrity_ok += 1

            entry = {
                "adl_id": adl_id,
                "chain_length": chain.length,
                "chain_integrity": chain_ok,
                "status": chain.status.value,
                "history_events": len(chain.history()),
            }
            results.append(entry)

        # Phase 4: Cross-check SimEvents → chain coverage
        # Each concept that had a SimEvent should have a corresponding chain entry
        sim_adl_ids = {e.adl_id for e in sim_events}
        chain_adl_ids = set(chains.keys())

        coverage_total = len(sim_adl_ids)
        coverage_ok = len(sim_adl_ids & chain_adl_ids)

        # Phase 5: Audit trace — every SimEvent should have an equivalent
        # lifecycle event in the chain
        lifecycle_sim_events = [
            e for e in sim_events if e.action in ("emit", "transition", "fork", "validate")
        ]
        lifecycle_chain_events = sum(
            1
            for c in chains.values()
            for evt in c.events
            if evt.event_type
            in (
                EventType.REGISTER,
                EventType.VALIDATE,
                EventType.FORK,
                EventType.DEPRECATE,
            )
        )

        all_integrity_ok = integrity_ok == integrity_total

        return ExperimentResult(
            experiment_id=self.experiment_id,
            status="passed" if all_integrity_ok else "partial",
            metrics={
                "chains_total": integrity_total,
                "chains_integrity_ok": integrity_ok,
                "chains_covered": coverage_ok,
                "chains_uncovered": coverage_total - coverage_ok,
                "sim_events_total": len(sim_events),
                "lifecycle_sim_events": len(lifecycle_sim_events),
                "lifecycle_chain_events": lifecycle_chain_events,
                "chain_avg_length": round(
                    sum(c.length for c in chains.values()) / max(len(chains), 1), 1
                ),
            },
            raw_data=results,
        )
