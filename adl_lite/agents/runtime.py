"""Thin multi-agent runtime (M3).

Architecture notes (first-principles, adversarial-review driven):
- The runtime is GLUE: dequeue loop + role whitelist + audit events. If it
  cannot call existing assets it gets cut, not fattened.
- P0-2: ``run_task`` appends the TASK_CLAIM chain event FIRST (the queue lease
  is volatile and deliberately not chain-backed; the chain must show
  IN_PROGRESS or ``submit``'s transition guard fails).
- P2-1: ``_material_path`` is defined here (task input_ref or a temp file) —
  no dangling calls.
- P1-4 deployment model: the in-process ``asyncio.Future`` checkpoint works
  ONLY in single-process deployments (API and runtime in one process, e.g.
  ``adl-lite run``). Cross-process deployments must use a persisted
  CheckpointRequest (MESSAGE on chain) + polling — out of scope for M3-M4.
- P1-6: un-consumed backlog is visible via ``RuntimeManager.status()`` /
  ``TaskQueue.pending_count()``.

Implementation note vs. the plan's pseudocode: the plan sketched ``_default_tools``
as the ``tools.py`` wrappers, but those LOAD/SAVE the state file on every call
and would race the runtime's in-memory engine. The tools used here are
in-memory closures bound to the runtime's own engine — same behavior, no disk
churn. Also, ``LLMBackend.complete`` is synchronous in this codebase, so all
LLM calls are bridged with ``asyncio.to_thread``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from enum import Enum
from pathlib import Path
from typing import Any

from ..canonicalization import LLMBackend
from ..consensus import ConsensusEngine
from ..models import DiscoveryStatus, Event, EventType
from ..ontology import default_ontology
from .bus import MessageBus, TaskQueue
from .config import AgentConfig
from .identity import AgentProfile, AgentRegistry, AgentRole
from .roles import ROLE_SPECS, RoleSpec
from .task import Task, TaskRegistry


class CheckpointKind(str, Enum):
    TASK_CREATE_COMPLEX = "task_create_complex"  # non-template free objective
    TASK_CLOSE_MUTATES_VALIDATED = "task_close_mutates_validated"
    AGENT_REGISTER_PROD = "agent_register_prod"
    FORK_OR_DEPRECATE_VALIDATED = "fork_or_deprecate_validated"


# ----------------------------------------------------------------------
# Checkpoint approval registry (single-process only, P1-4)
# ----------------------------------------------------------------------

_CHECKPOINT_FUTURES: dict[str, asyncio.Future] = {}


def checkpoint_handler() -> Callable[[dict[str, Any]], Awaitable[bool]]:
    """Build a checkpoint callback that blocks on a human approval.

    The approval id is the task_id. ``approve_checkpoint`` resolves the
    future from any in-process caller (CLI handler, API endpoint).
    """

    async def _handler(req: dict[str, Any]) -> bool:
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        task_id = req["task_id"]
        _CHECKPOINT_FUTURES[task_id] = fut
        try:
            return await asyncio.wait_for(fut, timeout=float(req.get("timeout", 300)))
        finally:
            _CHECKPOINT_FUTURES.pop(task_id, None)

    return _handler


def approve_checkpoint(task_id: str, approved: bool = True) -> bool:
    """Resolve a pending checkpoint. Returns False if no checkpoint is
    waiting for ``task_id`` (or it already timed out)."""
    fut = _CHECKPOINT_FUTURES.get(task_id)
    if fut is None or fut.done():
        return False
    fut.set_result(approved)
    return True


def pending_checkpoints() -> list[str]:
    return sorted(_CHECKPOINT_FUTURES)


# ----------------------------------------------------------------------
# In-memory tool registry (engine-bound closures, no disk reload)
# ----------------------------------------------------------------------


def _mem_register(
    engine: ConsensusEngine, path: str | Path | None = None, adl_id: str | None = None
) -> dict[str, Any]:
    """In-memory counterpart of tools.adl_consensus_register — registers
    directly into the runtime's engine (no state-file reload)."""
    if path is not None:
        from ..parser import parse_file

        doc = parse_file(path)
        engine.register(doc)
        return {"registered": doc.adl_id}
    if adl_id is not None:
        if adl_id not in engine.chains:
            from ..models import ADLDocument, ADLFrontMatter, ADLType, ProvisionalNames

            stub = ADLDocument(
                front_matter=ADLFrontMatter(
                    adl_type=ADLType.CONCEPT,
                    adl_id=adl_id,
                    scope="public",
                    provisional_names=ProvisionalNames(en=adl_id),
                )
            )
            engine.register(stub)
        return {"registered": adl_id}
    raise ValueError("adl_consensus_register requires path or adl_id")


