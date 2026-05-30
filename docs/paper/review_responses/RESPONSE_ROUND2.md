# Response Letter to Second-Round Reviewer Comments

## Manuscript: "Event-First Operational Ontology: Cryptographic Event Chains for Multi-Agent Concept Consensus" (Revised Version 2)

---

Dear Reviewer,

Thank you for your thorough and constructive second-round review of our revised manuscript. We are deeply grateful for the detailed feedback you provided in both rounds, which has been instrumental in strengthening the conceptual rigor, formal foundations, and standards alignment of this work.

In this second revision, we have addressed all remaining concerns through substantial new material: formal derivation semantics with algorithms, a tampering detection taxonomy, a comprehensive threat-model table, expanded related work covering CIDOC CRM and CRDTs, detailed per-operation latency measurements, and further comparisons with SHACL/ShEx. We believe the revised manuscript now fully addresses the gaps identified in your initial assessment and meets the standards expected of a Semantic Web publication.

Below we respond to each of your second-round comments in turn. All changes are cross-referenced by section number in the revised manuscript.

---

## New Comments (Second Round)

### Comment N1: Status Derivation Not Formalized

**Reviewer**: "How exactly is status/confidence derived? Please formalize the derivation functions, quorum thresholds, tie-breaking rules."

**Response**: We agree that the derivation semantics were described informally in the first revision and required full formalization. We have added a new **Section 3.9, "Formal Derivation Semantics,"** that completely specifies the status and confidence derivation functions. Status derivation depends exclusively on the most recent lifecycle event in the chain (last-write-wins), making it deterministic and O(1) after chain traversal. Confidence derivation aggregates all `VALIDATE` event payloads, applying a validator-count bonus that rewards broader consensus. We provide **Algorithm 1 (DeriveStatus)** and **Algorithm 2 (DeriveConfidence)** as pseudocode, together with a formal specification of quorum thresholds (minimum number of validators for each confidence level), fork resolution rules (longest-valid-chain wins, with timestamp tie-breaking), and the complete set of tie-breaking policies for edge cases. These algorithms are implemented in the `EventChain.derive_status()` and `EventChain.derive_confidence()` methods of the reference toolkit.

**Changes made**:
- **Section 3.9** (new): "Formal Derivation Semantics"
- **Algorithm 1** (new): `DeriveStatus(chain) -> (status, timestamp)`
- **Algorithm 2** (new): `DeriveConfidence(chain) -> (confidence, validator_set, quorum_met)`
- Section 3.9.1: Quorum thresholds and confidence levels (formal table)
- Section 3.9.2: Fork resolution and tie-breaking rules
- Cross-references added from Sections 3.2 and 3.5 to Section 3.9

---

### Comment N2: Tampering Detection Not Classified

**Reviewer**: "Which classes of tampering are detected at verification time?"

**Response**: This is an important gap in the first revision's security analysis. We have added a comprehensive **tampering detection taxonomy table** in **Section 3.7** that classifies all tampering attacks into nine distinct classes. Of these, five are detected natively by `verify_integrity()` without any signature infrastructure: (1) **content tampering** (modification of event payload data), (2) **link breakage** (alteration of the `prev_hash` pointer), (3) **deletion** (removal of events from the chain), (4) **reordering** (changing the sequence of events), and (5) **cross-chain injection** (inserting events from a different chain). Four additional attack classes require digital signatures for detection: (6) **equivocation** (an actor issues contradictory statements), (7) **replay** (reusing an event from one chain in another context), (8) **backdating** (fabricating an event with an earlier timestamp), and (9) **impersonation** (an actor forges another actor's events). The table explicitly marks which attacks are detected in Phase 1 (hash-chaining only) versus Phase 3 (with Linked Data Proofs), directly addressing the phased threat model introduced in the first revision.

**Changes made**:
- **Section 3.7** (updated): Tampering detection taxonomy table with 9 attack classes
- Section 3.7.1: Phase 1 detectable attacks (5 classes, hash-chain based)
- Section 3.7.2: Phase 3 detectable attacks (4 classes, signature based)
- Updated threat model cross-references linking each attack class to mitigation strategy

