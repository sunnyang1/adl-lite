"""Shared synthetic embedding backend and corpus for E29/E30.

This module is intentionally not registered as an experiment.
"""

from __future__ import annotations

from collections import Counter

import numpy as np

_STOPWORDS = {
    "the",
    "and",
    "in",
    "of",
    "a",
    "an",
    "for",
    "with",
    "from",
    "via",
    "based",
    "during",
    "to",
    "on",
    "is",
}


class OfflineBackend:
    """Deterministic word-level embedding backend for offline experiments."""

    embedding_dim = 128
    model_name = "offline-word"

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.embedding_dim), dtype=np.float32)
        for i, text in enumerate(texts):
            tokens = [t for t in text.lower().split() if t and t not in _STOPWORDS]
            counts = Counter(tokens)
            for token, count in counts.items():
                idx = sum(ord(c) for c in token) % self.embedding_dim
                vectors[i, idx] += count
            norm = np.linalg.norm(vectors[i])
            if norm:
                vectors[i] /= norm
        return vectors


CORPUS: dict[str, str] = {
    "disc-grad-1": "topic gradient: gradient explosion in deep neural networks",
    "disc-grad-2": "topic gradient: exploding gradients during backpropagation",
    "disc-grad-3": "topic gradient: vanishing and exploding gradient problem",
    "disc-capital-1": "topic capital: capital reflux trap in emerging markets",
    "disc-capital-2": "topic capital: capital flight and reflux dynamics",
    "disc-capital-3": "topic capital: emerging market capital reflux cycle",
    "disc-attn-1": "topic attention: attention residual connection in transformers",
    "disc-attn-2": "topic attention: residual attention mechanism for deep nets",
    "disc-attn-3": "topic attention: transformer attention with residual links",
    "disc-matdo-1": "topic matdo: matdo fork kinetic consensus protocol",
    "disc-matdo-2": "topic matdo: kinetic fork resolution in matdo",
    "disc-matdo-3": "topic matdo: matdo protocol fork dynamics",
    "disc-weather-1": "topic weather: weather data retrieval from satellite sources",
    "disc-weather-2": "topic weather: satellite based weather data access",
    "disc-weather-3": "topic weather: retrieving weather records via satellite",
}


def corpus_group(adl_id: str) -> str:
    return adl_id.rsplit("-", 1)[0]
