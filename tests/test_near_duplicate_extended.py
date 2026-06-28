"""Extended tests for near_duplicate module — behaviors 1-13."""

from __future__ import annotations

import pytest

from adl_lite.models import (
    ADLDocument,
    ADLFrontMatter,
    ADLType,
    Event,
    EventChain,
    EventType,
    ProvisionalNames,
)
from adl_lite.near_duplicate import (
    _extract_comparison_text,
    _normalize_name,
    check_near_duplicate,
    check_near_duplicate_embedding,
    suggest_merge,
)

# ---------------------------------------------------------------------------
# Behavior 1: _normalize_name preserves Unicode/CJK, strips punctuation, folds case
# ---------------------------------------------------------------------------


class TestNormalizeNameExtended:
    """Extended _normalize_name tests covering Unicode/CJK, punctuation, case-fold."""

    def test_preserves_cjk_characters(self):
        """CJK characters should remain after normalization."""
        result = _normalize_name("梯度爆炸")
        assert "梯" in result
        assert "度" in result
        assert "爆" in result
        assert "炸" in result

    def test_preserves_unicode_letters(self):
        """General Unicode letters (e.g., accented) are preserved after casefold."""
        result = _normalize_name("Überflüssig")
        assert "ü" in result  # casefolded ü remains
        # casefold preserves ß on most Python versions (ß → ß, not "ss")
        # The ß character is a Unicode letter that _normalize_name keeps
        assert "überflüssig" in result or "überflussig" in result

    def test_strips_punctuation(self):
        """Punctuation characters should be removed."""
        result = _normalize_name("Hello, World! (test)")
        # Comma, exclamation, parens removed; case-folded
        assert "," not in result
        assert "!" not in result
        assert "(" not in result
        assert ")" not in result

    def test_folds_case(self):
        """Mixed case should be folded to lowercase."""
        result = _normalize_name("UPPER lower MiXed")
        assert result == "upper lower mixed"

    def test_collapses_whitespace(self):
        """Multiple whitespace chars collapse to single space."""
        result = _normalize_name("a   b\t\nc")
        assert result == "a b c"

    def test_mixed_unicode_and_punctuation(self):
        """CJK with punctuation — punctuation stripped, CJK kept."""
        result = _normalize_name("梯度-爆炸！")
        assert "梯" in result
        assert "度" in result
        assert "爆" in result
        assert "炸" in result
        assert "-" not in result
        assert "！" not in result


# ---------------------------------------------------------------------------
# Behavior 2: _extract_comparison_text from ADLDocument returns provisional_names.en
# ---------------------------------------------------------------------------


class TestExtractComparisonTextADLDocument:
    """Test _extract_comparison_text with ADLDocument input."""

    def _make_doc(
        self,
        adl_id: str = "test-doc",
        en_name: str | None = None,
        zh_name: str | None = None,
    ) -> ADLDocument:
        fm = ADLFrontMatter(
            adl_type=ADLType.CONCEPT,
            adl_id=adl_id,
            provisional_names=ProvisionalNames(en=en_name, zh=zh_name),
        )
        return ADLDocument(front_matter=fm, markdown_body="", adl_blocks=[], action_blocks=[])

    def test_returns_en_name(self):
        """ADLDocument with provisional_names.en should return the English name."""
        doc = self._make_doc(adl_id="fallback-id", en_name="Gradient Explosion")
        text = _extract_comparison_text(doc)
        assert "gradient explosion" in text.casefold()

    def test_fallback_to_adl_id_when_no_names(self):
        """When provisional_names has no en, fallback to adl_id."""
        doc = self._make_doc(adl_id="my-concept-id", en_name=None, zh_name=None)
        text = _extract_comparison_text(doc)
        assert "my-concept-id" in text

    def test_zh_name_also_included(self):
        """Both en and zh names are included in the text."""
        doc = self._make_doc(adl_id="test", en_name="Gradient", zh_name="梯度")
        text = _extract_comparison_text(doc)
        assert "gradient" in text.casefold()
        assert "梯度" in text


# ---------------------------------------------------------------------------
# Behavior 3: _extract_comparison_text from EventChain payload returns name, fallback concept_id
# ---------------------------------------------------------------------------


class TestExtractComparisonTextEventChain:
    """Test _extract_comparison_text with EventChain input."""

    def _make_chain_with_name(self, concept_id: str, en_name: str) -> EventChain:
        chain = EventChain(concept_id=concept_id)
        chain.append(
            Event(
                concept_id=concept_id,
                event_type=EventType.SNAPSHOT,
                actor="system",
                payload={"provisional_names": {"en": en_name, "zh": None}},
            )
        )
        return chain

    def _make_chain_no_name(self, concept_id: str) -> EventChain:
        chain = EventChain(concept_id=concept_id)
        # No provisional_names in payload
        chain.append(
            Event(
                concept_id=concept_id,
                event_type=EventType.REGISTER,
                actor="system",
                payload={},
            )
        )
        return chain

    def test_returns_payload_name(self):
        """EventChain with provisional_names.en in payload returns that name."""
        chain = self._make_chain_with_name("my-concept", "Gradient Explosion")
        text = _extract_comparison_text(chain)
        assert "gradient explosion" in text.casefold()

    def test_fallback_to_concept_id(self):
        """When payload has no names, fallback to concept_id."""
        chain = self._make_chain_no_name("my-concept-id")
        text = _extract_comparison_text(chain)
        assert "my-concept-id" in text