---

### Comment N4: Security Claims Not Summarized

**Reviewer**: "Security claims are not summarized in a single threat-model table."

**Response**: We have added **Table X in Section 6.5**, a comprehensive threat-model summary matrix that consolidates all security claims across both phases of the roadmap. The table is organized as a 9-capability by 3-adversary-class matrix. The three adversary classes are: (1) **Trusted Collaborator** (insiders with legitimate access), (2) **Curious Observer** (passive eavesdroppers without write access), and (3) **Active Adversary** (unauthorized actors attempting to modify or forge events). Each cell indicates whether the capability is provided in Phase 1 (current implementation), Phase 3 (future work with signatures), or not applicable. This makes the Phase 1 versus Phase 3 scope boundaries explicit and unambiguous, directly addressing your concern that the security posture was previously diffused across multiple sections.

**Changes made**:
- **Table X** (new): Threat-model matrix in Section 6.5 (9 capabilities x 3 adversary classes)
- Section 6.5 (updated): Expanded discussion with clear Phase 1 vs. Phase 3 scope delineation
- Cross-references from Sections 3.7 and 3.9 to Table X

---

### Comment N5: Missing Event-Centric Ontologies

**Reviewer**: "Limited discussion of CIDOC CRM, SEM/LODE."

**Response**: You are correct that the first revision's related work did not adequately cover event-centric ontologies from the cultural heritage and linked data publishing communities. We have added a new **Section 2.3.5, "Event-Centric Ontologies,"** that provides thorough coverage of three major families: (1) **CIDOC CRM** (ISO 21127), with particular attention to the E5 Event class and its relationship to our EventChain abstraction -- we discuss how CIDOC CRM's event-centric modeling of cultural heritage objects informed our design, while noting that ADL Lite focuses on operational governance events rather than historical events; (2) **SEM/LODE** (Simple Event Model / Linked Open Data Events), covering the lightweight event publishing patterns that align with our Markdown-native authoring philosophy; and (3) **RDF Stream Processing** (C-SPARQL and CQELS), discussing how continuous query models over event streams relate to our append-only chain model and how they might serve as integration targets in Phase 3. This addition positions ADL Lite within the broader landscape of event-based knowledge representation.

**Changes made**:
- **Section 2.3.5** (new): "Event-Centric Ontologies -- CIDOC CRM, SEM/LODE, and RDF Stream Processing"
- Subsection 2.3.5.1: CIDOC CRM (ISO 21127, E5 Event class) and comparison to EventChain
- Subsection 2.3.5.2: SEM/LODE lightweight event publishing
- Subsection 2.3.5.3: RDF Stream Processing (C-SPARQL, CQELS) and Phase 3 integration

---

### Comment N6: SHACL/ShEx Not Compared

**Reviewer**: "SHACL/ShEx are natural points of comparison for constraint validation."

**Response**: This is a perceptive observation. We have added a detailed **comparison table in Section 2.1.2** that evaluates the Comparator enum precondition system against SHACL and ShEx across nine dimensions: expressiveness, deployment dependencies, standardization status, graph-level constraints, scalar constraints, closed-world assumption, runtime overhead, tooling ecosystem, and Semantic Web integration path. The key insight is that the Comparator system trades expressiveness for **zero-dependency deployment** -- it requires no triple store, no RDF parser, and no external library, making it immediately usable in LLM-native and Markdown-native workflows. SHACL and ShEx offer far richer graph-level constraint expressiveness but require RDF infrastructure that contradicts the Phase 1 design goal of lightweight, pip-installable deployment. Crucially, we clarify that **SHACL shapes are planned as a Phase 3 governance layer**: the event chain provides the tamper-evident audit log, while SHACL validates the derived RDF graph, creating a complementary architecture rather than a competing one.

**Changes made**:
- **Section 2.1.2** (updated): Comparison table -- Comparator enum vs. SHACL vs. ShEx (9 dimensions)
- Section 2.1.2.1: Discussion of the expressiveness-deployment trade-off
- Section 2.1.2.2: Phase 3 SHACL integration plan as complementary governance layer

---

### Comment N7: Missing CRDT Literature

