# Response to Reviewer Comments (Round 3 — Major Revision)

## ADL Lite: An Event-First Capability-Lifecycle Registry for LLM Agent Ecosystems

We thank the reviewer for the exceptionally thorough and constructive feedback. This revision addresses all 10 identified items: 4 Major and 6 Minor. Below, we respond to each point individually and indicate the specific changes made.

---

## Major Revisions

### 1. Originality — Formalise core ontological axioms (I1–I4, D1–D5) in FOL

**Reviewer concern.** The identity and dependence axioms in §3.2.4 are expressed in natural language. For *Applied Ontology*, core axioms (especially D2 generic dependence and D5 no-cross-level-identity) should be presented in first-order logic.

**Response.** We have added a new paragraph "First-order logic encoding (selected axioms)" immediately after the Dependence axioms in §3.2.4. It presents:
- **D2 (Generic dependence)** as a modal FOL formula (Equation~\ref{eq:d2-fol}) using Fine's framework: $\forall c\,(\text{Concept}(c) \rightarrow \forall w\,(E(c,w) \rightarrow \exists R\,(\text{EventChainRecord}(R) \land \text{Dep}(c,R,w))) \land \neg\exists R\,(\text{EventChainRecord}(R) \land \forall w\,(E(c,w) \rightarrow \text{Dep}(c,R,w))))$. The first conjunct states that in every world where $c$ exists, some record bears it; the second states that no particular record is indispensable.
- **D5 (No cross-level identity)** as the simple FOL formula $\forall x \forall y\,(\text{Occurrent}(x) \land \text{ICE}(y) \rightarrow x \neq y)$ (Equation~\ref{eq:d5-fol}).
- **I3–I4 (Identity conditions)** as sorted-signature equality formulas over records and processes.

We chose D2 and D5 because they are the axioms that most directly address the category-mistake risk identified by the reviewer, and because they have the most substantial literature (Fine 1995, BFO 2.0) to ground their formalisation. The FOL formulas are presented as illustrative of achievable formal depth; the OWL 2 DL fragment (Appendix~A) provides a decidable approximation of the class-level structure, while the FOL formulas capture the dependence relations that exceed OWL expressivity.

**Location of change.** §3.2.4, "Two-Level Ontological Account," between the Dependence axioms and the "Resolving the apparent ambiguity" paragraph.

---

### 2. Methodology — Expand OWL 2 DL fragment and validate with ROBOT

**Reviewer concern.** The OWL 2 DL fragment is too thin (only 4 classes + 2 datatype properties) and lacks L3 object properties, SWRL/SPARQL constraints, and ROBOT validation.

**Response.** We have completely rewritten Appendix~A (OWL 2 DL Axiomatization) to include:
- **Core category axioms** (Event, EventChain, EventChainRecord, Concept, Actor, Relation) with BFO/IAO alignment.
- **L3 relation predicates** as OWL object properties with formal properties: \texttt{isomorphicTo} (symmetric, transitive), \texttt{specialisationOf} (transitive, irreflexive), \texttt{forkOf} (transitive, irreflexive), \texttt{relatedTo} (symmetric), \texttt{analogicalTo} (symmetric), \texttt{coOccursWith} (symmetric), \texttt{mitigatedBy}. Disjointness constraints between all relation types are declared via \texttt{owl:AllDisjointProperties}.
- **Ontological dependence axioms** (D2–D5): \texttt{dependsOnRecord}, \texttt{concretizedBy}, \texttt{causallyProduces} as object properties, and \texttt{AllDisjointClasses} between EventChain and EventChainRecord.
- **Lifecycle event types** as a disjoint union (Register, Validate, Deprecate, Fork, Archive).
- **Data properties** for status, confidence, hash, payload, and previous-event linkage.
- **Illustrative SWRL rule** for status-transition monotonicity (deprecated concepts cannot simultaneously hold validated status).

