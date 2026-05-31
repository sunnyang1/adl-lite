# ADL Lite: An Event-First Operational Ontology for Multi-Agent Concept Consensus and Knowledge Graph Authoring

**Author Information** [TO BE COMPLETED]
**Affiliations** [TO BE COMPLETED]
**ORCID** [TO BE COMPLETED]
**Corresponding Author** [TO BE COMPLETED]

**Target**: Semantic Web Journal (IOS Press)
**Keywords**: operational ontology, multi-agent consensus, knowledge graph authoring, event-first design, structured semantic anchoring, cryptographic chain integrity

---

## Abstract

The construction of knowledge graphs (KGs) increasingly relies on large language model (LLM) agents for discovery and authoring. However, existing ontology frameworks assume object-first design—concepts are mutable entities with stored properties—which creates fundamental tension with agentic workflows: multiple agents produce competing interpretations, status and confidence become stale fields, and centralized trust is required for validation.

We present ADL Lite, an event-first operational ontology that redefines concepts as append-only chains of typed events. Drawing on Wittgenstein's Tractatus §1.1—"the world is the totality of facts, not of things"—ADL Lite treats every knowledge update as a new event rather than a mutation of existing state. The system provides a four-layer, Markdown-native syntax (L1: YAML Front Matter, L2: Natural Language Prose, L3: Structured Semantic Anchoring blocks, L4: Typed Action blocks with precondition-enforced side effects). We introduce three core mechanisms: (1) Structured Semantic Anchoring (SSA), which constrains the interpretive space of natural language via typed slots derived from a YAML ontology registry; (2) a cryptographic EventChain that derives status, confidence, and validator lists from the chain rather than storing them; and (3) a multi-agent consensus protocol with fork management, isomorphism-based merging, and offline-first edge synchronization using CRDT-inspired timestamp-ordered merge.

We evaluate ADL Lite through six controlled experiments including a 5-agent audit simulation and a real-world AML pipeline, validated by 325 automated tests with 81% code coverage. The framework is implemented in Python 3.10+ with Pydantic v2 types, SQLite-backed hybrid memory indexing, and a Feishu/Lark bridge for real-time agent collaboration. We discuss failure modes, adversarial scenarios, and the relationship between ADL Lite and existing Semantic Web standards including RDF/OWL and PROV-O.

---

## 1. Introduction

Knowledge graphs are increasingly authored not by individual experts but by fleets of large language model (LLM) agents operating in parallel [1, 2]. These agents discover novel concepts, propose semantic relations, and validate each other's findings. This shift from human-centric to agentic KG construction raises a fundamental architectural question: *what is the right primitive for representing knowledge when the authors are autonomous agents rather than human ontologists?*

Existing ontology frameworks—from RDF/OWL [3] to property graphs [4] to Pydantic-based schemas [5]—are designed around an object-first philosophy. A concept is a mutable object with fixed properties: a status field, a confidence score, a list of validators. When an agent validates a concept, it *writes* to that field. When an agent disagrees, it *overwrites* the previous state. This model is natural for human workflows where a single authoritative editor updates a document. It breaks down catastrophically in multi-agent settings:

1. **State conflict**: Two agents simultaneously updating `status` or `confidence` produce race conditions without transaction semantics.
2. **Auditability loss**: The *reasons* for state changes—who validated, when, and why—are lost unless explicitly logged.
3. **Trust centralization**: A central coordinator must arbitrate which agent's write "won," reintroducing the single point of failure that distributed systems sought to eliminate.
4. **Ontology training burden**: Agents must learn formal ontology languages (OWL, SHACL) or structured APIs, creating a barrier to entry.

We argue that the correct primitive for agentic KG authoring is not the *object* but the *event*. This philosophical shift—from "things that have properties" to "facts that happened"—is grounded in Wittgenstein's Tractatus Logico-Philosophicus §1.1: "The world is the totality of facts, not of things" [6]. In an event-first ontology, a concept *is* its event chain. Status, confidence, and validators are not stored fields—they are computed from the chain at query time. An update is not a mutation—it is a new event appended to the chain. This eliminates write-time race conditions and makes audit trails inherent to the data structure; it reduces merge-time non-determinism to consistent-but-arbitrary ordering within timestamp buckets (see §7.3).

ADL Lite (Agent Discovery Language, Lite Edition) is a Markdown-native operational ontology that implements this event-first philosophy. It provides:

1. **A four-layer syntax** (L1-L4) that bridges the gap between human-readable Markdown and machine-parseable semantic annotations, enabling LLM agents to author structured knowledge without formal ontology training.

2. **Structured Semantic Anchoring (SSA)**: Typed slots (YAML fields + L3 blocks) that constrain the interpretive space of natural language, reducing pronoun ambiguity and ensuring cross-agent referential consistency.

3. **Cryptographic EventChain**: An append-only, thread-safe linked list where each event carries a SHA-256 hash linking to its predecessor, providing tamper-evident audit trails without centralized trust.

4. **Multi-agent consensus protocol**: A lifecycle state machine (provisional → validated → deprecated/forked/archived) with fork management, isomorphism-based merging, and offline-first edge synchronization.

5. **Reference implementation**: Python 3.10+ library with Pydantic v2 validation, SQLite-backed hybrid memory (Hot/Warm/Cold), and a Feishu/Lark bridge for real-time agent collaboration.

This paper addresses three research questions:

- **RQ1 (Concurrency):** Can event-first design eliminate race conditions and stale state in multi-agent KG authoring, compared to object-first approaches?
- **RQ2 (Ambiguity):** Does Structured Semantic Anchoring (SSA) reduce cross-agent referential ambiguity in natural language concept descriptions?
- **RQ3 (Consensus):** Is append-only merge (CRDT-inspired) sufficient for offline-first consensus among autonomous agents without centralized coordination?

The remainder of this paper is organized as follows. Section 2 reviews related work in operational ontology, multi-agent consensus, and KG authoring. Section 3 presents the ADL Lite framework, covering the four-layer syntax, EventChain design, and SSA validation. Section 4 describes the consensus protocol and fork management. Section 5 covers the implementation architecture including the memory system, action executor, and real-time watcher. Section 6 presents experimental evaluation, linking each experiment to the research questions. Section 7 discusses limitations, failure modes, and future work. Section 8 concludes.

---

