# ADL Lite Paper Restructuring Plan

## Problem Diagnosis

The paper has been revised to answer reviewer questions, but many additions feel "forced" into sections where they don't naturally belong. The paper reads like a patchwork rather than a coherent narrative.

## Major Structural Issues

### 1. Section 4 (Architecture) — Fragmented Flow

**Current order:**
- 4.1 Document Model → forced "Guidance: near-duplicate" paragraph → 4.2 EventChain → 4.3 Crypto → 4.4 Precondition Language → forced "Expressivity catalog" table → 4.5 Action Executor → 4.6 Consensus → 4.7 Formal Semantics → 4.9 CRDT (with forced "Interaction with hash chains") → 4.10 Event Frameworks → 4.11 Trust Model (with forced "Undetectable tamper scenarios")

**Problem:** The expressivity catalog sits between precondition language and Action Executor. The near-duplicate guidance is a standalone paragraph. The undetectable scenarios are inserted mid-trust-assumptions. The CRDT interaction is an afterthought paragraph.

**New order:**
- 4.1 Document Model (integrate near-duplicate guidance into L3 description naturally)
- 4.2 EventChain Core
- 4.3 Cryptographic Integrity
- 4.4 Precondition Language (with expressivity as a subsection)
- 4.5 Action Executor and Consensus
- 4.6 Formal Derivation Semantics
- 4.7 Comparison with Event Frameworks
- 4.8 Trust Model and Security Boundaries (integrate undetectable scenarios as part of threat model)
- 4.9 Optional CRDT Merge (integrate hash chain interaction as part of the design)

### 2. Section 5 (Empirical) — Jumbled Narrative

**Current order:** E1 → E2 → E3 → E4 → E6 → AML case study → E6b → E13-16 → E5 → adversarial → E17 → E19 → summary → comparative eval

**Problem:** The flow jumps from real experiments to planned studies to conceptual comparisons. The AML case study is inserted after E6, breaking the scalability narrative. E5 (planned) comes after boundary tests. Adversarial comes after E5.

**New order:**
- 5.1 Validation Strategy
- 5.2 Core Correctness (E1-E4)
- 5.3 Scalability (E6, E6b)
- 5.4 Boundary and Stress (E13-E16)
- 5.5 Domain Applicability (AML case study + E5 future design)
- 5.6 Multi-Agent Simulation (E17)
- 5.7 Comparative Governance (E19, E12)
- 5.8 Adversarial Trials (E4e)
- 5.9 Summary

### 3. Section 6 (Discussion) — "Addressing Reviewer Questions" Anti-Pattern

**Problem:** This entire subsection is a list of reviewer questions with answers. It reads like a response letter, not a paper discussion.

**Solution:** Remove the entire subsection. Distribute content:
- Q1 (precondition/formalization) → Section 4.4
- Q2 (fork/merge) → Section 4.6
- Q3 (PROV-O/SHACL) → Section 4.1 or 7.2
- Q4 (actor identity) → Section 4.8
- Q5 (two-level account) → Section 3
- Q6 (OWL interoperability) → Section 6.2 or 7.2
- Q7 (empirical extension) → Section 5 intro
- Q8 (relation lifecycle) → Section 3.3

### 4. Section 7 (Conclusion) — Defensive "Response to Review" Paragraph

**Problem:** The last paragraph explicitly says "This revision addresses reviewer concerns..." which is a cover letter convention, not a conclusion convention.

**Solution:** Remove it entirely.

## Minor Polish Issues

1. Introduction "operational ontology" definition — the expanded contrast with OBO and executable ontologies is too long and defensive. Trim to one clear contrast.
2. Related Work — the SafeHarness/PRISM paragraph comes after the main table, which is awkward. Integrate into the table or move to a subsection.
3. The paper mentions "Phase 1.5" in many places without clear explanation. Consolidate Phase 1.5 discussion.
