# Adversarial Review — ADL Lite

**Date**: 2026-05-31 | **Reviewer**: Red-team adversarial audit
**Scope**: `adl_lite/` (6,151 LOC, 23 .py files), 11 experiments, paper claims

---

## 1. P0 — Critical Architecture Bugs

### 1.1 Dual Chain System: ConceptChain ≠ EventChain

**Location**: `consensus.py:103` vs `models.py:148`

The codebase contains two independent, incompatible chain implementations:

| | `EventChain` (models.py) | `ConceptChain` (consensus.py) |
|---|---|---|
| Unit | `Event` (Pydantic, uuid4, SHA-256) | `ConsensusEntry` (plain class, no ID, SHA-256) |
| Used by | DataImporter, SyncManager, RealtimeWatcher | ConsensusEngine |
| Status derived? | Yes (`chain.status` property) | Yes (`chain.latest_status` property) |
| Event types | 13 `EventType` enum values | 5 `DiscoveryStatus` enum values |

**They are never connected.** An `Event` appended to `EventChain` never appears in `ConceptChain`, and a `ConsensusEntry` appended to `ConceptChain` never produces an `Event`. The paper claims a unified event-first architecture but the code presents two parallel systems that don't communicate.

### 1.2 ActionExecutor Mutates FrontMatter Directly — Contradicts Central Paper Claim

**Location**: `action_executor.py:345`

```python
doc.front_matter.status = new_status  # ← Direct mutation
```

This contradicts the paper's most emphatic claim:

> "Status is never stored; it is always computed from the chain." — paper §3.1
> "A concept's `status` is not a stored property but a value derived from the history of events." — paper §4.2

When `ActionExecutor._apply_transition()` runs:
1. Sets `doc.front_matter.status` directly (stores status in mutable field)
2. Does NOT append a `VALIDATE`/`DEPRECATE` Event to any `EventChain`
3. Does NOT append a `ConsensusEntry` to any `ConceptChain`

### 1.3 ActionExecutor Bypasses ConsensusEngine Entirely

`ActionExecutor._apply_transition()` (line 345) writes directly to `doc.front_matter.status`. It never calls `ConsensusEngine.transition()` which is the only code path that appends `ConsensusEntry` objects. The `ConsensusEngine` and `ActionExecutor` are unaware of each other's existence.

### 1.4 E10 Overrides Chain-Derived Confidence to Pass Preconditions

**Location**: `experiments/e10_fde_pipeline.py:88`

```python
doc.front_matter.confidence = 0.7  # Override chain-derived confidence
```

The comment admits the override. Without it, `validate` action preconditions fail because chain-derived confidence from data import events is 0.0. The "full FDE pipeline" experiment stores confidence in the front matter to bypass the very architecture it claims to test.

---

## 2. P1 — Design-Level Issues

### 2.1 Smurfing Detection: False Negatives on Mixed-Pattern Accounts

**Location**: `realtime.py:152-155`

```python
amounts = [float(e.payload.get("Amount Received", 0)) for e in ld_events]
if len(amounts) == 5 and all(a < 1000 for a in amounts):
```

If an account has 3 smurfing events (all <$1,000) and 2 large laundering events ($5,000, $10,000), the smurfing alert **never fires** because `all()` requires every laundering event to be under $1,000.

**Why E7 passes**: The test injects ONLY smurfing events for the smurf test account. No real-world mixed-pattern account is tested.

### 2.2 No Concurrency Protection

All shared state is unprotected:
- `EventChain._events` — bare list
- `ConsensusEngine.chains` — bare dict
- `RealtimeWatcher._alerts` — bare list
- `EdgeNode.chain` — shared mutable reference

Two threads appending to the same chain simultaneously can corrupt `previous_event_id` linking. The paper claims edges "operate independently" but no concurrent test exists.

### 2.3 RealtimeWatcher.attach() Non-Composable

**Location**: `realtime.py:96`

```python
chain.append = _wrapped_append  # ← Overwrites any prior wrapper
```

A second watcher that calls `attach()` on the same chain destroys the first watcher's wrapper. Multiple watchers cannot coexist on one chain.

### 2.4 DataImporter Mangles Quoted Values

**Location**: `data_importer.py:71`

```python
v.strip('"') if isinstance(v, str) else v
```

Removes ALL leading/trailing double-quote characters from every CSV string value. A cell containing `""nested quotes""` becomes `nested quotes` — information loss.

### 2.5 SyncManager Merge: Timestamp Collision Ordering

**Location**: `sync_manager.py:171`

```python
all_events.sort(key=lambda e: (e.timestamp, e.event_id))
```

For events with identical timestamps, ordering depends on `event_id` (uuid4). The merge result is deterministic within one process but may differ between machines if uuids differ. The paper describes this as "CRDT" but CRDTs guarantee eventual convergence of state, not identical ordering.

### 2.6 EventChain.from_parsed() Fabricates Synthetic Lifecycle Events

**Location**: `models.py:323-370`

When parsing a Markdown file with `status: validated`, `from_parsed()` creates:
1. A `SNAPSHOT` event (copying L1 fields into payload)
2. A `VALIDATE` event (synthesized from YAML, not authored by any agent)

The `VALIDATE` event was never actually created by an agent action. `chain.history()` returns a fabricated event trail for all pre-L4 concept files. An auditor reviewing `chain.history()` would see a VALIDATE event that never happened.

