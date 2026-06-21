"""Multi-tenant namespace management for FDE Platform."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class TenantContext:
    """Holds the identity and configuration for a single tenant."""

    tenant_id: str
    name: str
    config: dict = field(default_factory=dict)


class TenantManager:
    """Manages tenant namespaces and data isolation.

    Provides in-memory tenant registry suitable for MVP single-node deployment.
    In V1.0 this will be backed by PostgreSQL with per-tenant schemas.

    Usage::

        tm = TenantManager()
        ctx = tm.create_tenant("acme-corp", {"domain": "logistics"})
        tm.get_tenant(ctx.tenant_id)
    """

    def __init__(self) -> None:
        self._tenants: dict[str, TenantContext] = {}

    def create_tenant(self, name: str, config: dict | None = None) -> TenantContext:
        """Register a new tenant and return its context.

        Args:
            name: Human-readable tenant name.
            config: Optional tenant-specific configuration dictionary.

        Returns:
            A new TenantContext with a unique tenant_id.
        """
        tenant_id: str = uuid4().hex
        ctx = TenantContext(
            tenant_id=tenant_id,
            name=name,
            config=config if config is not None else {},
        )
        self._tenants[tenant_id] = ctx
        return ctx

    def get_tenant(self, tenant_id: str) -> TenantContext | None:
        """Look up a tenant by its ID.

        Args:
            tenant_id: The unique tenant identifier.

        Returns:
            TenantContext if found, None otherwise.
        """
        return self._tenants.get(tenant_id)

    def list_tenants(self) -> list[TenantContext]:
        """Return all registered tenants."""
        return list(self._tenants.values())

    def delete_tenant(self, tenant_id: str) -> bool:
        """Remove a tenant from the registry.

        Args:
            tenant_id: The unique tenant identifier.

        Returns:
            True if the tenant was found and removed, False otherwise.
        """
        if tenant_id in self._tenants:
            del self._tenants[tenant_id]
            return True
        return False
