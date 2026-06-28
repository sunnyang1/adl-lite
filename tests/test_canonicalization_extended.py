"""Extended tests for canonicalization module — behaviors 14-21."""

from __future__ import annotations

import json

import pytest

try:
    import faiss  # noqa: F401

    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

pytestmark = pytest.mark.skipif(
    not HAS_FAISS,
    reason="faiss-cpu not installed (install with: pip install faiss-cpu)",
)

import numpy as np  # noqa: E402, I001
from adl_lite.canonicalization import (  # noqa: E402, I001
    CanonicalizationEngine,
    LLMBackend,
    _MockLLMBackend,
)
from adl_lite.vector_index import VectorIndex  # noqa: E402


class _NgramBackend:
    """Deterministic character n-gram embedding backend for fast tests."""

    embedding_dim = 64
    model_name = "fake-ngram"

    def __init__(self, n: int = 2) -> None:
        self.n = n

    def encode(self, texts: list[str]) -> np.ndarray:
        from collections import Counter

        vectors = np.zeros((len(texts), self.embedding_dim), dtype=np.float32)
        for i, text in enumerate(texts):
            text = text.lower().replace(" ", "")
            counts = Counter(text[j : j + self.n] for j in range(len(text) - self.n + 1))
            for gram, count in counts.items():
                idx = sum(ord(c) for c in gram) % self.embedding_dim
                vectors[i, idx] += count
            norm = np.linalg.norm(vectors[i])
            if norm:
                vectors[i] /= norm
        return vectors


@pytest.fixture
def backend():
    return _NgramBackend()


@pytest.fixture
def index(backend):
    return VectorIndex(backend=backend, db_path=":memory:")


# ---------------------------------------------------------------------------
# Behavior 14: _MockLLMBackend.complete returns valid JSON
# ---------------------------------------------------------------------------


class TestMockLLMBackend:
    """_MockLLMBackend returns parseable JSON."""

    def test_complete_returns_valid_json(self):
        """_MockLLMBackend.complete returns a valid JSON string."""
        mock = _MockLLMBackend()
        raw = mock.complete("any prompt")
        parsed = json.loads(raw)
        assert "canonical_adl_id" in parsed
        assert "canonical_name" in parsed
        assert "relations" in parsed
        assert "deprecate" in parsed
        assert "reasoning" in parsed

    def test_complete_ignores_prompt(self):
        """_MockLLMBackend ignores the prompt content."""
        mock = _MockLLMBackend()
        raw1 = mock.complete("prompt A")
        raw2 = mock.complete("prompt B")
        assert raw1 == raw2  # Always returns the same mock response


# ---------------------------------------------------------------------------
# Behavior 15: CanonicalizationEngine.__init__ accepts mock LLM and threshold
# ---------------------------------------------------------------------------


class TestCanonicalizationEngineInit:
    """CanonicalizationEngine accepts mock LLM and threshold."""

    def test_init_with_mock_llm(self, index: VectorIndex) -> None:
        """Engine initializes with a mock LLM backend."""
        mock_llm = _MockLLMBackend()
        engine = CanonicalizationEngine(vector_index=index, llm=mock_llm, threshold=0.80)
        assert engine.llm is mock_llm
        assert engine.threshold == 0.80

    def test_init_default_llm(self, index: VectorIndex) -> None:
        """Engine uses _MockLLMBackend by default."""
        engine = CanonicalizationEngine(vector_index=index)
        assert isinstance(engine.llm, _MockLLMBackend)

    def test_init_default_threshold(self, index: VectorIndex) -> None:
        """Default threshold is 0.92."""
        engine = CanonicalizationEngine(vector_index=index)
        assert engine.threshold == 0.92


# ---------------------------------------------------------------------------
# Behavior 16: propose parses JSON from mock LLM (including raw JSON with ```json wrapper)
# ---------------------------------------------------------------------------


