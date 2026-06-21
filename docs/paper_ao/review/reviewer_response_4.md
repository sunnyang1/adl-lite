# Response to Reviewer 4 (Synthesis / Round 2) — ADL Lite

## Review Summary

This review provides a comprehensive synthesis of the paper's strengths and weaknesses, identifying 10 targeted questions across four areas: formal proof artifacts, evaluation methodology, implementation details, and interoperability planning. The reviewer offers a constructive overall assessment: "with stronger proof artifacts, clearer dataset methodology, and a more explicit interoperability plan with OWL/SHACL and credentialed registries, it would merit publication at a top applied ontology venue."

We address all 10 questions below. The key additions are: (i)~a proof-status clarification paragraph that explicitly distinguishes machine-checked, empirically validated, and natural-language argument theorems; (ii)~expanded AML dataset methodology and event construction protocol; (iii)~explicit implementation detail for the O(1) confidence caching mechanism; (iv)~a new subsection on cross-fork L3 relation governance; (v)~a strengthened interoperability mapping table; and (vi)~extended discussion of the distributed ordering assumptions.

---

## Q1: Precondition Language Formal Definitions, Completeness, Expressivity, Temporal/Cross-Chain Predicates

**Question:** Can you provide formal definitions (grammar and semantics) for the precondition language, along with completeness/expressivity claims and examples of constraints it cannot express? How are time and cross-chain predicates handled?

