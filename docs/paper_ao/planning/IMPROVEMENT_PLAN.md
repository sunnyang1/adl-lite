# ADL Lite Paper Improvement Plan
## Based on Peer Review: Revise-and-Resubmit Strategy

> **Target**: ESWC 2027 / ISWC 2027 / AAMAS 2027  
> **Review Outcome**: Revise and resubmit — focused on formal precision, authenticated provenance, broader empirical validation  
> **Paper State**: Current version addresses reviewer questions in §6.2 but lacks the depth requested in 9 formal questions  
> **Estimated Effort**: 6–8 weeks (full-time equivalent)  

---

## Executive Summary

The reviewer recommends **revise-and-resubmit** with three pillars:

| Pillar | Core Problem | What the Reviewer Wants |
|--------|-------------|------------------------|
| **1. Formal Precision** | δ(C), γ(C), precondition language referenced but not fully defined; complexity, edge cases, decidability missing | Full formal definitions, syntax/semantics, decision procedures, complexity proofs, examples |
| **2. Authenticated Provenance** | Phase 1: string identifiers, no crypto binding, LWW, Git rewriting possible; "verifiable" overstated | Near-term bridge: signed Git commits, periodic anchoring, transparency logs; honest scope of "verifiable" |
| **3. Broader Empirical Validation** | 9.3k events, 19 precondition cases, internal correctness only; no external validity | Multi-author collaboration, adversarial trials, head-to-head benchmarks, usability studies, reproducible scripts |

This plan decomposes every weakness and every question into **atomic, verifiable tasks** with file paths, LaTeX sections, and success criteria.

---

## Part I: Thematic Task Groups (Priority-Ordered)

---

### Group A: Formal Semantics & Precondition Language (P0 — Highest Priority)

> **Reviewer's concern**: "The paper references δ(C), γ(C), well-formedness predicates, and the precondition language but does not show full formal definitions, complexity, or examples in the excerpt."  
> **Question**: "Please formalize the precondition language (syntax, operators, scoping), its decision procedures, and complexity; which fragments are guaranteed decidable and how are cross-chain predicates handled?"

#### A1. Formal Precondition Language Specification (§4.2.3 or new §4.3)

**Target file**: `sections/04_architecture.tex`  
**What to add**: A complete formal specification of the precondition language as a standalone subsection (~1.5 pages).

**Required content**:

```
Syntax (BNF or equivalent):
  precondition ::= rule { "and" rule }
  rule         ::= path comparator value
  path         ::= field { "." field }
  comparator   ::= "EQ" | "NEQ" | "GT" | "GTE" | "LT" | "LTE" | "IN" | "EXISTS"
  value        ::= literal | [ literal { "," literal } ]

Semantics (operational):
  Eval(rule, snapshot) → {true, false, error}
  error cases: path not found, type mismatch, value out of range

Well-formedness predicate WF_pre(precondition):
  - Every path in rule resolves to a known field in the derived snapshot schema
  - No comparator requires a type incompatible with the path's declared type
  - No cross-chain references appear in Phase 1 (scoping restriction)

Decidability proof sketch (Proposition):
  "The precondition language is a decidable fragment with O(1) evaluation time
   per rule and O(k) per precondition, where k = number of rules."
  Proof: Each rule evaluates by direct field lookup (constant time) and
  comparator dispatch (closed enumeration, no recursion, no quantification).
  No rule references unbounded structures; the snapshot is a fixed-size
  finite record. Therefore evaluation always terminates in bounded time.

Cross-chain predicates:
  Phase 1: explicitly disallowed (scoping restriction).
  Phase 2: single-registry cross-chain via concept_id dereference (future work).
  Phase 3: federation via Blocklace DAG merge (future work).
```

**Concrete example to include**:
```yaml
preconditions:
  - field: "status"
    comparator: "EQ"
    value: "provisional"
  - field: "confidence"
    comparator: "GTE"
    value: 0.5
  - field: "validators"
    comparator: "EXISTS"
    value: null
```
Show the full evaluation trace: snapshot → field lookup → comparator dispatch → boolean conjunction.

**Corner cases to document**:
- Empty `validators` list with `EXISTS`: returns false (list empty)
- `NaN` in confidence field: caught by Pydantic validator before precondition evaluation
- `actor` field empty string: rejected by well-formedness axiom (actor ≠ "")
- Cross-chain `concept_id` in payload: ignored by Phase 1 precondition engine

**Success criteria**: A reader can implement the precondition evaluator from this section alone, without reading the Python code.

---

#### A2. Precise δ(C) and γ(C) Definitions with Edge Cases (§4.2.2)

**Target file**: `sections/04_architecture.tex`  
**Current state**: Referenced but not fully formalized in the main text (some in Appendix E).

**What to add**:

**Definition 1 (Status Derivation δ(C))**:
```
δ(C) : EventChain → DiscoveryStatus

Input:  C = [e_1, e_2, ..., e_n]  (ordered by previous_event_id linkage)
Output: s ∈ {provisional, validated, deprecated, forked, archived}

δ(C) =
  ┌ archived      if ∃e_i : e_i.event_type = ARCHIVE
  ├ deprecated    if ∃e_i : e_i.event_type = DEPRECATE
  ├ forked        if ∃e_i : e_i.event_type = FORK
  ├ validated     if ∃e_i : e_i.event_type = VALIDATE
  │                 and no later ARCHIVE / DEPRECATE / FORK
  └ provisional otherwise (including C = [] and C = [REGISTER])

Precedence (left-to-right, highest priority first):
  ARCHIVE > DEPRECATE > FORK > VALIDATE > provisional

Edge cases:
  - δ([]) = provisional  (empty chain: concept not yet registered)
  - δ([REGISTER]) = provisional
  - δ([REGISTER, VALIDATE, VALIDATE]) = validated
  - δ([REGISTER, VALIDATE, DEPRECATE, VALIDATE]) = deprecated
    (second VALIDATE is legal but ignored by δ; the event is still in the chain)
```

