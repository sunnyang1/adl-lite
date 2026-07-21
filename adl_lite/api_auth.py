"""ADL Lite — Authentication and rate-limiting for the REST API.

Provides JWT-based and API-key-based authentication, admin role gating,
and a sliding-window rate limiter. All components are designed as FastAPI
dependencies or Starlette middleware so they can be toggled on/off via the
``create_app()`` factory.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import BaseModel

from .logging_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# JWT configuration defaults
# ---------------------------------------------------------------------------

_ALGORITHM = "HS256"
_DEFAULT_EXPIRY_HOURS = 24


# ---------------------------------------------------------------------------
# User identity model
# ---------------------------------------------------------------------------


class UserInfo(BaseModel):
    """Authenticated user identity returned by ``require_auth``."""

    identity: str
    role: str = "user"
    tenant_id: str | None = None  # Resolved tenant (JWT claim / API-key mapping)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def create_access_token(
    data: dict,
    secret: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token.

    Args:
        data: Payload dict — must include ``sub`` (subject) and ``role``.
        secret: Signing secret key.
        expires_delta: Optional custom expiry. Defaults to 24 hours.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=_DEFAULT_EXPIRY_HOURS)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, secret, algorithm=_ALGORITHM)  # type: ignore[no-any-return]


def get_current_user(token: str, secret: str) -> dict:
    """Decode and validate a JWT token, returning the payload dict.

    Args:
        token: JWT string.
        secret: Signing secret used to verify the signature.

    Returns:
        Decoded payload dict with ``sub`` and ``role`` fields.

    Raises:
        ExpiredSignatureError: Token has expired.
        JWTError: Token is invalid (bad signature, malformed, etc.).
    """
    payload = jwt.decode(token, secret, algorithms=[_ALGORITHM])
    return dict(payload)  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# OAuth2 scheme (for OpenAPI docs)
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


# ---------------------------------------------------------------------------
# Auth dependency factory
# ---------------------------------------------------------------------------

# Module-level overrides — set by ``create_app()`` at startup.
# No default JWT secret: when auth is enabled a secret MUST be supplied
# explicitly (see ``configure_auth``), otherwise token signing/verification
# would silently rely on a publicly known key.
_jwt_secret: str | None = None
_api_keys: set[str] = set()
_auth_enabled: bool = True

# API-key → tenant id mapping (injected via ``configure_auth``). Used by
# ``resolve_api_key_tenant`` to attribute a tenant to key-authenticated calls.
_api_key_tenants: dict[str, str] = {}


def is_auth_enabled() -> bool:
    """Return whether authentication is currently enabled."""
    return _auth_enabled


def resolve_api_key_tenant(key: str) -> str | None:
    """Resolve the tenant id mapped to an API key, if any.

    Returns the tenant id for ``key`` when present in the ``api_key_tenants``
    mapping, otherwise ``None``. This is deliberately decoupled from
    ``verify_api_key`` (which only validates the key identity).
    """
    return _api_key_tenants.get(key)


def configure_auth(
    jwt_secret: str | None,
    api_keys: set[str],
    auth_enabled: bool,
    api_key_tenants: dict[str, str] | None = None,
) -> None:
    """Set module-level auth configuration (called by ``create_app()``).

    Args:
        jwt_secret: JWT signing secret. Required when ``auth_enabled=True``;
            there is intentionally no default so deployments cannot silently
            fall back to a publicly known key.
        api_keys: Set of valid API keys.
        auth_enabled: Whether authentication is required.
        api_key_tenants: Optional mapping of API key → tenant id, used to
            attribute a tenant to key-authenticated requests.

    Raises:
        ValueError: ``auth_enabled=True`` without an explicit ``jwt_secret``.
    """
    if auth_enabled and not jwt_secret:
        raise ValueError(
            "JWT secret is required when auth_enabled=True. "
            "Set the JWT_SECRET environment variable or pass jwt_secret=... "
            "to create_app()/configure_auth(). Refusing to start with a "
            "default, publicly known secret."
        )
    global _jwt_secret, _api_keys, _auth_enabled, _api_key_tenants
    _jwt_secret = jwt_secret
    _api_keys = api_keys
    _auth_enabled = auth_enabled
    _api_key_tenants = dict(api_key_tenants) if api_key_tenants else {}
    logger.info(
        "Auth configured: auth_enabled=%s, api_keys=%d, tenant_mappings=%d",
        auth_enabled,
        len(api_keys),
        len(_api_key_tenants),
    )


def require_auth(
    token: str | None = Depends(oauth2_scheme),
    api_key: str | None = Header(None, alias="X-API-Key"),
) -> UserInfo:
    """FastAPI dependency that validates JWT OR API key.

    Either a valid ``Authorization: Bearer <jwt>`` header or a valid
    ``X-API-Key`` header is sufficient. When ``auth_enabled=False`` a
    default user is returned (backward-compatibility mode).

    Raises:
        HTTPException(401): No auth provided, or both JWT and API key invalid.
    """
    if not _auth_enabled:
        # Backward-compatibility mode: unauthenticated callers get a
        # read-only identity. Admin-only endpoints (mode switches) reject
        # this identity via ``require_admin``.
        return UserInfo(identity="anonymous", role="reader")

    # Try JWT first
    if token:
        if _jwt_secret is None:
            # Should be unreachable: configure_auth() refuses auth-enabled
            # startup without a secret. Defensive guard for direct module use.
            logger.error("JWT presented but no JWT secret is configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="JWT secret is not configured on the server",
            )
        try:
            payload = get_current_user(token, _jwt_secret)
            return UserInfo(
                identity=payload.get("sub", "unknown"),
                role=payload.get("role", "user"),
                tenant_id=payload.get("tenant_id"),
            )
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            ) from None
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from None

    # Fallback to API key
    if api_key:
        identity = verify_api_key(api_key, _api_keys)
        if identity is not None:
            return UserInfo(
                identity=identity,
                role="user",
                tenant_id=resolve_api_key_tenant(api_key),
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        ) from None

    # No auth at all
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    ) from None


def require_admin(
    user: UserInfo = Depends(require_auth),
) -> UserInfo:
    """FastAPI dependency that requires admin role.

    Raises:
        HTTPException(403): User does not have admin role.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        ) from None
    return user


