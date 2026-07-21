"""ADL Lite — FastAPI REST API for consensus lifecycle operations.

Exposes the ConsensusEngine and related subsystems as JSON endpoints
under ``/api/v1/consensus/``. Designed for integration with external
agent orchestrators and web-based dashboards.

Phase-2 multi-tenant slice
--------------------------
Each request resolves a ``TenantContext`` (via ``require_tenant``). Data-plane
endpoints operate on a per-tenant ``ConsensusEngine`` obtained from
``_get_engine(tid)`` (physically isolated via separate state files) and are
metered through ``meter_api_call``. Two read-only usage endpoints expose the
per-tenant counters.

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
    GET    /api/v1/consensus/mode              — get current mode (dev/production, N_min)
    GET    /api/v1/tenants/{tenant_id}/usage          — current-period usage (same tenant / admin)
    GET    /api/v1/tenants/{tenant_id}/usage/export   — usage export CSV/JSON (same tenant / admin)
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import __version__
from .api_auth import (
    RateLimitMiddleware,
    UserInfo,
    configure_auth,
    require_admin,
)
from .consensus import ConsensusEngine
from .exceptions import ADLConsensusError
from .metering import (
    DEFAULT_PERIOD,
    MeteringRecord,
    UsageMeter,
    compute_period_window,
    get_usage_meter,
)
from .models import ADLDocument, ADLFrontMatter, ADLType, DiscoveryStatus, Event, EventType
from .ontology import default_ontology
from .quota import check_quota, configure_quota, get_quota_config
from .tenant import (
    DEFAULT_TENANT,
    TenantContext,
    _safe_tenant_id,
    get_tenant_registry,
)

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

# Module-level engine and lock. The default-tenant engine is lazily initialised
# on first request and persists across the lifetime of the server process.
# Per-tenant engines are held in ``_engine_cache`` (keyed by tenant id).
_engine: ConsensusEngine | None = None
_engine_cache: dict[str, ConsensusEngine] = {}
_engine_lock = threading.Lock()
_state_path: Path = Path("adl_consensus.json")
_state_base_dir: Path | None = None

# Module-level metering singleton (re-bound inside ``create_app`` when a
# metering db path is supplied).
_meter: UsageMeter | None = None

# Module-level quota config singleton reference (aliases the process-wide
# singleton from ``quota.py`` so tests can reach ``_quota_config.reset()``).
_quota_config = get_quota_config()


def _load_engine(path: Path) -> ConsensusEngine:
    """Build a ``ConsensusEngine`` and hydrate it from ``path`` if present."""
    engine = ConsensusEngine(ontology=default_ontology())
    if path.exists() and path.stat().st_size > 0:
        data = json.loads(path.read_text(encoding="utf-8"))
        for cid, events_data in data.get("chains", {}).items():
            chain = engine.chains.get(cid)
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
            engine.chains[cid] = chain
    return engine


def _tenant_state_path(tid: str) -> Path:
    """Resolve the state-file path for a non-default tenant.

    Tenant state files live in a per-deployment state directory. When no
    explicit ``state_base_dir`` is supplied they are colocated with the
    default-tenant state file under a ``<state_file_stem>_tenants`` subdir.
    Keying the subdir on the default state file keeps concurrent apps (and
    isolated test runs) from colliding on a shared parent such as ``/tmp``.
    """
    safe = _safe_tenant_id(tid)
    if _state_base_dir is not None:
        base = _state_base_dir
    else:
        base = _state_path.parent / f"{_state_path.stem}_tenants"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{safe}.json"


def _get_engine(tid: str = DEFAULT_TENANT) -> ConsensusEngine:
    """Return the ``ConsensusEngine`` for tenant ``tid``.

    The default tenant uses the module-level ``_engine`` global (loaded from
    ``_state_path``); every other tenant is cached in ``_engine_cache`` and
    persisted to ``state_dir/{tid}.json``.
    """
    if tid == DEFAULT_TENANT:
        global _engine
        if _engine is None:
            with _engine_lock:
                if _engine is None:
                    _engine = _load_engine(_state_path)
        return _engine
    global _engine_cache
    if tid not in _engine_cache:
        with _engine_lock:
            if tid not in _engine_cache:
                _engine_cache[tid] = _load_engine(_tenant_state_path(tid))
    return _engine_cache[tid]


def _save_engine(tid: str = DEFAULT_TENANT, engine: ConsensusEngine | None = None) -> None:
    """Persist ``engine`` for tenant ``tid`` (and update the cache)."""
    if engine is None:
        # Nothing to persist; the cache is left untouched.
        return
    if tid == DEFAULT_TENANT:
        global _engine
        _engine = engine
        target = _state_path
    else:
        global _engine_cache
        _engine_cache[tid] = engine
        target = _tenant_state_path(tid)
    payload = {"chains": {cid: chain.history() for cid, chain in engine.chains.items()}}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def meter_api_call(
    tenant: TenantContext = Depends(check_quota),
    request: Request = None,  # type: ignore[assignment]
) -> TenantContext:
    """Metering dependency: record one API call for the resolved tenant.

    Appended to every data-plane endpoint. Returns the ``TenantContext`` so
    endpoints can read ``caller.id``. ``request`` is injected by FastAPI (it
    is never ``None`` at request time).
    """
    endpoint = request.url.path if request is not None else None
    # Record under the tenant's quota period so usage lines up with the
    # window that ``check_quota`` queries (period alignment, R12 §共享知识(3)).
    policy = get_quota_config().get_policy(tenant.id)
    _meter.record_api_call(tenant.id, endpoint=endpoint, period=policy.period)  # type: ignore[union-attr]
    return tenant


def create_app(
    state_path: str | None = None,
    auth_enabled: bool = False,
    jwt_secret: str = "change-me",
    api_keys: set[str] | None = None,
    rate_limit: int = 0,
    cors_origins: list[str] | None = None,
    api_key_tenants: dict[str, str] | None = None,
    state_base_dir: str | None = None,
    metering_db_path: str | None = None,
    quota_max_api_calls: int | None = None,
    quota_max_entities: int | None = None,
    quota_period: Literal["daily", "monthly"] = "monthly",
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        state_path: Path to the default-tenant consensus state JSON file.
            Defaults to ``adl_consensus.json`` in the CWD.
        auth_enabled: Whether to require authentication on endpoints.
        jwt_secret: Secret key for JWT signing/verification.
        api_keys: Set of valid API keys for ``X-API-Key`` auth.
        rate_limit: Max requests per 60s window per client. ``0`` disables.
        cors_origins: Allowed CORS origins. ``None`` allows all (dev mode).
        api_key_tenants: Optional API-key → tenant id mapping.
        state_base_dir: Base directory for per-tenant state files. Defaults
            to the parent of ``state_path``.
        metering_db_path: Path to the SQLite metering database. Defaults to
            an in-memory store.
        quota_max_api_calls: Global max API calls per period. ``None`` = unlimited.
        quota_max_entities: Global max registered entities per period. ``None`` = unlimited.
    """
    global _state_path, _engine, _engine_cache, _state_base_dir, _meter
    if state_path is not None:
        _state_path = Path(state_path)
    _engine = None  # Reset so it re-loads from the (possibly new) state_path
    _engine_cache.clear()
    _state_base_dir = Path(state_base_dir) if state_base_dir else None

    # Configure auth module globals
    configure_auth(  # type: ignore[call-arg]
        jwt_secret=jwt_secret,
        api_keys=api_keys or set(),
        auth_enabled=auth_enabled,
        api_key_tenants=api_key_tenants,
    )

    # (Re)bind the metering singleton for this app instance.
    _meter = get_usage_meter(metering_db_path)

    # Initialize QuotaConfig global policy (reset first for clean test state).
    _quota_config.reset()
    _quota_config._meter_db_path = metering_db_path
    if (
        quota_max_api_calls is not None
        or quota_max_entities is not None
        or quota_period != "monthly"
    ):
        configure_quota(
            max_api_calls=quota_max_api_calls,
            max_entities=quota_max_entities,
            period=quota_period,
        )

    app = FastAPI(
        title="ADL Lite Consensus API",
        version=__version__,
        description="REST API for ADL Lite consensus lifecycle operations",
    )

    # Add CORS middleware
    if cors_origins is None:
        # Development mode: allow all origins
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        # Production mode: restrict to specified origins
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
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
        caller: TenantContext = Depends(meter_api_call),
    ) -> StatusResponse:
        tid = caller.id
        engine = _get_engine(tid)
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
        _save_engine(tid, engine)
        # Successful registration counts as one registered entity (R6).
        # Record under the tenant's quota period so the entity count aligns
        # with the window that ``check_quota`` queries (period alignment).
        policy = get_quota_config().get_policy(tid)
        _meter.record_entity(tid, period=policy.period)  # type: ignore[union-attr]

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
        caller: TenantContext = Depends(meter_api_call),
    ) -> StatusResponse:
        tid = caller.id
        engine = _get_engine(tid)
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

        _save_engine(tid, engine)

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
        caller: TenantContext = Depends(meter_api_call),
    ) -> StatusResponse:
        tid = caller.id
        engine = _get_engine(tid)
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
        caller: TenantContext = Depends(meter_api_call),
    ) -> HistoryResponse:
        tid = caller.id
        engine = _get_engine(tid)
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
        caller: TenantContext = Depends(meter_api_call),
    ) -> StatusResponse:
        tid = caller.id
        engine = _get_engine(tid)
        try:
            new_chain = engine.fork(req.original_id, req.fork_id, req.actor, req.reason)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ADLConsensusError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        _save_engine(tid, engine)

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
        caller: TenantContext = Depends(meter_api_call),
    ) -> VerifyResponse:
        tid = caller.id
        engine = _get_engine(tid)
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
        caller: TenantContext = Depends(meter_api_call),
    ) -> PaginatedListResponse:
        if limit > _MAX_LIMIT:
            raise HTTPException(
                status_code=400, detail=f"Limit cannot exceed {_MAX_LIMIT}"
            ) from None

        tid = caller.id
        engine = _get_engine(tid)
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
    # GET /api/v1/consensus/mode
    # ------------------------------------------------------------------
    @app.get("/api/v1/consensus/mode", response_model=dict)
    def get_mode(
        caller: TenantContext = Depends(meter_api_call),
    ) -> dict[str, Any]:
        """Return current consensus mode (dev/production) and N_min threshold."""
        tid = caller.id
        engine = _get_engine(tid)
        n_min = engine._effective_n_min()
        return {
            "mode": "dev" if engine.dev_mode else "production",
            "n_min": n_min,
            "dev_mode": engine.dev_mode,
        }

    # ------------------------------------------------------------------
    # POST /api/v1/consensus/mode/dev  (control plane — not metered)
    # ------------------------------------------------------------------
    @app.post("/api/v1/consensus/mode/dev", response_model=dict)
    def set_dev_mode(
        user: UserInfo = Depends(require_admin),
    ) -> dict[str, Any]:
        engine = _get_engine(DEFAULT_TENANT)
        engine.set_dev_mode()
        return {"mode": "dev", "n_min": 1, "dev_mode": True}

    # ------------------------------------------------------------------
    # POST /api/v1/consensus/mode/production  (control plane — not metered)
    # ------------------------------------------------------------------
    @app.post("/api/v1/consensus/mode/production", response_model=dict)
    def set_production_mode(
        user: UserInfo = Depends(require_admin),
    ) -> dict[str, Any]:
        engine = _get_engine(DEFAULT_TENANT)
        engine.set_production_mode()
        n_min = engine._effective_n_min()
        return {"mode": "production", "n_min": n_min, "dev_mode": False}

    # ------------------------------------------------------------------
    # GET /api/v1/tenants/{tenant_id}/usage
    # ------------------------------------------------------------------
    @app.get("/api/v1/tenants/{tenant_id}/usage", response_model=MeteringRecord)
    def get_tenant_usage(
        tenant_id: str,
        caller: TenantContext = Depends(meter_api_call),
    ) -> MeteringRecord:
        """Return the current-period usage for a tenant.

        Authorization: the caller must be the same tenant or an admin.
        """
        if caller.id != tenant_id and caller.user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Forbidden: cannot view usage of another tenant",
            )
        window = compute_period_window(datetime.now(timezone.utc), DEFAULT_PERIOD)
        return _meter.get_record(tenant_id, window.period_start, window.period_end)  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # GET /api/v1/tenants/{tenant_id}/usage/export
    # ------------------------------------------------------------------
    @app.get("/api/v1/tenants/{tenant_id}/usage/export")
    def export_tenant_usage(
        tenant_id: str,
        format: str = Query(default="csv", alias="format"),
        caller: TenantContext = Depends(meter_api_call),
    ) -> Response:
        """Export a tenant's current-period usage as CSV or JSON."""
        if caller.id != tenant_id and caller.user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Forbidden: cannot export usage of another tenant",
            )
        if format not in ("csv", "json"):
            raise HTTPException(status_code=400, detail="format must be 'csv' or 'json'")
        window = compute_period_window(datetime.now(timezone.utc), DEFAULT_PERIOD)
        content = _meter.export(  # type: ignore[union-attr]
            tenant_id, window.period_start, window.period_end, fmt=format
        )
        media_type = "text/csv" if format == "csv" else "application/json"
        return Response(content=content, media_type=media_type)

    return app


# ---------------------------------------------------------------------------
# Convenience: default app instance for ``uvicorn adl_lite.api:create_app``
# ---------------------------------------------------------------------------

# Read configuration from environment variables
from .config import get_api_config  # noqa: E402

_meter = get_usage_meter()
registry = get_tenant_registry()
_config = get_api_config()
app = create_app(
    cors_origins=_config["cors_origins"],
    auth_enabled=_config["auth_enabled"],
    jwt_secret=_config["jwt_secret"],
    rate_limit=_config["rate_limit"],
    api_key_tenants=_config["api_key_tenants"],
    metering_db_path=_config["metering_db_path"],
    state_base_dir=_config["state_base_dir"],
    quota_max_api_calls=_config["quota_max_api_calls"],
    quota_max_entities=_config["quota_max_entities"],
    quota_period=_config["quota_period"],
)
