# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased] — 2026-06-03: AO Reviewer Revision

### Added

- **Trust model & security boundaries** (`docs/paper_ao/sections/04_architecture.tex` §4.8): explicit threat model table (8 threats), trust assumptions, planned Phase 3 mitigations (Ed25519/Linked Data Proofs/DIDs)
- **CRDT convergence semantics**: Theorem 7 (LWW-Set merge) + Corollary (G-Set CRDT) in §4.6, with full proof sketches in Appendix E
- **Comparative evaluation** (§5.7): 4-task governance suite vs nanopublications + PROV-O, 8-metric comparison table
- **Adversarial test suite** (Appendix C): 8 attack classes, 32 test cases, results table
- **SHACL coverage analysis** (Appendix B): 5 constraint definitions, Core vs SPARQL expressivity table
- **Hardware environment + latency decomposition** (§5.6): Apple M2 specs, per-stage latency breakdown (CSV 13%, Pydantic 58%, SHA-256 16%, ChainVerify 10%)
- **Related work expansions** (§2): OBO Foundry change management, RO-Crate/FAIR Digital Objects, blockchain provenance, Git signed-commit workflows, PLUGMEM integration
- **Formal notation table** (§4.6): $\Sigma$, $\text{WF}$, $\delta$, $\gamma$, $\text{Fork}$ symbol reference
- **TLA$^{+}$ mechanised proof footnote** (§4.6)
- **PLUGMEM integration discussion** (§6.5)

### Changed

- **BFO GDC category fix** (§3.2.2, §3.4.1, Table 1): Concept depends on EventChain as ICE (Information Content Entity) bearer, not as occurrent. Added formal dependency diagram.
- **References**: 61 placeholder entries removed; 13 cited placeholders replaced with real citations. Now 30 real references (100%).
- **Paper page count**: 45 → 52 pages

### Fixed

- Theorem 6 proof relocation (was orphaned during CRDT theorem insertion, now correctly positioned before Theorem 7)

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
