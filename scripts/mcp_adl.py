#!/usr/bin/env python3
"""
Minimal MCP-style ADL tool server (stdio JSON-RPC lite).

Exposes: adl_parse, adl_validate, adl_query_related

Usage:
    echo '{"tool":"adl_validate","args":{"path":"examples/capital_reflux_trap.md"}}' | python scripts/mcp_adl.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from adl_lite.tools import adl_parse, adl_query_related, adl_validate  # noqa: E402

TOOLS = {
    "adl_parse": lambda a: adl_parse(a["path"]),
    "adl_validate": lambda a: adl_validate(a["path"]),
    "adl_query_related": lambda a: adl_query_related(
        a["adl_id"], a.get("db", ":memory:"), depth=a.get("depth", 1)
    ),
}


def handle_request(payload: dict) -> dict:
    tool = payload.get("tool")
    args = payload.get("args", {})
    if tool not in TOOLS:
        return {"ok": False, "error": f"unknown tool: {tool}"}
    try:
        result = TOOLS[tool](args)
        return {"ok": True, "result": result}
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        return {"ok": False, "error": str(exc)}


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req = json.loads(line)
        resp = handle_request(req)
        print(json.dumps(resp), flush=True)


if __name__ == "__main__":
    main()