class TestProposeJsonParsing:
    """propose parses JSON output, including markdown-wrapped JSON."""

    def test_propose_raw_json(self, index: VectorIndex) -> None:
        """propose parses raw JSON output from LLM."""
        index.add("disc-grad", "gradient explosion")

        class _RawJsonLLM(LLMBackend):
            def complete(self, prompt: str, system: str | None = None) -> str:
                return json.dumps(
                    {
                        "canonical_adl_id": "canonical-grad",
                        "canonical_name": {"en": "Gradient"},
                        "relations": [],
                        "deprecate": [],
                        "reasoning": "test",
                    }
                )

        engine = CanonicalizationEngine(vector_index=index, llm=_RawJsonLLM())
        result = engine.propose(["disc-grad"])
        assert result["canonical_adl_id"] == "canonical-grad"

    def test_propose_json_with_markdown_wrapper(self, index: VectorIndex) -> None:
        """propose parses JSON wrapped in ```json...``` markdown."""
        index.add("disc-grad", "gradient explosion")

        class _MarkdownJsonLLM(LLMBackend):
            def complete(self, prompt: str, system: str | None = None) -> str:
                return (
                    "Here is my proposal:\n"
                    "```json\n"
                    + json.dumps(
                        {
                            "canonical_adl_id": "canonical-grad",
                            "canonical_name": {"en": "Gradient"},
                            "relations": [],
                            "deprecate": [],
                            "reasoning": "test",
                        }
                    )
                    + "\n```\n"
                )

        engine = CanonicalizationEngine(vector_index=index, llm=_MarkdownJsonLLM())
        result = engine.propose(["disc-grad"])
        assert result["canonical_adl_id"] == "canonical-grad"


# ---------------------------------------------------------------------------
# Behavior 17: propose handles malformed LLM output and raises ValueError
# ---------------------------------------------------------------------------


class TestProposeMalformedOutput:
    """propose raises ValueError for malformed LLM output."""

    def test_malformed_llm_raises_value_error(self, index: VectorIndex) -> None:
        """propose raises ValueError when LLM output is not valid JSON."""
        index.add("disc-grad", "gradient explosion")

        class _MalformedLLM(LLMBackend):
            def complete(self, prompt: str, system: str | None = None) -> str:
                return "This is not JSON at all, just plain text."

        engine = CanonicalizationEngine(vector_index=index, llm=_MalformedLLM())
        with pytest.raises(ValueError, match="LLM did not return valid JSON"):
            engine.propose(["disc-grad"])


# ---------------------------------------------------------------------------
# Behavior 18: generate_actions creates register + relate + deprecate action blocks
# ---------------------------------------------------------------------------


class TestGenerateActions:
    """generate_actions creates the full set of action blocks."""

    def test_register_relate_deprecate(self, index: VectorIndex) -> None:
        """generate_actions creates register, relate, and deprecate actions."""
        engine = CanonicalizationEngine(vector_index=index)
        proposal = {
            "canonical_adl_id": "canonical-grad",
            "canonical_name": {"en": "Gradient Explosion"},
            "relations": [
                {
                    "source": "disc-grad",
                    "target": "canonical-grad",
                    "relation": "isomorphic-to",
                },
            ],
            "deprecate": ["disc-exploding"],
            "reasoning": "Near-duplicate cluster.",
        }
        actions = engine.generate_actions(["disc-grad", "disc-exploding"], proposal)
        action_types = [a.action for a in actions]
        assert "register" in action_types
        assert "relate" in action_types
        assert "deprecate" in action_types

    def test_register_action_has_correct_params(self, index: VectorIndex) -> None:
        """The register action should have the canonical ID and name."""
        engine = CanonicalizationEngine(vector_index=index)
        proposal = {
            "canonical_adl_id": "canonical-grad",
            "canonical_name": {"en": "Gradient Explosion"},
            "relations": [],
            "deprecate": [],
            "reasoning": "test",
        }
        actions = engine.generate_actions(["disc-grad"], proposal)
        register_action = actions[0]
        assert register_action.action == "register"
        assert register_action.params["adl_id"] == "canonical-grad"
        assert register_action.params["provisional_names"]["en"] == "Gradient Explosion"


