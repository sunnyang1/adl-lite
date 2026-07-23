"""E31: Lazy-validator/executor detectability with vs without the EAL.

Motivation (docs/design/execution-attestation.md §1): the registry's deepest
gap was that honest and dishonest claims cost the same. This experiment
quantifies Phase 1+2's core value proposition: independent replay turns
invisible laziness into observable refutations.

Setup (deterministic simulation, seeded RNG, no LLM):
- N capabilities; a fraction p_lazy have "lazy executors" who record EXECUTE
  receipts with fabricated output commitments (they never ran anything).
- Baseline arm (pre-EAL status quo): manual review samples a small fraction
  of capabilities and catches lazy ones only within the sample.
- EAL arm: each capability receives r independent replays from distinct
  organizational scopes; a fabricated commitment mismatches on replay →
  refute. Replay infrastructure flakes at rate ε produce `inconclusive`
  (never a false refute — honest flake handling per design §9).

Metrics: detection rate vs r, false-positive rate, replays per detection,
and cost comparison (manual review-minutes vs replay milliseconds).
"""

from __future__ import annotations

import random

from adl_lite.attestation import AttestationIndex, AttestationValidator
from adl_lite.execution_log import ExecutionLog
from adl_lite.ld_proof import generate_keypair
from adl_lite.models import Event, EventType
from adl_lite.replay import sha256_commitment

from .base import BaseExperiment, ExperimentResult
from .registry import register

N_CAPABILITIES = 200
P_LAZY = 0.3
FLAKE_RATE = 0.02
BASELINE_SAMPLE_RATE = 0.05
BASELINE_REVIEW_MINUTES_PER_CAP = 30.0
REPLAY_MS_PER_CAP = 250.0
SCOPES = ["scope/org-a", "scope/org-b", "scope/org-c"]


def _attest_event(cap_id: str, subject_id: str, verdict: str, scope: str, actor: str) -> Event:
    return Event(
        concept_id=cap_id,
        event_type=EventType.ATTEST,
        actor=actor,
        payload={
            "subject_execution": subject_id,
            "method": "replay",
            "verdict": verdict,
            "scope": scope,
            "replay": {
                "input_commitment": "sha256:sim-input",
                "output_commitment": "sha256:sim-output",
                "match": verdict == "confirm",
                "tolerance": "exact",
            },
            "evidence_ref": None,
        },
    )


