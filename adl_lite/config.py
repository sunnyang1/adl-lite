"""ADL Lite configuration module.

Reads configuration from environment variables with sensible defaults.
"""

import json
import os


def get_cors_origins() -> list[str] | None:
    """Read CORS allowed origins from environment variable.

    Returns:
        - None if CORS_ALLOW_ALL=true (development mode, allow all origins)
        - List of allowed origins from CORS_ORIGINS env var (production mode)
        - Default: None (allow all) for development convenience

    Environment Variables:
        CORS_ALLOW_ALL: Set to "true" to allow all origins (development)
        CORS_ORIGINS: Comma-separated list of allowed origins (production)
            Example: "https://example.com,https://app.example.com"

    Examples:
        # Development (allow all)
        CORS_ALLOW_ALL=true python -m uvicorn adl_lite.api:app

        # Production (restrict origins)
        CORS_ORIGINS=https://example.com,https://app.example.com python -m uvicorn adl_lite.api:app
    """
    # Check if CORS_ALLOW_ALL is set to "true"
    if os.getenv("CORS_ALLOW_ALL", "").lower() == "true":
        return None  # None means allow all origins

    # Read CORS_ORIGINS from environment
    cors_origins_str = os.getenv("CORS_ORIGINS", "")
    if cors_origins_str:
        # Parse comma-separated list of origins
        return [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

    # Default: None (allow all) for development convenience
    return None


def get_api_config() -> dict:
    """Read API configuration from environment variables.

    Returns:
        Dictionary with API configuration.
    """
    # API-key → tenant mapping. Accepts either a JSON object
    # (``{"key": "tenant"}``) or a ``key:tenant,key2:tenant2`` string.
    api_key_tenants_raw = os.getenv("API_KEY_TENANTS", "")
    api_key_tenants: dict[str, str] = {}
    if api_key_tenants_raw:
        try:
            parsed = json.loads(api_key_tenants_raw)
            if isinstance(parsed, dict):
                api_key_tenants = {str(k): str(v) for k, v in parsed.items()}
        except json.JSONDecodeError:
            for pair in api_key_tenants_raw.split(","):
                if ":" in pair:
                    key, tenant = pair.split(":", 1)
                    api_key_tenants[key.strip()] = tenant.strip()

    # Quota defaults (all optional — unset = unlimited, backward-compatible).
    _q_api = os.getenv("QUOTA_MAX_API_CALLS")
    _q_entities = os.getenv("QUOTA_MAX_ENTITIES")
    quota_max_api_calls: int | None = None
    quota_max_entities: int | None = None
    if _q_api and _q_api.strip():
        quota_max_api_calls = int(_q_api)
    if _q_entities and _q_entities.strip():
        quota_max_entities = int(_q_entities)

    return {
        "cors_origins": get_cors_origins(),
        "auth_enabled": os.getenv("AUTH_ENABLED", "false").lower() == "true",
        "jwt_secret": os.getenv("JWT_SECRET", "change-me"),
        "rate_limit": int(os.getenv("RATE_LIMIT", "0")),
        "api_key_tenants": api_key_tenants,
        "metering_db_path": os.getenv("METERING_DB_PATH") or None,
        "state_base_dir": os.getenv("STATE_BASE_DIR") or None,
        "quota_max_api_calls": quota_max_api_calls,
        "quota_max_entities": quota_max_entities,
        "quota_period": os.getenv("QUOTA_PERIOD", "monthly"),
    }


def get_neo4j_config() -> dict:
    """Read Neo4j connection configuration from environment variables.

    Environment Variables:
        NEO4J_URI: Neo4j connection URI (default: "bolt://localhost:7687")
        NEO4J_USER: Neo4j username (default: "neo4j")
        NEO4J_PASSWORD: Neo4j password (default: "password")
        NEO4J_DATABASE: Neo4j database name (default: "neo4j")

    Returns:
        Dictionary with Neo4j connection configuration.
    """
    return {
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("NEO4J_PASSWORD", "password"),
        "database": os.getenv("NEO4J_DATABASE", "neo4j"),
    }
