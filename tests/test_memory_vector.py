"""Tests for ADLMemory semantic search via an optional vector index."""

from __future__ import annotations

from collections import Counter

import numpy as np
import pytest

try:
    import faiss  # noqa: F401

    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

from adl_lite.exceptions import ADLMemoryError
from adl_lite.memory import ADLMemory
from adl_lite.parser import parse_text

# VectorIndex requires faiss-cpu; skip all tests that use it.
pytestmark = pytest.mark.skipif(
    not HAS_FAISS,
    reason="faiss-cpu not installed (install with: pip install faiss-cpu)",
)

from adl_lite.vector_index import VectorIndex  # noqa: E402


class _NgramBackend:
    """Deterministic character n-gram embedding backend for fast tests."""

    embedding_dim = 64
    model_name = "fake-ngram"

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.embedding_dim), dtype=np.float32)
        for i, text in enumerate(texts):
            text = text.lower().replace(" ", "")
            counts = Counter(text[j : j + 2] for j in range(len(text) - 1))
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


class TestADLMemorySemanticSearch:
    def test_semantic_search_without_vector_index(self, tmp_path) -> None:
        mem = ADLMemory(str(tmp_path / "mem.db"))
        doc = parse_text(
            "---\nadl_type: discovery\nadl_id: a\nstatus: provisional\nconfidence: 0.5\n---\n\n# Apple\n"
        )
        mem.store(doc)
        with pytest.raises(ADLMemoryError):
            mem.semantic_search("apple", top_k=5)
        mem.close()

    def test_semantic_search_ranks_related(self, backend, tmp_path) -> None:
        db = tmp_path / "mem.db"
        vector_index = VectorIndex(backend=backend, db_path=str(tmp_path / "vec.db"))
        mem = ADLMemory(str(db), vector_index=vector_index)

        docs = {
            "disc-grad": "Gradient Explosion",
            "disc-exploding": "Exploding Gradients",
            "disc-capital": "Capital Reflux",
        }
        for adl_id, title in docs.items():
            doc = parse_text(
                f"---\n"
                f"adl_type: discovery\n"
                f"adl_id: {adl_id}\n"
                f"status: provisional\n"
                f"confidence: 0.5\n"
                f"---\n\n"
                f"# {title}\n\n"
                f"Description of {title}.\n"
            )
            mem.store(doc)

        results = mem.semantic_search("gradient explosion", top_k=3, threshold=0.6)
        ids = [r["adl_id"] for r in results]
        assert ids[0] == "disc-grad"
        assert "disc-exploding" in ids
        assert "disc-capital" not in ids
        mem.close()

    def test_semantic_search_prefilter(self, backend, tmp_path) -> None:
        db = tmp_path / "mem.db"
        vector_index = VectorIndex(backend=backend, db_path=str(tmp_path / "vec.db"))
        mem = ADLMemory(str(db), vector_index=vector_index)

        docs = {
            "disc-grad": ("Gradient Explosion", "ml"),
            "disc-exploding": ("Exploding Gradients", "ml"),
            "disc-capital": ("Capital Reflux", "finance"),
        }
        for adl_id, (title, domain) in docs.items():
            doc = parse_text(
                f"---\n"
                f"adl_type: discovery\n"
                f"adl_id: {adl_id}\n"
                f"status: provisional\n"
                f"confidence: 0.5\n"
                f"domain: {domain}\n"
                f"---\n\n"
                f"# {title}\n\n"
                f"Description of {title}.\n"
            )
            mem.store(doc)

        results = mem.semantic_search("gradient explosion", top_k=3, domain="ml", threshold=0.6)
        ids = {r["adl_id"] for r in results}
        assert ids == {"disc-grad", "disc-exploding"}
        mem.close()
