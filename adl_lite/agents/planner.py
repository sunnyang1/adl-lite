"""Schema-first task decomposition (M3).

The planner is deliberately thin: ask the LLM for a JSON decomposition, filter
every capability through the SAME vocabulary used by ``TaskRegistry`` and
``TaskQueue.dequeue`` (P1-3: ontology predicates ∪ registered discovery chain
ids), then create tasks. If the vocabulary ever diverged, planner output would
produce tasks no agent could ever claim — a silent deadlock.

Note: ``LLMBackend.complete`` is a SYNCHRONOUS call in this codebase (mock and
real backends alike), so the runtime bridges it with ``asyncio.to_thread`` to
keep the event loop unblocked.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from ..canonicalization import LLMBackend
from ..consensus import ConsensusEngine
from ..ontology import OntologyManager, default_ontology
from .identity import chain_kind
from .task import Task, TaskRegistry

_PLAN_PROMPT = (
    "Decompose the objective into subtasks. Return JSON only: "
    '[{"objective": str, "required_capabilities": [str]}]'
)
_PLAN_SYSTEM = "You are a planning agent. Capabilities must be ontology predicates."


class Planner:
    """LLM task decomposition with ontology-gated capability validation."""

    def __init__(
        self,
        engine: ConsensusEngine | None = None,
        llm: LLMBackend | None = None,
        ontology: OntologyManager | None = None,
        registry: TaskRegistry | None = None,
    ) -> None:
        self.engine = engine or ConsensusEngine(dev_mode=True)
        self._ontology = ontology
        self._llm = llm
        self.registry = registry or TaskRegistry(engine=self.engine)

    # ------------------------------------------------------------------

    async def plan(self, objective: str, context: dict[str, Any] | None = None) -> list[Task]:
        """Decompose and create tasks. Invalid capabilities are FILTERED OUT
        (and reported); tasks with zero valid capabilities are skipped."""
        llm = self._llm or self._mock_llm()
        prompt = _PLAN_PROMPT
        if context:
            prompt += f" Context: {json.dumps(context)}"
        raw = await asyncio.to_thread(llm.complete, prompt, _PLAN_SYSTEM)
        try:
            subtasks = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError(f"planner: LLM did not return JSON: {raw!r}") from exc
        if not isinstance(subtasks, list):
            raise ValueError(f"planner: expected a JSON list, got {type(subtasks)}")

        tasks: list[Task] = []
        for st in subtasks:
            if not isinstance(st, dict) or not st.get("objective"):
                continue
            caps = [
                c
                for c in st.get("required_capabilities", [])
                if isinstance(c, str) and self.validate_capability(c)
            ]
            if not caps:
                continue  # nothing an agent could ever claim (P1-3 deadlock guard)
            tasks.append(
                self.registry.create_task(
                    objective=st["objective"],
                    required_capabilities=caps,
                    created_by="planner",
                )
            )
        return tasks

    # ------------------------------------------------------------------

    def validate_capability(self, capability: str) -> bool:
        """Schema-first (P1-3): a capability is legal iff it is an ontology
        predicate OR a registered discovery chain id — the exact same rule as
        ``TaskRegistry._is_known_capability``, so planner validation and queue
        matching can never diverge."""
        om = self._ontology or default_ontology()
        if om.validate_predicate(capability):
            return True
        return any(
            chain_kind(self.engine.chains[c]) == "discovery" and c == capability
            for c in self.engine.chains
        )

    def _mock_llm(self) -> LLMBackend:
        """Deterministic fallback for tests/demos when no backend is injected:
        return a tiny planner-shaped JSON (never the canonicalizer mock, whose
        output shape is unrelated to planning)."""
        from ..canonicalization import _MockLLMBackend

        class _PlannerMock(_MockLLMBackend):
            def complete(self, prompt: str, system: str | None = None) -> str:  # noqa: ARG002
                return json.dumps(
                    [
                        {
                            "objective": "land a capability from the task material",
                            # "depends-on" is a real ontology predicate (P1-3).
                            "required_capabilities": ["depends-on"],
                        }
                    ]
                )

        return _PlannerMock()  # type: ignore[return-value]
