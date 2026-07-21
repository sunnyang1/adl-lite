"""ADL Lite — Per-tenant quota enforcement (R12).

Provides a thread-safe, in-memory quota policy store and a FastAPI dependency
(``check_quota``) that gates requests by raising ``HTTPException(429)`` when
a tenant has exceeded its configured limits.

Design decisions
----------------
* **Storage**: memory-level Python dict (no SQLite) — quotas are operational
  config, not user data. Consistent with ``rate_limit`` / ``cors_origins``.
* **Default unlimited**: ``QuotaPolicy(max_api_calls=None, max_entities=None)``
  means no limits → fast path skips all metering queries → zero regression.
* **Dependency chain**: ``require_tenant → check_quota → meter_api_call → endpoint``.
  ``check_quota`` returns ``TenantContext`` (same type as ``require_tenant``)
  so endpoint signatures need zero changes.
* **Thread safety**: ``threading.Lock`` guards all ``_policies`` mutations.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel

from .tenant import TenantContext, require_tenant


class QuotaPolicy(BaseModel):
    """Per-tenant (or global default) quota policy.

    Attributes:
        max_api_calls: Maximum API calls per period. ``None`` = unlimited.
        max_entities: Maximum registered entities per period. ``None`` = unlimited.
        period: Aggregation window — ``"daily"`` or ``"monthly"``.
    """

    max_api_calls: int | None = None
    max_entities: int | None = None
    period: Literal["daily", "monthly"] = "monthly"


class QuotaConfig:
    """Thread-safe, in-memory quota policy store (process-wide singleton).

    Holds a global default policy keyed by ``"*"`` and optional per-tenant
    overrides by tenant id. ``get_policy(tenant_id)`` resolves in this order:

    1. Tenant-specific override (``_policies["<tenant_id>"]``)
    2. Global default (``_policies["*"]``)
    3. Hard-coded ``QuotaPolicy()`` — fully unlimited

    All mutations are guarded by ``threading.Lock`` for safe concurrent access.
    """

    def __init__(self) -> None:
        self._policies: dict[str, QuotaPolicy] = {}
        self._lock = threading.Lock()
        # DB path for the UsageMeter singleton used by create_app.
        # ``None`` means the default persistent per-user meter db.
        self._meter_db_path: str | None = None

    # -- query ----------------------------------------------------------

    def get_policy(self, tenant_id: str) -> QuotaPolicy:
        """Resolve the effective quota policy for *tenant_id*.

        Returns the tenant override, the global default, or an unlimited
        ``QuotaPolicy()`` if nothing is configured.
        """
        with self._lock:
            policies = dict(self._policies)
        if tenant_id in policies:
            return policies[tenant_id]
        if "*" in policies:
            return policies["*"]
        return QuotaPolicy()

    # -- mutation -------------------------------------------------------

    def set_global(self, policy: QuotaPolicy) -> None:
        """Set the global default quota policy (key ``"*"``)."""
        with self._lock:
            self._policies["*"] = policy

    def set_tenant(self, tenant_id: str, policy: QuotaPolicy) -> None:
        """Set a per-tenant quota override for *tenant_id*."""
        with self._lock:
            self._policies[tenant_id] = policy

    def reset(self) -> None:
        """Clear **all** policies (convenience for test teardown)."""
        with self._lock:
            self._policies.clear()


# ---------------------------------------------------------------------------
# Module-level singleton accessor
# ---------------------------------------------------------------------------

_quota_config: QuotaConfig | None = None


def get_quota_config() -> QuotaConfig:
    """Return the process-wide ``QuotaConfig`` singleton, creating it on first call."""
    global _quota_config
    if _quota_config is None:
        _quota_config = QuotaConfig()
    return _quota_config


# ---------------------------------------------------------------------------
# FastAPI dependency — check_quota
# ---------------------------------------------------------------------------


def check_quota(
    tenant: TenantContext = Depends(require_tenant),
) -> TenantContext:
    """FastAPI dependency: enforce quota **before** the request is metered.

    This sits between ``require_tenant`` and ``meter_api_call`` in the
    dependency chain. It returns the ``TenantContext`` unmodified so that
    downstream dependencies and endpoints receive the same object.

    **Fast path**: when both *max_api_calls* and *max_entities* are ``None``
    (the default), the function returns immediately **without** touching the
    metering store. This guarantees zero overhead and zero regression for
    deployments that do not configure quotas.

    **Comparison operator**: uses ``>=`` (current ≥ max → denied). This means
    ``max_api_calls=0`` is a valid "block everything" policy.

    Raises:
        HTTPException(429): The tenant has exceeded a configured limit. The
            ``detail`` payload includes ``error``, ``detail`` (human-readable),
            ``quota`` (limit config), ``current`` (usage snapshot), and
            ``retry_after`` (ISO-8601 period end).
    """
    # Lazy import — avoids circular import with metering.py at module load.
    from .metering import compute_period_window, get_usage_meter

    config = get_quota_config()
    policy = config.get_policy(tenant.id)

    # Fast path — no limits configured → skip metering query entirely.
    if policy.max_api_calls is None and policy.max_entities is None:
        return tenant

    # At least one dimension has a limit → fetch current usage.
    now = datetime.now(timezone.utc)
    window = compute_period_window(now, policy.period)

    # Use the same metering DB that create_app wired up (falls back to
    # the default persistent per-user db when no explicit db_path was set).
    meter = get_usage_meter(config._meter_db_path)
    record = meter.get_record(tenant.id, window.period_start, window.period_end)

    # Check api_calls dimension (strict: >= means "at or over limit").
    if policy.max_api_calls is not None and record.api_calls >= policy.max_api_calls:
        raise _quota_exceeded(
            which="api_calls",
            policy=policy,
            record=record,
            retry_after=window.period_end,
        )

    # Check entities dimension.
    if policy.max_entities is not None and record.registered_entities >= policy.max_entities:
        raise _quota_exceeded(
            which="registered_entities",
            policy=policy,
            record=record,
            retry_after=window.period_end,
        )

    return tenant


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _retry_after_seconds(retry_after: str) -> int:
    """Compute the ``Retry-After`` value (seconds) from an ISO-8601 ``Z`` string.

    Falls back to ``0`` if the timestamp cannot be parsed.
    """
    try:
        end = datetime.fromisoformat(retry_after.replace("Z", "+00:00"))
        delta = (end - datetime.now(timezone.utc)).total_seconds()
        return max(0, int(delta))
    except (ValueError, TypeError):
        return 0


def _quota_exceeded(
    which: str,
    policy: QuotaPolicy,
    record,  # MeteringRecord (lazy import avoids type annotation)
    retry_after: str,
) -> HTTPException:
    """Build a consistent 429 ``HTTPException`` for a quota violation."""
    max_val = policy.max_api_calls if which == "api_calls" else policy.max_entities
    cur_val = record.api_calls if which == "api_calls" else record.registered_entities

    return HTTPException(
        status_code=429,
        detail={
            "error": "quota_exceeded",
            "detail": f"Quota exceeded: {which} (current: {cur_val}, max: {max_val})",
            "quota": {
                "max_api_calls": policy.max_api_calls,
                "max_entities": policy.max_entities,
                "period": policy.period,
            },
            "current": {
                "api_calls": record.api_calls,
                "registered_entities": record.registered_entities,
                "period_start": record.period_start,
                "period_end": record.period_end,
            },
            "retry_after": retry_after,
        },
        # Standard 429 header (seconds) — conventional and proxy-friendly.
        headers={"Retry-After": str(_retry_after_seconds(retry_after))},
    )


# ---------------------------------------------------------------------------
# Convenience configuration function
# ---------------------------------------------------------------------------


def configure_quota(
    tenant_id: str = "*",
    max_api_calls: int | None = None,
    max_entities: int | None = None,
    period: Literal["daily", "monthly"] = "monthly",
) -> None:
    """Convenience function to set a quota policy without reaching into internals.

    Args:
        tenant_id: ``"*"`` for the global default, or a specific tenant id.
        max_api_calls: Max API calls per period. ``None`` = unlimited.
        max_entities: Max registered entities per period. ``None`` = unlimited.
        period: ``"daily"`` or ``"monthly"``.

    Examples:
        Set a global limit of 10 000 calls per month::

            configure_quota(max_api_calls=10000)

        Give tenant *acme* a higher allowance::

            configure_quota("acme", max_api_calls=50000)

        Reset to unlimited (useful between tests)::

            get_quota_config().reset()
    """
    config = get_quota_config()
    policy = QuotaPolicy(
        max_api_calls=max_api_calls,
        max_entities=max_entities,
        period=period,
    )
    if tenant_id == "*":
        config.set_global(policy)
    else:
        config.set_tenant(tenant_id, policy)
