# ADL Lite Applied Ontology Paper — Compression Plan

**Target:** 40–50 pages (~850 lines of LaTeX source)  
**Current body:** 1,894 lines (excluding commented-out appendices)  
**Reduction required:** ~1,172 lines (62% of body)

---

## Executive Summary

The main paper body is distributed across 9 `.tex` files under `docs/paper_ao/sections/`. The largest sections are §4 Architecture (669 lines) and §5 Empirical Validation (428 lines), which together account for 58% of the body. Compression focuses on migrating detailed formal material, extensive comparison tables, and reproducibility protocols to 13 supplementary appendices (A–M), while preserving the narrative arc and core contributions in the main text.

---

## Section-by-Section Analysis

### abstract.tex (7 lines → 7 lines)
- **Current:** 7 lines
- **Target:** 7
- **Strategy:** No compression. The abstract is already concise and must remain intact.
- **Appendix mapping:** None

### 01_introduction.tex (93 lines → 50 lines)
- **Current:** 93 lines
- **Target:** 50
- **Reduction:** 43 lines (46%)
- **Compression instructions:**
  1. Compress the background paragraph (§1.1) from ~700 words to ~200 words; keep only the four-property gap statement and the one-sentence positioning of KYA/AgentSafe/LLM4ACOE.
  2. Delete the full five-family systematic-awareness paragraph and the "Why existing families are insufficient" extended justification; replace with a single sentence: "Representative systems from five distinct families fail to cover the full intersection of properties (a)–(d); see Appendix~F for detailed comparison tables."
  3. Keep the "operational ontology" definition paragraph intact (essential for reviewers).
  4. Keep contributions (§1.3) and roadmap (§1.4) verbatim; these are the paper's structural skeleton.
  5. Delete the "ontological novelty of the event-first stance" philosophical expansion (paragraph 4); move to Appendix~A if needed.
- **Appendix mapping:** Comparison tables → Appendix F

### 02_related_work.tex (224 lines → 90 lines)
- **Current:** 224 lines
- **Target:** 90
- **Reduction:** 134 lines (60%)
- **Compression instructions:**
  1. **Migrate all 7 comparison tables to Appendix F:**
     - Table `tab:agent-governance` (agent governance systems)
     - Table `tab:wikidata-comparison` (Wikidata vs. ADL Lite)
     - Table `tab:package-comparison` (software registries)
     - Table `tab:nanopub-comparison` (nanopublications vs. EventChains)
     - Table `tab:event-topology` (event topology and integrity)
     - Table `tab:positioning` (positioning against 7 approaches)
     - Table `tab:foundational-positioning` (from §6, but historically part of §2 narrative)
  2. Compress each subsection to a single paragraph (3–5 sentences) summarizing the family and ADL Lite's relationship to it, with a cross-reference to the full table in Appendix~F.
  3. Delete the extended RO-Crate integration paragraph (§2.4); keep one sentence: "ADL Lite interoperates with RO-Crate as a governance layer; details are provided in the supplementary material."
  4. Delete the standards integration paragraph (PROV-O/SHACL/ODRL/DCAT) from §2.4; move to Appendix~J.
  5. Keep the positioning statement (§2.5) and the final gap statement (last paragraph) intact.
- **Appendix mapping:** All 7 tables → Appendix F; standards integration → Appendix J

### 03_ontological_analysis.tex (273 lines → 110 lines)
- **Current:** 273 lines
- **Target:** 110
- **Reduction:** 163 lines (60%)
- **Compression instructions:**
  1. **Migrate OWL 2 DL axiomatization fragment to Appendix A:**
     - Move §3.6 (Formal Alignment Fragment) entirely; replace with a single sentence: "A partial OWL~2 DL axiomatization is provided in Appendix~A; the fragment enables ROBOT compatibility but does not capture δ/γ, which exceed DL expressivity."
  2. Compress the two-level ontological account (§3.2.4) from ~55 lines to ~20 lines: keep the Level 1 / Level 2 distinction and the five dependence axioms, but delete the full paragraph-by-paragraph expansion.
  3. Compress identity conditions (§3.3) from ~35 lines to ~15 lines: keep the equations and the fork/deprecation identity rules, delete the OntoClean evaluation paragraph (move to Appendix~A).
  4. Compress ontological dependence (§3.4) from ~25 lines to ~12 lines: keep the three-form summary (historical, generic, mutual), delete the extended BFO exegesis.
  5. Keep the categories and taxonomy table (`tab:upper-ontology-mapping`) in the main text; it is the section's anchor.
  6. Compress deviation analysis (§3.7) from ~15 lines to ~8 lines; keep the three deviations as a bulleted list.
- **Appendix mapping:** OWL 2 DL axiomatization → Appendix A

