#!/usr/bin/env python3
"""
Benchmark: CRDT cached semantics (O(1)) vs simulated LWW scan (O(|V|)).

Demonstrates that the incremental cache in v0.3.5 makes CRDT semantics
as fast as the old LWW rule, despite the more complex derivation logic.

Usage:
    python experiments/benchmark_crdt_vs_lww.py

Output:
    Prints timing comparison for status/confidence queries and append
    operations at chain lengths 1K, 5K, 10K, 50K.
"""

from __future__ import annotations

import time

from adl_lite import Event, EventChain, EventType

# ---------------------------------------------------------------------------
# Simulated LWW (old behavior) — full scan on every query
# ---------------------------------------------------------------------------


def _lww_status_scan(chain: EventChain) -> str:
    """Simulate old LWW: status = type of last lifecycle event."""
    type_to_status = {
        EventType.REGISTER: "provisional",
        EventType.VALIDATE: "validated",
        EventType.DEPRECATE: "deprecated",
        EventType.FORK: "forked",
        EventType.ARCHIVE: "archived",
    }
    for event in reversed(chain._events):
        if event.event_type in type_to_status:
            return type_to_status[event.event_type]
    return "provisional"


def _lww_confidence_scan(chain: EventChain) -> float:
    """Simulate old LWW: confidence = last VALIDATE / SNAPSHOT confidence."""
    for event in reversed(chain._events):
        if event.event_type in (EventType.VALIDATE, EventType.SNAPSHOT):
            return float(event.payload.get("confidence", 0.0))
    return 0.0


# ---------------------------------------------------------------------------
# Benchmark helpers
# ---------------------------------------------------------------------------


def _build_chain(length: int, validate_every: int = 5) -> EventChain:
    """Build a chain of `length` events with sporadic VALIDATE."""
    chain = EventChain(concept_id="bench")
    for i in range(length):
        if i % validate_every == 0:
            chain.append(
                Event(
                    concept_id="bench",
                    event_type=EventType.VALIDATE,
                    actor=f"agent_{i % 10}",
                    payload={"confidence": 0.5 + (i % 50) / 100},
                )
            )
        else:
            chain.append(
                Event(
                    concept_id="bench",
                    event_type=EventType.REGISTER,
                    actor=f"agent_{i % 10}",
                )
            )
    return chain


def _benchmark(name: str, fn, repeats: int = 1000) -> float:
    """Return average time per call in microseconds."""
    start = time.perf_counter()
    for _ in range(repeats):
        fn()
    elapsed = time.perf_counter() - start
    avg_us = (elapsed / repeats) * 1e6
    return avg_us


# ---------------------------------------------------------------------------
# Main benchmark
# ---------------------------------------------------------------------------


def run():
    print("=" * 70)
    print(" ADL Lite — CRDT Cached vs LWW Scan Benchmark ".center(70))
    print("=" * 70)
    print(
        f"\n{'Chain length':>12} | {'Query':>18} | {'CRDT (μs)':>12} | {'LWW (μs)':>12} | {'Speedup':>10}"
    )
    print("-" * 70)

    for length in (1000, 5000, 10000, 50000):
        chain = _build_chain(length)
        _chain = chain

        # CRDT cached query
        crdt_status_us = _benchmark(
            "status", lambda chain=_chain: chain.status, repeats=max(100, 50000 // length)
        )
        crdt_conf_us = _benchmark(
            "confidence", lambda chain=_chain: chain.confidence, repeats=max(100, 50000 // length)
        )

        # LWW scan query
        lww_status_us = _benchmark(
            "status_scan",
            lambda chain=_chain: _lww_status_scan(chain),
            repeats=max(100, 50000 // length),
        )
        lww_conf_us = _benchmark(
            "conf_scan",
            lambda chain=_chain: _lww_confidence_scan(chain),
            repeats=max(100, 50000 // length),
        )

        status_speedup = lww_status_us / crdt_status_us if crdt_status_us > 0 else float("inf")
        conf_speedup = lww_conf_us / crdt_conf_us if crdt_conf_us > 0 else float("inf")

        print(
            f"{length:>12,} | {'status':>18} | {crdt_status_us:>12.2f} | {lww_status_us:>12.2f} | {status_speedup:>9.1f}x"
        )
        print(
            f"{'':>12} | {'confidence':>18} | {crdt_conf_us:>12.2f} | {lww_conf_us:>12.2f} | {conf_speedup:>9.1f}x"
        )
        print("-" * 70)

    # Append benchmark (both are O(1), but show absolute numbers)
    print("\nAppend benchmark (1,000 events):")
    chain = EventChain(concept_id="append-bench")

    def _append_1k():
        c = EventChain(concept_id="append-bench")
        for i in range(1000):
            c.append(
                Event(
                    concept_id="append-bench",
                    event_type=EventType.VALIDATE,
                    actor=f"agent_{i % 10}",
                    payload={"confidence": 0.85},
                )
            )
        return c

    append_us = _benchmark("append_1k", _append_1k, repeats=10)
    print(f"  Average time for 1,000 appends: {append_us / 1000:.2f} ms")
    print(f"  Per-append: {append_us / 1000:.2f} μs")

    print("\n" + "=" * 70)
    print("Done. ✓")
    print("=" * 70)


if __name__ == "__main__":
    run()