def _mem_transition(
    engine: ConsensusEngine, adl_id: str, to_status: str, actor: str, reason: str = ""
) -> dict[str, Any]:
    from ..models import DiscoveryStatus

    target = DiscoveryStatus(to_status)
    event = engine.transition(adl_id, target, actor=actor, reason=reason)
    if event is None:
        return {"adl_id": adl_id, "error": "transition returned None"}
    return {
        "adl_id": adl_id,
        "event_type": event.event_type.value,
        "actor": event.actor,
        "hash": event.hash,
        "timestamp": event.timestamp,
    }


def _default_tools(
    engine: ConsensusEngine,
    task_registry: TaskRegistry | None = None,
) -> dict[str, Callable[..., Any]]:
    """Tool registry for the runtime: in-memory closures over ``engine``.

    Whitelist names must match ``RoleSpec.allowed_tools`` (roles.py).
    ``task_registry`` is accepted for future task-facing tools; M3 uses only
    discovery-facing tools.
    """
    om = default_ontology()

    def _verify(adl_id: str) -> dict[str, Any]:
        chain = engine.chains.get(adl_id)
        if chain is None:
            return {"ok": False, "adl_id": adl_id, "error": "not registered"}
        return {"ok": chain.verify_integrity(), "adl_id": adl_id}

    return {
        "adl_parse": lambda path: _mem_parse(path),
        "adl_validate": lambda path: _mem_validate(path),
        "adl_consensus_register": lambda path=None, adl_id=None, state=None:  # noqa: ARG005
        _mem_register(engine, path=path, adl_id=adl_id),
        "adl_consensus_transition": lambda adl_id,
        to_status,
        actor,
        reason="",
        state=None:  # noqa: ARG005
        _mem_transition(engine, adl_id, to_status, actor, reason),
        "adl_ontology_query": om.query_schema,
        "adl_consensus_verify": _verify,
        "adl_store": lambda path, db: _mem_store(path, db),
        "adl_query_related": lambda adl_id, db, depth=1: _mem_query_related(adl_id, db, depth),
    }


def _mem_parse(path: str | Path) -> dict[str, Any]:
    from ..parser import parse_file

    doc = parse_file(path)
    return {
        "adl_id": doc.adl_id,
        "_summary": {
            "adl_id": doc.adl_id,
            "concept_name": doc.concept_name,
            "relations": len(doc.relations),
            "evidence": len(doc.evidence),
        },
    }


def _mem_validate(path: str | Path) -> dict[str, Any]:
    from ..parser import parse_file
    from ..validator import ADLValidator

    try:
        doc = parse_file(path)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "path": str(path), "errors": [f"parse error: {exc}"]}
    errors = ADLValidator().validate_document(doc)
    return {"ok": len(errors) == 0, "path": str(path), "errors": errors}


def _mem_store(path: str | Path, db: str | Path) -> dict[str, Any]:
    from ..memory import ADLMemory

    mem = ADLMemory(db_path=str(db))
    try:
        from ..parser import parse_file

        doc = parse_file(path)
        mem.store(doc)
        return {"stored": doc.adl_id, "db": str(db)}
    finally:
        mem.close()


def _mem_query_related(adl_id: str, db: str | Path, depth: int = 1) -> list[dict[str, Any]]:
    from ..memory import ADLMemory

    mem = ADLMemory(db_path=str(db))
    try:
        return [
            {"concept": c, "relation": r, "confidence": conf}
            for c, r, conf in mem.find_related(adl_id, depth=depth)
        ]
    finally:
        mem.close()


