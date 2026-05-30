# Research Loop Closure Checklist

Use this checklist before claiming Phase 1 + ontology pilots are paper-ready. Last verified: **2026-05-24**.

## Automated gates

- [x] **pytest green** — `pytest tests/ -v && pytest experiments/ -v`
- [x] **validate examples** — `adl-lite validate examples/*.md`
- [x] **strict ontology validate** — `adl-lite validate --strict examples/*.md` (expect 5/5 pass)
- [x] **Phase B reproducible** — `python -m experiments.run_phase_b` → `docs/experiments/summary_phase_b.json`
- [x] **RQ1 LLM judge reproducible** — `python -m experiments.rq1_llm_judge --summarize-from-template --proxy-only --no-plain-fixture` → `docs/experiments/rq1_llm_judge_summary.json`
- [x] **Ontology 2a–2c** — registry, `--strict`, `adl_ontology_query` in `tools.py` + CLI
- [x] **Human RQ1** — **cancelled** (2026-05-24); subjective RQ1 = LLM-as-judge / proxy only (`docs/experiments/HUMAN_RQ1_PROTOCOL.md` retained for audit)
- [x] **Paper numbers frozen** — see `pilot_freeze` block in `docs/experiments/RESULTS.md`

## One-command reproduction bundle

```bash
cd adl-lite
pip install -e ".[dev,experiments]"

# Core quality gates
pytest tests/ -v
pytest experiments/ -v
adl-lite validate examples/*.md
adl-lite validate --strict examples/*.md
adl-lite ontology validate --examples

# Phase B + RQ pilots
python -m experiments.run_phase_b
python -m experiments.rq1_llm_judge --summarize-from-template --proxy-only --no-plain-fixture
python -m experiments.rq1_human_eval   # scaffold only (human RQ1 cancelled)
./scripts/demo_pipeline.sh --scripted

# Optional: RQ3 ablation refresh
python -m experiments.rq3_retrieval --mode phase_b -k 10 --scorer tfidf
python -m experiments.rq3_retrieval --mode phase_b -k 10 --scorer hybrid
```

## Frozen pilot artifacts

| Artifact | Role |
|----------|------|
| `docs/experiments/summary_phase_b.json` | RQ1 rubric, RQ2 scripted, RQ3 TF-IDF, RQ4 |
| `docs/experiments/rq1_llm_judge_summary.json` | RQ1 LLM-as-judge (Wave 6b proxy) |
| `docs/experiments/rq3_ablation.json` | RQ3 scenario vs L3-only splits |
| `docs/experiments/rq1_human_summary.json` | Human RQ1 scaffold (**cancelled**; LLM-judge in `rq1_llm_judge_summary.json`) |
| `docs/paper/table2_results.md` | Paper Table 2 roll-up |

## Manual steps to fully close the loop

1. **Paper submission** — follow `docs/PAPER_SUBMISSION_PLAN.md`; freeze `pilot_freeze` after any API re-runs
2. **Sync DRAFT.md** — ensure claims match `RESULTS.md` (no human RQ1 means)
3. **Commit frozen artifacts** — user decision; include JSON summaries and doc freeze block
4. **Optional:** hybrid embeddings require `pip install -e ".[experiments-embeddings]"` for full RQ3 hybrid row reproduction

## Honest claim boundaries

- LLM proxy scores are **not** human ground truth
- Fair-plain Δ=**0** on current MiMo corpus (structure does not change L2 wording)
- RQ3 headline Δ=**+0.20** hit recall is driven by **L3-only** queries (`q21`–`q25`); scenario-only hit Δ=**0.00**
- Ontology strict mode: registry conformance on n=5 examples; no RQ outcome lift claimed
