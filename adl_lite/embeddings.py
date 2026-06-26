"""Pluggable embedding backends for ADL Lite semantic search.

Supports a local sentence-transformers backend (default, offline) and an
optional OpenAI backend. Imports are lazy so that core ADL Lite startup stays
fast when embedding dependencies are not installed.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class EmbeddingBackend(Protocol):
    """Protocol for an embedding encoder."""

    @property
    def embedding_dim(self) -> int:
        """Dimensionality of produced vectors."""
        ...

    @property
    def model_name(self) -> str:
        """Human-readable model identifier (used for versioning)."""
        ...

    def encode(self, texts: list[str]) -> np.ndarray:
        """Encode a list of texts into a (len(texts), embedding_dim) float array."""
        ...


class SentenceTransformerBackend:
    """Local sentence-transformers backend (offline, default)."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str | None = None,
        batch_size: int = 32,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._batch_size = batch_size
        self._model: Any | None = None

    def _load(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise ImportError(
                    "sentence-transformers is required for the local embedding backend. "
                    'Install it with: pip install -e ".[embeddings]"'
                ) from exc
            self._model = SentenceTransformer(self._model_name, device=self._device)
        return self._model

    @property
    def embedding_dim(self) -> int:
        model = self._load()
        return int(getattr(model, "get_sentence_embedding_dimension", lambda: 384)())

    @property
    def model_name(self) -> str:
        return self._model_name

    def encode(self, texts: list[str]) -> np.ndarray:
        model = self._load()
        embeddings = model.encode(
            texts,
            batch_size=self._batch_size,
            convert_to_numpy=True,
            normalize_embeddings=False,
            show_progress_bar=False,
        )
        return np.asarray(embeddings, dtype=np.float32)


class OpenAIBackend:
    """OpenAI text-embedding backend (requires API key)."""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        client: object | None = None,
    ) -> None:
        self._model = model
        self._client = client
        self._dim: int | None = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import openai
            except ImportError as exc:
                raise ImportError(
                    "openai is required for the OpenAI embedding backend. "
                    'Install it with: pip install -e ".[embeddings]"'
                ) from exc
            self._client = openai.OpenAI()
        return self._client

    @property
    def embedding_dim(self) -> int:
        # Known dimensions for current OpenAI embedding models.
        dims = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        return dims.get(self._model, 1536)

    @property
    def model_name(self) -> str:
        return self._model

    def encode(self, texts: list[str]) -> np.ndarray:
        client = self._get_client()
        response = client.embeddings.create(input=texts, model=self._model)
        vectors = [item.embedding for item in response.data]
        return np.asarray(vectors, dtype=np.float32)


def get_default_embedding_backend() -> EmbeddingBackend:
    """Return the local sentence-transformers backend by default.

    ADL Lite is local-first: this function will *not* silently fall back to a
    cloud API. Install the embeddings extra to use the default backend, or pass
    an explicit backend (e.g. ``OpenAIBackend``) to ``VectorIndex``.
    """
    try:
        from sentence_transformers import SentenceTransformer

        del SentenceTransformer
        return SentenceTransformerBackend()
    except ImportError as exc:
        raise ImportError(
            "No local embedding backend available. Install embeddings extras with: "
            'pip install -e ".[embeddings]"'
        ) from exc
