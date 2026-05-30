# v0.3.1 — RQ1 scale-up and paper narrative

## Highlights

- **RQ1 scale-up complete:** curated and judged set now reaches **n=15** discoveries with consolidated summaries.
- **Paper narrative pack:** updated **AAMAS-target outline** and experiment-facing docs for write-up flow.
- **LLM judges integrated:** RQ1 LLM-as-judge workflow plus proxy judge artifacts for no-key reproduction paths.
- **Phase B path retained:** retrieval/eval stack and scripted demo remain reproducible with current commands.

## Reproduce

```bash
cd adl-lite
pip install -e ".[dev,experiments]"
pytest tests/ experiments/ -q
python -m experiments.run_phase_b
./scripts/demo_pipeline.sh --scripted
python -m experiments.rq1_llm_judge --all
adl-lite validate examples/*.md
```

If API access for LLM judges is unavailable, use:
- `docs/experiments/rq1_llm_judge_summary.json`

## Key artifacts

- `docs/experiments/rq1_human_summary.json`
- `docs/experiments/rq1_llm_judge_summary.json`
- `docs/paper/OUTLINE.md`
- `docs/experiments/summary_phase_b.json`

## Breaking changes

None expected.
