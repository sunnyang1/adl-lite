#!/usr/bin/bash
# Reproduce PROV-O export for all example concepts.
# Usage: bash scripts/reproduce/reproduce_prov.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

python "$SCRIPT_DIR/_reproduce_prov.py"
