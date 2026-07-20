"""ADL Lite — Multi-tenant context resolution and per-tenant engine registry.

This module introduces the tenant abstraction used by the Phase-2
multi-tenant slice:

* ``TenantContext`` — the resolved tenant for a single request.
* ``require_tenant`` — a FastAPI dependency that wraps ``require_auth`` and
  returns a ``TenantContext``.
* ``TenantRegistry`` — a thin, lazy registry that delegates per-tenant
  ``ConsensusEngine`` persistence/caching to ``adl_lite.api`` (so that the
  module-level ``_engine`` / ``_engine_cache`` remain the single source of
  truth, protecting the legacy lazy-load tests).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from fastapi import Depends
from pydantic import BaseModel

from . import api_auth
from .api_auth import UserInfo, require_auth

if TYPE_CHECKING:
    from .consensus import ConsensusEngine

# Shared tenant id used when authentication is disabled (single-tenant mode).
DEFAULT_TENANT = "default"

# Characters allowed in a sanitized tenant id used as a filename component.
_SAFE_TENANT_RE = re.compile(r"[^A-Za-z0-9_.-]")


def _safe_tenant_id(tid: str) -> str:
    """Sanitize a tenant id into a filesystem-safe component.

    Only ``[A-Za-z0-9_.-]`` are kept; everything else becomes ``_``. An
    empty result falls back to ``"default"``.
    """
    if not tid:
        return DEFAULT_TENANT
    safe = _SAFE_TENANT_RE.sub("_", tid)
    return safe or DEFAULT_TENANT


class TenantContext(BaseModel):
    """Resolved tenant context for a single request."""

    id: str
    user: UserInfo


def require_tenant(user: UserInfo = Depends(require_auth)) -> TenantContext:
    """Resolve the tenant for the current request.

    Resolution rules (see design doc §7.3):
      * ``auth_enabled=False`` → always the ``default`` tenant (backward
        compat — single-tenant behavior is unchanged).
      * ``auth_enabled=True`` with an explicit ``tenant_id`` (JWT claim or
        API-key mapping) → use that value.
      * ``auth_enabled=True`` without an explicit tenant → derive the tenant
        from the authenticated ``user.identity`` (zero regression: every
        authenticated request still gets a non-empty tenant).
    """
    # When auth is disabled there is no identity to derive a tenant from, so
    # we always fall back to the shared default tenant.
    if not api_auth.is_auth_enabled():  # type: ignore[attr-defined]
        return TenantContext(id=DEFAULT_TENANT, user=user)

    if user.tenant_id:  # type: ignore[attr-defined]
        return TenantContext(id=user.tenant_id, user=user)  # type: ignore[attr-defined]

    # Authenticated but no explicit tenant claim → derive from identity.
    return TenantContext(id=user.identity or DEFAULT_TENANT, user=user)


class TenantRegistry:
    """Lazy per-tenant ``ConsensusEngine`` registry.

    All engine state lives in ``adl_lite.api`` (the module-level ``_engine``
    for the default tenant and ``_engine_cache`` for every other tenant). This
    class is a thin delegation layer so callers can reason about tenants
    without reaching into ``api`` internals. The lazy ``import adl_lite.api``
    inside each method avoids a circular import at module load time.
    """

    def _get_engine(self, tid: str = DEFAULT_TENANT) -> ConsensusEngine:
        import adl_lite.api as api

        return api._get_engine(tid)

    def _save_engine(
        self, tid: str = DEFAULT_TENANT, engine: ConsensusEngine | None = None
    ) -> None:
        import adl_lite.api as api

        api._save_engine(tid, engine)

    def reset(self) -> None:
        """Clear all cached engines (used between tests / on reload)."""
        import adl_lite.api as api

        api._engine = None
        api._engine_cache.clear()


_registry: TenantRegistry | None = None


def get_tenant_registry() -> TenantRegistry:
    """Return the process-wide ``TenantRegistry`` singleton."""
    global _registry
    if _registry is None:
        _registry = TenantRegistry()
    return _registry
