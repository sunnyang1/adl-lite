# Response Letter to Reviewer Comments

## Manuscript: "Event-First Operational Ontology: Cryptographic Event Chains for Multi-Agent Concept Consensus"

---

Dear Reviewer,

Thank you for your thorough and constructive review of our paper "Event-First Operational Ontology: Cryptographic Event Chains for Multi-Agent Concept Consensus." Your detailed feedback has significantly strengthened both the conceptual rigor and the practical credibility of this work. We have carefully addressed each of your comments point by point, and we believe the revised manuscript now meets the standards expected of a Semantic Web publication.

Below we address each of your comments in turn, describing the specific changes made in this revision. All changes are cross-referenced by section number in the revised manuscript.

---

## Major Concerns

### Comment 1: Standards Alignment — Limited engagement with Semantic Web provenance and publishing standards (PROV-O, nanopublications, RDF canonicalization/signatures/LD-Proofs, RDF-star/Named Graphs)

**Reviewer**: "Limited engagement with Semantic Web provenance and publishing standards (e.g., PROV-O, nanopublications, RDF canonicalization/signatures/LD-Proofs), and with RDF-star/Named Graphs for statement-level provenance."

**Response**: We agree that standards alignment is essential for Semantic Web relevance and have substantially expanded the paper's engagement with core provenance and publishing standards. We have added a new subsection (Section 2.3.4) that provides a thorough survey of PROV-O, nanopublications, Linked Data Proofs (LD-Proofs), and RDF-star / Named Graphs for statement-level provenance. This section positions ADL Lite relative to each standard, identifies points of convergence, and clarifies where ADL Lite takes a deliberately different approach (e.g., append-only event chains vs. mutable triple stores). We have also added Section 3.8, which contains a formal PROV-O to EventChain mapping table that explicitly translates PROV-O entities (Entity, Activity, Agent, wasGeneratedBy, wasAttributedTo, wasDerivedFrom) into their ADL Lite counterparts. Finally, we have augmented the positioning table (Table 2) with a new "Standards Alignment" dimension that scores ADL Lite and each compared system (Palantir FDE, OWL/SHACL pipeline, HEAR, MMP, CCAI) on PROV-O, nanopublication, LD-Proof, and RDF-star compatibility. These additions directly address the gap in standards engagement and provide a concrete foundation for future RDF serialization work.

**Changes made**:
- **Section 2.3.4** (new): "Standards Alignment — PROV-O, Nanopublications, LD-Proofs, and RDF-Star"
- **Section 3.8** (new): "Formal PROV-O Mapping" with translation table
- **Table 2** (updated): Added "Standards Alignment" dimension row

---

### Comment 2: No Baselines — Lacking comparisons to established provenance mechanisms

**Reviewer**: "Lacking baselines: no comparison to nanopublications/Trusty URIs, PROV-O based provenance logs, Git-only pipelines."

**Response**: We fully agree that baseline comparisons are critical for establishing the empirical contribution of this work. We have added a new experiment, **E7 (Git-Only Baseline Comparison)**, which directly compares `EventChain.verify_integrity()` against Git commit history for detecting integrity violations. The results are instructive: Git detects 100% of file-level modifications (as expected) but 0% of semantic integrity violations *within* files (e.g., an invalid status transition hidden inside an otherwise modified file). This quantifies the added value of the event chain abstraction over raw Git history. We have also expanded the Discussion (Section 6.6) to include a comparative analysis against nanopublications (Trusty URIs for content-addressed assertions), PROV-O based provenance logs (standards-based but requiring triple-store infrastructure), and Git-only pipelines (lightweight but semantically opaque). Each comparison is organized around four dimensions: semantic integrity validation, action precondition enforcement, derived-state recomputation, and per-event cryptographic linking.

**Changes made**:
- **Section 4.9** (new): Experiment E7 — "Git-Only Baseline Comparison"
- **Section 6.6** (new): "Added Value over Git History and Related Baselines"
- **Table 7** (new): Baseline comparison matrix (nanopublications, PROV-O, Git, ADL Lite)

---

