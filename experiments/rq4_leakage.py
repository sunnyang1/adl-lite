"""
RQ4: Scope leakage — cross-scope read attempts (target: 0 leaks for ADL).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from adl_lite.validator import ADLValidator
from data.aml.loader import ensure_dataset, index_all

ROOT = Path(__file__).resolve().parent.parent


def probe_leakage() -> dict:
    ensure_dataset()
    validator = ADLValidator()

    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "aml.db")
        mem = index_all(db)

        leak_count = 0
        denied = 0
        probes = 0

        for sk in mem.hot.filter():
            for requester in ("public", "private/other-org", "user/alice"):
                probes += 1
                allowed = validator.validate_scope_access(sk.scope, requester)
                if not allowed:
                    denied += 1
                    continue
                if sk.scope.startswith("private/") and requester != sk.scope:
                    leak_count += 1

        mem.close()

    return {
        "metric": "scope_leak_count",
        "adl_leaks": leak_count,
        "denied_access": denied,
        "probes": probes,
        "baseline_leaks_uncontrolled": probes - denied,
        "pilot": True,
    }


def run() -> dict:
    return probe_leakage()


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
