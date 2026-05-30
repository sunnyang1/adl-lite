"""RQ3 embedding/hybrid scorer tests (no model download in CI)."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import pytest

from adl_lite import parse_file
from experiments.embeddings import EmbeddingIndex, embed_texts
from experiments.rq3_retrieval import (
    _normalize_scores,
    _rank_adl,
    adl_index_text,
    build_concept_name_lookup,
    run,
)
from experiments.tfidf import TfidfIndex


class _HashEmbedder:
    """Deterministic mock vectors from text hashes (no sentence-transformers)."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode()).digest()
            vec = [((b / 255.0) * 2 - 1) for b in digest[:16]]
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            out.append([v / norm for v in vec])
        return out


def test_embed_texts_import_error_without_provider(monkeypatch):
    monkeypatch.setattr("experiments.embeddings.embeddings_available", lambda: False)
    with pytest.raises(ImportError, match="sentence-transformers"):
        embed_texts(["hello"])


def test_normalize_scores():
    assert _normalize_scores({}) == {}
    assert _normalize_scores({"a": 1.0, "b": 1.0}) == {"a": 0.0, "b": 0.0}
    norm = _normalize_scores({"a": 0.0, "b": 10.0})
    assert norm["a"] == 0.0
    assert norm["b"] == 1.0


def test_embedding_index_mock_rank():
    provider = _HashEmbedder()
    idx = EmbeddingIndex(provider=provider)
    idx.add("a", "smurfing small deposit structuring")
    idx.add("b", "crypto mixer blockchain tumbler")
    idx.build()
    ranked = idx.rank("small deposit smurfing", k=1)
    assert ranked[0][0] == "a"


def test_hybrid_rank_adl_uses_mock_embedder():
    root = Path(__file__).resolve().parent.parent
    paths = [
        root / "data" / "aml" / "concepts" / "aml-smurfing.md",
        root / "data" / "aml" / "concepts" / "aml-crypto-mix.md",
    ]
    provider = _HashEmbedder()
    name_lookup = build_concept_name_lookup(paths)
    docs_by_id = {parse_file(p).adl_id: parse_file(p) for p in paths}

    tfidf = TfidfIndex()
    embed_index = EmbeddingIndex(provider=provider)
    for doc_id, doc in docs_by_id.items():
        text = adl_index_text(doc, name_lookup)
        tfidf.add(doc_id, text)
        embed_index.add(doc_id, text)
    embed_index.build()

    ranked = _rank_adl(
        tfidf,
        docs_by_id,
        name_lookup,
        "customer splits cash deposits staying below currency reporting threshold",
        k=1,
        scorer="hybrid",
        embed_index=embed_index,
    )
    assert ranked[0][0] == "aml-smurfing"


def test_phase_b_scenario_metrics_with_mock():
    out = run(mode="phase_b", k=10, scorer="hybrid", embed_provider=_HashEmbedder())
    assert out["phase_b"] is True
    assert out["scorer"] == "hybrid_fair_plain"
    assert out["scenario_n_queries"] == 20
    assert "scenario_hit_delta" in out
    assert "scenario_label_delta" in out
    assert out["scenario_label_delta"] >= 0
    assert out["scenario_subset"]["n_queries"] == 20
    assert out["l3_only_subset"]["n_queries"] == 5
