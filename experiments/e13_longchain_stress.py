"""E13: Long-chain performance degradation (negative-result experiment).

Tests that VerifyIntegrity remains O(n) in theory but exhibits measurable
latency degradation and memory pressure at scale.  This experiment is designed
to produce *bounded* negative results: we expect linear growth, but we report
the exact constants and the point where GC / memory pressure becomes visible.
"""

from __future__ import annotations

import gc
import time
import tracemalloc

from adl_lite.models import Event, EventChain, EventType

from .base import BaseExperiment, ExperimentResult
from .registry import register


@register("E13")
class E13LongChainStress(BaseExperiment):
    experiment_id = "E13"
    name = "Long-chain performance degradation"
    description = "VerifyIntegrity latency and memory at 100–50k events"

    def run(self) -> ExperimentResult:
        raw_data = []
        # Test points: geometric progression
        sizes = [100, 500, 1_000, 5_000, 10_000, 20_000, 50_000]

        for n in sizes:
            chain = self._build_chain(n)
            # Warm-up + GC baseline
            gc.collect()
            tracemalloc.start()
            t0 = time.perf_counter()
            ok = chain.verify_integrity()
            t1 = time.perf_counter()
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            raw_data.append(
                {
                    "n_events": n,
                    "verify_ms": round((t1 - t0) * 1000, 3),
                    "memory_current_mb": round(current / (1024 * 1024), 3),
                    "memory_peak_mb": round(peak / (1024 * 1024), 3),
                    "integrity_ok": ok,
                    "events_per_ms": round(n / ((t1 - t0) * 1000), 1),
                }
            )

        # Compute linear regression slope (ms per event)
        import statistics
        xs = [d["n_events"] for d in raw_data]
        ys = [d["verify_ms"] for d in raw_data]
        mean_x = statistics.mean(xs)
        mean_y = statistics.mean(ys)
        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        den = sum((x - mean_x) ** 2 for x in xs)
        slope = num / den if den else 0.0
        intercept = mean_y - slope * mean_x

        # R^2
        ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
        ss_tot = sum((y - mean_y) ** 2 for y in ys)
        r_squared = 1 - ss_res / ss_tot if ss_tot else 0.0

        # Identify the point where memory > 50 MB (soft threshold)
        memory_threshold_hit = next(
            (d for d in raw_data if d["memory_peak_mb"] > 50), None
        )

        return ExperimentResult(
            experiment_id=self.experiment_id,
            status="passed",
            metrics={
                "slope_ms_per_event": round(slope * 1000, 6),  # microseconds
                "intercept_ms": round(intercept, 3),
                "r_squared": round(r_squared, 4),
                "max_n_events": max(xs),
                "max_verify_ms": max(ys),
                "memory_threshold_hit_at": memory_threshold_hit["n_events"] if memory_threshold_hit else None,
            },
            raw_data=raw_data,
        )

    def _build_chain(self, n: int) -> EventChain:
        chain = EventChain(concept_id=f"stress-{n}")
        for i in range(n):
            chain.append(
                Event(
                    concept_id=chain.concept_id,
                    event_type=EventType.REGISTER if i == 0 else EventType.EVIDENCE,
                    actor="agent_stress",
                    reasoning=f"event {i}",
                    payload={"seq": i, "data": "x" * 100},  # 100-byte payload
                )
            )
        return chain
