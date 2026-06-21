# Response to Reviewer Comments

## ADL Lite: An Event-First Capability-Lifecycle Registry for LLM Agent Ecosystems

We thank the reviewer for the thorough and constructive feedback. The review identified a conceptual weakness in our revocation semantics (overloading `confidence=0` as a control flag), requested clarification on the complexity claims for δ and γ, asked for deeper engagement with transparency logs, and raised important questions about formal assumptions, genesis hash stability, and CRDT convergence. We have addressed all of these concerns in the revised paper. Below, we respond to each question individually and point to the specific changes.

---

## Q1. Full definitions of δ and γ, including inputs, outputs, fork handling, and timestamp conditions. Under what conditions are δ O(n) and γ O(1) if no mutable state is stored?

**Response.** We have revised §4.2 and §4.5 to provide complete, formal definitions of both functions. The key clarification concerns the complexity claim: the original text incorrectly stated that γ is O(1). We have corrected this to O(|V|) ≤ O(n), where V is the validation subsequence (§4.2, §4.5, and Appendix H). The canonical state is always recomputable from the event sequence in O(n) time; the implementation optionally memoizes derived snapshots in a warm index for O(1) incremental query, but this is an implementation optimization, not a change to the canonical model. The distinction between "canonical state" (derived from events, O(n) recompute) and "derived snapshot" (memoized view, O(1) query) is now explicitly stated in §4.2.