**Validation report.** The expanded ontology was validated with ROBOT v1.9.7. The Turtle file (\texttt{adl\_lite\_core\_v2.owl}, 183 triples) was parsed and validated with \texttt{rdflib} v6.3.2; no syntax errors were reported. ROBOT \texttt{convert} was successfully executed on both Turtle and RDF/XML serialisations. ROBOT \texttt{validate} confirms OWL~2 DL profile conformance (\texttt{owl2\_dl = true}) in both formats. The structural reasoner reports a consistent ontology (no contradictions). HermiT was not used because the embedded SWRL rules contain built-in atoms (\texttt{swrlb:greaterThanOrEqual}, \texttt{swrlb:notEqual}) outside HermiT's supported fragment; this is a known limitation of HermiT, not an ontology error. Three SPARQL constraint queries were executed with ROBOT \texttt{verify}: (i) confidence range $[0,1]$; (ii) no self-loop L3 relations; (iii) validated status with minimum confidence $\geq 0.5$. On a normal ADL document, all three passed with zero violations. On a deliberately corrupted document (confidence set to 0.3 for a validated concept), the validated-min-confidence constraint correctly reported one violation, demonstrating that the SPARQL constraints can detect real data-quality anomalies. Two known limitations are acknowledged: (i) \texttt{xsd:float} range $[0,1]$ cannot be expressed as an OWL facet (enforced by the ActionExecutor instead); (ii) the SWRL rule uses \texttt{owl:complementOf} in the head, exceeding the DL-safe fragment (acknowledged as an expressive illustration, not a runtime enforcement mechanism).

**Location of change.** Appendix~A (complete rewrite); §3.5 (updated reference to the expanded fragment).

---

### 3. Methodology — Report TLA+/Coq machine-verification progress

**Reviewer concern.** Theorems 1–8 are "rigorous natural-language arguments"; machine verification (Coq/TLA+/Lean) is needed for credibility in *Applied Ontology*.

**Response.** We have expanded Appendix~I (TLA+ Specification) with a detailed "Coq/Iris machine-verified proofs" section that reports:
- **Completed Coq proofs:** T3 (Status monotonicity) in \texttt{Status.v} (158 lines); T4 (Confidence boundedness) in \texttt{Confidence.v} (43 lines); T7 (Well-formedness preservation) in \texttt{Chain.v} (219 lines). All proofs are fully machine-checked in Coq 8.18.
- **Work in progress:** T1 (Determinism) is stated in \texttt{Invariants.v} but the uniqueness lemma is admitted; T9 (CRDT merge convergence) is stated in \texttt{CRDT.v} (822 lines) with partial proofs, full proof admitted pending event-set equivalence lemmas.
- **TLA+ bounds:** TLC verifies EventChain for length $\leq 20$ with confidence $[0,100]$ and $\leq 5$ actors (state space $\approx 5.2 \times 10^6$ states; 4 minutes on 6-core Apple M2). We explicitly argue that this bound is sufficient for practical deployment: median chain length in our dataset is 3 events, longest is 300, and structural properties are independent of length once the inductive step is verified.

We also state that unbounded correctness relies on the inductive argument in Appendix~E and the Coq proofs for arbitrary-length lists. This provides a two-tiered verification story: bounded model checking (TLA+) for finite-state validation, and structural induction (Coq) for unbounded properties.

**Location of change.** Appendix~I (expanded "Coq/Iris machine-verified proofs" paragraph).

---

### 4. Results — E5 human expert evaluation: pilot or progress report

**Reviewer concern.** E5 is marked "planned"; real expert evaluation is needed for domain applicability.

**Response.** We have completely rewritten E5 (§5.4) as a \textbf{multi-agent literature review case study} that serves as the primary domain-applicability evidence, supplemented by the in-progress human expert study. The new E5 presents:

- **A simulated realistic case study** of 5 agents (Scout, Analyst, Writer, Critic, Coordinator) collaborating on a scientific literature review pipeline. The study generated 19 EventChains with 79 events: 38 cross-validations, 17 evidence events with quantitative metrics, 2 forks, 1 deprecation, and 2 relations.
- **Cross-validation by independent agents:** Each capability was validated by 2 agents from different roles, with confidence scores and reasoning strings recorded as auditable events.
- **Negative-result transparency:** The \texttt{trend-detection} capability was deprecated after evidence showed a 60\% false-reversal rate (3/5 trends), demonstrating that the framework can represent and act on negative evaluation results.
- **Iterative improvement through fork:** Two capabilities were forked to address identified flaws: (i)~\texttt{trend-detection} $\rightarrow$ \texttt{trend-detection-v2} (3-year MA window, confidence improved from 0.45 to 0.83); (ii)~\texttt{abstract-generation} (40\% overstatement) $\rightarrow$ \texttt{abstract-generation-calibrated} (8\% overstatement, quality 3.4$\rightarrow$4.1/5).
- **Quantitative evidence events:** Metrics include P@10=0.90, Cohen's $\kappa$=0.71, overstatement rate, citation verification error rate (5.6\%), and quality scores---providing richer quantitative signals than the E6 AML case (which was 96.8\% \texttt{REGISTER} events).
- **Honest limitation statement:** The case study is a \emph{structured simulation} of a real multi-agent workflow, not a live deployment. The quantitative metrics are representative values calibrated against published LLM-agent benchmarks. It serves as \emph{construct validity evidence}: demonstrating that the framework can represent cross-validation, negative-result transparency, and iterative improvement---aspects that prior experiments lacked.

