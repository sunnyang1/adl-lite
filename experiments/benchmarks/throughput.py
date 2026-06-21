"""
experiments/benchmarks/throughput.py
Standalone throughput benchmark for ADL Lite.

Benchmarks:
    - event append
    - chain integrity verification
    - consensus transitions
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from adl_lite.models import (
    ADLDocument,
    ADLFrontMatter,
    ADLType,
    DiscoveryStatus,
    Event,
    EventChain,
    EventType,
)
from adl_lite.consensus import ConsensusEngine

N_APPEND = 10_000
N_VERIFY = 1_000
N_TRANSITIONS = 1_000


def benchmark_event_append() -> dict[str, Any]:
    chain = EventChain(concept_id="bench-append")
    start = time.perf_counter()
    for i in range(N_APPEND):
        chain.append(
            Event(
                concept_id="bench-append",
                event_type=EventType.REGISTER,
                actor=f"agent_{i % 5}",
                payload={"idx": i},
            )
        )
    elapsed = time.perf_counter() - start
    return {
        "operation": "event_append",
        "count": N_APPEND,
        "elapsed_sec": round(elapsed, 4),
        "throughput_eps": round(N_APPEND / elapsed, 2) if elapsed > 0 else 0.0,
    }


def benchmark_integrity_verify() -> dict[str, Any]:
    chain = EventChain(concept_id="bench-verify")
    for i in range(N_VERIFY):
        chain.append(
            Event(
                concept_id="bench-verify",
                event_type=EventType.VALIDATE,
                actor="agent_1",
                payload={"confidence": 0.85},
            )
        )
    start = time.perf_counter()
    ok = chain.verify_integrity()
    elapsed = time.perf_counter() - start
    return {
        "operation": "integrity_verify",
        "count": N_VERIFY,
        "elapsed_sec": round(elapsed, 4),
        "throughput_cps": round(N_VERIFY / elapsed, 2) if elapsed > 0 else 0.0,
        "integrity_ok": ok,
    }


def benchmark_consensus_transitions() -> dict[str, Any]:
    engine = ConsensusEngine()
    docs = []
    for i in range(N_TRANSITIONS):
        doc = ADLDocument(
            front_matter=ADLFrontMatter(
                adl_type=ADLType.DISCOVERY,
                adl_id=f"bench-transition-{i}",
                status=DiscoveryStatus.PROVISIONAL,
                confidence=0.0,
            )
        )
        engine.register(doc)
        docs.append(doc)

    start = time.perf_counter()
    for i, doc in enumerate(docs):
        engine.transition(
            doc.adl_id,
            DiscoveryStatus.VALIDATED,
            actor=f"agent_{i % 3}",
            payload={"confidence": 0.8},
        )
    elapsed = time.perf_counter() - start
    return {
        "operation": "consensus_transitions",
        "count": N_TRANSITIONS,
        "elapsed_sec": round(elapsed, 4),
        "throughput_tps": round(N_TRANSITIONS / elapsed, 2) if elapsed > 0 else 0.0,
    }


def run_all() -> list[dict[str, Any]]:
    results = []
    results.append(benchmark_event_append())
    results.append(benchmark_integrity_verify())
    results.append(benchmark_consensus_transitions())

    print("\n=== ADL Lite Throughput Benchmark ===\n")
    for r in results:
        print(f"  {r['operation']}")
        for k, v in r.items():
            if k != "operation":
                print(f"    {k}: {v}")
        print()
    return results


def test_benchmark_throughput() -> None:
    """Pytest wrapper."""
    results = run_all()
    for r in results:
        assert r["elapsed_sec"] > 0
        if r["operation"] == "integrity_verify":
            assert r["integrity_ok"] is True


if __name__ == "__main__":
    run_all()
