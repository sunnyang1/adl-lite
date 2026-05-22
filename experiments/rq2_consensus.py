"""
RQ2: Consensus rounds — transitions to validated (ADL vs no-chain baseline).
"""

from __future__ import annotations

import json
from pathlib import Path

from adl_lite import ConsensusEngine, DiscoveryStatus, parse_file

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"


def count_consensus_rounds(paths: list[Path]) -> dict:
    engine = ConsensusEngine()
    total_transitions = 0
    validated = 0

    for path in paths:
        doc = parse_file(path)
        engine.register(doc)
        total_transitions += 1
        if doc.status == DiscoveryStatus.PROVISIONAL:
            engine.transition(
                doc.adl_id,
                DiscoveryStatus.VALIDATED,
                actor="reviewer",
                reason="RQ2 scripted validation",
            )
            total_transitions += 1
        if engine.get_status(doc.adl_id) == DiscoveryStatus.VALIDATED:
            validated += 1

    # Baseline: no explicit chain — 0 recorded transitions
    baseline_transitions = 0

    return {
        "metric": "consensus_transitions",
        "adl_transitions": total_transitions,
        "adl_validated_count": validated,
        "baseline_transitions": baseline_transitions,
        "n_docs": len(paths),
        "pilot": True,
    }


def run(paths: list[Path] | None = None) -> dict:
    paths = paths or list(EXAMPLES.glob("*.md"))
    return count_consensus_rounds(paths)


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