@register("E31")
class E31LazyValidatorDetection(BaseExperiment):
    experiment_id = "E31"
    name = "Lazy executor detectability (EAL vs manual baseline)"
    description = (
        "Quantify detection rate / false positives / cost of catching lazy "
        "executors (fabricated receipts) via independent replay vs manual sampling"
    )

    def run(self) -> ExperimentResult:
        rng = random.Random(31)
        key = generate_keypair()

        lazy_ids: set[str] = set()
        logs: dict[str, ExecutionLog] = {}

        # --- Population: honest receipts vs fabricated receipts ----------
        for i in range(N_CAPABILITIES):
            cap_id = f"cap-{i:04d}"
            log = ExecutionLog(cap_id)
            true_commitment = sha256_commitment(f"true-output-{i}".encode())
            lazy = rng.random() < P_LAZY
            if lazy:
                lazy_ids.add(cap_id)
                # Fabricated commitment: never executed, hash of junk.
                recorded = sha256_commitment(f"fabricated-{rng.random()}".encode())
            else:
                recorded = true_commitment
            log.record(
                executor=f"executor-{i}",
                input_commitment="sha256:sim-input",
                output_commitment=recorded,
                private_key=key,
            )
            logs[cap_id] = log

        assert all(log.verify_integrity() for log in logs.values())

        # --- Baseline arm: manual sampling review ------------------------
        sampled = [cap_id for cap_id in logs if rng.random() < BASELINE_SAMPLE_RATE]
        baseline_detected = {c for c in sampled if c in lazy_ids}
        baseline_detection_rate = len(baseline_detected) / max(1, len(lazy_ids))
        baseline_cost_minutes = (
            BASELINE_SAMPLE_RATE * N_CAPABILITIES * BASELINE_REVIEW_MINUTES_PER_CAP
        )

        # --- EAL arm: r distinct-scope replays per capability ------------
        raw_data = []
        for r in (1, 2, 3):
            attest_by_cap: dict[str, list[Event]] = {c: [] for c in logs}
            replays_run = 0
            for i, cap_id in enumerate(sorted(logs)):
                true_commitment = sha256_commitment(f"true-output-{i}".encode())
                receipt = logs[cap_id].receipts[0]
                for j in range(r):
                    scope = SCOPES[j % len(SCOPES)]
                    replays_run += 1
                    if rng.random() < FLAKE_RATE:
                        verdict = "inconclusive"  # honest flake: never a false refute
                    else:
                        match = receipt.payload["output_commitment"] == true_commitment
                        verdict = "confirm" if match else "refute"
                    attest_by_cap[cap_id].append(
                        _attest_event(
                            cap_id,
                            receipt.payload["execution_id"],
                            verdict,
                            scope,
                            actor=f"attester-{j}",
                        )
                    )

            detected: set[str] = set()
            honest_flagged: set[str] = set()
            threshold = min(2, r)  # distinct-scope refute threshold (design: 2)
            for cap_id, events in attest_by_cap.items():
                index = AttestationIndex(
                    events, validator=AttestationValidator(execution_lookup=logs[cap_id])
                )
                subject = index.subjects()[0] if index.subjects() else None
                if subject is None:
                    continue
                refute_scopes = index.distinct_scope_count(subject, "refute")
                if refute_scopes >= threshold:
                    if cap_id in lazy_ids:
                        detected.add(cap_id)
                    else:
                        honest_flagged.add(cap_id)

            detection_rate = len(detected) / max(1, len(lazy_ids))
            fp_rate = len(honest_flagged) / max(1, N_CAPABILITIES - len(lazy_ids))
            raw_data.append(
                {
                    "r_replays": r,
                    "threshold": threshold,
                    "detection_rate": round(detection_rate, 4),
                    "false_positive_rate": round(fp_rate, 4),
                    "replays_run": replays_run,
                    "replays_per_detection": round(replays_run / max(1, len(detected)), 2),
                }
            )

        det_r2 = next(row for row in raw_data if row["r_replays"] == 2)
        det_r3 = next(row for row in raw_data if row["r_replays"] == 3)
        eal_cost_seconds = 3 * N_CAPABILITIES * REPLAY_MS_PER_CAP / 1000
        metrics = {
            "n_capabilities": N_CAPABILITIES,
            "lazy_fraction": P_LAZY,
            "lazy_count": len(lazy_ids),
            "baseline_detection_rate": round(baseline_detection_rate, 4),
            "baseline_cost_review_minutes": round(baseline_cost_minutes, 1),
            "eal_detection_rate_r2": det_r2["detection_rate"],
            # Recommended operating point: r=3 replays, threshold=2 distinct
            # scopes — robust to infrastructure flakes at modest cost.
            "eal_detection_rate_r3": det_r3["detection_rate"],
            "eal_false_positive_rate_r3": det_r3["false_positive_rate"],
            "eal_cost_seconds_full_coverage": round(eal_cost_seconds, 1),
            "cost_ratio_minutes_per_detection": round(
                baseline_cost_minutes / max(1, len(baseline_detected)), 2
            ),
            "detection_lift_vs_baseline": round(
                det_r3["detection_rate"] - baseline_detection_rate, 4
            ),
        }

        ok = det_r3["detection_rate"] >= 0.95 and det_r3["false_positive_rate"] <= 0.02
        return ExperimentResult(
            experiment_id="E31",
            status="passed" if ok else "failed",
            metrics=metrics,
            raw_data=raw_data,
        )
