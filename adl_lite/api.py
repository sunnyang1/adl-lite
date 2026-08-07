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
    POST   /api/v1/auth/token                   — OAuth2 password-flow token issuance
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

Scope ACL (read path)
---------------------
Read endpoints enforce the document ``scope`` taxonomy
(``public`` / ``private/<org>`` / ``user/<id>`` / ``shared/<collab>``):
anonymous callers (auth disabled) read only ``public`` documents; an
authenticated caller additionally reads ``private/<their tenant>`` and
``user/<their identity>``; ``admin`` reads everything. ``/list`` filters
invisible documents; single-document reads return 404 (existence is not
leaked to unauthorized callers).
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from . import __version__
from .agents.bus import TaskQueue
from .agents.identity import (
    AgentProfile,
    AgentRegistry,
    AgentRole,
    chain_kind,
)
from .api_auth import (
    RateLimitMiddleware,
    UserInfo,
    configure_auth,
    is_auth_enabled,
    issue_token_for_api_key,
    require_admin,
)
from .config import DEFAULT_CORS_ORIGINS, get_api_config
from .consensus import ConsensusEngine
from .exceptions import ADLConsensusError
from .logging_config import get_logger
from .metering import (
    DEFAULT_PERIOD,
    MeteringRecord,
    UsageMeter,
    compute_period_window,
    get_usage_meter,
)
from .models import (
    ADLDocument,
    ADLFrontMatter,
    ADLType,
    DiscoveryStatus,
    Event,
    EventChain,
    EventType,
)
from .ontology import default_ontology
from .quota import check_quota, configure_quota, get_quota_config
from .tenant import (
    DEFAULT_TENANT,
    TenantContext,
    _safe_tenant_id,
    get_tenant_registry,
)
from .validator import ADLValidator

logger = get_logger(__name__)

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


class AgentRegisterRequest(BaseModel):
    """Request body for registering an agent identity (admin-gated, M1b)."""

    name: str = Field(..., description="Agent display name")
    role: str = Field(
        ..., description="AgentRole value: discoverer|reviewer|skeptic|merger|librarian|planner"
    )
    model: str = Field(default="", description="Preferred LLM model id")
    capabilities: list[str] = Field(
        default_factory=list, description="Capability tags (ontology vocabulary)"
    )
    scope: str = Field(default="public", description="Visibility scope")
    org_id: str | None = Field(
        default=None, description="Organization affiliation (M4; not trust in M1)"
    )
    did: str = Field(
        default="", description="Optional pre-generated DID (else derived from public_key)"
    )
    public_key: str | None = Field(
        default=None, description="Base64 Ed25519 public key (private key stays with caller)"
    )
    genesis_signature: str = Field(
        default="", description="Optional base64 genesis signature (P2-10 caller-side)"
    )
    genesis_proof: dict[str, Any] | None = Field(
        default=None, description="Optional LD-Proof object"
    )


class AgentAttestRequest(BaseModel):
    """Bind a caller-side genesis signature/proof to a registered agent (M1b)."""

    signature: str = Field(..., description="Base64 Ed25519 signature over genesis event hash")
    proof: dict[str, Any] | None = Field(default=None, description="Optional LD-Proof object")


class AgentValidateRequest(BaseModel):
    """Request body for validating an agent identity."""

    validator_did: str = Field(..., description="DID of the validating agent")
    reason: str = Field(default="", description="Validation rationale")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Validation confidence")
    signature: str = Field(default="", description="Base64 signature (required for admin=True)")


class AdminPublicKeyRequest(BaseModel):
    """Register an admin DID public key (P0-3 binding point, admin-gated)."""

    did: str = Field(..., description="Admin DID")
    public_key: str = Field(..., description="Base64 Ed25519 public key")


class AgentResponse(BaseModel):
    """Response for agent registration / validation."""

    did: str
    role: str = ""
    name: str = ""
    status: str = "pending"
    validator_count: int = 0
    scope: str = "public"


