"""Proof trace checker T2/T3 must match the CRDT LUB derivation semantics.

Regression test for the E24 ``proof_trace_checker_results.json`` anomaly:
T2 (Fork Confluence) pass rate was 0.0327 and T3 (Transition Monotonicity)
was 0.1203, contradicting the paper's claim that randomized trace checking
confirms the theorems (``05_empirical_validation.tex`` §5, E25 narrative;
``04_architecture.tex`` §4.2.1).

Root cause: the checker assumed last-writer-wins semantics ("after FORK,
status == FORKED"; "after DEPRECATE, status == DEPRECATED"), but ADL Lite
derives status as the CRDT LUB over ALL lifecycle events (``crdt.py``
``StatusOrder``; ``models.py`` ``_compute_status_from_events``). When a chain
already contains DEPRECATE/ARCHIVE, the LUB keeps the higher status, so the
old assertions failed on genuinely correct chains.

These tests pin the correct behaviour: fork/transition checks must use LUB
semantics, i.e. status after the event equals ``max(before, event_status)``.
"""

from __future__ import annotations

import random

from adl_lite.crdt import StatusOrder
from adl_lite.models import DiscoveryStatus, Event, EventChain, EventType
from experiments import proof_trace_checker as ptc


def _lub(a: DiscoveryStatus, b: DiscoveryStatus) -> DiscoveryStatus:
    """CRDT LUB: the higher of two statuses in the lattice order."""
    return a if StatusOrder[a.name] >= StatusOrder[b.name] else b


def test_t2_checker_uses_lub_semantics() -> None:
    """FORK must raise status to max(previous, forked), not force FORKED."""
    # Chain that already reached DEPRECATED: LUB(DEPRECATED, FORKED) = DEPRECATED
    chain = EventChain(concept_id="t2-lub")
    chain.append(Event(concept_id="t2-lub", event_type=EventType.REGISTER, actor="a"))
    chain.append(Event(concept_id="t2-lub", event_type=EventType.DEPRECATE, actor="a"))
    assert chain.status == DiscoveryStatus.DEPRECATED

    ok = ptc.check_theorem_2_fork_confluence(chain)
    assert ok, (
        "T2 must pass when LUB(previous, FORKED) keeps a higher status; "
        "the checker must not require status == FORKED (LWW assumption)"
    )
    # LUB semantics: status after fork is max(previous, forked)
    assert chain.status == _lub(DiscoveryStatus.DEPRECATED, DiscoveryStatus.FORKED)


def test_t2_checker_raises_status_when_previous_is_lower() -> None:
    """FORK on a provisional chain must produce FORKED."""
    chain = EventChain(concept_id="t2-raise")
    chain.append(Event(concept_id="t2-raise", event_type=EventType.REGISTER, actor="a"))
    assert chain.status == DiscoveryStatus.PROVISIONAL

    ok = ptc.check_theorem_2_fork_confluence(chain)
    assert ok
    assert chain.status == DiscoveryStatus.FORKED


def test_t3_checker_uses_lub_semantics() -> None:
    """DEPRECATE must raise status to max(previous, deprecated), not force DEPRECATED."""
    # Chain that already reached ARCHIVED: LUB(ARCHIVED, DEPRECATED) = ARCHIVED
    chain = EventChain(concept_id="t3-lub")
    chain.append(Event(concept_id="t3-lub", event_type=EventType.REGISTER, actor="a"))
    chain.append(Event(concept_id="t3-lub", event_type=EventType.ARCHIVE, actor="a"))
    assert chain.status == DiscoveryStatus.ARCHIVED

    ok = ptc.check_theorem_3_transition_monotonicity(chain)
    assert ok, (
        "T3 must pass when LUB(previous, DEPRECATED) keeps a higher status; "
        "the checker must not require status == DEPRECATED (LWW assumption)"
    )
    assert chain.status == _lub(DiscoveryStatus.ARCHIVED, DiscoveryStatus.DEPRECATED)


def test_t3_checker_comm_event_preserves_status() -> None:
    """A communication event must never change derived status (LUB is over lifecycle only)."""
    chain = EventChain(concept_id="t3-comm")
    chain.append(Event(concept_id="t3-comm", event_type=EventType.REGISTER, actor="a"))
    before = chain.status
    chain.append(
        Event(
            concept_id="t3-comm",
            event_type=EventType.ANNOUNCE,
            actor="a",
            payload={"action": "announce"},
        )
    )
    assert chain.status == before


def test_random_traces_t2_t3_pass_rate_is_high() -> None:
    """Over random traces, T2/T3 must pass at ~100% under LUB semantics."""
    random.seed(42)
    t2_fail = 0
    t3_fail = 0
    n = 200
    for i in range(n):
        chain = ptc.generate_random_chain(
            concept_id=f"trace-{i}", min_length=2, max_length=30, seed=i
        )
        if not chain.verify_integrity():
            continue  # generator produced an invalid chain; not a theorem failure
        if not ptc.check_theorem_2_fork_confluence(chain):
            t2_fail += 1
        if not ptc.check_theorem_3_transition_monotonicity(chain):
            t3_fail += 1
    # Allow tiny slack for generator edge cases; the old checker failed 96.7%/87.97%.
    assert t2_fail / n < 0.05, f"T2 failed {t2_fail}/{n} traces (expected <5%)"
    assert t3_fail / n < 0.05, f"T3 failed {t3_fail}/{n} traces (expected <5%)"
