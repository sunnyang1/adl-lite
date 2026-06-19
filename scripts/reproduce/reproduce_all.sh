#!/usr/bin/env bash
# reproduce_all.sh — Full reproduction suite: install, test, benchmark, experiment, report
# Usage: bash scripts/reproduce/reproduce_all.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

REPORT_DIR="$PROJECT_ROOT/docs/reports"
mkdir -p "$REPORT_DIR"
REPORT_FILE="$REPORT_DIR/reproduce_all_report.txt"

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

{
    echo "ADL Lite Reproduction Report"
    echo "Generated: $TIMESTAMP"
    echo "============================================================"
    echo ""
} > "$REPORT_FILE"

PASS=0
FAIL=0

record() {
    local name="$1"
    local status="$2"
    local detail="$3"
    if [ "$status" -eq 0 ]; then
        echo "  → $name: PASS"
        echo "$name: PASS${detail:+ ($detail)}" >> "$REPORT_FILE"
        ((PASS++)) || true
    else
        echo "  → $name: FAIL"
        echo "$name: FAIL${detail:+ ($detail)}" >> "$REPORT_FILE"
        ((FAIL++)) || true
    fi
}

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "   ADL Lite Full Reproduction Suite"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# 1. Install dependencies
echo "[1/5] Installing dependencies..."
if pip install -e ".[dev]" > >(tee -a "$REPORT_FILE") 2>&1; then
    record "Install" 0
else
    record "Install" 1
fi
echo ""

# 2. Run all tests
echo "[2/5] Running tests..."
if pytest tests/ -v --cov=adl_lite --cov-report=term-missing > >(tee -a "$REPORT_FILE") 2>&1; then
    record "Tests" 0
else
    record "Tests" 1
fi
echo ""

# 3. Run all benchmarks
echo "[3/5] Running benchmarks..."
if python experiments/benchmarks/throughput.py > >(tee -a "$REPORT_FILE") 2>&1; then
    record "Benchmarks" 0
else
    record "Benchmarks" 1
fi
echo ""

# 4. Run all experiments
echo "[4/5] Running experiments..."
if python -m experiments.runner all > >(tee -a "$REPORT_FILE") 2>&1; then
    record "Experiments" 0
else
    record "Experiments" 1
fi
echo ""

# 5. Finalize report
echo "[5/5] Generating report..."
{
    echo ""
    echo "============================================================"
    echo "SUMMARY"
    echo "============================================================"
    echo "Passed: $PASS"
    echo "Failed: $FAIL"
    echo ""
    if [ "$FAIL" -eq 0 ]; then
        echo "OVERALL: ALL PASS"
    else
        echo "OVERALL: SOME FAILED"
    fi
    echo ""
    echo "Full report: $REPORT_FILE"
} >> "$REPORT_FILE"

cat "$REPORT_FILE"

if [ "$FAIL" -eq 0 ]; then
    exit 0
else
    exit 1
fi
