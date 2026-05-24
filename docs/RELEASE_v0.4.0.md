# v0.4.0 — Ontology middle layer (2a–2c)

## Highlights

- **Operational ontology registry:** `adl_lite/adl_core_ontology.yaml` with closed predicate and transition sets.
- **Strict validation (opt-in):** `adl-lite validate --strict` rejects unknown L3 predicates.
- **Agent introspection (2c):** `adl_ontology_query` in `tools.py`, CLI `adl-lite ontology query`, MCP script support.
- **Research loop closure:** frozen pilot numbers (`docs/experiments/RESULTS.md`), human RQ1 protocol, reproducibility checklist.

## Reproduce

```bash
cd adl-lite
pip install -e ".[dev,experiments]"
pytest tests/ -v
pytest experiments/ -v
adl-lite validate examples/*.md
adl-lite validate --strict examples/*.md
adl-lite ontology validate --examples
python -m experiments.run_phase_b
python -m experiments.rq1_llm_judge --summarize-from-template --proxy-only --no-plain-fixture
python -m experiments.rq1_human_eval
./scripts/demo_pipeline.sh --scripted
```

See `docs/experiments/RESEARCH_LOOP_CHECKLIST.md` for the full closure bundle.

## Key artifacts

- `adl_lite/adl_core_ontology.yaml`
- `adl_lite/ontology.py`
- `docs/experiments/RESEARCH_LOOP_CHECKLIST.md`
- `docs/experiments/HUMAN_RQ1_PROTOCOL.md`
- `docs/experiments/summary_phase_b.json` (frozen 2026-05-24)

## Breaking changes

None expected. Strict ontology validation remains **opt-in** (`--strict` or `ADL_STRICT_ONTOLOGY=1`).

## Pending (post-release)

- Human RQ1 inter-rater study execution (`referent_clarity` fields still null)
- Optional Turtle export (Phase 3)
