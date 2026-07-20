"""E34: Precondition Language Formalization — Syntax, Semantics, and O(1) Benchmark.

This experiment formally defines the ADL Lite precondition language, proves
(informally) its safety properties, and empirically validates the O(1) per-rule
evaluation claim under realistic rule sets and varying chain lengths.

Formal Precondition Language
============================

Syntax
------
A precondition rule is a 3-tuple::

    R = ⟨field, comparator, value⟩

where:

* **field** ∈ F — a field name from the ADLFrontMatter schema
  (e.g. ``status``, ``confidence``, ``validators``, ``scope``).
* **comparator** ∈ {EQ, NEQ, GT, GTE, LT, LTE, IN, EXISTS} — the Comparator enum.
* **value** ∈ V ∪ {⊥} — a literal value (scalar, string, or list).  For the
  EXISTS comparator, ``value`` is ignored (⊥).

Semantics
---------
For a front-matter instance ``fm : ADLFrontMatter``, define the evaluation
function ``eval(R, fm) → {True, False}`` as follows:

1. Let ``actual = getattr(fm, R.field, None)``.
2. If ``R.comparator == EXISTS``:
   return ``actual is not None``.
3. If ``R.comparator == IN``:
   let ``target_list = R.value`` if ``R.value`` is a list, else ``[R.value]``;
   return ``actual ∈ target_list``.
4. If ``actual is None`` and ``R.comparator ≠ {EQ, NEQ}``: return ``False``.
5. For scalar comparators (EQ, NEQ, GT, GTE, LT, LTE):
   dispatch to the corresponding Python operator.
6. If the operator raises ``TypeError`` (incompatible types): return ``False``.
7. For EQ/NEQ with ``actual`` being a dict/list/tuple/set/frozenset: return ``False``.

Safety Properties
-----------------

* **Totality**: ``eval(R, fm)`` is defined for every ``R`` and every ``fm``.
  Proof by case analysis on ``comparator``: every branch returns a bool, and
  the catch-all ``TypeError`` handler guarantees termination.
* **Determinism**: ``eval(R, fm)`` is deterministic.  ``getattr``, Python
  built-in operators, and ``is None`` are all deterministic.
* **No Turing-completeness / no eval()**: The implementation uses a closed
  ``Comparator`` enum with explicit operator dispatch.  No dynamic code
  execution is performed.  This is a **safety guarantee** against injection
  attacks.
* **Type-safe fallback**: Incompatible types never raise; they evaluate to
  ``False``, preventing unsafe actions from proceeding on malformed data.
* **Side-effect freedom**: ``check()`` is a pure function: it does not mutate
  ``fm`` or any external state.

Complexity
----------

* **Time**: ``eval(R, fm)`` is ``O(1)`` because:
  - ``getattr`` on a Pydantic model is ``O(1)`` (fixed attribute lookup).
  - Operator dispatch is a hash-map lookup + single primitive operation.
  - ``IN`` on a constant-size list is ``O(|list|)``, but the list is the rule's
    ``value`` (bounded by the ontology, typically ≤ 10), making it effectively
    ``O(1)`` in practice.
* **Space**: ``O(1)`` auxiliary space (no allocation proportional to input size).

For a rule set ``S = {R₁, …, R_k}``, the total evaluation time is ``O(k)``.
The claim in the paper is ``O(1) per rule``, i.e. linear in the number of rules
with a constant per-rule factor.

Empirical Validation
--------------------
This experiment measures:

1. **Per-rule time** for rule sets of size 5, 10, 20.
2. **Independence from chain length** — evaluate the same rule set against
   front matter derived from chains of length 1, 10, 100, 500, 1000.
3. **Comparison with naive recompute** — simulating a system that does not use
   the incremental EventChain caches (i.e., re-derives status and confidence
   from all events on every check).

Expected results:

* Per-rule time remains constant (~0.5–2 µs) regardless of chain length.
* Naive recompute time grows linearly with chain length.
* Rule-set time grows linearly with ``k`` (confirming ``O(k)`` total).
"""

from __future__ import annotations

import statistics
import time
from typing import Any

from adl_lite import (
    ADLType,
    Comparator,
    DiscoveryStatus,
    Event,
    EventChain,
    EventType,
    PreconditionRule,
)
from adl_lite.models import ADLFrontMatter

from .base import BaseExperiment, ExperimentResult
from .registry import register

# ---------------------------------------------------------------------------
# Formal grammar helpers (documented for the paper)
# ---------------------------------------------------------------------------


