"""ADL Lite configuration module.

Reads configuration from environment variables with sensible defaults.
"""

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
    return {
        "cors_origins": get_cors_origins(),
        "auth_enabled": os.getenv("AUTH_ENABLED", "false").lower() == "true",
        "jwt_secret": os.getenv("JWT_SECRET", "change-me"),
        "rate_limit": int(os.getenv("RATE_LIMIT", "0")),
    }
