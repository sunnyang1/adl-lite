"""E32: Evidence-weighted confidence vs plain G-Counter under adversarial validation.

Motivation (docs/design/execution-attestation.md §7.1): the confidence
G-Counter takes the max VALIDATE confidence at face value; a coalition of
overconfident validators can inflate any paper capability. The
evidence-weighted variant (``attested_confidence``) discounts VALIDATE events
that lack distinct-scope attestation backing — WITHOUT breaking CRDT
monotonicity (D3).

Setup (deterministic, seeded, no LLM):
- N capabilities; ground truth: ``works`` (True) or ``broken`` (False).
- Every capability accumulates VALIDATE events claiming confidence ~0.9
  (adversarial: broken capabilities get equally confident validations).
- Working capabilities receive ≥2 distinct-scope replay confirms; broken ones
  receive none (lazy validators never actually ran them).
- Compare each estimator's confidence against ground truth:
  - G-Counter: chain.confidence (max VALIDATE)
  - Evidence-weighted: attested_confidence(chain, index)
- Metric: Brier score (mean squared error vs ground-truth 0/1), lower better.
"""

from __future__ import annotations

import random

from adl_lite.attestation import AttestationIndex, AttestationValidator, attested_confidence
from adl_lite.execution_log import ExecutionLog
from adl_lite.ld_proof import generate_keypair
from adl_lite.models import Event, EventChain, EventType

from .base import BaseExperiment, ExperimentResult
from .registry import register

N_CAPABILITIES = 200
P_BROKEN = 0.4
VALIDATOR_COUNT = 4
SCOPES = ["scope/org-b", "scope/org-c"]


def _validate_events(chain: EventChain, cap_id: str, confidence: float, rng: random.Random) -> None:
    chain.append(Event(concept_id=cap_id, event_type=EventType.REGISTER, actor="d", payload={}))
    for v in range(VALIDATOR_COUNT):
        # Adversarial overconfidence: broken capabilities get the same ~0.9.
        conf = min(1.0, max(0.0, confidence + rng.uniform(-0.05, 0.05)))
        chain.append(
            Event(
                concept_id=cap_id,
                event_type=EventType.VALIDATE,
                actor=f"validator-{v}",
                payload={"confidence": round(conf, 3)},
            )
        )


def _attest_events(cap_id: str, execution_id: str) -> list[Event]:
    return [
        Event(
            concept_id=cap_id,
            event_type=EventType.ATTEST,
            actor=f"attester-{j}",
            payload={
                "subject_execution": execution_id,
                "method": "replay",
                "verdict": "confirm",
                "scope": SCOPES[j % len(SCOPES)],
                "replay": {
                    "input_commitment": "sha256:sim",
                    "output_commitment": "sha256:sim",
                    "match": True,
                    "tolerance": "exact",
                },
                "evidence_ref": None,
            },
        )
        for j in range(2)
    ]


@register("E32")
class E32EvidenceWeightedConfidence(BaseExperiment):
    experiment_id = "E32"
    name = "Evidence-weighted confidence vs G-Counter (adversarial)"
    description = (
        "Brier-score comparison of attested_confidence vs plain G-Counter "
        "when validators are adversarially overconfident on broken capabilities"
    )

    def run(self) -> ExperimentResult:
        rng = random.Random(32)
        key = generate_keypair()

        gcounter_sq_err = 0.0
        weighted_sq_err = 0.0
        discounted_count = 0

        for i in range(N_CAPABILITIES):
            cap_id = f"cap-{i:04d}"
            broken = rng.random() < P_BROKEN
            truth = 0.0 if broken else 1.0

            chain = EventChain(cap_id)
            _validate_events(chain, cap_id, confidence=0.9, rng=rng)

            # Executions + attestations only exist for working capabilities:
            # broken ones never produce independent replay confirms.
            log = ExecutionLog(cap_id)
            receipt = log.record(
                executor=f"executor-{i}",
                input_commitment="sha256:sim",
                output_commitment="sha256:sim",
                private_key=key,
            )
            attest_events = (
                [] if broken else _attest_events(cap_id, receipt.payload["execution_id"])
            )
            index = AttestationIndex(attest_events, validator=AttestationValidator(log))

            gc = chain.confidence
            aw = attested_confidence(chain, index)
            if aw < gc:
                discounted_count += 1
            gcounter_sq_err += (gc - truth) ** 2
            weighted_sq_err += (aw - truth) ** 2

        g_brier = gcounter_sq_err / N_CAPABILITIES
        w_brier = weighted_sq_err / N_CAPABILITIES
        improvement = (g_brier - w_brier) / max(g_brier, 1e-9)

        metrics = {
            "n_capabilities": N_CAPABILITIES,
            "p_broken": P_BROKEN,
            "gcounter_brier": round(g_brier, 4),
            "evidence_weighted_brier": round(w_brier, 4),
            "brier_improvement_pct": round(improvement * 100, 1),
            "capabilities_discounted": discounted_count,
        }
        # Evidence weighting must strictly improve calibration under adversarial
        # validation, and never INCREASE any confidence above the G-Counter.
        ok = w_brier < g_brier and discounted_count > 0
        return ExperimentResult(
            experiment_id="E32",
            status="passed" if ok else "failed",
            metrics=metrics,
            raw_data=[
                {"estimator": "g_counter", "brier": round(g_brier, 4)},
                {"estimator": "evidence_weighted", "brier": round(w_brier, 4)},
            ],
        )