def _formal_grammar() -> str:
    """Return the formal grammar as a BNF-like string.

    This is a documentation function; it is not executed during benchmarking.
    """
    return """
    ⟨Rule⟩        ::= ⟨Field⟩ ⟨Comparator⟩ ⟨Value⟩
    ⟨Field⟩       ::= "status" | "confidence" | "validators" | "scope"
                      | "domain" | "novelty" | "adl_type" | "mechanism"
    ⟨Comparator⟩  ::= "eq" | "neq" | "gt" | "gte" | "lt" | "lte" | "in" | "exists"
    ⟨Value⟩       ::= ⟨Scalar⟩ | ⟨List⟩ | ⊥
    ⟨Scalar⟩      ::= ⟨String⟩ | ⟨Float⟩ | ⟨Int⟩ | ⟨Bool⟩
    ⟨List⟩        ::= "[" ⟨Scalar⟩ ("," ⟨Scalar⟩)* "]"
    """


# ---------------------------------------------------------------------------
# Semantic rules (one per comparator)
# ---------------------------------------------------------------------------


def _semantic_table() -> dict[str, str]:
    """Human-readable semantics for each comparator."""
    return {
        "EQ": "eval(⟨f, EQ, v⟩, fm)  ⟺  getattr(fm, f) == v",
        "NEQ": "eval(⟨f, NEQ, v⟩, fm) ⟺  getattr(fm, f) != v",
        "GT": "eval(⟨f, GT, v⟩, fm)  ⟺  getattr(fm, f) > v  (and not None)",
        "GTE": "eval(⟨f, GTE, v⟩, fm) ⟺  getattr(fm, f) >= v (and not None)",
        "LT": "eval(⟨f, LT, v⟩, fm)  ⟺  getattr(fm, f) < v  (and not None)",
        "LTE": "eval(⟨f, LTE, v⟩, fm) ⟺  getattr(fm, f) <= v (and not None)",
        "IN": "eval(⟨f, IN, v⟩, fm)  ⟺  getattr(fm, f) ∈ (v if list else [v])",
        "EXISTS": "eval(⟨f, EXISTS, ⊥⟩, fm) ⟺  getattr(fm, f) is not None",
    }


# ---------------------------------------------------------------------------
# Benchmark helpers
# ---------------------------------------------------------------------------


def _build_realistic_rule_set(k: int) -> list[PreconditionRule]:
    """Build a realistic precondition rule set of size *k*.

    The rules cycle through realistic ontology constraints:
      - status checks (EQ/NEQ)
      - confidence thresholds (GTE)
      - scope/domain checks (IN/EXISTS)
      - novelty bounds (LTE)
    """
    rules = []
    templates = [
        PreconditionRule(field="status", comparator=Comparator.EQ, value="validated"),
        PreconditionRule(field="confidence", comparator=Comparator.GTE, value=0.5),
        PreconditionRule(
            field="scope", comparator=Comparator.IN, value=["public", "private/ceiec-aml"]
        ),
        PreconditionRule(field="domain", comparator=Comparator.EXISTS, value=None),
        PreconditionRule(field="novelty", comparator=Comparator.LTE, value=1.0),
        PreconditionRule(field="status", comparator=Comparator.NEQ, value="archived"),
        PreconditionRule(field="confidence", comparator=Comparator.GT, value=0.0),
        PreconditionRule(field="novelty", comparator=Comparator.LT, value=2.0),
    ]
    for i in range(k):
        rules.append(templates[i % len(templates)])
    return rules


def _make_front_matter(chain_length: int) -> ADLFrontMatter:
    """Build a front-matter snapshot derived from a chain of *chain_length* events.

    This exercises the full derivation path (status, confidence, validators)
    so that the benchmark measures the realistic cost of precondition evaluation
    against a *derived* snapshot, not a hand-crafted one.
    """
    concept_id = f"bench-{chain_length}"
    chain = EventChain(concept_id=concept_id)
    chain.append(Event(concept_id=concept_id, event_type=EventType.REGISTER, actor="system"))
    for i in range(1, chain_length):
        if i % 5 == 0:
            chain.append(
                Event(
                    concept_id=concept_id,
                    event_type=EventType.DEPRECATE,
                    actor=f"agent_{i}",
                )
            )
        elif i % 3 == 0:
            chain.append(
                Event(
                    concept_id=concept_id,
                    event_type=EventType.VALIDATE,
                    actor=f"agent_{i}",
                    payload={"confidence": min(0.95, 0.5 + i * 0.01)},
                )
            )
        else:
            chain.append(
                Event(
                    concept_id=concept_id,
                    event_type=EventType.EVIDENCE,
                    actor=f"agent_{i}",
                    payload={},
                )
            )
    # Derive snapshot from chain (realistic code path)
    identity = {
        "domain": "financial_aml",
        "mechanism": None,
        "scope": "public",
        "novelty": 0.7,
        "provisional_names": {"zh": "测试", "en": "Test"},
        "evidence_refs": ["vecdb://test"],
    }
    return chain.snapshot(adl_type=ADLType.DISCOVERY, identity_fields=identity)