**Reviewer**: "Work on CRDTs is relevant to concurrency/conflict resolution."

**Response**: You are absolutely right -- the concurrency model in Section 3.6 needed grounding in the CRDT literature. We have added a new **Section 2.3.6, "Conflict-Free Replicated Data Types,"** that discusses three relevant bodies of work: (1) **Automerge**, whose multi-value register semantics offer an alternative to our last-write-wins (LWW) approach for status derivation -- we discuss the trade-off between Automerge's richer conflict representation and our simpler deterministic resolution; (2) **Yjs**, whose YATA algorithm for collaborative text editing inspired aspects of our fork detection mechanism; and (3) the **CRDT-ontology intersection**, surveying recent work on applying CRDTs to RDF graphs and OWL ontologies. We candidly acknowledge that ADL Lite currently uses a simple LWW strategy rather than a full CRDT merge semantics, and we have listed **CRDT-based conflict resolution as a future work item in Section 7.2**, with a concrete proposal for a multi-value register extension that would preserve all conflicting status proposals rather than selecting a single winner.

**Changes made**:
- **Section 2.3.6** (new): "Conflict-Free Replicated Data Types"
- Subsection 2.3.6.1: Automerge (multi-value register vs. LWW)
- Subsection 2.3.6.2: Yjs (YATA algorithm and fork detection)
- Subsection 2.3.6.3: CRDT-ontology intersection
- **Section 7.2** (updated): CRDT-based conflict resolution added as future work

---

### Comment N8: E6 Per-Operation Latency Missing

**Reviewer**: "Per-operation latency (append, verify, derive), resource utilization should be included."

**Response**: The 238-second aggregate runtime figure was indeed insufficiently decomposed. We have performed a detailed **phase-level breakdown** of the E6 experiment, identifying five distinct phases: (1) CSV parsing and row ingestion, (2) Event object creation (Python object instantiation and payload construction), (3) Chain append operations (hash computation and link insertion), (4) Integrity verification (`verify_integrity()` across all chains), and (5) I/O operations (disk reads/writes for persistence). We report **per-event latencies** for the three core operations: approximately 23 microseconds for event creation, 4.7 microseconds for chain append, and 7 microseconds for integrity verification (measured on the same hardware as the original 238s run). We have also added a **chain-length sensitivity table** showing how `verify_integrity()` latency scales linearly with chain length, confirming the expected O(n) complexity and providing concrete numbers for planning deployments at different scales.

**Changes made**:
- **Section 4.8** (updated): Five-phase decomposition of 238s runtime
- Section 4.8.1: Per-event latencies (creation ~23us, append ~4.7us, verify ~7us)
- **Table Y** (new): Chain-length sensitivity analysis for `verify_integrity()`
- Section 4.8.2: Resource utilization details (CPU cores, memory bandwidth, disk I/O)

---

### Comment N9: "Zero Integrity Failures" Unsurprising

**Reviewer**: "'Zero integrity failures' is unsurprising given a correct implementation."

**Response**: You raise a valid methodological point. We have added a dedicated paragraph in **Section 6.2** acknowledging that the zero-integrity-failure results in E1-E4 are **necessary but not sufficient** evidence of correctness -- they confirm that the implementation behaves as specified, not that the specification itself is novel. We reframe the contribution of E1-E4 as threefold: (1) **exhaustive coverage** -- every integrity violation class is tested, not just a sample; (2) **reproducibility** -- the tests are deterministic, automated, and included in the pip-installable toolkit; and (3) **regression baseline** -- future changes to the event chain logic can be validated against this comprehensive test suite. We then direct the reader to **E5-E7** as providing more discriminative evidence: E5 demonstrates multi-agent fork detection, E6 demonstrates throughput at scale, and E7 (the Git baseline) quantifies the added value of semantic event chains over raw version control.

**Changes made**:
- **Section 6.2** (updated): Added paragraph reframing E1-E4 contribution (exhaustive coverage, reproducibility, regression baseline)
- Section 6.2: Explicit acknowledgment that zero failures confirm correctness, not novelty
- Cross-references to E5-E7 for discriminative evidence

