"""
CRDT convergence proofs — executable tests verifying lattice properties.

Covers:
  1. Commutativity: merge(A,B) == merge(B,A)
  2. Associativity: merge(merge(A,B), C) == merge(A, merge(B,C))
  3. Idempotence: merge(A,A) == A
  4. Monotonicity: state never shrinks with event appends
  5. Convergence under partition: two edges, merge dominates both
  6. Multi-way merge: N edges, any merge order yields same result
  7. Round-trip: CRDTState → dict → back
  8. from_chain: derive CRDT state from existing EventChain
"""


from adl_lite.crdt import (
    CRDTState,
    StatusOrder,
    prove_associativity,
    prove_commutativity,
    prove_convergence_under_partition,
    prove_idempotence,
    prove_monotonicity,
    prove_multi_way_merge,
)
from adl_lite.models import Event, EventChain, EventType


class TestCRDTConvergence:
    """Executable CRDT convergence proofs."""

    def test_commutativity(self):
        prove_commutativity()

    def test_associativity(self):
        prove_associativity()

    def test_idempotence(self):
        prove_idempotence()

    def test_monotonicity(self):
        prove_monotonicity()

    def test_convergence_under_partition(self):
        prove_convergence_under_partition()

    def test_multi_way_merge(self):
        prove_multi_way_merge()


class TestCRDTState:
    """Unit tests for CRDTState operations."""

    def test_default_is_provisional(self):
        s = CRDTState()
        assert s.status == StatusOrder.PROVISIONAL
        assert s.confidence == 0.0
        assert s.validator_count == 0

    def test_status_order(self):
        """StatusOrder must reflect correct lifecycle progression."""
        assert StatusOrder.PROVISIONAL < StatusOrder.VALIDATED
        assert StatusOrder.FORKED < StatusOrder.VALIDATED
        assert StatusOrder.VALIDATED < StatusOrder.DEPRECATED
        assert StatusOrder.DEPRECATED < StatusOrder.ARCHIVED

    def test_merge_lub_for_status(self):
        """LUB of provisional+validated = validated."""
        a = CRDTState(status=StatusOrder.PROVISIONAL)
        b = CRDTState(status=StatusOrder.VALIDATED, confidence=0.8)
        merged = a.merge(b)
        assert merged.status == StatusOrder.VALIDATED
        # confidence follows G-Counter (max)
        assert merged.confidence == 0.8

    def test_merge_empty_is_neutral(self):
        s = CRDTState(StatusOrder.VALIDATED, 0.9, 3, 5)
        empty = CRDTState()
        assert s.merge(empty) == s
        assert empty.merge(s) == s

    def test_apply_event_validate(self):
        s = CRDTState()
        s2 = s.apply_event("validate", {"confidence": 0.85})
        assert s2.status == StatusOrder.VALIDATED
        assert s2.confidence == 0.85
        assert s2.validator_count == 1

    def test_apply_event_evidence(self):
        s = CRDTState()
        s2 = s.apply_event("evidence", {})
        assert s2.evidence_count == 1

    def test_apply_event_status_regression_prevented(self):
        """Cannot go from validated back to provisional."""
        s = CRDTState(status=StatusOrder.VALIDATED)
        s2 = s.apply_event("register", {})
        assert s2.status == StatusOrder.VALIDATED  # unchanged

    def test_into_dict_roundtrip(self):
        s = CRDTState(StatusOrder.DEPRECATED, 0.75, 4, 10)
        d = s.into_dict()
        assert d["status"] == "deprecated"
        assert d["confidence"] == 0.75
        assert d["validator_count"] == 4
        assert d["evidence_count"] == 10

    def test_from_chain(self):
        """Derive CRDT state from existing EventChain."""
        chain = EventChain(concept_id="crdt-test")
        chain.append(Event(concept_id="crdt-test", event_type=EventType.REGISTER, actor="a"))
        chain.append(
            Event(
                concept_id="crdt-test",
                event_type=EventType.VALIDATE,
                actor="b",
                payload={"confidence": 0.80},
            )
        )
        chain.append(Event(concept_id="crdt-test", event_type=EventType.EVIDENCE, actor="c"))
        chain.append(
            Event(
                concept_id="crdt-test",
                event_type=EventType.VALIDATE,
                actor="d",
                payload={"confidence": 0.92},
            )
        )

        state = CRDTState.from_chain(chain)

        assert state.status == StatusOrder.VALIDATED
        assert state.confidence == 0.92  # max of {0.80, 0.92}
        assert state.validator_count == 2
        assert state.evidence_count == 1
