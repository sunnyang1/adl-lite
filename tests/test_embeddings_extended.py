"""Extended tests for embeddings module — behaviors 29-32."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from adl_lite.embeddings import (
    OpenAIBackend,
    SentenceTransformerBackend,
    get_default_embedding_backend,
)

# ---------------------------------------------------------------------------
# Behavior 29: SentenceTransformerBackend — mock model load, verify encode output shape
# ---------------------------------------------------------------------------


class TestSentenceTransformerBackendMock:
    """SentenceTransformerBackend with mocked SentenceTransformer."""

    def test_mock_model_load_and_encode_shape(self):
        """With a mocked model, encode returns (len(texts), embedding_dim) array."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        # encode returns a numpy array
        mock_embeddings = np.random.rand(3, 384).astype(np.float32)
        mock_model.encode.return_value = mock_embeddings

        backend = SentenceTransformerBackend(model_name="all-MiniLM-L6-v2")
        # Inject the mock model
        backend._model = mock_model

        result = backend.encode(["text1", "text2", "text3"])
        assert result.shape == (3, 384)
        assert result.dtype == np.float32

    def test_embedding_dim_property(self):
        """embedding_dim property returns the model's dimension."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384

        backend = SentenceTransformerBackend(model_name="all-MiniLM-L6-v2")
        backend._model = mock_model

        assert backend.embedding_dim == 384


# ---------------------------------------------------------------------------
# Behavior 30: OpenAIBackend.embedding_dim returns known model dimension
# ---------------------------------------------------------------------------


class TestOpenAIBackendEmbeddingDim:
    """OpenAIBackend.embedding_dim returns known dimensions for supported models."""

    def test_small_model_dim(self):
        """text-embedding-3-small has dimension 1536."""
        backend = OpenAIBackend(model="text-embedding-3-small")
        assert backend.embedding_dim == 1536

    def test_large_model_dim(self):
        """text-embedding-3-large has dimension 3072."""
        backend = OpenAIBackend(model="text-embedding-3-large")
        assert backend.embedding_dim == 3072

    def test_ada002_dim(self):
        """text-embedding-ada-002 has dimension 1536."""
        backend = OpenAIBackend(model="text-embedding-ada-002")
        assert backend.embedding_dim == 1536

    def test_unknown_model_default_dim(self):
        """Unknown model defaults to 1536."""
        backend = OpenAIBackend(model="custom-embedding-model")
        assert backend.embedding_dim == 1536


# ---------------------------------------------------------------------------
# Behavior 31: OpenAIBackend.model_name returns configured model string
# ---------------------------------------------------------------------------


class TestOpenAIBackendModelName:
    """OpenAIBackend.model_name returns the configured model."""

    def test_model_name_default(self):
        """Default model_name is text-embedding-3-small."""
        backend = OpenAIBackend()
        assert backend.model_name == "text-embedding-3-small"

    def test_model_name_custom(self):
        """Custom model name is returned correctly."""
        backend = OpenAIBackend(model="text-embedding-3-large")
        assert backend.model_name == "text-embedding-3-large"

    def test_model_name_arbitrary(self):
        """Arbitrary model name is preserved."""
        backend = OpenAIBackend(model="my-custom-model")
        assert backend.model_name == "my-custom-model"


# ---------------------------------------------------------------------------
# Behavior 32: get_default_embedding_backend raises ImportError when
#              sentence-transformers unavailable
# ---------------------------------------------------------------------------


class TestGetDefaultBackendImportError:
    """get_default_embedding_backend raises ImportError without sentence-transformers."""

    def test_raises_import_error_when_unavailable(self):
        """When sentence_transformers is unavailable, ImportError is raised."""
        with patch.dict(sys.modules, {"sentence_transformers": None}):
            with pytest.raises(ImportError, match="No local embedding backend available"):
                get_default_embedding_backend()

    def test_import_error_message_mention_install(self):
        """ImportError message mentions install instructions."""
        with patch.dict(sys.modules, {"sentence_transformers": None}):
            try:
                get_default_embedding_backend()
            except ImportError as exc:
                assert "pip install" in str(exc) or "embeddings" in str(exc)
