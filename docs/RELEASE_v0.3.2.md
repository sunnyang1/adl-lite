# v0.3.2 — plain-LLM baseline, RQ3 ablation, release sync

## Highlights

- **Live plain-LLM baseline (MiMo):** refreshed `python -m experiments.rq1_plain_discover --target-complete 15` run confirms **n=15** plain outputs wired on the RQ1 template.
- **RQ3 Table 1 ablation landed:** scenario-only (`q01-q20`) vs L3-only (`q21-q25`) split now documented with concentrated L3 lift in retrieval deltas.
- **Paper draft updates included:** introduction/evaluation drafts plus release-facing experiment narrative updates are synced.
- **RQ1 judge artifacts refreshed honestly:** summary/template/docs now annotate that Wave 5a live proxy re-judge was attempted but blocked (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` unset), so plain-LLM fixture scores remain until proxy judge credentials are wired.

## Reproduce

```bash
cd adl-lite
source .env
pip install -e ".[dev,experiments]"
pytest tests/ experiments/ -q
python -m experiments.rq1_plain_discover --target-complete 15
python -m experiments.rq1_llm_judge --summarize-from-template
python -m experiments.rq3_retrieval
```

## Key artifacts

- `docs/experiments/RESULTS.md`
- `docs/experiments/rq1_llm_judge_summary.json`
- `data/eval/human_rq1_template.json`
- `docs/experiments/rq3_ablation.json`
- `docs/paper/draft_introduction.md`

## Notes

- `.env` and `experiments/outputs/*.md` remain uncommitted by policy.
- Live proxy judge replacement for `plain_llm` should be rerun after proxy-backed judge credentials are configured.
