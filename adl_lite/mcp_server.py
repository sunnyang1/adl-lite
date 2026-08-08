"""ADL Lite — FastMCP tool server for the capability-lifecycle registry.

Exposes 26 tools, 2 resources, and 1 prompt via the official MCP Python SDK's
FastMCP class. Tools wrap the existing consensus engine, parser, validator,
ontology subsystems, agent identity/trust, and task lifecycle.

Usage:
    # stdio transport (for Claude Desktop, etc.)
    python -m adl_lite.mcp_server

    # streamable-http transport (for web-based clients)
    python -m adl_lite.mcp_server --transport streamable-http

    # Or via CLI subcommand:
    adl-lite mcp
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# P0-2: chain-type marker so discovery listing excludes agent/task chains.
from .agents.identity import chain_kind as _chain_kind
from .consensus import ConsensusEngine
from .logging_config import get_logger
from .models import (
    ADLDocument,
    ADLFrontMatter,
    ADLType,
    DiscoveryStatus,
    EventChain,
    EventType,
    ProvisionalNames,
)
from .ontology import default_ontology
from .tools import adl_parse as _adl_parse
from .tools import adl_validate as _adl_validate
from .validator import ADLValidator

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Scope ACL — MCP has no tenant/user context, so read tools expose
# public-scope documents only (writes are unaffected).
# ---------------------------------------------------------------------------

_SCOPE_VALIDATOR = ADLValidator()


def _chain_scope(chain: EventChain) -> str:
    """Derive a chain's visibility scope from its genesis event payload."""
    events = chain.events
    if events:
        scope = events[0].payload.get("scope")
        if isinstance(scope, str) and scope:
            return scope
    return "public"


def _is_public(chain: EventChain) -> bool:
    """Return True when the chain is readable without any tenant context."""
    return _SCOPE_VALIDATOR.validate_scope_access(_chain_scope(chain), "public")


# ---------------------------------------------------------------------------
# Engine singleton — lazy init from state file (same pattern as api.py)
# ---------------------------------------------------------------------------

_engine: ConsensusEngine | None = None
_engine_lock = threading.Lock()
_state_path: Path = Path(".adl/state.json")


