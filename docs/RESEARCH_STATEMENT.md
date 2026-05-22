# ADL Lite — Research Statement

**Agent Discovery Language (Lite Edition)**  
Target venue: AAMAS 2027 | Phase 1: May–June 2026

---

## Problem

Multi-agent research and engineering teams increasingly delegate *discovery* to LLM agents: novel patterns in AML graphs, training dynamics, materials simulations, and cross-domain analogies. Today these outputs land as unstructured Markdown or chat logs. That creates three systemic failures:

1. **Ambiguity** — pronouns and implicit referents break cross-agent alignment.
2. **Scope leakage** — private discoveries bleed into public retrieval paths.
3. **Fork chaos** — competing interpretations lack merge/parallel/prune policy.

Existing fixes (JSON schemas, knowledge graphs, raw wiki) each sacrifice human editability, lightweight deployment, or consensus audit trails.

## Proposal

**ADL Lite** is a Markdown-native discovery language with three layers:

- **L1 YAML** — identity, scope URI, status badge, confidence, mechanism
- **L2 Markdown** — discovery prose and `[[Wiki Links]]`
- **L3 `adl:*` blocks** — typed relations, evidence chains, formal seals

A Python toolkit (`adl-lite` CLI + library) provides parsing, SSA validation, hybrid memory indexing (Hot/Warm), and a Concept Consensus Chain isomorphic to blockchain append-only logs — applied to concept lifecycle rather than assets.

## Research questions

| ID | Question |
|----|----------|
| RQ1 | Does Structured Semantic Anchoring reduce referential ambiguity vs plain Markdown? |
| RQ2 | Does an explicit consensus chain reduce coordination cost to reach `validated`? |
| RQ3 | Do L3 relation graphs improve retrieval Recall@10 on a domain query set? |
| RQ4 | Can scope ACL guarantee zero cross-tenant leakage on indexed reads? |

## Method (Phase 1)

- **Dataset:** 20 AML concept stubs + 15 labeled queries (`data/aml/`)
- **Harness:** Scripted 5-agent sim (Discoverer, Reviewer, Skeptic, Merger, Librarian) — no API key
- **Baselines:** Plain Markdown (L3 stripped), YAML-only wiki
- **Metrics:** Pilot scripts in `experiments/rq*.py`; results in `docs/experiments/RESULTS.md`

## Preliminary pilot findings

*(Reproduce: `python -m experiments.run_all`)*

- **RQ4:** 0 scope leaks under ACL probes (pilot)
- **RQ1:** Near-zero pronoun rate on validated examples vs synthetic plain baseline
- **RQ3:** ADL index matches or exceeds plain token overlap Recall@10 (pilot, lexical rubric)

Numbers are **pilot-labeled**; Phase 2 targets human rubrics and embedding retrieval.

## Contributions

1. Normative spec (`docs/SPEC.md`) extractable without 550-line design transcript
2. Open-source reference implementation (parser, validator, memory, consensus)
3. Reproducible evaluation harness + AML mini-dataset
4. Agent workflow documentation and prompt templates for discovery authoring

## Broader impact

ADL Lite enables audit-ready multi-agent discovery in regulated domains (AML, safety-critical ML) while staying compatible with Obsidian and Git-based workflows. Scope URIs and consensus chains provide provenance for downstream automation without locking teams into proprietary graph stores.

## Timeline

| Phase | Window | Deliverable |
|-------|--------|-------------|
| Phase 1 | May–Jun 2026 | Toolkit + pilot RESULTS |
| Phase 2 | Q3 2026 | Embedding retrieval, LLM sim ablation |
| Paper | AAMAS 2027 | Full empirical + case studies |

## References

- Repository: ADL Lite (`adl-lite` on GitHub)
- Design provenance: `ADL_Lite_对话全记录.md`
- Implementation plan: `docs/IMPLEMENTATION_PLAN.md`

---

*Contact: CEIEC AI Infrastructure — research outreach / 申博 portfolio piece.*
