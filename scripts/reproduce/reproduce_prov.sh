#!/usr/bin/env bash
# reproduce_prov.sh — Generate PROV-O Turtle files for all example concepts and validate with rdflib.
# Usage: bash scripts/reproduce/reproduce_prov.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

python "$SCRIPT_DIR/_reproduce_prov.py"
