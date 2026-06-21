# ADL Lite — External Reviewer Brief: Formal Semantics

> **Role:** Formal Semantics / Logic Reviewer  
> **Focus:** Theorem 1–8, proof sketches (Appendix E), precondition language (§4.3), formal derivation semantics (§4.4), TLA+ specification (Appendix I)  
> **Paper length:** 49 pages (main) + 21 pages (supplementary)  
> **Target venue:** Applied Ontology (ESWC/ISWC 2027 track)

---

## Paper Summary (for Reviewer Context)

ADL Lite proposes an **event-first** capability-lifecycle registry for multi-agent LLM ecosystems. The core formal object is the **EventChain**: an append-only, cryptographically linked sequence of events. Every concept (capability, relation, discovery) is an EventChain; its status, confidence, and validator set are **derived** from the chain via deterministic functions $\delta(C)$ and $\gamma(C)$, never stored as mutable fields.

The paper states **8 theorems** (Theorems 1–6 core, 7–8 auxiliary) plus 2 lemmas and 1 corollary in the supplementary material. All proofs are **natural-language argument sketches**; machine-checked proofs (Coq/TLA+) are scoped to future work.

---

## Sections to Focus On

| Section | Lines | What to Check |
|---------|-------|---------------|
| §4.4 Formal Derivation Semantics | ~65 lines | Theorem statements, definitions of $\delta$, $\gamma$, well-formedness |
| §4.3 Formal Precondition Language | ~40 lines | Theorem 8 (complexity), comparator semantics, decidability claims |
| §4.5 Comparison with Formal Event Frameworks | ~15 lines | Event Calculus / DL-Lite$_{\\mathcal{R}}$ claims |
| Appendix E (Proof Sketches) | ~320 lines | Full proofs for 6 core theorems + CRDT convergence + G-Set corollary |
| Appendix I (TLA+ Spec) | varies | State machine specification, TLC model-checking scope |
| Appendix H (Decidability) | varies | Complexity class membership (**P**), Horn-clause fragment claim |

---

## Concrete Review Questions (Checklist)

### Theorem Statements

- [ ] **Theorem 1 (Determinism):** Is the claim that $\delta(C)$ is "computable in $O(|C|)$ time" correct? The text says "scanning the chain once" — is this sufficient given the filter to $C_{\\text{life}}$?
- [ ] **Theorem 2 (Confluence under Fork):** Does the theorem correctly handle the case where $C$ has no lifecycle events? (Edge case: empty $C_{\\text{life}}$ after fork?)
- [ ] **Theorem 3 (Transition Monotonicity):** The theorem uses "valid iff" — is this a biconditional? Check whether the ActionExecutor precondition system is *complete* (no false negatives) as assumed in the proof.
- [ ] **Theorem 4 (Boundedness):** The proof assumes $c_{\\text{base}} \\in [0.5, 1]$ because of the precondition $c \\geq 0.5$. Is this precondition *always* enforced before the theorem is invoked, or could a malformed event violate it?
- [ ] **Theorem 5 (Monotonicity):** The theorem requires "new non-colluding actor with confidence $\\geq c_{\\text{base}}$". Is the "non-colluding" qualifier formalized anywhere, or is it an operational assumption?
- [ ] **Theorem 6 (Status–Confidence Consistency):** The claim is $\gamma(C) \\geq 0.5$ when $\delta(C) = \\text{validated}$. Is the lower bound $0.5$ or $>0$? The main text says $\\geq 0.5$; the proof in Appendix E establishes $>0$ but the tighter bound is stated.
- [ ] **Theorem 7 (Well-Formedness Preservation):** This theorem is numbered "7" in §4.4. ~~but "Theorem~7 (CRDT Convergence)" appears in §4.4.5. **There are two Theorem 7s.**~~ This was a numbering error that has been fixed: CRDT Convergence is now **Theorem~9**. Verify that all references to Theorem~9 (CRDT Convergence) are correct and consistent across the paper.
- [ ] **Theorem 8 (Precondition Evaluation):** The $\\mathcal{O}(1)$ claim assumes "derived snapshot is cached." Is this assumption made explicit in the theorem statement? What if the snapshot is not cached?

### Proof Rigor