class AgentListResponse(BaseModel):
    """Paginated response for listing agents."""

    agents: list[AgentResponse]
    total: int
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

# P0-3 (M1b): admin DID -> public key (base64). This is the single binding
# point between the API-key trust (require_admin) and the DID-signature trust
# (AgentRegistry._verify_admin_signature). Persisted in the state file's top
# level under "admin_public_keys".
_admin_public_keys: dict[str, str] = {}

# M3: volatile runtime queue (per-process). Bound inside ``create_app`` to the
# app's engine via TaskRegistry. P1-6 backlog visibility reads this.
_runtime_queue: TaskQueue | None = None

# M4: global B4 diversity switch (P1-8 operational surface). Defaults to
# enabled via ADL_AGENT_DIVERSITY env (mirrors the CLI/API control plane).
_diversity_enabled: bool = os.getenv("ADL_AGENT_DIVERSITY", "1") in ("1", "true", "True")


def _load_engine(path: Path) -> ConsensusEngine:
    """Build a ``ConsensusEngine`` and hydrate it from ``path`` if present."""
    global _admin_public_keys
    engine = ConsensusEngine(ontology=default_ontology())
    if path.exists() and path.stat().st_size > 0:
        data = json.loads(path.read_text(encoding="utf-8"))
        # M1b: restore admin public-key whitelist (absent in legacy files).
        for key, value in data.get("admin_public_keys", {}).items():
            _admin_public_keys[key] = value
        for cid, events_data in data.get("chains", {}).items():
            chain = engine.chains.get(cid)
            if chain is None:
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
                # Preserve signature/proof/previous_event_id (M1a fidelity fix).
                for key in ("event_id", "hash", "_prev_hash", "previous_event_id", "signature"):
                    if key in raw:
                        setattr(event, key, raw[key])
                if "proof" in raw:
                    event.proof = raw["proof"]
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


def _ensure_runtime_queue() -> TaskQueue:
    """M3: lazily bind the volatile runtime queue to the default-tenant
    engine (reset by ``create_app``). P1-6 backlog lives here."""
    global _runtime_queue
    if _runtime_queue is None:
        from .agents.task import TaskRegistry

        _runtime_queue = TaskQueue(TaskRegistry(engine=_get_engine(DEFAULT_TENANT)))
    return _runtime_queue


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
        },
        # M1b: persist the admin public-key whitelist (P0-3 binding point).
        "admin_public_keys": dict(_admin_public_keys),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Scope ACL helpers (read path)
# ---------------------------------------------------------------------------

# Shared validator instance — validate_scope_access is stateless.
_SCOPE_VALIDATOR = ADLValidator()


def _chain_scope(chain: EventChain) -> str:
    """Derive a chain's visibility scope from its genesis event payload.

    Documents registered through the API/MCP carry their front-matter scope in
    the genesis SNAPSHOT event payload (see ``EventChain.from_parsed``). Chains
    without scope metadata (forks, engine-level genesis REGISTER events, state
    files written before the ACL existed) default to ``"public"``.
    """
    events = chain.events
    if events:
        scope = events[0].payload.get("scope")
        if isinstance(scope, str) and scope:
            return scope
    return "public"


def _requester_scopes(caller: TenantContext) -> list[str]:
    """Map the caller identity to candidate requester scopes for the ACL check.

    * auth disabled → the anonymous reader may only read ``public`` documents.
    * auth enabled  → ``public`` + ``private/<tenant>`` + ``user/<identity>``.
    """
    if not is_auth_enabled():
        return ["public"]
    scopes = ["public"]
    if caller.id and caller.id != DEFAULT_TENANT:
        scopes.append(f"private/{caller.id}")
    identity = caller.user.identity
    if identity:
        scopes.append(f"user/{identity}")
    return scopes


