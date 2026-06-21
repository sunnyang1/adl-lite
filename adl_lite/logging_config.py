"""Structured logging configuration for ADL Lite.

Provides a default logger that can be configured via environment variables:
    ADL_LOG_LEVEL  — logging level (DEBUG, INFO, WARNING, ERROR; default: INFO)
    ADL_LOG_FORMAT — output format (json, text; default: text)
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Default logger
# ---------------------------------------------------------------------------


def _get_level() -> int:
    raw = os.environ.get("ADL_LOG_LEVEL", "INFO").upper()
    return getattr(logging, raw, logging.INFO)


def _make_formatter(fmt: str) -> logging.Formatter:
    if fmt == "json":
        return _JsonFormatter()
    return logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


class _JsonFormatter(logging.Formatter):
    """Minimal JSON-line formatter — no extra dependencies."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            payload["error"] = str(record.exc_info[1])
        return json.dumps(payload, default=str)


_logger = logging.getLogger("adl_lite")
_logger.setLevel(_get_level())

if not _logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_make_formatter(os.environ.get("ADL_LOG_FORMAT", "text")))
    _logger.addHandler(handler)
    _logger.propagate = False  # Don't duplicate to root logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a child logger under the adl_lite namespace.

    Args:
        name: Sub-logger name (e.g. "parser", "consensus"). If None, returns root adl_lite logger.

    Example:
        >>> logger = get_logger("parser")
        >>> logger.info("Parsing document %s", doc_path)
    """
    if name:
        return logging.getLogger(f"adl_lite.{name}")
    return _logger