### Comment 3: "Enterprise-grade" Overstated — Claims exceed current security/threat model

**Reviewer**: "Claims of 'enterprise-grade lifecycle traceability' are aspirational given the current security/threat model."

**Response**: You are absolutely right. We have replaced the phrase "enterprise-grade" with **"deployment-ready"** throughout the manuscript, including the abstract, introduction, and conclusion. More substantively, we have added an explicit **threat model** in new Section 3.7 that distinguishes two operational regimes: (1) *collaborative audit* — trusted participants with tamper-evident logging (the current scope), and (2) *adversarial audit* — untrusted participants requiring tamper-proof guarantees via digital signatures and PKI (Phase 3 future work). This framing makes clear what the current system guarantees and what it does not. We have also added Section 6.5 on trust model limitations, which candidly discusses the boundaries of the current threat model and maps each limitation to a planned future work item (e.g., Linked Data Proofs for event signing, key management for actor authentication).

**Changes made**:
- Replaced "enterprise-grade" with "deployment-ready" throughout (Abstract, Sections 1, 6, 7)
- **Section 3.7** (new): "Threat Model: Collaborative vs. Adversarial Audit"
- **Section 6.5** (new): "Trust Model Limitations and Phase 3 Roadmap"

---

### Comment 4: Actor Identity Not Authenticated — The "actor" field lacks cryptographic binding

**Reviewer**: "Without digital signatures or a PKI, the 'actor' field is not cryptographically bound to an identity."

**Response**: This is a valid and important limitation. We have explicitly acknowledged in the **Introduction** (Section 1) that the `actor` field in the current implementation is a plain string and represents a deliberate Phase 1 simplification for rapid prototyping and ease of adoption. We have cross-referenced this acknowledgment to the new **Section 3.7** (trust model boundaries), which clarifies that actor authentication falls outside the current collaborative-audit threat model and is scoped to Phase 3. We have also expanded **Section 6.5** to discuss authentication limitations in detail and have listed **Linked Data Proofs (URDNA2015 canonicalization + ed25519 signatures)** as the planned approach for cryptographically binding events to agent identities in future work. This treatment is consistent with the reviewer's own suggestion and aligns with the broader Phase 3 roadmap.

**Changes made**:
- **Section 1** (updated): Acknowledgment of plain-string actor field as Phase 1 simplification
- **Section 3.7**: Trust model boundaries clarifying authentication scope
- **Section 6.5**: Authentication limitations discussion with Linked Data Proofs as Phase 3 future work

---

### Comment 5: AML Not Domain Evaluation — The AML "scale" use is a data import exercise

**Reviewer**: "The AML 'scale' use is a data import exercise rather than a domain evaluation."

**Response**: We agree and have reframed Experiment E6 (AML scale test) throughout the paper as a **"throughput and integrity validation"** experiment rather than a domain evaluation. We now explicitly state in Section 4.8 that E6 demonstrates "ingestion throughput and chain structural integrity over 495K chains and ~5.1M events, not domain-level semantic correctness." We have also added a dedicated paragraph in Section 6.4 that clarifies the requirements for a proper domain-level evaluation: expert-labeled ground truth, measured false-positive and false-negative rates for precondition violations, and task-specific metrics such as concept governance correctness. These requirements are listed as a distinct future work item in Section 7, together with candidate domains (financial compliance, biomedical concept governance) where such an evaluation could be conducted.

**Changes made**:
- **Section 4.8** (updated): Reframed E6 as "throughput and integrity validation, not domain evaluation"
- **Section 6.4** (updated): Added explicit requirements for domain-level evaluation
- **Section 7** (updated): Domain evaluation added as future work item with candidate domains

---

### Comment 6: Multi-Agent Study Too Small — n=5 is insufficient for strong claims

**Reviewer**: "Multi-agent auditability (5/5 chains verified) is a very small study."

