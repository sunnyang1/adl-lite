"""ADL Lite — FastAPI REST API for consensus lifecycle operations.

Exposes the ConsensusEngine and related subsystems as JSON endpoints
under ``/api/v1/consensus/``. Designed for integration with external
agent orchestrators and web-based dashboards.

Endpoints:
    POST   /api/v1/consensus/register        — register a capability
    POST   /api/v1/consensus/transition       — transition status
    GET    /api/v1/consensus/status/{adl_id}  — query current status
    GET    /api/v1/consensus/history/{adl_id} — full event history
    POST   /api/v1/consensus/fork             — fork a capability
    GET    /api/v1/consensus/verify/{adl_id}  — verify chain integrity
    GET    /api/v1/consensus/list             — list all registered capabilities
    POST   /api/v1/consensus/mode/dev         — set dev mode (admin only)
    POST   /api/v1/consensus/mode/production  — set production mode (admin only)
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .api_auth import (
    RateLimitMiddleware,
    UserInfo,
    configure_auth,
    require_admin,
    require_auth,
)
from .consensus import ConsensusEngine
from .exceptions import ADLConsensusError
from .models import ADLDocument, ADLFrontMatter, ADLType, DiscoveryStatus, Event, EventType
from .ontology import default_ontology

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """Request body for registering a capability."""

    adl_id: str = Field(..., description="Unique capability identifier")
    scope: str = Field(default="public", description="Visibility scope")
    domain: str = Field(default="", description="Domain tag")


class TransitionRequest(BaseModel):
    """Request body for transitioning a capability status."""

    adl_id: str = Field(..., description="Capability to transition")
    to_status: str = Field(..., description="Target status: validated|deprecated|archived")
    actor: str = Field(..., description="Actor performing the transition")
    reason: str = Field(default="", description="Reason for the transition")
    payload: dict[str, Any] = Field(default_factory=dict, description="Extra payload data")


class ForkRequest(BaseModel):
    """Request body for creating a capability fork."""

    original_id: str = Field(..., description="Original capability to fork from")
    fork_id: str = Field(..., description="New fork capability ID")
    actor: str = Field(..., description="Actor creating the fork")
    reason: str = Field(default="", description="Reason for the fork")


class StatusResponse(BaseModel):
    """Response for status query."""

    adl_id: str
    status: str
    confidence: float = 0.0
    validators: list[str] = Field(default_factory=list)
    dev_mode: bool = False


class HistoryResponse(BaseModel):
    """Response for history query."""

    adl_id: str
    events: list[dict[str, Any]]


class VerifyResponse(BaseModel):
    """Response for integrity verification."""

    adl_id: str
    integrity_ok: bool


class PaginatedListResponse(BaseModel):
    """Paginated response for listing registered capabilities."""

    capabilities: list[str]
    total: int
    count: int  # Alias for total (backward compat with old ListResponse)
    offset: int
    limit: int


class ListResponse(BaseModel):
    """Legacy response for listing registered capabilities (backward compat)."""

    capabilities: list[str]
    count: int


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: str = ""


# ---------------------------------------------------------------------------
# Pagination constants
# ---------------------------------------------------------------------------

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50
_DEFAULT_OFFSET = 0


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

# Module-level engine and lock. The engine is lazily initialised on first
# request and persists across the lifetime of the server process.
_engine: ConsensusEngine | None = None
_engine_lock = threading.Lock()
_state_path: Path = Path("adl_consensus.json")


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
                        chain = _engine.chains.get(cid)
                        if chain is None:
                            from .models import EventChain

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


def create_app(
    state_path: str | None = None,
    auth_enabled: bool = False,
    jwt_secret: str = "change-me",
    api_keys: set[str] | None = None,
    rate_limit: int = 0,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        state_path: Path to consensus state JSON file. Defaults to
            ``adl_consensus.json`` in the current working directory.
        auth_enabled: Whether to require authentication on endpoints.
            When ``False``, all endpoints are accessible without auth
            (backward compat with existing tests).
        jwt_secret: Secret key for JWT signing/verification.
        api_keys: Set of valid API keys for ``X-API-Key`` auth.
        rate_limit: Max requests per 60s window per client. ``0`` disables.
    """
    global _state_path, _engine
    if state_path is not None:
        _state_path = Path(state_path)
    _engine = None  # Reset engine so it re-loads from new state_path

    # Configure auth module globals
    configure_auth(
        jwt_secret=jwt_secret,
        api_keys=api_keys or set(),
        auth_enabled=auth_enabled,
    )

    app = FastAPI(
        title="ADL Lite Consensus API",
        version="0.5.0-alpha",
        description="REST API for ADL Lite consensus lifecycle operations",
    )

    # Add rate-limit middleware
    if rate_limit > 0:
        app.add_middleware(RateLimitMiddleware, rate_limit=rate_limit)

    # ------------------------------------------------------------------
    # POST /api/v1/consensus/register
    # ------------------------------------------------------------------
    @app.post("/api/v1/consensus/register", response_model=StatusResponse)
    def register_capability(
        req: RegisterRequest,
        user: UserInfo = Depends(require_auth),
    ) -> StatusResponse:
        engine = _get_engine()
        if req.adl_id in engine.chains:
            raise HTTPException(status_code=409, detail=f"Already registered: {req.adl_id}")

        stub = ADLDocument(
            front_matter=ADLFrontMatter(
                adl_type=ADLType.CONCEPT,
                adl_id=req.adl_id,
                scope=req.scope,
                domain=req.domain,
            )
        )
        chain = engine.register(stub)
        _save_engine(engine)

        return StatusResponse(
            adl_id=req.adl_id,
            status=chain.status.value,
            confidence=chain.confidence,
            validators=list(chain.validators),
            dev_mode=engine.dev_mode,
        )

    # ------------------------------------------------------------------
    # POST /api/v1/consensus/transition
    # ------------------------------------------------------------------
    @app.post("/api/v1/consensus/transition", response_model=StatusResponse)
    def transition_capability(
        req: TransitionRequest,
        user: UserInfo = Depends(require_auth),
    ) -> StatusResponse:
        engine = _get_engine()
        try:
            target = DiscoveryStatus(req.to_status)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid status: {req.to_status}"
            ) from None

        try:
            event = engine.transition(
                req.adl_id,
                target,
                actor=req.actor,
                reason=req.reason,
                payload=req.payload,
            )
        except ADLConsensusError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        if event is None:
            raise HTTPException(status_code=500, detail="Transition failed: no event returned")

        _save_engine(engine)

        chain = engine.chains[req.adl_id]
        return StatusResponse(
            adl_id=req.adl_id,
            status=chain.status.value,
            confidence=chain.confidence,
            validators=list(chain.validators),
            dev_mode=engine.dev_mode,
        )

    # ------------------------------------------------------------------
    # GET /api/v1/consensus/status/{adl_id}
    # ------------------------------------------------------------------
    @app.get("/api/v1/consensus/status/{adl_id}", response_model=StatusResponse)
    def get_status(
        adl_id: str,
        user: UserInfo = Depends(require_auth),
    ) -> StatusResponse:
        engine = _get_engine()
        if adl_id not in engine.chains:
            raise HTTPException(status_code=404, detail=f"Not registered: {adl_id}")

        chain = engine.chains[adl_id]
        return StatusResponse(
            adl_id=adl_id,
            status=chain.status.value,
            confidence=chain.confidence,
            validators=list(chain.validators),
            dev_mode=engine.dev_mode,
        )

    # ------------------------------------------------------------------
    # GET /api/v1/consensus/history/{adl_id}
    # ------------------------------------------------------------------
    @app.get("/api/v1/consensus/history/{adl_id}", response_model=HistoryResponse)
    def get_history(
        adl_id: str,
        user: UserInfo = Depends(require_auth),
    ) -> HistoryResponse:
        engine = _get_engine()
        history = engine.get_history(adl_id)
        if not history:
            raise HTTPException(status_code=404, detail=f"No history for: {adl_id}")

        return HistoryResponse(adl_id=adl_id, events=history)

    # ------------------------------------------------------------------
    # POST /api/v1/consensus/fork
    # ------------------------------------------------------------------
    @app.post("/api/v1/consensus/fork", response_model=StatusResponse)
    def fork_capability(
        req: ForkRequest,
        user: UserInfo = Depends(require_auth),
    ) -> StatusResponse:
        engine = _get_engine()
        try:
            new_chain = engine.fork(req.original_id, req.fork_id, req.actor, req.reason)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ADLConsensusError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        _save_engine(engine)

        return StatusResponse(
            adl_id=req.fork_id,
            status=new_chain.status.value,
            confidence=new_chain.confidence,
            validators=list(new_chain.validators),
            dev_mode=engine.dev_mode,
        )

    # ------------------------------------------------------------------
    # GET /api/v1/consensus/verify/{adl_id}
    # ------------------------------------------------------------------
    @app.get("/api/v1/consensus/verify/{adl_id}", response_model=VerifyResponse)
    def verify_integrity(
        adl_id: str,
        user: UserInfo = Depends(require_auth),
    ) -> VerifyResponse:
        engine = _get_engine()
        if adl_id not in engine.chains:
            raise HTTPException(status_code=404, detail=f"Not registered: {adl_id}")

        ok = engine.chains[adl_id].verify_integrity()
        return VerifyResponse(adl_id=adl_id, integrity_ok=ok)

    # ------------------------------------------------------------------
    # GET /api/v1/consensus/list
    # ------------------------------------------------------------------
    @app.get("/api/v1/consensus/list", response_model=PaginatedListResponse)
    def list_capabilities(
        offset: int = Query(default=_DEFAULT_OFFSET, ge=0, description="Pagination offset"),
        limit: int = Query(default=_DEFAULT_LIMIT, ge=1, description="Page size (max 200)"),
        user: UserInfo = Depends(require_auth),
    ) -> PaginatedListResponse:
        if limit > _MAX_LIMIT:
            raise HTTPException(
                status_code=400, detail=f"Limit cannot exceed {_MAX_LIMIT}"
            ) from None

        engine = _get_engine()
        caps = sorted(engine.chains.keys())
        total = len(caps)
        slice_caps = caps[offset : offset + limit]
        return PaginatedListResponse(
            capabilities=slice_caps,
            total=total,
            count=total,
            offset=offset,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # POST /api/v1/consensus/mode/dev
    # ------------------------------------------------------------------
    @app.post("/api/v1/consensus/mode/dev", response_model=dict)
    def set_dev_mode(
        user: UserInfo = Depends(require_admin),
    ) -> dict[str, Any]:
        engine = _get_engine()
        engine.set_dev_mode()
        return {"mode": "dev", "n_min": 1, "dev_mode": True}

    # ------------------------------------------------------------------
    # POST /api/v1/consensus/mode/production
    # ------------------------------------------------------------------
    @app.post("/api/v1/consensus/mode/production", response_model=dict)
    def set_production_mode(
        user: UserInfo = Depends(require_admin),
    ) -> dict[str, Any]:
        engine = _get_engine()
        engine.set_production_mode()
        n_min = engine._effective_n_min()
        return {"mode": "production", "n_min": n_min, "dev_mode": False}

    return app


# ---------------------------------------------------------------------------
# Convenience: default app instance for ``uvicorn adl_lite.api:create_app``
# ---------------------------------------------------------------------------

app = create_app()