### 04_architecture.tex (669 lines → 220 lines)
- **Current:** 669 lines
- **Target:** 220
- **Reduction:** 449 lines (67%)
- **Compression instructions:**
  1. **Migrate complete theorem proofs to Appendix E:**
     - Move all proof environments (Theorems 1–7, Corollary G-Set) from §4.5; keep only theorem statements and one-sentence proof sketches in the main text.
  2. **Migrate BNF grammar and full inference rules to Appendix G:**
     - Move the complete BNF grammar (§4.3.1) and operational semantics inference rules; keep only the comparator alphabet and the high-level syntax equation in the main text.
  3. **Migrate complexity/satisfiability analysis to Appendix H:**
     - Move the full complexity class discussion (P membership, NExpTime comparison, DL-lite correspondence) from §4.3.3; keep only the complexity summary table and one concluding sentence.
  4. **Migrate TLA+ specification reference to Appendix I:**
     - Move the 147-line TLA+ spec and TLC results; keep a one-sentence reference.
  5. **Migrate full threat model table to Appendix K:**
     - Move Table `tab:threat-model` and the Phase 1.5 / Phase 3 mitigation details; keep only the trust assumptions (3 bullets) and a reference to Appendix~K.
  6. **Compress formal derivation semantics (§4.5):**
     - Keep the notation table (`tab:formal-notation`) and the δ/γ definitions.
     - Delete the full algorithmic prose for δ and γ (the equations are sufficient).
     - Delete the sensitivity analysis paragraph; move to Appendix~E.
  7. **Compress comparison with formal frameworks (§4.6):**
     - Compress Event Calculus, Situation Calculus, and DL subsections from ~80 lines to ~30 lines total: keep the core equivalence claims and the expressiveness bounds paragraph, delete the extended philosophical exposition.
  8. **Compress trust model (§4.7):**
     - Keep the trust assumptions and the 4 limitation bullets.
     - Delete the collusion lemmas (move to Appendix~K), the Phase 1.5 bridge details (move to Appendix~K), and the fault/recovery paragraph (move to Appendix~D).
  9. Keep the document model (§4.1), EventChain data structure (§4.2), and cryptographic integrity (§4.2.1) intact; these are the architecture's foundation.
- **Appendix mapping:** Proofs → E; BNF/inference → G; Complexity → H; TLA+ → I; Threat model → K

### 05_empirical_validation.tex (428 lines → 150 lines)
- **Current:** 428 lines
- **Target:** 150
- **Reduction:** 278 lines (65%)
- **Compression instructions:**
  1. **Migrate adversarial integrity trials (§5.7) to Appendix C:**
     - Move the full 7-attack + 4-undetectable tables and methodology; keep a one-sentence summary: "1,407 adversarial trials (7 scenarios × 201 chains) achieved 100% detection recall; see Appendix~C."
  2. **Migrate full reproducibility protocol (§5.10) to Appendix D:**
     - Move the Docker environment, reproduction scripts, and artifact manifest; keep the hardware spec and one sentence: "Full reproducibility protocol is in Appendix~D."
  3. **Migrate E19 governance cost methodology to Appendix L:**
     - Move the task definitions, baseline descriptions, and estimated cost table (`tab:e19-benchmark`); keep one paragraph: "An author-estimated cost analysis (E19) suggests ADL Lite requires fewer LOC than nanopub/PROV-O baselines; see Appendix~L."
  4. **Compress boundary experiments (E13–E16):**
     - Compress the four boundary subsections from ~80 lines to ~20 lines total: keep the headline results and one-sentence interpretation, delete the per-experiment paragraph-level detail.
  5. **Compress E6 (scalability):**
     - Keep the throughput figure and the integrity result.
     - Delete the latency decomposition, dataset derivation paragraph, and synthetic event generation strategy; move to Appendix~D.
     - Delete the event-distribution table (`tab:event-distribution`); move to Appendix~D.
  6. **Compress E5 (domain evaluation):**
     - Keep the status disclaimer (preliminary design) and the procedure summary.
     - Delete the expected outcomes and the pilot E17 paragraph; these are future work.
  7. **Compress comparative evaluation (E12):**
     - Keep the two comparison tables (`tab:comparative-eval`, `tab:comparative-benchmark`) if space permits; otherwise migrate to Appendix~F.
     - Delete the extended interpretation paragraphs ("Capability-governance efficacy", "Failure modes", "Approximate baselines"); keep one sentence each.
  8. Keep E1–E4 summaries intact; they are the core validation results and total only ~40 lines.
  9. Keep the results summary table (`tab:results`) intact; it is the section's anchor.
- **Appendix mapping:** Adversarial → C; Reproducibility → D; E19 → L; extra tables → F

