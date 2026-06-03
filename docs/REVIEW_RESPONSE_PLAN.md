# ADL Lite — Reviewer Response & Revision Plan

**Review Target**: `paper_ao/` (Applied Ontology submission)
**Review Date**: 2026-06-03
**Reviewer Verdict**: **Recommend substantial revision** — promising work, genuine originality, but formal rigor, empirical scope, and scholarly completeness fall short.

---

## Quantitative State Assessment

| Item | Current | Target | Gap |
|------|---------|--------|-----|
| References (total) | 112 | ~80 real | 61 placeholders (54% fake) |
| Real citations | 51 | 80+ | 29+ to replace/add |
| Theorems with proofs | 6 (+ appendix E) | 6 (adequate) | Clarify δ/γ/WF definitions in body |
| CRDT concurrency semantics | Sketch only | Formal CRDT merge rules | Full subsection needed |
| Adversarial test cases | 10 (E1 only) | 50+ across 6 attack classes | Appendix C underspecified |
| Comparative eval against baselines | None | Nanopublications + PROV-O | New experiment needed |
| Authentication/threat model | Deferred to Phase 3 | Explicit threat model + mitigation | New subsection |
| Performance reporting detail | 31,100 evt/s, no HW | Hardware specs + latency decomposition | Enhance E6 section |

---

## P0 — Must Fix for Acceptance (Blocking)

### P0.1 🔴 BFO GDC Category Clarification
**Reviewer concern**: "Concept as GDC depending on an EventChain (occurrent) is ontologically questionable."

**Current state**: The paper already partially addresses this in §3.4.1 (lines 117–121):
> "A Concept depends on the *information artifact* (the serialized EventChain record) rather than on the occurrent."

But the cross-mapping table (Table 1) and §3.2.2 still say "Depends on chain for identity" without clarifying that the chain is treated as an **ICE (Information Content Entity)**, not an occurrent.

**Required actions**:
- [ ] **§3.2.2 (Concept as GDC)**: Add explicit statement that the Concept depends on EventChain *as ICE bearer*, not as occurrent. Formalize: Concept →GDC→ ICE(EventChain).
- [ ] **Table 1 (Cross-mapping)**: Change Note column from "Depends on chain for identity" to "Depends on EventChain as information content entity (ICE bearer)"
- [ ] **§3.4.1**: Strengthen the existing argument with a formal dependency diagram
- [ ] **Add a footnote**: "In BFO 2020, an ICE is a GDC concretized by some material bearer (the Markdown file). The EventChain qua ICE is the continuant; the events occurring constitute the occurrent process."

**Files**: `sections/03_ontological_analysis.tex` (subsections 3.2.2, 3.4.1, Table 1)

---

### P0.2 🔴 Formal Semantics: Expose δ, γ, WF in Main Body
**Reviewer concern**: "The key formal components (δ, γ, WF, fork/confluence) and theorems are not available for scrutiny in detail."

**Current state**: These ARE defined in §4.6 with full LaTeX and 6 theorems. Appendix E has complete proof sketches (257 lines). The reviewer may have received an earlier version without these.

**Required actions**:
- [ ] **Verify**: §4.6 is included in the submitted version
- [ ] **§4.6**: Add explicit notation definitions before theorems (already done — verify completeness)
- [ ] **Add Corollary**: Status–Confidence Consistency (γ ≥ 0.5 when validated) — technically already present as Theorem 6
- [ ] **§4.6.4**: Expand fork/confluence from 3-line sketch to full semantics with:
  - Definition of fork as a function Fork(C, agent) → (C_fork, C_child)
  - Confluence lemma: ∀C, Fork(C, a₁); Fork(C, a₂) both produce valid fork events
  - Independence: derived state of C_child ⊥ derived state of C_fork

**Files**: `sections/04_architecture.tex` (subsection 4.6, 4.6.4)

---

### P0.3 🔴 Replace 61 Placeholder Citations
**Reviewer concern**: "Numerous placeholder citations ('Placeholder [1965]', '?')"

**Current state**: `references.bib` has 112 entries total. **61 are placeholders** (`ref1`–`ref61` marked "Replace with actual bibliographic data"). That's 54% fake.