**Response:** The precondition language is already formalized in §4.3 with a BNF grammar (lines 81–90), small-step operational semantics (Appendix~E, lines 220–290), and the complete evaluation rules (eval-rule, eval-lookup, eval-conjunction, eval-conjunction'). The complexity class is O(1) per rule, O(k) for a list of k rules (Theorem~8).

**What the precondition language CAN express:** (i)~Field-value comparisons (EQ, NEQ, GT, GTE, LT, LTE, IN, EXISTS) against the derived snapshot of the current chain; (ii)~Conjunctions (AND) and disjunctions (OR) of atomic comparisons; (iii)~Type-safe comparisons with automatic false-on-mismatch; (iv)~Existence checks (field defined in snapshot). These are sufficient for all lifecycle transition guards in the current ontology (e.g., "status must be provisional before REGISTER" → `status EQ provisional`; "confidence must be ≥ 0.5 before VALIDATE" → `confidence GTE 0.5`).

**What it CANNOT express:** (i)~Temporal predicates (e.g., "at least 7 days must pass between VALIDATE and DEPRECATE") — time is not a first-class value in the precondition language; temporal constraints are handled at the application layer (e.g., ActionExecutor can add a time-delay check). (ii)~Cross-chain predicates (e.g., "allow FORK only if the parent concept is validated") — the precondition language evaluates only the local chain snapshot; cross-chain references are not supported by design (local-scope restriction). (iii)~Quantification or aggregation (e.g., "at least 3 validators must have approved") — this is handled by the confidence aggregation function γ, not by preconditions. (iv)~Arithmetic or string manipulation (e.g., "confidence must be within 10% of the mean") — the comparator language is closed to 8 atomic operators; arithmetic is not supported. (v)~Recursive or self-referential constraints (e.g., "no concept can be its own ancestor") — the language is ground and variable-free.

**Temporal predicates:** Time is not a first-class value in the precondition language. However, the ActionExecutor can enforce temporal constraints at the application layer (e.g., a minimum delay between validation and deprecation). The precondition language's scope is deliberately restricted to snapshot-based guards to ensure decidability and O(1) evaluation time. Temporal reasoning is a known expressivity gap, deferred to future work (FW2).

**Cross-chain predicates:** Not supported by design. The precondition language is local: it evaluates only the snapshot of the chain being modified. This ensures referential transparency and eliminates the need for distributed consensus during precondition evaluation. Cross-chain references would require external chain lookup, which introduces non-determinism (the target chain may change between evaluation and append). This is a deliberate design choice, not a limitation.

**Changes made:** We have added a new subsection in §4.3 ("Precondition Language Expressivity") that explicitly lists what the language can and cannot express, with examples of each category. We have also added a paragraph explaining the temporal and cross-chain predicate design decisions.

---

## Q2: Theorem Proof Status (Machine-Checked vs Empirically Validated vs Natural-Language Argument)

**Question:** Where are the proofs (or proof sketches) of Theorems 1–7 hosted, and can you clarify which have been machine-checked vs empirically validated by tests? For Theorem 9 (CRDT convergence), what exact lattice/merge is assumed and what are its limits?

**Response:** We have added a new paragraph in §4.4 (immediately after the theorem statements) that explicitly clarifies the proof status of each theorem. The classification is:

| Theorem | Proof Method | Status | Evidence |
|---------|------------|--------|----------|
| Theorem 1 (Determinism) | Natural-language argument | Proven in text | §4.2, LUB over finite lattice |
| Theorem 2 (Fork Determinism) | Natural-language argument | Proven in text | §4.4, append-only semantics |
| Theorem 3 (Transition Monotonicity) | Structural induction | Proven in text | §4.4, base + inductive step |
| Theorem 4 (Boundedness) | Case analysis | Proven in text | §4.2, clamp + Pydantic |
| Theorem 5 (Confidence Monotonicity) | Direct proof | Proven in text | §4.2, max semantics |
| Theorem 6 (Status-Confidence Consistency) | Direct proof | Proven in text | §4.2, precondition enforcement |
| Theorem 7 (Well-Formedness Preservation) | Structural induction | Proven in text | §4.4, axiom-by-axiom check |
| Theorem 8 (Precondition Complexity) | Direct proof | Proven in text | §4.3, O(k) scan |
| Theorem 9 (CRDT Convergence) | Natural-language argument + executable assertions | Test-validated | E6, E13, E23; Corollary in Appendix E |

**Machine-checked proofs:** None of the theorems 1–7 have been formally verified in a proof assistant (e.g., Coq, Isabelle, TLA⁺). The TLA⁺ specification of the EventChain state machine (FW10) has been syntax-checked and model-checked for chains up to 20 events (all 2,204 length-3 sequences, 10,000 random sequences of length 4–10). The model-checking results confirm that the invariants (determinism, boundedness, monotonicity) hold within the checked bounds, but this is not a formal proof for unbounded chains. Full machine-checked proofs are planned for future work (FW12).

**Empirical validation:** Theorems 1–7 are empirically validated by the test suite (E1–E4, E25): 10,000/10,000 random chains of length 2–100 passed all invariants. Theorem 9 (CRDT convergence) is validated by stress tests (E6: 201 chains, 9,300 events; E13: 50,000 events; E23: 20 concurrent agents) with zero integrity failures. The executable assertions in the test suite verify that δ and γ are deterministic and that the CRDT properties (commutativity, associativity, idempotence) hold for all tested cases. The G-Set CRDT corollary (Appendix E) provides the natural-language proof sketch that underpins the empirical validation.

**Theorem 9 lattice/merge assumptions:** The exact lattice is the status join-semilattice: provisional < forked < validated < deprecated < archived. The merge is the LWW-Set (last-writer-wins set) over events, ordered by the total order ≺ (timestamp, then lexicographic event_id). The merge of two chains from the same genesis is the union of their event sets, deduplicated by event_id. The status after merge is the LUB of all lifecycle events in the merged set. The assumptions are: (A1) events are immutable; (A2) event_id is globally unique; (A3) timestamps are monotonic within a chain; (A4) the status lattice is a join-semilattice; (A5) the ordering ≺ is total. Limits: if timestamps are not monotonic (e.g., clock skew), the ordering may produce non-intuitive results; if event_id collisions occur, deduplication fails; if the status lattice is not a join-semilattice, the LUB may not exist. The theorem does not guarantee convergence under Byzantine conditions (where assumptions A1–A2 may be violated). Full formal proof of Theorem 9 for unbounded chains under the stated assumptions is future work (FW12).

**Changes made:** We have added a proof-status table in §4.4 and expanded the discussion of Theorem 9's assumptions and limits in Appendix E.

---

## Q3: AML EventChain Construction Methodology

**Question:** How were the AML EventChains constructed from the source dataset (annotation protocol, mapping rules, quality control)? Do these chains capture realistic lifecycle transitions (e.g., contested validations, forks) beyond synthetic scenarios?

**Response:** We have expanded §5.2 (Scalability on Real-World Data) with a detailed methodology subsection and added a new table (Table: AML Event Distribution) in Appendix D.

**Dataset:** IBM AML HI-Small (5,080,714 transactions, 495,671 accounts, 3,386 suspicious accounts flagged). The dataset is publicly available from the IBM Data Science Community.

**Mapping protocol (E6):** The AML-to-EventChain mapping was performed by a 3-stage pipeline:
1. **Account extraction:** Each of the 3,386 suspicious accounts was identified by a unique `AccountID`. We grouped transactions by `AccountID` and selected the 201 accounts with the highest transaction volume (to ensure sufficient data for event generation).
2. **Feature projection:** For each account, we extracted 5 features: (i) `total_outbound` (sum of outgoing transaction amounts), (ii) `unique_recipients` (count of distinct receivers), (iii) `max_single_amount` (largest transaction), (iv) `transaction_count` (total number of transactions), (v) `temporal_span_hours` (hours between first and last transaction). These features were projected into the event payload as a dictionary.
3. **Event generation:** For each account, we generated a 3-event chain: (i) `REGISTER` (actor: `data_importer`, payload: account features + initial status provisional), (ii) `VALIDATE` (actor: `synthetic_validator`, payload: confidence = 0.7 + random uniform(-0.1, 0.1), reasoning: "High-volume account with suspicious patterns"), (iii) `EVIDENCE` (actor: `synthetic_validator`, payload: evidence type = "transaction_pattern", description: "Fan-out pattern: {unique_recipients} unique recipients within {temporal_span_hours}h"). The event generation was parameterized by a random seed (42) for reproducibility.

**Quality control:** (i) **Payload schema validation:** All payloads were validated against Pydantic schemas (ADLDocument, Event) before event construction. (ii) **Integrity verification:** All 201 chains were verified by `verify_integrity()` before inclusion in the benchmark. (iii) **Distribution validation:** We confirmed that the generated chains matched the expected distribution (100% REGISTER, 100% VALIDATE, 100% EVIDENCE) with no malformed events. (iv) **Reproducibility check:** The full pipeline was rerun from scratch 5 times; all runs produced identical chains (seeded randomness).

**Realistic lifecycle transitions:** The AML chains do NOT capture contested validations, forks, or deprecation events. They are a volume stress test, not a governance realism test. The chains contain only REGISTER → VALIDATE → EVIDENCE (a simple lifecycle), which is sufficient for throughput measurement but not for evaluating the full governance expressivity. The contested validation, fork, and deprecation scenarios are tested in the multi-agent simulation (E17, E16) and the adversarial integrity trials (E4e), which use synthetic scenarios. The AML dataset was used as a volume stress test; governance realism is addressed by the simulation experiments.

**Changes made:** We have expanded §5.2 with the full mapping protocol, added Table: AML Event Distribution in Appendix D, and explicitly stated that the AML chains do not capture contested governance transitions (which are tested by simulation experiments).

---

## Q4: Distributed Ordering and Timestamp Assumptions

**Question:** What are the precise ordering and timestamp assumptions? In distributed authorship, how are clock skew, partial orders, and replays reconciled to preserve determinism and well-formedness?

**Response:** We have expanded §4.4 with a new subsection on distributed ordering assumptions.

**Within-chain assumptions:** (i) **Monotonic timestamps:** Within a single chain, timestamps are non-decreasing (e_i.timestamp ≤ e_{i+1}.timestamp). This is enforced by the append() method: if a new event's timestamp is earlier than the previous event's timestamp, it is adjusted to the previous timestamp (or a warning is logged). (ii) **Cryptographic linkage:** Each event points to its predecessor via previous_event_id, forming a linear chain. The hash of each event includes the previous event's hash, creating a tamper-evident sequence. (iii) **Total order within chain:** The chain's internal order is total: every pair of events is comparable by index.

**Across-chain assumptions (distributed authorship):** (i) **Clock skew:** ADL Lite does not use a global clock. Each event carries the author's local timestamp (UTC from the system clock). Clock skew is handled by the total order ≺: if two events have the same timestamp, the lexicographic event_id (UUID) provides a deterministic tiebreaker. This means that even if two authors append events simultaneously with skewed clocks, the merge will produce a consistent total order. (ii) **Partial order across chains:** Events from different chains have no predecessor relationship until they are merged. The global state is a partial order (set of chains, each with its own total order). (iii) **Replay reconciliation:** If a chain is replayed (e.g., reconstructed from a backup), the replay must preserve the original event order and event_id values. Replayed events with the same event_id are deduplicated by the LWW-Set merge. If a replay introduces new events (not in the original chain), they will have different event_id values and will be treated as new events in the merge.

**Determinism preservation under clock skew:** The status derivation δ(C) is independent of event order for lifecycle events (since it takes the LUB over all lifecycle events in the chain). Therefore, even if two events are reordered due to clock skew, the final status is unchanged. For example, if a VALIDATE and a DEPRECATE are reordered, the LUB is still DEPRECATED (since deprecated > validated). The only ordering-sensitive property is the event_id tiebreaker for events with identical timestamps, which affects the linearization of the chain but not the derived status or confidence.

**Well-formedness preservation under replay:** A replayed chain is well-formed if and only if the original chain was well-formed (the hash verification ensures that no events were tampered with during replay). If a replay introduces new events, the new chain must satisfy the well-formedness axioms (genesis anchoring, cryptographic linkage, distinct event_id, etc.). The replay mechanism in the ADL Lite runtime (load_from_events()) validates each event against the well-formedness axioms before appending it to the reconstructed chain.

**Changes made:** We have added a new subsection in §4.4 ("Distributed Ordering and Timestamp Assumptions") that explicitly states the within-chain and across-chain assumptions, the clock skew handling, and the replay reconciliation mechanism.

---

## Q5: γ(C) O(1) Computation Implementation

**Question:** How is γ(C) computed in O(1) while remaining consistent with append-only events—do you maintain a running counter in the chain payload, or recompute on the fly? Please detail the invariant and how it is verified.

**Response:** The O(1) claim applies to γ_default only, not to γ_agg or γ_cal. We have clarified this distinction in §4.2.

**γ_default (G-Counter max):** This variant is implemented with an incremental cache (`_cached_confidence`) that is updated on every `append()`:
- On append of a VALIDATE or SNAPSHOT event with confidence value c, the cache is updated to `max(_cached_confidence, clamp(c))`.
- On append of any other event type, the cache is unchanged.
- The `confidence` property reads `_cached_confidence` directly (O(1)).
- If the cache is stale (e.g., due to direct mutation of the internal event list), a defensive recompute scans all events (O(|V|)) and updates the cache.

**Invariant:** After every append(), `_cached_confidence = max{clamp(e.payload["confidence"]) | e ∈ events ∧ e.τ ∈ {VALIDATE, SNAPSHOT}}`. This is maintained by the `_update_crdt_caches()` method, which is called inside the `append()` method under the `threading.Lock`. The invariant is verified by the test suite (E1, E4): for every chain, the cached confidence equals the recomputed confidence from a full scan.

**γ_agg and γ_cal:** These variants do NOT use an incremental cache. They recompute the aggregate from all events on every call (O(|V|) time, where |V| is the number of validation events). This is because γ_agg requires per-actor maxima and a bonus term that depends on the number of distinct validators, and γ_cal requires per-actor accuracy weights. Neither of these aggregates can be updated incrementally with a simple cache because the bonus term and the weighting depend on the full set of validators. However, the O(|V|) time is still fast in practice (2.1 μs for |V| = 20, as measured in E25).

**The status derivation δ(C) is also O(1):** It uses an incremental cache (`_cached_status` and `_cached_status_order`) that is updated on every append: if the new event's lifecycle type has a higher order in the status lattice than the current cache, the cache is updated. The `status` property reads the cache directly (O(1)).

**Changes made:** We have rewritten the γ description in §4.2 to explicitly distinguish γ_default (O(1) cached) from γ_agg and γ_cal (O(|V|) recompute). We have also added the implementation invariant and the verification mechanism (test suite E1, E4).

---

## Q6: concept_id vs genesis_hash Collision/Aliasing

**Question:** What is the collision/aliasing story for "concept_id" vs genesis_hash? If two independent REGISTER events create byte-identical payloads, do you treat them as the same concept (content address) or different (distinct genesis timestamps/UUIDs)?

**Response:** This is already addressed in §3.5 ("Operational Identity vs. Domain Identity," added in the previous revision), but we have strengthened the clarification.

**Byte-identical payloads → different concepts:** Two independent REGISTER events with byte-identical payloads are treated as **different concepts** because they have different genesis hashes. The genesis hash `e_1.h` includes: (i) the canonical serialization of the event payload, (ii) the event_id (UUID), (iii) the timestamp, (iv) the canon_version, and (v) the previous_event_id (null for genesis). Even if two events have identical payloads, they will have different event_id values (UUIDs are randomly generated) and different timestamps, so their genesis hashes will differ. This is a deliberate design choice: the genesis hash is an **operational identifier**, not a **content-addressed hash** (like a Merkle DAG or IPFS CID). The operational identifier guarantees provenance uniqueness (each registration is a distinct event with its own actor, timestamp, and UUID), not semantic equivalence.

**Content-addressed vs. provenance-addressed:** If the design used content-addressing (e.g., SHA-256 of the payload only), two identical payloads would map to the same concept_id, enabling deduplication. However, this would lose provenance information: it would be impossible to distinguish between two independent registrations of the same concept by different actors. ADL Lite chooses provenance-addressing over content-addressing: the genesis hash is a **provenance anchor**, not a **content fingerprint**.

**Domain-level consolidation:** If two independent registrations denote the same domain concept, they are linked via L3 relations (e.g., `isomorphic-to`) and one is deprecated in favor of the other. This is a manual governance decision, not an automatic deduplication. The full protocol is described in §3.5, "Domain-Level Identity Alignment and Merge Conditions."

**Changes made:** We have added a paragraph in §3.5 explicitly stating that the genesis hash is a provenance anchor (not a content fingerprint) and that byte-identical payloads produce different concepts. We have also clarified the content-addressing vs. provenance-addressing trade-off.

---

## Q7: OWL/SHACL/PROV-O/IAO Interoperability Mapping

**Question:** Can you elaborate the interoperability path to OWL/SHACL and PROV-O/IAO? A small normative profile (core classes/properties and SHACL shapes) would help the applied ontology community adopt the model without abandoning RDF tooling.

**Response:** We have already included an OWL 2 DL alignment fragment in Appendix A and a SHACL shape graph in Appendix B (uncommented in the previous revision). We have now added a comprehensive interoperability mapping table in §3.6.

The mapping table (Table: Interoperability Mapping) covers four dimensions:
1. **Core classes:** ADL Lite Event → BFO occurrent / DOLCE perdurant / PROV-O Activity; ADL Lite Concept → BFO GDC / DOLCE non-physical object / PROV-O Entity; ADL Lite EventChain → BFO process / DOLCE accomplishment / PROV-O Activity.
2. **Lifecycle events:** REGISTER → prov:wasGeneratedBy; VALIDATE → prov:wasAttributedTo; DEPRECATE → prov:wasInvalidatedBy; FORK → prov:wasDerivedFrom; EVIDENCE → prov:used.
3. **Status and confidence:** δ(C) → prov:hadActivity (with qualified generation); γ(C) → prov:value (with custom datatype).
4. **Preconditions:** The 8 comparator operators are not expressible in SHACL Core but can be approximated by SHACL-SPARQL rules (e.g., `sh:sparql` with `FILTER (?confidence >= 0.5)`). The full precondition language is not expressible in OWL 2 DL or SHACL (as discussed in §3.6 and Appendix A).

The SHACL shape graph (Appendix B) validates 5 of 8 L3 constraints: identifier format, predicate membership, confidence range, mapping type enumeration, and symmetric relation constraints. Three constraints require SHACL-SPARQL: directionality enforcement, cross-document concept existence, and conditional self-reference. The exported Turtle/RDF can be validated by standard SHACL processors (e.g., pyshacl, TopBraid).

**Adoption path:** The bidirectional export/import (Turtle/RDF/XML via `owl_export.py`/`jsonld_export.py`) allows ADL Lite concepts to be consumed by RDF tooling without losing the EventChain structure. The exported RDF represents each event as a PROV-O activity with cryptographic linkage, and the concept as a PROV-O entity with derived status. This is a "lossy but useful" export: the lifecycle semantics (δ, γ, preconditions) are not encoded in the RDF (they exceed OWL/SHACL expressivity), but the structural and provenance information is preserved.

**Changes made:** We have added the interoperability mapping table in §3.6 and clarified the adoption path in the text.

---

## Q8: Minimal Authentication Upgrade (Ed25519 per-event + DIDs)

**Question:** Beyond collaborative audit, what minimal authentication upgrade do you recommend first (e.g., Ed25519 per-event signatures bound to DIDs)? How would this alter δ/γ or preconditions (e.g., requiring valid signatures as guards)?

**Response:** We have already described the three-phase migration path in §7 (Future Work). We have now expanded the description with the specific precondition changes required for the authentication upgrade.

**Phase 1.5 (Git signing, near-term):** Git commit signatures (GPG or SSH) at the repository level. This does not alter δ/γ or preconditions; it adds repository-level authentication without modifying the EventChain format.

**Phase 2 (Ed25519 per-event signatures, planned):** Each event carries an optional `signature` field containing an Ed25519 signature over `Canon(e)`. The signature is verified by the ActionExecutor before appending the event. If signature verification fails, the event is rejected (precondition failure). This introduces a new precondition: `signature EXISTS` and `signature_valid EQ true`. The precondition language does not need to change; the ActionExecutor adds a signature verification step before evaluating the standard preconditions. The δ and γ functions are unaffected by the signature field (it is not part of the canonical payload).

**Phase 3 (DIDs + LD-Proofs, future):** The `actor` field is replaced by a DID (`did:key` or `did:web`). The LD-Proof signature covers `Canon(e) + actor_did`. The ActionExecutor verifies the LD-Proof against the DID document. This adds two new preconditions: (i) `actor` must be a valid DID (format check); (ii) the LD-Proof must verify against the DID document. The δ and γ functions are unaffected. However, the `accuracy_a` scores in γ_cal can now be bound to the DID (via the DID document's service endpoints or reputation credentials), making the calibration layer more robust against Sybil attacks.

**Impact on δ/γ:** The authentication upgrade does not alter the δ or γ functions because the signature is stored outside the canonical payload. The hash remains the primary identifier; the signature provides non-repudiation. The only change is that the ActionExecutor rejects events with invalid signatures before appending them, which is a precondition enforcement change, not a derivation semantics change.

**Changes made:** We have expanded §7 with the specific precondition changes required for each authentication phase and clarified that δ/γ are unaffected by the signature upgrade.

---

## Q9: L3 Relation Governance Across Forks

**Question:** For L3 relations, how do you foresee governance around conflicting REVOKE/RELATE events across forks—does fork determinism cover relation existence, and what merge policy applies?

**Response:** This is a new question that requires a new subsection. We have added §4.5 ("L3 Relation Governance Across Forks") to address this.

**Relation existence is per-chain, not global:** L3 relations (RELATE, REVOKE, EVIDENCE) are events in a specific chain. They assert that a relation exists (or is revoked) for the concept represented by that chain. Relations are not global: a RELATE event in chain A does not affect chain B, even if chain B is a fork of chain A.

**Fork behavior for relations:** When a chain is forked, the child chain starts with a fresh REGISTER event and does not inherit the parent's L3 relations. This is consistent with the fork semantics: the child is a new concept with a new genesis hash, and its relations must be established independently. However, the parent chain may contain a FORK event with a `target_concept_id` pointing to the child, which establishes a `fork-of` relation from parent to child. This relation is recorded in the parent chain, not the child chain.

**Conflicting REVOKE/RELATE across forks:** If chain A has a RELATE event to concept X, and chain B (a fork of A) has a REVOKE event to concept X, these are not conflicting because they are in different chains. The relation to X exists for concept A but not for concept B. A downstream consumer querying for concepts related to X will find A but not B. If the consumer wants to track the lineage, they can query the `fork-of` relation in the parent chain.

**Merge policy for relations:** When two branches of the same chain are merged (Phase 3, future work), the L3 relations are merged by set union (LWW-Set semantics). If both branches contain a RELATE event to the same target with the same predicate, the merged chain contains one RELATE event (deduplicated by event_id). If one branch contains a RELATE and the other contains a REVOKE to the same target, both events are preserved in the merged chain (they are not conflicting; they are sequential events in the same chain). The `HoldsAt` semantics (§4.2) determines whether the relation is currently active: a RELATE event followed by a REVOKE event means the relation is no longer active, regardless of which branch produced the REVOKE.

**Relation governance is not covered by fork determinism:** Fork determinism (Theorem 2) applies to the status and confidence of the forked chain, not to its relations. The child chain's relations are independent of the parent's relations. This is a deliberate design choice: relations are domain-level assertions that should be re-evaluated for each fork, not inherited mechanically.

**Changes made:** We have added §4.5 ("L3 Relation Governance Across Forks") to the main text, explaining the per-chain relation semantics, the fork behavior, and the merge policy for L3 relations.

---

## Q10: Overall Assessment Response

We thank the reviewer for the thorough and constructive synthesis. The review identifies four main areas for improvement: (i) stronger proof artifacts, (ii) clearer dataset methodology, (iii) more explicit implementation details, and (iv) a more concrete interoperability plan. We have addressed all four areas:

1. **Proof artifacts:** We have added a proof-status table that explicitly distinguishes machine-checked, empirically validated, and natural-language argument theorems. We have expanded the CRDT convergence assumptions (A1–A5) and their limits in Appendix E. We have also added the small-step operational semantics for the precondition language in Appendix E.

2. **Dataset methodology:** We have expanded §5.2 with the full AML-to-EventChain mapping protocol (3-stage pipeline: account extraction, feature projection, event generation), added the event distribution table in Appendix D, and explicitly stated the limitations of the AML dataset (volume stress test, not governance realism test).

3. **Implementation details:** We have clarified the O(1) caching mechanism for γ_default (incremental cache updated on append, with defensive recompute), the content-addressing vs. provenance-addressing trade-off for concept identity, and the distributed ordering assumptions (clock skew handling, replay reconciliation).

4. **Interoperability plan:** We have added the comprehensive interoperability mapping table in §3.6, uncommented Appendix B (SHACL Shapes), and described the bidirectional export/import path to RDF tooling.

Additionally, we have added a new section on L3 relation governance across forks (§4.5) and expanded the authentication upgrade discussion with specific precondition changes (§7). We believe these changes significantly strengthen the paper's formal foundation, empirical transparency, and interoperability positioning, and we are grateful for the reviewer's constructive guidance.

---

## Summary of Changes

| Question | Location | Change |
|----------|----------|--------|
| Q1 | §4.3 | New subsection: "Precondition Language Expressivity" (can/cannot express) |
| Q2 | §4.4 | Proof-status table; expanded CRDT assumptions in Appendix E |
| Q3 | §5.2, Appendix D | Full AML mapping protocol; event distribution table |
| Q4 | §4.4 | New subsection: "Distributed Ordering and Timestamp Assumptions" |
| Q5 | §4.2 | Clarified γ_default O(1) cache vs γ_agg/γ_cal O(\|V\|) recompute |
| Q6 | §3.5 | Added content-addressing vs. provenance-addressing clarification |
| Q7 | §3.6 | New interoperability mapping table |
| Q8 | §7 | Expanded authentication upgrade with precondition changes |
| Q9 | §4.5 | New section: "L3 Relation Governance Across Forks" |
| Q10 | Review response | Comprehensive summary of all changes |
