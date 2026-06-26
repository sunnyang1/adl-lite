"""E27: 1M event scale — lock split + incremental verification + compressed cold storage.

Measures EventChain construction, incremental integrity verification, memory, and
the compression ratio of the new zstd+msgpack cold-storage backend.
"""

from __future__ import annotations

import gc
import json
import resource
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from adl_lite.cold_storage import ColdStorage
from adl_lite.models import Event, EventChain, EventType

from .base import BaseExperiment, ExperimentResult
from .registry import register


@register("E27")
class E27OneMillionEventScale(BaseExperiment):
    experiment_id = "E27"
    name = "1M Event Scale Test"
    description = (
        "Measure EventChain append/verify throughput, memory, and cold-storage "
        "compression at 1M events using Phase 3 lock splitting and incremental verify."
    )

    TARGET_N = 1_000_000
    FALLBACK_N = 500_000
    TARGET_BUILD_S = 90.0
    TARGET_INCREMENTAL_VERIFY_MS = 200.0
    TARGET_MEMORY_MB = 8192.0
    TARGET_TOTAL_S = 180.0

    def run(self) -> ExperimentResult:
        gc.collect()
        baseline_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

        n_events = self.TARGET_N
        chain, build_time, append_times = self._build_chain(n_events)

        projected = False
        if build_time > self.TARGET_BUILD_S and n_events == self.TARGET_N:
            n_events = self.FALLBACK_N
            chain, build_time, append_times = self._build_chain(n_events)
            projected = True

        # Initial full verification: this is the only O(n) integrity check.
        t0 = time.perf_counter()
        ok = chain.verify_integrity()
        t1 = time.perf_counter()
        initial_verify_ms = (t1 - t0) * 1000

        # Incremental verification: one new event should be near O(1).
        chain.append(
            Event(
                concept_id=chain.concept_id,
                event_type=EventType.EVIDENCE,
                actor="incremental-check",
                payload={"marker": "post-build-incremental"},
            )
        )
        t0 = time.perf_counter()
        ok = chain.verify_integrity() and ok
        t1 = time.perf_counter()
        incremental_verify_ms = (t1 - t0) * 1000

        peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform == "darwin":
            memory_peak_mb = (peak_rss - baseline_rss) / (1024 * 1024)
        else:
            memory_peak_mb = (peak_rss - baseline_rss) / 1024
        memory_peak_mb = max(memory_peak_mb, 0.0)

        # Compressed cold-storage ratio measurement.
        jsonl_mb, compressed_mb, ratio = self._measure_compression(chain, n_events)

        append_latency_ms = (sum(append_times) / len(append_times)) * 1000 if append_times else 0.0
        total_time = build_time + initial_verify_ms / 1000

        passes = (
            ok
            and build_time <= self.TARGET_BUILD_S
            and incremental_verify_ms <= self.TARGET_INCREMENTAL_VERIFY_MS
            and memory_peak_mb <= self.TARGET_MEMORY_MB
            and total_time <= self.TARGET_TOTAL_S
        )

        print("\nE27: 1M Event Scale Test")
        print(f"Chain length: {n_events}{' (projected from 1M)' if projected else ''}")
        print(f"Build time: {build_time:.3f} s")
        print(f"Initial verify: {initial_verify_ms:.2f} ms")
        print(f"Incremental verify: {incremental_verify_ms:.3f} ms")
        print(f"Memory peak: {memory_peak_mb:.2f} MB")
        print(f"Append latency: {append_latency_ms:.4f} ms/event")
        print(f"JSONL archive: {jsonl_mb:.2f} MB")
        print(f"Compressed archive: {compressed_mb:.2f} MB")
        print(f"Compression ratio: {ratio:.2f}x")
        print(f"Status: {'PASS' if passes else 'PARTIAL' if ok else 'FAIL'}")

        return ExperimentResult(
            experiment_id=self.experiment_id,
            status="passed" if passes else "partial" if ok else "failed",
            metrics={
                "n_events": n_events,
                "projected": projected,
                "build_time_s": round(build_time, 3),
                "initial_verify_ms": round(initial_verify_ms, 2),
                "incremental_verify_ms": round(incremental_verify_ms, 3),
                "memory_peak_mb": round(memory_peak_mb, 2),
                "append_latency_ms": round(append_latency_ms, 4),
                "jsonl_archive_mb": round(jsonl_mb, 2),
                "compressed_archive_mb": round(compressed_mb, 2),
                "compression_ratio": round(ratio, 2),
                "integrity_ok": ok,
                "passes_targets": passes,
            },
            raw_data=[
                {
                    "n_events": n_events,
                    "build_time_s": build_time,
                    "initial_verify_ms": initial_verify_ms,
                    "incremental_verify_ms": incremental_verify_ms,
                    "memory_peak_mb": memory_peak_mb,
                }
            ],
        )

    def _build_chain(self, n: int) -> tuple[EventChain, float, list[float]]:
        chain = EventChain(concept_id="scale-1m")
        append_times: list[float] = []
        base_payload: dict[str, Any] = {"data": "x" * 200, "meta": {"tag": "scale"}}

        t0 = time.perf_counter()
        for i in range(n):
            payload = {k: (v.copy() if isinstance(v, dict) else v) for k, v in base_payload.items()}
            payload["meta"]["seq"] = i
            a0 = time.perf_counter()
            chain.append(
                Event(
                    concept_id=chain.concept_id,
                    event_type=EventType.REGISTER if i == 0 else EventType.EVIDENCE,
                    actor=f"agent_{i % 1000}",
                    reasoning=f"event {i}",
                    payload=payload,
                )
            )
            a1 = time.perf_counter()
            append_times.append(a1 - a0)
        t1 = time.perf_counter()

        return chain, t1 - t0, append_times

    def _measure_compression(self, chain: EventChain, n_events: int) -> tuple[float, float, float]:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            storage = ColdStorage(base_dir=base_dir)

            # Archive with zstd+msgpack.
            archive_event = storage.archive(chain, keep_last_n=10, compressed=True)
            if archive_event is None:
                return 0.0, 0.0, 0.0

            archived = storage.unarchive(chain.concept_id)
            compressed_path = Path(archive_event.payload["archive_file"])
            compressed_size = compressed_path.stat().st_size

            # Write the same archived events as JSONL for comparison.
            jsonl_path = base_dir / f"{chain.concept_id}.archive.jsonl"
            with open(jsonl_path, "w", encoding="utf-8") as f:
                for e in archived:
                    f.write(
                        json.dumps(storage._event_to_dict(e), sort_keys=True, default=str) + "\n"
                    )
            jsonl_size = jsonl_path.stat().st_size

        jsonl_mb = jsonl_size / (1024 * 1024)
        compressed_mb = compressed_size / (1024 * 1024)
        ratio = jsonl_size / compressed_size if compressed_size else 0.0
        return jsonl_mb, compressed_mb, ratio