**Required actions**:
- [ ] **Batch replace**: Use CrossRef/DBLP/Google Scholar to find real citations for each placeholder
- [ ] **Map ref1–ref61 to actual papers**: Each `\cite{refN}` in the text needs tracing to determine topic, then substitution
- [ ] **Remove unused placeholders**: If some refs are not cited in text, delete them
- [ ] **Add missing related work citations** (see P0.5)

**Files**: `references.bib` (61 entries), all `.tex` files that `\cite{refN}`

---

### P0.4 🔴 Add Authentication & Threat Model Section
**Reviewer concern**: "Absence of authenticated identities (digital signatures) in current phase leaves a significant trust gap."

**Current state**: Trust model is deferred to Phase 3. Paper acknowledges this as a limitation.

**Required actions**:
- [ ] **New §4.8 (or §3.7 in paper_v3 style): "Trust Model and Security Boundaries"**
  - Define threat model explicitly: what attacker capabilities are assumed
  - Trust assumptions: Git history integrity, actor identity verification, event non-repudiation
  - Current phase: cryptographic hash chain ensures *content integrity* but not *actor identity*
  - Planned Phase 3: Linked Data Proofs (W3C), Ed25519 signatures on events, W3C DID integration
  - Explicitly state: hash chains prevent tampering but do not prevent impersonation — this is a known gap
- [ ] **§6.3 (Limitations)**: Already mentions this — ensure consistency with new section
- [ ] **Add to Table 1**: Row for "Signature" or "Authentication" mapped to ICE

**Files**: `sections/04_architecture.tex` (new subsection), `sections/06_discussion.tex`

---

### P0.5 🔴 Add Missing Related Work
**Reviewer concern**: "Limited engagement with OBO/OntoBio, RO-Crate, FAIR Digital Objects, blockchain-based provenance."

**Required actions for §2 (Related Work)**:
- [ ] **§2.2.x**: OBO Foundry and OntoBio — ontology change management, versioning practices (e.g., OORT, OntoFox)
- [ ] **§2.3.x**: RO-Crate and FAIR Digital Objects — research object packaging with provenance
- [ ] **§2.3.x**: Blockchain-based provenance (e.g., Ethereum + IPFS, Hyperledger for supply chain)
- [ ] **§2.3.x**: Git signed-commit workflows as close operational analogs
- [ ] **§2.4.x**: PLUGMEM (arXiv:2603.03296) — complementary memory abstraction; ADL Lite provides governance layer

**Files**: `sections/02_related_work.tex`, `references.bib`

---

## P1 — Important to Strengthen

### P1.1 🟠 CRDT & Fork/Confluence Semantics
**Reviewer concern**: "Fork/confluence and concurrency semantics are only sketched; last-write-wins style."

**Required actions**:
- [ ] **§4.6.4**: Replace current sketch with formal CRDT semantics:
  - Define LWW-Element-Set for confidence aggregation
  - Define merge function Merge(C₁, C₂) for concurrent chains
  - State convergence: If C₁ and C₂ are concurrent branches, Merge(C₁, C₂) yields a well-formed chain with δ deterministic
- [ ] **Add Theorem 7 (CRDT Convergence)**: For any concurrent branches B₁, B₂, Merge(LWW(B₁), LWW(B₂)) = Merge(LWW(B₂), LWW(B₁))
- [ ] **Clarify**: ADL Lite does not enforce CRDT — it *supports* CRDT merge as an optional resolution strategy. Fork/deprecate is the primary mechanism.

**Files**: `sections/04_architecture.tex`, `sections/appendix_e.tex`

---

### P1.2 🟠 Adversarial Evaluation Suite
**Reviewer concern**: "Only 10 corrupted chains; no adversarial tamper tests, replay attacks, or clock skew."

**Required actions**:
- [ ] **Expand Appendix C**: From placeholder to full adversarial test specification
- [ ] **Add attack classes**:
  1. Content tampering (existing)
  2. Event reordering (existing)
  3. Event deletion (existing)
  4. Event replay across chains (existing)
  5. Timestamp manipulation (clock skew)
  6. Concurrent fork conflict (two agents forking simultaneously)
  7. Genesis event replacement
  8. Hash collision attempt (birthday attack on SHA-256 — theoretical)
