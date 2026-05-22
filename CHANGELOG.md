# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - 2026-05-23

### Added

- Example fork pair (`examples/matdo_original.md`, `examples/matdo_fork_kinetic.md`)
- Wiki-link extraction (`extract_wiki_links`, `ADLDocument.wiki_links`)
- Agent tools module (`adl_lite/tools.py`) and `prompts/write_discovery.md`
- Agent workflow doc (`docs/AGENT_WORKFLOW.md`)
- Scripted 5-agent simulation (`experiments/harness.py`, `python -m experiments.run_sim --scripted`)
- AML mini-dataset (`data/aml/` — 20 concepts, 15 queries)
- Evaluation pilots RQ1–RQ4 (`experiments/rq*.py`, `python -m experiments.run_all`)
- Baselines: plain Markdown and YAML-only wiki
- Paper pack: `docs/paper/OUTLINE.md`, `FIGURES.md`, `RELATED_WORK.md`
- Research statement (`docs/RESEARCH_STATEMENT.md`)
- Pilot results (`docs/experiments/RESULTS.md`)
- Optional MCP script (`scripts/mcp_adl.py`)
- CI workflow (`.github/workflows/ci.yml`)
- Tests: `test_consensus_forks.py`, `test_aml_dataset.py`, `test_experiments.py`

## [0.1.0] - 2026-05-23

### Added

- Markdown-native ADL parser (L1 YAML, L2 body, L3 `adl:*` blocks)
- Pydantic models, SSA validator, hybrid memory index, consensus engine
- Example discovery document (`examples/capital_reflux_trap.md`)
- `adl-lite` CLI: `parse`, `validate`, `store`, `related`, `consensus`
- Normative spec (`docs/SPEC.md`) and Phase 1 implementation plan

[0.2.0]: https://github.com/sunnyang1/adl-lite/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/sunnyang1/adl-lite/releases/tag/v0.1.0
