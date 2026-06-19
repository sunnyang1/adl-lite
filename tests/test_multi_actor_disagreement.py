"""
tests/test_multi_actor_disagreement.py
20 distinct multi-actor disagreement scenarios for γ(C) and status transitions.
"""

from __future__ import annotations

import math
import pytest

from adl_lite.models import (
    DiscoveryStatus,
    Event,
    EventChain,
    EventType,
)

BETA = 0.05


def gamma(chain: EventChain, beta: float = BETA) -> float:
    """Confidence aggregation function γ(C) from paper §4.6."""
    V = [e for e in chain.events if e.event_type == EventType.VALIDATE]
    if not V:
        return 0.0

    actors = {e.actor for e in V}

    def phi(actor: str) -> float:
        confidences = [
            e.payload.get("confidence", 0.0)
            for e in V
            if e.actor == actor
        ]
        return max(confidences) if confidences else 0.0

    mean_phi = sum(phi(a) for a in actors) / len(actors) if actors else 0.0
    c_base = max(0.5, mean_phi)
    n_vals = len(actors)
    return min(1.0, c_base + beta * (n_vals - 1))


def _make_chain(events_data: list[dict]) -> EventChain:
    chain = EventChain(concept_id="multi-actor-test")
    for data in events_data:
        chain.append(
            Event(
                concept_id="multi-actor-test",
                event_type=data["event_type"],
                actor=data["actor"],
                payload=data.get("payload", {}),
            )
        )
    return chain


