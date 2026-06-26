"""Near-Duplicate Detection for ADL Lite.

Detects conceptually similar capabilities that may be near-duplicates of
existing entries. Supports deterministic string similarity, embedding-based
semantic similarity, and a FAISS-backed :class:`VectorIndex` for scalable
search.

Paper §6.2: "Near-duplicate detection is available for merge suggestions."
"""

from __future__ import annotations

import re

from .models import (
    ADLActionBlock,
    ADLDocument,
    ADLEvidenceBlock,
    ADLFormalSealBlock,
    ADLRelationBlock,
    EventChain,
)


def _normalize_name(name: str) -> str:
    """Normalize a name for comparison: case-fold, remove punctuation, collapse whitespace.

    Keeps Unicode letters and digits so that CJK and other non-ASCII scripts
    are preserved.
    """
    name = name.casefold()
    name = re.sub(r"[^\w\s]", "", name, flags=re.UNICODE)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _extract_comparison_text(
    candidate: ADLDocument | EventChain | str, max_chars: int = 2000
) -> str:
    """Extract a single comparable text string from a document, chain, or name."""
    if isinstance(candidate, str):
        return candidate

    parts: list[str] = []

    if isinstance(candidate, ADLDocument):
        # ADLDocument path: prefer explicit names, fall back to adl_id
        names = candidate.front_matter.provisional_names
        if names:
            if names.en:
                parts.append(names.en)
            if names.zh:
                parts.append(names.zh)
        if not parts:
            parts.append(candidate.adl_id)
    else:
        # EventChain path: prefer names from SNAPSHOT-like payloads, fall back to concept_id
        for event in candidate.events:
            payload = event.payload or {}
            names = payload.get("provisional_names", {})
            if isinstance(names, dict):
                if names.get("en"):
                    parts.append(names["en"])
                if names.get("zh"):
                    parts.append(names["zh"])
        if not parts:
            parts.append(candidate.concept_id)

    text = " ".join(p for p in parts if p).strip()
    if len(text) > max_chars:
        text = text[:max_chars]
    return text


def _jaccard_similarity(a: str, b: str) -> float:
    """Compute Jaccard similarity between two strings (word-level)."""
    set_a = set(_normalize_name(a).split())
    set_b = set(_normalize_name(b).split())
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def _levenshtein_ratio(a: str, b: str) -> float:
    """Compute Levenshtein similarity ratio (0-1)."""
    import difflib

    return difflib.SequenceMatcher(None, a, b).ratio()


def check_near_duplicate(
    candidate: ADLDocument | str,
    existing_chains: list[EventChain],
    threshold: float = 0.85,
    method: str = "jaccard",
) -> list[dict]:
    """Check if a candidate concept is a near-duplicate of any existing chain.

    Args:
        candidate: New ADLDocument or concept name string to check.
        existing_chains: List of existing EventChains to compare against.
        threshold: Similarity threshold (0-1); above this = near-duplicate.
        method: "jaccard", "levenshtein", or "embedding".

    Returns:
        List of match dicts sorted by similarity descending:
        ``{"concept_id": str, "similarity": float, "method": str}``.
    """
    if method == "embedding":
        return check_near_duplicate_embedding(candidate, existing_chains, threshold=threshold)

    candidate_text = _extract_comparison_text(candidate)

    matches: list[dict] = []
    for chain in existing_chains:
        existing_text = _extract_comparison_text(chain)

        if method == "levenshtein":
            similarity = _levenshtein_ratio(candidate_text, existing_text)
        else:
            similarity = _jaccard_similarity(candidate_text, existing_text)

        if similarity >= threshold:
            matches.append(
                {
                    "concept_id": chain.concept_id,
                    "similarity": round(similarity, 4),
                    "method": method,
                }
            )

    matches.sort(key=lambda x: x["similarity"], reverse=True)
    return matches