def _get_engine() -> ConsensusEngine:
    """Return the shared ConsensusEngine, loading state from disk if needed."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = ConsensusEngine(ontology=default_ontology())
                if _state_path.exists() and _state_path.stat().st_size > 0:
                    data = json.loads(_state_path.read_text(encoding="utf-8"))
                    for cid, events_data in data.get("chains", {}).items():
                        from .models import Event, EventChain

                        chain = EventChain(concept_id=cid)
                        for raw in events_data:
                            event = Event(
                                concept_id=cid,
                                event_type=EventType(raw.get("event_type", "register")),
                                actor=raw.get("actor", "system"),
                                reasoning=raw.get("reasoning", raw.get("reason", "")),
                                timestamp=raw.get("timestamp", ""),
                                payload=raw.get("payload", {}),
                            )
                            if "event_id" in raw:
                                event.event_id = raw["event_id"]
                            if "hash" in raw:
                                event.hash = raw["hash"]
                            if "_prev_hash" in raw:
                                event._prev_hash = raw["_prev_hash"]
                            if "previous_event_id" in raw:
                                event.previous_event_id = raw["previous_event_id"]
                            if "signature" in raw:
                                event.signature = raw["signature"]
                            if "proof" in raw:
                                event.proof = raw["proof"]
                            chain.append(event)
                        _engine.chains[cid] = chain
    return _engine


def _save_engine(engine: ConsensusEngine) -> None:
    """Persist engine state to disk (full event fields incl. signature/proof)."""
    payload = {
        "chains": {
            cid: [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type.value,
                    "actor": e.actor,
                    "reasoning": e.reasoning,
                    "timestamp": e.timestamp,
                    "hash": e.hash,
                    "_prev_hash": getattr(e, "_prev_hash", ""),
                    "previous_event_id": e.previous_event_id,
                    "signature": e.signature,
                    "proof": e.proof,
                    "payload": e.payload,
                }
                for e in chain.events
            ]
            for cid, chain in engine.chains.items()
        }
    }
    _state_path.parent.mkdir(parents=True, exist_ok=True)
    _state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Server factory
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# MCP write-tool gate (P0-3). stdio has no auth context, so write tools are
# rejected unless an explicit admin token is configured (streamable-http only
# can carry it via an Authorization header — see P1-1 in the implementation
# plan).
# ---------------------------------------------------------------------------

_MCP_ADMIN_TOKEN: str | None = None


def _mcp_write_allowed() -> bool:
    return bool(_MCP_ADMIN_TOKEN)


def create_mcp_server(
    state_path: str | None = None,
    admin_token: str | None = None,
) -> FastMCP:
    """Create and configure a FastMCP server for ADL Lite.

    Args:
        state_path: Path to consensus state JSON file. Defaults to
            ``.adl/state.json`` in the current working directory.
        admin_token: Bearer token required for MCP write tools (P0-3/P1-1).
            ``None`` (default) denies all write tools; only meaningful for
            streamable-http transport (stdio has no auth context).

    Returns:
        A configured FastMCP instance with agent + consensus tools.
    """
    global _state_path, _engine, _MCP_ADMIN_TOKEN
    if state_path is not None:
        _state_path = Path(state_path)
    _MCP_ADMIN_TOKEN = admin_token
    _engine = None  # Reset engine so it re-loads from (potentially new) state_path

    mcp = FastMCP("adl-lite", instructions="ADL Lite capability-lifecycle registry MCP server")

    # ------------------------------------------------------------------
    # Tool 1: adl_parse
    # ------------------------------------------------------------------

    @mcp.tool()
    def adl_parse(path: str) -> dict[str, Any]:
        """Parse an ADL Markdown file and return a summary dict with
        adl_id, concept_name, relations count, and evidence count."""
        raw = _adl_parse(path)
        # Extract summary from the full parse output
        summary = raw.get("_summary", {})
        return {
            "adl_id": summary.get("adl_id", ""),
            "concept_name": summary.get("concept_name", ""),
            "relations": summary.get("relations", 0),
            "evidence": summary.get("evidence", 0),
        }

    # ------------------------------------------------------------------
    # Tool 2: adl_validate
    # ------------------------------------------------------------------

    @mcp.tool()
    def adl_validate(path: str) -> dict[str, Any]:
        """Validate an ADL Markdown file, returning ok (bool) and errors list."""
        return _adl_validate(path)

    # ------------------------------------------------------------------
    # Tool 3: adl_register
    # ------------------------------------------------------------------

    @mcp.tool()
    def adl_register(
        adl_id: str,
        domain: str = "general",
        scope: str = "public",
    ) -> dict[str, Any]:
        """Register a capability in the consensus engine. Returns adl_id,
        status, event_id, and timestamp."""
        engine = _get_engine()

        # Create stub document for registration
        stub = ADLDocument(
            front_matter=ADLFrontMatter(
                adl_type=ADLType.CONCEPT,
                adl_id=adl_id,
                scope=scope,
                domain=domain,
                provisional_names=ProvisionalNames(en=adl_id),
            )
        )
        chain = engine.register(stub)
        _save_engine(engine)

        # Get the latest event for event_id and timestamp
        latest_event = chain.events[-1] if chain.events else None
        return {
            "adl_id": adl_id,
            "status": chain.status.value,
            "event_id": latest_event.event_id if latest_event else "",
            "timestamp": latest_event.timestamp if latest_event else "",
        }

    # ------------------------------------------------------------------
    # Tool 4: adl_transition
    # ------------------------------------------------------------------

    @mcp.tool()
    def adl_transition(
        adl_id: str,
        to_status: str,
        actor: str = "mcp-user",
        reason: str = "",
    ) -> dict[str, Any]:
        """Transition a capability to a new status. Returns adl_id,
        event_type, actor, hash, and timestamp."""
        engine = _get_engine()

        try:
            target = DiscoveryStatus(to_status)
        except ValueError:
            return {"adl_id": adl_id, "error": f"Invalid status: {to_status}"}

        try:
            event = engine.transition(adl_id, target, actor=actor, reason=reason)
        except Exception as exc:
            return {"adl_id": adl_id, "error": str(exc)}

        if event is None:
            return {"adl_id": adl_id, "error": "Transition returned None"}

        _save_engine(engine)
        return {
            "adl_id": adl_id,
            "event_type": event.event_type.value,
            "actor": event.actor,
            "hash": event.hash,
            "timestamp": event.timestamp,
        }

    # ------------------------------------------------------------------
    # Tool 5: adl_status
    # ------------------------------------------------------------------

    @mcp.tool()
    def adl_status(adl_id: str) -> dict[str, Any]:
        """Get the current status and confidence of a capability.
        Returns adl_id, status, confidence, and event_count."""
        engine = _get_engine()

        chain = engine.chains.get(adl_id)
        if chain is None or not _is_public(chain):
            if chain is not None:
                logger.warning("MCP scope ACL denied adl_status for adl_id=%s", adl_id)
            return {
                "adl_id": adl_id,
                "status": "provisional",
                "confidence": 0.0,
                "event_count": 0,
                "error": "not registered",
            }

        return {
            "adl_id": adl_id,
            "status": chain.status.value,
            "confidence": chain.confidence,
            "event_count": chain.length,
        }

    # ------------------------------------------------------------------
    # Tool 6: adl_verify
    # ------------------------------------------------------------------

    @mcp.tool()
    def adl_verify(adl_id: str) -> dict[str, Any]:
        """Verify chain integrity for a capability. Returns ok, adl_id,
        status, and chain_length."""
        engine = _get_engine()

        chain = engine.chains.get(adl_id)
        if chain is None or not _is_public(chain):
            return {
                "ok": False,
                "adl_id": adl_id,
                "status": "unknown",
                "chain_length": 0,
                "error": "not registered",
            }

        ok = chain.verify_integrity()
        return {
            "ok": ok,
            "adl_id": adl_id,
            "status": engine.get_status(adl_id).value,
            "chain_length": chain.length,
        }

    # ------------------------------------------------------------------
    # Tool 7: adl_history
    # ------------------------------------------------------------------

    @mcp.tool()
    def adl_history(adl_id: str) -> list[dict[str, Any]]:
        """Get event chain history for a capability. Returns a list of
        event dicts with event_type, actor, timestamp, and hash."""
        engine = _get_engine()
        chain = engine.chains.get(adl_id)
        if chain is None or not _is_public(chain):
            return []
        return engine.get_history(adl_id)

    # ------------------------------------------------------------------
    # Tool 8: adl_fork
    # ------------------------------------------------------------------

    @mcp.tool()
    def adl_fork(
        adl_id: str,
        event_id: str = "*",
        new_scope: str = "public",
    ) -> dict[str, Any]:
        """Fork a capability chain at a specific event. Returns forked_adl_id,
        fork_event_id, and parent_adl_id."""
        engine = _get_engine()

        # Generate a deterministic fork ID
        forked_id = f"{adl_id}-fork-{len(engine.chains)}"

        try:
            new_chain = engine.fork(adl_id, forked_id, actor="mcp-server", reason="MCP fork")
        except KeyError as exc:
            return {"error": str(exc), "parent_adl_id": adl_id}
        except Exception as exc:
            return {"error": str(exc), "parent_adl_id": adl_id}

        _save_engine(engine)

        # Get the fork's registration event
        fork_event = new_chain.events[-1] if new_chain.events else None
        return {
            "forked_adl_id": forked_id,
            "fork_event_id": fork_event.event_id if fork_event else "",
            "parent_adl_id": adl_id,
        }

    # ------------------------------------------------------------------
    # Tool 9: adl_list
    # ------------------------------------------------------------------

    @mcp.tool()
    def adl_list(offset: int = 0, limit: int = 50) -> dict[str, Any]:
        """List all registered capabilities (paginated). Returns capabilities
        list, total count, offset, and limit."""
        engine = _get_engine()
        # Scope ACL: only public-scope capabilities are listed (no tenant
        # context exists for MCP callers). P0-2: discovery chains only.
        caps = sorted(
            cid
            for cid, chain in engine.chains.items()
            if _is_public(chain) and _chain_kind(chain) == "discovery"
        )
        total = len(caps)
        slice_caps = caps[offset : offset + limit]
        return {
            "capabilities": slice_caps,
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    # ------------------------------------------------------------------
    # Tool 10: adl_ontology_query
    # ------------------------------------------------------------------

    @mcp.tool()
    def adl_ontology_query(
        predicate: str | None = None,
        from_status: str | None = None,
        to_status: str | None = None,
    ) -> dict[str, Any]:
        """Introspect the ADL ontology registry. Returns predicates,
        transitions, scope_prefixes, and mapping_types."""
        mgr = default_ontology()
        return mgr.query_schema(
            predicate=predicate,
            from_status=from_status,
            to_status=to_status,
        )

    # ------------------------------------------------------------------
    # M1b agent tools. Write tools require the admin token (P0-3); read
    # tools expose public-scope agents only.
    # ------------------------------------------------------------------

    @mcp.tool()
    def adl_agent_register(
        name: str,
        role: str,
        capabilities: list[str] | None = None,
        scope: str = "public",
        public_key: str = "",
    ) -> dict[str, Any]:
        """Register an agent identity (write tool; requires admin token)."""
        if not _mcp_write_allowed():
            return {"ok": False, "error": "MCP write tools require admin token (P0-3)"}
        from .agents.identity import AgentProfile, AgentRegistry, AgentRole

        engine = _get_engine()
        try:
            profile = AgentProfile(
                did="",
                role=AgentRole(role),
                name=name,
                capabilities=capabilities or [],
                scope=scope,
            )
            registry = AgentRegistry(engine=engine)
            chain = registry.register_agent(profile, public_key=public_key or None)
        except (ValueError, Exception) as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        _save_engine(engine)
        return {
            "ok": True,
            "did": profile.did,
            "status": registry.agent_status(profile.did).value,
            "validator_count": len(registry._agent_validators(chain)),
        }

    @mcp.tool()
    def adl_agent_attest(did: str, signature: str) -> dict[str, Any]:
        """Bind a caller-side genesis signature (write tool; requires admin token)."""
        if not _mcp_write_allowed():
            return {"ok": False, "error": "MCP write tools require admin token (P0-3)"}
        from .agents.identity import AgentRegistry

        engine = _get_engine()
        chain = engine.chains.get(did)
        if chain is None or _chain_kind(chain) != "agent":
            return {"ok": False, "did": did, "error": "not registered"}
        chain.events[0].signature = signature
        _save_engine(engine)
        registry = AgentRegistry(engine=engine)
        return {"ok": True, "did": did, "status": registry.agent_status(did).value}

    @mcp.tool()
    def adl_agent_validate(
        did: str,
        actor_did: str,
        reason: str = "",
        confidence: float = 0.9,
        signature: str = "",
        admin: bool = False,
    ) -> dict[str, Any]:
        """Validate an agent identity (write tool; requires admin token)."""
        if not _mcp_write_allowed():
            return {"ok": False, "error": "MCP write tools require admin token (P0-3)"}
        from .agents.identity import AgentRegistry

        engine = _get_engine()
        registry = AgentRegistry(engine=engine, admin_calls_allowed=admin)
        try:
            event = registry.validate_agent(
                did,
                actor_did,
                reason=reason,
                confidence=confidence,
                signature=signature,
                admin=admin,
            )
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "did": did, "error": str(exc)}
        _save_engine(engine)
        return {
            "ok": True,
            "did": did,
            "event_type": event.event_type.value,
            "status": registry.agent_status(did).value,
        }

    @mcp.tool()
    def adl_agent_get(did: str) -> dict[str, Any]:
        """Get an agent profile (public scope only)."""
        from .agents.identity import AgentRegistry

        engine = _get_engine()
        chain = engine.chains.get(did)
        if chain is None or _chain_kind(chain) != "agent":
            return {"did": did, "error": "not registered"}
        if not _is_public(chain):
            return {"did": did, "error": "not registered"}
        registry = AgentRegistry(engine=engine)
        profile = registry.resolve_profile(chain)
        return {
            "did": did,
            "role": profile.role.value,
            "name": profile.name,
            "capabilities": profile.capabilities,
            "scope": profile.scope,
            "status": registry.agent_status(did).value,
        }

    @mcp.tool()
    def adl_agent_list(offset: int = 0, limit: int = 50) -> dict[str, Any]:
        """List registered agents (public scope only)."""
        from .agents.identity import AgentRegistry

        engine = _get_engine()
        registry = AgentRegistry(engine=engine)
        profiles = [p for p in registry.list_agents() if _is_public(engine.chains[p.did])]
        total = len(profiles)
        slice_items = profiles[offset : offset + limit]
        return {
            "agents": [
                {
                    "did": p.did,
                    "role": p.role.value,
                    "name": p.name,
                    "status": registry.agent_status(p.did).value,
                }
                for p in slice_items
            ],
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    @mcp.tool()
    def adl_agent_deprecate(did: str, actor: str, reason: str = "") -> dict[str, Any]:
        """Decommission an agent (write tool; requires admin token)."""
        if not _mcp_write_allowed():
            return {"ok": False, "error": "MCP write tools require admin token (P0-3)"}
        from .agents.identity import AgentRegistry

        engine = _get_engine()
        registry = AgentRegistry(engine=engine)
        try:
            registry.deprecate_agent(did, actor, reason)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "did": did, "error": str(exc)}
        _save_engine(engine)
        return {"ok": True, "did": did, "status": registry.agent_status(did).value}

    # ------------------------------------------------------------------
    # M2 task tools. Write tools require the admin token (P0-3).
    # ------------------------------------------------------------------

    @mcp.tool()
    def adl_task_create(
        objective: str, capabilities: list[str] | None = None, priority: int = 0
    ) -> dict[str, Any]:
        """Create a task chain (write tool; requires admin token)."""
        if not _mcp_write_allowed():
            return {"ok": False, "error": "MCP write tools require admin token (P0-3)"}
        from .agents.task import TaskRegistry

        engine = _get_engine()
        registry = TaskRegistry(engine=engine)
        task = registry.create_task(
            objective=objective, required_capabilities=capabilities or [], priority=priority
        )
        _save_engine(engine)
        return {"ok": True, "task_id": task.task_id, "status": task.status.value}

    @mcp.tool()
    def adl_task_claim(task_id: str, agent_did: str) -> dict[str, Any]:
        """Claim a task (write tool; requires admin token)."""
        if not _mcp_write_allowed():
            return {"ok": False, "error": "MCP write tools require admin token (P0-3)"}
        from .agents.task import TaskRegistry

        engine = _get_engine()
        registry = TaskRegistry(engine=engine)
        try:
            ev = registry.claim(task_id, agent_did)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "task_id": task_id, "error": str(exc)}
        _save_engine(engine)
        return {"ok": True, "task_id": task_id, "event_type": ev.event_type.value}

    @mcp.tool()
    def adl_task_submit(
        task_id: str, agent_did: str, result_ref: str, summary: str = "", confidence: float = 0.5
    ) -> dict[str, Any]:
        """Submit a task result (write tool; requires admin token)."""
        if not _mcp_write_allowed():
            return {"ok": False, "error": "MCP write tools require admin token (P0-3)"}
        from .agents.task import TaskRegistry

        engine = _get_engine()
        registry = TaskRegistry(engine=engine)
        try:
            ev = registry.submit(task_id, agent_did, result_ref, summary, confidence)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "task_id": task_id, "error": str(exc)}
        _save_engine(engine)
        return {"ok": True, "task_id": task_id, "event_type": ev.event_type.value}

    @mcp.tool()
    def adl_task_validate(
        task_id: str,
        validator_did: str,
        accepted: bool,
        confidence: float = 0.8,
        critique: str = "",
    ) -> dict[str, Any]:
        """Accept/reject a task submission (write tool; requires admin token)."""
        if not _mcp_write_allowed():
            return {"ok": False, "error": "MCP write tools require admin token (P0-3)"}
        from .agents.task import TaskRegistry

        engine = _get_engine()
        registry = TaskRegistry(engine=engine)
        try:
            ev = registry.validate_result(task_id, validator_did, accepted, confidence, critique)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "task_id": task_id, "error": str(exc)}
        _save_engine(engine)
        return {"ok": True, "task_id": task_id, "event_type": ev.event_type.value}

    @mcp.tool()
    def adl_task_close(task_id: str, actor: str, outcome: str, reason: str = "") -> dict[str, Any]:
        """Close a task (write tool; requires admin token)."""
        if not _mcp_write_allowed():
            return {"ok": False, "error": "MCP write tools require admin token (P0-3)"}
        from .agents.task import TaskRegistry

        engine = _get_engine()
        registry = TaskRegistry(engine=engine)
        try:
            ev = registry.close(task_id, actor, outcome, reason)  # type: ignore[arg-type]
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "task_id": task_id, "error": str(exc)}
        _save_engine(engine)
        return {"ok": True, "task_id": task_id, "event_type": ev.event_type.value}

    @mcp.tool()
    def adl_task_get(task_id: str) -> dict[str, Any]:
        """Get a task's derived status and result reference."""
        from .agents.task import TaskRegistry

        engine = _get_engine()
        if task_id not in engine.chains:
            return {"ok": False, "task_id": task_id, "error": "not registered"}
        registry = TaskRegistry(engine=engine)
        t = registry.get_task(task_id)
        return {
            "ok": True,
            "task_id": task_id,
            "status": t.status.value,
            "objective": t.objective,
            "result_ref": t.result_ref,
        }

    @mcp.tool()
    def adl_task_list(status: str = "", offset: int = 0, limit: int = 50) -> dict[str, Any]:
        """List tasks (optionally filtered by status)."""
        from .agents.task import TaskRegistry, TaskStatus

        engine = _get_engine()
        registry = TaskRegistry(engine=engine)
        st = TaskStatus(status) if status else None
        tasks = [
            {
                "task_id": t.task_id,
                "status": t.status.value,
                "objective": t.objective,
                "priority": t.priority,
            }
            for t in registry.list_tasks(status=st)
        ]
        total = len(tasks)
        return {
            "tasks": tasks[offset : offset + limit],
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    # ------------------------------------------------------------------
    # M3: runtime tools. adl_task_enqueue is fire-and-forget: it lands the
    # task on the chain (persistent); the run_forever loop consumes it via
    # the volatile queue (results polled through adl_task_get — plan risk 5).
    # ------------------------------------------------------------------

    @mcp.tool()
    def adl_task_enqueue(
        objective: str,
        capabilities: list[str] | None = None,
        input_ref: str = "",
        priority: int = 0,
    ) -> dict[str, Any]:
        """Enqueue a task for the runtime (write tool; requires admin token).
        Fire-and-forget: returns immediately with a task_id; poll
        adl_task_get for the result."""
        if not _mcp_write_allowed():
            return {"ok": False, "error": "MCP write tools require admin token (P0-3)"}
        from .agents.task import TaskRegistry

        engine = _get_engine()
        registry = TaskRegistry(engine=engine)
        task = registry.create_task(
            objective=objective,
            required_capabilities=capabilities or [],
            priority=priority,
            input_ref=input_ref or None,
            created_by="mcp",
        )
        _save_engine(engine)
        return {
            "ok": True,
            "task_id": task.task_id,
            "status": task.status.value,
            "note": "fire-and-forget: poll adl_task_get for the result",
        }

    @mcp.tool()
    def adl_runtime_start(did: str) -> dict[str, Any]:
        """Validate an agent for runtime execution (read tool). The
        run_forever loop itself is started in-process via ``adl-lite run``
        (single-process deployment, P1-4); this tool confirms the agent is
        registered and reports its status."""
        from .agents.identity import AgentRegistry

        engine = _get_engine()
        registry = AgentRegistry(engine=engine)
        profile = registry.get_agent(did)
        if profile is None:
            return {"ok": False, "did": did, "error": "not registered"}
        return {
            "ok": True,
            "did": did,
            "role": profile.role.value,
            "status": registry.agent_status(did).value,
            "note": "run_forever loop: adl-lite run --did <did> (single-process)",
        }

    @mcp.tool()
    def adl_agent_reputation(did: str) -> dict[str, Any]:
        """Weak-signal reputation for an agent (M4, read tool; ranking only,
        P1-7). Public-scope agents only (no tenant context in MCP)."""
        from .agents.identity import AgentRegistry, chain_kind
        from .agents.trust import Reputation

        engine = _get_engine()
        chain = engine.chains.get(did)
        if chain is None or chain_kind(chain) != "agent" or not _is_public(chain):
            return {"ok": False, "did": did, "error": "not registered or not public"}
        rep = Reputation(engine, AgentRegistry(engine=engine))
        s = rep.score(did)
        return {
            "ok": True,
            "did": did,
            "score_v2": rep.formula_v2(s),
            "validate_count": s.validate_count,
            "submit_count": s.submit_count,
            "accepted_count": s.accepted_count,
            "task_success_rate": s.task_success_rate,
            "fork_merge_rate": s.fork_merge_rate,
            "deprecation_rate": s.deprecation_rate,
        }

    # ------------------------------------------------------------------
    # Resource 1: adl://ontology
    # ------------------------------------------------------------------

    @mcp.resource("adl://ontology")
    def ontology_resource() -> dict[str, Any]:
        """The core ADL ontology schema as a JSON resource."""
        mgr = default_ontology()
        return mgr.query_schema()

    # ------------------------------------------------------------------
    # Resource 2: adl://capability/{adl_id}
    # ------------------------------------------------------------------

    @mcp.resource("adl://capability/{adl_id}")
    def capability_resource(adl_id: str) -> dict[str, Any]:
        """Capability detail resource: status + latest event info."""
        engine = _get_engine()

        chain = engine.chains.get(adl_id)
        if chain is None or not _is_public(chain):
            return {"adl_id": adl_id, "status": "unknown", "error": "not registered"}

        latest = chain.events[-1] if chain.events else None
        return {
            "adl_id": adl_id,
            "status": chain.status.value,
            "confidence": chain.confidence,
            "latest_event_type": latest.event_type.value if latest else "",
            "latest_event_actor": latest.actor if latest else "",
            "latest_event_timestamp": latest.timestamp if latest else "",
        }

    # ------------------------------------------------------------------
    # Prompt 1: adl_lifecycle_prompt
    # ------------------------------------------------------------------

    @mcp.prompt()
    def adl_lifecycle_prompt(adl_id: str) -> str:
        """Generate a prompt template for analyzing a capability lifecycle."""
        engine = _get_engine()

        chain = engine.chains.get(adl_id)
        if chain is None or not _is_public(chain):
            return (
                f"Analyze the capability lifecycle for '{adl_id}'. "
                f"This capability is not yet registered in the consensus engine. "
                f"Consider: Should it be registered? What domain and scope would be appropriate?"
            )
        history = chain.history()
        status = chain.status.value

        events_summary = "\n".join(
            f"  - {e['event_type']} by {e['actor']} at {e['timestamp']}" for e in history
        )

        return (
            f"Analyze the capability lifecycle for '{adl_id}' (current status: {status}).\n\n"
            f"Event chain history ({len(history)} events):\n{events_summary}\n\n"
            f"Consider:\n"
            f"1. Is the current lifecycle status appropriate for this capability?\n"
            f"2. What transitions are available from {status}?\n"
            f"3. Are there any integrity concerns in the event chain?\n"
            f"4. What evidence or validation would support the next transition?"
        )

    return mcp


# ---------------------------------------------------------------------------
# Default server instance for `python -m adl_lite.mcp_server`
# ---------------------------------------------------------------------------

_default_server = create_mcp_server()


def main() -> None:
    """Entry point for running the MCP server."""
    import argparse

    parser = argparse.ArgumentParser(description="ADL Lite MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport mode (default: stdio)",
    )
    parser.add_argument(
        "--state-path",
        default=None,
        help="Path to consensus state JSON file (default: .adl/state.json)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for streamable-http transport (default: 8000)",
    )
    parser.add_argument(
        "--admin-token",
        default=None,
        help="Bearer token required for write tools (streamable-http only; "
        "stdio has no auth context and denies writes — P0-3/P1-1)",
    )
    args = parser.parse_args()

    server = create_mcp_server(state_path=args.state_path, admin_token=args.admin_token)

    if args.transport == "stdio":
        server.run(transport="stdio")
    else:
        server.run(transport="streamable-http", port=args.port)


if __name__ == "__main__":
    main()