def _can_read(doc_scope: str, caller: TenantContext) -> bool:
    """Return True when ``caller`` may read a document with ``doc_scope``."""
    if caller.user.role == "admin":
        return True
    return any(
        _SCOPE_VALIDATOR.validate_scope_access(doc_scope, requester)
        for requester in _requester_scopes(caller)
    )


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
    jwt_secret: str | None = None,
    api_keys: set[str] | None = None,
    rate_limit: int = 0,
    cors_origins: list[str] | None = None,
    api_key_tenants: dict[str, str] | None = None,
    state_base_dir: str | None = None,
    metering_db_path: str | None = None,
    quota_max_api_calls: int | None = None,
    quota_max_entities: int | None = None,
    quota_period: Literal["daily", "monthly"] = "monthly",
    admin_username: str | None = None,
    admin_password: str | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        state_path: Path to the default-tenant consensus state JSON file.
            Defaults to ``adl_consensus.json`` in the CWD.
        auth_enabled: Whether to require authentication on endpoints.
        jwt_secret: Secret key for JWT signing/verification. **Required** when
            ``auth_enabled=True`` — there is no default secret, so a misconfigured
            deployment fails fast instead of silently using a known key.
        api_keys: Set of valid API keys for ``X-API-Key`` auth.
        rate_limit: Max requests per 60s window per client. ``0`` disables.
        cors_origins: Allowed CORS origins. ``None`` defaults to localhost
            origins (``DEFAULT_CORS_ORIGINS``); pass ``["*"]`` explicitly for
            wide-open development CORS.
        api_key_tenants: Optional API-key → tenant id mapping.
        state_base_dir: Base directory for per-tenant state files. Defaults
            to the parent of ``state_path``.
        metering_db_path: Path to the SQLite metering database. Defaults to a
            persistent per-user file (see ``adl_lite.metering``); ``":memory:"``
            selects a volatile in-memory store.
        quota_max_api_calls: Global max API calls per period. ``None`` = unlimited.
        quota_max_entities: Global max registered entities per period. ``None`` = unlimited.

    Raises:
        ValueError: ``auth_enabled=True`` without an explicit ``jwt_secret``.
    """
    global _state_path, _engine, _engine_cache, _state_base_dir, _meter, _admin_public_keys
    global _runtime_queue
    if state_path is not None:
        _state_path = Path(state_path)
    _engine = None  # Reset so it re-loads from the (possibly new) state_path
    _engine_cache.clear()
    _admin_public_keys.clear()
    _runtime_queue = None  # Re-bound lazily to the new engine (M3, volatile)
    _state_base_dir = Path(state_base_dir) if state_base_dir else None

    # Configure auth module globals. Raises ValueError when auth is enabled
    # without an explicit JWT secret (fail-fast on insecure configuration).
    configure_auth(  # type: ignore[call-arg]
        jwt_secret=jwt_secret,
        api_keys=api_keys or set(),
        auth_enabled=auth_enabled,
        api_key_tenants=api_key_tenants,
        admin_username=admin_username,
        admin_password=admin_password,
    )
    logger.info(
        "Creating ADL Lite API app: auth_enabled=%s, state_path=%s, cors_origins=%s",
        auth_enabled,
        _state_path,
        cors_origins if cors_origins is not None else DEFAULT_CORS_ORIGINS,
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

    # Add CORS middleware. The default is a localhost-only allowlist; a
    # wildcard requires an explicit opt-in (cors_origins=["*"]).
    if cors_origins is None:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=DEFAULT_CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )
    else:
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
    # POST /api/v1/auth/token — OAuth2 password-flow token issuance.
    # Backs the ``tokenUrl`` advertised by the OAuth2 security scheme.
    # ------------------------------------------------------------------
    @app.post("/api/v1/auth/token", response_model=dict)
    def issue_access_token(
        form: OAuth2PasswordRequestForm = Depends(),
    ) -> dict[str, Any]:
        """Exchange an API-key credential (password field) for a signed JWT."""
        if not is_auth_enabled():
            raise HTTPException(
                status_code=400,
                detail="Token issuance is unavailable while auth_enabled=False",
            )
        token = issue_token_for_api_key(form.username, form.password)
        if token is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {"access_token": token, "token_type": "bearer"}

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
        # P0-2: agent/task chains are not discovery capabilities — do not
        # expose them as "provisional" concepts via the discovery endpoints.
        if chain_kind(chain) != "discovery":
            raise HTTPException(status_code=404, detail=f"Not registered: {adl_id}")
        if not _can_read(_chain_scope(chain), caller):
            # 404 (not 403) so unauthorized callers cannot probe existence.
            logger.warning(
                "Scope ACL denied status read: adl_id=%s caller=%s",
                adl_id,
                caller.user.identity,
            )
            raise HTTPException(status_code=404, detail=f"Not registered: {adl_id}")
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
        chain = engine.chains.get(adl_id)
        if chain is not None and not _can_read(_chain_scope(chain), caller):
            logger.warning(
                "Scope ACL denied history read: adl_id=%s caller=%s",
                adl_id,
                caller.user.identity,
            )
            chain = None
        if chain is None:
            raise HTTPException(status_code=404, detail=f"No history for: {adl_id}")
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

        chain = engine.chains[adl_id]
        if not _can_read(_chain_scope(chain), caller):
            logger.warning(
                "Scope ACL denied verify read: adl_id=%s caller=%s",
                adl_id,
                caller.user.identity,
            )
            raise HTTPException(status_code=404, detail=f"Not registered: {adl_id}")
        ok = chain.verify_integrity()
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
        # Scope ACL: only documents visible to the caller are listed.
        # P0-2: only DISCOVERY chains surface here; agent/task chains are
        # excluded via the genesis event_type marker (chain_kind).
        caps = sorted(
            cid
            for cid, chain in engine.chains.items()
            if chain_kind(chain) == "discovery" and _can_read(_chain_scope(chain), caller)
        )
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

    # ------------------------------------------------------------------
    # Agent identity endpoints (M1b). Admin-gated control-plane endpoints use
    # require_admin (not metered); data-plane endpoints use meter_api_call.
    # ------------------------------------------------------------------

    def _make_agent_registry(tid: str = DEFAULT_TENANT) -> AgentRegistry:
        """Build an AgentRegistry for the tenant engine.

        admin_calls_allowed=True is safe here because every admin=True call
        must pass the require_admin gate on the endpoint below (P0-3).
        """
        engine = _get_engine(tid)
        return AgentRegistry(
            engine=engine,
            admin_public_keys=dict(_admin_public_keys),
            admin_calls_allowed=True,
        )

    @app.post("/api/v1/agents/register", response_model=AgentResponse)
    def api_agent_register(
        req: AgentRegisterRequest,
        user: UserInfo = Depends(require_admin),
    ) -> AgentResponse:
        """Register an agent identity (admin-gated control plane)."""
        engine = _get_engine(DEFAULT_TENANT)
        try:
            role = AgentRole(req.role)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid role: {req.role}") from exc
        registry = _make_agent_registry(DEFAULT_TENANT)
        try:
            profile = AgentProfile(
                did=req.did,
                role=role,
                name=req.name,
                model=req.model,
                capabilities=req.capabilities,
                scope=req.scope,
                org_id=req.org_id,
            )
            chain = registry.register_agent(
                profile,
                public_key=req.public_key,
                genesis_signature=req.genesis_signature,
                genesis_proof=req.genesis_proof,
            )
        except (ADLConsensusError, ValueError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        _save_engine(DEFAULT_TENANT, engine)
        return AgentResponse(
            did=profile.did,
            role=profile.role.value,
            name=profile.name,
            status=registry.agent_status(profile.did).value,
            validator_count=len(registry._agent_validators(chain)),
            scope=profile.scope,
        )

    @app.post("/api/v1/agents/{did}/attest", response_model=AgentResponse)
    def api_agent_attest(
        did: str,
        req: AgentAttestRequest,
        caller: TenantContext = Depends(meter_api_call),
    ) -> AgentResponse:
        """Bind a caller-side genesis signature/proof (P2-10: key stays with caller)."""
        engine = _get_engine(caller.id)
        if did not in engine.chains or chain_kind(engine.chains[did]) != "agent":
            raise HTTPException(status_code=404, detail=f"Unknown agent: {did}")
        chain = engine.chains[did]
        chain.events[0].signature = req.signature
        if req.proof is not None:
            chain.events[0].proof = req.proof
        _save_engine(caller.id, engine)
        registry = _make_agent_registry(caller.id)
        return AgentResponse(
            did=did,
            status=registry.agent_status(did).value,
            validator_count=len(registry._agent_validators(chain)),
        )

    @app.post("/api/v1/agents/{did}/admin-validate", response_model=AgentResponse)
    def api_agent_admin_validate(
        did: str,
        req: AgentValidateRequest,
        user: UserInfo = Depends(require_admin),
    ) -> AgentResponse:
        """Trust-root bootstrap path (P0-1): admin signs the target hash."""
        engine = _get_engine(DEFAULT_TENANT)
        registry = _make_agent_registry(DEFAULT_TENANT)
        try:
            chain = engine.chains[did]
            registry.validate_agent(
                did,
                req.validator_did,
                reason=req.reason,
                confidence=req.confidence,
                signature=req.signature,
                admin=True,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Unknown agent: {did}") from exc
        except ADLConsensusError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        _save_engine(DEFAULT_TENANT, engine)
        return AgentResponse(
            did=did,
            status=registry.agent_status(did).value,
            validator_count=len(registry._agent_validators(chain)),
        )

    @app.post("/api/v1/agents/{did}/validate", response_model=AgentResponse)
    def api_agent_validate(
        did: str,
        req: AgentValidateRequest,
        caller: TenantContext = Depends(meter_api_call),
    ) -> AgentResponse:
        """Regular agent-to-agent validation (N_min enforced)."""
        engine = _get_engine(caller.id)
        registry = _make_agent_registry(caller.id)
        try:
            chain = engine.chains[did]
            registry.validate_agent(
                did,
                req.validator_did,
                reason=req.reason,
                confidence=req.confidence,
                signature=req.signature,
                admin=False,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Unknown agent: {did}") from exc
        except ADLConsensusError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        _save_engine(caller.id, engine)
        return AgentResponse(
            did=did,
            status=registry.agent_status(did).value,
            validator_count=len(registry._agent_validators(chain)),
        )

    @app.post("/api/v1/agents/{did}/deprecate", response_model=AgentResponse)
    def api_agent_deprecate(
        did: str,
        req: dict[str, str],
        user: UserInfo = Depends(require_admin),
    ) -> AgentResponse:
        """Decommission an agent (admin-gated control plane)."""
        engine = _get_engine(DEFAULT_TENANT)
        registry = _make_agent_registry(DEFAULT_TENANT)
        actor = req.get("actor", DEFAULT_TENANT)
        try:
            registry.deprecate_agent(did, actor, req.get("reason", ""))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Unknown agent: {did}") from exc
        except ADLConsensusError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        _save_engine(DEFAULT_TENANT, engine)
        return AgentResponse(did=did, status=registry.agent_status(did).value)

    @app.get("/api/v1/agents/{did}", response_model=AgentResponse)
    def api_agent_get(
        did: str,
        caller: TenantContext = Depends(meter_api_call),
    ) -> AgentResponse:
        engine = _get_engine(caller.id)
        chain = engine.chains.get(did)
        if chain is None or chain_kind(chain) != "agent":
            raise HTTPException(status_code=404, detail=f"Unknown agent: {did}")
        if not _can_read(_chain_scope(chain), caller):
            raise HTTPException(status_code=404, detail=f"Unknown agent: {did}")
        registry = _make_agent_registry(caller.id)
        profile = registry.resolve_profile(chain)
        return AgentResponse(
            did=did,
            role=profile.role.value,
            name=profile.name,
            status=registry.agent_status(did).value,
            validator_count=len(registry._agent_validators(chain)),
            scope=profile.scope,
        )

    @app.get("/api/v1/agents", response_model=AgentListResponse)
    def api_agent_list(
        offset: int = Query(default=_DEFAULT_OFFSET, ge=0),
        limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
        scope: str | None = Query(default=None),
        caller: TenantContext = Depends(meter_api_call),
    ) -> AgentListResponse:
        engine = _get_engine(caller.id)
        registry = _make_agent_registry(caller.id)
        profiles = registry.list_agents(scope=scope)
        # Scope ACL: only agents readable by the caller.
        visible = [p for p in profiles if _can_read(_chain_scope(engine.chains[p.did]), caller)]
        total = len(visible)
        slice_items = visible[offset : offset + limit]
        return AgentListResponse(
            agents=[
                AgentResponse(
                    did=p.did,
                    role=p.role.value,
                    name=p.name,
                    status=registry.agent_status(p.did).value,
                    validator_count=len(registry._agent_validators(engine.chains[p.did])),
                    scope=p.scope,
                )
                for p in slice_items
            ],
            total=total,
            offset=offset,
            limit=limit,
        )

    @app.get("/api/v1/agents/{did}/history", response_model=HistoryResponse)
    def api_agent_history(
        did: str,
        caller: TenantContext = Depends(meter_api_call),
    ) -> HistoryResponse:
        engine = _get_engine(caller.id)
        chain = engine.chains.get(did)
        if chain is None or chain_kind(chain) != "agent":
            raise HTTPException(status_code=404, detail=f"Unknown agent: {did}")
        if not _can_read(_chain_scope(chain), caller):
            raise HTTPException(status_code=404, detail=f"Unknown agent: {did}")
        return HistoryResponse(adl_id=did, events=engine.get_history(did))

    @app.post("/api/v1/admin/public-key", response_model=dict)
    def api_admin_public_key(
        req: AdminPublicKeyRequest,
        user: UserInfo = Depends(require_admin),
    ) -> dict[str, Any]:
        """Register an admin DID public key (P0-3: API-key ↔ DID-signature binding)."""
        _admin_public_keys[req.did] = req.public_key
        engine = _get_engine(DEFAULT_TENANT)
        _save_engine(DEFAULT_TENANT, engine)
        return {"registered": req.did, "admin_public_keys": len(_admin_public_keys)}

    # ------------------------------------------------------------------
    # Task lifecycle endpoints (M2). Data-plane (metered). The chain guards
    # transitions; lease checks live in TaskQueue (M3 runtime).
    # ------------------------------------------------------------------

    def _task_registry_for(tid: str):
        from .agents.task import TaskRegistry

        return _get_engine(tid), TaskRegistry(engine=_get_engine(tid))

    @app.post("/api/v1/tasks/create", response_model=dict)
    def api_task_create(
        req: dict[str, Any],
        caller: TenantContext = Depends(meter_api_call),
    ) -> dict[str, Any]:
        engine, registry = _task_registry_for(caller.id)
        task = registry.create_task(
            objective=req["objective"],
            required_capabilities=req.get("capabilities") or req.get("required_capabilities") or [],
            created_by=req.get("created_by", "planner"),
            priority=req.get("priority", 0),
            scope=req.get("scope", "public"),
            tenant=caller.id,
        )
        _save_engine(caller.id, engine)
        return {"task_id": task.task_id, "status": task.status.value}

    @app.post("/api/v1/tasks/{task_id}/claim", response_model=dict)
    def api_task_claim(
        task_id: str,
        req: dict[str, str],
        caller: TenantContext = Depends(meter_api_call),
    ) -> dict[str, Any]:
        engine, registry = _task_registry_for(caller.id)
        try:
            ev = registry.claim(task_id, req["agent_did"])
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ADLConsensusError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        _save_engine(caller.id, engine)
        return {"task_id": task_id, "event_type": ev.event_type.value}

    @app.post("/api/v1/tasks/{task_id}/submit", response_model=dict)
    def api_task_submit(
        task_id: str,
        req: dict[str, Any],
        caller: TenantContext = Depends(meter_api_call),
    ) -> dict[str, Any]:
        engine, registry = _task_registry_for(caller.id)
        try:
            ev = registry.submit(
                task_id,
                req["agent_did"],
                req["result_ref"],
                summary=req.get("summary", ""),
                confidence=req.get("confidence", 0.5),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ADLConsensusError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        _save_engine(caller.id, engine)
        return {
            "task_id": task_id,
            "event_type": ev.event_type.value,
            "result_ref": req["result_ref"],
        }

    @app.post("/api/v1/tasks/{task_id}/validate", response_model=dict)
    def api_task_validate(
        task_id: str,
        req: dict[str, Any],
        caller: TenantContext = Depends(meter_api_call),
    ) -> dict[str, Any]:
        engine, registry = _task_registry_for(caller.id)
        try:
            ev = registry.validate_result(
                task_id,
                req["validator_did"],
                req["accepted"],
                confidence=req.get("confidence", 0.8),
                critique=req.get("critique", ""),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ADLConsensusError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        _save_engine(caller.id, engine)
        return {"task_id": task_id, "event_type": ev.event_type.value}

    @app.post("/api/v1/tasks/{task_id}/close", response_model=dict)
    def api_task_close(
        task_id: str,
        req: dict[str, str],
        caller: TenantContext = Depends(meter_api_call),
    ) -> dict[str, Any]:
        engine, registry = _task_registry_for(caller.id)
        try:
            ev = registry.close(task_id, req["actor"], req["outcome"], reason=req.get("reason", ""))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ADLConsensusError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        _save_engine(caller.id, engine)
        return {"task_id": task_id, "event_type": ev.event_type.value}

    @app.get("/api/v1/tasks/{task_id}", response_model=dict)
    def api_task_get(
        task_id: str,
        caller: TenantContext = Depends(meter_api_call),
    ) -> dict[str, Any]:
        engine = _get_engine(caller.id)
        if task_id not in engine.chains:
            raise HTTPException(status_code=404, detail=f"Unknown task: {task_id}")
        _engine, registry = _task_registry_for(caller.id)
        t = registry.get_task(task_id)
        return {
            "task_id": task_id,
            "status": t.status.value,
            "objective": t.objective,
            "result_ref": t.result_ref,
            "required_capabilities": t.required_capabilities,
        }

    @app.get("/api/v1/tasks", response_model=dict)
    def api_task_list(
        status: str | None = Query(default=None),
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=50, ge=1, le=_MAX_LIMIT),
        caller: TenantContext = Depends(meter_api_call),
    ) -> dict[str, Any]:
        from .agents.task import TaskStatus

        _engine, registry = _task_registry_for(caller.id)
        st = TaskStatus(status) if status else None
        tasks = [
            {
                "task_id": t.task_id,
                "status": t.status.value,
                "objective": t.objective,
                "priority": t.priority,
                "result_ref": t.result_ref,
            }
            for t in registry.list_tasks(status=st, tenant=caller.id)
        ]
        total = len(tasks)
        return {
            "tasks": tasks[offset : offset + limit],
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    # ------------------------------------------------------------------
    # M3: runtime control plane
    # ------------------------------------------------------------------

    @app.get("/api/v1/runtime/status", response_model=dict)
    def api_runtime_status(
        caller: TenantContext = Depends(meter_api_call),
    ) -> dict[str, Any]:
        """P1-6: un-consumed task backlog + per-agent run state (volatile)."""
        queue = _ensure_runtime_queue()
        return {
            "pending": queue.pending_count(),
            "queue_depth": queue.queue_depth(),
            "agents": {},  # run_forever loops are managed by CLI/MCP in M3
        }

    @app.post("/api/v1/checkpoints/{task_id}/approve", response_model=dict)
    def api_checkpoint_approve(
        task_id: str,
        user: UserInfo = Depends(require_admin),
    ) -> dict[str, Any]:
        """Resolve a pending human checkpoint (single-process deployment,
        P1-4). Body-free; ``approve`` resolves the in-process Future."""
        from .agents.runtime import approve_checkpoint

        ok = approve_checkpoint(task_id)
        if not ok:
            raise HTTPException(status_code=404, detail=f"No pending checkpoint for {task_id}")
        return {"task_id": task_id, "approved": True}

    # ------------------------------------------------------------------
    # M4: reputation + trust control plane
    # ------------------------------------------------------------------

    @app.get("/api/v1/agents/{did}/reputation", response_model=dict)
    def api_agent_reputation(
        did: str,
        caller: TenantContext = Depends(meter_api_call),
    ) -> dict[str, Any]:
        """Weak-signal reputation for an agent (P1-7: ranking only)."""
        from .agents.trust import Reputation

        tid = caller.id
        engine = _get_engine(tid)
        chain = engine.chains.get(did)
        if chain is None or chain_kind(chain) != "agent":
            raise HTTPException(status_code=404, detail=f"Not registered: {did}")
        if not _can_read(_chain_scope(chain), caller):
            raise HTTPException(status_code=404, detail=f"Not registered: {did}")
        registry = AgentRegistry(engine=engine)
        rep = Reputation(engine, registry)
        s = rep.score(did)
        return {
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

    @app.get("/api/v1/admin/trust/diversity", response_model=dict)
    def api_trust_diversity_get(
        user: UserInfo = Depends(require_admin),
    ) -> dict[str, Any]:
        """M4/P1-8: view the global B4 diversity switch."""
        return {"diversity_enabled": _diversity_enabled}

    @app.post("/api/v1/admin/trust/diversity", response_model=dict)
    def api_trust_diversity_set(
        enabled: bool,
        user: UserInfo = Depends(require_admin),
    ) -> dict[str, Any]:
        """M4/P1-8: toggle the global B4 diversity switch."""
        global _diversity_enabled
        _diversity_enabled = enabled
        return {"diversity_enabled": _diversity_enabled}

    # ------------------------------------------------------------------
    # M5: meta — single source of truth for the task state machine and the
    # role tool whitelists (read-only, data-plane metered).
    # ------------------------------------------------------------------

    @app.get("/api/v1/meta/task-transitions", response_model=dict)
    def api_meta_task_transitions(
        caller: TenantContext = Depends(meter_api_call),
    ) -> dict[str, Any]:
        """Serialize the task state machine (``_TASK_TRANSITIONS``) so
        dashboards and validators share one source of truth.

        Keys and values are the ``TaskStatus`` string forms; target sets are
        emitted in declaration order for a deterministic response.
        """
        from .agents.task import _TASK_TRANSITIONS, TaskStatus

        order = {status: i for i, status in enumerate(TaskStatus)}
        transitions = {
            src.value: [dst.value for dst in sorted(targets, key=order.__getitem__)]
            for src, targets in _TASK_TRANSITIONS.items()
        }
        return {"transitions": transitions}

    @app.get("/api/v1/meta/roles", response_model=dict)
    def api_meta_roles(
        caller: TenantContext = Depends(meter_api_call),
    ) -> dict[str, Any]:
        """Serialize the runtime role specs (tool whitelists + validation
        policy + system prompt) so enforcement and documentation never
        diverge from ``agents.roles.ROLE_SPECS``."""
        from .agents.roles import ROLE_SPECS

        roles = {
            spec.role.value: {
                "allowed_tools": list(spec.allowed_tools),
                "validation_policy": spec.validation_policy,
                "system_prompt": spec.system_prompt,
            }
            for spec in ROLE_SPECS.values()
        }
        return {"roles": roles}

    return app


# ---------------------------------------------------------------------------
# Convenience: default app instance for ``uvicorn adl_lite.api:create_app``
# ---------------------------------------------------------------------------

# Read configuration from environment variables
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
    admin_username=_config["admin_username"],
    admin_password=_config["admin_password"],
)
