"""Run all experiments and generate JSON summary."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import all experiment modules so @register decorators fire
from experiments import (  # noqa: E402
    e1_chain_integrity,  # noqa: F401
    e2_status_derivation,  # noqa: F401
    e3_snapshot_roundtrip,  # noqa: F401
    e4_precondition,  # noqa: F401
    e5_agent_audit,  # noqa: F401
    e6_aml_pipeline,  # noqa: F401
    e7_realtime_watcher,  # noqa: F401
    e8_edge_sync,  # noqa: F401
    e9_git_baseline,  # noqa: F401
    e10_fde_pipeline,  # noqa: F401
    e11_sideeffect_stress,  # noqa: F401
)
from experiments.registry import list_all  # noqa: E402
from experiments.runner import run_one  # noqa: E402


def main():
    results = []
    for exp_info in list_all():
        eid = exp_info["id"]
        result = run_one(eid)
        results.append(
            {
                "id": eid,
                "status": result.status,
                "metrics": result.metrics,
            }
        )

    results_dir = PROJECT_ROOT / "artifacts" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    with open(results_dir / "experiments.json", "w") as f:
        json.dump(results, f, indent=2)

    passed = sum(1 for r in results if r.get("status") == "passed")
    total = len(results)
    print(f"\nExperiments: {passed}/{total} passed")
    print("OVERALL: PASS" if passed == total else "OVERALL: PARTIAL")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