**Definition 2 (Confidence Derivation γ(C))**:
```
γ(C) : EventChain → [0, 1]

Input:  C = [e_1, ..., e_n]
Output: c ∈ [0, 1]

Let V = { e_i | e_i.event_type = VALIDATE and e_i.actor ∉ ColludingSet }
  (In Phase 1, ColludingSet is assumed empty; see §4.5.1 for collusion analysis)

Let c_base = 0.5  (default confidence for concepts without explicit VALIDATE)

γ(C) =
  ├ 0.0                     if δ(C) ∈ {deprecated, archived}
  ├ min(1.0, c_base + 0.05 × (|V| - 1))  if |V| ≥ 1
  └ c_base                  if |V| = 0

Explicit formula:
  γ(C) = min(1.0, 0.5 + 0.05 × max(0, |V| - 1))
       = min(1.0, 0.45 + 0.05 × |V|)
```

**Computational complexity**:
```
Proposition: δ(C) and γ(C) are computable in O(n) time, where n = |C|.
Proof: Both functions scan the chain once. δ(C) tracks the highest-priority
lifecycle event seen; γ(C) counts valid VALIDATE events. No backtracking,
no recursion, no quantification. ∎

Proposition: For chains with δ(C) = validated, incremental computation
of δ(C') after appending one event is O(1) amortized.
Proof: The derived snapshot (L1 YAML) is cached. Appending a new event
requires only comparing the new event_type against the current status
and applying the precedence rule. ∎
```

**Edge cases table** (add to text):

| Event sequence | δ(C) | γ(C) | Notes |
|---------------|------|------|-------|
| `[]` | provisional | 0.50 | Empty chain |
| `[REGISTER]` | provisional | 0.50 | No validators |
| `[REGISTER, VALIDATE×1]` | validated | 0.50 | c_base + 0.05×0 |
| `[REGISTER, VALIDATE×2]` | validated | 0.55 | Two distinct validators |
| `[REGISTER, VALIDATE×11]` | validated | 1.00 | Capped at 1.0 |
| `[REGISTER, VALIDATE, DEPRECATE]` | deprecated | 0.00 | DEPRECATE overrides |
| `[REGISTER, VALIDATE, DEPRECATE, VALIDATE]` | deprecated | 0.00 | Second VALIDATE ignored by δ |
| `[REGISTER, VALIDATE, VALIDATE, VALIDATE]` (same actor) | validated | 0.55 | Same actor counts once per §4.5.1 |

**Success criteria**: A formal-methods reviewer can verify δ(C) and γ(C) definitions against the implementation without ambiguity.

---

#### A3. Well-Formedness Predicates (§4.2.1)

**Target file**: `sections/04_architecture.tex`  
**What to add**: Formal well-formedness axioms for EventChains, not just scattered in prose.

```
Definition 3 (Well-Formedness). An EventChain C is well-formed, denoted WF(C), iff:

WF1. Non-empty genesis: e_1.event_type = REGISTER  (if C ≠ [])
WF2. Unique event IDs: ∀i,j : e_i.event_id = e_j.event_id → i = j
WF3. Hash linkage: ∀i > 1 : e_i.previous_event_id = e_{i-1}.event_id
                    and e_i.hash = SHA-256(serialize(e_i))
WF4. Actor non-empty: ∀i : e_i.actor ≠ "" and e_i.actor ≠ null
WF5. Timestamp monotonic: ∀i > 1 : e_i.timestamp ≥ e_{i-1}.timestamp
                          (non-strict: simultaneous events allowed)
WF6. Type closure: ∀i : e_i.event_type ∈ Σ_life ∪ Σ_comm
WF7. Payload type safety: e_i.payload conforms to event_type schema
                          (enforced by Pydantic validator)
```

**Success criteria**: All 7 well-formedness conditions are explicitly listed and cross-referenced to the implementation.

---

### Group B: Authentication, Provenance & Trust Model (P0 — Highest Priority)

> **Reviewer's concern**: "Authentication gap in Phase 1: string identifiers and last-write-wins mean authorship and validator identity are not cryptographically bound; Git history rewriting remains a concern absent external anchoring."  
> **Question**: "In Phase 1, how is validator identity authenticated and how do you mitigate Git history rewriting or chain splicing? Would Git signed commits or periodic anchoring to a transparency log be a feasible near-term bridge to Phase 3?"

#### B1. Honest "Verifiable" Scope — Clarify Terminology (§1.1, §4.5, Abstract)

**Target files**: `sections/abstract.tex`, `sections/01_introduction.tex`, `sections/04_architecture.tex`, `sections/06_discussion.tex`  

**What to do**: Replace all instances of "verifiable" with one of three precise terms:

| Old term | New term | Meaning | Where used |
|---------|----------|---------|------------|
| "verifiable governance" | "tamper-evident governance" | Hash-chain detects modifications | Abstract, §1.1 |
| "verifiable integrity" | "integrity-verifiable" | verify_integrity() returns true/false | §4.2, §5.1 |
| "verifiable provenance" | "auditable provenance" | Events are traceable, not cryptographically signed | §2.2, §6.3 |

**New paragraph in §4.5 (Trust Model)**:  
> "Phase 1 provides **tamper-evidence**, not **tamper-proofing** or **non-repudiation**. The SHA-256 hash chain detects modifications to event order or content (Theorem 1), but it does not authenticate the actor's identity. A malicious actor with repository write access could rewrite Git history, rebase commits, or forge `actor` strings. These attacks are detectable by external observers comparing their local clone against a reference, but they are not prevented by the chain itself. We therefore characterize Phase 1 as a **collaborative non-Byzantine** setting: honest participants detect dishonest modifications, but the system does not cryptographically enforce honesty."