---

## 3. P2 — Paper Claims vs Code Reality

### 3.1 "Status is never stored" — FALSE

Three counters in core code paths:
1. `action_executor.py:345` — stores status in `doc.front_matter.status`
2. `consensus.py:123` — stores status in `ConceptEntry.to_status`
3. `e10_fde_pipeline.py:88` — stores confidence in `doc.front_matter.confidence`

### 3.2 "Six proved properties including determinism (Theorem 1)" — NO FORMAL PROOF

No theorem prover artifacts exist: no Coq, Lean, TLA+, Isabelle, or any formal verification file. The "theorems" are prose statements.

### 3.3 "Zero merge conflicts" (E8) — TAUTOLOGICAL

E8 merges: Edge-A appends `VALIDATE` + Edge-B appends `ANNOUNCE`. These are non-conflicting by construction. Untested scenarios:
- Both edges append `VALIDATE` with different confidence values (semantic conflict)
- Edge-A appends `DEPRECATE` + Edge-B appends `VALIDATE` (contradictory lifecycle)
- Edge-A appends `ARCHIVE` + Edge-B appends `FORK` (divergent terminal states)

### 3.4 "495,671 chains, zero failures" (E6) — MEASURES IMPORT, NOT TAMPER DETECTION

E6 imports CSV data and builds fresh EventChains. All pass `verify_integrity()` because they were just created. No adversarial tampering was introduced to any chain.

### 3.5 Implicit Timestamp Monotonicity Assumption

Merge sorts events by timestamp. If edge nodes have clock skew, merged chain ordering may not reflect causal order. The paper acknowledges this for hashing but not for merge sorting.

---

## 4. Experiment Methodology Gaps

| Issue | Detail |
|-------|--------|
| E1: 10 corrupted chains | Only 2-3 per corruption type; not statistically significant |
| E4: 13 test cases | Covers only 3 of 9 actions. 6 actions untested: fork, archive, announce, publish, sync_dashboard, listen |
| E10: 5 accounts tested | 0.001% of the 495,671 imported accounts |
| E11: Stub executor | "1000 effects, 100% success" uses a random-fail stub, not real Lark bridge |
| E6: No adversarial tampering | 495,671 chains tested for import integrity, not tamper detection |
| No concurrent test | All experiments single-threaded |

## 5. Security

| Issue | Severity |
|-------|----------|
| No actor authentication — any agent can claim any identity | HIGH |
| No payload size limit on Event | MEDIUM |
| No path traversal protection on `parse_file()` | LOW |
| YAML parser uses `safe_load()` — acceptable for current threat model | INFO |

## 6. Coverage Gaps: Untested Scenarios

- Concurrent chain append (2 threads, same concept_id)
- Contradictory lifecycle merge (VALIDATE ⇄ DEPRECATE)
- Mixed laundering pattern detection (smurf + large txns on same account)
- Rogue actor forging `previous_event_id`
- Parser: YAML bomb / billion-laughs attack
- CSV formula injection via DataImporter
- Large Event payload (>1MB)
- ForkManager with deeply nested forks (>10 levels)

---

## 7. Claim-vs-Reality Summary

| Paper Claim | Verdict | Why |
|-------------|---------|-----|
| "Status is never stored; always computed from chain" | ❌ FALSE | 3 code paths directly store status |
| "Six proved properties (Theorem 1-6)" | ⚠️ UNVERIFIED | No formal proof artifacts exist |
| "Zero merge conflicts" | ⚠️ TAUTOLOGICAL | Only non-conflicting scenarios tested |
| "495,671 chains, zero integrity failures" | ⚠️ MISLEADING | Measures import correctness, not tamper detection |
| "EventChain IS the concept" | ⚠️ PARTIAL | ConceptChain still exists and handles transitions |
| "CRDT-based merging" | ⚠️ OVERSTATED | No state-based merge; only timestamp sort + dedup |
| "Cryptographic integrity" | ✅ TRUE | SHA-256 hashing + previous_event_id linking works |
| "Status derivation 100% correct (2,204 cases)" | ✅ TRUE | Exhaustive test, correctly implemented |
| "Precondition enforcement F1=1.0" | ✅ TRUE | 13 tested cases pass correctly |
| "pip-installable, no enterprise infra" | ✅ TRUE | Verified |

## 8. Recommended Fix Priority

1. **Unify EventChain + ConceptChain** — pick one chain system, eliminate the other
2. **Make ActionExecutor append Events** — `_apply_transition()` must call `chain.append(Event(VALIDATE, ...))` instead of `doc.front_matter.status = ...`
3. **Fix smurfing `all()` bug** — use windowed check, not global
4. **Add formal proofs or remove theorem claims** — either deliver Coq/Lean files or downgrade "Theorem" → "Property"
5. **Expand E8 to test semantic conflicts** — VALIDATE+DEPRECATE, VALIDATE+FORK
6. **Add concurrency test** — two threads, same chain, verify integrity
7. **Remove E6's "zero failures" framing** — reframe as "import correctness" not "tamper detection"
8. **Remove `from_parsed()` synthetic events** or clearly mark them as `synthetic=True`
9. **Test remaining 6 actions in E4** — fork, archive, announce, publish, sync_dashboard, listen
10. **Test full pipeline on >0.1% of E6 data** — at minimum 5% (24,783 accounts)