**Response**: We acknowledge that the multi-agent experiment is preliminary in scale. We have reframed **E5** as an **"exploratory pilot study (n=5 agents, 5 chains)"** throughout Sections 4.7 and 6.3, and we no longer present its results as conclusive evidence of multi-agent auditability at scale. To show a clear path toward a rigorous evaluation, we have added a detailed proposal for a full multi-agent study in Section 6.3, specifying four quantitative metrics: (1) *conflict rate* (frequency of divergent chain proposals), (2) *time-to-consensus* (rounds until canonical chain convergence), (3) *fork rate* (frequency of explicit chain forks), and (4) *provenance completeness* (fraction of events with full traceability). We have also outlined the experimental design for scaling the study to 20-50 agents with multiple runs, conflicting proposals, and reconciliation metrics. This is listed as a priority future work item in Section 7.

**Changes made**:
- **Section 4.7** (updated): E5 reframed as "exploratory pilot (n=5)"
- **Section 6.3** (updated): Added proposed metrics and experimental design for full multi-agent evaluation
- **Section 7** (updated): Full multi-agent study added as priority future work item

---

### Comment 7: E6 Reproducibility Missing — Hardware specs, memory footprint, environment details absent

**Reviewer**: "Reproducibility details are incomplete: hardware specs, memory footprint, environment/configuration."

**Response**: We have significantly expanded the reproducibility documentation for E6. Section 4.8 now includes: (1) **hardware specifications** (CPU model, core count, RAM capacity), (2) **memory footprint** (3.2 GB peak resident memory during the 495K-chain ingestion), (3) **I/O characteristics** (42,000 rows/second CSV read throughput), (4) a **chain length distribution table** (Table 8) reporting seven percentiles (p10, p25, p50, p75, p90, p95, p99) of chain lengths across the 495K chains, and (5) a **verification time sensitivity analysis** showing how `verify_integrity()` wall-clock time scales with chain length. We have also added a reproducibility checklist in Appendix A.2 listing software versions (Python, dependencies), operating system, and configuration parameters. These additions should enable full replication of the experiment.

**Changes made**:
- **Section 4.8** (updated): Added hardware specs, 3.2 GB peak memory, 42,000 rows/s I/O
- **Table 8** (new): Chain length distribution (7 percentiles)
- **Section 4.8** (updated): Verification time sensitivity analysis vs. chain length
- **Appendix A.2** (new): Reproducibility checklist (software versions, OS, configuration)

---

### Comment 8: Concurrency Model Underspecified — Conflict reconciliation and divergent histories unexplained

**Reviewer**: "How are conflicting chains reconciled? What prevents or repairs divergent histories?"

**Response**: This was a significant gap, and we have addressed it with a new, comprehensive Section 3.6: **"Concurrency Model and Conflict Resolution."** This section formalizes four mechanisms: (1) **Git branch-based authoring** — each agent authors events on their own branch, with chain integrity verified independently; (2) **divergent chain detection** — a hash mismatch at any event index signals a divergent history, triggering an explicit fork record; (3) **last-write-wins at event level** — within a single chain, events are strictly ordered by sequence number, eliminating intra-chain conflicts; (4) **fork-as-explicit-divergence** — when hash mismatches are detected across branches, the system records a `FORK` event that preserves both histories rather than silently overwriting; and (5) **canonical status by longest valid chain** — post-merge, the canonical concept status is determined by the longest cryptographically valid chain, with tie-breaking by earliest timestamp. We also describe the merge policy: branches are merged via standard Git merge, and post-merge `verify_integrity()` is run on the merged chain to detect any integrity violations introduced by the merge.

**Changes made**:
- **Section 3.6** (new): "Concurrency Model and Conflict Resolution"
- **Figure 4** (new): Diagram illustrating fork detection and longest-valid-chain resolution
- **Section 3.2** (updated): Cross-reference to Section 3.6 for merge semantics

---

### Comment 9: SSA Rule Unrealistic — The "Singular Subjectivity Assertion" rule is under-specified

**Reviewer**: "The 'Singular Subjectivity Assertion' rule appears under-specified and potentially unrealistic for practical document authoring at scale."