# ---------------------------------------------------------------------------
# API key verification
# ---------------------------------------------------------------------------


def verify_api_key(key: str, valid_keys: set[str]) -> str | None:
    """Verify an API key against the configured set.

    Args:
        key: The key string from the ``X-API-Key`` header.
        valid_keys: Set of accepted API keys.

    Returns:
        The key identity (the key string itself) if valid, ``None`` otherwise.
    """
    if key in valid_keys:
        return key
    return None


def issue_token_for_api_key(username: str, password: str) -> str | None:
    """Issue a signed JWT for the OAuth2 password flow.

    The password flow is backed by the configured API keys: ``password`` must
    be one of the keys passed to ``configure_auth``. The issued token carries
    ``sub=username``, ``role="user"``, and — when the key has a tenant
    mapping — the mapped ``tenant_id`` claim.

    Returns:
        Encoded JWT string, or ``None`` when the credential is invalid or
        token issuance is not properly configured (auth disabled / no secret).
    """
    if not _auth_enabled or _jwt_secret is None:
        return None
    if verify_api_key(password, _api_keys) is None:
        logger.warning("Token issuance rejected: invalid credential for username=%r", username)
        return None
    claims: dict[str, Any] = {"sub": username, "role": "user"}
    tenant_id = resolve_api_key_tenant(password)
    if tenant_id is not None:
        claims["tenant_id"] = tenant_id
    logger.info("Issued access token for username=%r (tenant=%s)", username, tenant_id)
    return create_access_token(claims, secret=_jwt_secret)


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


class RateLimiter:
    """Sliding-window rate limiter.

    Args:
        max_requests: Maximum requests per ``window_seconds`` per client.
        window_seconds: Duration of the sliding window in seconds.
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}

    def _clean_window(self, client_id: str) -> None:
        """Remove timestamps outside the current window."""
        now = time.time()
        cutoff = now - self.window_seconds
        if client_id in self._requests:
            self._requests[client_id] = [t for t in self._requests[client_id] if t > cutoff]

    def check(self, client_id: str) -> bool:
        """Check whether a request from ``client_id`` is within the limit.

        Returns:
            ``True`` if the request is allowed, ``False`` if over limit.
        """
        if self.max_requests <= 0:
            return True  # rate limiting disabled

        self._clean_window(client_id)
        timestamps = self._requests.get(client_id, [])
        if len(timestamps) >= self.max_requests:
            return False

        now = time.time()
        timestamps.append(now)
        self._requests[client_id] = timestamps
        return True

    def get_retry_after(self, client_id: str) -> int:
        """Return the number of seconds until the oldest request in the window expires.

        Returns:
            Seconds until the client can make another request. Returns 0 if
            the client is not currently rate-limited.
        """
        if client_id not in self._requests:
            return 0
        self._clean_window(client_id)
        timestamps = self._requests[client_id]
        if not timestamps:
            return 0
        oldest = timestamps[0]
        now = time.time()
        remaining = int(self.window_seconds - (now - oldest))
        return max(remaining, 1)


# ---------------------------------------------------------------------------
# Rate-limit middleware
# ---------------------------------------------------------------------------


class RateLimitMiddleware:
    """Starlette-style ASGI middleware for per-client rate limiting.

    Client identity is determined by the ``X-API-Key`` header if present,
    otherwise by the client IP address.

    Args:
        app: The ASGI application to wrap.
        rate_limit: Maximum requests per window. ``0`` disables rate limiting.
        window_seconds: Duration of the sliding window.
    """

    def __init__(
        self,
        app: Callable[..., Any],
        rate_limit: int = 60,
        window_seconds: int = 60,
    ) -> None:
        self.app = app
        self.rate_limit = rate_limit
        self._limiter = RateLimiter(max_requests=rate_limit, window_seconds=window_seconds)

    async def __call__(
        self, scope: dict[str, Any], receive: Callable[..., Any], send: Callable[..., Any]
    ) -> None:
        """ASGI middleware entry point."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if self.rate_limit <= 0:
            await self.app(scope, receive, send)
            return

        # Determine client identity
        headers = dict(scope.get("headers", []))
        api_key_bytes = headers.get(b"x-api-key")
        if api_key_bytes:
            client_id = api_key_bytes.decode("utf-8")
        else:
            # Use client IP from scope
            client = scope.get("client")
            client_id = client[0] if client else "unknown"

        if not self._limiter.check(client_id):
            # Over limit — send 429 response
            retry_after = self._limiter.get_retry_after(client_id)
            response_headers = [
                [b"content-type", b"application/json"],
                [b"retry-after", str(retry_after).encode("utf-8")],
            ]
            body = (
                b'{"detail":"Rate limit exceeded","Retry-After":' + str(retry_after).encode() + b"}"
            )
            await send(
                {
                    "type": "http.response.start",
                    "status": 429,
                    "headers": response_headers,
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": body,
                }
            )
            return

        await self.app(scope, receive, send)
