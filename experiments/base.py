"""Base experiment interface and result type.

Every ADL Lite experiment must subclass BaseExperiment and implement run().
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExperimentResult:
    """Unified output format for all experiments."""

    experiment_id: str
    status: str  # "passed" | "failed" | "partial"
    metrics: dict[str, Any] = field(default_factory=dict)
    raw_data: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "status": self.status,
            "metrics": self.metrics,
            "raw_data": self.raw_data,
            "errors": self.errors,
            "duration_ms": self.duration_ms,
        }


class BaseExperiment:
    """Abstract base for all ADL Lite experiments."""

    experiment_id: str = ""
    name: str = ""
    description: str = ""

    def run(self) -> ExperimentResult:
        raise NotImplementedError

    def _run_wrapper(self) -> ExperimentResult:
        start = time.perf_counter()
        try:
            result = self.run()
        except Exception as exc:
            result = ExperimentResult(
                experiment_id=self.experiment_id,
                status="failed",
                errors=[str(exc)],
                raw_data=[],
            )
        result.duration_ms = int((time.perf_counter() - start) * 1000)
        if result.experiment_id == "":
            result.experiment_id = self.experiment_id
        return result
