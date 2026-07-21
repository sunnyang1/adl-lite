"""Unit tests for adl_lite.metering — UsageMeter, period windows, export."""

from __future__ import annotations

from datetime import datetime, timezone

from adl_lite.metering import (
    DEFAULT_PERIOD,
    PeriodWindow,
    UsageMeter,
    compute_period_window,
    get_usage_meter,
)


def test_default_period_is_monthly() -> None:
    assert DEFAULT_PERIOD == "monthly"


def test_period_window_monthly() -> None:
    now = datetime(2025, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    w = compute_period_window(now, "monthly")
    assert isinstance(w, PeriodWindow)
    assert w.period == "monthly"
    assert w.period_start == "2025-07-01T00:00:00Z"
    assert w.period_end == "2025-08-01T00:00:00Z"


def test_period_window_monthly_december_rollover() -> None:
    now = datetime(2025, 12, 25, tzinfo=timezone.utc)
    w = compute_period_window(now, "monthly")
    assert w.period_start == "2025-12-01T00:00:00Z"
    assert w.period_end == "2026-01-01T00:00:00Z"


def test_period_window_daily() -> None:
    now = datetime(2025, 7, 15, 13, 30, 0, tzinfo=timezone.utc)
    w = compute_period_window(now, "daily")
    assert w.period == "daily"
    assert w.period_start == "2025-07-15T00:00:00Z"
    assert w.period_end == "2025-07-16T00:00:00Z"


def test_compute_period_window_rejects_unknown() -> None:
    import pytest

    with pytest.raises(ValueError):
        compute_period_window(datetime(2025, 7, 15, tzinfo=timezone.utc), "weekly")


def test_record_api_call_and_entity_memory() -> None:
    meter = UsageMeter(":memory:")
    now = datetime.now(timezone.utc)
    w = compute_period_window(now, "monthly")
    meter.record_api_call("t1")
    meter.record_api_call("t1")
    meter.record_entity("t1")
    rec = meter.get_record("t1", w.period_start, w.period_end)
    assert rec.api_calls == 2
    assert rec.registered_entities == 1
    assert rec.tenant_id == "t1"


def test_cross_tenant_isolation() -> None:
    meter = UsageMeter(":memory:")
    now = datetime.now(timezone.utc)
    w = compute_period_window(now, "monthly")
    meter.record_api_call("a")
    meter.record_entity("a")
    rec_a = meter.get_record("a", w.period_start, w.period_end)
    rec_b = meter.get_record("b", w.period_start, w.period_end)
    assert rec_a.api_calls == 1
    assert rec_a.registered_entities == 1
    assert rec_b.api_calls == 0
    assert rec_b.registered_entities == 0


def test_endpoint_breakdown_recorded() -> None:
    meter = UsageMeter(":memory:")
    now = datetime.now(timezone.utc)
    w = compute_period_window(now, "monthly")
    meter.record_api_call("t1", endpoint="/api/v1/consensus/register")
    meter.record_api_call("t1", endpoint="/api/v1/consensus/register")
    meter.record_api_call("t1", endpoint="/api/v1/consensus/list")
    breakdown = meter.get_endpoint_breakdown("t1", w.period_start)
    assert breakdown.get("/api/v1/consensus/register") == 2
    assert breakdown.get("/api/v1/consensus/list") == 1


def test_cross_period_reset() -> None:
    meter = UsageMeter(":memory:")
    now = datetime.now(timezone.utc)
    w = compute_period_window(now, "monthly")
    meter.record_api_call("t1")
    meter.record_entity("t1")
    rec = meter.get_record("t1", w.period_start, w.period_end)
    assert rec.api_calls == 1
    # Reset the current period → counters return to zero.
    meter.reset("t1", w.period_start, w.period_end)
    rec2 = meter.get_record("t1", w.period_start, w.period_end)
    assert rec2.api_calls == 0
    assert rec2.registered_entities == 0
    # A different period window is independent.
    other = compute_period_window(datetime(2025, 6, 10, tzinfo=timezone.utc), "monthly")
    rec_other = meter.get_record("t1", other.period_start, other.period_end)
    assert rec_other.api_calls == 0


def test_persistence_file_path(tmp_path) -> None:
    db = str(tmp_path / "meter.db")
    meter = UsageMeter(db)
    now = datetime.now(timezone.utc)
    w = compute_period_window(now, "monthly")
    meter.record_api_call("t1")
    meter.record_entity("t1")
    # A fresh instance on the same file observes the persisted counters.
    meter2 = UsageMeter(db)
    rec = meter2.get_record("t1", w.period_start, w.period_end)
    assert rec.api_calls == 1
    assert rec.registered_entities == 1


def test_export_csv() -> None:
    meter = UsageMeter(":memory:")
    now = datetime.now(timezone.utc)
    w = compute_period_window(now, "monthly")
    meter.record_api_call("t1")
    meter.record_entity("t1")
    csv_text = meter.export("t1", w.period_start, w.period_end, fmt="csv")
    assert "tenant_id,api_calls,registered_entities" in csv_text
    assert "t1,1,1" in csv_text


def test_export_json() -> None:
    import json

    meter = UsageMeter(":memory:")
    now = datetime.now(timezone.utc)
    w = compute_period_window(now, "monthly")
    meter.record_api_call("t1")
    meter.record_entity("t1")
    json_text = meter.export("t1", w.period_start, w.period_end, fmt="json")
    data = json.loads(json_text)
    assert isinstance(data, list)
    assert data[0]["tenant_id"] == "t1"
    assert data[0]["api_calls"] == 1
    assert data[0]["registered_entities"] == 1


def test_export_invalid_format() -> None:
    import pytest

    meter = UsageMeter(":memory:")
    now = datetime.now(timezone.utc)
    w = compute_period_window(now, "monthly")
    with pytest.raises(ValueError):
        meter.export("t1", w.period_start, w.period_end, fmt="xml")


def test_get_usage_meter_singleton() -> None:
    a = get_usage_meter(":memory:")
    b = get_usage_meter(":memory:")
    assert a is b


# ---------------------------------------------------------------------------
# P1-2: persistent default storage
# ---------------------------------------------------------------------------


def test_default_metering_db_is_persistent_file() -> None:
    """The default storage is a per-user file, not volatile in-memory."""
    from adl_lite.metering import _DEFAULT_METERING_DB

    assert _DEFAULT_METERING_DB != ":memory:"
    assert _DEFAULT_METERING_DB.endswith("metering.db")


def test_usage_meter_default_path_round_trip(tmp_path, monkeypatch) -> None:
    """With no explicit path, UsageMeter persists under the user data dir."""
    import adl_lite.metering as metering_module

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(metering_module, "_DEFAULT_METERING_DB", str(fake_home / "m.db"))
    monkeypatch.setattr(
        metering_module, "_default_metering_db_path", lambda: str(fake_home / "m.db")
    )

    meter = UsageMeter()  # no explicit path → default persistent file
    assert meter.db_path == str(fake_home / "m.db")
    now = datetime.now(timezone.utc)
    w = compute_period_window(now, "monthly")
    meter.record_api_call("tenant-x")
    meter.conn.close()
    # A fresh instance on the default path sees the counter (survives "restart").
    meter2 = UsageMeter()
    assert meter2.get_record("tenant-x", w.period_start, w.period_end).api_calls == 1


def test_in_memory_mode_logs_warning(caplog) -> None:
    """Explicit ':memory:' is allowed but must warn about non-persistence."""
    import logging

    # The adl_lite root logger sets propagate=False, so attach caplog's
    # handler to the metering logger directly.
    metering_logger = logging.getLogger("adl_lite.metering")
    metering_logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.WARNING, logger="adl_lite.metering"):
            UsageMeter(":memory:")
    finally:
        metering_logger.removeHandler(caplog.handler)
    assert any("in-memory" in rec.message for rec in caplog.records)


def test_get_usage_meter_default_key_is_persistent(tmp_path, monkeypatch) -> None:
    """get_usage_meter(None) keys its singleton on the default file path."""
    import adl_lite.metering as metering_module

    fake_db = str(tmp_path / "default.db")
    monkeypatch.setattr(metering_module, "_DEFAULT_METERING_DB", fake_db)
    monkeypatch.setattr(metering_module, "_default_metering_db_path", lambda: fake_db)
    metering_module._meter_singletons.pop(fake_db, None)
    try:
        meter = get_usage_meter()
        assert meter.db_path == fake_db
        assert metering_module._meter_singletons[fake_db] is meter
    finally:
        metering_module._meter_singletons.pop(fake_db, None)