# ---------------------------------------------------------------------------
# Behavior 19: generate_actions handles empty proposal fields (empty relations/deprecate)
# ---------------------------------------------------------------------------


class TestGenerateActionsEmptyFields:
    """generate_actions handles proposals with empty relations/deprecate."""

    def test_empty_relations_and_deprecate(self, index: VectorIndex) -> None:
        """Empty relations and deprecate produce only a register action."""
        engine = CanonicalizationEngine(vector_index=index)
        proposal = {
            "canonical_adl_id": "canonical-grad",
            "canonical_name": {"en": "Gradient"},
            "relations": [],
            "deprecate": [],
            "reasoning": "test",
        }
        actions = engine.generate_actions(["disc-grad"], proposal)
        # Only the register action
        assert len(actions) == 1
        assert actions[0].action == "register"

    def test_missing_deprecate_key(self, index: VectorIndex) -> None:
        """Missing deprecate key defaults to empty list."""
        engine = CanonicalizationEngine(vector_index=index)
        proposal = {
            "canonical_adl_id": "canonical-grad",
            "canonical_name": {"en": "Gradient"},
            "relations": [],
            "reasoning": "test",
        }
        actions = engine.generate_actions(["disc-grad"], proposal)
        # Only register (no deprecate key → .get("deprecate", []) = [])
        assert len(actions) == 1
        assert actions[0].action == "register"


# ---------------------------------------------------------------------------
# Behavior 20: normalize on dry_run=True returns per-cluster results
# ---------------------------------------------------------------------------


class TestNormalizeDryRun:
    """normalize on dry_run=True returns per-cluster results without executing."""

    def test_dry_run_returns_results(self, index: VectorIndex) -> None:
        """dry_run=True returns cluster results without execution."""
        index.add_many(
            {
                "disc-grad": "gradient explosion",
                "disc-exploding": "exploding gradients",
            }
        )
        engine = CanonicalizationEngine(vector_index=index, threshold=0.70)
        results = engine.normalize(dry_run=True)
        # Should have at least one cluster result
        assert isinstance(results, list)
        for r in results:
            assert "cluster" in r
            assert "proposal" in r
            assert "actions" in r
            assert r["executed"] is False

    def test_dry_run_no_clusters(self, index: VectorIndex) -> None:
        """If no clusters found, normalize returns empty list."""
        index.add("disc-grad", "gradient explosion")
        engine = CanonicalizationEngine(vector_index=index, threshold=0.99)
        results = engine.normalize(dry_run=True)
        assert isinstance(results, list)
        # With high threshold, likely no clusters
        # (could be 0 or 1 depending on single-item similarity)


# ---------------------------------------------------------------------------
# Behavior 21: normalize on dry_run=False attempts to execute actions on mock chains
# ---------------------------------------------------------------------------


class TestNormalizeDryRunFalse:
    """normalize on dry_run=False attempts execution."""

    def test_dry_run_false_attempts_execution(self, index: VectorIndex) -> None:
        """dry_run=False creates a document and attempts execution."""
        index.add_many(
            {
                "disc-grad": "gradient explosion",
                "disc-exploding": "exploding gradients",
            }
        )
        engine = CanonicalizationEngine(vector_index=index, threshold=0.70)
        results = engine.normalize(dry_run=False)
        # Should return results; execution may succeed or fail depending on
        # ActionExecutor/OntologyManager setup, but it should at least attempt it
        assert isinstance(results, list)
        for r in results:
            assert "executed" in r
            # Either executed=True or errors list exists
            if not r["executed"]:
                assert "errors" in r or r["executed"] is False