- [ ] **Run actual tests via pytest** and report results in §5
- [ ] **Table of results**: Attack class, detection rate, false positive rate

**Files**: `sections/appendix_c.tex`, `sections/05_empirical_validation.tex`

---

### P1.3 🟠 Comparative Evaluation (Nanopubs + PROV-O)
**Reviewer concern**: "No comparative evaluation against established provenance solutions."

**Required actions**:
- [ ] **New §5.7 (or E12): "Comparative Governance Evaluation"**
  - **Task suite**: Acceptance/retraction workflow, audit query, consensus threshold
  - **Baselines**: (a) Nanopublications with Trusty URIs, (b) PROV-O pipeline with RDF canonicalization
  - **Metrics**: Audit query time (O(1) per nanopub vs O(n) per chain), verification cost, provenance completeness
  - **Acknowledge**: ADL Lite is not directly comparable on authentication (no signatures yet) but shows advantage in multi-event lifecycle view
- [ ] **PROV-O round-tripping**: Demonstrate EventChain → PROV-O export (already in Appendix A) and PROV-O → EventChain import

**Files**: New section in `sections/05_empirical_validation.tex`, `sections/appendix_a.tex`

---

### P1.4 🟠 Performance Reporting Detail
**Reviewer concern**: "31,100 events/s lacks hardware specs, workloads, and baselines."

**Required actions**:
- [ ] **§5.5**: Add hardware specs (CPU model, RAM, OS, Python version)
- [ ] **Latency decomposition**: CSV parsing time vs. event materialization vs. SHA-256 hashing vs. chain verification
- [ ] **Baseline comparison**: Plain CSV write vs. ADL Lite import (same data)

**Files**: `sections/05_empirical_validation.tex`

---

## P2 — Nice to Have

### P2.1 🟡 Mechanized Proofs
**Reviewer suggestion**: "Isabelle/Coq/TLA+ or model checking."

- [ ] Add footnote: "A TLA+ specification of the fork/confluence semantics is available in the supplementary materials."
- [ ] Optional: Create TLA+ spec for EventChain state machine
- [ ] Priority: Low — proofs in Appendix E are adequate for acceptance. Mechanized proofs strengthen but not required.

### P2.2 🟡 PLUGMEM Integration Demo
**Reviewer suggestion**: "Demonstrating such integration would show practical synergy."

- [ ] Add paragraph in §6 (Discussion): How ADL Lite's governance layer could serve as a substrate for PLUGMEM's memory abstraction
- [ ] Conceptual diagram: PLUGMEM (memory/retrieval) → ADL Lite (lifecycle governance) → Agent consensus

### P2.3 🟡 SHACL Profile Coverage Analysis
- [ ] Appendix B: Add coverage analysis table — which L3 relation types are covered by which SHACL shapes
- [ ] Mention constraint language expressiveness relative to SHACL Core vs. SHACL-SPARQL

---

## Reviewer Questions — Response Draft

### Q1: BFO GDC vs EventChain dependence

> **Answer**: The Concept depends on the EventChain *as Information Content Entity (ICE)* — a generically dependent continuant in BFO 2020 that is concretized by the Markdown/YAML record. The events occurring are occurrences (perdurants). The chain qua ICE is a continuant whose temporal parts are the discrete states of the record at each commit. We will clarify this explicitly in §3.2.2 and add a formal dependency: `Concept →GDC→ ICE(EventChain_record)`.

### Q2: Formal definitions and proofs

> **Answer**: δ, γ, and WF are defined in §4.6 of the submitted manuscript (which was included). Proof sketches for all 6 theorems are in Appendix E. We will verify these were present in the reviewed version and will make definitions more prominent by relocating the formal notation table to the beginning of §4.6.

### Q3: Threat model and authentication

> **Answer**: Current threat model assumes: (1) trusted Git repository (signed commits verify committer identity), (2) no adversarial actor compromise. Hash chains ensure content integrity but not actor identity — this is a Phase 3 item. Planned: W3C Linked Data Proofs (Ed25519 signatures) on each event, with key discovery via DIDs. Clock skew is handled by cryptographic linkage (prev_hash), not timestamp ordering.