# 20 distinct scenarios
SCENARIOS = [
    # 1: no validators
    (
        [{"event_type": EventType.REGISTER, "actor": "system"}],
        0.0,
        DiscoveryStatus.PROVISIONAL,
    ),
    # 2: single high-confidence validator
    (
        [{"event_type": EventType.VALIDATE, "actor": "A", "payload": {"confidence": 0.9}}],
        0.9,
        DiscoveryStatus.VALIDATED,
    ),
    # 3: two validators disagreeing
    (
        [
            {"event_type": EventType.VALIDATE, "actor": "A", "payload": {"confidence": 0.9}},
            {"event_type": EventType.VALIDATE, "actor": "B", "payload": {"confidence": 0.3}},
        ],
        0.65,
        DiscoveryStatus.VALIDATED,
    ),
    # 4: two validators + deprecate
    (
        [
            {"event_type": EventType.VALIDATE, "actor": "A", "payload": {"confidence": 0.9}},
            {"event_type": EventType.VALIDATE, "actor": "B", "payload": {"confidence": 0.3}},
            {"event_type": EventType.DEPRECATE, "actor": "C"},
        ],
        0.65,
        DiscoveryStatus.DEPRECATED,
    ),
    # 5: two high validators
    (
        [
            {"event_type": EventType.VALIDATE, "actor": "A", "payload": {"confidence": 0.9}},
            {"event_type": EventType.VALIDATE, "actor": "B", "payload": {"confidence": 0.9}},
        ],
        0.95,
        DiscoveryStatus.VALIDATED,
    ),
    # 6: three high validators
    (
        [
            {"event_type": EventType.VALIDATE, "actor": "A", "payload": {"confidence": 0.9}},
            {"event_type": EventType.VALIDATE, "actor": "B", "payload": {"confidence": 0.9}},
            {"event_type": EventType.VALIDATE, "actor": "C", "payload": {"confidence": 0.9}},
        ],
        1.0,
        DiscoveryStatus.VALIDATED,
    ),
    # 7: duplicate actor low then high (max taken)
    (
        [
            {"event_type": EventType.VALIDATE, "actor": "A", "payload": {"confidence": 0.9}},
            {"event_type": EventType.VALIDATE, "actor": "A", "payload": {"confidence": 0.3}},
        ],
        0.9,
        DiscoveryStatus.VALIDATED,
    ),
    # 8: single low validator
    (
        [{"event_type": EventType.VALIDATE, "actor": "A", "payload": {"confidence": 0.3}}],
        0.5,
        DiscoveryStatus.VALIDATED,
    ),
    # 9: two low validators
    (
        [
            {"event_type": EventType.VALIDATE, "actor": "A", "payload": {"confidence": 0.3}},
            {"event_type": EventType.VALIDATE, "actor": "B", "payload": {"confidence": 0.3}},
        ],
        0.55,
        DiscoveryStatus.VALIDATED,
    ),
    # 10: three mixed validators
    (
        [
            {"event_type": EventType.VALIDATE, "actor": "A", "payload": {"confidence": 0.9}},
            {"event_type": EventType.VALIDATE, "actor": "B", "payload": {"confidence": 0.3}},
            {"event_type": EventType.VALIDATE, "actor": "C", "payload": {"confidence": 0.8}},
        ],
        min(1.0, max(0.5, (0.9 + 0.3 + 0.8) / 3.0) + BETA * 2),
        DiscoveryStatus.VALIDATED,
    ),
    # 11: deprecate then validate (CRDT LUB: DEPRECATED)
    (
        [
            {"event_type": EventType.VALIDATE, "actor": "A", "payload": {"confidence": 0.9}},
            {"event_type": EventType.DEPRECATE, "actor": "B"},
            {"event_type": EventType.VALIDATE, "actor": "C", "payload": {"confidence": 0.8}},
        ],
        0.9,
        DiscoveryStatus.DEPRECATED,
    ),
    # 12: validate then deprecate
    (
        [
            {"event_type": EventType.VALIDATE, "actor": "A", "payload": {"confidence": 0.9}},
            {"event_type": EventType.DEPRECATE, "actor": "B"},
            {"event_type": EventType.DEPRECATE, "actor": "C"},
        ],
        0.9,
        DiscoveryStatus.DEPRECATED,
    ),
    # 13: deprecate then validate then validate (CRDT LUB: DEPRECATED)
    (
        [
            {"event_type": EventType.VALIDATE, "actor": "A", "payload": {"confidence": 0.9}},
            {"event_type": EventType.VALIDATE, "actor": "B", "payload": {"confidence": 0.9}},
            {"event_type": EventType.DEPRECATE, "actor": "C"},
            {"event_type": EventType.VALIDATE, "actor": "D", "payload": {"confidence": 0.5}},
        ],
        min(1.0, max(0.5, (0.9 + 0.9 + 0.5) / 3.0) + BETA * 2),
        DiscoveryStatus.DEPRECATED,
    ),
    # 14: four max confidence
    (
        [
            {"event_type": EventType.VALIDATE, "actor": "A", "payload": {"confidence": 1.0}},
            {"event_type": EventType.VALIDATE, "actor": "B", "payload": {"confidence": 1.0}},
            {"event_type": EventType.VALIDATE, "actor": "C", "payload": {"confidence": 1.0}},
            {"event_type": EventType.VALIDATE, "actor": "D", "payload": {"confidence": 1.0}},
        ],
        1.0,
        DiscoveryStatus.VALIDATED,
    ),
    # 15: two zero confidence
    (
        [
            {"event_type": EventType.VALIDATE, "actor": "A", "payload": {"confidence": 0.0}},
            {"event_type": EventType.VALIDATE, "actor": "B", "payload": {"confidence": 0.0}},
        ],
        0.55,
        DiscoveryStatus.VALIDATED,
    ),
    # 16: four mixed validators
    (
        [
            {"event_type": EventType.VALIDATE, "actor": "A", "payload": {"confidence": 0.6}},
            {"event_type": EventType.VALIDATE, "actor": "B", "payload": {"confidence": 0.7}},
            {"event_type": EventType.VALIDATE, "actor": "C", "payload": {"confidence": 0.8}},
            {"event_type": EventType.VALIDATE, "actor": "D", "payload": {"confidence": 0.9}},
        ],
        min(1.0, max(0.5, (0.6 + 0.7 + 0.8 + 0.9) / 4.0) + BETA * 3),
        DiscoveryStatus.VALIDATED,
    ),
    # 17: duplicate actor lower confidence
    (
        [
            {"event_type": EventType.VALIDATE, "actor": "A", "payload": {"confidence": 0.9}},
            {"event_type": EventType.VALIDATE, "actor": "B", "payload": {"confidence": 0.3}},
            {"event_type": EventType.VALIDATE, "actor": "A", "payload": {"confidence": 0.5}},
        ],
        0.65,
        DiscoveryStatus.VALIDATED,
    ),
    # 18: duplicate actor higher confidence
    (
        [
            {"event_type": EventType.VALIDATE, "actor": "A", "payload": {"confidence": 0.9}},
            {"event_type": EventType.VALIDATE, "actor": "B", "payload": {"confidence": 0.3}},
            {"event_type": EventType.VALIDATE, "actor": "A", "payload": {"confidence": 1.0}},
        ],
        min(1.0, max(0.5, (1.0 + 0.3) / 2.0) + BETA * 1),
        DiscoveryStatus.VALIDATED,
    ),
    # 19: validate then deprecate by same actor
    (
        [
            {"event_type": EventType.VALIDATE, "actor": "A", "payload": {"confidence": 0.9}},
            {"event_type": EventType.VALIDATE, "actor": "B", "payload": {"confidence": 0.3}},
            {"event_type": EventType.DEPRECATE, "actor": "A"},
        ],
        0.65,
        DiscoveryStatus.DEPRECATED,
    ),
    # 20: validate then fork (CRDT LUB: VALIDATED dominates FORKED)
    (
        [
            {"event_type": EventType.VALIDATE, "actor": "A", "payload": {"confidence": 0.9}},
            {"event_type": EventType.VALIDATE, "actor": "B", "payload": {"confidence": 0.3}},
            {"event_type": EventType.FORK, "actor": "C"},
        ],
        0.65,
        DiscoveryStatus.VALIDATED,
    ),
]


class TestMultiActorDisagreement:
    """20 scenarios covering multi-actor validation, deprecation, and forking."""

    @pytest.mark.parametrize(
        "events, expected_gamma, expected_status",
        SCENARIOS,
    )
    def test_gamma_and_status(
        self,
        events: list[dict],
        expected_gamma: float,
        expected_status: DiscoveryStatus,
    ):
        chain = _make_chain(events)
        actual_gamma = gamma(chain)
        actual_status = chain.status

        assert math.isclose(
            actual_gamma,
            expected_gamma,
            rel_tol=1e-9,
            abs_tol=1e-9,
        ), f"γ(C) mismatch: expected {expected_gamma}, got {actual_gamma}"

        assert actual_status == expected_status, (
            f"Status mismatch: expected {expected_status}, got {actual_status}"
        )