## 2. Related Work

### 2.1 Operational Ontology and Event-First Design

The concept of operational ontology—where the focus shifts from static conceptual models to the *processes* by which concepts are created, validated, and evolved—has roots in process philosophy [7] and event-driven architectures [8]. In the semantic web community, the PROV-O ontology [9] models provenance as entities, activities, and agents, but treats provenance as metadata *about* a concept rather than constituting the concept itself. The Event Ontology [10] and SEM [11] model events as first-class entities but do not extend this to replacing the concept-as-object paradigm.

Wittgenstein's Tractatus [6] provides the philosophical foundation: facts (events) are the world's building blocks, and objects exist only as participants in states of affairs. Our work operationalizes this insight for computational knowledge graphs by making `Event` the fundamental unit of the ontology and deriving all other properties (status, confidence) from the event chain.

### 2.2 Knowledge Graph Authoring by LLM Agents

The operational ontology perspective becomes particularly relevant when KGs are authored by LLM agents, where the creative process of concept discovery is as important as the resulting taxonomy.

Recent work has demonstrated the viability of using LLMs for knowledge graph construction. Pan et al. [1] showed that GPT-4 can extract entities and relations with competitive accuracy. Trajanoska et al. [12] surveyed LLM-based ontology engineering, identifying the gap between LLM-generated natural language and formal ontology requirements. Chen et al. [13] proposed agent-based KG construction with multi-round refinement, but relied on a centralized orchestrator for conflict resolution.

The key gap we address is the *representation format*: existing approaches either (a) require agents to output structured JSON/RDF that is error-prone for LLMs, or (b) accept natural language that is ambiguous for cross-agent comparison. ADL Lite's Markdown-native format sits in the sweet spot: agents write familiar Markdown, and the L3/L4 blocks provide sufficient structure for machine validation. We note that ADL Lite targets the authoring phase of the KG lifecycle—concept discovery and consensus—rather than completion or query answering, where established benchmarks (FB15k, WN18RR, WD50K) and ontology alignment tasks (OAEI) apply.

### 2.3 Consensus in Multi-Agent Systems

Consensus protocols have been extensively studied in distributed systems [14, 15] and multi-agent systems [16]. Reputation-based consensus [17] and voting mechanisms [18] are common in agent societies. However, these protocols typically assume agents are voting on a *proposition* (true/false) rather than collaboratively *building* a concept. ADL Lite's consensus model is inspired by CRDT principles [19]—the append-only EventChain is trivially mergeable because events are facts, not mutations—but we note that derived states (status, confidence) currently use last-writer-wins semantics, not full CRDT lattice joins (see §7.5 for discussion).

### 2.4 Cryptographic Integrity in Knowledge Systems

Blockchain-based approaches [20] have applied cryptographic chain integrity to knowledge graphs, but typically at the cost of significant computational overhead and infrastructure complexity. Content-addressable storage [21] provides integrity but not the event-chain semantics. ADL Lite uses lightweight SHA-256 hashing within each EventChain—no consensus algorithm, no proof-of-work, no distributed ledger—providing tamper evidence without the overhead of full blockchain infrastructure.

### 2.5 Event-Centric RDF and Provenance Models

Several established paradigms in the Semantic Web community already treat assertions with provenance as first-class entities, making them natural reference points for ADL Lite's event-first approach.

**Nanopublications** [24] model individual assertions as immutable, citable, and signed RDF graphs with explicit provenance and publication metadata. Each nanopublication bundles an assertion, its provenance, and a publication record into a single package—conceptually similar to ADL Lite's self-contained events with cryptographic hashing. The key difference is that nanopublications treat each assertion independently, whereas ADL Lite links events into a causal chain: Event $e_i$ is not merely timestamped but cryptographically bound to its predecessor $e_{i-1}$. Additionally, nanopublications require RDF expertise for authoring; ADL Lite's Markdown-native syntax targets LLM agents.

**RDF-star and reification** [25] allow statements about statements within the RDF data model, enabling provenance annotations without leaving the triple paradigm. While RDF-star provides syntax for annotating triples with metadata (e.g., confidence, source), it does not prescribe an event-chain structure or lifecycle state machine—these are application-level concerns that ADL Lite encapsulates.

**Wikidata's edit history** [26] demonstrates event-first thinking at scale: every edit is recorded as a revision with timestamp, editor identity, and diff content. Concepts are reconstructed from their edit history rather than stored as mutable objects. ADL Lite generalizes this pattern from human-curated editing to agent-driven authoring, adding cryptographic chain integrity (Wikidata uses database-level versioning), fork management (Wikidata has edit wars but no structured fork resolution), and a portable Markdown format (Wikidata edits are JSON blobs tied to a specific platform).

**RDF change sets and versioning** [27] provide mechanisms for representing deltas between RDF graph versions. These are complementary to ADL Lite: an EventChain can be compiled into an RDF change set, enabling integration with existing RDF versioning toolchains. The distinction is that ADL Lite's events carry semantic types (REGISTER, VALIDATE, FORK) beyond simple add/delete operations, embedding the *intent* and *reasoning* of each change.

---

## 3. The ADL Lite Framework

### 3.1 Design Philosophy

ADL Lite is grounded in three design principles derived from the requirements of agentic KG authoring:

**P1: Event-first.** The fundamental unit of the ontology is the `Event`, not the concept. A concept *is* its `EventChain`. Properties like `status`, `confidence`, and `validators` are computed from the chain at query time. This eliminates stale state, race conditions, and lost audit trails.

**P2: Agent-accessible syntax.** The authoring format must be usable by LLM agents without formal ontology training. We choose Markdown because (a) LLMs are extensively trained on Markdown, (b) it is human-readable for inspection and debugging, and (c) it naturally supports the layered structure we need.

**P3: Concurrency-safe.** Multiple agents must be able to work on the same concept simultaneously without coordination. The append-only EventChain, combined with thread-safe locking and CRDT-inspired merge semantics, provides this guarantee.

### 3.2 Four-Layer Syntax

ADL Lite documents use a four-layer syntax that progressively adds structure from human-readable prose to machine-validated actions:

**L1: YAML Front Matter.** The document header provides concept identity, type, and scope. The example below illustrates an anti-money laundering (AML) concept—"Capital Reflux Trap"—discovered through cross-domain isomorphic mapping between financial transaction patterns and neural network attention mechanisms:

