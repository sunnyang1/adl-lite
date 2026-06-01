#!/usr/bin/bash
# Reproduce SHACL validation over exported PROV-O Turtle.
# Usage: bash scripts/reproduce/reproduce_shacl.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

python "$SCRIPT_DIR/_reproduce_shacl.py"
