"""
ADL Lite — agent-facing tool wrappers for capability-lifecycle registry operations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .cli import _default_state_path, _load_engine, _save_engine
from .exceptions import ADLConsensusError
from .memory import ADLMemory
from .models import DiscoveryStatus
from .ontology import OntologyManager, default_ontology
from .parser import ADLParseError, parse_file
from .validator import ADLValidator


def adl_parse(path: str | Path) -> dict[str, Any]:
    """Parse an ADL file; returns summary dict (matches `adl-lite parse -o json` shape)."""
    doc = parse_file(path)
    data: dict[str, Any] = json.loads(doc.model_dump_json())
    data["_summary"] = {
        "adl_id": doc.adl_id,
        "concept_name": doc.concept_name,
        "relations": len(doc.relations),
        "evidence": len(doc.evidence),
        "wiki_links": doc.wiki_links,
    }
    return data


def adl_validate(path: str | Path) -> dict[str, Any]:
    """Validate one file; returns {ok, errors, path}."""
    path = Path(path)
    try:
        doc = parse_file(path)
    except (ADLParseError, OSError, ValueError) as exc:
        return {"ok": False, "path": str(path), "errors": [f"parse error: {exc}"]}

    errors = ADLValidator().validate_document(doc)
    return {"ok": len(errors) == 0, "path": str(path), "errors": errors}


def adl_store(path: str | Path, db: str | Path) -> dict[str, Any]:
    """Store document in ADLMemory."""
    doc = parse_file(path)
    mem = ADLMemory(db_path=str(db))
    mem.store(doc)
    mem.close()
    return {"stored": doc.adl_id, "db": str(db)}


def adl_query_related(
    adl_id: str,
    db: str | Path,
    depth: int = 1,
) -> list[dict[str, Any]]:
    """Graph neighbors for a capability adl_id."""
    mem = ADLMemory(db_path=str(db))
    related = mem.find_related(adl_id, depth=depth)
    mem.close()
    return [
        {"concept": concept, "relation": relation, "confidence": conf}
        for concept, relation, conf in related
    ]


def adl_consensus_register(
    path: str | Path | None = None,
    adl_id: str | None = None,
    state: str | Path | None = None,
) -> dict[str, Any]:
    """Register capability in consensus engine."""
    state_path = Path(state) if state else _default_state_path(None)
    engine = _load_engine(state_path)

    if path:
        doc = parse_file(path)
        engine.register(doc)
        cid = doc.adl_id
    elif adl_id:
        if adl_id not in engine.chains:
            from .models import ADLDocument, ADLFrontMatter, ADLType, ProvisionalNames

            stub = ADLDocument(
                front_matter=ADLFrontMatter(
                    adl_type=ADLType.CONCEPT,
                    adl_id=adl_id,
                    scope="public",
                    provisional_names=ProvisionalNames(en=adl_id),
                )
            )
            engine.register(stub)
        cid = adl_id
    else:
        raise ValueError("adl_consensus_register requires path or adl_id")

    _save_engine(engine, state_path)
    return {"registered": cid, "state": str(state_path)}


def adl_consensus_transition(
    adl_id: str,
    to_status: str | DiscoveryStatus,
    actor: str,
    reason: str = "",
    state: str | Path | None = None,
) -> dict[str, Any]:
    """Transition capability status via consensus engine."""
    state_path = Path(state) if state else _default_state_path(None)
    engine = _load_engine(state_path)
    target = DiscoveryStatus(to_status) if isinstance(to_status, str) else to_status
    event = engine.transition(adl_id, target, actor=actor, reason=reason)
    _save_engine(engine, state_path)
    if event is None:
        return {"adl_id": adl_id, "error": "transition returned None"}
    # engine.transition() returns an Event — use event_type for the target status
    return {
        "adl_id": adl_id,
        "event_type": event.event_type.value,
        "actor": event.actor,
        "hash": event.hash,
        "timestamp": event.timestamp,
    }


def adl_ontology_query(
    ontology_path: str | Path | None = None,
    predicate: str | None = None,
    from_status: str | None = None,
    to_status: str | None = None,
) -> dict[str, Any]:
    """
    Introspect the core ontology registry (Milestone 2c).

    Returns predicates, status transitions, scope prefixes, mapping types,
    and registry version/path. Optional filters narrow the response:

        predicate     — include only that predicate (with allowed_mapping_types)
        from_status   — restrict allowed_transitions to one source status
        to_status     — with from_status, adds is_valid_transition bool
    """
    mgr = OntologyManager(ontology_path) if ontology_path else default_ontology()
    return mgr.query_schema(
        predicate=predicate,
        from_status=from_status,
        to_status=to_status,
    )


def adl_consensus_verify(
    adl_id: str,
    state: str | Path | None = None,
) -> dict[str, Any]:
    """Verify chain integrity for adl_id."""
    state_path = Path(state) if state else _default_state_path(None)
    engine = _load_engine(state_path)
    if adl_id not in engine.chains:
        return {"ok": False, "adl_id": adl_id, "error": "not registered"}
    ok = engine.chains[adl_id].verify_integrity()
    return {
        "ok": ok,
        "adl_id": adl_id,
        "status": engine.get_status(adl_id).value,
    }


# ---------------------------------------------------------------------------
# Agent identity tools (M1b)
# ---------------------------------------------------------------------------


def _agent_registry(state_path: Path, admin_calls_allowed: bool = False):
    """Load engine + AgentRegistry for a state path (CLI/tools default: admin off)."""
    from .agents.identity import AgentRegistry

    engine = _load_engine(state_path)
    registry = AgentRegistry(engine=engine, admin_calls_allowed=admin_calls_allowed)
    return engine, registry


def adl_agent_register(
    name: str,
    role: str,
    model: str = "",
    capabilities: list[str] | None = None,
    scope: str = "public",
    org_id: str | None = None,
    public_key: Any | None = None,
    state: str | Path | None = None,
) -> dict[str, Any]:
    """Register an agent identity (private key stays with the caller, P2-10)."""
    from .agents.identity import AgentProfile, AgentRole

    state_path = Path(state) if state else _default_state_path(None)
    engine, registry = _agent_registry(state_path)
    try:
        profile = AgentProfile(
            did="",
            role=AgentRole(role),
            name=name,
            model=model,
            capabilities=capabilities or [],
            scope=scope,
            org_id=org_id,
        )
        chain = registry.register_agent(profile, public_key=public_key)
    except (ADLConsensusError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}
    _save_engine(engine, state_path)
    return {
        "ok": True,
        "did": profile.did,
        "status": registry.agent_status(profile.did).value,
        "validator_count": len(registry._agent_validators(chain)),
        "state": str(state_path),
    }


def adl_agent_attest(
    did: str,
    signature: str,
    proof: dict[str, Any] | None = None,
    state: str | Path | None = None,
) -> dict[str, Any]:
    """Bind a caller-side genesis signature/proof to a registered agent."""
    state_path = Path(state) if state else _default_state_path(None)
    engine, registry = _agent_registry(state_path)
    chain = engine.chains.get(did)
    if chain is None:
        return {"ok": False, "did": did, "error": "not registered"}
    chain.events[0].signature = signature
    if proof is not None:
        chain.events[0].proof = proof
    _save_engine(engine, state_path)
    return {
        "ok": True,
        "did": did,
        "status": registry.agent_status(did).value,
        "state": str(state_path),
    }


def adl_agent_validate(
    did: str,
    actor_did: str,
    reason: str = "",
    confidence: float = 0.9,
    signature: str = "",
    admin: bool = False,
    state: str | Path | None = None,
) -> dict[str, Any]:
    """Validate an agent identity; admin=True is the trust-root path (P0-1)."""
    state_path = Path(state) if state else _default_state_path(None)
    engine, registry = _agent_registry(state_path, admin_calls_allowed=admin)
    try:
        event = registry.validate_agent(
            did,
            actor_did,
            reason=reason,
            confidence=confidence,
            signature=signature,
            admin=admin,
        )
    except ADLConsensusError as exc:
        return {"ok": False, "did": did, "error": str(exc)}
    _save_engine(engine, state_path)
    return {
        "ok": True,
        "did": did,
        "event_type": event.event_type.value,
        "actor": event.actor,
        "status": registry.agent_status(did).value,
        "state": str(state_path),
    }


def adl_agent_list(
    scope: str | None = None,
    state: str | Path | None = None,
) -> dict[str, Any]:
    """List registered agents (optionally filtered by scope)."""
    state_path = Path(state) if state else _default_state_path(None)
    _engine, registry = _agent_registry(state_path)
    agents = [
        {
            "did": p.did,
            "role": p.role.value,
            "name": p.name,
            "status": registry.agent_status(p.did).value,
        }
        for p in registry.list_agents(scope=scope)
    ]
    return {"ok": True, "total": len(agents), "agents": agents}


def adl_agent_get(
    did: str,
    state: str | Path | None = None,
) -> dict[str, Any]:
    """Get a single agent profile (derived from its chain)."""
    state_path = Path(state) if state else _default_state_path(None)
    _engine, registry = _agent_registry(state_path)
    profile = registry.get_agent(did)
    if profile is None:
        return {"ok": False, "did": did, "error": "not registered"}
    return {
        "ok": True,
        "did": did,
        "role": profile.role.value,
        "name": profile.name,
        "model": profile.model,
        "capabilities": profile.capabilities,
        "scope": profile.scope,
        "status": registry.agent_status(did).value,
    }


def adl_agent_deprecate(
    did: str,
    actor: str,
    reason: str = "",
    state: str | Path | None = None,
) -> dict[str, Any]:
    """Decommission an agent (owner or admin)."""
    state_path = Path(state) if state else _default_state_path(None)
    engine, registry = _agent_registry(state_path)
    try:
        registry.deprecate_agent(did, actor, reason)
    except ADLConsensusError as exc:
        return {"ok": False, "did": did, "error": str(exc)}
    _save_engine(engine, state_path)
    return {"ok": True, "did": did, "status": registry.agent_status(did).value}


def adl_agent_reputation(did: str, state: str | Path | None = None) -> dict[str, Any]:
    """M4: reputation score for an agent (weak signal, P1-7 — ranking only)."""
    state_path = Path(state) if state else _default_state_path(None)
    engine, registry = _agent_registry(state_path)
    from .agents.trust import Reputation

    rep = Reputation(engine, registry)
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
        "note": "weak signal: ranking only, never security admission",
    }


def adl_agent_trust_check(
    did: str,
    state: str | Path | None = None,
    diversity: bool = False,
    min_reputation: float = 0.0,
) -> dict[str, Any]:
    """M4: run the trust model (B1-B4) against a chain.

    ``diversity=True`` activates B4 with a DidWebAffiliationResolver
    (offline-first); ``min_reputation>0`` enforces the reputation floor.
    """
    from .agents.identity import chain_kind
    from .agents.trust import DidWebAffiliationResolver, Reputation
    from .trust_model import ConsensusConfig, TrustValidator

    state_path = Path(state) if state else _default_state_path(None)
    engine = _load_engine(state_path)
    chain = engine.chains.get(did)
    if chain is None:
        return {"ok": False, "did": did, "error": "not registered"}
    if chain_kind(chain) != "discovery":
        return {
            "ok": False,
            "did": did,
            "error": f"trust-check targets discovery chains only (got {chain_kind(chain)})",
        }

    from .agents.identity import AgentRegistry

    provider = DidWebAffiliationResolver(offline=True) if diversity else None
    reputation_store = (
        Reputation(engine, AgentRegistry(engine=engine)) if min_reputation > 0 else None
    )
    validator = TrustValidator(diversity_provider=provider, reputation_store=reputation_store)
    config = ConsensusConfig(
        enforce_validator_diversity=diversity,
        min_validator_reputation=min_reputation,
        min_distinct_validators=1 if diversity else None,
    )
    result = validator.validate_event_chain(chain, config)
    return {
        "ok": result.valid,
        "did": did,
        "valid": result.valid,
        "errors": result.errors,
        "distinct_validators": result.distinct_validators,
        "diversity_satisfied": result.diversity_satisfied,
    }


# ---------------------------------------------------------------------------
# Task lifecycle tools (M2)
# ---------------------------------------------------------------------------


def _task_registry(state_path: Path):
    from .agents.task import TaskRegistry

    engine = _load_engine(state_path)
    return engine, TaskRegistry(engine=engine)


def adl_task_create(
    objective: str,
    capabilities: list[str] | None = None,
    created_by: str = "planner",
    priority: int = 0,
    scope: str = "public",
    state: str | Path | None = None,
) -> dict[str, Any]:
    """Create a task as an EventChain."""
    state_path = Path(state) if state else _default_state_path(None)
    engine, registry = _task_registry(state_path)
    task = registry.create_task(
        objective=objective,
        required_capabilities=capabilities or [],
        created_by=created_by,
        priority=priority,
        scope=scope,
    )
    _save_engine(engine, state_path)
    return {"ok": True, "task_id": task.task_id, "status": task.status.value}


def adl_task_assign(
    task_id: str, agent_did: str, actor: str = "planner", state: str | Path | None = None
) -> dict[str, Any]:
    state_path = Path(state) if state else _default_state_path(None)
    engine, registry = _task_registry(state_path)
    try:
        ev = registry.assign(task_id, agent_did, actor)
    except (ADLConsensusError, KeyError) as exc:
        return {"ok": False, "task_id": task_id, "error": str(exc)}
    _save_engine(engine, state_path)
    return {"ok": True, "task_id": task_id, "event_type": ev.event_type.value}


def adl_task_claim(task_id: str, agent_did: str, state: str | Path | None = None) -> dict[str, Any]:
    state_path = Path(state) if state else _default_state_path(None)
    engine, registry = _task_registry(state_path)
    try:
        ev = registry.claim(task_id, agent_did)
    except (ADLConsensusError, KeyError) as exc:
        return {"ok": False, "task_id": task_id, "error": str(exc)}
    _save_engine(engine, state_path)
    return {"ok": True, "task_id": task_id, "event_type": ev.event_type.value}


def adl_task_submit(
    task_id: str,
    agent_did: str,
    result_ref: str,
    summary: str = "",
    confidence: float = 0.5,
    state: str | Path | None = None,
) -> dict[str, Any]:
    state_path = Path(state) if state else _default_state_path(None)
    engine, registry = _task_registry(state_path)
    try:
        ev = registry.submit(task_id, agent_did, result_ref, summary, confidence)
    except (ADLConsensusError, KeyError) as exc:
        return {"ok": False, "task_id": task_id, "error": str(exc)}
    _save_engine(engine, state_path)
    return {
        "ok": True,
        "task_id": task_id,
        "event_type": ev.event_type.value,
        "result_ref": result_ref,
    }


def adl_task_validate(
    task_id: str,
    validator_did: str,
    accepted: bool,
    confidence: float = 0.8,
    critique: str = "",
    state: str | Path | None = None,
) -> dict[str, Any]:
    state_path = Path(state) if state else _default_state_path(None)
    engine, registry = _task_registry(state_path)
    try:
        ev = registry.validate_result(task_id, validator_did, accepted, confidence, critique)
    except (ADLConsensusError, KeyError) as exc:
        return {"ok": False, "task_id": task_id, "error": str(exc)}
    _save_engine(engine, state_path)
    return {"ok": True, "task_id": task_id, "event_type": ev.event_type.value}


def adl_task_close(
    task_id: str, outcome: str, actor: str, reason: str = "", state: str | Path | None = None
) -> dict[str, Any]:
    state_path = Path(state) if state else _default_state_path(None)
    engine, registry = _task_registry(state_path)
    try:
        ev = registry.close(task_id, actor, outcome, reason)  # type: ignore[arg-type]
    except (ADLConsensusError, KeyError) as exc:
        return {"ok": False, "task_id": task_id, "error": str(exc)}
    _save_engine(engine, state_path)
    return {"ok": True, "task_id": task_id, "event_type": ev.event_type.value}


def adl_task_get(task_id: str, state: str | Path | None = None) -> dict[str, Any]:
    state_path = Path(state) if state else _default_state_path(None)
    _engine, registry = _task_registry(state_path)
    if task_id not in _engine.chains:
        return {"ok": False, "task_id": task_id, "error": "not registered"}
    t = registry.get_task(task_id)
    return {
        "ok": True,
        "task_id": task_id,
        "status": t.status.value,
        "objective": t.objective,
        "result_ref": t.result_ref,
        "required_capabilities": t.required_capabilities,
    }


def adl_task_list(status: str | None = None, state: str | Path | None = None) -> dict[str, Any]:
    from .agents.task import TaskStatus

    state_path = Path(state) if state else _default_state_path(None)
    _engine, registry = _task_registry(state_path)
    st = TaskStatus(status) if status else None
    tasks = [
        {
            "task_id": t.task_id,
            "status": t.status.value,
            "objective": t.objective,
            "priority": t.priority,
            "result_ref": t.result_ref,
        }
        for t in registry.list_tasks(status=st)
    ]
    return {"ok": True, "total": len(tasks), "tasks": tasks}
