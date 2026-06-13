# ADL Lite Paper Revision Plan

## Objective
Address all Major and Minor revision points from the peer review report to meet Applied Ontology publication standards.

## Stage 1: Structural & Framing Changes
1. **Introduction (01_introduction.tex)**
   - Weaken "paradigm-level reduction" → "operationalization of event-first stance"
   - Distinguish philosophical contribution (Wittgenstein/BFO/DOLCE grounding) from engineering contribution (Markdown-native, hash-linked, deterministic derivation)
   - Add explicit counter-example argument: why CIDOC CRM, SEO, nanopublications cannot simultaneously satisfy (a) document-native authoring, (b) tamper detection, (c) lifecycle state machines, (d) pip-installable deployment
   - Add Roadmap subsection defining Phase 1/2/3

2. **Related Work (02_related_work.tex)**
   - Compress from 212 lines to ~130 lines (60% target)
   - Remove descriptive fluff; keep only critical analysis that establishes research gap
   - Trim: LLM-native OE subsection (keep 2 paragraphs not 3+survey), CRDT subsection (compress), event-centric ontologies (compress CIDOC CRM, SEM/LODE, RDF stream)
   - Keep: Foundational ontology comparison (needed for Section 3), nanopublication comparison (needed for positioning), positioning table

## Stage 2: Methodology & Formal Semantics
3. **Architecture (04_architecture.tex)**
   - Add paragraph justifying informal proofs: "The seven theorems are proved by natural-language argument because each reduces to a single case analysis or induction on a finite chain. The logical structure is a decidable fragment of first-order logic (no quantifier alternation, no fixed-point operators). A TLA+ specification is provided as supplementary material..."
   - Add confidence parameter rationale: 0.5 base from social science consensus thresholds (majority belief = 0.5), 0.05 from calibration against 10 validators → max 0.95 + base; sensitivity analysis note

## Stage 3: Empirical Validation
4. **Empirical Validation (05_empirical_validation.tex)**
   - Expand E4: add boundary tests for concurrent actions, extreme confidence (0.0, 1.0, NaN), long chains (>10,000 events)
   - E6: add 10-run statistics (mean ± std), baseline comparison (raw CSV read vs EventChain), latency decomposition table already present but add cross-reference
   - Add synthetic event generation strategy: "governance events injected by stratified random sampling: VALIDATE at 2.2% (uniform over chains with ≥5 events), DEPRECATE at 0.5% (targeting chains with ≥10 events), FORK at 0.3% (random chain selection), EVIDENCE at 0.2% (uniform)"
   - Reposition E5/E6: explicitly label as "framework paper" with "domain evaluation deferred to future work" — add preliminary E5 pilot results if available, otherwise strengthen the framework-paper framing

## Stage 4: Bibliography & Polish
5. **references.bib**
   - Fix wittgenstein_tractatus: @article → @book
   - Fix prov_o_mapping: @article → @misc (W3C Recommendation)
   - Fix linked_data_proofs: @article → @misc (W3C Candidate Recommendation)
   - Fix rdf_star: @article → @misc (W3C Working Draft)
   - Fix cidoc_crm: @article → @misc (ISO standard)
   - Fix c_sparql: @inproceedings → keep (ISWC paper)
   - Fix cert_transparency: @inproceedings → @misc (RFC)
   - Fix w3c_rsp: @techreport → @misc
   - Fix json_ld: @techreport → @misc

## Stage 5: Integration & Verification
6. Compile LaTeX and verify no errors
7. Review word count and section balance
