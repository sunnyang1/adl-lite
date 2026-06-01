#!/usr/bin/bash
# Reproduce RDF-star export + SPARQL queries.
# Usage: bash scripts/reproduce/reproduce_rdfstar.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

python "$SCRIPT_DIR/_reproduce_rdfstar.py"