- [ ] **Proof structure:** Are the proofs in Appendix E truly *sketches* or *complete proofs*? The paper says "rigorous natural-language argument" — does this meet the venue's standard?
- [ ] **Induction base cases:** Theorem 3 (Monotonicity of Status) uses structural induction. Is the base case ($C = [e_1]$) correctly handled? What about the empty chain?
- [ ] **Assumption traceability:** Each proof ends with "Assumptions used: (A1), (A2), (A3)..." Are these assumptions all discharged or verified elsewhere in the paper?
- [ ] **Lemma 1 (Collusion Upper Bound):** The lemma is stated in §4.6.2 but proved by reference to Appendix E. Is the proof in Appendix E actually present? (Check: it is not — Appendix E only covers the 6 core theorems + CRDT + corollary. The lemma proof is inline in §4.6.2.)
- [ ] **Corollary (G-Set CRDT):** The corollary in Appendix E depends on the immutability of events. Is the immutability claim established as an axiom or as a property of the implementation?

### Formalism Gaps

- [ ] **Well-formedness predicate ($\\text{WF}(C)$):** The paper lists 8 axioms but only summarizes them in Table 4. The full conjunctive formalization is "in Appendix E." Is it actually there? (Check Appendix E: it defines the axioms in the proof of Theorem 7, but not as a standalone list.)
- [ ] **Event alphabet closure:** Theorem 1 assumes $\\Sigma_{\\text{life}}$ is "closed" (no extension). Is this a formal assumption or an implementation constraint? What happens if the ontology is extended?
- [ ] **Confidence aggregation parameters:** The paper uses fixed $\beta = 0.05$ and $c_{\\min} = 0.5$. Appendix E provides a sensitivity table. Is there a theorem that guarantees correctness for all parameter combinations in the table, or only for the default values?
- [ ] **TLA+ scope:** The paper says "TLC verifies Theorems 1–3 for all event sequences of length $\\leq 20$." Is this sufficient? What about unbounded chains? The paper admits this is a limitation — is it adequately acknowledged?
- [ ] **Horn-clause fragment claim:** §4.5 and Appendix H claim preconditions are a Horn-clause fragment of FOL. Is this formally justified? Each precondition rule is a single atomic comparison, but the *conjunction* of rules is not a Horn clause in the standard sense (no implication to a head predicate).

### Notation & Consistency

- [ ] **Notation drift:** In §4.4, the paper uses $\\tau$ for event type; in Appendix E, it uses $\\textit{type}$. Are these the same?
- [ ] **$\\oplus$ operator:** Used for chain append in §4.4. Is it defined as a list concatenation, or does it include well-formedness checking? The proof of Theorem 7 suggests it includes checking.
- [ ] **$\\text{actors}(V)$ vs. $\\textit{actors}(V)$:** Notation switches between text and math mode. Is this intentional?
- [ ] **Theorem 7 duplication:** As noted above, there are two distinct theorems numbered 7. This needs renumbering (e.g., Well-Formedness Preservation as Theorem 7, CRDT Convergence as Theorem 9).

---

## Known Issues to Flag (Pre-emptive Honesty)

1. ~~**Two Theorem 7s:**~~ **FIXED.** The CRDT Convergence theorem has been renumbered to **Theorem 9** across §4.4.5, §1, §6, Appendix E, and Appendix K.
2. **Lemma proofs not in Appendix E:** Lemma 1 and Lemma 2 are proved inline in §4.6.2, not in Appendix E. The paper claims "full details are in Appendix E" for these lemmas, but they are not there.
3. **TLA+ spec not shown in main text:** The paper references Appendix I for the TLA+ specification, but the TLA+ module is not included in the main text. If the venue requires it, we may need to include a truncated spec.
4. **Horn-clause claim may be overstated:** The precondition language is not technically a Horn-clause fragment because there are no rules with heads and bodies; it is a simple conjunction of ground comparisons. The comparison to UFO-B FOL is a conceptual alignment, not a formal embedding.

---

## Deliverable

Please return a **review report** with:
- **Major issues:** Any theorem that is false, incorrectly stated, or has a gap that cannot be filled with a reasonable proof sketch.
- **Minor issues:** Notation inconsistencies, numbering errors, proof sketch omissions that are easily fixable.
- **Questions:** Anything that needs clarification from the authors.
- **Verdict:** Accept / Minor revision / Major revision / Reject (with rationale focused on formal correctness).

---

*Generated: 2025-06-16 | Paper version: v0.3.5 (Month 2, Week 7)*
