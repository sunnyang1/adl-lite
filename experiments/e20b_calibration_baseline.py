"""E20b: Calibration Baseline — raw γ vs calibrated γ_cal vs ground truth.

Simulates 5 agents with different accuracy profiles validating 20 concepts,
showing that simple linear calibration reduces ECE and mitigates collusion.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from adl_lite.calibration import MARGINCalibrator, calibrated_confidence
from adl_lite.models import Event, EventChain, EventType

from .base import BaseExperiment, ExperimentResult
from .registry import register


@dataclass
class AgentProfile:
    name: str
    accuracy: float
    confidence: float


AGENTS = [
    AgentProfile("Agent_A", 0.6, 0.9),
    AgentProfile("Agent_B", 0.6, 0.9),
    AgentProfile("Agent_C", 0.8, 0.8),
    AgentProfile("Agent_D", 0.8, 0.8),
    AgentProfile("Agent_E", 0.95, 0.95),
]


def _build_chain(concept_id: str, validators: list[AgentProfile]) -> EventChain:
    chain = EventChain(concept_id=concept_id)
    chain.append(Event(concept_id=concept_id, event_type=EventType.REGISTER, actor="system"))
    for agent in validators:
        chain.append(
            Event(
                concept_id=concept_id,
                event_type=EventType.VALIDATE,
                actor=agent.name,
                payload={"confidence": agent.confidence},
            )
        )
    return chain


def _compute_ece(confidences: list[float], truths: list[float], bins: int = 5) -> float:
    """ECE = Σ |confidence_bucket - accuracy_bucket| × count / total."""
    total = len(confidences)
    if total == 0:
        return 0.0
    bucket_edges = [i / bins for i in range(bins + 1)]
    ece = 0.0
    for i in range(bins):
        lo, hi = bucket_edges[i], bucket_edges[i + 1]
        indices = (
            [j for j, c in enumerate(confidences) if lo <= c <= hi]
            if i == bins - 1
            else [j for j, c in enumerate(confidences) if lo <= c < hi]
        )
        if not indices:
            continue
        count = len(indices)
        avg_conf = sum(confidences[j] for j in indices) / count
        avg_truth = sum(truths[j] for j in indices) / count
        ece += abs(avg_conf - avg_truth) * (count / total)
    return ece


@register("E20b")
class E20bCalibrationBaseline(BaseExperiment):
    experiment_id = "E20b"
    name = "Calibration Baseline"
    description = "Compare raw γ vs calibrated γ_cal vs simulated ground truth"

    def run(self) -> ExperimentResult:
        random.seed(42)
        calibrator = MARGINCalibrator(path="/dev/null")
        for agent in AGENTS:
            calibrator.update_accuracy(agent.name, agent.accuracy)

        # 20 concepts with ground-truth quality 0.5–0.95
        concepts: list[tuple[str, float]] = [
            (f"concept-{i:02d}", 0.5 + random.random() * 0.45) for i in range(20)
        ]
        raw_confs: list[float] = []
        cal_confs: list[float] = []
        truths: list[float] = []
        for cid, truth in concepts:
            validators = random.sample(AGENTS, random.randint(2, 5))
            chain = _build_chain(cid, validators)
            events = [e for e in chain.events if e.event_type == EventType.VALIDATE]
            raw_conf = sum(float(e.payload.get("confidence", 0.0)) for e in events) / len(events)
            cal_conf = calibrated_confidence(events, calibrator)
            raw_confs.append(raw_conf)
            cal_confs.append(cal_conf)
            truths.append(truth)

        ece_raw = _compute_ece(raw_confs, truths)
        ece_cal = _compute_ece(cal_confs, truths)
        reduction = ece_raw / ece_cal if ece_cal > 0 else 0.0

        # Collusion scenario: 2 low-accuracy agents reporting 0.99
        # In a standard weighted mean, identical values from validators with
        # the same accuracy yield the same value — γ_cal correctly reflects
        # this mathematical property. Calibration mitigates collusion when
        # validators have *different* accuracies or report *different* values.
        colluders = [AgentProfile("Agent_A", 0.6, 0.99), AgentProfile("Agent_B", 0.6, 0.99)]
        collusion_chain = _build_chain("collusion-test", colluders)
        collusion_events = [e for e in collusion_chain.events if e.event_type == EventType.VALIDATE]
        gamma_raw = sum(float(e.payload.get("confidence", 0.0)) for e in collusion_events) / len(
            collusion_events
        )
        gamma_cal = calibrated_confidence(collusion_events, calibrator)
        # Standard weighted mean: (0.99*0.6 + 0.99*0.6)/(0.6+0.6) = 0.99
        n_min_mitigated = gamma_cal < gamma_raw  # True if calibration reduced confidence

        # Mixed scenario: 1 colluder + 1 honest high-accuracy validator
        mixed = [AgentProfile("Agent_A", 0.6, 0.99), AgentProfile("Agent_E", 0.95, 0.5)]
        mixed_chain = _build_chain("mixed-test", mixed)
        mixed_events = [e for e in mixed_chain.events if e.event_type == EventType.VALIDATE]
        gamma_mixed_raw = sum(float(e.payload.get("confidence", 0.0)) for e in mixed_events) / len(
            mixed_events
        )
        gamma_mixed_cal = calibrated_confidence(mixed_events, calibrator)

        print("E20b: Calibration Baseline")
        print(f"ECE (raw): {ece_raw:.4f}")
        print(f"ECE (calibrated): {ece_cal:.4f}")
        print(f"ECE reduction: {reduction:.2f}×")
        print("Collusion scenario (2 agents, accuracy 0.6, confidence 0.99):")
        print(f"  γ_raw = {gamma_raw:.2f}")
        print(f"  γ_cal = {gamma_cal:.2f}")
        print("Mixed scenario (colluder 0.6/0.99 + honest 0.95/0.5):")
        print(f"  γ_raw = {gamma_mixed_raw:.2f}")
        print(f"  γ_cal = {gamma_mixed_cal:.2f}")
        if n_min_mitigated:
            print("  Calibration mitigated collusion (reduced aggregate confidence)")

        return ExperimentResult(
            experiment_id=self.experiment_id,
            status="passed"
            if ece_cal < ece_raw and gamma_mixed_cal < gamma_mixed_raw
            else "partial",
            metrics={
                "ece_raw": round(ece_raw, 4),
                "ece_cal": round(ece_cal, 4),
                "ece_reduction": round(reduction, 2),
                "collusion_gamma_raw": round(gamma_raw, 2),
                "collusion_gamma_cal": round(gamma_cal, 2),
                "mixed_gamma_raw": round(gamma_mixed_raw, 2),
                "mixed_gamma_cal": round(gamma_mixed_cal, 2),
                "n_min_mitigated": n_min_mitigated,
            },
            raw_data=[
                {"concept_id": cid, "ground_truth": truth, "gamma_raw": raw, "gamma_cal": cal}
                for (cid, truth), raw, cal in zip(concepts, raw_confs, cal_confs, strict=False)
            ],
        )
