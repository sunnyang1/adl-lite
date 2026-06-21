"""
Near-Duplicate Detection for ADL Lite.

Detects conceptually similar capabilities that may be near-duplicates
of existing entries. Uses simple string similarity and optional embedding
similarity (when sentence-transformers is available).

Paper §6.2: "Near-duplicate detection is available for merge suggestions."
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import ADLDocument, EventChain


def _normalize_name(name: str) -> str:
    """Normalize a name for comparison: lowercase, remove punctuation, collapse whitespace."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


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
    """
    Check if a candidate concept is a near-duplicate of any existing chain.

    Args:
        candidate: New ADLDocument or concept name string to check
        existing_chains: List of existing EventChains to compare against
        threshold: Similarity threshold (0-1); above this = near-duplicate
        method: "jaccard" or "levenshtein"

    Returns:
        List of match dicts: [{"concept_id": str, "similarity": float, "method": str}]
        Sorted by similarity descending.
    """
    if isinstance(candidate, str):
        candidate_name = candidate
    else:
        # Use English name if available, otherwise Chinese, otherwise concept_id
        candidate_name = (
            candidate.front_matter.provisional_names.en
            or candidate.front_matter.provisional_names.zh
            or candidate.adl_id
        )

    matches: list[dict] = []
    for chain in existing_chains:
        existing_name = chain.concept_id
        # Try to get a better name from the chain's markdown body or events
        for event in chain.events:
            if event.event_type.value == "snapshot":
                payload = event.payload
                if isinstance(payload, dict):
                    names = payload.get("provisional_names", {})
                    if isinstance(names, dict):
                        existing_name = names.get("en") or names.get("zh") or existing_name

        if method == "jaccard":
            similarity = _jaccard_similarity(candidate_name, existing_name)
        elif method == "levenshtein":
            similarity = _levenshtein_ratio(candidate_name, existing_name)
        else:
            similarity = _jaccard_similarity(candidate_name, existing_name)

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
    """
    Suggest a merge if a near-duplicate is detected.

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


# Optional: embedding-based similarity when sentence-transformers is available
try:
    from sentence_transformers import SentenceTransformer, util

    _EMBEDDING_MODEL = None

    def _get_embedding_model() -> SentenceTransformer:
        global _EMBEDDING_MODEL
        if _EMBEDDING_MODEL is None:
            _EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        return _EMBEDDING_MODEL

    def check_near_duplicate_embedding(
        candidate: ADLDocument | str,
        existing_chains: list[EventChain],
        threshold: float = 0.90,
    ) -> list[dict]:
        """Near-duplicate detection using sentence embeddings (requires sentence-transformers)."""
        if isinstance(candidate, str):
            candidate_text = candidate
        else:
            candidate_text = (
                candidate.front_matter.provisional_names.en
                or candidate.front_matter.provisional_names.zh
                or candidate.adl_id
            )

        model = _get_embedding_model()
        candidate_embedding = model.encode(candidate_text, convert_to_tensor=True)

        matches: list[dict] = []
        for chain in existing_chains:
            existing_text = chain.concept_id
            for event in chain.events:
                if event.event_type.value == "snapshot":
                    payload = event.payload
                    if isinstance(payload, dict):
                        names = payload.get("provisional_names", {})
                        if isinstance(names, dict):
                            existing_text = names.get("en") or names.get("zh") or existing_text

            existing_embedding = model.encode(existing_text, convert_to_tensor=True)
            similarity = float(util.pytorch_cos_sim(candidate_embedding, existing_embedding)[0][0])

            if similarity >= threshold:
                matches.append(
                    {
                        "concept_id": chain.concept_id,
                        "similarity": round(similarity, 4),
                        "method": "embedding",
                    }
                )

        matches.sort(key=lambda x: x["similarity"], reverse=True)
        return matches

except ImportError:
    # sentence-transformers not installed; embedding-based detection unavailable
    pass
