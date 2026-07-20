"""E2: Status derivation accuracy.

Verifies that EventChain.status correctly derives from any event sequence.
This is the foundational experiment — all other event-first tests depend on
correct status derivation.

Method: Exhaustive enumeration of 3-event sequences using lifecycle + comm
event types, comparing chain.status to expected ground truth.
"""

from __future__ import annotations

import itertools

from adl_lite.models import DiscoveryStatus, Event, EventChain, EventType

from .base import BaseExperiment, ExperimentResult
from .registry import register

# Ground truth: given a sequence of event types, what status should the chain have?
# Rule: LUB (max) over lifecycle lattice.  Communication events (ANNOUNCE, PUBLISH,
# RELATE, EVIDENCE, SEAL, SNAPSHOT) map to PROVISIONAL and do not affect the LUB.
# This matches the CRDT join-semantics in EventChain._update_crdt_caches.

LIFECYCLE_EVENTS = {
    EventType.REGISTER: DiscoveryStatus.PROVISIONAL,
    EventType.VALIDATE: DiscoveryStatus.VALIDATED,
    EventType.DEPRECATE: DiscoveryStatus.DEPRECATED,
    EventType.FORK: DiscoveryStatus.FORKED,
    EventType.ARCHIVE: DiscoveryStatus.ARCHIVED,
}

STATUS_ORDER = {
    DiscoveryStatus.PROVISIONAL: 0,
    DiscoveryStatus.FORKED: 1,
    DiscoveryStatus.VALIDATED: 2,
    DiscoveryStatus.DEPRECATED: 3,
    DiscoveryStatus.ARCHIVED: 4,
}

# All event types we enumerate over
ALL_TYPES = list(EventType)


def _expected_status(events: list[EventType]) -> DiscoveryStatus:
    """Ground truth: LUB of all lifecycle event statuses. Empty chain = PROVISIONAL.

    This is the CRDT join-semantics: status is the max over the lifecycle lattice,
    never regressing.  It is *not* "last lifecycle event wins" because the lattice
    order is monotonic (e.g. VALIDATE then FORK stays VALIDATED, not FORKED).
    """
    max_order = -1
    for et in events:
        if et in LIFECYCLE_EVENTS:
            order = STATUS_ORDER[LIFECYCLE_EVENTS[et]]
            if order > max_order:
                max_order = order
    if max_order < 0:
        return DiscoveryStatus.PROVISIONAL
    return DiscoveryStatus([s for s, o in STATUS_ORDER.items() if o == max_order][0])


@register("E2")
class E2StatusDerivation(BaseExperiment):
    experiment_id = "E2"
    name = "Status derivation accuracy"
    description = "Verify chain.status correctly derives from all event sequences"

    def run(self) -> ExperimentResult:
        results = []
        errors = []
        correct = 0
        total = 0

        # Exhaustive: all 3-event sequences (13^3 = 2197 combinations)
        for combo in itertools.product(ALL_TYPES, repeat=3):
            chain = EventChain(concept_id="e2-test")
            for et in combo:
                chain.append(Event(concept_id="e2-test", event_type=et, actor="system"))

            derived = chain.status
            expected = _expected_status(list(combo))
            ok = derived == expected
            total += 1
            if ok:
                correct += 1
            else:
                err = (
                    f"Events={[e.value for e in combo]} "
                    f"expected={expected.value} derived={derived.value}"
                )
                errors.append(err)
                results.append(
                    {
                        "events": [e.value for e in combo],
                        "expected": expected.value,
                        "derived": derived.value,
                        "ok": False,
                    }
                )

        # Also test edge cases
        edge_cases = [
            ([], DiscoveryStatus.PROVISIONAL, "empty chain → provisional"),
            ([EventType.REGISTER], DiscoveryStatus.PROVISIONAL, "register only"),
            (
                [EventType.REGISTER, EventType.VALIDATE],
                DiscoveryStatus.VALIDATED,
                "register→validate",
            ),
            ([EventType.REGISTER, EventType.FORK], DiscoveryStatus.FORKED, "register→fork"),
            (
                [EventType.REGISTER, EventType.VALIDATE, EventType.DEPRECATE],
                DiscoveryStatus.DEPRECATED,
                "full lifecycle",
            ),
            (
                [EventType.REGISTER, EventType.ANNOUNCE, EventType.PUBLISH],
                DiscoveryStatus.PROVISIONAL,
                "comms dont change status",
            ),
            (
                [EventType.REGISTER, EventType.VALIDATE, EventType.RELATE],
                DiscoveryStatus.VALIDATED,
                "validate+relate → validated",
            ),
        ]

        for events, expected, label in edge_cases:
            chain = EventChain(concept_id="e2-edge")
            for et in events:
                chain.append(Event(concept_id="e2-edge", event_type=et, actor="system"))
            derived = chain.status
            ok = derived == expected
            total += 1
            if ok:
                correct += 1
            else:
                errors.append(
                    f"Edge case [{label}]: expected={expected.value} derived={derived.value}"
                )

        accuracy = correct / total if total else 0.0

        return ExperimentResult(
            experiment_id=self.experiment_id,
            status="passed" if accuracy == 1.0 else "partial",
            metrics={
                "total_cases": total,
                "correct": correct,
                "accuracy": round(accuracy, 4),
                "error_count": len(errors),
            },
            raw_data=results,
            errors=errors[:20],  # Truncate error list
        )
