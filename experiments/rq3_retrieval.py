"""
RQ3: Retrieval Recall@k on AML query set.

- pilot: token overlap + relation boost
- phase_b: TF-IDF + L3 relation text + query-aligned / graph propagation boost
  vs fair plain (L2 only, L3 blocks stripped)
- phase_b+ (optional): sentence-transformers embedding or hybrid scorer
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Literal

from adl_lite import parse_file
from adl_lite.models import ADLDocument
from data.aml.loader import ensure_dataset, index_all, load_queries
from experiments.baselines.fair_plain import adl_to_fair_plain
from experiments.baselines.plain_markdown import index_plain_markdown
from experiments.embeddings import EmbeddingIndex, EmbeddingProvider, embeddings_available
from experiments.tfidf import TfidfIndex, _tokenize

Scorer = Literal["tfidf", "embedding", "hybrid"]

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "aml"

# Phase B graph boost: propagate score to relation targets in top pool
_GRAPH_NEIGHBOR_WEIGHT = 0.35
_RELATION_OVERLAP_WEIGHT = 0.3
_SCORE_EPS = 1e-12


def _tokenize_set(text: str) -> set[str]:
    return set(_tokenize(text))


def _target_concept_id(target: str) -> str | None:
    if target.startswith("adl://"):
        return target.rsplit("/", 1)[-1]
    return None


def build_concept_name_lookup(paths: list[Path]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for path in paths:
        doc = parse_file(path)
        lookup[doc.adl_id] = doc.concept_name
    return lookup


def _plain_index_text(path: Path) -> str:
    plain = adl_to_fair_plain(path)
    return f"{plain.concept_name} {plain.markdown_body}"


def adl_index_text(doc: ADLDocument, name_lookup: dict[str, str]) -> str:
    """ADL index: L2 + L3 relations (incl. resolved target concept names)."""
    parts = [doc.concept_name, doc.markdown_body]
    for rel in doc.relations:
        parts.append(rel.relation)
        if rel.mapping_type:
            parts.append(rel.mapping_type)
        tid = _target_concept_id(rel.target)
        if tid and tid in name_lookup:
            parts.append(name_lookup[tid])
            parts.append(tid.replace("-", " "))
        elif not rel.target.startswith("adl://"):
            parts.append(rel.target)
        else:
            parts.append(rel.target)
    return " ".join(parts)


def _relation_overlap_boost(doc: ADLDocument, query_tokens: set[str], name_lookup: dict[str, str]) -> float:
    if not query_tokens:
        return 0.0
    boost = 0.0
    for rel in doc.relations:
        tid = _target_concept_id(rel.target)
        extra = name_lookup.get(tid, "") if tid else rel.target
        rel_tokens = _tokenize_set(
            " ".join(filter(None, [rel.relation, rel.mapping_type, extra, rel.target]))
        )
        overlap = len(query_tokens & rel_tokens)
        if overlap:
            boost += _RELATION_OVERLAP_WEIGHT * overlap / len(query_tokens)
    return boost


def _graph_neighbor_boost(
    base_ranked: list[tuple[str, float]],
    docs_by_id: dict[str, ADLDocument],
    k: int,
) -> dict[str, float]:
    """Boost related concept ids linked from high-scoring ADL docs."""
    pool = base_ranked[: max(k, 3)]
    neighbor_boost: dict[str, float] = {}
    for doc_id, score in pool:
        if score <= 0:
            continue
        for rel in docs_by_id[doc_id].relations:
            tid = _target_concept_id(rel.target)
            if tid and tid in docs_by_id:
                neighbor_boost[tid] = max(
                    neighbor_boost.get(tid, 0.0),
                    score * _GRAPH_NEIGHBOR_WEIGHT,
                )
    return neighbor_boost


def _l3_boost(
    doc_id: str,
    docs_by_id: dict[str, ADLDocument],
    query_tokens: set[str],
    name_lookup: dict[str, str],
    neighbors: dict[str, float],
) -> float:
    doc = docs_by_id[doc_id]
    return neighbors.get(doc_id, 0.0) + _relation_overlap_boost(doc, query_tokens, name_lookup)


def _normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    mn = min(scores.values())
    mx = max(scores.values())
    span = mx - mn
    if span < _SCORE_EPS:
        return {doc_id: 0.0 for doc_id in scores}
    return {doc_id: (score - mn) / span for doc_id, score in scores.items()}


def _rank_adl(
    index: TfidfIndex,
    docs_by_id: dict[str, ADLDocument],
    name_lookup: dict[str, str],
    query: str,
    k: int,
    *,
    scorer: Scorer = "tfidf",
    embed_index: EmbeddingIndex | None = None,
) -> list[tuple[str, float]]:
    q_tokens = _tokenize_set(query)
    base = index.rank(query, k=k * 3)
    neighbors = _graph_neighbor_boost(base, docs_by_id, k)

    if scorer == "tfidf":

        def total_score(item: tuple[str, float]) -> float:
            doc_id, tfidf = item
            return tfidf + _l3_boost(doc_id, docs_by_id, q_tokens, name_lookup, neighbors)

        return sorted(base, key=total_score, reverse=True)

    doc_ids = [doc_id for doc_id, _ in base]
    tfidf_l3 = {
        doc_id: tfidf + _l3_boost(doc_id, docs_by_id, q_tokens, name_lookup, neighbors)
        for doc_id, tfidf in base
    }
    norm_tfidf_l3 = _normalize_scores(tfidf_l3)

    if scorer == "embedding":
        if embed_index is None:
            raise ValueError("embed_index required for embedding scorer")
        embed_ranked = embed_index.rank(query, k=len(docs_by_id))
        embed_map = dict(embed_ranked)
        final = {doc_id: embed_map.get(doc_id, 0.0) for doc_id in doc_ids}
    else:
        if embed_index is None:
            raise ValueError("embed_index required for hybrid scorer")
        embed_ranked = embed_index.rank(query, k=len(docs_by_id))
        norm_embed = _normalize_scores(dict(embed_ranked))
        final = {
            doc_id: norm_tfidf_l3.get(doc_id, 0.0) + 0.5 * norm_embed.get(doc_id, 0.0)
            for doc_id in doc_ids
        }

    ranked = sorted(((doc_id, final[doc_id]) for doc_id in doc_ids), key=lambda x: x[1], reverse=True)
    return ranked


def _top_hits(ranked: list[tuple[str, float]], k: int) -> set[str]:
    """Docs in top-k with strictly positive score (ignore tie-break noise at zero)."""
    return {doc_id for doc_id, score in ranked[:k] if score > _SCORE_EPS}


def _hit_recall(ranked: list[tuple[str, float]], relevant: set[str], k: int) -> float:
    top = _top_hits(ranked, k)
    return 1.0 if relevant & top else 0.0


def _label_recall(ranked: list[tuple[str, float]], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    top = _top_hits(ranked, k)
    return len(relevant & top) / len(relevant)


def recall_at_k_pilot(
    mem_paths: list[Path],
    queries: list[dict],
    k: int = 10,
    use_relations: bool = True,
) -> float:
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "idx.db")
        if use_relations:
            mem = index_all(db)
        else:
            mem = index_plain_markdown(mem_paths, db)

        hits = 0
        total = len(queries)
        for q in queries:
            q_tokens = {w.lower() for w in q["text"].split() if len(w) > 2}
            relevant = set(q["relevant"])
            scored: list[tuple[str, float]] = []

            for entry in mem.hot.filter():
                doc = mem.retrieve(entry.adl_id)
                if not doc:
                    continue
                text = doc.markdown_body + " " + doc.concept_name
                doc_tokens = {w.lower() for w in text.split() if len(w) > 2}
                overlap = len(q_tokens & doc_tokens) / max(len(q_tokens), 1)
                if use_relations:
                    overlap += 0.1 * len(doc.relations)
                scored.append((entry.adl_id, overlap))

            scored.sort(key=lambda x: x[1], reverse=True)
            top_ids = {s[0] for s in scored[:k]}
            if relevant & top_ids:
                hits += 1

        mem.close()
        return hits / max(total, 1)


def _scenario_queries(queries: list[dict]) -> list[dict]:
    return [q for q in queries if not q.get("l3_only")]


def _aggregate_recall(
    paths: list[Path],
    queries: list[dict],
    k: int,
    scorer: Scorer,
    embed_provider: EmbeddingProvider | None = None,
) -> dict[str, float]:
    name_lookup = build_concept_name_lookup(paths)
    docs_by_id: dict[str, ADLDocument] = {}
    adl_index = TfidfIndex()
    plain_index = TfidfIndex()
    embed_index: EmbeddingIndex | None = None

    for path in paths:
        doc = parse_file(path)
        docs_by_id[doc.adl_id] = doc
        adl_index.add(doc.adl_id, adl_index_text(doc, name_lookup))
        plain_index.add(doc.adl_id, _plain_index_text(path))

    if scorer in ("embedding", "hybrid"):
        embed_index = EmbeddingIndex(provider=embed_provider)
        for doc_id, doc in docs_by_id.items():
            embed_index.add(doc_id, adl_index_text(doc, name_lookup))
        embed_index.build()

    adl_hits = 0.0
    plain_hits = 0.0
    adl_label = 0.0
    plain_label = 0.0
    n = max(len(queries), 1)

    for q in queries:
        relevant = set(q["relevant"])
        adl_ranked = _rank_adl(
            adl_index,
            docs_by_id,
            name_lookup,
            q["text"],
            k,
            scorer=scorer,
            embed_index=embed_index,
        )
        plain_ranked = plain_index.rank(q["text"], k=k)

        adl_hits += _hit_recall(adl_ranked, relevant, k)
        plain_hits += _hit_recall(plain_ranked, relevant, k)
        adl_label += _label_recall(adl_ranked, relevant, k)
        plain_label += _label_recall(plain_ranked, relevant, k)

    return {
        "hit_adl": adl_hits / n,
        "hit_plain": plain_hits / n,
        "label_adl": adl_label / n,
        "label_plain": plain_label / n,
    }


def recall_at_k_tfidf_pair(
    paths: list[Path],
    queries: list[dict],
    k: int = 10,
    *,
    scorer: Scorer = "tfidf",
    embed_provider: EmbeddingProvider | None = None,
) -> dict[str, float]:
    """Return hit/label recall for ADL vs fair plain."""
    return _aggregate_recall(paths, queries, k, scorer, embed_provider)


def _scorer_label(scorer: Scorer) -> str:
    if scorer == "tfidf":
        return "tfidf_fair_plain"
    return f"{scorer}_fair_plain"


def run(
    mode: str = "pilot",
    k: int = 10,
    *,
    scorer: Scorer = "tfidf",
    embed_provider: EmbeddingProvider | None = None,
) -> dict:
    ensure_dataset()
    paths = [
        DATA / e["path"]
        for e in json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))["concepts"]
    ]
    queries = load_queries()

    if mode == "phase_b":
        if scorer in ("embedding", "hybrid") and embed_provider is None and not embeddings_available():
            raise ImportError(
                "sentence-transformers required for embedding/hybrid scorer; "
                "pip install adl-lite[experiments-embeddings]"
            )
        scores = recall_at_k_tfidf_pair(
            paths, queries, k=k, scorer=scorer, embed_provider=embed_provider
        )
        scenario = _scenario_queries(queries)
        scenario_scores = recall_at_k_tfidf_pair(
            paths, scenario, k=k, scorer=scorer, embed_provider=embed_provider
        )
        adl_recall = scores["hit_adl"]
        plain_recall = scores["hit_plain"]
        label_adl = scores["label_adl"]
        label_plain = scores["label_plain"]
        label = _scorer_label(scorer)
    else:
        adl_recall = recall_at_k_pilot(paths, queries, k=k, use_relations=True)
        plain_recall = recall_at_k_pilot(paths, queries, k=k, use_relations=False)
        label_adl = label_plain = 0.0
        scenario_scores = None
        label = "token_overlap"

    result = {
        "metric": f"recall_at_{k}",
        "scorer": label,
        "adl_recall": round(adl_recall, 4),
        "plain_baseline_recall": round(plain_recall, 4),
        "delta": round(adl_recall - plain_recall, 4),
        "label_recall_adl": round(label_adl, 4) if mode == "phase_b" else None,
        "label_recall_plain": round(label_plain, 4) if mode == "phase_b" else None,
        "label_recall_delta": round(label_adl - label_plain, 4) if mode == "phase_b" else None,
        "n_queries": len(queries),
        "pilot": mode == "pilot",
        "phase_b": mode == "phase_b",
    }
    if scenario_scores is not None:
        result["scenario_n_queries"] = len(scenario)
        result["scenario_hit_delta"] = round(
            scenario_scores["hit_adl"] - scenario_scores["hit_plain"], 4
        )
        result["scenario_label_delta"] = round(
            scenario_scores["label_adl"] - scenario_scores["label_plain"], 4
        )
    return result


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=("pilot", "phase_b"), default="pilot")
    p.add_argument("--scorer", choices=("tfidf", "embedding", "hybrid"), default="tfidf")
    p.add_argument("-k", type=int, default=10)
    args = p.parse_args()
    print(json.dumps(run(mode=args.mode, k=args.k, scorer=args.scorer), indent=2))