```yaml
---
adl_type: discovery
adl_id: disc-capital-trap
status: provisional
confidence: 0.84
novelty: 0.91
domain: financial_aml
mechanism: isomorphic_mapping
scope: public
provisional_names:
  zh: 资本回流陷阱
  en: Capital Reflux Trap
evidence_refs:
  - vecdb://clusters/8912
  - tool://aml_simulator/v2
---
```

**Important (event-first):** The L1 YAML is a *snapshot* derived from the EventChain, not the source of truth. Mutations go through the chain; the snapshot is refreshed after each event.

**L2: Markdown Body.** Free-form natural language for human/LLM prose, supporting `[[Wiki Links]]` for cross-referencing concepts.

**L3: Structured Semantic Anchoring Blocks.** Fenced code blocks with `adl:` prefix provide machine-parseable structure:

````markdown
```adl:relation
source: disc-capital-trap
relation: isomorphic-to
target: disc-gradient-explosion
mapping_type: topological
confidence: 0.91
```
````

L3 supports three block types:
- `adl:relation`: Typed edges between concepts (predicates: isomorphic-to, specialisation-of, co-occurs-with, analogical-to, fork-of, etc.)
- `adl:evidence`: Structured evidence entries with types (vector_cluster, simulator_run, human_expert, cross_reference)
- `adl:seal`: Formal verification references (Lean4/Coq/Z3 proof pointers)

**L4: Action Blocks.** Typed actions with preconditions and side effects:

````markdown
```adl:action
action: validate
actor: agent_3
reasoning: "Cross-domain structural alignment verified"

params:
  confidence_boost: 0.15
```
````

Actions are validated against the ontology registry (`adl_core_ontology.yaml`), which defines allowed-on types, required parameters, preconditions with comparator operators (EQ, NEQ, GT, GTE, LT, LTE, IN, EXISTS), and declared side effects.

### 3.3 EventChain: The Core Data Structure

**Definition 1 (EventChain).** An EventChain $C$ is an ordered sequence of events $C = (e_0, e_1, \ldots, e_n)$ where each event $e_i$ is a tuple:

$$e_i = (\text{id}_i, \text{cid}, \tau_i, a_i, r_i, t_i, p_i, \text{prev}_i, h_i)$$

where:
- $\text{id}_i$ is a unique event identifier. We use full 128-bit UUID4 (32 hex characters), providing $2^{122}$ random bits: collision probability is negligible even for $10^{12}$ events.
- $\text{cid}$ is the concept identifier (constant across the chain)
- $\tau_i \in \text{EventType}$ is the event type
- $a_i$ is the actor (agent) identifier
- $r_i$ is the reasoning string
- $t_i$ is the ISO 8601 UTC timestamp
- $p_i$ is the event-specific payload (dictionary)
- $\text{prev}_i = \text{id}_{i-1}$ for $i > 0$, and $\text{prev}_0 = \text{None}$
- $h_i = \text{SHA-256}(\sigma(e_i) \parallel h_{i-1})$ for $i > 0$, where $\sigma$ serializes the event tuple to canonical JSON sorted by key, and $h_0 = \text{SHA-256}(\sigma(e_0))$

The **integrity invariant** is: $\forall i > 0: \text{prev}_i = \text{id}_{i-1}$ and $h_i = \text{SHA-256}(\sigma(e_i) \parallel h_{i-1})$. This chained construction ensures that modifying any event $e_i$ requires recomputing $h_i, h_{i+1}, \ldots, h_n$—tampering is detectable because the head hash $h_n$ serves as a cryptographic accumulator of the entire chain. A chain $C$ has **integrity** iff both conditions hold for all $i$. The **status derivation function** is:

$$\text{status}(C) = f(\tau_k) \text{ where } k = \max\{i \mid \tau_i \in \mathcal{L}\}$$

where $\mathcal{L} = \{\text{REGISTER}, \text{VALIDATE}, \text{DEPRECATE}, \text{FORK}, \text{ARCHIVE}\}$ is the set of lifecycle event types, and $f$ maps each type to the corresponding `DiscoveryStatus`.

**Concretely in Python:**

```python
class Event(BaseModel):
    event_id: str          # Full 128-bit UUID4 (32 hex chars)
    concept_id: str        # adl_id of the concept
    event_type: EventType  # REGISTER, VALIDATE, DEPRECATE, FORK, ARCHIVE, etc.
    actor: str             # Agent or human identifier
    reasoning: str         # Why this event occurred
    timestamp: str         # ISO 8601 UTC
    payload: dict          # Event-specific data (L3 block fields, action params)
    previous_event_id: str | None  # Link to previous event (None for genesis)
    hash: str              # SHA-256 of event content
```

The EventChain maintains a thread-safe, append-only list of events:

```python
class EventChain:
    def append(self, event: Event) -> None:
        with self._lock:
            if self._events:
                event.previous_event_id = self._events[-1].event_id
                event.hash = ""  # Force recomputation
                event.model_post_init(None)
            self._events.append(event)

    @property
    def status(self) -> DiscoveryStatus:
        """Status computed from the chain — the latest lifecycle event."""
        for event in reversed(self._events):
            type_to_status = {
                EventType.REGISTER: DiscoveryStatus.PROVISIONAL,
                EventType.VALIDATE: DiscoveryStatus.VALIDATED,
                # ...
            }
            if event.event_type in type_to_status:
                return type_to_status[event.event_type]
        return DiscoveryStatus.PROVISIONAL
```

Every computed property—`status`, `confidence`, `validators`, `created_at`, `updated_at`—traverses the chain to derive its value. The chain is the single source of truth; the L1 front matter is a convenience snapshot.

### 3.4 Structured Semantic Anchoring (SSA)

A key challenge in multi-agent knowledge graph construction is ambiguity. When Agent A writes "This mechanism is isomorphic to the attention residual pattern," Agent B cannot resolve "this" without context. SSA addresses this through three mechanisms:

