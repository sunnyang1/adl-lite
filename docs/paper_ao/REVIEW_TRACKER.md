# ADL Lite Paper Review Tracker

## Paper: ADL Lite: An Event-First Capability-Lifecycle Registry for LLM Agent Ecosystems
## Target Venue: Applied Ontology

---

## Round 1 (v1) — 2025-07-03
**Token:** `XEOxFgUv8dfIJMTB7et4kr7U6ipbDI1VkMsGB_uCET8`
**Verdict:** Acceptance pending moderate revisions
**Key Issues:**
- Formalization insufficient (OWL/SHACL missing, only v1 sketch)
- Empirical validation weak (synthetic only, no cross-validation)

---

## Round 2 (v2) — 2025-07-04
**Token:** `jGJnExg2_6tptUC6LOeGR1Omy7sEG9dEHqgtI9IxHKA`
**Verdict:** Acceptance after substantial revision
**Key Issues:**
- GDC/ICE dependence conflict in OntoClean analysis
- Missing domain-grounded expert evaluation (AML)
- Formal artifacts not fully released (Coq proofs incomplete)

**Response:** 5 parallel workstreams (WS1-WS5) across 103 pages.

---

## Round 3 (v3) — 2025-07-05
**Token:** `pB_4LFbO96QnL8KNKDEVtEmVuRy5frOKFceqfGyB_PQ`
**Verdict:** Major Revision
**Key Issues (5 structural):**
1. Missing compact OWL 2 DL module with BFO/IAO imports
2. OntoClean treatment superficial (only 6 classes, no constraints)
3. Identity/dependence axioms lack necessary/sufficient conditions
4. Coq mechanization not clearly documented in paper
5. No controlled comparison with nanopubs/PROV-O+signatures

**Response:** 5 parallel workstreams expanded to 125 pages.

---

## Round 4 (v4) — 2025-07-06
**Token:** `iyns4wPmiZLCAIUqHEGTVoi9c04A0AOv2IY4Vh5xAFU`
**Verdict:** On the cusp (between Minor and Major revision)
**Assessment:**
> "strong on concept and engineering feasibility, somewhat underdeveloped in adversarial robustness and empirical ontology validation. I encourage revision that strengthens formal exposition and includes an initial domain expert assessment."

**Remaining Gaps (for v5):**
1. **Initial domain expert assessment** — structured rubric, 3-5 experts, 5-10 concepts
2. **Formal exposition** — precondition grammar, CRDT lattice, identity under fork/merge in paper body
3. **Adversarial robustness discussion** — non-Byzantine limitations, DID/LD-Proofs mitigation path
4. **Head-to-head baseline comparison** — quantitative comparison with nanopubs/PROV-O

**Response Plan:**
- WS1: Design structured expert evaluation rubric + pilot (pending local filesystem access)
- WS2: Move precondition grammar, CRDT lattice, identity axioms from appendix to paper body
- WS3: Add adversarial robustness section + run E19 comparison experiment
- Expected paper length: 125-135 pages

---

## Current Status (2025-07-06)
- **GitHub PDF:** `docs/paper_ao/main.pdf` (v4, 125 pages, 965KB)
- **Local filesystem:** Permission denied (EPERM) on macOS — TCC/SIP protection suspected
- **Next action:** Fix filesystem access or upload via GitHub API directly

## Reviewer Questions Summary (9 questions)

| # | Question | Status |
|---|----------|--------|
| 1 | Coq development link + exact theorem statements | ✅ Answered in v4 §5.8 |
| 2 | FORK/merge identity criteria | ✅ Answered in v4 §3.2.6 |
| 3 | Precondition language formalization | ⚠️ Partially in appendix; needs to move to body |
| 4 | CRDT lattice semantics | ⚠️ Partially in appendix; needs to move to body |
| 5 | HoldsAt vs BFO/UFO relational qualities | ✅ Answered in v4 §3.2.3 |
| 6 | DID/LD-Proofs integration plan | ⚠️ Mentioned in §6.3; needs expansion |
| 7 | Storage/verification cost profiles | ⚠️ Mentioned in §5.5; needs expansion |
| 8 | AML expert evaluation | ❌ Not yet executed (planned) |
| 9 | Vector index relevance | ✅ Trimmed in v4 |

---

## Round 5 (v5) — 2026-08-05
**Verdict:** Pre-submission hardening (internal team revision, no new reviewer token)
**Scope:** Applied Ontology submission cleanup — eliminate hard blockers before resubmission.

**Changes made:**
1. **Test numbers updated to measured values.** All stale declarations (1,311 tests / 88 files / 77% coverage; 944 pytest cases) replaced with the measured fast-suite baseline: **1,651 tests (106 files) at 91% coverage** (§7, §4.4, §5.8, supplementary Appendix E, R&R attachment).
2. **R&R chapter removed from submission body.** The "Response to Reviewers" section was deleted from `main.tex`; its content was moved to `docs/paper_ao/reviewer_response_rr.tex` as an R&R attachment that is not part of the submitted manuscript.
3. **E36 expert evaluation honestly rewritten.** The pilot domain-expert evaluation is now reported as a *simulated pilot + planned full-scale study*: fabricated claims of three real AML specialists, verbatim expert quotes, and unverifiable κ=0.72 / r=0.68 statistics were removed; quantitative benchmarks now reference the reproducible E32 (κ=0.67) and E35 (κ=1.0 by construction, r=0.60) simulated results. All E36 tables are labeled "simulated."
4. **ROBOT validation contradiction eliminated.** §6 previously claimed the OWL 2 DL fragment was "not ROBOT-validated"; corrected to match §3.5 and Appendix A: ROBOT OWL 2 DL profile conformance, structural consistency, and SPARQL constraint verification are confirmed (report: `docs/OWL2_DL_ROBOT_VALIDATION_REPORT.md`).
5. **Citations completed.** Orphan entries now cited in §2: `zhou2026governance` (governance), `mazzocca2024didvc` (DID/VC), corrected `akbarfam2024blockchain` (SOK blockchain provenance, formerly placeholder "Others"). New entries added and cited: `barbereau2026lifecycle` (blockchain lifecycle, arXiv 2606.10631), `mcp2024anthropic`, `a2a2025google`, `agntcy2025linux` (MCP/A2A/AGNTCY with differentiated lifecycle-audit positioning).
6. **E36 numbering conflict fixed.** The adversarial robustness baseline comparison was renumbered from E36 to **E37** (§5, §6, Appendix C); E36 now uniquely denotes the (simulated) domain-expert evaluation.
7. **Version docs updated to v0.6.0-alpha** (`README.md`, `review/reviewer_briefs/README.md`, `REVIEW_TRACKER.md`).

**Status:** Ready for Applied Ontology submission (pending final LaTeX compile check).