# ----------------------------------------------------------------------
# AgentRuntime
# ----------------------------------------------------------------------


class AgentRuntime:
    """Thin runtime: dequeue → reason → whitelisted tools → audit every action.

    Single-agent loop. ``RuntimeManager`` owns the lifecycle for many agents.
    """

    def __init__(
        self,
        agent_did: str,
        profile: AgentProfile,
        engine: ConsensusEngine,
        agent_registry: AgentRegistry,
        task_registry: TaskRegistry,
        task_queue: TaskQueue,
        bus: MessageBus | None = None,
        llm: LLMBackend | None = None,
        tools: dict[str, Callable[..., Any]] | None = None,
        checkpoint: Callable[[dict[str, Any]], Awaitable[bool]] | None = None,
        signer: Callable[[bytes], str] | None = None,
    ) -> None:
        self.agent_did = agent_did
        self.profile = profile
        self.engine = engine
        self.agent_registry = agent_registry
        self.task_registry = task_registry
        self.task_queue = task_queue
        self.bus = bus
        self.spec: RoleSpec = ROLE_SPECS[profile.role]
        self._tools = tools or _default_tools(engine, task_registry)
        self._llm = llm or AgentConfig.from_env().build_llm()
        self._checkpoint = checkpoint
        # P1 (closure): optional event signer. When set, tool calls that
        # produce DID-actor chain events (consensus_transition) attach a
        # signature so strict trust checks (B2) can verify them. The key
        # stays with the caller (P2-10); None keeps the loose behaviour.
        self._signer = signer
        self._running = False
        self._tasks_done = 0

    # ------------------------------------------------------------------
    # Loop
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def tasks_done(self) -> int:
        return self._tasks_done

    async def run_forever(self) -> None:
        self._running = True
        try:
            while self._running:
                task = await self.task_queue.dequeue(self.agent_did, self.profile.capabilities)
                if task is None:
                    await asyncio.sleep(0.5)
                    continue
                await self.run_task(task)
                self._tasks_done += 1
        finally:
            self._running = False

    async def stop(self) -> None:
        self._running = False

    # ------------------------------------------------------------------
    # Task execution
    # ------------------------------------------------------------------

    async def run_task(self, task: Task) -> None:
        try:
            # P0-2: TASK_CLAIM must land on the chain BEFORE execute — the
            # queue lease is volatile, and submit's guard needs IN_PROGRESS.
            self.task_registry.claim(task.task_id, self.agent_did)
            result = await self._execute(task)
            self.task_registry.submit(
                task.task_id,
                self.agent_did,
                result_ref=result["adl_id"],
                summary=result.get("summary", ""),
            )
        except Exception as exc:  # noqa: BLE001
            self.task_queue.release(task.task_id, self.agent_did)  # lease back
            self._record_event(
                task.task_id,
                EventType.MESSAGE,
                {"level": "error", "error": str(exc)},
                actor=self.agent_did,
            )

    async def _execute(self, task: Task) -> dict[str, Any]:
        """Role-driven execution. Every role fires its whitelisted tool chain
        (all calls go through ``_call_tool``, which appends a MESSAGE audit
        event per invocation). ``result_ref`` is the discovery chain produced
        by an earlier role; when it is missing the role degrades to reasoning
        + verifying the current task chain."""
        # 1. Checkpoint (optional): complex free-form objectives need approval.
        if self._checkpoint and task.parent_task_id is None:
            ok = await self._checkpoint(
                {
                    "kind": CheckpointKind.TASK_CREATE_COMPLEX,
                    "task_id": task.task_id,
                    "objective": task.objective,
                }
            )
            if not ok:
                raise PermissionError("checkpoint rejected task")

        # 2. Reason (sync backend bridged to the event loop).
        reasoning = await asyncio.to_thread(
            self._llm.complete, task.objective, self.spec.system_prompt
        )

        # 3. Role tool chain.
        if self.profile.role == AgentRole.DISCOVERER:
            path = self._material_path(task)
            parsed = await self._call_tool("adl_parse", {"path": path}, task.task_id)
            adl_id = (parsed.get("_summary") or {}).get("adl_id") or task.task_id
            await self._call_tool("adl_consensus_register", {"adl_id": adl_id}, task.task_id)
            return {"adl_id": adl_id, "summary": reasoning}

        if self.profile.role == AgentRole.REVIEWER:
            # Validate the material; approve (transition to validated) only
            # when validation passes AND a result chain was produced earlier.
            adl_id = task.result_ref or task.task_id
            path = self._material_path(task)
            vres = await self._call_tool("adl_validate", {"path": path}, task.task_id)
            if vres.get("ok") and task.result_ref is not None:
                await self._call_tool(
                    "adl_consensus_transition",
                    {
                        "adl_id": adl_id,
                        "to_status": "validated",
                        "actor": self.agent_did,
                        "reason": reasoning,
                    },
                    task.task_id,
                )
            return {"adl_id": adl_id, "summary": reasoning}

        if self.profile.role == AgentRole.SKEPTIC:
            # Challenge the result chain: a failed verification (challenge
            # stands) forks it; a pass just records the conclusion.
            adl_id = task.result_ref or task.task_id
            vres = await self._call_tool("adl_consensus_verify", {"adl_id": adl_id}, task.task_id)
            if not vres.get("ok") and task.result_ref is not None:
                await self._call_tool(
                    "adl_consensus_transition",
                    {
                        "adl_id": adl_id,
                        "to_status": "forked",
                        "actor": self.agent_did,
                        "reason": reasoning,
                    },
                    task.task_id,
                )
            return {"adl_id": adl_id, "summary": reasoning}

        if self.profile.role == AgentRole.MERGER:
            # Resolve forks: verify first; only re-validate when the chain is
            # actually forked (a valid transition needs forked -> validated).
            adl_id = task.result_ref or task.task_id
            vres = await self._call_tool("adl_consensus_verify", {"adl_id": adl_id}, task.task_id)
            if vres.get("ok") and task.result_ref is not None:
                chain = self.engine.chains.get(adl_id)
                if chain is not None and chain.status == DiscoveryStatus.FORKED:
                    await self._call_tool(
                        "adl_consensus_transition",
                        {
                            "adl_id": adl_id,
                            "to_status": "validated",
                            "actor": self.agent_did,
                            "reason": reasoning,
                        },
                        task.task_id,
                    )
            return {"adl_id": adl_id, "summary": reasoning}

        if self.profile.role == AgentRole.LIBRARIAN:
            # Curate: persist the material into the memory db and query the
            # result chain's graph neighbors. The db comes from the task
            # payload (``db_ref``), defaulting to a shared temp store.
            adl_id = task.result_ref or task.task_id
            path = self._material_path(task)
            genesis = self.engine.chains[task.task_id].events[0].payload
            db = genesis.get("db_ref") or "/tmp/adl_mem.db"
            await self._call_tool("adl_store", {"path": path, "db": db}, task.task_id)
            await self._call_tool("adl_query_related", {"adl_id": adl_id, "db": db}, task.task_id)
            return {"adl_id": adl_id, "summary": reasoning}

        return {"adl_id": task.task_id, "summary": reasoning}

    def _material_path(self, task: Task) -> str:
        """P2-1: Discoverer input source. Prefer the task's ``input_ref``
        (file path / URI) from the TASK_CREATE payload; fall back to a temp
        file holding the objective text."""
        genesis = self.engine.chains[task.task_id].events[0].payload
        ref = genesis.get("input_ref")
        if ref:
            return str(ref)
        path = Path(f"/tmp/adl_task_{task.task_id.replace(':', '_')}.md")
        path.write_text(task.objective, encoding="utf-8")
        return str(path)

    # ------------------------------------------------------------------
    # Tool call + audit
    # ------------------------------------------------------------------

    async def _call_tool(
        self, tool_name: str, params: dict[str, Any], task_id: str
    ) -> dict[str, Any]:
        """Whitelist-enforced tool call. Every invocation is audited with a
        MESSAGE event on the task chain (RT-03 compares counts)."""
        if tool_name not in self.spec.allowed_tools:
            raise PermissionError(f"{self.profile.role.value} cannot call {tool_name}")
        if tool_name not in self._tools:
            raise KeyError(f"tool not registered: {tool_name}")
        self._record_event(
            task_id,
            EventType.MESSAGE,
            {"tool": tool_name, "params": params},
            actor=self.agent_did,
        )
        result = await asyncio.to_thread(self._tools[tool_name], **params)
        # P1 (closure): sign events this agent produced via
        # consensus_transition (VALIDATE/FORK) so strict trust checks (B2)
        # can verify them. Event hashes exclude signature, so this is
        # integrity-safe (same pattern as the API attest endpoint).
        if (
            self._signer is not None
            and tool_name == "adl_consensus_transition"
            and isinstance(result, dict)
            and result.get("adl_id")
        ):
            chain = self.engine.chains.get(result["adl_id"])
            if chain is not None and chain.events:
                last = chain.events[-1]
                if (
                    last.event_type in (EventType.VALIDATE, EventType.FORK)
                    and last.actor == self.agent_did
                    and not last.signature
                ):
                    last.signature = self._signer(last.hash.encode("utf-8"))
        return dict(result) if isinstance(result, dict) else result

    def _record_event(
        self,
        chain_id: str,
        event_type: EventType,
        payload: dict[str, Any],
        actor: str,
        reasoning: str = "",
    ) -> Event:
        """Audit closure: every action leaves an event on the task/ability
        chain, so ``verify_integrity`` can validate the whole run."""
        event = Event(
            concept_id=chain_id,
            event_type=event_type,
            actor=actor,
            reasoning=reasoning,
            payload=payload,
        )
        self.engine.chains[chain_id].append(event)
        return event