**Success criteria**: A reviewer cannot accuse the paper of overstating security claims.

---

#### B2. Near-Term Authentication Bridge — Git Signed Commits + Transparency Anchoring (§4.5, new §4.5.2, §7.2 FW4)

**Target files**: `sections/04_architecture.tex`, `sections/07_conclusion.tex`  

**What to add**: A concrete, implementable near-term bridge that does not require full DIDs/LD-Proofs.

```
Phase 1.5: Near-Term Authentication Bridge (implementable before Phase 3)

Mechanism 1 — Git Signed Commits:
  - Each actor generates an Ed25519 key pair (ssh-keygen -t ed25519)
  - Git commits containing ADL events are signed with git commit -S
  - The `actor` field in each event contains the key fingerprint
  - verify_integrity() checks: (a) hash chain intact, (b) Git commit
    signature valid, (c) signature key matches event.actor fingerprint
  - Cost: one terminal command per actor; no external infrastructure

Mechanism 2 — Periodic Transparency Anchoring:
  - Daily (or per-release), compute the SHA-256 of the entire registry
    state (all chains concatenated)
  - Anchor this hash to a public transparency log:
    * Option A: GitHub commit SHA (immutable, publicly observable)
    * Option B: sigstore.dev Rekor log (free, open, append-only)
    * Option C: Ethereum L2 calldata (low cost, immutable timestamp)
  - Anyone can verify: the registry has not been tampered with since
    the last anchor by comparing the recomputed hash against the log
  - Cost: one API call per day; <$0.01 per anchor

Threat model addressed:
  - Git history rewriting: detectable via signature mismatch or anchor
    hash mismatch
  - Chain splicing: detectable because the spliced segment's previous_event_id
    will not match the legitimate chain's event_id
  - Impersonation: detectable if the forger cannot produce a valid signature
    for the claimed actor key
  - Replay: detectable because event_id must be unique (WF2)

Threat model NOT addressed (Phase 3):
  - Compromised actor keys (requires revocation + key rotation)
  - Fork equivocation (requires CRDT convergence + LD-Proofs)
  - Eclipse / Sybil attacks (requires reputation or stake)
```

**Implementation note**: The paper does NOT need to implement this. It needs to **formally specify** it as a feasible near-term bridge, show that it addresses the reviewer's concern, and scope Phase 3 to the remaining threats.

**Success criteria**: The reviewer can no longer say "Phase 1 has no authentication." The honest answer is: "Phase 1 has tamper-evidence; Phase 1.5 (specified here) adds signed Git commits + transparency anchoring; Phase 3 adds DIDs/LD-Proofs for full non-repudiation."

---

#### B3. Fork/Confluence Model Beyond LWW — Formal Specification (§4.2.2, §4.4, §6.2 Q2)

> **Question**: "What is the fork/confluence model beyond last-write-wins? How are concurrent branches ordered, and what guarantees are provided if events are appended independently and later merged?"

**Target file**: `sections/04_architecture.tex`  

**What to add**:

```
Definition 4 (Fork Semantics). A fork is a divergence event in a capability's
history, formalized as follows:

  FORK event: e_fork = (event_type=FORK, actor=a, payload={parent_concept_id, reason})
  Parent chain: C_parent = [..., e_fork]  (fork event is appended to parent)
  Child chain:  C_child  = [e_reg]       (fresh REGISTER event)
  where e_reg.payload.parent_concept_id = C_parent.concept_id
  and e_reg.hash links to e_reg itself (genesis of child)

The parent chain continues to exist; the child chain is a new EventChain with
its own concept_id and its own genesis hash. The fork relationship is recorded
bidirectionally: parent knows child via e_fork.payload; child knows parent via
e_reg.payload.

Ordering under concurrent forks:
  When multiple agents fork the same parent concurrently, each produces a
distinct child chain with a distinct concept_id. There is no global ordering
of child chains relative to each other. The event_id tie-breaker applies only
within a single chain, not across chains.

Confluence (Phase 1 — LWW):
  Merge is not supported in Phase 1. The parent and child chains evolve
  independently. "Confluence" is therefore trivial: each chain is a separate
  concept with its own δ/γ. The LWW rule applies only to the parent chain
  when multiple agents append to it concurrently: the first event (by timestamp,
  tie-broken by event_id) is accepted; subsequent events that violate
  preconditions are rejected or trigger a fork-on-conflict.

Confluence (Phase 2 — Registry-level merge):
  If two branches modify the same capability and later need to reconcile,
  the registry operator can issue a MERGE event that appends to both chains
  with a payload containing the merged derived state. This is a manual,
  operator-driven process, not an automatic CRDT.

Confluence (Phase 3 — Blocklace DAG + CRDT):
  See §4.5.1 and FW4. The Blocklace hash DAG provides automatic convergence
  for partial-order events. ADL Lite's δ/γ functions operate at the
  application layer above the convergent transport layer. The DAG guarantees
  that all honest nodes eventually agree on the set of events; ADL Lite
  guarantees that δ/γ are deterministic over any agreed event set.
```

**Success criteria**: The reviewer can no longer ask "what is the fork model beyond LWW?" because the three-phase model is explicit.

---

### Group C: Experimental Rigor & External Validity (P0 — Highest Priority)

> **Reviewer's concern**: "Narrow validation scope: tests focus on internal correctness (derivation, integrity) rather than external validity (how well the registry supports real governance decisions or reduces errors in practice)."  
> **Question**: "How were AML events mapped to capability EventChains? Why is this dataset representative of capability lifecycle governance rather than, say, software tool registries or SKILL.md ecosystems?"  
> **Question**: "What is the empirical methodology behind the nanopublications/Git comparisons (workloads, hardware, metrics), and can you release scripts for reproducibility?"

#### C1. AML Dataset Motivation — Clarify & Justify (§5.5, §6.2 Q7)

