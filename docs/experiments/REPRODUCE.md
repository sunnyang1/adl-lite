# Experiment Reproduction Guide

Use this checklist to reproduce ADL Lite experiment outputs from a clean checkout.

## Setup

```bash
cd adl-lite
pip install -e ".[dev,experiments]"
```

## Reproduction Commands

```bash
# 1) Core tests (must pass)
pytest tests/ experiments/ -q

# 2) Phase B summary artifacts
python -m experiments.run_phase_b

# 3) Scripted end-to-end pipeline
./scripts/demo_pipeline.sh --scripted

# 4) RQ1 LLM-as-judge sweep
python -m experiments.rq1_llm_judge --all

# 5) Validate ADL examples
adl-lite validate examples/*.md
```

## Notes on LLM judge runs

- `python -m experiments.rq1_llm_judge --all` needs configured provider API access.
- If API access is unavailable, use the committed proxy summary:
  - `docs/experiments/rq1_llm_judge_summary.json`

## Expected outputs

- Passing test suites under `tests/` and `experiments/`
- `docs/experiments/summary_phase_b.json`
- `docs/experiments/rq1_llm_judge_summary.json`

## Quick verification order

1. `pytest tests/ experiments/ -q`
2. `python -m experiments.run_phase_b`
3. `./scripts/demo_pipeline.sh --scripted`
4. `python -m experiments.rq1_llm_judge --all` (or inspect proxy JSON)
5. `adl-lite validate examples/*.md`
