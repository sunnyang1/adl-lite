"""
CRDT merge_event_chains N>=3 formal proofs and edge case tests.

Tests the generalized merge_event_chains(*chains) supporting N>=3 chains
per Theorem 9 generalization (paper §4.7).
"""

from __future__ import annotations

import itertools
import time

import pytest

from adl_lite.models import Event, EventChain, EventType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    concept_id: str,
    event_type: EventType = EventType.REGISTER,
    timestamp: str = "2025-01-01T00:00:00+00:00",
    actor: str = "test",
    payload: dict | None = None,
) -> Event:
    """Create an event with explicit timestamp."""
    return Event(
        concept_id=concept_id,
        event_type=event_type,
        actor=actor,
        timestamp=timestamp,
        payload=payload or {},
    )


def _make_chain(concept_id: str, events: list[Event] | None = None) -> EventChain:
    """Create a chain with the given events."""
    chain = EventChain(concept_id=concept_id)
    if events:
        for e in events:
            chain.append(e)
    return chain


def _event_ids(chain: EventChain) -> set[str]:
    """Return the set of event_ids in a chain."""
    return {e.event_id for e in chain.events}


def _event_count(chain: EventChain) -> int:
    """Return the number of events in a chain."""
    return len(chain.events)


# ---------------------------------------------------------------------------
# Test class: N-way merge basic functionality
# ---------------------------------------------------------------------------