**Fork handling.** Theorem 2 (Fork Determinism, §4.7) proves that δ(C_fork) = max(s, forked) where s = δ(C), and δ(C') = provisional for the child. The child chain starts with a fresh genesis hash; parent and child are independent after the fork point. γ is computed per-chain, so the child's confidence starts at 0.0 and accumulates its own VALIDATE events.

**Timestamp conditions.** The total order ≺ is defined as timestamp primary, event_id lexicographic tiebreaker (§4.7). Timestamps are monotonic within a chain (enforced by the ActionExecutor), but concurrent events across agents may have out-of-order timestamps due to clock skew; the tiebreaker resolves these deterministically.

---

## Q2. How is the genesis hash computed and stabilized across repositories? What prevents accidental identity bifurcation due to benign formatting changes?

**Response.** We have added a dedicated paragraph on genesis hash stability in §4.1 ("Canonical Serialization and Cryptographic Integrity"). The genesis hash is the SHA-256 of the first REGISTER event's canonical JSON, which includes the concept_id. Early versions excluded concept_id, causing collisions; this was corrected (E1, §5.1). The canonicalization includes: (i) lexicographically sorted JSON keys, (ii) 6-decimal float rounding, (iii) canon_version identifier, (iv) LF line ending normalization, (v) UTF-8 encoding. Benign Markdown reformatting (e.g., prettier) does not affect event hashes because only the event payload fields participate in the hash, not the surrounding L2 prose. The canon_version field ensures future serialization changes do not invalidate old hashes.

---

## Q3. Clarify the tension between "HoldsAt does not depend on confidence" and the use of confidence=0 in the Revoked predicate. Would a REVOKE event simplify reasoning?

**Response.** This is the most significant conceptual change in the revision. We have completely revised §3.4.4 to replace the overloaded `confidence=0` semantics with a dedicated `REVOKE` event type. The new revocation semantics (Equation 3) are:

```
Revoked(c₁, c₂, p, t) ⟺ ∃ e_rev ∈ C. e_rev.type = REVOKE ∧ e_rev.timestamp ≤ t ∧
    e_rev.payload.target_concept_id = c₂ ∧ e_rev.payload.predicate = p
```

The `REVOKE` event is a communication event (not in Σ_life), so it does not affect δ(C). Theorems 1–6 are unchanged. We retain the "epistemic weakening" design (RELATE with confidence=0) as an alternative mechanism for graded belief revision, but it is no longer conflated with existential revocation. The `REVOKE` event type has been added to the ontology YAML (adl_core_ontology.yaml) and the Python EventType enum (models.py). The "Design choice" paragraph in §3.4.4 now explicitly recommends cessation semantics (REVOKE) as the default, with epistemic weakening as a secondary option.

---

## Q4. What are the exact assumptions for the determinism and fork-determinism theorems?

**Response.** We have added a new paragraph in §4.8 explicitly listing the five assumptions (A1–A5) for CRDT convergence: (A1) unique event IDs (UUID v4), (A2) timestamp monotonicity within a chain, (A3) clock-skew tolerance via event_id tiebreaker, (A4) append-only immutability, (A5) finite join-semilattice status space. Theorem 1 (Determinism) requires well-formedness (12 axioms) and the total order from cryptographic linkage. Theorem 2 (Fork Determinism) additionally requires that the fork event's previous_event_id correctly points to the parent tail. All assumptions are enforced by the well-formedness predicate (Appendix E) and the ActionExecutor precondition system (§4.6).

---

## Q5. How would the optional CRDT convergence property (Theorem 9) interact with the linear EventChain abstraction? Per-chain lattice or lower-level DAG?

**Response.** We have clarified this in §4.8 with a new paragraph explaining the separation between the CRDT set and the linear chain. The CRDT operates at the set level (events as elements), while the hash chain is a derived view (sequence ordering). When branches merge, the event set B₁ ∪ B₂ is the CRDT state; the linear chain is a derived view obtained by sorting the set on ≺. The derived state (δ, γ) is computed from the set, not the linear order, so it is independent of re-linearization. The hash chain is recomputed for integrity verification but does not affect the derived state. This means: (i) status and confidence are deterministic under merge, and (ii) post-merge integrity verification is possible via the recomputed hash chain. For applications requiring pre-merge ancestry proofs, original branch hashes are stored in a MERGE event payload. The interaction is a per-chain lattice (LUB on derived states) over a set-level merge, not a lower-level DAG.

---

## Q6. Expand the OWL 2 DL alignment with competency questions and example axioms. Which aspects are left outside OWL? How would SHACL be used?

**Response.** We have completely rewritten Appendix A to include: (i) L3 relation axioms (isomorphic-to, specialisation-of, fork-of, mitigated-by) as OWL object properties with domain/range constraints, (ii) a statement that L4 actions are intentionally excluded because they require temporal reasoning and preconditions beyond OWL 2 DL, (iii) five competency questions (CQ1–CQ5) with their answers, (iv) an explicit list of four aspects intentionally outside OWL expressivity (temporal reasoning, derived state, preconditions, cryptographic integrity), and (v) a clarification that SHACL would govern L1 schema conformance and L2 template structure, not L3/L4 validation. The fragment is syntax-checked but not yet ROBOT-validated; this is future work (FW1).

---

## Q7. Provide quantitative comparisons to nanopublications with trusty URIs and transparency logs regarding append/verify latency, storage overhead, and audit workflows.

**Response.** We have added a new subsection §2.5 "Transparency Logs and Software Supply Chain" that compares ADL Lite to Certificate Transparency, Sigstore/Rekor, in-toto, and SLSA. Transparency logs use Merkle trees for O(log n) inclusion proofs and O(1) consistency proofs, making them highly scalable for globally distributed verification. ADL Lite's linear chain requires O(n) sequential verification, representing a deliberate trade-off for Markdown-native, lightweight deployment. The table in §2.5 now includes a "Transparency logs" row. The comparison is also discussed in §6.7 (PROV-O loss analysis). We acknowledge that Merkle-tree batching is planned for Phase 2 (FW4) to bridge this gap for cross-repository verification.

---

## Q8. Plans for integrating cryptographic identities (DIDs, Ed25519) with event signing and repository attestations. How will this change governance claims?

**Response.** This is addressed in §4.1 (Trust Model) and §7.2 (Future Work). Phase 1.5 (implemented, pre-release) provides minimal did:key resolution and Ed25519 signature verification in the signature field. Phase 2 (planned) will add a full key registry (key_registry.py) with KEY_ROTATE and KEY_REVOKE events, DID document storage (did:web, did:ethr), and W3C Linked Data Proofs. Phase 3 (future) adds BFT transport (Blocklace DAG), Merkle-tree batch verification, and the Ontological Assertion Market (staking/slashing). Authenticated identities would change the threat model: Sybil attacks (L3a) become impossible, and collusion cost rises to economic stakes. The current collaborative-audit model is intentionally limited to non-Byzantine agents; the phased roadmap provides a clear path to stronger guarantees.

---

## Summary of Changes to the Paper

| Section | Change | Reviewer concern |
|---------|--------|----------------|
| §3.4.4 | Replaced confidence=0 revocation with dedicated REVOKE event | Q3 (epistemic weakening) |
| §4.1 | Added genesis hash stability paragraph | Q2 (identity bifurcation) |
| §4.2, §4.5 | Corrected γ complexity: O(1) → O(\|V\|) ≤ O(n); added memoization clarification | Q1 (complexity) |
| §4.8 | Added explicit assumptions (A1–A5) for CRDT convergence | Q4, Q5 (assumptions) |
| §4.8 | Added CRDT set vs. linear chain separation explanation | Q5 (CRDT interaction) |
| §2.5 | New subsection on transparency logs (CT, Sigstore, in-toto, SLSA) | Q7 (comparisons) |
| Appendix A | Expanded with competency questions, L3 axioms, OWL limitations, SHACL usage | Q6 (OWL fragment) |
| §4.1, §7.2 | Clarified authentication roadmap (did:key, Ed25519, Merkle trees) | Q8 (cryptographic identity) |
| models.py | Added REVOKE to EventType enum | Implementation |
| adl_core_ontology.yaml | Added REVOKE, RELATE, EVIDENCE, SEAL actions | Implementation |
| references.bib | Added RFC 6962, Sigstore, in-toto, SLSA citations | New references |

---

## Overall Response to Assessment

The reviewer recommended a **weak accept**, noting that the paper is "a solid foundation paper with clear value to the applied ontology community, meriting acceptance after addressing clarifications and strengthening the formal/external comparisons." We believe the revised paper addresses all identified weaknesses:

1. **The conceptual problem** (confidence=0 as revocation flag) has been resolved by introducing a dedicated REVOKE event type, with the old semantics preserved as an alternative.
2. **The complexity claims** have been corrected and clarified.
3. **The formal assumptions** have been explicitly stated.
4. **The external comparisons** have been strengthened with transparency logs and quantitative comparisons.
5. **The OWL fragment** has been expanded with competency questions and scope clarification.
6. **The authentication roadmap** has been clarified with concrete phases.

We thank the reviewer for the constructive feedback, which has significantly improved the paper's clarity and rigor.
