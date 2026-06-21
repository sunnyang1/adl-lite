#!/usr/bin/env bash
# ADL Lite — One-Click Reproduction Script
#
# Usage:
#   ./reproduce.sh              # Run all core experiments
#   ./reproduce.sh quick       # Run only fast experiments (E1-E4, E24)
#   ./reproduce.sh docker       # Build and run in Docker
#
# Output: docs/experiments/experiment_results.json

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/docs/experiments"
mkdir -p "${OUTPUT_DIR}"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

print_banner() {
    echo ""
    echo "=========================================="
    echo "  ADL Lite Experiment Reproduction"
    echo "=========================================="
    echo ""
}

check_environment() {
    log_info "Checking environment..."

    if ! command -v python3 &>/dev/null; then
        log_error "python3 not found. Please install Python 3.10+."
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    log_info "Python version: ${PYTHON_VERSION}"

    if ! python3 -c "import adl_lite" 2>/dev/null; then
        log_warn "adl_lite not installed. Installing in editable mode..."
        pip install -e "${SCRIPT_DIR}[dev,experiments]"
    fi

    # Check for optional dependencies
    if python3 -c "import rdflib" 2>/dev/null; then
        log_info "rdflib: OK"
    else
        log_warn "rdflib not found. E12/E19 benchmark comparisons may be limited."
    fi

    if python3 -c "import pyshacl" 2>/dev/null; then
        log_info "pyshacl: OK"
    else
        log_warn "pyshacl not found. SHACL validation will be skipped."
    fi
}

run_quick() {
    print_banner
    check_environment

    log_info "Running quick experiments (E1-E4, E24)..."
    python3 -m experiments.runner E1
    python3 -m experiments.runner E2
    python3 -m experiments.runner E3
    python3 -m experiments.runner E4
    python3 -m experiments.runner E24

    log_info "Quick experiments complete."
    log_info "Results: ${OUTPUT_DIR}/experiment_results.json"
}

run_all() {
    print_banner
    check_environment

    log_info "Running ALL experiments (this may take 5-15 minutes)..."
    python3 -m experiments.runner all

    log_info "All experiments complete."
    log_info "Results: ${OUTPUT_DIR}/experiment_results.json"
}

run_docker() {
    print_banner

    if ! command -v docker &>/dev/null; then
        log_error "Docker not found. Please install Docker."
        exit 1
    fi

    log_info "Building Docker image..."
    docker build -t adl-lite-repro "${SCRIPT_DIR}"

    log_info "Running experiments in Docker..."
    docker run --rm \
        -v "${OUTPUT_DIR}:/app/docs/experiments" \
        adl-lite-repro

    log_info "Docker experiments complete."
    log_info "Results: ${OUTPUT_DIR}/experiment_results.json"
}

run_tests() {
    print_banner
    check_environment

    log_info "Running pytest suite..."
    python3 -m pytest tests/ -v --tb=short

    log_info "Tests complete."
}

print_help() {
    cat <<EOF
ADL Lite Reproduction Script

Usage:
  ./reproduce.sh [command]

Commands:
  quick    Run fast experiments (E1-E4, E24) — ~30 seconds
  all      Run all experiments — ~5-15 minutes
  docker   Build and run in Docker container
  test     Run pytest suite only
  help     Show this message

Examples:
  ./reproduce.sh quick
  ./reproduce.sh all
  ./reproduce.sh docker

Output:
  Experiment results are written to:
    docs/experiments/experiment_results.json
  Proof trace checker results:
    docs/experiments/proof_trace_checker_results.json
EOF
}

# Main entry
COMMAND="${1:-all}"

case "${COMMAND}" in
    quick)
        run_quick
        ;;
    all)
        run_all
        ;;
    docker)
        run_docker
        ;;
    test|tests)
        run_tests
        ;;
    help|--help|-h)
        print_help
        ;;
    *)
        log_error "Unknown command: ${COMMAND}"
        print_help
        exit 1
        ;;
esac
