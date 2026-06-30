"""LLM-driven canonicalization workflow for ADL Lite.

Clusters near-duplicate concepts using a vector index, asks an LLM to propose a
canonical form and inter-concept relations, and emits auditable ADL action
blocks. All mutations are gated: by default the workflow is dry-run; callers
must explicitly execute the generated actions.
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import networkx as nx

if TYPE_CHECKING:
    from .models import ADLActionBlock
    from .vector_index import VectorIndex


@runtime_checkable
class LLMBackend(Protocol):
    """Minimal protocol for an LLM used by the canonicalization workflow."""

    def complete(self, prompt: str, system: str | None = None) -> str: ...


class _MockLLMBackend:
    """Placeholder backend for tests and dry-run demos."""

    def complete(self, prompt: str, system: str | None = None) -> str:  # noqa: ARG002
        return json.dumps(
            {
                "canonical_adl_id": "canonical-concept",
                "canonical_name": {"en": "Canonical Concept"},
                "relations": [],
                "deprecate": [],
                "reasoning": "No LLM configured; mock response.",
            }
        )


class OpenAILLMBackend:
    """OpenAI backend for canonicalization with simple retry/backoff."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        client: object | None = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> None:
        self._model = model
        self._client = client
        self._max_retries = max_retries
        self._base_delay = base_delay

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import openai
            except ImportError as exc:
                raise ImportError(
                    "openai is required for OpenAILLMBackend. "
                    'Install it with: pip install -e ".[embeddings]"'
                ) from exc
            self._client = openai.OpenAI()
        return self._client

    def complete(self, prompt: str, system: str | None = None) -> str:
        client = self._get_client()
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                response = client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=0.0,
                )
                return str(response.choices[0].message.content)
            except Exception as exc:
                last_exc = exc
                # Only retry on rate-limit or transient API errors.
                import openai

                if not isinstance(
                    exc, openai.RateLimitError | openai.APIError | openai.APITimeoutError
                ):
                    break
                if attempt < self._max_retries - 1:
                    time.sleep(self._base_delay * (2**attempt))

        raise RuntimeError(
            f"OpenAI request failed after {self._max_retries} attempt(s): {last_exc}"
        ) from last_exc


class AnthropicLLMBackend:
    """Anthropic backend for canonicalization with retry/backoff.

    Implements the LLMBackend protocol using the Anthropic Messages API.
    Requires ``anthropic>=0.25`` (the ``[experiments]`` extra).
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        client: object | None = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> None:
        self._model = model
        self._client = client
        self._max_retries = max_retries
        self._base_delay = base_delay

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import anthropic
            except ImportError as exc:
                raise ImportError(
                    "anthropic is required for AnthropicLLMBackend. "
                    'Install it with: pip install -e ".[experiments]"'
                ) from exc
            self._client = anthropic.Anthropic()
        return self._client

    def complete(self, prompt: str, system: str | None = None) -> str:
        client = self._get_client()
        kwargs: dict = {}
        if system:
            kwargs["system"] = system

        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                message = client.messages.create(
                    model=self._model,
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}],
                    **kwargs,
                )
                # Extract text content from the response
                content = ""
                for block in message.content:
                    if block.type == "text":
                        content += block.text
                return content
            except Exception as exc:
                last_exc = exc
                # Only retry on rate-limit or transient API errors
                import anthropic

                if not isinstance(
                    exc, anthropic.RateLimitError | anthropic.APIError | anthropic.APITimeoutError
                ):
                    break
                if attempt < self._max_retries - 1:
                    import time

                    time.sleep(self._base_delay * (2**attempt))

        raise RuntimeError(
            f"Anthropic request failed after {self._max_retries} attempt(s): {last_exc}"
        ) from last_exc


class CanonicalizationEngine:
    """Find near-duplicate clusters and propose canonical forms via LLM."""

    DEFAULT_PROMPT = """
You are an ontology curator. Below is a cluster of concept descriptions that
may be near-duplicates or specialisations of one another.

Propose:
1. A canonical concept ID (lowercase alphanumeric with hyphens) and English name.
2. For each original concept, a relation to the canonical concept chosen from:
   isomorphic-to, specialisation-of, fork-of, or deprecate-as-duplicate.
3. A short reasoning string.

Return **only** a JSON object with this shape:
{
  "canonical_adl_id": "...",
  "canonical_name": {"en": "..."},
  "relations": [
    {"source": "<original_adl_id>", "target": "<canonical_adl_id>", "relation": "..."}
  ],
  "deprecate": ["<original_adl_id>", ...],
  "reasoning": "..."
}