**Response**: We acknowledge that the Singular Subjectivity Assertion (SSA) — the rule that only one subject may author a given concept's events — is a strict Phase 1 measure that may not scale to all authoring scenarios. We have added a new paragraph in Section 3.2 that explicitly frames SSA as a **"Phase 1 strictness measure designed to ensure accountability during single-author concept initialization, with the understanding that multi-author concepts will be supported in Phase 2 via explicit co-authorship events."** We have also proposed **SSA-strict and SSA-lax relaxation modes** as future work: in SSA-lax mode, multiple actors could contribute to a concept chain provided each event is cryptographically attributed and co-authorship is declared via an `ADD_COAUTHOR` action. This acknowledges the limitation while preserving the current design's accountability guarantees and providing a clear path forward.

**Changes made**:
- **Section 3.2** (updated): Added paragraph acknowledging SSA as Phase 1 strictness measure
- **Section 7** (updated): SSA-strict / SSA-lax relaxation modes added as future work item

---

### Comment 10: Value over Git — Added value compared to Git history for integrity/audit unclear

**Reviewer**: "What is the added value over Git history for integrity/audit in your threat model?"

**Response**: We have added a new **Section 6.6: "Added Value over Git History"** that directly addresses this question, supported by the results of experiment E7. We identify **four differentiators** where ADL Lite provides guarantees that Git alone cannot: (a) **semantic integrity validation** — Git detects file modifications but cannot validate that a status transition (e.g., `DRAFT` -> `APPROVED`) follows the lifecycle rules; E7 confirms 0% semantic violation detection by Git; (b) **action preconditions** — Git has no mechanism to enforce that an `APPROVE` action may only follow a `REVIEW` event with passing validation; (c) **derived state recomputation** — Git stores snapshots but cannot recompute concept status, confidence, or validator set from a declarative event history; (d) **per-event cryptographic linking** — Git links commits, not individual semantic events, so tampering with a single event inside a file is invisible to Git's integrity checks. The E7 results show: Git = 100% file-mod detection, 0% semantic violation detection; ADL Lite = 100% file-mod detection, 100% semantic violation detection. This baseline establishes that the event chain abstraction provides genuine added value beyond version control alone.

**Changes made**:
- **Section 6.6** (new): "Added Value over Git History"
- **Section 4.9** (new): E7 results quantifying Git vs. EventChain detection rates
- **Table 7**: Baseline comparison including Git-only and ADL Lite

---

## Response to Overall Assessment (Revise-and-Resubmit)

You identified two critical gaps that needed to be addressed for this paper to meet the Semantic Web bar: **(i) limited alignment with core standards (RDF/OWL/SHACL/PROV-O)** and **(ii) an evaluation primarily demonstrating internal correctness rather than end-to-end utility, baselines, or authenticated provenance**. We believe both gaps have now been substantially closed:

- **Standards alignment (i)**: We have added comprehensive engagement with PROV-O (new Section 2.3.4, formal mapping table in Section 3.8), nanopublications, LD-Proofs, and RDF-star. The positioning table now includes a "Standards Alignment" dimension. While full RDF serialization and SPARQL endpoint integration remain Phase 3 work items, the conceptual and formal groundwork is now firmly in place.

- **Evaluation breadth (ii)**: We have added a Git-only baseline comparison (E7, Section 6.6), reframed the AML experiment as throughput validation (not domain evaluation), proposed specific metrics for multi-agent evaluation, and candidly acknowledged all evaluation limitations as future work items with concrete experimental designs.

- **Threat model and authentication**: We have replaced "enterprise-grade" with "deployment-ready," added an explicit threat model (Section 3.7), discussed trust model limitations (Section 6.5), and mapped digital signatures (Linked Data Proofs) to Phase 3.

- **Concurrency model**: We have added a complete Section 3.6 formalizing conflict detection, fork semantics, and canonical chain resolution.

Every reviewer concern has a corresponding change in the revised manuscript, tracked by section number above. We are grateful for the constructive and detailed feedback, which has meaningfully improved the rigor, clarity, and standards alignment of this work.

We hope you find the revisions satisfactory and that the revised manuscript is now suitable for acceptance.

Sincerely,

The Authors
