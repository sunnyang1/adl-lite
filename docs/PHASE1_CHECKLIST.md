# Phase 1 Checklist (2026-05-23 → 2026-06-30)

Track progress here or mirror as a GitHub issue. Full context: [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md).

## Foundation
- [x] `LICENSE` (MIT)
- [x] `CHANGELOG.md`
- [x] `docs/SPEC.md`
- [x] README: provenance link to `ADL_Lite_对话全记录.md` + plan link

## CLI (`adl-lite`)
- [x] `parse`
- [x] `validate`
- [x] `store`
- [x] `related`
- [x] `consensus register | transition | verify`
- [x] `tests/test_cli.py`

## Examples & tests
- [x] Example 2 (non-AML concept) — `examples/gradient_explosion.md`
- [x] Example 3 (public `concept` doc) — `examples/gradient_explosion.md`
- [x] Example 4 (fork pair) — `examples/matdo_original.md` + `matdo_fork_kinetic.md`
- [x] Golden parser tests — `tests/test_golden_parser.py`
- [x] Scope ACL tests — `tests/test_scope_access.py`
- [x] Consensus fork tests — `tests/test_consensus_forks.py`
- [x] Wiki-link extraction — `extract_wiki_links()` + `doc.wiki_links`
- [x] ≥20 pytest tests total

## Agent & sim
- [x] `adl_lite/tools.py`
- [x] `prompts/write_discovery.md`
- [x] `docs/AGENT_WORKFLOW.md`
- [x] Scripted 5-agent harness — `experiments/harness.py`, `python -m experiments.run_sim --scripted`
- [x] AML dataset: 20 concepts, 15 queries — `data/aml/`
- [x] (Optional) MCP server — `scripts/mcp_adl.py`

## Evaluation
- [x] Baseline: plain Markdown — `experiments/baselines/plain_markdown.py`
- [x] Baseline: YAML-only wiki — `experiments/baselines/yaml_wiki.py`
- [x] RQ1 ambiguity metric — `experiments/rq1_ambiguity.py`
- [x] RQ2 consensus rounds — `experiments/rq2_consensus.py`
- [x] RQ3 Recall@10 — `experiments/rq3_retrieval.py`
- [x] RQ4 scope leakage = 0 — `experiments/rq4_leakage.py`
- [x] `docs/experiments/RESULTS.md`
- [x] `python -m experiments.run_all`

## Academic
- [x] `docs/paper/OUTLINE.md`
- [x] Lifecycle + architecture figures — `docs/paper/FIGURES.md`
- [x] `docs/paper/RELATED_WORK.md`
- [x] `docs/RESEARCH_STATEMENT.md`

## CI
- [x] `.github/workflows/ci.yml`

## Done when
- [x] New contributor can reproduce one number from `RESULTS.md`
- [x] `adl-lite validate examples/*.md` passes in CI
