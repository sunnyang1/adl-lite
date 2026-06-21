"""
experiments/benchmarks/concurrency_stress.py
Concurrency quantification tests.

Configurations:
    2/5/10/20 threads × 1000 events each
Measures:
    throughput, latency, conflict rate, integrity preservation rate
Output:
    table printed to stdout
"""

from __future__ import annotations

import threading
import time
from typing import Any

from adl_lite.models import Event, EventChain, EventType

THREAD_COUNTS = [2, 5, 10, 20]
EVENTS_PER_THREAD = 1000


def _run_benchmark(num_threads: int, events_per_thread: int) -> dict[str, Any]:
    chain = EventChain(concept_id="concurrency-stress")
    barrier = threading.Barrier(num_threads)
    results = {
        "thread_times": [],
        "errors": 0,
        "successful": 0,
    }
    lock = threading.Lock()

    def worker(tid: int) -> None:
        try:
            barrier.wait(timeout=5)
        except Exception:
            pass
        start = time.perf_counter()
        local_success = 0
        for i in range(events_per_thread):
            try:
                chain.append(
                    Event(
                        concept_id="concurrency-stress",
                        event_type=EventType.REGISTER,
                        actor=f"thread_{tid}",
                        payload={"index": i, "tid": tid},
                    )
                )
                local_success += 1
            except Exception:
                with lock:
                    results["errors"] += 1
        elapsed = time.perf_counter() - start
        with lock:
            results["thread_times"].append(elapsed)
            results["successful"] += local_success

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]

    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    total_time = time.perf_counter() - t0

    total_events = num_threads * events_per_thread
    throughput = total_events / total_time if total_time > 0 else 0.0
    max_latency = max(results["thread_times"]) if results["thread_times"] else 0.0
    conflicts = results["errors"]
    integrity_ok = chain.verify_integrity()
    integrity_rate = 1.0 if integrity_ok else 0.0

    return {
        "threads": num_threads,
        "total_events": total_events,
        "throughput": round(throughput, 2),
        "max_latency": round(max_latency, 4),
        "conflicts": conflicts,
        "integrity_rate": integrity_rate,
    }


def _print_table(rows: list[dict[str, Any]]) -> None:
    header = (
        f"{'threads':>8} | {'total_events':>12} | {'throughput':>12} | "
        f"{'max_latency':>12} | {'conflicts':>10} | {'integrity_rate':>14}"
    )
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['threads']:>8} | {r['total_events']:>12} | "
            f"{r['throughput']:>12.2f} | {r['max_latency']:>12.4f} | "
            f"{r['conflicts']:>10} | {r['integrity_rate']:>14.2f}"
        )


def run_concurrency_stress() -> list[dict[str, Any]]:
    rows = []
    for tc in THREAD_COUNTS:
        row = _run_benchmark(tc, EVENTS_PER_THREAD)
        rows.append(row)
    _print_table(rows)
    return rows


def test_concurrency_stress() -> None:
    """Pytest entry point."""
    rows = run_concurrency_stress()
    for r in rows:
        assert r["integrity_rate"] == 1.0, f"Integrity broken for {r['threads']} threads"
        assert r["conflicts"] == 0, f"Unexpected conflicts for {r['threads']} threads"


if __name__ == "__main__":
    run_concurrency_stress()
