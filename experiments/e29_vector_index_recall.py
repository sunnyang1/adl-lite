"""E29: Vector index recall — FAISS ANN vs brute-force cosine.

Builds a small synthetic corpus with known near-duplicate groups, indexes it with a
deterministic embedding backend, and measures whether the vector index retrieves the
relevant group members. The experiment is fully offline and does not require a
downloaded sentence-transformers model.
"""

from __future__ import annotations

from typing import Any

from adl_lite.vector_index import VectorIndex

from ._synthetic_embeddings import CORPUS, OfflineBackend, corpus_group
from .base import BaseExperiment, ExperimentResult
from .registry import register


@register("E29")
class E29VectorIndexRecall(BaseExperiment):
    experiment_id = "E29"
    name = "Vector Index Recall"
    description = "Measure FAISS ANN recall against brute-force cosine on synthetic groups"

    def run(self) -> ExperimentResult:
        backend = OfflineBackend()
        index = VectorIndex(backend=backend, db_path=":memory:")
        index.add_many(CORPUS)

        ids = list(CORPUS.keys())
        ground_truth = {
            adl_id: {
                other_id
                for other_id in ids
                if other_id != adl_id and corpus_group(other_id) == corpus_group(adl_id)
            }
            for adl_id in ids
        }

        top_k = 5
        threshold = 0.3
        recalls: list[float] = []
        raw_data: list[dict[str, Any]] = []

        for query_id in ids:
            results = index.search(CORPUS[query_id], top_k=top_k, threshold=threshold)
            retrieved = {r["adl_id"] for r in results if r["adl_id"] != query_id}
            truth = ground_truth[query_id]
            recall = len(retrieved & truth) / len(truth) if truth else 1.0
            recalls.append(recall)
            raw_data.append(
                {
                    "query_id": query_id,
                    "recall": round(recall, 4),
                    "retrieved": sorted(retrieved),
                    "truth": sorted(truth),
                }
            )

        avg_recall = sum(recalls) / len(recalls) if recalls else 0.0

        return ExperimentResult(
            experiment_id=self.experiment_id,
            status="passed" if avg_recall >= 0.8 else "failed",
            metrics={
                "avg_recall_at_5": round(avg_recall, 4),
                "min_recall_at_5": round(min(recalls), 4),
                "queries": len(recalls),
                "top_k": top_k,
                "threshold": threshold,
            },
            raw_data=raw_data,
            errors=[] if avg_recall >= 0.8 else [f"Average recall {avg_recall:.2f} below 0.8"],
        )
