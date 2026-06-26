"""Tests for adl_lite.canonicalization."""

from __future__ import annotations

import json
from collections import Counter

import numpy as np
import pytest

from adl_lite.canonicalization import CanonicalizationEngine, LLMBackend
from adl_lite.vector_index import VectorIndex


class _FakeLLM(LLMBackend):
    """LLM backend that returns a deterministic JSON proposal."""

    def complete(self, prompt: str, system: str | None = None) -> str:  # noqa: ARG002
        return json.dumps(
            {
                "canonical_adl_id": "canonical-gradient",
                "canonical_name": {"en": "Gradient Explosion"},
                "relations": [
                    {
                        "source": "disc-grad",
                        "target": "canonical-gradient",
                        "relation": "isomorphic-to",
                    },
                    {
                        "source": "disc-exploding",
                        "target": "canonical-gradient",
                        "relation": "isomorphic-to",
                    },
                ],
                "deprecate": [],
                "reasoning": "Near-duplicate cluster.",
            }
        )


class _NgramBackend:
    """Deterministic character n-gram embedding backend for fast tests."""

    embedding_dim = 64
    model_name = "fake-ngram"

    def __init__(self, n: int = 2) -> None:
        self.n = n

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.embedding_dim), dtype=np.float32)
        for i, text in enumerate(texts):
            text = text.lower().replace(" ", "")
            counts = Counter(text[j : j + self.n] for j in range(len(text) - self.n + 1))
            for gram, count in counts.items():
                idx = sum(ord(c) for c in gram) % self.embedding_dim
                vectors[i, idx] += count
            norm = np.linalg.norm(vectors[i])
            if norm:
                vectors[i] /= norm
        return vectors


@pytest.fixture
def backend():
    return _NgramBackend()


@pytest.fixture
def index(backend):
    return VectorIndex(backend=backend, db_path=":memory:")


class TestCanonicalizationEngine:
    def test_find_clusters(self, index: VectorIndex) -> None:
        index.add_many(
            {
                "disc-grad": "gradient explosion",
                "disc-exploding": "exploding gradients",
                "disc-capital": "capital reflux",
            }
        )
        engine = CanonicalizationEngine(vector_index=index, threshold=0.70)
        clusters = engine.find_clusters()
        # gradient explosion and exploding gradients should cluster.
        assert len(clusters) == 1
        assert sorted(clusters[0]) == ["disc-exploding", "disc-grad"]

    def test_propose_and_generate_actions(self, index: VectorIndex) -> None:
        index.add_many(
            {
                "disc-grad": "gradient explosion",
                "disc-exploding": "exploding gradients",
            }
        )
        engine = CanonicalizationEngine(vector_index=index, llm=_FakeLLM())
        proposal = engine.propose(["disc-grad", "disc-exploding"])
        assert proposal["canonical_adl_id"] == "canonical-gradient"

        actions = engine.generate_actions(["disc-grad", "disc-exploding"], proposal)
        assert len(actions) == 3  # register + 2 relations
        assert actions[0].action == "register"
        assert actions[1].action == "relate"

    def test_normalize_dry_run(self, index: VectorIndex) -> None:
        index.add_many(
            {
                "disc-grad": "gradient explosion",
                "disc-exploding": "exploding gradients",
            }
        )
        engine = CanonicalizationEngine(vector_index=index, llm=_FakeLLM(), threshold=0.70)
        results = engine.normalize(dry_run=True)
        assert len(results) == 1
        assert results[0]["executed"] is False
        assert len(results[0]["actions"]) > 0
