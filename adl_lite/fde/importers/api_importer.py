"""API importer — fetches data from external REST APIs."""

from __future__ import annotations

import json
from typing import Any


class APIImporter:
    """Imports data from external REST API endpoints."""

    @staticmethod
    def import_api(
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: Any = None,
        options: dict | None = None,
    ) -> dict[str, Any]:
        """
        Call an external API and return the parsed response.

        Uses httpx for synchronous HTTP (MVP). For async usage, wrap in an async context.

        Args:
            url: The API endpoint URL.
            method: HTTP method (GET, POST, PUT, DELETE).
            headers: Optional request headers.
            body: Optional request body (dict or string).
            options: Optional dict with:
                - timeout: float (default 30.0)
                - max_retries: int (default 1)
                - extract_path: str — JSONPath-style key to extract from response (e.g. "data.items")

        Returns:
            Dict with keys: status_code, data, headers, elapsed_ms.
        """
        opts = options or {}
        timeout = opts.get("timeout", 30.0)
        max_retries = opts.get("max_retries", 1)

        try:
            import httpx

            for attempt in range(max_retries + 1):
                try:
                    with httpx.Client(timeout=timeout) as client:
                        response = client.request(
                            method=method,
                            url=url,
                            headers=headers or {},
                            json=body if isinstance(body, dict) else None,
                            content=body if isinstance(body, str) else None,
                        )
                        elapsed_ms = response.elapsed.total_seconds() * 1000
                        resp_headers = dict(response.headers)

                        # Try to parse JSON
                        try:
                            data = response.json()
                        except json.JSONDecodeError:
                            data = response.text

                        # Extract sub-path if specified
                        extract_path = opts.get("extract_path", "")
                        if extract_path and isinstance(data, dict):
                            for key in extract_path.split("."):
                                if isinstance(data, dict):
                                    data = data.get(key, data)

                        return {
                            "status_code": response.status_code,
                            "data": data,
                            "headers": resp_headers,
                            "elapsed_ms": round(elapsed_ms, 2),
                        }
                except httpx.RequestError:
                    if attempt == max_retries:
                        raise
        except ImportError:
            return {
                "status_code": 0,
                "data": {"error": "httpx is required for API import."},
                "headers": {},
                "elapsed_ms": 0,
            }

        return {"status_code": 0, "data": {}, "headers": {}, "elapsed_ms": 0}
