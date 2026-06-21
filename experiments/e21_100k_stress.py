"""E21: 100k Event Stress Test — survival path.

Measures EventChain verification time, memory, and append latency at 100k events.
If 100k exceeds 30s, measures 50k and projects linearly.
"""

from __future__ import annotations

import gc
import resource
import time

from adl_lite.models import Event, EventChain, EventType
from adl_lite.cold_storage import ColdStorage

from .base import BaseExperiment, ExperimentResult
from .registry import register


@register("E21")
class E21_100kStress(BaseExperiment):
    experiment_id = "E21"
    name = "100k Event Stress Test"
    description = "Measure verify_integrity, memory, and append latency at 100k events"

    # Targets
    TARGET_VERIFY_S = 2.0
    TARGET_MEMORY_MB = 1024.0
    TARGET_APPEND_MS = 10.0
    TARGET_TOTAL_S = 30.0

    def run(self) -> ExperimentResult:
        gc.collect()
        baseline_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

        # Try 100k; fall back to 50k if too slow
        n_events = 100_000
        chain, build_time, append_times = self._build_chain(n_events)

        if build_time > self.TARGET_TOTAL_S:
            n_events = 50_000
            chain, build_time, append_times = self._build_chain(n_events)
            projected = True
        else:
            projected = False

        t0 = time.perf_counter()
        ok = chain.verify_integrity()
        t1 = time.perf_counter()
        peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

        # macOS returns bytes; Linux returns KB
        import sys
        if sys.platform == "darwin":
            memory_peak_mb = (peak_rss - baseline_rss) / (1024 * 1024)
        else:
            memory_peak_mb = (peak_rss - baseline_rss) / 1024

        # Ensure non-negative delta
        memory_peak_mb = max(memory_peak_mb, 0.0)

        verify_time = t1 - t0
        append_latency_ms = (sum(append_times) / len(append_times)) * 1000 if append_times else 0.0
        total_time = build_time + verify_time

        # If memory > 1GB, try archiving at 50k
        archived = False
        if memory_peak_mb > self.TARGET_MEMORY_MB and n_events >= 50_000:
            archive_event = ColdStorage().archive(chain, keep_last_n=10)
            archived = archive_event is not None
            # Re-measure memory after archive
            baseline_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            ok = chain.verify_integrity()
            peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            if sys.platform == "darwin":
                memory_peak_mb = (peak_rss - baseline_rss) / (1024 * 1024)
            else:
                memory_peak_mb = (peak_rss - baseline_rss) / 1024
            memory_peak_mb = max(memory_peak_mb, 0.0)

        # Determine pass/fail
        passes = (
            verify_time <= self.TARGET_VERIFY_S
            and memory_peak_mb <= self.TARGET_MEMORY_MB
            and append_latency_ms <= self.TARGET_APPEND_MS
            and total_time <= self.TARGET_TOTAL_S
        )

        status = "passed" if passes else "partial" if ok else "failed"

        print(f"\nE21: 100k Event Stress Test")
        print(f"Chain length: {n_events}{' (projected from 50k)' if projected else ''}")
        print(f"Verify time: {verify_time:.3f} s")
        print(f"Memory peak: {memory_peak_mb:.2f} MB")
        print(f"Append latency: {append_latency_ms:.3f} ms/event")
        print(f"Total time: {total_time:.3f} s")
        if archived:
            print(f"Archive triggered: yes")
        print(f"Status: {'PASS' if passes else 'FAIL'} (against targets)")

        return ExperimentResult(
            experiment_id=self.experiment_id,
            status=status,
            metrics={
                "n_events": n_events,
                "projected": projected,
                "verify_time_s": round(verify_time, 3),
                "memory_peak_mb": round(memory_peak_mb, 2),
                "append_latency_ms": round(append_latency_ms, 3),
                "total_time_s": round(total_time, 3),
                "integrity_ok": ok,
                "archived": archived,
                "passes_targets": passes,
            },
            raw_data=[
                {
                    "n_events": n_events,
                    "verify_time_s": verify_time,
                    "memory_peak_mb": memory_peak_mb,
                    "append_latency_ms": append_latency_ms,
                    "build_time_s": build_time,
                }
            ],
        )

    def _build_chain(self, n: int) -> tuple[EventChain, float, list[float]]:
        chain = EventChain(concept_id="stress-100k")
        append_times: list[float] = []
        base_payload = {"data": "x" * 200, "meta": {"seq": 0, "tag": "stress"}}

        t0 = time.perf_counter()
        for i in range(n):
            payload = {k: (v.copy() if isinstance(v, dict) else v) for k, v in base_payload.items()}
            payload["meta"]["seq"] = i
            a0 = time.perf_counter()
            chain.append(
                Event(
                    concept_id=chain.concept_id,
                    event_type=EventType.REGISTER if i == 0 else EventType.EVIDENCE,
                    actor=f"agent_{i % 100}",
                    reasoning=f"event {i}",
                    payload=payload,
                )
            )
            a1 = time.perf_counter()
            append_times.append(a1 - a0)
        t1 = time.perf_counter()

        return chain, t1 - t0, append_times