**Target file**: `sections/05_empirical_validation.tex`  

**What to add**: A new paragraph in §5.5 (E6) and §6.2 (Q7) explaining the AML dataset choice:

```
Dataset selection rationale. The IBM AML HI-Small dataset was selected for
three reasons relevant to capability-lifecycle governance:

1. Realistic event volume: AML transaction records represent a high-volume,
   low-structure data stream that must be governed (flagged, validated,
   deprecated) by human analysts and automated rules. This mirrors the
   capability-registry scenario where raw data (tool outputs, API responses,
   LLM generations) vastly outnumber governance events.

2. Ground-truth labels: The dataset contains 3,386 suspicious accounts with
   expert-annotated labels, enabling us to simulate a "validation" workflow
   (analyst confirms/disputes a machine-generated suspicion). This is
   structurally analogous to a validator confirming or rejecting a capability
   claim.

3. Open availability: The dataset is publicly available (IBM Data Asset eXchange),
   enabling reproducibility. We explicitly acknowledge that it is a
   **volume stress test**, not a domain validation: we are testing whether the
   registry can handle 9,300 events across 201 chains, not whether our
   laundering-pattern detection is accurate. Domain-level AML effectiveness is
   scoped to future work (E5).

Limitations of this choice:
  - AML transactions are not capabilities; they are data events. The analogy
    is structural (high-volume data + sparse governance), not semantic.
  - A more direct evaluation would use SKILL.md ecosystems or software tool
    registries (e.g., PyPI, npm). We chose AML because of the available
    volume and labels; SKILL.md ecosystems are the next target (FW5).
```

**Success criteria**: The reviewer understands why AML was chosen and acknowledges its structural relevance while accepting its semantic limitations.

---

#### C2. Head-to-Head Benchmark: ADL Lite vs. Nanopub vs. PROV-O (new §5.6)

> **Question**: "Can you provide a normative mapping to PROV-O, SHACL, and RO-Crate (with an example serialization), and clarify round-trip fidelity between Markdown-native ADL and RDF stacks?"  
> The reviewer also wants: "Comparative claims against nanopubs and Git-native systems should include standardized benchmarks."

**Target files**: New experiment file, `sections/05_empirical_validation.tex`  

**What to add**: A new experiment E19 (head-to-head benchmark) with four standardized tasks.

**Task definitions**:
```
T1 — Acceptance workflow: A concept must be accepted by k ≥ 2 validators.
T2 — Retraction workflow: A validated concept must be deprecated with a reason.
T3 — Audit query: At time t, what is the status of concept X and who validated it?
T4 — Consensus threshold: Has concept X reached confidence ≥ 0.7?
```

**Systems to compare**:
```
S1 — ADL Lite (existing code, Python API)
S2 — Nanopublications + Python scripts (rdflib + trusty URI generation)
S3 — PROV-O + Python scripts (rdflib + prov library)
S4 — Git-only baseline (Markdown + Git log parsing, no ADL semantics)
```

**Metrics**:
```
M1 — Developer time (hours to implement each task, measured by author + 1 other)
M2 — Lines of code (excluding comments and tests)
M3 — Task execution latency (ms, end-to-end, cold start)
M4 — Error rate (incorrect task completion / total attempts)
M5 — Audit completeness (fraction of provenance questions answerable)
```