---

### Comment N10: L1 Recomputation on Every Read

**Reviewer**: "Treating L1 as derived snapshot implies every read triggers recomputation."

**Response**: This was an imprecision in the first revision's description. We have clarified in **Section 3.2** that L1 (the Markdown document layer) is **derived once at load time**, not on every read access. Specifically: when an EventChain is loaded from persistent storage, the L1 snapshot is computed by applying all events in sequence to the initial state -- this is a one-time O(n) operation. Subsequently, **status and confidence are cached on first access** and invalidated only when a new event is appended to the chain. We have also added a note explaining that **canonical JSON serialization** is used for all hash computations, ensuring platform-independent and deterministic hash values regardless of Python version or operating system. This addresses the concern about recomputation overhead while maintaining the theoretical purity of the derived-state model.

**Changes made**:
- **Section 3.2** (updated): Clarified that L1 is derived ONCE at load, not on every read
- Section 3.2: Status/confidence caching on first access with invalidation on append
- Section 3.2: Canonical JSON specification for platform-independent hashes

---

### Comment N11: Schema Drift Prevention

**Reviewer**: "What prevents schema drift in predicate vocabularies?"

**Response**: Schema drift is a genuine concern for long-running concept governance. We have added a dedicated discussion in **Section 6.4** covering three mechanisms that prevent or mitigate schema drift: (1) **closed predicate set in strict mode** -- the action registry can be configured to reject events that reference predicates not in the initially declared vocabulary, preventing uncontrolled vocabulary growth; (2) **Pydantic datatype normalization** -- all event payloads are validated against Pydantic models that enforce consistent datatype interpretation across platforms; and (3) **SHACL/ShEx shapes as Phase 3 governance** -- we describe how SHACL shapes (discussed in Section 2.1.2) will serve as the authoritative schema definition in Phase 3, providing a standards-based mechanism for vocabulary evolution with explicit versioning and deprecation policies. Together, these mechanisms provide a graduated approach: strict mode prevents drift in Phase 1, while Phase 3 introduces governance tooling for managed vocabulary evolution.

**Changes made**:
- **Section 6.4** (updated): Schema drift prevention discussion (3 mechanisms)
- Section 6.4.1: Closed predicate set in strict mode
- Section 6.4.2: Pydantic datatype normalization
- Section 6.4.3: SHACL/ShEx shapes as Phase 3 governance (cross-reference to Section 2.1.2)

---

### Comment N12: Concurrent VALIDATE+DEPRECATE

**Reviewer**: "How does the system handle concurrent conflicting actions?"

**Response**: We have formalized the concurrent action resolution semantics in **Section 3.6**. When two lifecycle actions targeting the same concept are issued concurrently (e.g., one agent issues `VALIDATE(alpha)` while another issues `DEPRECATE(beta)`), **both events are appended to the chain in timestamp order**, and the **last lifecycle event wins deterministically**. For example, given the event sequence `[VALIDATE(alpha), DEPRECATE(beta)]`, the concept's derived status is `DEPRECATED` because `DEPRECATE` is the last lifecycle event. This deterministic rule eliminates ambiguity and ensures all agents converge to the same state without requiring a consensus protocol. We have added a concrete example walkthrough in Section 3.6.1. We also cross-reference **Section 2.3.6** (CRDTs), acknowledging that the current LWW strategy is a deliberate simplification and that CRDT-based multi-value registers (as discussed in the Automerge comparison) represent a promising future direction for preserving all conflicting proposals rather than selecting a single winner.

**Changes made**:
- **Section 3.6** (updated): Formal concurrent action resolution semantics
- Section 3.6.1: Concrete example -- `[VALIDATE(alpha), DEPRECATE(beta)] -> DEPRECATED`
- Section 3.6: Last lifecycle event wins rule (deterministic, timestamp-ordered)
- Cross-reference to Section 2.3.6 (CRDTs) and Section 7.2 (future work)

---

## Follow-Up Comments (Round 1 to Round 2 Progress)

### Comment N3: Experiment Numbering Consistency

**Reviewer** (Round 1): The paper references experiments inconsistently (e.g., "six experiments" in some places, "E1-E6" in others).

