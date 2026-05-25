"""
Subprocess wrapper for lark-cli (https://github.com/larksuite/cli).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any


class LarkCliNotFoundError(RuntimeError):
    """lark-cli binary is not on PATH."""


class LarkCliError(RuntimeError):
    """lark-cli returned an error or non-zero exit code."""

    def __init__(self, message: str, *, payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.payload = payload or {}


def find_lark_cli(explicit: str | None = None) -> str:
    if explicit:
        path = explicit
        if not os.path.isfile(path) or not os.access(path, os.X_OK):
            raise LarkCliNotFoundError(f"lark-cli not executable: {explicit}")
        return path
    path = shutil.which("lark-cli")
    if not path:
        raise LarkCliNotFoundError(
            "lark-cli not found on PATH. Install: npx @larksuite/cli@latest install "
            "or build from https://github.com/larksuite/cli"
        )
    return path


def run_lark_cli(
    args: list[str],
    *,
    lark_cli: str | None = None,
    timeout: float = 120.0,
) -> dict[str, Any]:
    """
    Run lark-cli with JSON on stdout. Raises LarkCliError on failure.
    """
    binary = find_lark_cli(lark_cli)
    proc = subprocess.run(
        [binary, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()

    payload: dict[str, Any] | None = None
    if stdout:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            payload = None

    if proc.returncode != 0:
        hint = ""
        if payload and isinstance(payload.get("error"), dict):
            err = payload["error"]
            hint = str(err.get("hint") or err.get("message") or "")
        msg = hint or stderr or stdout or f"lark-cli exited {proc.returncode}"
        raise LarkCliError(msg, payload=payload or {"stdout": stdout, "stderr": stderr})

    if payload is None:
        if not stdout:
            return {"ok": True}
        raise LarkCliError(
            f"lark-cli returned non-JSON output: {stdout[:500]}",
            payload={"stdout": stdout, "stderr": stderr},
        )

    if payload.get("ok") is False:
        err = payload.get("error") or {}
        msg = err.get("message") if isinstance(err, dict) else str(err)
        hint = err.get("hint", "") if isinstance(err, dict) else ""
        raise LarkCliError(
            f"{msg}" + (f" — {hint}" if hint else ""),
            payload=payload,
        )

    return payload


def auth_status(*, lark_cli: str | None = None) -> dict[str, Any]:
    return run_lark_cli(["auth", "status"], lark_cli=lark_cli)
