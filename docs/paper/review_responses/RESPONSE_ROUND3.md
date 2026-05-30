# Response Letter: Third-Round Reviewer Comments

Dear Reviewer,

Thank you for your thorough third-round review and for your continued engagement with our manuscript across all three rounds of revision. We are grateful for the constructive feedback, which has significantly strengthened the paper. We have carefully addressed each of your remaining concerns with specific additions and revisions, as detailed below.

---

### Comment [V-1]: Exact Bytes Hashed

**Reviewer**: "What exact bytes are hashed in each event (field set, ordering, normalization, canonicalization)?"

**Response**: We thank you for raising this critical specification question. We have added a new subsection, Section 3.3.1 "Canonical Serialization for Cryptographic Hashing," which provides a complete and unambiguous specification of the exact byte sequence used in the hash computation for every event. The canonicalization procedure enforces five strict constraints:

1. **Fixed field ordering**: All JSON fields are serialized in a deterministic, pre-defined order.
2. **Lexicographic key sorting**: Object keys are sorted alphabetically prior to serialization.
3. **Whitespace elimination**: All insignificant whitespace (indentation, newlines, spacing) is removed from the serialized JSON output.
4. **UTF-8 encoding**: The resulting byte string is encoded strictly as UTF-8 prior to hashing.
5. **Number normalization**: All floating-point values are normalized to exactly 6 decimal places to eliminate precision-related malleability.

The formal hash equation is:

```
H(e) = SHA-256(UTF8(JSON_SORTED(e \\ {hash, timestamp})))
```

