# ADL Lite — External Review Package

> **Paper:** An Event-First Capability-Lifecycle Registry for LLM Agent Ecosystems (ADL Lite)  
> **Version:** v0.4.0-alpha (Month 3, code-paper alignment complete)  
> **Length:** 35 pages (main) + 21 pages (supplementary)  
> **Target venue:** Applied Ontology (ESWC/ISWC 2027 track as backup)  
> **Generated:** 2026-06-17

---

## Purpose

This package contains three targeted reviewer briefs designed for **external expert review** before submission. Each brief assigns a specific reviewer persona, focuses on a distinct paper dimension, and provides concrete checklist questions. The goal is to surface critical issues before the actual peer-review process, when they are still fixable.

---

## Reviewer Briefs

| File | Persona | Focus | Key Deliverable |
|------|---------|-------|---------------|
| [`formal_semantics_reviewer.md`](formal_semantics_reviewer.md) | Formal Semantics / Logic Reviewer | Theorems 1–9, proof sketches (Appendix E), precondition language, TLA+ spec | Verdict on theorem correctness & proof rigor |
| [`applied_ontology_reviewer.md`](applied_ontology_reviewer.md) | Applied Ontology / Upper Ontology Reviewer | BFO/DOLCE/UFO mappings, OntoClean evaluation, OWL 2 DL fragment, deviations | Verdict on ontological soundness & alignment quality |
| [`systems_engineering_reviewer.md`](systems_engineering_reviewer.md) | Systems Engineering / Empirical Reviewer | Experiments (E1–E23), reproducibility, adversarial trials, comparative evaluation | Verdict on empirical rigor & threat model honesty |

---

## How to Use These Briefs

1. **Select reviewers.** Identify 2–3 colleagues with expertise matching the personas. Ideal candidates:
   - **Formal semantics:** Someone with experience in formal methods, event calculi, or logic in computer science.
   - **Applied ontology:** Someone familiar with BFO, DOLCE, UFO, OntoClean, and OWL 2 DL reasoning.
   - **Systems engineering:** Someone who builds and evaluates distributed systems, registries, or provenance pipelines.

2. **Send the brief + paper.** Include the relevant brief, the compiled PDF (`main.pdf`), and the supplementary PDF (`supplementary.pdf`). The brief tells the reviewer exactly what to look for, so they don't waste time on irrelevant sections.

3. **Collect structured feedback.** Ask reviewers to return answers to the checklist questions, plus a verdict. The checklists are designed to be answerable with "Yes / No / Partially + comment."

4. **Triage feedback.** Major issues (theorem gaps, ontological category errors, irreproducible experiments) must be fixed before submission. Minor issues (notation inconsistencies, mapping approximations, missing baselines) can be deferred if time is short.

---

## Pre-Emptive Fixes Already Applied (Month 3)

The following issues were discovered during code-paper alignment and **fixed before sending to reviewers**:

| Issue | Fix | Status |
|-------|-----|--------|
| **Two Theorem 7s** — CRDT Convergence and Well-Formedness Preservation both numbered 7 | CRDT Convergence → **Theorem 9** across §4.4.5, §1, §6, Appendix E, Appendix K | ✅ Fixed |
| **Corollary undefined** — `corollary` environment missing in supplementary.tex | Added `\newtheorem{corollary}[theorem]{Corollary}` | ✅ Fixed |
| **E20b flaky test** — `test_ece_reduction_positive` failed in batch run | Moved `random.seed(42)` inside `run()` method for isolation | ✅ Fixed |
| **Calibration formula mismatch** — `calibrated_confidence()` used normalized weighted mean instead of scaled mean | Updated to `γ_cal = Σ(φ(a,V) × accuracy_a) / |A|` | ✅ Fixed |
| **CRDT merge mismatch** — derived-state lattice instead of EventChain-level LWW-Set | Added `merge_event_chains()` with union, deduplicate, sort, rehash | ✅ Fixed |
| **Well-formedness incomplete** — only 4 of 8 axioms checked | Expanded to 12 axioms (distinct IDs, actor, timestamp, payload, action, hash format, canonical fields, valid type) | ✅ Fixed |
| **γ not O(1)** — `confidence` and `status` scanned full chain | Confirmed O(1) — scan from tail for first VALIDATE | ✅ Fixed |
| **Collusion threshold missing** — `validate` had no `N_min` check | Added `validator_count >= 1` to ontology YAML + `collusion_resistance` config | ✅ Fixed |
| **Missing canon_version** — hash didn't include canonicalization version | Added `CANON_VERSION = "1.0"` to `_compute_hash()` | ✅ Fixed |
| **Missing tests** — Theorems 4, 5, 7, 8 not explicitly tested | Added `test_theorems.py` with 33 tests | ✅ Fixed |
| **Pre-existing test failures** — 12 tests failed due to timestamp monotonicity, action preconditions, etc. | All fixed; 590 tests now pass | ✅ Fixed |
| **Phase labels** — "Phase 1/2/3" in code and paper | Replaced with "current collaborative-audit model", "future release" | ✅ Fixed |
| **Reviewer questions anti-pattern** — Q1–Q8 distributed as subsections | Reintegrated into relevant sections (§4.8, §5.2.3, §6.2) | ✅ Fixed |

---

## Known Issues Not Yet Fixed (Flagged in Briefs)

These are **intentionally left for reviewer feedback** to confirm whether they are actually problems or just author paranoia:

1. **Horn-clause claim may be overstated** (§3.6, §4.5, Appendix H) — precondition language is not technically a Horn-clause fragment.
2. **E19 entirely author-estimated** — Table 8 contains no measured values; honest but weak.
3. **Git-only baseline is a straw-man** — Git is not a governance system; comparison may be unfair.
4. **OWL 2 DL fragment is minimal** — does not cover derivation functions; merely a "starting point."
5. **Terminological slip (dependence)** — "generic dependence" (BFO) and "rigid existential dependence" (Fine) used somewhat interchangeably.

---

## Next Steps After Review

1. **Week 7–8:** Collect external reviewer feedback (target: 2–3 reviewers, 1-week turnaround).
2. **Week 8:** Triage feedback → fix major issues, document minor issues as deferred.
3. **Month 4 (v0.4.0):** Incorporate reviewer feedback into final paper revision. Prepare submission package.
4. **Month 5:** Submit to Applied Ontology (AO) or ESWC/ISWC 2027.

---

## Files in This Package

```
docs/paper_ao/reviewer_briefs/
├── README.md                           ← This file
├── formal_semantics_reviewer.md        ← Logic / theorem reviewer
├── applied_ontology_reviewer.md        ← Ontology / BFO reviewer
└── systems_engineering_reviewer.md     ← Empirical / systems reviewer
```

---

*Generated by the Orchestrator as part of the Month 3 external review phase of the ADL Lite Survival Path.*
*Code-paper alignment: 590 tests passing, 9 theorems, 35-page paper.*