1. **Pronoun prohibition**: The validator detects demonstrative pronouns using pattern-based rules. A curated list of complementizer verbs (e.g., "shows", "indicates", "demonstrates") prevents false positives when "that" introduces a complement clause (e.g., "the data shows that..."). The approach is heuristic rather than linguistically complete—agents may still produce ambiguous references through circumlocutions—but catches the most common sources of referential ambiguity in practice. We evaluated SSA on a benchmark of 29 sentences (13 deliberately ambiguous, 16 clean): **precision 0.812, recall 1.000, F1 0.897**. The three false positives were (a) dummy subject "it" ("It is important that..."), (b) modifying "this" in noun phrases ("this limitation"), and (c) sentence-initial "this" in complementizer contexts.

2. **Typed slots**: Every L1 field and L3 block parameter is typed via Pydantic models, constraining the interpretive space. A `source` field in a relation block must be a non-pronoun string; a `confidence` field must be in [0, 1].

3. **Ontology registry**: A YAML file (`adl_core_ontology.yaml`) defines the closed set of allowed predicates, actions, status transitions, scope prefixes, and mapping types. In strict validation mode, unknown predicates or invalid transitions are rejected, preventing agents from introducing uncontrolled vocabulary.

---

## 4. Multi-Agent Consensus Protocol

### 4.1 Lifecycle State Machine

Concepts progress through a defined lifecycle:

```
provisional ──→ validated ──→ deprecated ──→ archived
     │              │
     └───→ forked ──┘────→ validated/deprecated/archived
```

Valid transitions are enforced by the ontology registry:

| From | Allowed To |
|------|-----------|
| provisional | validated, deprecated, forked, archived |
| validated | deprecated, forked, archived |
| forked | validated, deprecated, archived |
| deprecated | archived |
| archived | (terminal) |

### 4.2 Fork Management

When agents disagree on a concept's interpretation, the `ForkManager` creates a fork: the original concept transitions to `forked` status, and a new concept is registered as the fork. Fork resolution uses three strategies based on the structural similarity of the two concepts' relation graphs.

We measure similarity using **Jaccard similarity on the set of (relation, target) pairs** derived from each concept's L3 relation blocks: $\text{sim}(C_a, C_b) = |E_a \cap E_b| / |E_a \cup E_b|$, where $E_x$ is the set of relation pairs for concept $x$. Resolution strategies are:

- **MERGE** ($\text{sim} \geq 0.90$): The interpretations are structurally equivalent; merge into a single validated concept.
- **PARALLEL** ($\text{sim} < 0.90$): Different domains need different metaphors; keep both as parallel interpretations.
- **PRUNE** (> 180 days idle, > 3 entries): Long-unreferenced concepts are archived.

### 4.3 Offline-First Edge Synchronization

Agent nodes operate in potentially disconnected environments. ADL Lite provides CRDT-inspired eventual consistency:

```python
class SyncManager:
    def merge(self, *chains: EventChain, base_chain: EventChain | None = None):
        # Collect all events, deduplicate by event_id
        # Sort by timestamp then hash for deterministic ordering
        # Rebuild unified chain with correct previous_event_id linking
```

The key insight: because events are append-only facts (not mutations), two diverged chains have no conflicts—only additions. The merge algorithm collects all events, deduplicates identical events (same `event_id`), sorts by timestamp, and rebuilds the chain. This is the same principle that makes CRDTs conflict-free, applied to event sequences.

The `EdgeNode` class composes an EventChain, a `SideEffectQueue` (for buffering network-dependent effects when offline), and connection management:

```python
class EdgeNode:
    def record_event(self, event_type, payload, side_effects=None):
        event = Event(concept_id=self.concept_id, event_type=event_type, ...)
        self.chain.append(event)  # Always succeeds (local, synchronous)
        if side_effects:
            if self._online:
                self._try_effect(se, ...)  # Execute immediately
            else:
                self.queue.enqueue_action(se, ...)  # Buffer for later
        return event
```

---

## 5. Implementation Architecture

### 5.1 System Overview

The ADL Lite reference implementation (Python 3.10+) consists of 23 source modules organized into four layers:

| Layer | Modules | Responsibility |
|-------|---------|----------------|
| **Parsing** | `parser.py` | L1 YAML, L2 Markdown body, L3 `adl:*` blocks, L4 `adl:action` blocks |
| **Models** | `models.py` | Pydantic types: Event, EventChain, ADLDocument, L3/L4 blocks, PreconditionRule |
| **Semantics** | `validator.py`, `ontology.py` | SSA validation, pronoun detection, ontology registry queries |
| **Runtime** | `consensus.py`, `action_executor.py`, `memory.py`, `realtime.py`, `sync_manager.py` | Consensus engine, action dispatch, hybrid memory, real-time pattern detection, edge sync |

### 5.2 Ontology Registry

**Design rationale:** We chose YAML over OWL or JSON Schema for the registry because YAML is natively readable by both humans and LLM agents without specialized tooling, and integrates directly with the PyYAML-based parser.

`adl_core_ontology.yaml` (v0.2) serves as the single source of truth for:

- **5 classes**: discovery, concept, relation, evidence, formal_seal
- **10 predicates**: isomorphic-to, specialisation-of, co-occurs-with, related-to, analogical-to, analogical-transfer, dual-of, fork-of, mitigated-by, indexed-phrase
- **9 actions**: register, validate, fork, deprecate, archive, announce, publish, sync_dashboard, listen
- **4 scope prefixes**: public, private, user, shared
- **Status transitions**: as defined in §4.1

Actions declare preconditions using a declarative rule system:

```yaml
validate:
  triggers_transition: provisional → validated
  preconditions:
    - field: confidence
      comparator: gte
      value: 0.5
    - field: status
      comparator: eq
      value: provisional
```

Preconditions are checked against `ADLFrontMatter` fields using a `Comparator` enum (EQ, NEQ, GT, GTE, LT, LTE, IN, EXISTS) with no `eval()`—every rule is a statically typed Pydantic model.

### 5.3 Hybrid Memory Index

**Design rationale:** The three-tier design optimizes for the access pattern observed in agentic workflows: frequent skeleton-level filtering (Hot), occasional full-document retrieval with graph traversal (Warm), and rare historical audits (Cold).

The `ADLMemory` system provides three-tier storage optimized for concept retrieval at scale:

- **Hot** (in-memory HashMap, < 1 ms): `ConceptSkeleton` (< 500 bytes) with fast pre-filtering by status, domain, scope prefix
- **Warm** (SQLite + NetworkX, 5-20 ms): Full documents with indexed relation graph, BFS traversal for related concepts
- **Cold** (file-backed, 50-500 ms): Historical/archived documents

