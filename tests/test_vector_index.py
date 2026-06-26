"""Tests for adl_lite.vector_index and embedding dispatch."""

from __future__ import annotations

import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest

from adl_lite.embeddings import EmbeddingBackend
from adl_lite.vector_index import VectorIndex


class _FakeBackend:
    """Deterministic embedding backend for fast, offline unit tests."""

    embedding_dim = 8
    model_name = "fake"

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.embedding_dim), dtype=np.float32)
        for i, text in enumerate(texts):
            for j in range(self.embedding_dim):
                ch = text[j] if j < len(text) else "\x00"
                vectors[i, j] = ord(ch) / 255.0
        _normalize(vectors)
        return vectors


def _normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1
    vectors /= norms
    return vectors


@pytest.fixture
def backend() -> EmbeddingBackend:
    return _FakeBackend()  # type: ignore[return-value]


@pytest.fixture
def index(backend: EmbeddingBackend) -> VectorIndex:
    return VectorIndex(backend=backend, db_path=":memory:")


class TestVectorIndex:
    def test_add_and_search(self, index: VectorIndex) -> None:
        index.add("a", "apple banana")
        index.add("b", "banana cherry")
        index.add("c", "cherry date")

        results = index.search("apple", top_k=3)
        assert len(results) == 3
        assert results[0]["adl_id"] == "a"
        assert results[0]["similarity"] > results[1]["similarity"]

    def test_search_threshold(self, index: VectorIndex) -> None:
        index.add("a", "apple banana")
        index.add("b", "xyz qrs")

        results = index.search("apple", top_k=10, threshold=0.8)
        assert len(results) == 1
        assert results[0]["adl_id"] == "a"

    def test_add_many(self, index: VectorIndex) -> None:
        index.add_many(
            {
                "a": "apple",
                "b": "banana",
                "c": "cherry",
            }
        )
        results = index.search("banana", top_k=3)
        assert results[0]["adl_id"] == "b"

    def test_delete(self, index: VectorIndex) -> None:
        index.add("a", "apple")
        index.add("b", "banana")
        index.delete("a")

        results = index.search("apple", top_k=10)
        assert all(r["adl_id"] != "a" for r in results)

    def test_update(self, index: VectorIndex) -> None:
        index.add("a", "apple")
        index.add("a", "banana")

        results = index.search("apple", top_k=10)
        # After update, the old "apple" vector should be filtered out.
        assert all(r["adl_id"] != "a" or "banana" in r["text"] for r in results)

    def test_prefilter_ids(self, index: VectorIndex) -> None:
        index.add("a", "apple")
        index.add("b", "banana")
        index.add("c", "cherry")

        results = index.search("apple", top_k=10, prefilter_ids={"b", "c"})
        assert len(results) == 2
        assert all(r["adl_id"] in {"b", "c"} for r in results)

    def test_save_and_load(self, backend: EmbeddingBackend, tmp_path) -> None:
        db = tmp_path / "vec.db"
        index = VectorIndex(backend=backend, db_path=str(db))
        index.add("a", "apple")
        index.add("b", "banana")
        index.save()

        loaded = VectorIndex.load(backend=backend, db_path=str(db))
        results = loaded.search("apple", top_k=2)
        assert results[0]["adl_id"] == "a"

    def test_concurrent_add_and_search(self, backend: EmbeddingBackend) -> None:
        index = VectorIndex(backend=backend, db_path=":memory:")
        errors: list[Exception] = []
        barrier = threading.Barrier(4)

        def adder(label: str) -> None:
            try:
                barrier.wait(timeout=5)
                for i in range(50):
                    index.add(f"{label}-{i}", f"{label} concept {i}")
            except Exception as exc:
                errors.append(exc)

        def searcher() -> None:
            try:
                barrier.wait(timeout=5)
                for _ in range(50):
                    index.search("concept", top_k=5)
            except Exception as exc:
                errors.append(exc)

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(adder, f"t{i}") for i in range(3)]
            futures.append(pool.submit(searcher))
            for f in futures:
                f.result()

        assert not errors
        # All 150 add operations should be visible.
        assert len(index.search("concept", top_k=200)) == 150

    def test_close(self, backend: EmbeddingBackend) -> None:
        index = VectorIndex(backend=backend, db_path=":memory:")
        index.add("a", "apple")
        index.close()
        with pytest.raises((sqlite3.ProgrammingError, sqlite3.Error)):
            index.search("apple", top_k=1)
