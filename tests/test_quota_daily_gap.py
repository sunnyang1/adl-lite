"""Independent QA test (Yan): daily-period quota enforcement gap — R12.

Documented SOURCE BUG
---------------------
``UsageMeter.record_api_call`` / ``record_entity`` always record under the
hardcoded ``DEFAULT_PERIOD`` ("monthly"), while ``check_quota`` queries the
meter using ``policy.period``. For a ``"daily"`` quota, the query window
(day) never matches the stored row (month), so ``get_record`` returns a
zero-filled record and the 429 is never raised.

This test asserts the correct (per-design) behavior and currently FAILS,
pinning the bug so the engineer's fix can be verified.

Design reference: docs/phase2_r12_quota_design.md §共享知识 (3) "配额周期与计量周期对齐".
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from adl_lite.api import _quota_config, create_app
from adl_lite.quota import configure_quota

TEST_SECRET = "test-jwt-secret-daily-gap"
TEST_API_KEYS = {"key-acme"}


@pytest.fixture
def daily_app() -> Iterator[TestClient]:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        state_path = f.name
    with tempfile.TemporaryDirectory() as td:
        meter_db = str(Path(td) / "meter.db")
        app = create_app(
            state_path=state_path,
            auth_enabled=True,
            jwt_secret=TEST_SECRET,
            api_keys=TEST_API_KEYS,
            api_key_tenants={"key-acme": "acme"},
            metering_db_path=meter_db,
        )
        yield TestClient(app)
    Path(state_path).unlink(missing_ok=True)


def _key() -> dict:
    return {"X-API-Key": "key-acme"}


class TestDailyQuotaEnforcement:
    """A daily quota of 3 must block the 4th call (just like monthly)."""

    @pytest.fixture(autouse=True)
    def _setup(self, daily_app: TestClient) -> None:
        _quota_config.reset()
        configure_quota(max_api_calls=3, period="daily")

    def test_first_three_calls_succeed(self, daily_app: TestClient) -> None:
        h = _key()
        for i in range(3):
            r = daily_app.get("/api/v1/consensus/list", headers=h)
            assert r.status_code == 200, f"call {i + 1} expected 200, got {r.status_code}"

    def test_fourth_call_returns_429(self, daily_app: TestClient) -> None:
        h = _key()
        for _ in range(3):
            daily_app.get("/api/v1/consensus/list", headers=h)
        r = daily_app.get("/api/v1/consensus/list", headers=h)
        assert r.status_code == 429, f"expected 429 (daily quota), got {r.status_code}"