**Hypothesis**: ADL Lite will have lower developer time and lower error rate for lifecycle-governance tasks, at the cost of lower interop with RDF stacks (as measured by S3's ability to answer SPARQL queries).

**Success criteria**: A table in §5.6 with at least 3 systems × 4 tasks × 5 metrics, with honest discussion of where ADL Lite loses (interop, SPARQL queryability).

---

#### C3. Adversarial Trial Suite — Formalize & Expand (§5.7, Appendix C)

> **Reviewer wants**: "Adversarial trials probing impersonation, replay, selective omission (Git rewriting), reordering attacks, and chain splicing, together with ablation of planned Phase 3 mitigations."

**Target file**: `sections/05_empirical_validation.tex`, `sections/appendix_c.tex`  

**What to add**: Expand the 8 attack classes in Appendix C to 12, with explicit threat model mapping.

| Attack class | Description | Phase 1 detection | Phase 1.5 mitigation | Phase 3 mitigation |
|-------------|-------------|-------------------|-------------------|-------------------|
| Content tampering | Modify event payload | ✅ Hash mismatch | ✅ Signed commit | ✅ LD-Proof |
| Reordering | Swap two events | ✅ Hash mismatch | ✅ Signed commit | ✅ LD-Proof |
| Deletion | Remove middle event | ✅ Hash mismatch | ✅ Signed commit | ✅ LD-Proof |
| Replay | Copy event to another chain | ✅ event_id duplicate | ✅ Signed commit | ✅ LD-Proof |
| Impersonation | Forge actor string | ❌ Not detected | ✅ Signature mismatch | ✅ DID verification |
| Git rewriting | Rebase / force-push | ❌ Not detected | ✅ Anchor mismatch | ✅ Transparency log |
| Chain splicing | Join two unrelated chains | ✅ previous_event_id mismatch | ✅ Signed commit | ✅ LD-Proof |
| Hash collision | SHA-256 collision | ⚠️ Theoretical | ⚠️ Theoretical | ⚠️ Theoretical |
| Synthetic injection | Inject fake REGISTER | ❌ Not detected (valid event) | ✅ Signed commit | ✅ Reputation check |
| Scope escalation | Change public→private | ✅ Precondition rejects | ✅ Signed commit | ✅ Authorization check |
| Comparator bypass | Inject via eval exploit | ✅ No eval() | ✅ No eval() | ✅ No eval() |
| Selective omission | Omit own bad events | ❌ Not detected | ⚠️ Partial (anchor) | ✅ Gossip + CRDT |

**Success criteria**: The table shows an honest progression: Phase 1 detects structural attacks but not identity attacks; Phase 1.5 addresses identity; Phase 3 addresses omission and equivocation.

---

#### C4. Multi-Author Collaboration Experiment (new E17 or expand E16)

> **Reviewer wants**: "Multi-author, multi-repo collaboration with branching/merging, and the rate at which preconditions prevent bad lifecycle transitions versus a baseline (e.g., free-form Markdown)."

**Target file**: New experiment file, `sections/05_empirical_validation.tex`  

**What to add**: A multi-agent collaboration experiment simulating 5–10 agents over 3 repos.

```
Experiment E17: Multi-Author Collaboration Simulation

Setup:
  - 5 agents, each with a distinct actor string
  - 3 shared concepts, each in a separate Git repo (simulated)
  - 20 rounds, each round each agent may attempt one action on one concept
  - Actions: REGISTER, VALIDATE, DEPRECATE, FORK, EVIDENCE
  - Precondition enforcement: ON for half the rounds, OFF for half
    (the OFF phase simulates "free-form Markdown" baseline)

Metrics:
  - Good transition rate: valid actions accepted / total valid actions
  - Bad transition prevention: invalid actions rejected / total invalid actions
  - Conflict rate: agents disagreeing on same concept status
  - Recovery time: rounds to resolve a conflict
  - Audit completeness: fraction of actions traceable to actor

Baseline comparison:
  - With preconditions ON: measure bad-transition prevention rate
  - With preconditions OFF (free-form): measure bad-transition rate
  - Compute "precondition effectiveness" = (bad_rate_OFF - bad_rate_ON) / bad_rate_OFF
```

**Success criteria**: The paper reports that preconditions prevent ≥80% of invalid transitions compared to free-form Markdown, with quantitative evidence.

---

#### C5. Reproducibility Package (Appendix D, GitHub repo)

> **Reviewer wants**: "Can you release scripts for reproducibility?"

**Target file**: `sections/appendix_d.tex` (revive from commented-out), `README.md` in repo  

**What to add**:
```
Reproducibility package contents:
  1. requirements.txt: pinned versions of all dependencies
  2. experiment runner: python -m experiments.runner all
  3. Data pipeline: scripts to download IBM AML HI-Small and transform to EventChains
  4. Benchmark scripts: head-to-head comparison driver (S1–S4)
  5. Adversarial test suite: all 12 attack classes with expected pass/fail
  6. LaTeX source: full paper with compiled PDF
  7. Docker image: one-command reproduction environment

Artifact availability statement:
  "All code, data pipelines, and evaluation scripts are available at
   [GitHub/DOI link]. The Docker image reproduces all experiments in
   Table X with one command: docker run adl-lite-repro."
```

**Success criteria**: A reviewer can run `docker run adl-lite-repro` and reproduce all reported experiments.

---

### Group D: Related Work & Standards Integration (P1 — High Priority)

> **Reviewer's concern**: "Missing related work or comparisons: Standards integration (PROV-O, DCAT, ActivityStreams, ODRL); minimal treatment of signed Git commits, TUF/Sigstore anchoring, or transparency logs as near-term remedies."  
> "Overlap with runtime governance: Stronger positioning against recent institutional/policy systems (e.g., Institutional AI, GaaS, COMPASS, UALM) would clarify the interface between registry-level governance and runtime enforcement."

#### D1. Standards Integration — PROV-O, SHACL, RO-Crate, ODRL (§2.2, Appendix A, Appendix B)

**Target files**: `sections/02_related_work.tex`, `sections/appendix_a.tex`, `sections/appendix_b.tex`  

**What to add**:

```
§2.2.4: Standards Integration (new subsection, ~0.5 page)

PROV-O mapping (normative, not just descriptive):
  - Event → prov:Activity (with adl:event_type as prov:type)
  - Actor → prov:Agent (with adl:actor_id as prov:identifier)
  - EventChain → prov:Collection (or prov:Entity with derived membership)
  - SHA-256 hash → adl:hash (datatype property, range xsd:hexBinary)
  - Sequencing → prov:wasInformedBy (previous_event_id)
  - Concept → prov:Entity (with adl:status as prov:label)

RO-Crate integration:
  - An ADL Lite registry can be packaged as an RO-Crate Dataset
  - Each EventChain is an RO-Crate File with metadata
  - The RO-Crate metadata.json describes the registry structure

ODRL alignment (policy layer):
  - ADL Lite preconditions can be translated to ODRL permissions/prohibitions
  - Example: "VALIDATE requires status=provisional" → ODRL permission
    with duty: "precondition: status == provisional"
  - This positions ADL Lite as the enforcement layer for ODRL policies

DCAT alignment (catalog layer):
  - Each capability is a dcat:Dataset
  - The registry is a dcat:Catalog
  - Status and confidence are dcat:quality annotations
```

**Round-trip fidelity analysis** (add to Appendix A):
```
Round-trip fidelity: ADL → PROV-O → ADL
  - Preserved: event sequence, actor, timestamp, hash, event type
  - Lost: δ/γ derivation functions (no PROV-O equivalent)
  - Lost: precondition semantics (no PROV-O equivalent)
  - Lost: confidence aggregation algebra (no PROV-O equivalent)
  - Lost: action side-effects (no PROV-O equivalent)
  - Gained: SPARQL queryability, RDF interop, standard tooling

This is an asymmetric bridge: ADL → PROV-O is a one-way descriptive export;
PROV-O → ADL requires re-implementation of the operational layer.
```

**Success criteria**: The reviewer sees a concrete, normative mapping with explicit loss analysis, not just "we can map to PROV-O."

---

#### D2. Runtime Governance Positioning — Institutional AI, GaaS, COMPASS, UALM (§2.1 or §2.2)

**Target file**: `sections/02_related_work.tex`  

**What to add**: A new subsection "§2.1.4: Runtime Governance and Institutional Systems" (~0.5 page) positioning ADL Lite against the four systems mentioned by the reviewer.

| System | What it does | ADL Lite's relationship |
|--------|-------------|------------------------|
| Institutional AI (2601.11369) | Runtime enforcement with governance graphs and policy engines | ADL Lite is the registry of capabilities to which those policies attach; it provides the historical provenance that policy engines query |
| GaaS (2508.18765) | Governance-as-a-Service with explicit governance graphs | ADL Lite provides the capability governance history; GaaS could consume ADL Lite chains as governance evidence |
| COMPASS (2603.11277) | Multidimensional value alignment at orchestration time | ADL Lite is pre-orchestration: it governs capability claims before they are used in orchestration; COMPASS could query ADL Lite for capability trust scores |
| UALM (2601.15630) | Fleet governance in healthcare | ADL Lite is the capability registry layer; UALM is the fleet-management layer above it; both use event-based provenance |

**Key positioning sentence**:  
> "ADL Lite occupies the **registry layer** between permissioning (KYA) and runtime enforcement (AgentSafe, GaaS). It governs capability claims and their lifecycle history, which higher-level systems query for policy decisions."

**Success criteria**: The reviewer cannot say "ADL Lite's relationship to runtime governance is unclear."

---

### Group E: Ontological Depth & Concept Identity (P1 — High Priority)

> **Question**: "How do you preserve concept identity and dependence conditions across FORK and DEPRECATE events (e.g., when do forks constitute new concepts vs variants, and how is historical dependence represented)?"

#### E1. Concept Identity Across Fork and Deprecate (§3.2.5, §3.2.7)

**Target file**: `sections/03_ontological_analysis.tex`  

**What to add**: A formal definition of identity conditions for concepts, forks, and deprecated concepts.

```
Definition 5 (Concept Identity). A concept K is identified by its genesis event:

  identity(K) = SHA-256(e_1.event_id || e_1.timestamp || e_1.actor)

This is the genesis hash, computed at REGISTER time and immutable thereafter.

Fork identity:
  - A fork creates a NEW concept K' with identity(K') ≠ identity(K)
  - K' is related to K by the relation "fork-of" (from ontology registry)
  - K' is not a variant of K; it is a competing interpretation with independent
    lifecycle (its own δ/γ, its own validators, its own status transitions)
  - The "fork-of" relation is a UFO:Relator that mediates between K and K'

When is a fork a new concept vs. a variant?
  - In ADL Lite, ALL forks are new concepts (new concept_id, new genesis hash)
  - A "variant" would be a sub-class of the original concept, which is not
    supported in Phase 1. Phase 2 may introduce "sub-concept" relations.

Deprecated concept identity:
  - Deprecation does NOT change identity(K). The concept continues to exist
    with its original genesis hash; its status changes to "deprecated".
  - Historical dependence: all events prior to DEPRECATE remain in the chain
    and are part of the concept's identity (they contributed to its genesis hash
    via the hash chain, not directly to the identity function).
  - A deprecated concept can be "re-activated" by a subsequent VALIDATE event
    (if the community decides the deprecation was premature). This is not
    an identity change; it is a status change.
```

**Success criteria**: The reviewer can answer "when do forks constitute new concepts?" with "always, by design."

---

### Group F: Writing & Presentation (P1 — High Priority)

> **Reviewer's concern**: "Missing formalisms: tables and proofs referenced but not visible. Some rhetorical flourishes (Wittgenstein, marketing tone) distract from technical detail."

#### F1. Remove or Deflate Rhetorical Flourishes

**Target files**: `sections/abstract.tex`, `sections/01_introduction.tex`  

**What to do**:

| Location | Current | Change |
|---------|---------|--------|
| Abstract | "Wittgenstein Tractatus §1.1" | Remove or move to §1.1 footnote |
| §1.1 | "The world is the totality of facts, not of things" | Remove; replace with: "Event sourcing treats state as a derived function of history, not as a mutable attribute" |
| Throughout | Marketing tone ("fills a distinct layer", "real and timely gap") | Replace with precise technical claims: "governs capability claims" |
| §1.2 | "fourth route" | Remove; replace with "complementary governance layer" |

**Success criteria**: A formal-methods reviewer will not be distracted by philosophy quotes when looking for technical definitions.

---

#### F2. Ensure All Referenced Tables and Proofs Are Visible

**Target file**: `main.tex` (ensure all `\input` lines are active)  

**What to check**:

| Referenced item | Current status | Action |
|----------------|---------------|--------|
| Table 3 (document model) | Present in §4.1 | Verify |
| Table 4 (ontology-schema mapping) | Present in §4.1.1 | Verify |
| Table 5 (loss analysis) | Present in §6.2 | Verify |
| Table 6 (foundational positioning) | Present in §6.4 | Verify |
| Table 7 (event distribution) | Present in §5.5 | Verify |
| Theorem 1–7 proofs | Appendix E (commented out?) | **UN-COMMENT** or move to supplementary |
| Appendix A (PROV-O) | Commented out | **UN-COMMENT** or move to supplementary |
| Appendix B (SHACL) | Commented out | **UN-COMMENT** or move to supplementary |
| Appendix C (adversarial) | Commented out | **UN-COMMENT** or move to supplementary |
| Appendix D (reproducibility) | Commented out | **UN-COMMENT** or move to supplementary |
| Appendix E (proofs) | Commented out | **UN-COMMENT** or move to supplementary |
| Appendix F (RDF-star) | Commented out | **UN-COMMENT** or move to supplementary |

**Decision**: For ESWC/ISWC (15-page limit), appendices must move to supplementary material. For arXiv, keep them inline. Create a `supplementary.tex` that includes all appendices, and submit both.

**Success criteria**: Every table and proof referenced in the main text is either in the main text or in the supplementary material, with a clear pointer.

---

## Part II: Addressing the 9 Specific Questions

| Q# | Question | Section addressing | Status | Key change |
|----|----------|-------------------|--------|------------|
| Q1 | Formalize precondition language, δ/γ, decision procedures, complexity | §4.2.2, §4.2.3, new §4.3 | Partially addressed → Fully formalized | Add BNF syntax, decidability proof, complexity propositions, evaluation trace example |
| Q2 | Exact fork/merge rules; CRDT for Phase 3 | §4.2.2, §4.4, §6.2 | Partially addressed → Precise definition | Add Definition 4 (fork semantics), three-phase confluence model, explicit LWW limitations |
| Q3 | Machine-readable PROV-O/SHACL mapping with loss analysis | Appendix A, Appendix B, §2.2.4 | Partially addressed → Normative mapping | Add round-trip fidelity analysis, explicit "lost" constructs, RO-Crate/ODRL/DCAT alignment |
| Q4 | Actor identity; LD-Proofs; equivocation prevention | §4.5, new §4.5.2 | Partially addressed → Phase 1.5 bridge | Add signed Git commits + transparency anchoring as near-term feasible bridge |
| Q5 | Clean two-level account (occurrents vs records) | §3.2.5 | Already addressed → Strengthen | Add summary box, axiom table (I1–I4, D1–D5) |
| Q6 | OWL ontology interoperability | §6.2, Appendix A | Partially addressed → Explicit bidirectional bridge | Add OWL → ADL import path, automation scope |
| Q7 | Extension of empirical study | §5.5, §5.6, §5.7 | Partially addressed → Head-to-head + adversarial | Add E19 (benchmark), expand adversarial to 12 attack classes, add multi-agent collaboration |
| Q8 | Formal semantics for relation lifecycle and UFO relators | §3.2.6, §3.2.7 | Partially addressed → Complete | Add relation lifecycle formal semantics (establishment, modification, revocation) |
| Q9 | AML dataset representativeness | §5.5, §6.2 | Not addressed → Justified | Add dataset selection rationale with structural analogy and limitations |

---

## Part III: Implementation Timeline

### Week 1–2: Formal Semantics & Security
- **Day 1–2**: A1 — Precondition language formalization (BNF, semantics, decidability proof)
- **Day 3–4**: A2 — δ(C) and γ(C) full definitions with edge-case table
- **Day 5**: A3 — Well-formedness predicates (WF1–WF7)
- **Day 6–7**: B1 — Honest "verifiable" scope, terminology replacement
- **Day 8–10**: B2 — Phase 1.5 authentication bridge (signed Git commits + transparency anchoring)
- **Day 11–14**: B3 — Fork/confluence formalization (Definition 4)

### Week 3–4: Experiments & Benchmarks
- **Day 15–17**: C1 — AML dataset justification paragraph
- **Day 18–21**: C2 — E19 head-to-head benchmark (implement S2–S4, run T1–T4)
- **Day 22–24**: C3 — Expand adversarial suite to 12 attack classes
- **Day 25–28**: C4 — E17 multi-agent collaboration simulation

### Week 5: Standards & Related Work
- **Day 29–31**: D1 — PROV-O/SHACL/RO-Crate/ODRL normative mapping
- **Day 32–34**: D2 — Runtime governance positioning (Institutional AI, GaaS, COMPASS, UALM)
- **Day 35**: E1 — Concept identity across FORK/DEPRECATE

### Week 6: Writing, Polish & Reproducibility
- **Day 36–38**: F1 — Remove rhetorical flourishes, deflate marketing tone
- **Day 39–40**: F2 — Ensure all tables/proofs visible, supplementary material assembly
- **Day 41–42**: C5 — Reproducibility package (Docker, scripts, README)
- **Day 43–44**: Full paper compile, word count check, reference verification
- **Day 45–46**: Internal review pass: check all 9 questions, all 10 limitations, all tables
- **Day 47–48**: Response letter draft (point-by-point response to reviewer)

---

## Part IV: File Modification Checklist

| File | Action | Priority | Owner |
|------|--------|----------|-------|
| `sections/abstract.tex` | Deflate Wittgenstein; clarify "verifiable" scope | P1 | Author |
| `sections/01_introduction.tex` | Remove "fourth route"; add Phase 1/2/3 roadmap | P1 | Author |
| `sections/02_related_work.tex` | Add D2 (runtime governance); D1 (standards integration); compress existing | P1 | Author |
| `sections/03_ontological_analysis.tex` | Add E1 (identity); strengthen Q5 (two-level account) | P1 | Author |
| `sections/04_architecture.tex` | **Major rewrite**: A1–A3, B2–B3, new §4.5.2 | P0 | Author |
| `sections/05_empirical_validation.tex` | **Major rewrite**: C1, C2 (E19), C3, C4 (E17), C5 | P0 | Author |
| `sections/06_discussion.tex` | Update Q1–Q9 table; add D1/D2 cross-references | P1 | Author |
| `sections/07_conclusion.tex` | Adjust FW4 (Phase 1.5); clarify scope | P2 | Author |
| `sections/appendix_a.tex` | Expand PROV-O mapping with round-trip fidelity | P1 | Author |
| `sections/appendix_b.tex` | Keep SHACL example, add validation trace | P2 | Author |
| `sections/appendix_c.tex` | Expand to 12 attack classes, add threat-model table | P1 | Author |
| `sections/appendix_d.tex` | Revive: reproducibility package description | P1 | Author |
| `sections/appendix_e.tex` | Keep proofs, add δ/γ complexity proofs | P1 | Author |
| `sections/appendix_f.tex` | Keep RDF-star, compress to 1 page | P2 | Author |
| `references.bib` | Add 10+ new citations (Institutional AI, GaaS, COMPASS, UALM, etc.) | P1 | Author |
| `supplementary.tex` | New file: assemble all appendices for supplementary submission | P1 | Author |
| `experiments/e19_governance_benchmark.py` | New: head-to-head benchmark driver | P0 | Author |
| `experiments/e17_multi_agent_collab.py` | New: multi-agent collaboration simulation | P0 | Author |
| `experiments/e18_adversarial_expanded.py` | New: expanded adversarial suite (12 attacks) | P1 | Author |
| `Dockerfile` | New: reproducibility environment | P2 | Author |
| `REPRODUCIBILITY.md` | New: step-by-step reproduction instructions | P1 | Author |

---

## Part V: Risk Assessment & Fallbacks

| Risk | Impact | Probability | Fallback |
|------|--------|-------------|----------|
| E19 benchmark too complex to implement in 4 weeks | High | Medium | Reduce to 2 systems (ADL Lite vs. Git-only) instead of 4 |
| Ed25519 signed Git commits not feasible to test | Medium | Low | Specify formally without implementation; reviewer asked for "feasibility" not implementation |
| TLA+ length-100 state space explosion | Low | Medium | Report length-50 with explicit boundary note; use inductive proof instead |
| Paper exceeds page limit after additions | High | Medium | Move all appendices to supplementary; compress §2 to 60% of current length |
| arXiv IDs for Institutional AI / GaaS / COMPASS / UALM cannot be verified | Medium | Medium | Use Google Scholar citations or conference proceedings instead |
| Multi-agent simulation (E17) produces poor results | Medium | Medium | Report honestly as "negative result"; frame as "governance is hard even with preconditions" |
| δ/γ formalization reveals edge-case bugs | High | Low | Fix bugs, report in "failure cases" (strengthens credibility) |

---

## Part VI: Reviewer Response Letter Outline (Draft)

When resubmitting, include a point-by-point response letter:

```
Dear Editors and Reviewers,

We thank you for the thorough and constructive review. We have revised the
paper along three pillars you identified: (1) formal precision, (2) authenticated
provenance, and (3) broader empirical validation. Below is a point-by-point
response.

---

MAJOR REVISIONS

1. Formalization of precondition language, δ/γ, and complexity (Q1)
   - Added: BNF syntax for precondition language (§4.2.3)
   - Added: Decidability proof (Proposition 1) and O(1) complexity proof
   - Added: Full δ/γ definitions with edge-case table (§4.2.2)
   - Added: Well-formedness predicates WF1–WF7 (§4.2.1)
   - Added: Evaluation trace example showing field lookup → comparator → conjunction

2. Fork/confluence model beyond LWW (Q2)
   - Added: Definition 4 (fork semantics) with parent/child chain formalization
   - Added: Three-phase confluence model (Phase 1: no merge; Phase 2: manual;
     Phase 3: Blocklace DAG + CRDT)
   - Added: Explicit LWW limitations and ordering guarantees

3. Authentication bridge (Q4)
   - Added: Phase 1.5 — near-term feasible bridge using Git signed commits
     (Ed25519) + transparency log anchoring (sigstore.dev / Ethereum L2)
   - Added: Honest threat-model table: Phase 1 detects what? Phase 1.5 mitigates
     what? Phase 3 solves what?
   - Replaced "verifiable" with "tamper-evident" throughout to avoid overstating

4. Head-to-head benchmark (Q3, Q7)
   - Added: E19 experiment — 4 systems × 4 tasks × 5 metrics
   - Added: Normative PROV-O/SHACL/RO-Crate/ODRL mapping with loss analysis
   - Added: Round-trip fidelity analysis (ADL → PROV-O → ADL)
   - Added: Reproducibility package (Docker, scripts, data pipeline)

5. AML dataset justification (Q7, Q9)
   - Added: Explicit dataset selection rationale with structural analogy
   - Added: Honest limitations: "AML is a volume stress test, not domain validation"
   - Added: SKILL.md ecosystems as next target (FW5)

6. Concept identity across FORK/DEPRECATE (Q8)
   - Added: Definition 5 (concept identity via genesis hash)
   - Added: Fork = always new concept; deprecation = status change, not identity
   - Added: Historical dependence preservation via hash chain

7. Standards and runtime governance integration (Q3, related work)
   - Added: §2.2.4 — Standards Integration (PROV-O, RO-Crate, ODRL, DCAT)
   - Added: §2.1.4 — Runtime Governance Positioning (Institutional AI, GaaS,
     COMPASS, UALM) with explicit interface definition

MINOR REVISIONS

- Removed Wittgenstein quote from abstract; moved to §1.1 footnote
- Replaced "fourth route" with "complementary governance layer"
- Replaced marketing tone with precise technical claims
- Verified all referenced tables and proofs are in main text or supplementary
- Added 10+ new citations (2024–2026) to related work

---

We believe the revised paper meets the standards for a revise-and-resubmit
at ESWC/ISWC/AAMAS 2027. The three pillars you identified have been addressed
with formal definitions, feasible near-term authentication, and rigorous
empirical benchmarks.

Sincerely,
Anonymous Authors
```

---

## Summary: What Will Be Different

| Aspect | Current Paper | Revised Paper |
|--------|--------------|---------------|
| **Formalism** | Referenced but not fully shown | Full BNF, definitions, proofs, complexity |
| **Authentication** | "Phase 3 will add DIDs" | Phase 1.5: signed Git + transparency logs (feasible now) |
| **Experiments** | Internal correctness only | Head-to-head benchmark, multi-agent collaboration, adversarial suite |
| **Standards** | "Can map to PROV-O" | Normative mapping with explicit loss analysis, RO-Crate/ODRL/DCAT |
| **Related work** | Descriptive survey | Critical positioning with dimensional comparison tables |
| **Tone** | Philosophical + marketing | Precise technical + honest scope |
| **Reproducibility** | Mentioned | Docker + scripts + data pipeline + artifact availability statement |
