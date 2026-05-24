# v0.3.0 — Phase B evaluation pack

## Highlights

- **Phase B evaluation:** TF-IDF retrieval with L3 graph boost, fair plain baseline, and `run_phase_b` summary JSON.
- **RQ3 Δ = +0.20** hit recall @10 (n=25 queries); label recall delta **+0.22** vs fair plain TF-IDF.
- **Hybrid embeddings (Phase B+):** optional `sentence-transformers` scorer; scenario subset **q01–q20** label Δ **+0.07** vs fair plain (hit Δ +0.00).
- **LLM discoverer:** MiMo/OpenAI harness, batch RQ2 analysis (`rq2_llm_batch`), smoke-tested `--llm` sim path.
- **Demo pipeline:** `./scripts/demo_pipeline.sh --scripted` — validate → store → related query in one command.

## Reproduce

```bash
cd adl-lite
pip install -e ".[dev,experiments]"
# Optional embeddings: pip install -e ".[dev,experiments-embeddings]"

pytest tests/ experiments/ -q
python -m experiments.run_phase_b
adl-lite validate examples/*.md
./scripts/demo_pipeline.sh --scripted

# Optional LLM (requires .env)
python -m experiments.run_sim --llm --max-retries 1
python -m experiments.rq2_llm_batch --dry-run --n 5
python -m experiments.rq3_retrieval --mode phase_b --scorer hybrid -k 10
```

Artifacts: `docs/experiments/summary_phase_b.json`, `docs/experiments/rq2_llm_summary.json`.

## Breaking changes

None expected for v0.2.x consumers. New optional extras: `experiments-embeddings` for hybrid RQ3.

## Merged feature work

- RQ1 human evaluation scaffold and batch discovery prompts
- RQ2 LLM batch consensus analysis
- RQ3 hybrid embedding scorer
- End-to-end demo pipeline scripts
