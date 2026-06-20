# CRDT Migration Guide (v0.3.0 → v0.3.5)

**Scope:** `EventChain.status` and `EventChain.confidence` semantics changed from
last-write-wins (LWW) to CRDT join-semilattice / G-Counter.  This is a **breaking
change** for any code that relied on the previous LWW behavior.

---

## 1. What changed?

### 1.1 Status derivation — LWW → LUB

| Old (LWW) | New (LUB) |
|-------------|-----------|
| `status = type_of(last_event)` | `status = max_{≺}{type(e)}` over **all** events |
| `DEPRECATE` after `VALIDATE` → `deprecated` ✓ | `DEPRECATE` after `VALIDATE` → `deprecated` ✓ |
| `VALIDATE` after `DEPRECATE` → `validated` ✗ | `VALIDATE` after `DEPRECATE` → `deprecated` ✓ (never regresses) |
| `REGISTER` after `VALIDATE` → `provisional` ✗ | `REGISTER` after `VALIDATE` → `validated` ✓ (never regresses) |
| `ARCHIVE` after `VALIDATE` → `archived` ✓ | `ARCHIVE` after any → `archived` ✓ (permanent) |

The status lattice (partial order) is:

```
provisional (1) < forked (2) < validated (3) < deprecated (4) < archived (5)
```

`status` is the **Least Upper Bound (LUB)** of all lifecycle events in the chain.

### 1.2 Confidence derivation — LWW → G-Counter (max)

| Old (LWW) | New (G-Counter) |
|-----------|-----------------|
| `confidence = payload["confidence"] of last VALIDATE` | `confidence = max(payload["confidence"])` over **all** VALIDATE / SNAPSHOT events |

Example:
```python
chain.append(Event(..., VALIDATE, payload={"confidence": 0.9}))
chain.append(Event(..., VALIDATE, payload={"confidence": 0.5}))
# Old: confidence == 0.5
# New: confidence == 0.9  (max, never decreases)
```

This prevents a malicious or erroneous validator from **downgrading** a concept
after it has been validated with high confidence.

---

## 2. Why did we change?

### Reviewer feedback (peer review, round 4)

> "Derived-state computation (e.g., confidence = last writer) undermines
> consensus; no principled aggregation or trust model is provided. No formal
> CRDT lattice or convergence proof."

The LWW rule was simple but **unsafe** in a multi-agent setting:
- A single rogue validator could overwrite a high-confidence consensus with a
  low-confidence assertion.
- Status could regress (e.g., a validated concept could be "un-validated" by a
  later `REGISTER` event).

CRDT semantics guarantee **monotonicity** and **convergence**:
- `merge(A, B)` always yields the LUB of both states.
- No matter the order of events, all agents converge to the same derived state.

---

## 3. Do I need to change my code?

### 3.1 You do NOT need to change if…

- You only use `EventChain` through the normal API (`append()`, `status`,
  `confidence`). The new semantics are automatically applied.
- Your workflow never has out-of-order or conflicting lifecycle events
  (e.g., you never `VALIDATE` after `DEPRECATE`).

### 3.2 You SHOULD review if…

- You have tests that assert `confidence == last_value` instead of `max`.
- You have logic that assumes `status` can regress (e.g., `REGISTER` resets to
  `provisional`).
- You call `chain._events.append(...)` directly (bypassing `append()`). The
  incremental cache in `_update_crdt_caches()` will not fire, but the defensive
  fallback `_compute_status_from_events()` / `_compute_confidence_from_events()`
  still ensures correct CRDT semantics (at O(|V|) cost instead of O(1)).

### 3.3 Quick compatibility checklist

```python
from adl_lite import Event, EventChain, EventType

# ✅ 1. Confidence is max, not last
chain = EventChain("demo")
chain.append(Event("demo", EventType.VALIDATE, actor="a", payload={"confidence": 0.9}))
chain.append(Event("demo", EventType.VALIDATE, actor="b", payload={"confidence": 0.5}))
assert chain.confidence == 0.9   # was 0.5 in v0.3.0

# ✅ 2. Status is LUB, never regresses
chain2 = EventChain("demo2")
chain2.append(Event("demo2", EventType.VALIDATE, actor="a"))
chain2.append(Event("demo2", EventType.DEPRECATE, actor="b"))
chain2.append(Event("demo2", EventType.VALIDATE, actor="c"))
assert chain2.status.value == "deprecated"   # was "validated" in v0.3.0

# ✅ 3. ARCHIVE dominates everything
chain3 = EventChain("demo3")
chain3.append(Event("demo3", EventType.VALIDATE, actor="a"))
chain3.append(Event("demo3", EventType.ARCHIVE, actor="a"))
chain3.append(Event("demo3", EventType.VALIDATE, actor="b"))
assert chain3.status.value == "archived"
```

---

## 4. Performance impact

| Operation | v0.3.0 (LWW) | v0.3.5 (CRDT cached) | v0.3.5 (CRDT fallback) |
|-----------|-------------|----------------------|------------------------|
| `status` query | O(1) | O(1) | O(\|V\|) |
| `confidence` query | O(1) | O(1) | O(\|V\|) |
| `append()` | O(1) | O(1) | O(1) |

The incremental cache makes CRDT semantics **as fast as** the old LWW rule
for normal usage. The O(|V|) fallback only triggers when `_events` is mutated
directly (adversarial tests or direct list manipulation).

---

## 5. CRDT merge behavior

When merging two `EventChain`s (e.g., edge-to-core sync), the derived state is
the LUB of both chains:

```python
from adl_lite import merge_event_chains

merged = merge_event_chains(chain_a, chain_b)
# merged.status  = LUB(status_a, status_b)
# merged.confidence = max(confidence_a, confidence_b)
```

Properties guaranteed:
- **Commutativity**: `merge(A, B) == merge(B, A)`
- **Associativity**: `merge(merge(A, B), C) == merge(A, merge(B, C))`
- **Idempotence**: `merge(A, A) == A`
- **Monotonicity**: state never shrinks

---

## 6. References

- Paper §4.5: `δ(C)` and `γ_default` formulas
- Paper §4.7: CRDT convergence (Theorem 9)
- `adl_lite/crdt.py`: `CRDTState`, `StatusOrder`, `merge_event_chains`
- `tests/test_crdt_proofs.py`: executable proofs of all properties

---

*Last updated: 2025-06-20*
