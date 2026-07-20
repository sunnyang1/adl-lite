#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Prefer the project virtualenv when present so that runtime deps (pyyaml,
# pydantic, ...) resolve regardless of the caller's ambient PATH.
if [[ -x "$ROOT/.venv/bin/python3" ]]; then
  exec "$ROOT/.venv/bin/python3" "$ROOT/scripts/demo_pipeline.py" "$@"
fi
exec python3 "$ROOT/scripts/demo_pipeline.py" "$@"
