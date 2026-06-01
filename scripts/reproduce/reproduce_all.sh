#!/usr/bin/env bash
# reproduce_all.sh — Master artifact-reproduction orchestrator
# Usage: bash scripts/reproduce/reproduce_all.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "   ADL Lite Full Artifact Reproduction Suite"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

RESULTS=()
FAIL=0

run_sub() {
    local name="$1"
    local script="$2"
    local desc="$3"
    echo ""
    echo "────────────────────────────────────────────────────────────────────"
    echo "  [$name] $desc"
    echo "────────────────────────────────────────────────────────────────────"
    if bash "$script"; then
        RESULTS+=("$name: PASS")
        echo "  → $name: PASS"
    else
        RESULTS+=("$name: FAIL")
        echo "  → $name: FAIL"
        FAIL=1
    fi
}

# 1. Core experiments (E1–E11)
run_sub "EXP" "reproduce.sh" "Reproduce all 11 experiments (E1–E11)"

# 2. PROV-O export + SHACL validation
run_sub "PROV" "reproduce_prov.sh" "PROV-O export + SHACL shape validation"

# 3. LD-Proof signing
run_sub "SIGN" "reproduce_sign.sh" "Ed25519 LD-Proof generation and verification"

# 4. RDF-star export
run_sub "RDF*" "reproduce_rdfstar.sh" "RDF-star quoted-triple provenance export"

# 5. Adversarial integrity
run_sub "ADV" "reproduce_adversarial.sh" "Adversarial chain-integrity stress tests"

# Summary
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "   SUMMARY"
echo "═══════════════════════════════════════════════════════════════════"
for line in "${RESULTS[@]}"; do
    echo "   • $line"
done
echo ""
if [ $FAIL -eq 0 ]; then
    echo "   OVERALL: ALL PASS ✓"
    echo ""
    exit 0
else
    echo "   OVERALL: SOME FAILED ✗"
    echo ""
    exit 1
fi