def _naive_recompute_status(chain: EventChain) -> DiscoveryStatus:
    """Naive status recompute: scan ALL events every time (no cache)."""
    max_order = 0
    type_to_status = {
        EventType.REGISTER: DiscoveryStatus.PROVISIONAL,
        EventType.VALIDATE: DiscoveryStatus.VALIDATED,
        EventType.DEPRECATE: DiscoveryStatus.DEPRECATED,
        EventType.FORK: DiscoveryStatus.FORKED,
        EventType.ARCHIVE: DiscoveryStatus.ARCHIVED,
    }
    for event in chain.events:
        if event.event_type in type_to_status:
            from adl_lite.crdt import StatusOrder

            order = StatusOrder[type_to_status[event.event_type].name.upper()].value
            if order > max_order:
                max_order = order
    if max_order == 0:
        return DiscoveryStatus.PROVISIONAL
    from adl_lite.crdt import StatusOrder

    return DiscoveryStatus[StatusOrder(max_order).name]


# ---------------------------------------------------------------------------
# Experiment
# ---------------------------------------------------------------------------


@register("E34")
class E34PreconditionFormalization(BaseExperiment):
    experiment_id = "E34"
    name = "Precondition Language Formalization & O(1) Benchmark"
    description = (
        "Formal syntax, semantics, and safety of the ADL precondition language, "
        "plus empirical validation of O(1) per-rule evaluation."
    )

    def run(self) -> ExperimentResult:
        errors: list[str] = []
        metrics: dict[str, Any] = {}
        raw_data: list[dict[str, Any]] = []

        # ------------------------------------------------------------------
        # Part 1: Formal grammar and semantics (documented, not measured)
        # ------------------------------------------------------------------
        grammar = _formal_grammar()
        semantics = _semantic_table()
        print("=" * 60)
        print("E34: Precondition Language Formalization")
        print("=" * 60)
        print("\n--- Formal Grammar (BNF) ---")
        print(grammar)
        print("\n--- Semantic Rules ---")
        for op, rule_desc in semantics.items():
            print(f"  {op}: {rule_desc}")

        # ------------------------------------------------------------------
        # Part 2: Per-rule time vs rule-set size (k = 5, 10, 20)
        # ------------------------------------------------------------------
        print("\n--- Part 2: Per-rule time vs rule-set size ---")
        chain_lengths = [1, 10, 100, 500, 1000]
        k_values = [5, 10, 20]
        # Use a fixed medium chain length for the k-sweep
        base_fm = _make_front_matter(100)

        per_rule_times: dict[str, dict[str, float]] = {}
        for k in k_values:
            rules = _build_realistic_rule_set(k)
            # Warm-up
            for _ in range(10):
                for rule in rules:
                    rule.check(base_fm)
            # Measure total time for the rule set
            times = []
            for _ in range(200):
                t0 = time.perf_counter()
                for rule in rules:
                    rule.check(base_fm)
                t1 = time.perf_counter()
                times.append((t1 - t0) * 1e6)  # μs
            mean_total = statistics.mean(times)
            mean_per_rule = mean_total / k
            per_rule_times[f"k={k}"] = {
                "total_us": round(mean_total, 2),
                "per_rule_us": round(mean_per_rule, 3),
                "std_total_us": round(statistics.stdev(times), 2) if len(times) > 1 else 0.0,
            }
            raw_data.append(
                {
                    "benchmark": "per_rule_vs_k",
                    "k": k,
                    "chain_length": 100,
                    "mean_total_us": round(mean_total, 2),
                    "mean_per_rule_us": round(mean_per_rule, 3),
                    "std_total_us": round(statistics.stdev(times), 2) if len(times) > 1 else 0.0,
                }
            )
            print(f"  k={k:2d}: total={mean_total:.2f} µs, per-rule={mean_per_rule:.3f} µs")

        metrics["per_rule_times_us"] = per_rule_times

        # ------------------------------------------------------------------
        # Part 3: Independence from chain length
        # ------------------------------------------------------------------
        print("\n--- Part 3: Independence from chain length ---")
        test_rules = _build_realistic_rule_set(10)
        chain_independence: dict[str, float] = {}
        for cl in chain_lengths:
            fm = _make_front_matter(cl)
            # Warm-up
            for _ in range(10):
                for rule in test_rules:
                    rule.check(fm)
            times = []
            for _ in range(200):
                t0 = time.perf_counter()
                for rule in test_rules:
                    rule.check(fm)
                t1 = time.perf_counter()
                times.append((t1 - t0) * 1e6)
            mean_total = statistics.mean(times)
            chain_independence[f"len={cl}"] = round(mean_total, 2)
            raw_data.append(
                {
                    "benchmark": "chain_independence",
                    "chain_length": cl,
                    "k": 10,
                    "mean_total_us": round(mean_total, 2),
                    "std_total_us": round(statistics.stdev(times), 2) if len(times) > 1 else 0.0,
                }
            )
            print(f"  chain_length={cl:4d}: total={mean_total:.2f} µs")

        metrics["chain_independence_us"] = chain_independence

        # ------------------------------------------------------------------
        # Part 4: Naive recompute vs cached O(1)
        # ------------------------------------------------------------------
        print("\n--- Part 4: Naive recompute vs cached ---")
        naive_vs_cached: dict[str, dict[str, float]] = {}
        for cl in chain_lengths:
            chain = EventChain(concept_id=f"naive-{cl}")
            chain.append(
                Event(concept_id=f"naive-{cl}", event_type=EventType.REGISTER, actor="system")
            )
            for i in range(1, cl):
                chain.append(
                    Event(
                        concept_id=f"naive-{cl}",
                        event_type=EventType.VALIDATE,
                        actor=f"agent_{i}",
                        payload={"confidence": 0.8},
                    )
                )
            # Cached: use the chain's built-in snapshot (O(1) status + confidence)
            t0 = time.perf_counter()
            for _ in range(100):
                _ = chain.status
                _ = chain.confidence
            t_cached = (time.perf_counter() - t0) * 1e6 / 100

            # Naive: recompute from scratch every iteration
            t0 = time.perf_counter()
            for _ in range(100):
                _ = _naive_recompute_status(chain)
            t_naive = (time.perf_counter() - t0) * 1e6 / 100

            naive_vs_cached[f"len={cl}"] = {
                "cached_us": round(t_cached, 2),
                "naive_us": round(t_naive, 2),
                "speedup": round(t_naive / t_cached, 1) if t_cached > 0 else float("inf"),
            }
            raw_data.append(
                {
                    "benchmark": "naive_vs_cached",
                    "chain_length": cl,
                    "cached_us": round(t_cached, 2),
                    "naive_us": round(t_naive, 2),
                    "speedup": round(t_naive / t_cached, 1) if t_cached > 0 else float("inf"),
                }
            )
            print(
                f"  chain_length={cl:4d}: cached={t_cached:.2f} µs, naive={t_naive:.2f} µs, "
                f"speedup={naive_vs_cached[f'len={cl}']['speedup']:.1f}x"
            )

        metrics["naive_vs_cached"] = naive_vs_cached

        # ------------------------------------------------------------------
        # Validation
        # ------------------------------------------------------------------
        status = "passed"
        # Check that per-rule time is approximately constant (within 2x) across k
        per_rule_values = [v["per_rule_us"] for v in per_rule_times.values()]
        if max(per_rule_values) > 2 * min(per_rule_values):
            status = "partial"
            errors.append(f"Per-rule time varies too much across k: {per_rule_values}")
        # Check that chain independence holds (total time for 10 rules should not
        # grow more than 2x from len=1 to len=1000)
        chain_totals = [chain_independence[f"len={cl}"] for cl in chain_lengths]
        if chain_totals[-1] > 2 * chain_totals[0]:
            status = "partial"
            errors.append(f"Precondition time appears to grow with chain length: {chain_totals}")
        # Naive should be measurably slower for long chains
        if naive_vs_cached["len=1000"]["speedup"] < 2.0:
            status = "partial"
            errors.append(
                f"Naive vs cached speedup too low: {naive_vs_cached['len=1000']['speedup']}"
            )

        print("\n--- Summary ---")
        print(f"Status: {status}")
        if errors:
            for e in errors:
                print(f"  Warning: {e}")

        return ExperimentResult(
            experiment_id=self.experiment_id,
            status=status,
            metrics=metrics,
            raw_data=raw_data,
            errors=errors,
        )


if __name__ == "__main__":
    E34PreconditionFormalization().run()