# ----------------------------------------------------------------------
# RuntimeManager (many agents; P1-6 backlog visibility)
# ----------------------------------------------------------------------


class RuntimeManager:
    """Owns the per-agent run_forever tasks and exposes aggregate status."""

    def __init__(
        self,
        engine: ConsensusEngine,
        task_registry: TaskRegistry,
        task_queue: TaskQueue,
        agent_registry: AgentRegistry | None = None,
        bus: MessageBus | None = None,
    ) -> None:
        self.engine = engine
        self.task_registry = task_registry
        self.task_queue = task_queue
        self.agent_registry = agent_registry or AgentRegistry(engine=engine)
        self.bus = bus
        self._runtimes: dict[str, AgentRuntime] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}

    def start(
        self,
        agent_did: str,
        profile: AgentProfile,
        llm: LLMBackend | None = None,
        checkpoint: Callable[[dict[str, Any]], Awaitable[bool]] | None = None,
    ) -> AgentRuntime:
        """Spawn a runtime loop for an agent (idempotent: reuses existing)."""
        existing = self._runtimes.get(agent_did)
        if existing is not None:
            return existing
        rt = AgentRuntime(
            agent_did=agent_did,
            profile=profile,
            engine=self.engine,
            agent_registry=self.agent_registry,
            task_registry=self.task_registry,
            task_queue=self.task_queue,
            bus=self.bus,
            llm=llm,
            checkpoint=checkpoint,
        )
        self._runtimes[agent_did] = rt
        self._tasks[agent_did] = asyncio.create_task(rt.run_forever())
        return rt

    async def stop(self, agent_did: str) -> None:
        rt = self._runtimes.pop(agent_did, None)
        if rt is not None:
            await rt.stop()
        task = self._tasks.pop(agent_did, None)
        if task is not None and not task.done():
            task.cancel()

    async def stop_all(self) -> None:
        for did in list(self._runtimes):
            await self.stop(did)

    def status(self) -> dict[str, Any]:
        """P1-6: per-agent run state + un-consumed backlog."""
        return {
            "agents": {
                did: {
                    "role": rt.profile.role.value,
                    "running": rt.is_running,
                    "tasks_done": rt.tasks_done,
                }
                for did, rt in sorted(self._runtimes.items())
            },
            "pending": self.task_queue.pending_count(),
            "queue_depth": self.task_queue.queue_depth(),
        }
