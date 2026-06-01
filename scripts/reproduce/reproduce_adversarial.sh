#!/usr/bin/env bash
# reproduce_adversarial.sh — Reproduce adversarial integrity tests
set -euo pipefail

cd "$(cd "$(dirname "$0")" && pwd)" || exit 1

echo "========================================"
echo "Adversarial Integrity Test Reproduction"
echo "========================================"

cd ../.. || exit 1
pytest tests/test_adversarial_integrity.py -v --tb=short

echo ""
echo "OVERALL: PASS"
