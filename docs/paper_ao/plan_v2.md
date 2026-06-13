# ADL Lite Paper Revision Plan v2
## Addressing Peer Review Weaknesses and Questions

## Reviewer Weaknesses to Address

### W1. Technical limitations: Phase 1 trust model
- **Action**: Strengthen trust model section; make explicit that governance claims are scoped to collaborative-audit (non-Byzantine) settings; CRDT convergence scoped to optional LWW-Set merge only
- **Location**: 04_architecture.tex (Section 4.5), 06_discussion.tex (L4)

### W2. Ontological blur: record vs reality
- **Action**: Present clean two-level account in Section 3:
  - Level 1 (Occurrents): Event, EventChain-as-process, Action
  - Level 2 (Records/ICEs): EventChain-record, Concept, Relation
  - Explicit identity and dependence axioms
- **Location**: 03_ontological_analysis.tex (new subsection 3.2.5)

### W3. Experimental gaps: small scale, no concurrency, no adversarial
- **Action**: 
  - Add E4d: multi-agent concurrency tests (50 cases, 3-10 agents)
  - Add E4e: adversarial tampering tests (32 cases, already in appendix C)
  - Add scale-up projection: 10^5-10^6 events feasibility analysis
  - Add comparative baseline: nanopublications + PROV-O governance task comparison
- **Location**: 05_empirical_validation.tex

### W4. Limited precondition testing, no comparative baselines
- **Action**: Expand E4 to 91+ cases; add E12 comparative governance evaluation
- **Location**: 05_empirical_validation.tex

### W5. Strong claims without systematic survey
- **Action**: Weaken "first system" to "to our knowledge, no existing deployed system combines all four"; add explicit counter-example argument for CIDOC CRM, SEO, nanopublications, PROV-O
- **Location**: 01_introduction.tex, 02_related_work.tex

### W6. Placeholder references, partial interoperability
- **Action**: Replace anonymous references with real ones; strengthen PROV-O/SHACL mapping with concrete specifications and loss analysis
- **Location**: references.bib, appendix_a.tex, appendix_b.tex

### W7. Missing related work: Git-native systems
- **Action**: Already present in 02_related_work.tex (RO-Crate, DataLad, TerminusDB) - strengthen and expand

### W8. Missing institutional semantics
- **Action**: Already present in 02_related_work.tex (Searle) - strengthen connection to precondition system

## Reviewer Questions to Address

### Q1. Formalize precondition language and δ/γ derivation functions
- **Action**: Add formal syntax/semantics for precondition language; prove decidability; prove termination and predictability (not Turing-complete, stratified)
- **Location**: 04_architecture.tex (new subsection 4.3.1)

### Q2. Exact fork and merge rules; CRDT design for Phase 3
- **Action**: Formalize fork/merge rules; clarify Theorem 7 applies only to optional LWW-Set; describe concrete CRDT design for Phase 3
- **Location**: 04_architecture.tex (Section 4.4)

### Q3. Machine-readable PROV-O/SHACL mapping with loss analysis
- **Action**: Complete Appendix A with full Turtle; add loss analysis table
- **Location**: appendix_a.tex

### Q4. Actor identity management; Linked Data Proofs; equivocation prevention
- **Action**: Expand trust model with detailed Phase 3 design
- **Location**: 04_architecture.tex (Section 4.5), 06_discussion.tex

### Q5. Clean two-level account (occurrents vs records)
- **Action**: New subsection in Section 3 with explicit axioms
- **Location**: 03_ontological_analysis.tex

### Q6. OWL ontology interoperability
- **Action**: Add OWL export/import discussion; describe bridge between event-derived status and class/property axioms
- **Location**: 06_discussion.tex (FW1), appendix_f.tex

### Q7. Extend empirical study
- **Action**: Add multi-agent concurrency, adversarial, scale-up; report coverage and failure modes
- **Location**: 05_empirical_validation.tex

### Q8. Formal semantics for relation lifecycle, UFO relators
- **Action**: Formalize relation creation/revocation, role constraints, temporal scoping
- **Location**: 03_ontological_analysis.tex (Section 3.2.4), 04_architecture.tex (Section 4.1.1)

## Execution Order

### Stage 1: Core Revisions (Parallel)
- Revise 01_introduction.tex (weaken claims, add counter-examples)
- Revise 03_ontological_analysis.tex (two-level account, relation lifecycle)
- Revise 04_architecture.tex (precondition formalization, CRDT scoping, trust model)

### Stage 2: Empirical & Discussion (Parallel, depends on Stage 1)
- Revise 05_empirical_validation.tex (comparative baselines, concurrency, scale-up)
- Revise 06_discussion.tex (address all 8 questions, strengthen limitations)

### Stage 3: Integration (Sequential)
- Revise 02_related_work.tex (strengthen systematic comparison)
- Revise 07_conclusion.tex (reflect all changes)
- Revise abstract.tex
- Fix references.bib
- Update appendices

### Stage 4: Polish & Compile
- Apply research-paper-refiner skill
- Compile LaTeX and verify