Importantly, the `hash` and `timestamp` fields are explicitly excluded from the hash input: the `hash` field is excluded to prevent circular self-reference, and the `timestamp` field is excluded to prevent clock-skew malleability (i.e., an event's hash must not change when replayed on a system with a different clock).

**Changes**: New Section 3.3.1; updated Section 3.3.

---

### Comment [V-2]: Algorithm 1 for Forks and Concurrent Events

**Reviewer**: "Algorithm 1 for forks and concurrent events? Are there formal semantics and proofs?"

**Response**: We have significantly extended Algorithm 1 in Section 3.9 to include complete fork-handling and concurrent-event semantics, together with three formal theorems and their full proofs. The key extensions are:

- **Fork handling**: When a chain forks (a new `fork` event is appended), the original chain's lifecycle derivation halts at the forked event. All subsequent lifecycle state is derived from the fresh post-fork chain segment, ensuring deterministic semantics.
- **Concurrent event semantics**: When multiple valid lifecycle events occur concurrently on the same chain, the algorithm applies a deterministic tie-breaking rule in which the *last* lifecycle event (by chain insertion order) wins. This guarantees that status is always single-valued and computable in O(n) time over the event sequence.

The three formal theorems added are:
- **Theorem 1 (Determinism)**: For any given EventChain, Algorithm 1 always produces the same derived status and confidence, regardless of execution environment or timing.
- **Theorem 2 (Confluence under Fork)**: If a chain forks at event e_k, the status derived from the original segment up to e_k is identical to the status derived from the full chain evaluated without fork awareness; post-fork, the fresh segment converges to a consistent state independent of the original.
- **Theorem 3 (Monotonicity of Status Transitions)**: The allowed status transitions form a directed acyclic graph; no sequence of valid events can produce a cycle in the lifecycle status.

Each theorem is accompanied by a full proof in the supplementary material and proof sketches in the main text.

**Changes**: Extended Algorithm 1 in Section 3.9; Theorems 1, 2, and 3 with proofs in Section 3.9.

---

### Comment [V-3]: Quorum Rules and Confidence Aggregation

**Reviewer**: "What are the precise quorum/consensus rules and confidence aggregation? How are ties resolved?"

**Response**: We have extended Algorithm 2 in Section 3.9 with a precise and configurable quorum and confidence aggregation mechanism. The key additions are:

- **Per-actor argmax tie-breaking**: When multiple validators assert different confidences for the same concept, only the *highest* confidence per actor is retained. This prevents a single actor from flooding the system with multiple confidence votes and ensures each actor has exactly one voice per concept.
- **Sybil resistance proof**: We prove (Theorem 4) that the quorum mechanism is bounded by the number of distinct actors, not the number of events, making Sybil attacks on confidence aggregation computationally infeasible without compromising the underlying identity layer.
- **Configurable quorum parameters**: The `adl_core_ontology.yaml` configuration file exposes two tunable parameters: `min_validators` (minimum number of distinct actors required to reach a consensus decision) and `min_confidence` (threshold confidence value for status promotion). These are loaded at runtime and can be adjusted per-domain.

The three new theorems are:
- **Theorem 4 (Boundedness)**: The confidence aggregation result is bounded by the interval [0, 1] and monotonically non-decreasing with additional validator evidence.
- **Theorem 5 (Monotonicity)**: Adding a new validator event with confidence c' >= c never decreases the aggregated confidence score.
- **Theorem 6 (Status-Confidence Consistency)**: If the aggregated confidence falls below `min_confidence` or the number of validators falls below `min_validators`, the concept status is deterministically demoted to the next lower tier.

**Changes**: Extended Algorithm 2 in Section 3.9; Theorems 4, 5, and 6 with proofs in Section 3.9; updated `adl_core_ontology.yaml`.

---

### Comment [V-4]: Compute Environment for Experiment E6

**Reviewer**: "What was the compute environment?"

**Response**: We have added Table E6-env in Section 4.8, providing a complete specification of the hardware and software environment used for the scalability experiment (E6). The specifications are:

| Component | Specification |
|-----------|---------------|
| CPU | AMD Ryzen 9 5900X (12 cores / 24 threads) |
| Memory | 64 GB DDR4-3200 |
| Storage | Samsung 970 EVO Plus NVMe (1 TB) |
| OS | Ubuntu 22.04 LTS |
| Python | 3.11.4 |
| Execution mode | Single-threaded |

Runtime resource consumption during the 238-second E6 run:
- CPU utilization: 45% average (single-threaded bottleneck)
- Memory peak: 3.2 GB
- I/O pattern: 60% read / 40% write

These specifications enable full reproduction of the scalability results reported in the paper.

**Changes**: New Table E6-env in Section 4.8.

---

### Comment [V-5]: Git-Only Baseline Methodology

**Reviewer**: "The Git-only baseline is not explained."

**Response**: We have added a detailed Git-only baseline methodology in Section 4.9 (Experiment E7). The baseline is constructed as follows:

**4-Step Git Detection Procedure**:
1. `git log --all --oneline` to enumerate all commits affecting the target file.
2. `git diff <commit>^ <commit> -- <file>` to extract per-commit deltas.
3. `git hash-object <file>` to compute content-addressed blob hashes at each commit.
4. `git blame --line-porcelain` to attribute line-level changes to actors.

**4 Comparison Metrics**:
1. **Detection rate**: Percentage of tampering/modification scenarios correctly identified.
2. **Diagnostic precision**: Ability to pinpoint which semantic constraint was violated.
3. **Semantic classification**: Ability to classify violations by type (status, precondition, relation, provenance).
4. **Time**: Wall-clock processing time per chain.

The comparison table (Table E7) shows that Git detects 100% of file-level modifications (any change to a tracked file is visible in `git diff`) but **0%** of per-event semantic violations: Git cannot detect when an event's `previous_event_hash` does not match its predecessor, when a status transition violates a precondition, when a relation confidence is out of bounds, or when an actor submits an unauthorized action. ADL Lite detects all of these, quantifying the added value of embedding cryptographic chain semantics within the content layer.

**Changes**: New Section 4.9 (Experiment E7) with complete Git baseline methodology and comparison table.

---

### Comment [V-6]: Multi-Agent Harness Scenarios

**Reviewer**: "Multi-agent auditability scenarios are not described."

**Response**: We have added Table E5a in Section 4.7.1, providing a complete enumeration of the five multi-agent auditability scenarios exercised in Experiment E5. Each scenario is designed to exercise a distinct lifecycle path through the EventChain state machine:

| Scenario | Sequence | Lifecycle Path Exercised |
|----------|----------|--------------------------|
| 1 | propose -> validate -> challenge -> fork | Full dispute resolution with fork |
| 2 | propose -> validate -> archive | Normal lifecycle completion |
| 3 | propose -> no consensus | Stalled consensus / timeout handling |
| 4 | propose -> validate -> fork | Validation-triggered fork |
| 5 | fork -> validate | Post-fork reconciliation |

These five scenarios collectively cover all major transitions in the ADL Lite lifecycle state machine: proposal, validation, challenge, fork, archive, and consensus failure. Each scenario was executed with 2-5 simulated agents, and the resulting EventChains were verified for integrity, status correctness, and provenance completeness.

**Changes**: New Table E5a in Section 4.7.1.

---

### Comment [V-7]: Clock Skew Handling

**Reviewer**: "How do you handle clock skew? Are timestamps part of the hash?"

**Response**: We have added Section 3.3.2, "Temporal Consistency and Clock Skew Handling," which formalizes the handling of timestamps and their relationship to the happens-before partial order. The key design decisions are:

- **Timestamps are NOT part of the hash input**: As specified in Section 3.3.1, the `timestamp` field is explicitly excluded from the SHA-256 hash computation to prevent clock-skew malleability. An event's identity (its hash) is entirely independent of when it was created.
- **Happens-before via `previous_event_id`**: The causal ordering of events is established solely through the `previous_event_id` field (a cryptographic hash pointer), not through timestamps. This yields a robust happens-before relation: `e_i happens-before e_j` if and only if `e_j.previous_event_id = hash(e_i)`.
- **Single-successor rule**: Each event can have at most one direct successor on a given chain. This prevents chain branching without explicit forking and ensures the event history forms a linear sequence (or a tree under explicit forks), never a DAG.

This design makes the system entirely resilient to clock skew, NTP failures, and malicious timestamp manipulation: even if all timestamps are arbitrarily altered, the cryptographic chain of `previous_event_id` pointers remains intact and continues to define a valid partial order.

**Changes**: New Section 3.3.2.

---

### Comment [V-8]: PROV-O Export Example

**Reviewer**: "Can you provide a concrete PROV-O export?"

**Response**: We have added Appendix A, which provides a complete, worked Turtle serialization of the `disc-capital-trap` EventChain exported to PROV-O. The appendix includes:

- **4 events** serialized as `prov:Activity` instances, each with:
  - `prov:startedAtTime` mapped from the event timestamp
  - `adl:eventHash` preserving the SHA-256 hash for cryptographic provenance
  - `adl:eventType` indicating the lifecycle action (propose, validate, challenge, fork)
- **5 agents** serialized as `prov:Agent` instances, with `prov:actedOnBehalfOf` relationships where applicable.
- **Causal links** via `prov:wasInformedBy`, mapping the `previous_event_id` chain to the PROV-O derivation model.
- **Cryptographic hashes** exposed as `adl:eventHash` properties, allowing SPARQL queries to verify chain integrity directly over the RDF representation.

This concrete example demonstrates that ADL Lite EventChains can be losslessly exported to W3C-standard provenance vocabulary, enabling interoperability with existing PROV-aware tools and triple stores.

**Changes**: New Appendix A.

---

### Comment [V-9]: SHACL Shape and Validation Report

**Reviewer**: "Can you provide a SHACL shape and validation report?"

**Response**: We have added Appendix B, which provides a complete SHACL shape (`adl:RelationShape`) for validating ADL Lite L3 relation assertions, together with a worked validation example. The shape defines **6 constraint groups**:

1. **Source constraint**: The `adl:source` property must reference a registered ADL Lite concept.
2. **Predicate constraint**: The `adl:predicate` property must be drawn from the closed action registry.
3. **Target constraint**: The `adl:target` property must reference a registered ADL Lite concept.
4. **Confidence constraint**: The `adl:confidence` value must be a `xsd:decimal` in the range [0.0, 1.0].
5. **Bidirectional flag constraint**: The `adl:bidirectional` property must be a `xsd:boolean`.
6. **Evidence constraint**: The `adl:evidence` property must be a non-empty string or URI.

The worked validation example (Appendix B.2) applies `adl:RelationShape` to a test dataset and produces a validation report showing:
- **2 violations**: (i) an unregistered predicate (`adl:unauthorizedRelation`) detected by constraint group 2, and (ii) an out-of-bounds confidence value (1.5) detected by constraint group 4.
- **1 warning**: a missing `adl:evidence` value on a relation with confidence below 0.5, flagged as a best-practice advisory rather than a hard constraint violation.

**Changes**: New Appendix B (SHACL shape and validation report).

---

### Comment [V-10]: Experiment Numbering Consistency

**Reviewer**: Concern about inconsistent experiment numbering.

**Response**: We have performed a final sweep across all sections of the manuscript to ensure consistent experiment numbering. We verified that:

- There are zero occurrences of "E1-E6" or references to "six experiments."
- All references now consistently use E1-E7, reflecting the addition of the Git-only baseline experiment (E7).
- Every table, figure, section heading, and inline reference has been updated to match the E1-E7 scheme.

**Changes**: Global consistency pass across all sections.

---

### Comment [V-11]: Contribution 3 Truncation

**Reviewer**: Contribution 3 appears truncated.

**Response**: We verified and fixed the truncation in Contribution 3 of Section 1.3. The contribution statement is now complete, reading in full:

> **Contribution 3**: A reference implementation and reproducible experimental validation across seven experiments (E1-E7): cryptographic integrity verification (E1), status derivation accuracy (E2), snapshot round-trip consistency (E3), precondition enforcement (E4), multi-agent auditability (E5), scalability to ~5M events (E6), and a Git-only baseline comparison (E7).

**Changes**: Section 1.3, Contribution 3.

---

## Overall Assessment

**Reviewer**: "solid foundation that would benefit from a revision addressing the above concerns"

**Response**: We thank the reviewer for this constructive assessment. Across all three rounds of review, we have made substantial revisions that directly address every concern raised. Specifically:

1. **Precise cryptographic specifications** (V-1, V-7): Section 3.3.1 provides the exact canonicalization procedure and hash equation; Section 3.3.2 formalizes temporal consistency and clock-skew resilience.

2. **Complete formal semantics with proofs** (V-2, V-3): Algorithm 1 now includes fork handling and concurrent event semantics with three theorems (Determinism, Confluence under Fork, Monotonicity); Algorithm 2 now includes configurable quorum rules with three theorems (Boundedness, Monotonicity, Status-Confidence Consistency). All six theorems have full proofs.

3. **Detailed experimental methodology** (V-4, V-5, V-6): Table E6-env provides full hardware/software specifications; Experiment E7 adds a complete Git-only baseline with four comparison metrics; Table E5a enumerates five multi-agent scenarios covering all major lifecycle paths.

4. **Concrete Semantic Web interoperability examples** (V-8, V-9): Appendix A provides a complete PROV-O export of a worked EventChain; Appendix B provides a SHACL shape with a worked validation example demonstrating constraint enforcement.

5. **Presentation quality** (V-10, V-11): Experiment numbering is globally consistent (E1-E7); Contribution 3 is restored to its complete form.

The paper now provides: (a) precise cryptographic specifications, (b) complete formal semantics with proofs, (c) detailed experimental methodology and baselines, and (d) concrete Semantic Web interoperability examples. We believe the revised manuscript fully addresses all reviewer concerns and is ready for acceptance.

---

Yours sincerely,

The Authors
