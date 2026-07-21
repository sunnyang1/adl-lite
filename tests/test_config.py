"""
Tests for adl_lite.config — environment-variable configuration contract.

Covers defaults, env-var parsing, type conversion, and error handling for
get_cors_origins / get_api_config / get_neo4j_config.
"""

from __future__ import annotations

import pytest

from adl_lite.config import (
    DEFAULT_CORS_ORIGINS,
    get_api_config,
    get_cors_origins,
    get_neo4j_config,
)

_ENV_VARS = [
    "CORS_ALLOW_ALL",
    "CORS_ORIGINS",
    "AUTH_ENABLED",
    "JWT_SECRET",
    "RATE_LIMIT",
    "API_KEY_TENANTS",
    "METERING_DB_PATH",
    "STATE_BASE_DIR",
    "QUOTA_MAX_API_CALLS",
    "QUOTA_MAX_ENTITIES",
    "QUOTA_PERIOD",
    "NEO4J_URI",
    "NEO4J_USER",
    "NEO4J_PASSWORD",
    "NEO4J_DATABASE",
]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch):
    """Isolate every test from ambient configuration env vars."""
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)


# ---------------------------------------------------------------------------
# get_cors_origins
# ---------------------------------------------------------------------------


class TestGetCorsOrigins:
    def test_default_localhost_only(self):
        origins = get_cors_origins()
        assert origins == DEFAULT_CORS_ORIGINS
        assert "*" not in origins
        assert all("localhost" in o or "127.0.0.1" in o for o in origins)

    def test_default_returns_a_copy(self):
        """Mutating the returned list must not corrupt the module default."""
        origins = get_cors_origins()
        origins.append("https://evil.example")
        assert get_cors_origins() == DEFAULT_CORS_ORIGINS

    def test_allow_all_returns_none(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CORS_ALLOW_ALL", "true")
        assert get_cors_origins() is None

    def test_allow_all_case_insensitive(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CORS_ALLOW_ALL", "TRUE")
        assert get_cors_origins() is None

    def test_allow_all_requires_exact_true(self, monkeypatch: pytest.MonkeyPatch):
        """Only the literal 'true' opts in — '1'/'yes' do not."""
        monkeypatch.setenv("CORS_ALLOW_ALL", "1")
        assert get_cors_origins() == DEFAULT_CORS_ORIGINS

    def test_custom_origins_parsed(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CORS_ORIGINS", "https://a.example, https://b.example ,")
        assert get_cors_origins() == ["https://a.example", "https://b.example"]

    def test_allow_all_takes_precedence(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CORS_ALLOW_ALL", "true")
        monkeypatch.setenv("CORS_ORIGINS", "https://a.example")
        assert get_cors_origins() is None


# ---------------------------------------------------------------------------
# get_api_config
# ---------------------------------------------------------------------------


class TestGetApiConfig:
    def test_defaults(self):
        cfg = get_api_config()
        assert cfg["cors_origins"] == DEFAULT_CORS_ORIGINS
        assert cfg["auth_enabled"] is False
        assert cfg["jwt_secret"] is None  # no default secret
        assert cfg["rate_limit"] == 0
        assert cfg["api_key_tenants"] == {}
        assert cfg["metering_db_path"] is None
        assert cfg["state_base_dir"] is None
        assert cfg["quota_max_api_calls"] is None
        assert cfg["quota_max_entities"] is None
        assert cfg["quota_period"] == "monthly"

    def test_auth_and_secret(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("AUTH_ENABLED", "true")
        monkeypatch.setenv("JWT_SECRET", "s3cret")
        cfg = get_api_config()
        assert cfg["auth_enabled"] is True
        assert cfg["jwt_secret"] == "s3cret"

    def test_rate_limit_int_conversion(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("RATE_LIMIT", "50")
        assert get_api_config()["rate_limit"] == 50

    def test_rate_limit_invalid_raises(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("RATE_LIMIT", "not-a-number")
        with pytest.raises(ValueError):
            get_api_config()

    def test_api_key_tenants_json_form(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("API_KEY_TENANTS", '{"key-1": "tenant-a", "key-2": "tenant-b"}')
        assert get_api_config()["api_key_tenants"] == {
            "key-1": "tenant-a",
            "key-2": "tenant-b",
        }

    def test_api_key_tenants_pair_form(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("API_KEY_TENANTS", "key-1:tenant-a, key-2:tenant-b")
        assert get_api_config()["api_key_tenants"] == {
            "key-1": "tenant-a",
            "key-2": "tenant-b",
        }

    def test_api_key_tenants_garbage_ignored(self, monkeypatch: pytest.MonkeyPatch):
        """Non-JSON input without 'key:tenant' pairs yields an empty mapping."""
        monkeypatch.setenv("API_KEY_TENANTS", "not-json-no-colons")
        assert get_api_config()["api_key_tenants"] == {}

    def test_quota_int_conversion(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("QUOTA_MAX_API_CALLS", "1000")
        monkeypatch.setenv("QUOTA_MAX_ENTITIES", "500")
        monkeypatch.setenv("QUOTA_PERIOD", "daily")
        cfg = get_api_config()
        assert cfg["quota_max_api_calls"] == 1000
        assert cfg["quota_max_entities"] == 500
        assert cfg["quota_period"] == "daily"

    def test_quota_blank_means_unlimited(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("QUOTA_MAX_API_CALLS", "   ")
        assert get_api_config()["quota_max_api_calls"] is None

    def test_quota_invalid_raises(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("QUOTA_MAX_ENTITIES", "many")
        with pytest.raises(ValueError):
            get_api_config()

    def test_optional_paths(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("METERING_DB_PATH", "/tmp/metering.db")
        monkeypatch.setenv("STATE_BASE_DIR", "/var/adl")
        cfg = get_api_config()
        assert cfg["metering_db_path"] == "/tmp/metering.db"
        assert cfg["state_base_dir"] == "/var/adl"


# ---------------------------------------------------------------------------
# get_neo4j_config
# ---------------------------------------------------------------------------


class TestGetNeo4jConfig:
    def test_defaults(self):
        cfg = get_neo4j_config()
        assert cfg == {
            "uri": "bolt://localhost:7687",
            "user": "neo4j",
            "password": "password",
            "database": "neo4j",
        }

    def test_overrides(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("NEO4J_URI", "bolt://db.internal:7687")
        monkeypatch.setenv("NEO4J_USER", "adl")
        monkeypatch.setenv("NEO4J_PASSWORD", "pw")
        monkeypatch.setenv("NEO4J_DATABASE", "adldb")
        cfg = get_neo4j_config()
        assert cfg["uri"] == "bolt://db.internal:7687"
        assert cfg["user"] == "adl"
        assert cfg["password"] == "pw"
        assert cfg["database"] == "adldb"
