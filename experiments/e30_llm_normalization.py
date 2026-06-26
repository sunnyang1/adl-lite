"""E30: LLM-driven normalization workflow.

Builds a vector index over synthetic near-duplicate clusters, runs the
CanonicalizationEngine in dry-run mode with a deterministic fake LLM backend, and
verifies that the engine emits auditable action blocks without mutating chains.
"""

from __future__ import annotations

import json
from typing import Any

from adl_lite.canonicalization import CanonicalizationEngine, LLMBackend
from adl_lite.vector_index import VectorIndex

from ._synthetic_embeddings import CORPUS, OfflineBackend, corpus_group
from .base import BaseExperiment, ExperimentResult
from .registry import register


class _FakeLLM(LLMBackend):
    """Returns a deterministic canonicalization proposal for every cluster."""

    def complete(self, prompt: str, system: str | None = None) -> str:  # noqa: ARG002
        # Derive the canonical form from the first concept in the cluster.
        cluster_ids: list[str] = []
        for line in prompt.splitlines():
            if line.startswith("--- ") and line.endswith(" ---"):
                cluster_ids.append(line.strip("- "))

        first_id = cluster_ids[0] if cluster_ids else "canonical-concept"
        group = corpus_group(first_id)
        canonical_map = {
            "disc-grad": ("canonical-gradient-explosion", "Gradient Explosion"),
            "disc-capital": ("canonical-capital-reflux", "Capital Reflux"),
            "disc-attn": ("canonical-attention-residual", "Attention Residual"),
            "disc-matdo": ("canonical-matdo-fork", "Matdo Fork"),
            "disc-weather": ("canonical-weather-retrieval", "Weather Data Retrieval"),
        }
        canonical_id, canonical_name = canonical_map.get(
            group, ("canonical-concept", "Canonical Concept")
        )

        relations = [
            {"source": adl_id, "target": canonical_id, "relation": "isomorphic-to"}
            for adl_id in cluster_ids
        ]

        return json.dumps(
            {
                "canonical_adl_id": canonical_id,
                "canonical_name": {"en": canonical_name},
                "relations": relations,
                "deprecate": [],
                "reasoning": "Synthetic LLM normalization proposal.",
            }
        )


@register("E30")
class E30LLMNormalization(BaseExperiment):
    experiment_id = "E30"
    name = "LLM Normalization"
    description = "Dry-run LLM canonicalization over synthetic near-duplicate clusters"

    def run(self) -> ExperimentResult:
        backend = OfflineBackend()
        index = VectorIndex(backend=backend, db_path=":memory:")
        index.add_many(CORPUS)

        engine = CanonicalizationEngine(vector_index=index, llm=_FakeLLM(), threshold=0.50)
        results = engine.normalize(dry_run=True)

        raw_data: list[dict[str, Any]] = []
        for r in results:
            raw_data.append(
                {
                    "cluster": r["cluster"],
                    "canonical_adl_id": r["proposal"].get("canonical_adl_id"),
                    "actions": [a.action for a in r["actions"]],
                    "executed": r["executed"],
                }
            )

        cluster_count = len(results)
        action_count = sum(len(r["actions"]) for r in results)
        all_dry_run = all(not r["executed"] for r in results)
        expected_clusters = 5

        errors: list[str] = []
        if cluster_count < expected_clusters:
            errors.append(f"Expected {expected_clusters} clusters, found {cluster_count}")
        if action_count == 0:
            errors.append("No canonicalization actions generated")
        if not all_dry_run:
            errors.append("Dry-run mode mutated chains unexpectedly")

        # Verify that relations from the fake LLM were turned into relate actions.
        relate_count = sum(1 for r in results for a in r["actions"] if a.action == "relate")
        if relate_count == 0:
            errors.append("No relate actions generated from LLM proposal")

        return ExperimentResult(
            experiment_id=self.experiment_id,
            status="passed" if not errors else "failed",
            metrics={
                "clusters_found": cluster_count,
                "actions_generated": action_count,
                "relate_actions_generated": relate_count,
                "dry_run_honored": all_dry_run,
                "expected_clusters": expected_clusters,
            },
            raw_data=raw_data,
            errors=errors,
        )