**Response**: We have verified that **ALL experiment references are now consistently labeled E1 through E7 throughout the entire manuscript**. The previously problematic references -- "six experiments" in the abstract, "E1-E6" in the introduction, and inconsistent numbering in Sections 4 and 6 -- have all been corrected. Every mention of an experiment now uses the standardized `EX` format (E1, E2, ..., E7), including captions, cross-references, and the discussion sections. We have also added a summary table at the beginning of Section 4 that lists all seven experiments with their identifiers, descriptions, and primary claims, serving as a quick reference for readers.

**Changes made**:
- Abstract: Updated to "seven experiments (E1-E7)"
- Section 1: All experiment references normalized to E1-E7
- Section 4: Added summary table of experiments E1-E7
- Sections 4.1-4.9: Consistent EX labeling throughout
- Sections 5-6: All cross-references verified against E1-E7

---

## Response to Overall Assessment (Weak Reject)

You wrote: *"I recommend a weak reject... the path to Semantic Web compatibility is clearly within reach."*

We sincerely appreciate your candid assessment and the clear guidance you have provided across both review rounds. Your feedback has catalyzed a significant transformation of this paper. We respectfully argue that the revised manuscript now addresses all major concerns identified in both rounds:

**Across both rounds, we have made 25+ specific changes**, including:

1. **Standards alignment** (Round 1 concern): Added comprehensive engagement with PROV-O (Section 2.3.4, formal mapping table in Section 3.8), nanopublications, LD-Proofs, and RDF-star. Added CIDOC CRM, SEM/LODE (Section 2.3.5), and RDF Stream Processing coverage. SHACL/ShEx comparison (Section 2.1.2) clarifies the Phase 1 vs. Phase 3 boundary.

2. **Formalized semantics** (Round 2 concern): Added Section 3.9 with Algorithm 1 (DeriveStatus) and Algorithm 2 (DeriveConfidence). Added tampering detection taxonomy (Section 3.7) with 9 attack classes. Added comprehensive threat-model matrix (Table X, Section 6.5) mapping 9 capabilities across 3 adversary classes with clear Phase 1 vs. Phase 3 scope.

3. **Expanded related work** (Round 2 concern): Added CRDT literature (Section 2.3.6: Automerge, Yjs, CRDT-ontology intersection). Added event-centric ontologies (Section 2.3.5: CIDOC CRM, SEM/LODE). Added SHACL/ShEx comparison (Section 2.1.2).

4. **Improved evaluation** (Both rounds): Added E7 (Git baseline comparison, Section 4.9). Decomposed E6 into 5 phases with per-operation latencies (Section 4.8: ~23us creation, ~4.7us append, ~7us verify). Added chain-length sensitivity analysis. Added reproducibility checklist (Appendix A.2). Reframed E1-E4 as correctness confirmation with threefold contribution (exhaustive coverage, reproducibility, regression baseline).

5. **Clarified architecture** (Round 2 concern): Formalized concurrent action resolution (Section 3.6: last lifecycle event wins, deterministic). Clarified L1 derivation semantics (Section 3.2: derived once at load, cached on first access). Added schema drift prevention mechanisms (Section 6.4: closed predicate set, Pydantic normalization, SHACL governance).

The paper now provides: (a) a formally specified event-chain semantics with derivation algorithms; (b) a phased threat model that honestly scopes what is and is not implemented; (c) extensive engagement with Semantic Web standards and related work spanning provenance (PROV-O), validation (SHACL/ShEx), event ontologies (CIDOC CRM, SEM/LODE), and distributed systems (CRDTs); and (d) an evaluation that includes baseline comparisons, per-operation latency measurements, and reproducibility documentation.

We believe the path to full Semantic Web compatibility -- RDF serialization, SPARQL endpoints, Linked Data Proofs for authentication -- is now clearly mapped in the Phase 3 roadmap (Section 7), while the Phase 1 system offers immediate, zero-dependency value for LLM-native multi-agent workflows. We hope you find these revisions satisfactory and that the manuscript is now suitable for acceptance.

Sincerely,

The Authors