class TestMergeEventChainsN:
    """Tests for the generalized merge_event_chains(*chains) supporting N>=3."""

    def test_merge_2_chains(self) -> None:
        """2 chains → backward compatibility, same result as old API."""
        from adl_lite.crdt import merge_event_chains

        events_a = [
            _make_event("cap-1", EventType.REGISTER, "2025-01-01T10:00:00+00:00"),
            _make_event("cap-1", EventType.VALIDATE, "2025-01-01T11:00:00+00:00"),
        ]
        events_b = [
            _make_event("cap-1", EventType.REGISTER, "2025-01-01T10:00:00+00:00"),
            _make_event("cap-1", EventType.EVIDENCE, "2025-01-01T12:00:00+00:00"),
        ]

        chain_a = _make_chain("cap-1", events_a)
        chain_b = _make_chain("cap-1", events_b)

        result = merge_event_chains(chain_a, chain_b)

        # Should contain all events from both chains (deduped by event_id)
        event_ids = _event_ids(result)
        all_ids = _event_ids(chain_a) | _event_ids(chain_b)
        assert event_ids == all_ids
        # Result has at most |A| + |B| events after dedup
        assert result.length <= chain_a.length + chain_b.length

    def test_merge_3_chains(self) -> None:
        """3 chains with non-overlapping events → all events present."""
        from adl_lite.crdt import merge_event_chains

        chain_a = _make_chain(
            "cap-2",
            [
                _make_event("cap-2", EventType.REGISTER, "2025-01-02T10:00:00+00:00"),
                _make_event("cap-2", EventType.VALIDATE, "2025-01-02T11:00:00+00:00"),
            ],
        )
        chain_b = _make_chain(
            "cap-2",
            [
                _make_event("cap-2", EventType.EVIDENCE, "2025-01-02T12:00:00+00:00"),
            ],
        )
        chain_c = _make_chain(
            "cap-2",
            [
                _make_event("cap-2", EventType.DEPRECATE, "2025-01-02T13:00:00+00:00"),
                _make_event("cap-2", EventType.ARCHIVE, "2025-01-02T14:00:00+00:00"),
            ],
        )

        result = merge_event_chains(chain_a, chain_b, chain_c)

        # All 5 unique events should be present
        assert result.length == 5
        all_ids = _event_ids(chain_a) | _event_ids(chain_b) | _event_ids(chain_c)
        assert _event_ids(result) == all_ids

    def test_merge_5_chains(self) -> None:
        """5 chains, verify total event count = sum of unique event_ids."""
        from adl_lite.crdt import merge_event_chains

        chains = []
        expected_ids: set[str] = set()
        for i in range(5):
            events = [
                _make_event(
                    "cap-3",
                    EventType.REGISTER,
                    f"2025-01-03T{10 + i:02d}:00:00+00:00",
                    actor=f"agent_{i}",
                ),
                _make_event(
                    "cap-3",
                    EventType.VALIDATE,
                    f"2025-01-03T{10 + i:02d}:30:00+00:00",
                    actor=f"agent_{i}",
                ),
            ]
            chain = _make_chain("cap-3", events)
            chains.append(chain)
            expected_ids.update(_event_ids(chain))

        result = merge_event_chains(*chains)

        assert _event_count(result) == len(expected_ids)
        assert _event_ids(result) == expected_ids

    def test_merge_10_chains(self) -> None:
        """10 chains with 100 events each, verify performance < 1 second."""
        from adl_lite.crdt import merge_event_chains

        chains = []
        for i in range(10):
            events = []
            for j in range(100):
                hour = (i * 100 + j) // 60
                minute = (i * 100 + j) % 60
                events.append(
                    _make_event(
                        "cap-perf",
                        EventType.REGISTER,
                        f"2025-01-04T{hour:02d}:{minute:02d}:00+00:00",
                        actor=f"agent_{i}_{j}",
                    )
                )
            chains.append(_make_chain("cap-perf", events))

        start = time.perf_counter()
        result = merge_event_chains(*chains)
        elapsed = time.perf_counter() - start

        # Total unique events = 10 * 100 = 1000 (all different event_ids)
        assert result.length == 1000
        assert elapsed < 1.0, f"merge 10×100 chains took {elapsed:.3f}s, expected < 1s"

    # ------------------------------------------------------------------
    # Formal properties (N≥3)
    # ------------------------------------------------------------------

    def test_merge_n_way_commutative(self) -> None:
        """Any permutation yields same result for N=5."""
        from adl_lite.crdt import merge_event_chains

        chains = []
        for i in range(5):
            events = [
                _make_event(
                    "cap-comm",
                    EventType.REGISTER,
                    f"2025-01-05T{10 + i:02d}:00:00+00:00",
                    actor=f"agent_{i}",
                    payload={"data": f"val_{i}"},
                ),
                _make_event(
                    "cap-comm",
                    EventType.VALIDATE,
                    f"2025-01-05T{10 + i:02d}:30:00+00:00",
                    actor=f"agent_{i}",
                    payload={"confidence": 0.5 + i * 0.1},
                ),
            ]
            chains.append(_make_chain("cap-comm", events))

        # Get reference result from natural order
        reference = merge_event_chains(*chains)
        ref_ids = _event_ids(reference)
        ref_count = reference.length

        # Test several permutations
        for perm in itertools.permutations(chains):
            result = merge_event_chains(*perm)
            assert _event_count(result) == ref_count, "count mismatch for permutation"
            assert _event_ids(result) == ref_ids, "ids mismatch for permutation"
            # Verify event ordering by timestamp
            for j in range(result.length - 1):
                assert result.events[j].timestamp <= result.events[j + 1].timestamp, (
                    f"timestamp order violated in permutation at index {j}"
                )

    def test_merge_n_way_associative(self) -> None:
        """merge(merge(A,B), C) == merge(A, merge(B,C)) at EventChain level."""
        from adl_lite.crdt import merge_event_chains

        chain_a = _make_chain(
            "cap-assoc",
            [
                _make_event("cap-assoc", EventType.REGISTER, "2025-01-06T10:00:00+00:00"),
                _make_event("cap-assoc", EventType.VALIDATE, "2025-01-06T11:00:00+00:00"),
            ],
        )
        chain_b = _make_chain(
            "cap-assoc",
            [
                _make_event("cap-assoc", EventType.EVIDENCE, "2025-01-06T12:00:00+00:00"),
            ],
        )
        chain_c = _make_chain(
            "cap-assoc",
            [
                _make_event("cap-assoc", EventType.DEPRECATE, "2025-01-06T13:00:00+00:00"),
            ],
        )

        # Left-associative: merge(merge(A, B), C)
        left = merge_event_chains(merge_event_chains(chain_a, chain_b), chain_c)

        # Right-associative: merge(A, merge(B, C))
        right = merge_event_chains(chain_a, merge_event_chains(chain_b, chain_c))

        assert _event_ids(left) == _event_ids(right)
        assert left.length == right.length

        # Also test the N-way call == pairwise fold
        n_way = merge_event_chains(chain_a, chain_b, chain_c)
        assert _event_ids(n_way) == _event_ids(left)

    def test_merge_n_way_idempotent(self) -> None:
        """merge(A, A, A) == merge(A, A) == copy of A."""
        from adl_lite.crdt import merge_event_chains

        chain = _make_chain(
            "cap-idem",
            [
                _make_event("cap-idem", EventType.REGISTER, "2025-01-07T10:00:00+00:00"),
                _make_event("cap-idem", EventType.VALIDATE, "2025-01-07T11:00:00+00:00"),
            ],
        )

        result_aa = merge_event_chains(chain, chain)
        result_aaa = merge_event_chains(chain, chain, chain)

        assert _event_ids(result_aa) == _event_ids(chain)
        assert result_aa.length == chain.length
        assert _event_ids(result_aaa) == _event_ids(chain)
        assert result_aaa.length == chain.length

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_merge_zero_chains_raises(self) -> None:
        """Calling merge_event_chains() with no arguments raises ValueError."""
        from adl_lite.crdt import merge_event_chains

        with pytest.raises(ValueError, match="At least one EventChain required"):
            merge_event_chains()

    def test_merge_single_chain_identity(self) -> None:
        """Single chain → returns a copy (not the same object)."""
        from adl_lite.crdt import merge_event_chains

        chain = _make_chain(
            "cap-single",
            [
                _make_event("cap-single", EventType.REGISTER, "2025-01-08T10:00:00+00:00"),
                _make_event("cap-single", EventType.VALIDATE, "2025-01-08T11:00:00+00:00"),
            ],
        )

        result = merge_event_chains(chain)

        # Result is a copy, not the same object
        assert result is not chain
        assert result.concept_id == chain.concept_id
        assert _event_ids(result) == _event_ids(chain)
        assert result.length == chain.length

    def test_merge_empty_chains(self) -> None:
        """3 empty chains → result is empty."""
        from adl_lite.crdt import merge_event_chains

        chain_a = EventChain(concept_id="cap-empty")
        chain_b = EventChain(concept_id="cap-empty")
        chain_c = EventChain(concept_id="cap-empty")

        result = merge_event_chains(chain_a, chain_b, chain_c)

        assert result.length == 0
        assert result.concept_id == "cap-empty"

    def test_merge_identical_chains(self) -> None:
        """3 copies of same chain → single copy (idempotent, deduplicated)."""
        from adl_lite.crdt import merge_event_chains

        events = [
            _make_event("cap-id", EventType.REGISTER, "2025-01-09T10:00:00+00:00"),
            _make_event("cap-id", EventType.VALIDATE, "2025-01-09T11:00:00+00:00"),
            _make_event("cap-id", EventType.EVIDENCE, "2025-01-09T12:00:00+00:00"),
        ]
        chain = _make_chain("cap-id", events)

        result = merge_event_chains(chain, chain, chain)

        assert result.length == chain.length
        assert _event_ids(result) == _event_ids(chain)

    def test_merge_timestamp_conflicts(self) -> None:
        """Two different event_ids with same timestamp → both preserved."""
        from adl_lite.crdt import merge_event_chains

        # Same timestamp, different event_ids
        e1 = _make_event("cap-ts", EventType.REGISTER, "2025-01-10T12:00:00+00:00")
        e2 = _make_event("cap-ts", EventType.VALIDATE, "2025-01-10T12:00:00+00:00")

        chain_a = _make_chain("cap-ts", [e1])
        chain_b = _make_chain("cap-ts", [e2])

        result = merge_event_chains(chain_a, chain_b)

        # Both events should be present (different event_ids, same timestamp)
        assert result.length == 2
        result_ids = _event_ids(result)
        assert e1.event_id in result_ids
        assert e2.event_id in result_ids

    def test_merge_partial_overlap(self) -> None:
        """chain A has {e1,e2,e3}, chain B has {e2,e3,e4} → result has {e1,e2,e3,e4}."""
        from adl_lite.crdt import merge_event_chains

        e1 = _make_event("cap-overlap", EventType.REGISTER, "2025-01-11T10:00:00+00:00")
        e2 = _make_event("cap-overlap", EventType.VALIDATE, "2025-01-11T11:00:00+00:00")
        e3 = _make_event("cap-overlap", EventType.EVIDENCE, "2025-01-11T12:00:00+00:00")
        e4 = _make_event("cap-overlap", EventType.DEPRECATE, "2025-01-11T13:00:00+00:00")

        chain_a = _make_chain("cap-overlap", [e1, e2, e3])
        chain_b = _make_chain("cap-overlap", [e2, e3, e4])

        result = merge_event_chains(chain_a, chain_b)

        assert result.length == 4
        result_ids = _event_ids(result)
        assert e1.event_id in result_ids
        assert e2.event_id in result_ids
        assert e3.event_id in result_ids
        assert e4.event_id in result_ids

    def test_merge_different_concept_ids(self) -> None:
        """Merging chains with different concept_ids raises ValueError."""
        from adl_lite.crdt import merge_event_chains

        chain_a = EventChain(concept_id="cap-x")
        chain_b = EventChain(concept_id="cap-y")

        with pytest.raises(ValueError, match="concept_id"):
            merge_event_chains(chain_a, chain_b)

        # Also test with 3 chains, where mismatch is in the middle
        chain_c = EventChain(concept_id="cap-x")
        with pytest.raises(ValueError, match="concept_id"):
            merge_event_chains(chain_a, chain_c, chain_b)

    def test_merge_with_prove_multi_way(self) -> None:
        """Calls the new prove_event_chain_multi_way_merge() EventChain version."""
        from adl_lite.crdt import prove_event_chain_multi_way_merge

        # Should not raise
        prove_event_chain_multi_way_merge()

    def test_merge_lww_on_duplicate_event_id(self) -> None:
        """When two chains have the same event_id, LWW picks the later timestamp."""
        from adl_lite.crdt import merge_event_chains

        # Create two events with the same explicit event_id but different timestamps
        e_old = Event(
            event_id="fixed-id-001",
            concept_id="cap-lww",
            event_type=EventType.REGISTER,
            actor="agent-old",
            timestamp="2025-01-12T10:00:00+00:00",
            payload={"version": "old"},
        )
        e_new = Event(
            event_id="fixed-id-001",
            concept_id="cap-lww",
            event_type=EventType.REGISTER,
            actor="agent-new",
            timestamp="2025-01-12T11:00:00+00:00",
            payload={"version": "new"},
        )

        chain_a = _make_chain("cap-lww", [e_old])
        chain_b = _make_chain("cap-lww", [e_new])

        result = merge_event_chains(chain_a, chain_b)

        assert result.length == 1
        result_event = result.events[0]
        assert result_event.actor == "agent-new"
        assert result_event.payload == {"version": "new"}

    def test_merge_preserves_timestamp_order(self) -> None:
        """Merged chain events are sorted by timestamp (causal order)."""
        from adl_lite.crdt import merge_event_chains

        chain_a = _make_chain(
            "cap-order",
            [
                _make_event("cap-order", EventType.REGISTER, "2025-01-13T14:00:00+00:00"),
                _make_event("cap-order", EventType.ARCHIVE, "2025-01-13T15:00:00+00:00"),
            ],
        )
        chain_b = _make_chain(
            "cap-order",
            [
                _make_event("cap-order", EventType.VALIDATE, "2025-01-13T12:00:00+00:00"),
                _make_event("cap-order", EventType.EVIDENCE, "2025-01-13T13:00:00+00:00"),
            ],
        )
        chain_c = _make_chain(
            "cap-order",
            [
                _make_event("cap-order", EventType.DEPRECATE, "2025-01-13T16:00:00+00:00"),
            ],
        )

        result = merge_event_chains(chain_a, chain_b, chain_c)

        # Verify strict timestamp ordering
        for i in range(result.length - 1):
            ts_i = result.events[i].timestamp
            ts_next = result.events[i + 1].timestamp
            assert ts_i <= ts_next, f"Timestamp order violation: {ts_i} > {ts_next} at index {i}"

    def test_merge_concept_id_preserved(self) -> None:
        """Merged chain preserves the original concept_id."""
        from adl_lite.crdt import merge_event_chains

        chain_a = _make_chain(
            "cap-preserve",
            [_make_event("cap-preserve", EventType.REGISTER, "2025-01-14T10:00:00+00:00")],
        )
        chain_b = _make_chain(
            "cap-preserve",
            [_make_event("cap-preserve", EventType.VALIDATE, "2025-01-14T11:00:00+00:00")],
        )

        result = merge_event_chains(chain_a, chain_b)
        assert result.concept_id == "cap-preserve"

        result_3 = merge_event_chains(chain_a, chain_b, chain_a)
        assert result_3.concept_id == "cap-preserve"