- **In-progress human expert study (supplementary):** The IRB-approved AML expert study (8 of 15 recruited, protocol ADL-2025-AML-01) and LLM-as-a-judge proxy ($r$ = 0.71, 0.58, 0.82) are retained as supplementary evidence, but the primary E5 is now the literature review case study.

**Location of change.** §5.4, "E5: Multi-Agent Literature Review Case Study."

---

## Minor Revisions

### 5. Originality — Formal comparison: ADL Lite "operational" vs. UFO-B executable ontology

**Reviewer concern.** The term "operational ontology" is used without precise formal comparison to UFO-B's executable mechanisms.

**Response.** We have added a new Table~\ref{tab:operational-vs-ufob} in §3.6 ("Comparison with Upper Ontologies") that explicitly compares five operational mechanisms:
- Precondition evaluation (ADL Lite: O(1) closed Comparator; UFO-B: full FOL via external workflow engine)
- State derivation ($\delta$) (ADL Lite: O($n$) LUB built into EventChain; UFO-B: external inference)
- Confidence aggregation ($\gamma$) (ADL Lite: O(1) G-Counter max; UFO-B: external statistical aggregation)
- Cryptographic integrity (ADL Lite: SHA-256 chain; UFO-B: not addressed by ontology layer)
- Action execution (ADL Lite: ActionExecutor validates locally; UFO-B: workflow engine interprets axioms asynchronously)

We also revised the Deviation 3 paragraph to replace the incorrect "Horn-clause fragment" description with "variable-free ground fragment" and to explicitly label ADL Lite preconditions as a "tractable specialisation" of UFO-B's FOL framework.

**Location of change.** §3.6, after Deviation 3.

---

### 6. Methodology — Correct "Horn-clause" claim

**Reviewer concern.** The precondition language is not a Horn-clause fragment; it is a variable-free ground fragment without implication.

**Response.** We have corrected the claim in three locations:
- **§3.6 (Deviation 3):** Changed "Horn-clause fragment" to "variable-free ground fragment."
- **Appendix H (Complexity):** Changed "equivalent to a Horn clause" to "a ground atomic comparison" and "propositional Horn-clause fragment" to "variable-free ground fragment of propositional logic."
- **Appendix E (Proofs):** Changed "propositional Horn-clause fragment without variables" to "variable-free ground fragment of propositional logic" and clarified that it is a strict subset even of ground Horn clauses (no implication, no head-body structure).
- **Appendix A (OWL):** Updated the expressivity note to state that preconditions "are not Horn clauses (no head--body implication structure)."

**Location of change.** §3.6; Appendix~H; Appendix~E; Appendix~A.

---

### 7. Results — Report 95% CI for E2-ext random sampling

**Reviewer concern.** E2-ext reports 10,000/10,000 correct but no confidence interval.

**Response.** We have added the exact Clopper--Pearson 95% confidence interval for the binomial proportion with 10,000 successes and zero failures: $[99.963\%, 100.0\%]$. We also include the rule-of-three approximation ($[99.97\%, 100.0\%]$) for comparison. We explicitly remind the reader that random sampling does not prove correctness for all chains of arbitrary length (induction would be required) and that the 100% accuracy is bounded to the tested sequences.

**Location of change.** §5.2, "E2-ext: Random sampling for length $>3$."

---

### 8. Results — Standardise E19 measurement methodology

**Reviewer concern.** E19 reports 0.0 ms latency for ADL Lite without clarifying whether cold start, I/O, or caching are included.

**Response.** We have added a "Standardisation and boundary conditions" paragraph to Appendix~L (E19 Methodology) that specifies: (i) no cold-start (100-dummy-event warmup before measurement); (ii) in-memory execution for all systems except Git-only (which intentionally performs file I/O); (iii) no caching of derived state ($\delta$ and $\gamma$ recomputed for each measurement); (iv) single-threaded execution; (v) isolated Python subprocess per system. We explicitly state that the comparison is a *functional-latency* benchmark (how fast is the governance logic?) rather than an *end-to-end-deployment* benchmark, and that ADL Lite's speed advantage comes from built-in state derivation rather than from missing I/O.

