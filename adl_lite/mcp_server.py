"""ADL Lite — FastMCP tool server for the capability-lifecycle registry.

Exposes 10 tools, 2 resources, and 1 prompt via the official MCP Python SDK's
FastMCP class. Tools wrap the existing consensus engine, parser, validator,
and ontology subsystems.

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

from .consensus import ConsensusEngine
from .models import (
    ADLDocument,
    ADLFrontMatter,
    ADLType,
    DiscoveryStatus,
    EventType,
    ProvisionalNames,
)
from .ontology import default_ontology
from .tools import adl_parse as _adl_parse
from .tools import adl_validate as _adl_validate

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
                            chain.append(event)
                        _engine.chains[cid] = chain
    return _engine


def _save_engine(engine: ConsensusEngine) -> None:
    """Persist engine state to disk."""
    payload = {"chains": {cid: chain.history() for cid, chain in engine.chains.items()}}
    _state_path.parent.mkdir(parents=True, exist_ok=True)
    _state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Server factory
# ---------------------------------------------------------------------------


def create_mcp_server(state_path: str | None = None) -> FastMCP:
    """Create and configure a FastMCP server for ADL Lite.

    Args:
        state_path: Path to consensus state JSON file. Defaults to
            ``.adl/state.json`` in the current working directory.

    Returns:
        A configured FastMCP instance with 10 tools, 2 resources, 1 prompt.
    """
    global _state_path, _engine
    if state_path is not None:
        _state_path = Path(state_path)
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

        if adl_id not in engine.chains:
            return {
                "adl_id": adl_id,
                "status": "provisional",
                "confidence": 0.0,
                "event_count": 0,
                "error": "not registered",
            }

        chain = engine.chains[adl_id]
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

        if adl_id not in engine.chains:
            return {
                "ok": False,
                "adl_id": adl_id,
                "status": "unknown",
                "chain_length": 0,
                "error": "not registered",
            }

        ok = engine.chains[adl_id].verify_integrity()
        return {
            "ok": ok,
            "adl_id": adl_id,
            "status": engine.get_status(adl_id).value,
            "chain_length": engine.chains[adl_id].length,
        }

    # ------------------------------------------------------------------
    # Tool 7: adl_history
    # ------------------------------------------------------------------

    @mcp.tool()
    def adl_history(adl_id: str) -> list[dict[str, Any]]:
        """Get event chain history for a capability. Returns a list of
        event dicts with event_type, actor, timestamp, and hash."""
        engine = _get_engine()
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
        caps = sorted(engine.chains.keys())
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

        if adl_id not in engine.chains:
            return {"adl_id": adl_id, "status": "unknown", "error": "not registered"}

        chain = engine.chains[adl_id]
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

        if adl_id not in engine.chains:
            return (
                f"Analyze the capability lifecycle for '{adl_id}'. "
                f"This capability is not yet registered in the consensus engine. "
                f"Consider: Should it be registered? What domain and scope would be appropriate?"
            )

        chain = engine.chains[adl_id]
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
    args = parser.parse_args()

    server = create_mcp_server(state_path=args.state_path)

    if args.transport == "stdio":
        server.run(transport="stdio")
    else:
        server.run(transport="streamable-http", port=args.port)


if __name__ == "__main__":
    main()
