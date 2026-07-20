#!/usr/bin/env python
"""Compliance-ready build gate for ADL Lite Phase-1 foundation.

Verifies that the project is ready for a production build:

  1. Dependency declarations
       * ``[neo4j]`` extra contains ``neo4j>=5.0``
       * ``[experiments]`` extra contains ``pygit2>=1.12``
  2. Trust-model production defaults
       * ``ConsensusConfig(mode="prod").resolve().min_distinct_validators == 2``
       * ``ConsensusConfig(mode="prod").resolve().require_did_binding == True``

Exits 0 when compliant, 1 when any check fails (intended as a CI gate).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"


def _extra_declares(text: str, extra: str, needle: str) -> bool:
    """Return True if *extra* declares a dependency containing *needle*.

    Uses ``tomllib`` when available (Python >= 3.11); falls back to a raw
    substring scan of the TOML on Python 3.10 where ``tomllib`` is absent.
    """
    try:
        import tomllib

        data = tomllib.loads(text)
        deps = data.get("project", {}).get("optional-dependencies", {}).get(extra, []) or []
        return any(needle in dep for dep in deps)
    except ModuleNotFoundError:
        # Python < 3.11: degrade to a substring scan.
        return needle in text
    except Exception:
        # Any parse failure -> rely on the substring scan as a safety net.
        return needle in text


def main() -> int:
    failures: list[str] = []

    text = PYPROJECT.read_text(encoding="utf-8")

    if not _extra_declares(text, "neo4j", "neo4j>=5.0"):
        failures.append("[neo4j] extra must declare 'neo4j>=5.0'")
    if not _extra_declares(text, "experiments", "pygit2>=1.12"):
        failures.append("[experiments] extra must declare 'pygit2>=1.12'")

    # Trust-model production defaults — the single source of truth for N_min.
    try:
        from adl_lite.trust_model import ConsensusConfig
    except Exception as exc:  # pragma: no cover - import environment issue
        failures.append(f"Could not import trust model: {exc}")
        print("COMPLIANCE CHECK FAILED:")
        for item in failures:
            print(f"  - {item}")
        return 1

    resolved = ConsensusConfig(mode="prod").resolve()
    if resolved.min_distinct_validators != 2:
        failures.append(
            "ConsensusConfig(prod).min_distinct_validators must be 2, "
            f"got {resolved.min_distinct_validators}"
        )
    if resolved.require_did_binding is not True:
        failures.append("ConsensusConfig(prod).require_did_binding must be True")

    if failures:
        print("COMPLIANCE CHECK FAILED:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("COMPLIANCE CHECK PASSED: project is ready for a production build.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