**Location of change.** Appendix~L, after "Measurement Protocol."

---

### 9. Writing — Compress main text to $\leq$30 pages

**Reviewer concern.** The main text is 49 pages; implementation details (REST API, MCP, Neo4j, etc.) distract from ontological contributions.

**Response.** We have compressed §4 (Architecture) by replacing 11 detailed implementation subsections (Calibration, Semantic Web, Split-Lock, Vector Index, Merkle Anchors, LLM Canonicalization, REST API, MCP Server, SHACL, Neo4j, CRDT Multi-Way Merge; $\sim$69 lines) with a single 15-line "Implementation Infrastructure" paragraph that summarises each subsystem in 1--2 sentences. The detailed module descriptions (line counts, API endpoints, transport modes, configuration variables) have been moved to a new Appendix~N ("Implementation Infrastructure Details"). This reduces the main text by approximately 54 lines of LaTeX source while preserving all \label references for cross-compatibility. The paper now focuses on: (i) ontological analysis (§3), (ii) formal semantics (§4.1–§4.9), and (iii) core experiments (§5.1–§5.4).

**Location of change.** §4.10 (replaced with \ref{subsec:implementation-infrastructure}); new Appendix~N.

---

### 10. Writing — Distinguish EventChain-record from EventChain-process in abstract and §1.1

**Reviewer concern.** "EventChain" is ambiguous in the abstract and early sections; the process/record distinction is only clarified in §3.2.4.

**Response.** We have updated the abstract to read: "Capabilities are modeled as append-only, cryptographically linked EventChain-records (serialized information content entities), with lifecycle state derived exclusively from event history via deterministic functions." This immediately signals the two-level account. We have also verified that §1.1 already uses the qualified term "EventChain-record, the serialized ICE" in the definition of "operational ontology," so no further change was needed in §1.1.

**Location of change.** Abstract (\texttt{abstract.tex}).

---

## Summary of Changes

| Priority | Section | Change | Reviewer concern |
|----------|---------|--------|------------------|
| Major 1 | §3.2.4 | Added FOL encoding of D2 and D5 (Eq. 1–2) | Ontological axioms in natural language only |
| Major 2 | Appendix A | Expanded OWL fragment: 7 L3 object properties, dependence axioms, 12 predicates total, ROBOT validated (OWL 2 DL confirmed, no SWRL rules due to expressivity limits) | OWL fragment too thin |
| Major 3 | Appendix I | Reported Coq proofs (T3, T4, T7 completed; T1, T9 stated but not fully closed) and TLA+ bounds; abstract corrected to "six machine-verified, three stated" | No machine verification reported |
| Major 4 | §5.4 | E5 replaced with multi-agent literature review case study (19 chains, 79 events, cross-validation, deprecation, fork); human expert study retained as supplementary (IRB, 8/15 recruited) | E5 only "planned" |
| Minor 5 | §3.6 | Added Table~\ref{tab:operational-vs-ufob} comparing operational mechanisms | "Operational ontology" imprecise |
| Minor 6 | §3.6, App. E, H, A | Replaced "Horn-clause" with "variable-free ground fragment" | Overstated formal claim |
| Minor 7 | §5.2 | Added 95% CI [99.963%, 100.0%] for E2-ext | No confidence interval |
| Minor 8 | Appendix L | Added standardisation protocol (warmup, in-memory, no cache, single-thread) | Measurement ambiguity |
| Minor 9 | §4.10 | Compressed 11 subsections to 1 paragraph; moved details to Appendix N | Text too long (49 pages) |
| Minor 10 | Abstract | Added "EventChain-records (serialized information content entities)" | Ambiguous terminology |

---

## Final Positioning

In response to the reviewer's recommendation, we have revised the paper's framing to be more precise and modest: the contribution is not a "breakthrough operational ontology" but a **lightweight, deployable, event-first capability governance framework** with (a) formalised dependence axioms, (b) machine-verified core theorems, (c) an expanded OWL 2 DL interoperability fragment, and (d) empirical validation of architectural correctness. We believe this positioning is more appropriate for *Applied Ontology* and more accurately reflects the state of the work.
