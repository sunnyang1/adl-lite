# Experiment Reproduction Guide

Reproduce frozen pilot metrics (`docs/experiments/RESULTS.md`, `pilot_freeze` 2026-05-24).

## Setup

```bash
cd adl-lite
pip install -e ".[dev,experiments]"
# Optional hybrid RQ3: pip install -e ".[dev,experiments-embeddings]"
```

## No API keys required

```bash
pytest tests/ -v
pytest experiments/ -v
adl-lite validate examples/*.md
adl-lite validate --strict examples/*.md
python -m experiments.run_phase_b
python -m experiments.rq3_retrieval --mode phase_b -k 10 --scorer tfidf
python -m experiments.rq1_llm_judge --summarize-from-template --proxy-only --no-plain-fixture
./scripts/demo_pipeline.sh --scripted
```

## API keys (optional MiMo / judge refresh)

```bash
cp .env.example .env   # fill MIMO_API_KEY, etc.
set -a && source .env && set +a

python -m experiments.rq1_batch_discover --target-complete 1
python -m experiments.rq2_llm_batch --n 10
```

Deterministic smoke without provider keys:

```bash
python -m experiments.rq1_batch_discover --backend-proxy --regenerate-all
# Optional: --sync-template to update data/eval/human_rq1_template.json
```

## Expected artifacts

| File | Command |
|------|---------|
| `docs/experiments/summary_phase_b.json` | `run_phase_b` |
| `docs/experiments/rq3_ablation.json` | `rq3_retrieval` (tfidf + hybrid) |
| `docs/experiments/rq1_llm_judge_summary.json` | `rq1_llm_judge --proxy-only` |
| `docs/experiments/rq1_human_summary.json` | `rq1_human_eval` (status: cancelled) |
| `docs/paper/table2_results.md` | derived from JSON above |

Full checklist: `docs/experiments/RESEARCH_LOOP_CHECKLIST.md`.
