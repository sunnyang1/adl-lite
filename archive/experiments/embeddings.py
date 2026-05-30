"""Optional sentence-transformers embeddings for RQ3 hybrid retrieval."""

from __future__ import annotations

from typing import Protocol

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_model = None


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


def embeddings_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401

        return True
    except ImportError:
        return False


def _lazy_load_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def embed_texts(texts: list[str], provider: EmbeddingProvider | None = None) -> list[list[float]]:
    if provider is not None:
        return provider.embed(texts)
    if not embeddings_available():
        raise ImportError(
            "sentence-transformers not installed; "
            "pip install adl-lite[experiments-embeddings]"
        )
    model = _lazy_load_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vectors]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


class EmbeddingIndex:
    """Cosine rank over pre-embedded documents (vectors assumed L2-normalized)."""

    def __init__(self, provider: EmbeddingProvider | None = None) -> None:
        self._texts: dict[str, str] = {}
        self._vecs: dict[str, list[float]] = {}
        self._provider = provider

    def add(self, doc_id: str, text: str) -> None:
        self._texts[doc_id] = text

    def build(self) -> None:
        ids = list(self._texts.keys())
        if not ids:
            return
        vecs = embed_texts([self._texts[i] for i in ids], provider=self._provider)
        self._vecs = dict(zip(ids, vecs, strict=True))

    def score(self, query: str, doc_id: str) -> float:
        if doc_id not in self._vecs:
            return 0.0
        q_vec = embed_texts([query], provider=self._provider)[0]
        return _dot(q_vec, self._vecs[doc_id])

    def rank(self, query: str, k: int = 10) -> list[tuple[str, float]]:
        if not self._vecs:
            return []
        q_vec = embed_texts([query], provider=self._provider)[0]
        scored = [(doc_id, _dot(q_vec, vec)) for doc_id, vec in self._vecs.items()]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]