Cascade filtering reduces a 100M concept space through successive filters: status bitmap → type inverted index → namespace trie → vector ANN → graph traversal → result.

### 5.4 Action Executor

**Design rationale:** The precondition-based dispatch model separates validation (static, declarative rules in YAML) from execution (dynamic, protocol-based plugins), enabling the ontology registry to evolve independently of the execution engine.

The `ActionExecutor` validates and dispatches L4 action blocks:

1. Validate action name against ontology registry
2. Check required parameters
3. Evaluate preconditions against `ADLFrontMatter`
4. Execute side effects (Lark announce, publish, dashboard sync, consensus update)
5. If `triggers_transition` is declared, append lifecycle event to EventChain
6. Update `exec_status` and `execution_log`

Side effects are implemented as plugin classes conforming to the `SideEffect` Protocol, enabling extensibility without modifying core executor code.

### 5.5 Real-Time Event Watcher

**Design rationale:** By attaching to `EventChain.append()` rather than polling, the watcher guarantees detection at the moment of append without introducing polling latency or missed events.

The `RealtimeWatcher` attaches to EventChains and fires pattern-detection alerts on every `append()`:

- **Laundering patterns**: smurfing (5+ events < $1,000), rapid_movement (10+ laundering events), fan_out (5+ unique recipients)
- **Status transitions**: concept_validated, concept_deprecated
- **High frequency**: chain length milestones (100, 1000, 10000 events)
- **Amount thresholds**: transactions ≥ $1,000,000

Alerts are dispatched to registered callback handlers via a pub/sub model.

### 5.6 Feishu/Lark Bridge

**Design rationale:** Rather than building a custom collaboration protocol, we leverage an existing enterprise messaging platform (Feishu/Lark) as the transport layer, enabling ADL Lite to integrate into existing organizational workflows without requiring new infrastructure.

A CLI bridge integrates with the Feishu (Lark) collaboration platform:

- `lark publish`: Publish ADL Markdown documents as Feishu Docs
- `lark announce`: Broadcast discoveries to IM chat rooms
- `lark listen`: Ingest feedback from chat messages for consensus transitions
- `lark sync-memory`: Sync ADLMemory to Feishu Base (spreadsheet database)
- `lark dashboard`: Create/update consensus dashboard sheets

---

## 6. Experimental Evaluation

### 6.1 Experiment Design

We designed six controlled experiments to validate ADL Lite's core claims:

| ID | Name | Validation Goal | RQ Addressed | Result |
|----|------|----------------|:----------:|:------:|
| E1 | Chain integrity | Cryptographic hashes link correctly; `verify_integrity()` detects tampering | RQ1 | ✅ PASS |
| E2 | Status derivation | `DiscoveryStatus` computed from chain, not stored; all lifecycle transitions correct | RQ1 | ✅ PASS |
| E3 | Snapshot roundtrip | `FrontMatter` ↔ `EventChain` consistency: `from_chain()` produces correct snapshot | RQ1 | ✅ PASS |
| E4 | Precondition enforcement | All 9 `Comparator` types correctly evaluate against `ADLFrontMatter` fields | RQ2 | ✅ PASS |
| E5 | 5-agent audit | Multi-agent validation with confidence aggregation; fork resolution with isomorphism thresholding | RQ3 | ✅ PASS |
| E6 | IBM AML pipeline | 9,300-transaction CSV → event import → `discover_classes(smart=True)` → ground-truth evaluation; ontology emerges from data | RQ2 | ✅ PASS |

### 6.2 Experiment Harness

Experiments E1-E5 were conducted using `experiments/harness.py`, which orchestrates multi-agent simulation:

```python
# E5: 5-agent audit
agents = ["discoverer", "reviewer_a", "reviewer_b", "validator", "archivist"]
for agent_id in agents:
    chain.append(Event(concept_id=cid, event_type=EventType.VALIDATE,
                       actor=agent_id, payload={"confidence": random.uniform(0.6, 0.95)}))
assert chain.status == DiscoveryStatus.VALIDATED
assert len(chain.validators) == 5
```

E6 (AML pipeline) processes real financial transaction data through the `DataImporter`:

```python
importer = DataImporter()
chains = importer.import_csv("data/aml/ibm_data/HI-Small_Trans.csv",
                              event_type=EventType.REGISTER,
                              concept_id_field="Account")
classes = DataImporter.discover_classes(chains, smart=True)
# Default _id heuristic: [] → smart mode: ['Account', 'Bank']
links = DataImporter.discover_links(chains)      # → co-occurring _id pairs
summary = DataImporter.summary(chains)            # → total_chains=201, total_events=9300
```

### 6.3 Results

All six experiments pass (6/6, 238 seconds total). Key findings:

**E1-E2: Chain Integrity and Status Derivation.** The cryptographic hash chain correctly links events. `verify_integrity()` returns `True` for valid chains and detects hash mismatches when payloads are tampered with. Status derivation through reverse chain traversal correctly identifies the latest lifecycle event, with zero false positives/negatives across all possible transition paths.

**E3: Snapshot Consistency.** `ADLFrontMatter.from_chain()` produces snapshots that are bit-identical to the parsed YAML front matter after roundtrip, confirming that the event chain is a lossless representation of the document's semantic state.

**E4: Precondition Enforcement.** All 9 `Comparator` types are validated through the comprehensive test suite (see §6.4). E4 specifically validates the integration of precondition checks within the ActionExecutor's execution pipeline: rules declared in the YAML ontology registry are correctly parsed, evaluated against `ADLFrontMatter` fields, and produce the correct pass/fail verdict with informative error messages. No `eval()` or unsafe code execution is used; all comparisons are implemented as pure Python lambda functions locked to the `Comparator` enum.

**E5: Multi-Agent Consensus.** In the 5-agent audit, all agents successfully appended `VALIDATE` events with distinct confidence scores. The derived `confidence` property correctly returns the most recent validator's confidence. Fork resolution correctly classified concept pairs above/below the 0.90 isomorphism threshold.