# ---------------------------------------------------------------------------
# Behavior 4: _extract_comparison_text truncates length > max_chars
# ---------------------------------------------------------------------------


class TestExtractComparisonTextTruncation:
    """Test truncation of comparison text beyond max_chars."""

    def test_truncates_long_text_from_event_chain(self):
        """Text derived from EventChain longer than max_chars is truncated."""
        # Create a chain with a very long name in payload
        long_name = "a" * 3000
        chain = EventChain(concept_id="test")
        chain.append(
            Event(
                concept_id="test",
                event_type=EventType.SNAPSHOT,
                actor="system",
                payload={"provisional_names": {"en": long_name}},
            )
        )
        result = _extract_comparison_text(chain, max_chars=2000)
        assert len(result) <= 2000

    def test_short_text_not_truncated(self):
        """Text shorter than max_chars is not truncated."""
        short_str = "hello world"
        result = _extract_comparison_text(short_str, max_chars=2000)
        assert result == "hello world"
        assert len(result) == len(short_str)


# ---------------------------------------------------------------------------
# Behavior 5: check_near_duplicate with jaccard method and empty existing_chains returns []
# ---------------------------------------------------------------------------


class TestCheckNearDuplicateEmptyChains:
    """Edge case: empty existing_chains list."""

    def test_jaccard_empty_chains(self):
        """check_near_duplicate with jaccard and empty chains returns []."""
        result = check_near_duplicate("anything", [], method="jaccard")
        assert result == []


# ---------------------------------------------------------------------------
# Behavior 6: check_near_duplicate with levenshtein method returns matches sorted by similarity
# ---------------------------------------------------------------------------


class TestCheckNearDuplicateLevenshtein:
    """Levenshtein method returns matches sorted by similarity."""

    def _make_chain(self, concept_id: str, name: str) -> EventChain:
        chain = EventChain(concept_id=concept_id)
        chain.append(
            Event(
                concept_id=concept_id,
                event_type=EventType.SNAPSHOT,
                actor="system",
                payload={"provisional_names": {"en": name}},
            )
        )
        return chain

    def test_levenshtein_sorted_by_similarity(self):
        """Levenshtein matches should be sorted by similarity descending."""
        chains = [
            self._make_chain("c1", "Gradient Explosion"),
            self._make_chain("c2", "Gradient"),
            self._make_chain("c3", "Something Completely Different"),
        ]
        matches = check_near_duplicate(
            "Gradient Explosion", chains, threshold=0.4, method="levenshtein"
        )
        # Should be sorted by similarity descending
        sims = [m["similarity"] for m in matches]
        for i in range(len(sims) - 1):
            assert sims[i] >= sims[i + 1]
        # All have method "levenshtein"
        assert all(m["method"] == "levenshtein" for m in matches)


# ---------------------------------------------------------------------------
# Behavior 7: check_near_duplicate with below-threshold matches returns []
# ---------------------------------------------------------------------------


class TestCheckNearDuplicateBelowThreshold:
    """Below-threshold matches are filtered out."""

    def _make_chain(self, concept_id: str, name: str) -> EventChain:
        chain = EventChain(concept_id=concept_id)
        chain.append(
            Event(
                concept_id=concept_id,
                event_type=EventType.SNAPSHOT,
                actor="system",
                payload={"provisional_names": {"en": name}},
            )
        )
        return chain

    def test_below_threshold_returns_empty(self):
        """Matches below threshold should be filtered out."""
        chains = [self._make_chain("c1", "Completely Different Topic")]
        # High threshold — very different strings won't match
        result = check_near_duplicate("gradient explosion", chains, threshold=0.95)
        assert result == []


# ---------------------------------------------------------------------------
# Behavior 8: suggest_merge returns None when no matches
# ---------------------------------------------------------------------------


class TestSuggestMergeNoMatch:
    """suggest_merge returns None when no near-duplicates found."""

    def test_suggest_merge_returns_none(self):
        """When no matches, suggest_merge should return None."""
        result = suggest_merge("unique concept", [], threshold=0.85)
        assert result is None


# ---------------------------------------------------------------------------
# Behavior 9: suggest_merge returns merge suggestion dict with best match
# ---------------------------------------------------------------------------


