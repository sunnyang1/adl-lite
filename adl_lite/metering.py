"""ADL Lite — Usage metering (per-tenant, per-period counters).

Implements the Phase-2 metering data model:

* ``UsageMeter`` — persistent per-tenant counters (``api_calls`` /
  ``registered_entities``) aggregated by ``(tenant_id, period, period_start)``
  in a SQLite ``usage_meter`` table (plus a ``usage_events`` detail table
  supporting R8 endpoint breakdown).
* ``MeteringRecord`` — the aggregated view returned to callers.
* ``PeriodWindow`` / ``compute_period_window`` — UTC period semantics
  (``daily`` and ``monthly``, default ``monthly``).
* ``export`` — CSV / JSON export of a tenant's usage for a window.
"""

from __future__ import annotations

import csv
import io
import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel

# Default aggregation period. Monthly = natural UTC month.
DEFAULT_PERIOD: Literal["daily", "monthly"] = "monthly"

# Storage used when no explicit metering db path is configured. ``:memory:``
# keeps tests / dev runs self-contained and avoids polluting the CWD.
_DEFAULT_METERING_DB = ":memory:"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS usage_meter (
    tenant_id           TEXT NOT NULL,
    period              TEXT NOT NULL,
    period_start        TEXT NOT NULL,
    period_end          TEXT NOT NULL,
    api_calls           INTEGER NOT NULL DEFAULT 0,
    registered_entities INTEGER NOT NULL DEFAULT 0,
    updated_at          TEXT NOT NULL,
    PRIMARY KEY (tenant_id, period, period_start)
);