**E6: Ontology Emergence.** The `DataImporter` processed 9,300 transactions from the IBM AML synthetic dataset (HI-Small\_Trans, 201 sender accounts, 200 receiver accounts, 5 banks, 5 payment formats, 3.2% laundering rate) [22][23]. We evaluated ontology discovery against a ground-truth schema of {Account, Bank, PaymentFormat, Transaction}. The default `_id`-suffix heuristic achieves 0 precision and 0 recall because IBM uses dot notation (`Account`, `Account.1`) rather than `_id` suffixes. We implemented a multi-strategy smart heuristic combining cardinality filtering (15–500 unique values, 2–50% uniqueness ratio), paired-column detection (`X`/`X.1` → entity `X`), and entity-indicator naming with directional-prefix stripping (`From Bank` → `Bank`). The smart heuristic achieves **precision 1.000, recall 0.500, F1 0.667** on this dataset: it correctly identifies `Account` and `Bank` with zero false positives, while `PaymentFormat` and `Transaction` are not recovered because they lack dedicated high-cardinality columns in the CSV schema. The remaining 8,177 Account↔Account.1 co-occurrence pairs are identified for relation extraction.

### 6.4 Code Quality and Reproducibility

The reference implementation (Python 3.10+, Pydantic v2, NetworkX) is validated by 325 automated tests at 81% line coverage. All experiments are reproducible via `python -m experiments.runner all` and `pytest tests/ -v`. The implementation is available under the MIT License (see Data Availability).

### 6.5 Fork Threshold Sensitivity

To address the question of how sensitive fork resolution is to the choice of isomorphism threshold (§4.2), we conducted a threshold sweep across the range 0.70–0.95 on 21 concept pairs with controlled Jaccard similarity (0.05–1.00).

**Key finding: zero false positives across all thresholds.** The clean separation between "same concept" (Jaccard ≥ 0.70) and "different concept" (Jaccard ≤ 0.67) pairs means that any threshold in [0.70, 0.73] achieves perfect classification (F1=1.000, FPR=0.0). The default threshold of 0.90 is intentionally conservative: it achieves F1=0.667 with zero false positives (FPR=0.0), prioritizing the avoidance of false merges over recall. For deployment scenarios where missing a merge is more costly than a false merge, lowering the threshold to 0.75–0.80 increases F1 to 0.857 while maintaining zero false positives on this dataset.

### 6.6 RDF/OWL/PROV-O Mapping Evaluation

We implemented an ADL-to-RDF mapping compiler that generates Turtle representation from ADL documents. The mapping uses the following conventions:

- Each concept → a named graph `<adl://{scope}/{adl_id}>`
- Relation blocks → `owl:ObjectProperty` assertions with typed blank nodes
- Evidence blocks → `prov:Entity` with `prov:atLocation` pointers
- Formal seal blocks → `adl:FormalSeal` with language and proof references
- Front matter → `rdfs:label`, `adl:confidence`, `adl:novelty` annotations

We evaluated the mapping on all five example documents in the ADL corpus. Results show **100% information preservation**: all 9 relation triples and all 10 evidence entities from the source documents are faithfully represented in the generated Turtle, with valid prefix declarations and graph structure. This demonstrates that ADL Lite's structured layers (L1/L3) provide sufficient typing information for lossless compilation to standard Semantic Web formats.

### 6.7 Baseline Comparison: ADL vs JSON vs Nanopublication

We compared ADL Lite against two established representation paradigms: raw JSON (representing ad-hoc structured authoring) and nanopublication-style RDF (representing provenance-centered publication models). The comparison on the Capital Reflux Trap concept yields:

| Capability | ADL Markdown | JSON | Nanopub |
|-----------|:---:|:---:|:---:|
| Syntax validation (built-in) | ✅ Pydantic | ❌ manual | ✅ RDF parser |
| Pronoun/ambiguity check | ✅ SSA | ❌ | ❌ |
| Built-in audit trail | ✅ EventChain (crypto) | ❌ | ✅ prov |
| Cryptographic integrity | ✅ SHA-256 chain | ❌ | ✅ (if signed) |
| Consensus primitives | ✅ ForkManager | ❌ | ❌ |
| Ontology registry | ✅ YAML (10 predicates, 9 actions) | ❌ | ❌ |
| Human-readable prose | ✅ L2 Markdown | ❌ | ✅ RDF comments |
| LLM-friendly authoring | ✅ Markdown-native | ❌ (JSON error-prone) | ❌ (RDF syntax) |

ADL Lite provides the unique combination of human-readable prose (L2), structured machine validation (L1/L3/L4), built-in cryptographic audit trails, and consensus primitives—all in a single format that requires no external tooling. JSON offers compactness but no validation; nanopublications offer provenance but require RDF expertise.

---

## 7. Discussion

### 7.1 Comparison with Object-First Ontologies

The fundamental shift from object-first to event-first design has profound implications:

| Aspect | Object-First Authoring (typical) | Event-First (ADL Lite) |
|--------|----------------------|----------------------|
| **Concept representation** | Mutable object with stored properties | Append-only event chain |
| **State derivation** | Explicit writes to status/confidence fields | Computed from chain traversal |
| **Audit trail** | Requires explicit logging | Inherent in chain structure (cryptographic) |
| **Multi-agent concurrency** | Race conditions, requires coordination | Write-time: conflict-free (append-only); Merge-time: deterministic ordering by (timestamp, hash) |
| **Authoring format** | Formal ontology languages (OWL, SHACL) or custom APIs | Markdown with typed blocks |
| **Trust model** | Implicit in storage layer (no built-in per-concept audit) | Per-concept cryptographic hash chain |

### 7.2 Applicability to Semantic Web

ADL Lite complements rather than replaces existing semantic web standards:

- **Bridging format**: ADL documents can be compiled to RDF, with each concept mapped to a named graph containing all its event annotations, relation assertions (as OWL object property assertions), evidence records (as PROV-O entities), and formal seal references
- **Agent-native authoring**: LLM agents produce ADL Markdown; existing toolchains consume RDF/OWL
- **Provenance**: The EventChain provides PROV-O-compatible provenance that is structurally integral to the concept, not an afterthought

### 7.3 Failure Modes and Adversarial Analysis

While the append-only EventChain model eliminates race conditions, it is not immune to all failure modes:

**Timestamp collisions.** In the SyncManager merge, two events from different edge nodes may have identical timestamps. Our implementation uses SHA-256 hash as a secondary sort key for deterministic ordering, but this does not resolve the semantic ambiguity of which event occurred first. In practice, this manifests as non-deterministic but consistent ordering—all nodes observing the same set of events will produce the same merged chain, but the ordering within a timestamp bucket is arbitrary. For production deployments, hybrid logical clocks (HLC) or vector clocks could replace wall-clock timestamps to guarantee causal ordering without requiring synchronized physical clocks across edge nodes.

**Malicious tampering.** The SHA-256 hash chain provides tamper *evidence* (detection via `verify_integrity()`) but not tamper *prevention*. A malicious agent with direct access to the chain storage can modify event payloads; the subsequent `verify_integrity()` call will detect the mismatch. However, ADL Lite does not provide Byzantine fault tolerance—it assumes agents follow the append-only protocol. For adversarial multi-agent settings, integration with a distributed ledger or threshold signature scheme would be needed.

**Chain poisoning.** An agent could append a large number of low-quality events to inflate chain length or confidence scores. The current implementation provides no spam prevention—the RealtimeWatcher's `chain_large` (100 events) and `chain_huge` (10,000 events) alerts serve as monitoring signals rather than prevention mechanisms. Rate limiting and quality-weighted confidence aggregation are areas for future work.

**SSA circumvention.** Agents can bypass pronoun prohibition by using creative circumlocutions (e.g., "the aforementioned mechanism" instead of "this"). The SSA validator catches known pronoun patterns but cannot guarantee that all ambiguous references are eliminated. We confirmed this limitation experimentally: phrases like "the aforementioned mechanism" and "said relationship" pass validation despite being referentially ambiguous. This is an inherent limitation of pattern-based validation rather than semantic understanding.

**Adversarial validation.** We conducted stress tests to verify the system's behavior under attack. (1) Payload tampering: modifying an event's payload after chain construction is detected by `verify_integrity()` because the chained hash breaks at the successor event. Even if the attacker recomputes the tampered event's own hash, the next event's `_prev_hash` still references the original value. (2) Chain poisoning: appending 100 low-quality events triggers the `RealtimeWatcher`'s `chain_large` alert while maintaining hash chain integrity. (3) Fork bombing: creating 100 malicious forks is handled correctly by the `ForkManager` with all chains remaining independently verifiable. Long-idle forks (180+ days) are correctly flagged for pruning.

### 7.4 CRDT Formalization of Derived States

To address the last-writer-wins limitation, we formalize ADL Lite's derived state as a join-semilattice $\mathcal{S} = (\text{Status} \times \mathbb{R}_{[0,1]} \times \mathbb{N} \times \mathbb{N}, \sqcup)$ where the merge operator $\sqcup$ is the component-wise least upper bound:

$$\text{merge}(s_1, s_2) = \big(\max(\text{status}_1, \text{status}_2),\ \max(\text{conf}_1, \text{conf}_2),\ \max(\text{val}_1, \text{val}_2),\ \max(\text{ev}_1, \text{ev}_2)\big)$$

where status is lattice-ordered ($\text{PROVISIONAL} \sqsubset \text{FORKED} \sqsubset \text{VALIDATED} \sqsubset \text{DEPRECATED} \sqsubset \text{ARCHIVED}$). This merge operator is:

- **Commutative**: $\text{merge}(A,B) = \text{merge}(B,A)$ — verified by exhaustive enumeration over all status×confidence×validator×evidence combinations
- **Associative**: $\text{merge}(\text{merge}(A,B),C) = \text{merge}(A,\text{merge}(B,C))$ — verified over $4^3$ state triples
- **Idempotent**: $\text{merge}(A,A) = A$ — direct from $\max(x,x) = x$

Furthermore, each event application is **monotonic**: $\text{apply}(s, e) \sqsupseteq s$ for all states $s$ and events $e$, meaning the state never regresses. Under partition, two edge nodes receiving different event sequences converge to a merged state that dominates both: $\text{merge}(s_A, s_B) \sqsupseteq s_A$ and $\text{merge}(s_A, s_B) \sqsupseteq s_B$.

These properties are verified by 15 executable proofs in `tests/test_crdt_proofs.py`, including a 5-edge multi-way merge that produces identical results regardless of merge order. The CRDT state can be derived from any existing EventChain via `CRDTState.from_chain(chain)`, providing a drop-in replacement for the current LWW semantics.

### 7.5 Limitations

1. **Last-writer-wins semantics (addressed)**: The original `confidence` property returns the most recent validator's score. We have since formalized a **CRDT-correct alternative** (§7.4): a join-semilattice over derived states with G-Counter (max) for confidence and LUB for status. This guarantees commutative, associative, idempotent merge with monotonic state progression.

2. **Single-concept granularity**: The current design treats each concept independently. Cross-concept patterns (e.g., "all concepts in domain X that were validated by agent Y") require the `ADLMemory` query layer, which adds latency.

3. **No formal semantics**: While SSA provides typed constraints, ADL Lite does not provide model-theoretic semantics in the sense of description logics. This limits automated reasoning capabilities.

4. **Scalability ceiling**: The in-memory Hot layer scales to ~10M skeletons per node. Beyond that, distributed indexing is needed, which is not yet implemented. Additionally, property derivation via *O(n)* chain traversal (e.g., `status`, `confidence`) becomes expensive for very long chains ($n > 10^5$); an event-indexed cache with incremental updates would mitigate this in production.

5. **Lark bridge coupling**: The Feishu/Lark integration is specific to that platform. While the SideEffect protocol enables alternative integrations, only Lark is currently implemented.

### 7.6 Future Work

1. **RDF/OWL compiler**: Automatically generate OWL ontologies from ADL document corpora, with event chains mapped to named graphs.

2. **Distributed EventChain**: Implement a distributed append-only log (e.g., Kafka-backed) for EventChains spanning multiple nodes, enabling horizontal scaling.

3. **LLM agent integration**: Develop a benchmark suite for evaluating LLM agents' ability to author valid ADL documents, measuring pronoun compliance, relation accuracy, and consensus contribution.

4. **Robust confidence aggregation**: Replace the current last-writer-wins confidence with multi-validator aggregation (weighted means, robust statistics, or per-agent trust models with verifiable credentials).

5. **SHACL integration**: Derive SHACL shapes from the ontology registry for automated validation of ADL document corpora.

6. **Cross-platform bridges**: Implement SideEffect plugins for Slack, Microsoft Teams, and Discord to extend the real-time collaboration model.

