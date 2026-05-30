# ADL Lite — Research Statement

**Agent Discovery Language (Lite Edition)**  
Primary venues: ESWC 2027 + ISWC 2027 (Semantic Web / ontology learning / agentic KG) | Backup: AAMAS 2027 | Phase 1: May–June 2026

**Thesis (one line).** ADL Lite is a Markdown-native **operational ontology** for agentic knowledge-graph authoring—schema-guided L3 triples and a YAML predicate registry between plain notes and OWL-heavy stacks—with multi-agent consensus and scope ACL as auditable coordination layers, not a new MAS runtime.

**Tagline.** *Schema-guided operational ontology in Markdown; honest pilot evidence.*

---

## Problem

Multi-agent research and engineering teams increasingly delegate *discovery* to LLM agents: novel patterns in AML graphs, training dynamics, materials simulations, and cross-domain analogies. Today these outputs land as unstructured Markdown or chat logs. That creates three systemic failures:

1. **Ambiguity** — pronouns and implicit referents break cross-agent alignment.
2. **Scope leakage** — private discoveries bleed into public retrieval paths.
3. **Fork chaos** — competing interpretations lack merge/parallel/prune policy.

Existing fixes (JSON schemas, knowledge graphs, raw wiki) each sacrifice human editability, lightweight deployment, or consensus audit trails.

## Proposal

**ADL Lite** is a Markdown-native **operational ontology** (Semantic Web / agentic KG lead) with three layers:

- **L1 YAML** — identity, scope URI, status badge, confidence, mechanism
- **L2 Markdown** — discovery prose and `[[Wiki Links]]` under SSA referent discipline
- **L3 `adl:*` blocks** — RDF-like typed relations, evidence chains, formal seals; validated against a **closed YAML predicate registry** (Method D over Method E authoring)

A Python toolkit (`adl-lite` CLI + library) provides parsing, SSA + ontology validation, hybrid memory indexing (Hot/Warm), and an append-only **concept consensus chain** for lifecycle audit trails in multi-agent workflows—secondary to the ontology contract, not a replacement for agent orchestration platforms.

## Research questions

| ID | Question |
|----|----------|
| RQ1 | Does Structured Semantic Anchoring reduce referential ambiguity vs plain Markdown? |
| RQ2 | Does an explicit consensus chain reduce coordination cost to reach `validated`? |
| RQ3 | Do L3 relation graphs improve retrieval Recall@10 on a domain query set? |
| RQ4 | Can scope ACL guarantee zero cross-tenant leakage on indexed reads? |

## Method (Phase 1)

- **Dataset:** 20 AML concept stubs + 25 retrieval queries (`data/aml/queries.json`, Phase B)
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

1. **Operational ontology layer** — closed YAML predicate registry, schema-guided L3 validation (Method D), agent introspection; optional Turtle export (Phase 3)
2. **Tri-layer Markdown contract** — SSA, scope ACL, L3 relation/evidence blocks (`docs/SPEC.md`)
3. **Open-source reference implementation** — parser, validator, `ADLMemory`, consensus engine
4. **Reproducible evaluation harness** — AML mini-corpus, fair-plain and unstructured baselines, frozen Phase B metrics (`docs/experiments/RESULTS.md`)
5. **Pilot evidence with explicit limits** — mechanistic RQ2/RQ4 and L3-only RQ3 gains; unstructured-vs-ADL RQ1 signal; reported nulls (fair-plain RQ1 Δ=0; scenario RQ3 Δ=0). **Human RQ1 cancelled** — LLM-judge / proxy only for subjective clarity.

## Broader impact

ADL Lite enables audit-ready multi-agent discovery in regulated domains (AML, safety-critical ML) while staying compatible with Obsidian and Git-based workflows. Scope URIs and consensus chains provide provenance for downstream automation without locking teams into proprietary graph stores.

## Timeline

| Phase | Window | Deliverable |
|-------|--------|-------------|
| Phase 1 | May–Jun 2026 | Toolkit + pilot RESULTS |
| Phase 2 | Q3 2026 | Ontology 2a–2c, embedding retrieval, optional Turtle export |
| Paper sprint | Q3–Q4 2026 | Draft pack + track selection (ESWC / ISWC / LLMs4OL) |
| Primary submission | 2027 | ESWC 2027 + ISWC 2027 main / In-Use / Resource tracks |
| Optional sprint | May 2026 | ISWC 2026 Resource — tight; treat as stretch or defer to ISWC 2027 |
| Backup | 2027 | AAMAS 2027 (multi-agent consensus framing) |

## References

- Repository: ADL Lite (`adl-lite` on GitHub)
- Design provenance: `ADL_Lite_对话全记录.md`
- Implementation plan: `docs/IMPLEMENTATION_PLAN.md`

---

*Contact: CEIEC AI Infrastructure — research outreach / 申博 portfolio piece.*