Concept cluster:
{cluster_text}
"""

    def __init__(
        self,
        vector_index: VectorIndex,
        llm: LLMBackend | None = None,
        threshold: float = 0.92,
    ) -> None:
        self.vector_index = vector_index
        self.llm = llm or _MockLLMBackend()
        self.threshold = threshold

    def find_clusters(self, adl_ids: list[str] | None = None) -> list[list[str]]:
        """Return connected components of the similarity graph above threshold."""
        if adl_ids is None:
            rows = self.vector_index.conn.execute(
                "SELECT adl_id, text FROM vectors WHERE deleted = 0"
            ).fetchall()
            items = {row[0]: row[1] for row in rows}
        else:
            placeholders = ",".join("?" * len(adl_ids))
            rows = self.vector_index.conn.execute(
                f"""
                SELECT adl_id, text FROM vectors
                WHERE adl_id IN ({placeholders}) AND deleted = 0
                """,
                adl_ids,
            ).fetchall()
            items = {row[0]: row[1] for row in rows}

        graph = nx.Graph()
        graph.add_nodes_from(items.keys())

        for adl_id, text in items.items():
            results = self.vector_index.search(text, top_k=len(items), threshold=self.threshold)
            for r in results:
                other = r["adl_id"]
                if other != adl_id and graph.has_node(other):
                    graph.add_edge(adl_id, other)

        return [sorted(c) for c in nx.connected_components(graph) if len(c) > 1]

    def _cluster_text(self, cluster: list[str]) -> str:
        rows = self.vector_index.conn.execute(
            f"""
            SELECT adl_id, text FROM vectors
            WHERE adl_id IN ({",".join("?" * len(cluster))}) AND deleted = 0
            """,
            cluster,
        ).fetchall()
        parts = []
        for adl_id, text in rows:
            parts.append(f"--- {adl_id} ---\n{text}")
        return "\n\n".join(parts)

    def propose(self, cluster: list[str]) -> dict:
        """Ask the LLM to propose a canonical form for a cluster."""
        prompt = self.DEFAULT_PROMPT.replace("{cluster_text}", self._cluster_text(cluster))
        raw = self.llm.complete(prompt)

        # Try to extract JSON from markdown or raw string.
        try:
            parsed: dict = json.loads(raw)
        except json.JSONDecodeError:
            import re

            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
            else:
                raise ValueError(f"LLM did not return valid JSON: {raw}") from None

        return parsed

    def generate_actions(
        self,
        cluster: list[str],
        proposal: dict,
        actor: str = "canonicalization-engine",
    ) -> list[ADLActionBlock]:
        """Generate ADL action blocks from an LLM proposal without mutating chains."""
        from .models import ADLActionBlock

        actions: list[ADLActionBlock] = []
        canonical_id = str(proposal.get("canonical_adl_id") or "")
        canonical_name = proposal.get("canonical_name", {}).get("en", canonical_id)
        reasoning = proposal.get("reasoning", "Canonicalization proposal")

        # Register canonical concept first.
        actions.append(
            ADLActionBlock(
                action="register",
                actor=actor,
                reasoning=f"Create canonical concept '{canonical_name}': {reasoning}",
                params={
                    "adl_id": canonical_id,
                    "adl_type": "concept",
                    "provisional_names": {"en": canonical_name},
                },
            )
        )

        for rel in proposal.get("relations", []):
            actions.append(
                ADLActionBlock(
                    action="relate",
                    actor=actor,
                    reasoning=reasoning,
                    params={
                        "source": rel.get("source"),
                        "predicate": rel.get("relation", "isomorphic-to"),
                        "target": rel.get("target"),
                    },
                )
            )

        for dep_id in proposal.get("deprecate", []):
            actions.append(
                ADLActionBlock(
                    action="deprecate",
                    actor=actor,
                    reasoning=f"Deprecated {dep_id} as duplicate of {canonical_id}: {reasoning}",
                    params={"reason": reasoning},
                )
            )

        return actions

    def normalize(
        self,
        dry_run: bool = True,
        execute_actor: str = "canonicalization-engine",
    ) -> list[dict]:
        """Run the full normalization workflow.

        Returns a list of result dicts, one per cluster, containing the cluster,
        proposal, and generated action blocks. If ``dry_run`` is False, the
        actions are executed via :class:`ActionExecutor`.
        """
        from .action_executor import ActionExecutor
        from .consensus import ConsensusEngine
        from .models import ADLDocument, ADLFrontMatter, ADLType, ProvisionalNames
        from .ontology import OntologyManager

        clusters = self.find_clusters()
        results: list[dict] = []

        executor = ActionExecutor(OntologyManager())
        engine = ConsensusEngine()

        for cluster in clusters:
            proposal = self.propose(cluster)
            actions = self.generate_actions(cluster, proposal)

            result = {
                "cluster": cluster,
                "proposal": proposal,
                "actions": actions,
                "executed": False,
            }

            if not dry_run:
                # Build a minimal document for the canonical concept.
                canonical_id = str(proposal.get("canonical_adl_id") or "")
                canonical_name = proposal.get("canonical_name", {}).get("en", canonical_id)
                doc = ADLDocument(
                    front_matter=ADLFrontMatter(
                        adl_type=ADLType.CONCEPT,
                        adl_id=canonical_id,
                        provisional_names=ProvisionalNames(en=canonical_name),
                    ),
                    markdown_body=f"# {canonical_name}\n\nCanonical form proposed by LLM normalization.",
                    action_blocks=actions,
                )
                try:
                    executor.execute_pending(doc)
                    engine.register(doc)
                    result["executed"] = True
                except Exception as exc:
                    result["errors"] = [str(exc)]

            results.append(result)

        return results
