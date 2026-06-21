"""E14: Colluding validators attack (negative-result / vulnerability demo).

Demonstrates that the current γ(C) function is vulnerable to a coalition of
validators who collude to drive confidence to 1.0.  This is a *known design
limitation* (not a bug) scoped to Phase 1, but the experiment quantifies the
exact attack cost.
"""

from __future__ import annotations

from adl_lite.models import Event, EventChain, EventType

from .base import BaseExperiment, ExperimentResult
from .registry import register


@register("E14")
class E14ColludingValidators(BaseExperiment):
    experiment_id = "E14"
    name = "Colluding validators attack"
    description = "Quantify confidence manipulation by colluding validator coalitions"

    def run(self) -> ExperimentResult:
        raw_data = []

        # Build a base chain with a single REGISTER event
        chain = EventChain(concept_id="collusion-test")
        chain.append(
            Event(
                concept_id="collusion-test",
                event_type=EventType.REGISTER,
                actor="discoverer",
                reasoning="Genesis",
                payload={},
            )
        )

        base_confidence = chain.confidence  # 0.0 (no validators yet)

        # Simulate colluding coalitions of size k = 1..15
        for k in range(1, 16):
            # Fresh chain copy for each k (start from genesis)
            test_chain = EventChain(concept_id=f"collusion-{k}")
            test_chain.append(
                Event(
                    concept_id=f"collusion-{k}",
                    event_type=EventType.REGISTER,
                    actor="discoverer",
                    reasoning="Genesis",
                    payload={},
                )
            )

            # Each colluding validator reports confidence=0.99
            for i in range(k):
                test_chain.append(
                    Event(
                        concept_id=f"collusion-{k}",
                        event_type=EventType.VALIDATE,
                        actor=f"colluder_{i}",
                        reasoning="Collusion",
                        payload={"confidence": 0.99},
                    )
                )

            raw_data.append(
                {
                    "coalition_size": k,
                    "final_confidence": round(test_chain.confidence, 4),
                    "status": test_chain.status.value,
                    "validators": test_chain.validators,
                }
            )

        # Find the minimum coalition size that drives confidence to 1.0
        max_conf = max(d["final_confidence"] for d in raw_data)
        min_k_for_max = next(
            d["coalition_size"] for d in raw_data if d["final_confidence"] == max_conf
        )

        return ExperimentResult(
            experiment_id=self.experiment_id,
            status="passed",
            metrics={
                "base_confidence": base_confidence,
                "max_achievable_confidence": max_conf,
                "min_coalition_for_max": min_k_for_max,
                "vulnerable": True,
                "mitigation": "Phase 3: MARGIN calibration + staking-based validation (FW3/FW9)",
            },
            raw_data=raw_data,
        )