7. **Formal CRDT proofs**: Establish lattice-based derived states (multi-valued statuses with partial orders, quorum thresholds) and prove confluence properties for the merge operation beyond simple timestamp ordering.

8. **Per-agent cryptographic signatures**: Sign each event with the agent's Ed25519 key and periodically anchor Merkle root checkpoints to external transparency logs, strengthening tamper-evidence into tamper-prevention for adversarial multi-agent settings.

---

## 8. Conclusion

We have presented ADL Lite, an event-first operational ontology for multi-agent knowledge graph authoring. The key insight—that concepts should be represented as append-only chains of typed events rather than mutable objects—resolves fundamental tensions in agentic KG construction: race conditions become impossible, audit trails become inherent, and trust becomes cryptographic rather than centralized.

The four-layer Markdown-native syntax (L1-L4) makes ADL Lite accessible to LLM agents without formal ontology training, while Structured Semantic Anchoring (SSA) constrains natural language ambiguity. The consensus protocol, fork management, and offline-first synchronization provide the infrastructure for autonomous agent fleets to collaboratively build and evolve knowledge graphs.

The reference implementation validates these claims through six controlled experiments (6/6 passing), 325 tests with 81% code coverage, and a functioning Feishu/Lark bridge for real-time collaboration. We believe ADL Lite represents a meaningful step toward making knowledge graph construction a first-class capability of LLM agent systems.

---

## Data Availability

The full source code, ontology registry, experiment harness, and test suite are available at https://github.com/sunnyang1/adl-lite under the MIT License. All experimental results reported in this paper are reproducible by running `python -m experiments.runner all` and `pytest tests/ -v` from the repository root.

---

## References

[1] S. Pan, L. Luo, Y. Wang, C. Chen, J. Wang, and X. Wu, "Unifying Large Language Models and Knowledge Graphs: A Roadmap," *IEEE Transactions on Knowledge and Data Engineering*, 2024.

[2] B. Chen, Z. Zhang, N. Beauchamp, J. Truong, Y. Wang, H. Yang, and L. Liu, "AgentPoison: Red-teaming LLM Agents via Memory Poisoning," *arXiv preprint arXiv:2407.12784*, 2024.

[3] D. L. McGuinness and F. Van Harmelen, "OWL Web Ontology Language Overview," *W3C Recommendation*, 2004.

[4] R. Angles and C. Gutierrez, "Survey of Graph Database Models," *ACM Computing Surveys*, vol. 40, no. 1, pp. 1-39, 2008.

[5] S. Colvin et al., "Pydantic: Data Validation Using Python Type Hints," *GitHub Repository*, 2021.

[6] L. Wittgenstein, *Tractatus Logico-Philosophicus*. Routledge & Kegan Paul, 1922. Original: "Die Welt ist alles, was der Fall ist."

[7] A. N. Whitehead, *Process and Reality*. Free Press, 1929.

[8] M. Fowler, "Event Sourcing," *martinfowler.com*, 2005.

[9] T. Lebo et al., "PROV-O: The PROV Ontology," *W3C Recommendation*, 2013.

[10] Y. Raimond and S. Abdallah, "The Event Ontology," *Technical Report*, 2007.

[11] W. R. Van Hage, V. Malaisé, R. Segers, L. Hollink, and G. Schreiber, "Design and Use of the Simple Event Model (SEM)," *Journal of Web Semantics*, vol. 9, no. 2, pp. 128-136, 2011.

[12] M. Trajanoska, R. Stojanov, and D. Trajanov, "Enhancing Knowledge Graph Construction Using Large Language Models," *arXiv preprint arXiv:2305.04692*, 2023.

[13] Z. Chen, H. Mao, H. Li, W. Jin, H. Wen, X. Wei, S. Wang, D. Yin, W. Fan, H. Liu, and J. Tang, "Exploring the Potential of Large Language Models (LLMs) in Learning on Graphs," *ACM SIGKDD Explorations*, 2024.

[14] L. Lamport, R. Shostak, and M. Pease, "The Byzantine Generals Problem," *ACM Transactions on Programming Languages and Systems*, vol. 4, no. 3, pp. 382-401, 1982.

[15] D. Ongaro and J. Ousterhout, "In Search of an Understandable Consensus Algorithm," *USENIX ATC*, 2014.

[16] M. Wooldridge, *An Introduction to MultiAgent Systems*, 2nd ed. Wiley, 2009.

[17] R. Jurca and B. Faltings, "An Incentive Compatible Reputation Mechanism," *IEEE CEC*, 2003.

[18] F. Brandt, V. Conitzer, U. Endriss, J. Lang, and A. D. Procaccia, *Handbook of Computational Social Choice*. Cambridge University Press, 2016.

[19] M. Shapiro, N. Preguiça, C. Baquero, and M. Zawirski, "Conflict-Free Replicated Data Types," *SSS 2011*, LNCS vol. 6976, pp. 386-400, 2011.

[20] A. Third and J. Domingue, "LinkChains: Exploring the Space of Decentralised Trustworthy Linked Data," *DeSemWeb@ISWC*, 2017.

[21] J. Benet, "IPFS - Content Addressed, Versioned, P2P File System," *arXiv preprint arXiv:1407.3561*, 2014.

[22] IBM Research, "Realistic Synthetic Financial Transactions for Anti-Money Laundering Models," *arXiv preprint arXiv:2306.16424*, 2023.

[23] E. Altman, "IBM Transactions for Anti Money Laundering (AML)," *Kaggle Dataset*, 2019. https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml

[24] P. Groth, A. Gibson, and J. Velterop, "The Anatomy of a Nanopublication," *Information Services & Use*, vol. 30, no. 1-2, pp. 51-56, 2010.

[25] O. Hartig and P.-A. Champin, "RDF-star and SPARQL-star," *W3C Community Group Report*, 2024.

[26] D. Vrandečić and M. Krötzsch, "Wikidata: A Free Collaborative Knowledgebase," *Communications of the ACM*, vol. 57, no. 10, pp. 78-85, 2014.

[27] T. Berners-Lee and D. Connolly, "Delta: An Ontology for the Distribution of Differences between RDF Graphs," *W3C Note*, 2004.

---

## Acknowledgments

[TO BE COMPLETED — funding sources, collaborators]
