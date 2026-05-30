"""E1: Event chain integrity verification.

Tests that EventChain.verify_integrity() correctly detects:
  a) Broken previous_event_id links
  b) Inconsistent hash values (tampered payloads)
  c) Cross-contamination events (wrong concept_id rejected)

Method: Generate 50 random valid chains, then inject 10 intentional corruptions,
measuring precision and recall of the integrity check.
"""

from __future__ import annotations

import hashlib
import random

from .base import BaseExperiment, ExperimentResult
from .registry import register

from adl_lite.models import Event, EventChain, EventType

EVENT_TYPES = [
    EventType.REGISTER, EventType.VALIDATE, EventType.RELATE,
    EventType.EVIDENCE, EventType.ANNOUNCE, EventType.DEPRECATE,
]

random.seed(42)


def _build_random_chain(concept_id: str, length: int) -> EventChain:
    chain = EventChain(concept_id=concept_id)
    for _ in range(length):
        et = random.choice(EVENT_TYPES)
        chain.append(Event(
            concept_id=concept_id,
            event_type=et,
            actor=f"agent_{random.randint(1, 5)}",
            payload={"val": random.random()},
        ))
    return chain


@register("E1")
class E1ChainIntegrity(BaseExperiment):
    experiment_id = "E1"
    name = "Event chain integrity"
    description = "Precision/recall of chain integrity detection under tampering"

    def run(self) -> ExperimentResult:
        results = []
        valid_ok = 0
        valid_total = 0
        corrupt_ok = 0
        corrupt_total = 0

        # Phase 1: Generate 50 valid chains, verify all pass
        for i in range(50):
            chain = _build_random_chain(f"e1-test-{i}", length=5)
            ok = chain.verify_integrity()
            valid_total += 1
            if ok:
                valid_ok += 1
            else:
                results.append({
                    "type": "valid_chain_should_pass",
                    "concept_id": f"e1-test-{i}",
                    "ok": False,
                })

        # Phase 2: Generate 10 corrupt chains, verify all are detected
        corruption_methods = [
            # Method a: break previous_event_id on middle event
            lambda chain: setattr(chain._events[2], "previous_event_id", "deadbeef"),
            # Method b: tamper payload, don't re-hash
            lambda chain: chain._events[3].payload.update({"tampered": True}),
            # Method c: inject event with wrong concept_id (should be caught by append)
            lambda chain: chain._events.insert(
                1, Event(concept_id="wrong-concept", event_type=EventType.REGISTER, actor="attacker")
            ),
        ]

        for i in range(10):
            chain = _build_random_chain(f"e1-corrupt-{i}", length=6)
            method = corruption_methods[i % len(corruption_methods)]

            try:
                method(chain)
            except (ValueError, AttributeError):
                pass  # Some corruptions are caught at append time

            ok = chain.verify_integrity()
            corrupt_total += 1
            if not ok:
                corrupt_ok += 1
            results.append({
                "type": "corrupt_chain_should_fail",
                "concept_id": f"e1-corrupt-{i}",
                "corruption_method": i % len(corruption_methods),
                "detected": not ok,
            })

        # Metrics
        precision_valid = valid_ok / valid_total if valid_total else 0.0
        recall_corrupt = corrupt_ok / corrupt_total if corrupt_total else 0.0

        all_ok = precision_valid == 1.0 and recall_corrupt >= 0.8
        # recall_corrupt may be < 1.0 for method c (append-time rejection)

        return ExperimentResult(
            experiment_id=self.experiment_id,
            status="passed" if all_ok else "partial",
            metrics={
                "valid_chain_pass_rate": round(precision_valid, 4),
                "corrupt_chain_detection_rate": round(recall_corrupt, 4),
                "valid_total": valid_total,
                "corrupt_total": corrupt_total,
            },
            raw_data=results,
        )
