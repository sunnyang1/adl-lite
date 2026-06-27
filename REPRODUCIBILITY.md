# ADL Lite Reproducibility Package

This document provides step-by-step instructions to reproduce all experiments reported in the paper *ADL Lite: An Event-First Capability-Lifecycle Registry for LLM Agent Ecosystems*.

## Quick Start (Docker)

```bash
docker build -t adl-lite-repro .
docker run --rm adl-lite-repro
```

Expected output: a JSON summary of all experiments (E1–E30) with PASS/FAIL status.

## Manual Reproduction

### Prerequisites

- Python 3.10+
- Git
- 16 GB RAM recommended (for large-scale stress tests)
- macOS 14+ or Linux (Ubuntu 22.04+ tested)

### Installation

```bash
git clone [repo-url]
cd adl-lite
pip install -e ".[dev]"
```

### Data Pipeline

The IBM AML HI-Small dataset is automatically downloaded on first run:

```bash
python -m experiments.runner E6 --verbose
```

If automatic download fails, manually download from [IBM Data Asset eXchange](https://developer.ibm.com/exchanges/data/all/ibm-payments/) and place `HI-Small_Trans.csv` in `data/aml/`.

### Experiment Suite

| Experiment | Command | Expected Runtime | Key Output |
|-----------|---------|-----------------|------------|
| E1 (Chain integrity) | `python -m experiments.runner E1` | <1s | precision=1.0, recall=1.0 |
| E2 (Status derivation) | `python -m experiments.runner E2` | <1s | 2204/2204 correct |
| E3 (Snapshot round-trip) | `python -m experiments.runner E3` | <1s | 212/212 passed |
| E4 (Precondition enforcement) | `python -m experiments.runner E4` | <1s | 141/141 passed |
| E6 (Scalability on AML) | `python -m experiments.runner E6` | ~5s | throughput ~20,847 events/sec |
| E9 (Adversarial integrity) | `python -m experiments.runner E9` | ~2s | 53/57 detected |
| E13 (Long-chain stress) | `python -m experiments.runner E13` | ~2s | linear to 50k events |
| E14 (Collusion vulnerability) | `python -m experiments.runner E14` | ~1s | γ = 0.99 documented |
| E16 (Contention simulation) | `python -m experiments.runner E16` | ~2s | 95% rejection at k=20 |
| E20 (Template effectiveness) | `python -m experiments.runner E20` | ~1s | 100% section coverage |
| E20b (Calibration baseline) | `python -m experiments.runner E20b` | ~1s | ECE reduction 4.10× |
| E21 (100k event stress) | `python -m experiments.runner E21` | ~10s | linear scaling, <1GB |
| E24 (Proof trace) | `python -m experiments.runner E24` | ~5s | 10,000 chains: T1–T7 validated |
| E25 (Microbenchmark) | `python -m experiments.runner E25` | ~2s | precondition + confidence latency |
| E27 (1M event scale) | `python -m experiments.runner E27` | ~30s | linear throughput, zstd compression |
| E28 (10k concurrency) | `python -m experiments.runner E28` | ~20s | split-lock throughput |
| E29 (Vector recall) | `python -m experiments.runner E29` | ~5s | FAISS ANN recall ≥ 0.95 |
| E30 (LLM normalization) | `python -m experiments.runner E30` | ~3s | dry-run clusters + proposals |

### Full Suite

```bash
python -m experiments.runner all
```

Expected runtime: ~5 minutes on Apple M2, 16 GB RAM.

### Test Suite

```bash
pytest tests/ -q
```

Expected: 944 tests passed, 0 failed.

### One-Command Reproduction

For the fastest path, use the provided reproduction script:

```bash
./reproduce.sh
```

This executes all 6 steps automatically (environment → tests → experiments → benchmark → adversarial → summary). For a quick run on slower machines:

```bash
./reproduce.sh --quick
```

### Paper Compilation

```bash
cd docs/paper_ao
latexmk -pdf -interaction=nonstopmode main.tex
```

## Verification Checklist

- [ ] All experiments pass (E1–E30)
- [ ] Adversarial suite detects all 7 attack scenarios
- [ ] Invalid-chain tests catch 10/10 failure modes
- [ ] E6 throughput is within ±10% of reported 20,847 events/sec
- [ ] 944 tests pass with 0 failures
- [ ] Paper compiles without errors (51 pages)
- [ ] All referenced tables and proofs are visible in main text or supplementary

## Contact

For reproduction issues, open an issue at [GitHub repo] or email [contact].