def suggest_merge(
    candidate: ADLDocument | str,
    existing_chains: list[EventChain],
    threshold: float = 0.85,
) -> dict | None:
    """Suggest a merge if a near-duplicate is detected.

    Returns:
        Merge suggestion dict or None if no near-duplicate found.
    """
    matches = check_near_duplicate(candidate, existing_chains, threshold=threshold)
    if not matches:
        return None

    best_match = matches[0]
    return {
        "action": "suggest_merge",
        "candidate": candidate.adl_id if hasattr(candidate, "adl_id") else candidate,
        "target_concept_id": best_match["concept_id"],
        "similarity": best_match["similarity"],
        "reasoning": (
            f"Near-duplicate detected with similarity {best_match['similarity']}. "
            f"Consider merging or forking."
        ),
    }


def _extract_embedding_text(
    candidate: ADLDocument | EventChain | str, max_chars: int = 2000
) -> str:
    """Extract a rich text representation for dense embedding comparison."""
    if isinstance(candidate, str):
        return candidate

    parts: list[str] = []

    if isinstance(candidate, ADLDocument):
        names = candidate.front_matter.provisional_names
        if names:
            if names.en:
                parts.append(names.en)
            if names.zh:
                parts.append(names.zh)

        body = candidate.markdown_body or ""
        if body:
            parts.append(body)

        for block in getattr(candidate, "adl_blocks", []) or []:
            if isinstance(block, ADLRelationBlock):
                parts.append(f"{block.source} {block.relation} {block.target}")
            elif isinstance(block, ADLEvidenceBlock) and block.description:
                parts.append(block.description)
            elif isinstance(block, ADLFormalSealBlock) and block.assertion:
                parts.append(block.assertion)

        for action in getattr(candidate, "action_blocks", []) or []:
            if isinstance(action, ADLActionBlock) and action.reasoning:
                parts.append(action.reasoning)

        if not parts:
            parts.append(candidate.adl_id)
    else:
        # EventChain path: prefer names from SNAPSHOT-like payloads, fall back to concept_id
        for event in candidate.events:
            payload = event.payload or {}
            names = payload.get("provisional_names", {})
            if isinstance(names, dict):
                if names.get("en"):
                    parts.append(names["en"])
                if names.get("zh"):
                    parts.append(names["zh"])
        if not parts:
            parts.append(candidate.concept_id)

    text = " ".join(p for p in parts if p).strip()
    if len(text) > max_chars:
        text = text[:max_chars]
    return text


def check_near_duplicate_embedding(
    candidate: ADLDocument | str,
    existing_chains: list[EventChain] | None = None,
    threshold: float = 0.90,
    backend=None,
    vector_index=None,
    top_k: int = 10,
) -> list[dict]:
    """Near-duplicate detection using dense embeddings.

    Args:
        candidate: New ADLDocument or concept name string to check.
        existing_chains: List of existing EventChains to compare against.
            Required for the one-shot path; optional when ``vector_index`` is
            provided.
        threshold: Cosine similarity threshold.
        backend: Optional EmbeddingBackend. If None, uses the default backend.
        vector_index: Optional VectorIndex for repeated searches. If provided,
            ``existing_chains`` is used only to bound ``top_k`` when no explicit
            ``top_k`` is supplied.
        top_k: Maximum number of results to return.

    Returns:
        List of match dicts sorted by similarity descending.
    """
    from .embeddings import get_default_embedding_backend
    from .vector_index import VectorIndex

    emb_backend = backend or get_default_embedding_backend()
    candidate_text = _extract_embedding_text(candidate)

    if vector_index is not None:
        search_top_k = top_k
        if existing_chains is not None:
            search_top_k = max(top_k, len(existing_chains))
        results = vector_index.search(candidate_text, top_k=search_top_k, threshold=threshold)
        return [
            {"concept_id": r["adl_id"], "similarity": r["similarity"], "method": "embedding"}
            for r in results
        ]

    # One-shot path: build a temporary index from existing chains and search it.
    if existing_chains is None:
        return []
    texts = {chain.concept_id: _extract_embedding_text(chain) for chain in existing_chains}
    if not texts:
        return []

    index = VectorIndex(backend=emb_backend)
    index.add_many(texts)
    results = index.search(candidate_text, top_k=max(top_k, len(texts)), threshold=threshold)
    return [
        {"concept_id": r["adl_id"], "similarity": r["similarity"], "method": "embedding"}
        for r in results
    ]
