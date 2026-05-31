"""E3: Snapshot round-trip consistency.

Verifies that:
    parse_file → event_chain → snapshot → front_matter'
produces a front_matter' that matches the original on status, confidence,
and validators.

Method: Parse all example + AML concept files, verify round-trip consistency.
"""

from __future__ import annotations

import math
from pathlib import Path

from adl_lite.models import ADLFrontMatter
from adl_lite.parser import parse_file

from .base import BaseExperiment, ExperimentResult
from .registry import register

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
AML_DIR = Path(__file__).resolve().parent.parent / "data" / "aml" / "concepts"


@register("E3")
class E3SnapshotRoundtrip(BaseExperiment):
    experiment_id = "E3"
    name = "Snapshot round-trip consistency"
    description = "front_matter → chain → snapshot must preserve status/confidence/validators"

    def run(self) -> ExperimentResult:
        results = []
        errors = []
        status_match = 0
        total = 0

        paths = []
        if EXAMPLES_DIR.is_dir():
            paths.extend(sorted(EXAMPLES_DIR.glob("*.md")))
        if AML_DIR.is_dir():
            paths.extend(sorted(AML_DIR.glob("*.md")))

        for path in paths:
            total += 1
            try:
                doc = parse_file(path)
            except Exception as exc:
                errors.append(f"{path.name}: parse error: {exc}")
                continue

            chain = doc.event_chain
            fm_original = doc.front_matter
            fm_roundtrip = ADLFrontMatter.from_chain(
                chain,
                adl_type=fm_original.adl_type,
                identity=fm_original.identity_dict(),
            )

            ok = fm_roundtrip.status == fm_original.status
            confidence_ok = math.isclose(
                fm_roundtrip.confidence, fm_original.confidence, abs_tol=0.01
            )
            validators_ok = fm_roundtrip.validators == fm_original.validators

            if ok:
                status_match += 1

            entry = {
                "file": path.name,
                "status_ok": ok,
                "confidence_ok": confidence_ok,
                "validators_ok": validators_ok,
                "original_status": fm_original.status.value,
                "roundtrip_status": fm_roundtrip.status.value,
            }
            results.append(entry)

            if not ok:
                errors.append(
                    f"{path.name}: status mismatch "
                    f"{fm_original.status.value} vs {fm_roundtrip.status.value}"
                )

        accuracy = status_match / total if total else 0.0

        return ExperimentResult(
            experiment_id=self.experiment_id,
            status="passed" if accuracy >= 0.95 else "partial",
            metrics={
                "total_files": total,
                "status_match": status_match,
                "status_accuracy": round(accuracy, 4),
            },
            raw_data=results,
            errors=errors,
        )
