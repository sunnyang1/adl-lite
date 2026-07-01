"""E5: Multi-Agent Literature Review Case Study.

A simulated realistic case study of a 5-agent scientific literature review
pipeline, registered as a formal experiment in the ADL Lite framework.

The case study demonstrates:
  - Cross-validation by independent agents (2 validators per capability)
  - Negative-result transparency (trend-detection deprecated)
  - Iterative improvement via fork (abstract-generation -> calibrated)
  - L3 relation network (feeds-into, complements)
  - Quantitative evidence events (P@10, Cohen's kappa, overstatement rate)

Metrics:
  - total_chains: 19 (17 initial + 2 forked)
  - total_events: 79
  - status_dist: validated 18, deprecated 1
  - confidence range: 0.40–0.91 (mean 0.753)

The underlying simulation is in case_study/run_case_study.py; this experiment
wrapper makes it runnable via `python -m experiments.runner E5`.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .base import BaseExperiment, ExperimentResult
from .registry import register


@register("E5")
class E5LiteratureReviewCaseStudy(BaseExperiment):
    experiment_id = "E5"
    name = "Multi-Agent Literature Review Case Study"
    description = (
        "5-agent simulated literature review pipeline — "
        "cross-validation, deprecation, fork, and evidence"
    )

    def run(self) -> ExperimentResult:
        # Import the case study runner dynamically to avoid heavy deps at import time
        case_study_dir = Path(__file__).resolve().parent.parent / "case_study"
        sys.path.insert(0, str(case_study_dir))
        try:
            from run_case_study import compute_stats, run
        except ImportError as exc:
            return ExperimentResult(
                experiment_id=self.experiment_id,
                status="failed",
                errors=[f"Cannot import case_study/run_case_study.py: {exc}"],
            )
        finally:
            sys.path.pop(0)

        chains, event_log = run()
        stats = compute_stats(chains, event_log)

        # Derive per-capability metrics for the results table
        per_capability = []
        for cid, chain in chains.items():
            validations = [
                e for e in event_log if e["concept_id"] == cid and e["event_type"] == "validate"
            ]
            evidence = [
                e for e in event_log if e["concept_id"] == cid and e["event_type"] == "evidence"
            ]
            per_capability.append(
                {
                    "concept_id": cid,
                    "status": str(chain.status.value),
                    "confidence": round(chain.confidence, 3),
                    "validations": len(validations),
                    "evidence": len(evidence),
                    "events": chain.length,
                }
            )

        return ExperimentResult(
            experiment_id=self.experiment_id,
            status="passed",
            metrics={
                "total_chains": stats["total_chains"],
                "total_events": stats["total_events"],
                "validated": stats["status_dist"].get("validated", 0),
                "deprecated": stats["status_dist"].get("deprecated", 0),
                "forks": stats["forks"],
                "relates": stats["relates"],
                "evidence_events": stats["evidence"],
                "confidence_min": stats["confidence"]["min"],
                "confidence_max": stats["confidence"]["max"],
                "confidence_mean": stats["confidence"]["mean"],
            },
            raw_data=per_capability,
        )