### Q4: Concurrent fork resolution

> **Answer**: ADL Lite does not enforce a single resolution strategy — it provides infrastructure. Fork → deprecate is the primary mechanism. For concurrent forks, we propose optional CRDT LWW-Element-Set merge semantics for confidence aggregation (to be formalized in revision). Fork resolution is inherently social: agents must negotiate which fork to adopt.

### Q5: OWL/SHACL/PROV interop

> **Answer**: EventChain → PROV-O export is demonstrated in Appendix A. PROV-O → EventChain import is planned. SHACL shapes for L3 relation validation are in Appendix B. Full OWL translation requires mapping Event types to OWL class expressions — this is feasible but beyond current scope. We will add a round-tripping example in the revision.

### Q6: Comparative evaluation

> **Answer**: This is our primary P1 action item. We will design a governance task suite (acceptance/retraction, audit queries, consensus thresholds) and compare ADL Lite against (a) nanopubs with Trusty URIs and (b) a PROV-O pipeline. We acknowledge ADL Lite currently lacks signatures — we will report both with-signature (projected Phase 3) and without-signature results.

### Q7: Genesis event immutability in Git

> **Answer**: The genesis event's hash is computed over its content including concept_id, actor, and timestamp. In Git workflows, rebase/force-push can rewrite history but: (a) signed Git commits provide tamper-evidence via GPG signatures, (b) ADL Lite's chain verification detects any modification because the hash chain would break, (c) the authoritative chain is determined by the consensus mechanism (agent quorum), not by Git HEAD. We will clarify this in the Trust Model section.

---

## Work Estimate

| Priority | Task | Est. Lines/Effort | Section(s) |
|----------|------|-------------------|------------|
| P0 | BFO GDC clarification | ~30 lines | §3.2.2, §3.4.1, Table 1 |
| P0 | Formal semantics exposure | ~20 lines | §4.6 |
| P0 | Replace placeholder citations | 61 entries | references.bib + all .tex |
| P0 | Authentication & threat model | ~80 lines | New §4.8, §6.3 |
| P0 | Missing related work | ~100 lines | §2.2–2.4, references.bib |
| P1 | CRDT fork semantics | ~60 lines | §4.6.4, Appendix E |
| P1 | Adversarial eval suite | ~80 lines + code | Appendix C, §5 |
| P1 | Comparative evaluation | ~100 lines + experiment | New §5.7 |
| P1 | Performance detail | ~20 lines | §5.5 |
| P2 | Mechanized proofs | — (optional) | Footnote |
| P2 | PLUGMEM integration | ~20 lines | §6 |
| P2 | SHACL coverage | ~15 lines | Appendix B |

**Total estimated new content**: ~450 lines of LaTeX text + 61 bibliography replacements + 1 new experiment.

---

## Revision Strategy

**Recommended approach** (2-pass revision):

### Pass 1: Structural & Scholarly (P0 items)
1. Fix BFO GDC alignment in §3
2. Clean up 61 placeholder citations → real refs
3. Expand Related Work (§2) with OBO, RO-Crate, FAIR DO, blockchain provenance, PLUGMEM
4. Add Trust Model & Threat Model section
5. Ensure §4.6 formal semantics is properly exposed

### Pass 2: Empirical & Evaluative (P1 items)
1. Add CRDT fork semantics to §4.6.4
2. Run and document adversarial test suite
3. Design and execute comparative evaluation (nanopubs + PROV-O)
4. Add hardware specs to E6 performance reporting
5. Draft responses to 7 reviewer questions

---

## References to Add (Preliminary List)

- OBO Foundry principles (Smith et al., 2007, *Nature Biotechnology*)
- RO-Crate (Soiland-Reyes et al., 2022, *Data Science*)
- FAIR Digital Objects (De Smedt et al., 2020)
- PLUGMEM (arXiv:2603.03296)
- Ontology change management in OBO (Groß et al., OORT)
- Linked Data Proofs (W3C, 2020)
- Content-addressed provenance (Trusty URIs → Kuhn & Dumontier, 2015)
- Merkle tree / transparency log (Certificate Transparency, RFC 6962)
