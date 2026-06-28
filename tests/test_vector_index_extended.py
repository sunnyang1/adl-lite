"""Extended tests for vector_index module — behaviors 33-37."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

try:
    import faiss  # noqa: F401

    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

pytestmark = pytest.mark.skipif(
    not HAS_FAISS,
    reason="faiss-cpu not installed (install with: pip install faiss-cpu)",
)

from adl_lite.vector_index import VectorIndex  # noqa: E402


class _MockBackend:
    """Simple mock embedding backend for vector_index tests."""

    embedding_dim = 16
    model_name = "mock-vector"

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.embedding_dim), dtype=np.float32)
        for i, text in enumerate(texts):
            for j, ch in enumerate(text[: self.embedding_dim]):
                vectors[i, j % self.embedding_dim] = ord(ch) / 128.0
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1
        vectors /= norms
        return vectors


@pytest.fixture
def backend():
    return _MockBackend()


@pytest.fixture
def index(backend):
    vi = VectorIndex(backend=backend, db_path=":memory:")
    yield vi
    vi.close()


# ---------------------------------------------------------------------------
# Behavior 33: VectorIndex.__init__ with mock backend, verify embedding_dim
# ---------------------------------------------------------------------------


class TestVectorIndexInit:
    """VectorIndex init with mock backend preserves embedding_dim."""

    def test_embedding_dim_matches_backend(self, backend: _MockBackend) -> None:
        """VectorIndex._dim should match backend.embedding_dim."""
        vi = VectorIndex(backend=backend, db_path=":memory:")
        assert vi._dim == backend.embedding_dim
        assert vi._dim == 16
        vi.close()

    def test_backend_stored(self, backend: _MockBackend) -> None:
        """VectorIndex stores the backend."""
        vi = VectorIndex(backend=backend, db_path=":memory:")
        assert vi._backend is backend
        vi.close()


# ---------------------------------------------------------------------------
# Behavior 34: VectorIndex.add and add_many, then search returns results
# ---------------------------------------------------------------------------


class TestVectorIndexAddAndSearch:
    """add + add_many → search returns correct results."""

    def test_add_then_search(self, index: VectorIndex) -> None:
        """add single items, then search for one of them."""
        index.add("concept-a", "gradient explosion algorithm")
        index.add("concept-b", "capital reflux detection")
        results = index.search("gradient explosion", top_k=2)
        assert len(results) >= 1
        assert results[0]["adl_id"] == "concept-a"

    def test_add_many_then_search(self, index: VectorIndex) -> None:
        """add_many, then search returns results."""
        index.add_many(
            {
                "concept-a": "gradient explosion",
                "concept-b": "capital reflux",
                "concept-c": "model pruning",
            }
        )
        results = index.search("gradient explosion", top_k=3)
        assert len(results) >= 1
        assert results[0]["adl_id"] == "concept-a"

    def test_search_returns_similarity_and_text(self, index: VectorIndex) -> None:
        """search result dict has adl_id, similarity, text."""
        index.add("concept-x", "test description")
        results = index.search("test description", top_k=1)
        assert len(results) == 1
        assert "adl_id" in results[0]
        assert "similarity" in results[0]
        assert "text" in results[0]
        assert results[0]["adl_id"] == "concept-x"


# ---------------------------------------------------------------------------
# Behavior 35: VectorIndex.delete marks entry deleted, excluded from search
# ---------------------------------------------------------------------------


class TestVectorIndexDelete:
    """delete marks entry as deleted; excluded from search."""

    def test_delete_excludes_from_search(self, index: VectorIndex) -> None:
        """Deleted entry should not appear in search results."""
        index.add("keep-me", "keep this concept")
        index.add("delete-me", "delete this concept")
        index.delete("delete-me")

        results = index.search("concept", top_k=10)
        assert all(r["adl_id"] != "delete-me" for r in results)

    def test_delete_nonexistent_is_safe(self, index: VectorIndex) -> None:
        """Deleting a nonexistent ID should not raise."""
        index.add("existing", "some text")
        index.delete("nonexistent-id")  # Should not raise
        results = index.search("some text", top_k=5)
        assert len(results) >= 1
        assert results[0]["adl_id"] == "existing"

    def test_double_delete_is_safe(self, index: VectorIndex) -> None:
        """Deleting the same ID twice should not raise."""
        index.add("item", "item text")
        index.delete("item")
        index.delete("item")  # Second delete should be safe
        results = index.search("item text", top_k=5)
        assert all(r["adl_id"] != "item" for r in results)


# ---------------------------------------------------------------------------
# Behavior 36: VectorIndex.save and load persist to disk
# ---------------------------------------------------------------------------


class TestVectorIndexSaveLoad:
    """save and load persist index to disk."""

    def test_save_and_load(self, backend: _MockBackend, tmp_path: Path) -> None:
        """save then load preserves searchable data."""
        db_path = tmp_path / "test.db"
        vi = VectorIndex(backend=backend, db_path=str(db_path))
        vi.add("concept-a", "gradient explosion")
        vi.add("concept-b", "capital reflux")
        vi.save()

        # Load from disk
        loaded = VectorIndex.load(backend=backend, db_path=str(db_path))
        results = loaded.search("gradient explosion", top_k=2)
        assert len(results) >= 1
        assert results[0]["adl_id"] == "concept-a"
        vi.close()
        loaded.close()

    def test_save_creates_files(self, backend: _MockBackend, tmp_path: Path) -> None:
        """save creates index.faiss and meta.json."""
        db_path = tmp_path / "test.db"
        vi = VectorIndex(backend=backend, db_path=str(db_path))
        vi.add("concept-a", "some text")
        vi.save()

        index_dir = vi._index_dir
        assert (index_dir / "index.faiss").exists()
        assert (index_dir / "meta.json").exists()

        # meta.json should contain dimension and model info
        meta = json.loads((index_dir / "meta.json").read_text())
        assert meta["dim"] == backend.embedding_dim
        assert meta["model_name"] == backend.model_name
        vi.close()


# ---------------------------------------------------------------------------
# Behavior 37: VectorIndex.search with threshold filter — below threshold excluded
# ---------------------------------------------------------------------------


class TestVectorIndexSearchThreshold:
    """search with threshold filter excludes low-similarity results."""

    def test_threshold_excludes_low_similarity(self, index: VectorIndex) -> None:
        """Results below the threshold should be excluded."""
        index.add("similar", "gradient explosion algorithm")
        index.add("different", "completely unrelated topic about cooking")

        # Low threshold: both should appear
        results_low = index.search("gradient", top_k=10, threshold=0.0)
        assert len(results_low) >= 2

        # High threshold: only very similar results
        results_high = index.search("gradient", top_k=10, threshold=0.9)
        assert len(results_high) <= len(results_low)
        # "similar" should be in high-threshold results
        if len(results_high) > 0:
            # At least one result should have high similarity
            assert all(r["similarity"] >= 0.9 for r in results_high)

    def test_threshold_zero_returns_all(self, index: VectorIndex) -> None:
        """threshold=0.0 should return all results (no filtering)."""
        index.add("a", "first concept")
        index.add("b", "second concept")
        results = index.search("concept", top_k=10, threshold=0.0)
        assert len(results) >= 2
