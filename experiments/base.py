"""Base experiment interface and result type.

Every ADL Lite experiment must subclass BaseExperiment and implement run().
"""

from __future__ import annotations

import importlib.util
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
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

    def generate_latex_table(self, output_dir: Path) -> Path | None:
        """Auto-generate LaTeX table from this result and save to output_dir.

        Calls scripts/experiment_to_latex.py logic for this specific experiment.
        Returns path to generated .tex file, or None if no table generated.
        """
        if not self.metrics and not self.raw_data:
            return None

        output_dir.mkdir(parents=True, exist_ok=True)

        # Dynamically import scripts/experiment_to_latex.py
        script_path = Path(__file__).resolve().parent.parent / "scripts" / "experiment_to_latex.py"
        if not script_path.exists():
            return None

        spec = importlib.util.spec_from_file_location("experiment_to_latex", script_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        try:
            make_tabular = module.make_tabular
            format_number = module.format_number
            escape_latex = module.escape_latex
        except AttributeError:
            return None

        # Try known experiment-specific generators first
        eid_lower = self.experiment_id.lower()
        known_generators = getattr(module, "_KNOWN_GENERATORS", None)
        if known_generators is None:
            known_generators = {
                "e27": getattr(module, "generate_e27", None),
                "e28": getattr(module, "generate_e28", None),
                "e29": getattr(module, "generate_e29", None),
            }

        # Write temporary JSON for experiment-specific generators
        if eid_lower in known_generators and known_generators[eid_lower] is not None:
            tmp_json = output_dir.parent / "experiments" / f"{eid_lower}_tmp.json"
            tmp_json.parent.mkdir(parents=True, exist_ok=True)
            tmp_json.write_text(
                json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
            )
            try:
                known_generators[eid_lower](tmp_json, output_dir)
                tex_path = output_dir / f"{eid_lower}.tex"
                if tex_path.exists():
                    tmp_json.unlink(missing_ok=True)
                    return tex_path
            except Exception:
                pass
            tmp_json.unlink(missing_ok=True)

        # Generic fallback: metrics table
        columns = ["Metric", "Value"]
        align = r"@{}lr@{}"
        rows = []
        for k, v in self.metrics.items():
            rows.append([escape_latex(str(k)), format_number(v, 2)])

        if not rows:
            return None

        tex = make_tabular(
            columns,
            align,
            rows,
            f"tab:{eid_lower}-results",
            f"Experiment {escape_latex(self.experiment_id)} results",
        )
        tex_path = output_dir / f"{eid_lower}.tex"
        tex_path.write_text(tex, encoding="utf-8")
        return tex_path

    def to_json(self) -> str:
        """Serialize result to JSON string."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class BaseExperiment:
    """Abstract base for all ADL Lite experiments."""

    experiment_id: str = ""
    name: str = ""
    description: str = ""

    def run(self) -> ExperimentResult:
        raise NotImplementedError

    def verify_consistency(self) -> list[str]:
        """Verify experiment metadata matches naming conventions.

        Checks:
        - experiment_id matches expected pattern (e.g., E27 from e27_*.py)
        - name and description are non-empty
        - module filename matches experiment_id pattern
        Returns list of warning strings (empty if clean).
        """
        warnings: list[str] = []

        if not self.experiment_id:
            warnings.append("experiment_id is empty")
        else:
            match = re.match(r"^[Ee](\d+)([a-z]?)$", self.experiment_id)
            if not match:
                warnings.append(
                    f"experiment_id '{self.experiment_id}' does not match expected pattern "
                    f"(e.g., E2, E27, E20b)"
                )

        if not self.name or not self.name.strip():
            warnings.append("name is empty")
        if not self.description or not self.description.strip():
            warnings.append("description is empty")

        # Check module filename matches experiment_id pattern
        module_name = self.__class__.__module__
        if module_name and module_name != "__main__":
            parts = module_name.split(".")
            if parts:
                filename = parts[-1]
                if self.experiment_id:
                    eid_lower = self.experiment_id.lower()
                    num_match = re.match(r"^[e](\d+)([a-z]?)$", eid_lower)
                    if num_match:
                        num = num_match.group(1)
                        suffix = num_match.group(2)
                        expected_prefix = f"e{num}{suffix}_"
                        if not filename.startswith(expected_prefix):
                            warnings.append(
                                f"module filename '{filename}' does not match "
                                f"experiment_id '{self.experiment_id}' (expected prefix "
                                f"'{expected_prefix}')"
                            )

        return warnings

    def is_available(self) -> bool:
        """Whether this experiment's required optional dependencies are present.

        Override in experiments that need heavy optional dependencies (e.g. E19
        needs ``pygit2`` / ``prov``). The default is ``True`` (no special deps),
        which lets the runner list and run the experiment unconditionally.
        """
        return True

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