### 06_discussion.tex (113 lines → 60 lines)
- **Current:** 113 lines
- **Target:** 60
- **Reduction:** 53 lines (47%)
- **Compression instructions:**
  1. **Migrate loss-analysis table to Appendix J:**
     - Move Table `tab:loss-analysis` and the full PROV-O/SHACL/ODRL/DCAT mapping discussion from §6.2; keep one sentence: "A loss analysis of standards mappings is in Appendix~J."
  2. Compress reviewer Q&A (§6.2) from ~35 lines to ~15 lines: keep the question references and one-sentence answers, delete the full paragraph-level responses for Q3, Q5, Q6, Q8.
  3. Compress the capability-registry contribution (§6.3) from ~25 lines to ~12 lines: keep the three bullet headers, compress each to one sentence.
  4. Keep the limitations (§6.4) intact; they are essential for reviewer trust and map directly to future work.
  5. Keep the complementary systems (§6.6) and agent governance landscape (§6.7) as one combined paragraph.
- **Appendix mapping:** Loss analysis → J

### 07_conclusion.tex (65 lines → 35 lines)
- **Current:** 65 lines
- **Target:** 35
- **Reduction:** 30 lines (46%)
- **Compression instructions:**
  1. Compress the contribution restatement from ~30 lines to ~15 lines: merge the three contribution paragraphs into one bullet list with 1–2 sentences per item.
  2. Compress future work (§7.2) from ~30 lines to ~15 lines: keep the five thematic cluster headers and one sentence each, delete the per-item elaboration (FW1, FW3, FW4, etc.). The full future work is already in the discussion.
  3. Delete the "Limitations and Response to Review" subsection (§7.2.6); it duplicates discussion material.
- **Appendix mapping:** None

### agentsafe_integration.tex (22 lines → 0 lines)
- **Current:** 22 lines
- **Target:** 0
- **Strategy:** Drop from the main body. The AgentSafe integration is a secondary system sketch. It can be referenced in the discussion as a one-sentence complementary system or integrated into Appendix~J if a full mapping table is needed.
- **Appendix mapping:** Optional → Appendix J (if expanded)

---

## Content-to-Appendix Mapping Summary

| Appendix | Title | Source Section | Current Lines | Compression Action |
|----------|-------|----------------|---------------|-------------------|
| A | OWL 2 DL Axiomatization | §3.6 | ~20 | Move entire subsection |
| B | SHACL Shapes | `shacl_validation.py` + §2/§6 | ~56 | Consolidate existing + code |
| C | Adversarial Test Suite | §5.7 | ~50 | Move tables + methodology |
| D | Reproducibility Protocol | §5.10 + E6 details | ~80 | Move Docker + scripts + dataset |
| E | Complete Proofs | §4.5 + appendix_e.tex | ~320 | Move proofs + sensitivity |
| F | Comparison Tables | §2 (7 tables) + E12 | ~120 | Migrate all tables |
| G | BNF + Inference Rules | §4.3 | ~40 | Move BNF + inference rules |
| H | Complexity Analysis | §4.3.3 | ~25 | Move complexity class discussion |
| I | TLA+ Specification | §4.5 (existing) | ~147 | Include 147-line spec + TLC results |
| J | Loss Analysis | §6.2 | ~30 | Move standards mapping table |
| K | Threat Model | §4.7.5 | ~40 | Move threat table + mitigation details |
| L | E19 Methodology | §5.8 | ~40 | Move cost table + task definitions |
| M | Compression Log | This plan | ~80 | Populate tracking tables |

---

## Risk Assessment and Contingencies

1. **Table overflow in Appendix F:** If 7 tables exceed page limits, split into two sub-appendices (F1 Agent Governance, F2 Formal Frameworks) or convert to landscape format.
2. **Proof length in Appendix E:** The 320-line proof material is already written; if it grows, use two-column formatting or reduce font size (`\small`).
3. **TLA+ spec location:** The 147-line `EventChain.tla` file has not been located in the repository. If it is missing, Appendix~I will be a placeholder with a TODO and the inline TLA+ excerpt from §4.5.
4. **Cross-referencing:** After compression, every migrated element must be referenced from the main text via `Appendix~X`. A grep pass will verify that no dangling references exist.

---

## Verification Checklist

- [ ] All `.tex` files in `sections/` modified according to the plan above.
- [ ] All appendices in `supplementary/` populated with extracted content.
- [ ] `supplementary.tex` compiles independently with `pdflatex`.
- [ ] `main.tex` compiles with compressed sections and references supplementary appendices.
- [ ] `check_compression.py` reports total ≤ 850 lines and supplementary total ≥ 1,200 lines.
- [ ] Cross-reference audit: every `Table~\ref{...}` and `Appendix~X` resolves correctly.

---

*Plan generated by Worker_Paper (ADL Lite compression engineering).*  
*Date: 2026-06-15*