CREATE TABLE IF NOT EXISTS usage_events (
    tenant_id    TEXT NOT NULL,
    period       TEXT NOT NULL,
    period_start TEXT NOT NULL,
    endpoint     TEXT NOT NULL,
    ts           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_usage_events_tenant ON usage_events(tenant_id, period_start);
"""


def _iso_z(dt: datetime) -> str:
    """Format a datetime as an ISO-8601 UTC string with a ``Z`` suffix."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_iso() -> str:
    return _iso_z(datetime.now(timezone.utc))


class PeriodWindow(BaseModel):
    """A UTC period window for metering."""

    period: str
    period_start: str
    period_end: str


class MeteringRecord(BaseModel):
    """Aggregated metering record for a tenant within a period."""

    tenant_id: str
    api_calls: int = 0
    registered_entities: int = 0
    period_start: str
    period_end: str
    updated_at: str


def compute_period_window(now: datetime, period: str = DEFAULT_PERIOD) -> PeriodWindow:
    """Return the UTC period window that contains ``now``.

    * ``monthly`` → natural month UTC: 1st of the month 00:00Z → 1st of the
      next month 00:00Z.
    * ``daily`` → 00:00Z → next day 00:00Z.
    """
    if period not in ("daily", "monthly"):
        raise ValueError(f"Unsupported period: {period!r}")
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    if period == "daily":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    else:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
    return PeriodWindow(
        period=period,
        period_start=_iso_z(start),
        period_end=_iso_z(end),
    )


class UsageMeter:
    """Persistent per-tenant usage meter backed by SQLite."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path if db_path is not None else _DEFAULT_METERING_DB
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        # Retry instead of immediately failing on locked tables.
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    # -- recording --------------------------------------------------------

    def record_api_call(
        self, tenant_id: str, endpoint: str | None = None, period: str = DEFAULT_PERIOD
    ) -> None:
        """Increment ``api_calls`` for the tenant's current period (R6).

        The ``period`` must match the window that ``check_quota`` queries
        (``policy.period``) so recorded usage lines up with the quota window.
        Defaults to ``DEFAULT_PERIOD`` for backward-compatible callers.
        """
        window = compute_period_window(datetime.now(timezone.utc), period)
        self._increment(tenant_id, window, api_calls_delta=1)
        if endpoint is not None:
            self._record_event(tenant_id, endpoint, window)

    def record_entity(self, tenant_id: str, period: str = DEFAULT_PERIOD) -> None:
        """Increment ``registered_entities`` after a successful register (R6).

        The ``period`` must match the quota window (``policy.period``) so the
        recorded usage aligns with the query window. Defaults to
        ``DEFAULT_PERIOD`` for backward-compatible callers.
        """
        window = compute_period_window(datetime.now(timezone.utc), period)
        self._increment(tenant_id, window, registered_entities_delta=1)

    def _increment(
        self,
        tenant_id: str,
        window: PeriodWindow,
        api_calls_delta: int = 0,
        registered_entities_delta: int = 0,
    ) -> None:
        now_iso = _now_iso()
        with self._lock:
            row = self.conn.execute(
                """
                SELECT api_calls, registered_entities
                FROM usage_meter
                WHERE tenant_id = ? AND period = ? AND period_start = ?
                """,
                (tenant_id, window.period, window.period_start),
            ).fetchone()
            if row is None:
                api_calls = api_calls_delta
                registered = registered_entities_delta
            else:
                api_calls = row["api_calls"] + api_calls_delta
                registered = row["registered_entities"] + registered_entities_delta
            self.conn.execute(
                """
                INSERT INTO usage_meter
                    (tenant_id, period, period_start, period_end,
                     api_calls, registered_entities, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, period, period_start) DO UPDATE SET
                    api_calls = excluded.api_calls,
                    registered_entities = excluded.registered_entities,
                    updated_at = excluded.updated_at,
                    period_end = excluded.period_end
                """,
                (
                    tenant_id,
                    window.period,
                    window.period_start,
                    window.period_end,
                    api_calls,
                    registered,
                    now_iso,
                ),
            )
            self.conn.commit()

    def _record_event(self, tenant_id: str, endpoint: str, window: PeriodWindow) -> None:
        """Append a per-endpoint call detail row (supports R8 breakdown)."""
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO usage_events (tenant_id, period, period_start, endpoint, ts)
                VALUES (?, ?, ?, ?, ?)
                """,
                (tenant_id, window.period, window.period_start, endpoint, _now_iso()),
            )
            self.conn.commit()

    # -- querying ---------------------------------------------------------

    def get_record(self, tenant_id: str, period_start: str, period_end: str) -> MeteringRecord:
        """Return the aggregated record for a tenant/period (0-filled if absent)."""
        with self._lock:
            row = self.conn.execute(
                """
                SELECT api_calls, registered_entities, updated_at
                FROM usage_meter
                WHERE tenant_id = ? AND period_start = ? AND period_end = ?
                """,
                (tenant_id, period_start, period_end),
            ).fetchone()
        if row is None:
            return MeteringRecord(
                tenant_id=tenant_id,
                api_calls=0,
                registered_entities=0,
                period_start=period_start,
                period_end=period_end,
                updated_at=_now_iso(),
            )
        return MeteringRecord(
            tenant_id=tenant_id,
            api_calls=row["api_calls"],
            registered_entities=row["registered_entities"],
            period_start=period_start,
            period_end=period_end,
            updated_at=row["updated_at"],
        )

    def get_endpoint_breakdown(self, tenant_id: str, period_start: str) -> dict[str, int]:
        """Return per-endpoint API call counts for a tenant/period (R8)."""
        with self._lock:
            rows = self.conn.execute(
                """
                SELECT endpoint, COUNT(*) AS cnt
                FROM usage_events
                WHERE tenant_id = ? AND period_start = ?
                GROUP BY endpoint
                """,
                (tenant_id, period_start),
            ).fetchall()
        return {row["endpoint"]: row["cnt"] for row in rows}

    def reset(self, tenant_id: str, period_start: str, period_end: str) -> None:
        """Delete the metering rows for a specific tenant/period window."""
        with self._lock:
            self.conn.execute(
                """
                DELETE FROM usage_meter
                WHERE tenant_id = ? AND period_start = ? AND period_end = ?
                """,
                (tenant_id, period_start, period_end),
            )
            self.conn.execute(
                "DELETE FROM usage_events WHERE tenant_id = ? AND period_start = ?",
                (tenant_id, period_start),
            )
            self.conn.commit()

    # -- export -----------------------------------------------------------

    def export(self, tenant_id: str, period_start: str, period_end: str, fmt: str = "csv") -> str:
        """Export a tenant's usage for the given window as CSV or JSON text.

        Args:
            tenant_id: Tenant to export.
            period_start: Inclusive lower bound (UTC ISO, ``Z`` suffix).
            period_end: Inclusive upper bound.
            fmt: ``"csv"`` or ``"json"``.

        Returns:
            A serialized string (CSV text or JSON text).
        """
        with self._lock:
            rows = self.conn.execute(
                """
                SELECT tenant_id, period, period_start, period_end,
                       api_calls, registered_entities, updated_at
                FROM usage_meter
                WHERE tenant_id = ?
                  AND period_start >= ?
                  AND period_end <= ?
                ORDER BY period_start ASC
                """,
                (tenant_id, period_start, period_end),
            ).fetchall()
        records = [
            MeteringRecord(
                tenant_id=r["tenant_id"],
                api_calls=r["api_calls"],
                registered_entities=r["registered_entities"],
                period_start=r["period_start"],
                period_end=r["period_end"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]
        if fmt == "json":
            return json.dumps([r.model_dump() for r in records], indent=2)
        if fmt == "csv":
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(
                [
                    "tenant_id",
                    "api_calls",
                    "registered_entities",
                    "period_start",
                    "period_end",
                    "updated_at",
                ]
            )
            for r in records:
                writer.writerow(
                    [
                        r.tenant_id,
                        r.api_calls,
                        r.registered_entities,
                        r.period_start,
                        r.period_end,
                        r.updated_at,
                    ]
                )
            return buf.getvalue()
        raise ValueError(f"Unsupported export format: {fmt!r}")


# ---------------------------------------------------------------------------
# Module-level singleton accessor
# ---------------------------------------------------------------------------

_meter_singletons: dict[str, UsageMeter] = {}


def get_usage_meter(db_path: str | None = None) -> UsageMeter:
    """Return a process-wide ``UsageMeter`` singleton keyed by db path.

    ``None`` (or ``":memory:"``) maps to a single in-memory singleton.
    """
    key = db_path if db_path is not None else ":memory:"
    meter = _meter_singletons.get(key)
    if meter is None:
        meter = UsageMeter(db_path=db_path)
        _meter_singletons[key] = meter
    return meter