class TestSuggestMergeWithMatch:
    """suggest_merge returns a merge suggestion dict."""

    def _make_chain(self, concept_id: str, name: str) -> EventChain:
        chain = EventChain(concept_id=concept_id)
        chain.append(
            Event(
                concept_id=concept_id,
                event_type=EventType.SNAPSHOT,
                actor="system",
                payload={"provisional_names": {"en": name}},
            )
        )
        return chain

    def test_suggest_merge_returns_dict(self):
        """suggest_merge returns a dict with expected keys."""
        chains = [self._make_chain("target-id", "Gradient Explosion")]
        result = suggest_merge("gradient explosion", chains, threshold=0.85)
        assert result is not None
        assert result["action"] == "suggest_merge"
        assert result["target_concept_id"] == "target-id"
        assert "similarity" in result
        assert "reasoning" in result
        assert isinstance(result["similarity"], float)


# ---------------------------------------------------------------------------
# Behavior 10: check_near_duplicate with string candidates (not ADLDocument)
# ---------------------------------------------------------------------------


class TestCheckNearDuplicateStringCandidate:
    """String candidates are handled correctly."""

    def _make_chain(self, concept_id: str, name: str) -> EventChain:
        chain = EventChain(concept_id=concept_id)
        chain.append(
            Event(
                concept_id=concept_id,
                event_type=EventType.SNAPSHOT,
                actor="system",
                payload={"provisional_names": {"en": name}},
            )
        )
        return chain

    def test_string_candidate(self):
        """A plain string candidate should work with check_near_duplicate."""
        chains = [self._make_chain("c1", "Gradient Explosion")]
        matches = check_near_duplicate("gradient explosion", chains, threshold=0.85)
        assert len(matches) == 1
        assert matches[0]["concept_id"] == "c1"


# ---------------------------------------------------------------------------
# Behavior 11: check_near_duplicate_embedding with vector_index=None and existing_chains=None
# ---------------------------------------------------------------------------


class TestNearDuplicateEmbeddingEdgeCases:
    """Edge cases for embedding-based near-duplicate detection."""

    def test_vector_index_none_chains_none_returns_empty(self):
        """When both vector_index and existing_chains are None, return []."""
        # We need to mock the embedding backend since get_default_embedding_backend
        # will raise ImportError when sentence-transformers is unavailable.
        # Use a mock backend to avoid the import.
        from unittest.mock import MagicMock

        mock_backend = MagicMock()
        mock_backend.embedding_dim = 8
        mock_backend.model_name = "mock"
        mock_backend.encode = MagicMock(return_value=__import__("numpy").zeros((1, 8)))

        # With vector_index=None and existing_chains=None → returns []
        result = check_near_duplicate_embedding(
            "test", existing_chains=None, backend=mock_backend, vector_index=None
        )
        assert result == []


# ---------------------------------------------------------------------------
# Behavior 12: check_near_duplicate_embedding with mock vector_index.search returns formatted
# ---------------------------------------------------------------------------


class TestNearDuplicateEmbeddingWithMockIndex:
    """Mock vector_index.search should produce formatted results."""

    def test_mock_vector_index_search(self):
        """When a mock vector_index provides search results, they are formatted correctly."""
        from unittest.mock import MagicMock

        mock_index = MagicMock()
        mock_index.search.return_value = [
            {"adl_id": "concept-1", "similarity": 0.95},
            {"adl_id": "concept-2", "similarity": 0.80},
        ]

        result = check_near_duplicate_embedding(
            "test query", existing_chains=None, backend=MagicMock(), vector_index=mock_index
        )
        assert len(result) == 2
        assert result[0]["concept_id"] == "concept-1"
        assert result[0]["similarity"] == 0.95
        assert result[0]["method"] == "embedding"
        assert result[1]["concept_id"] == "concept-2"
        assert result[1]["method"] == "embedding"


# ---------------------------------------------------------------------------
# Behavior 13: Mock backend: in-memory VectorIndex build and search
# ---------------------------------------------------------------------------


try:
    import faiss  # noqa: F401

    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False


@pytest.mark.skipif(not HAS_FAISS, reason="faiss-cpu not installed")
class TestInMemoryVectorIndexBuildAndSearch:
    """Build an in-memory VectorIndex with mock backend and search."""

    def test_in_memory_build_and_search(self):
        """VectorIndex with mock backend can build and search."""
        import numpy as np

        from adl_lite.vector_index import VectorIndex

        class _MockEmbBackend:
            embedding_dim = 16
            model_name = "mock-emb"

            def encode(self, texts: list[str]) -> np.ndarray:
                vectors = np.zeros((len(texts), self.embedding_dim), dtype=np.float32)
                for i, text in enumerate(texts):
                    # Simple deterministic encoding: hash-based
                    for j, ch in enumerate(text[: self.embedding_dim]):
                        vectors[i, j % self.embedding_dim] = ord(ch) / 128.0
                norms = np.linalg.norm(vectors, axis=1, keepdims=True)
                norms[norms == 0] = 1
                vectors /= norms
                return vectors

        backend = _MockEmbBackend()
        index = VectorIndex(backend=backend, db_path=":memory:")
        index.add_many({"c1": "gradient explosion", "c2": "capital reflux"})
        results = index.search("gradient explosion", top_k=2)
        assert len(results) >= 1
        assert results[0]["adl_id"] == "c1"
        assert results[0]["similarity"] > 0.5
        index.close()
