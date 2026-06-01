#!/usr/bin/bash
# Reproduce all 11 experiments and generate results table.
# Usage: bash scripts/reproduce/reproduce.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "========================================"
echo "ADL Lite Experiment Reproduction"
echo "========================================"

python "$SCRIPT_DIR/_reproduce_experiments.py"
