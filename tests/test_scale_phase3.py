"""Phase 3 scale tests: split locks, incremental verify, compressed cold storage, cold tier."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from adl_lite.cold_storage import ColdStorage
from adl_lite.memory import ADLMemory
from adl_lite.models import (
    ActionExecStatus,
    ADLActionBlock,
    ADLDocument,
    ADLFrontMatter,
    ADLType,
    DiscoveryStatus,
    Event,
    EventChain,
    EventType,
)


def _build_chain(concept_id: str, n_events: int) -> EventChain:
    chain = EventChain(concept_id=concept_id)
    chain.append(
        Event(
            concept_id=concept_id,
            event_type=EventType.REGISTER,
            actor="system",
            payload={"seq": 0},
        )
    )
    for i in range(1, n_events):
        chain.append(
            Event(
                concept_id=concept_id,
                event_type=EventType.EVIDENCE,
                actor=f"agent_{i % 100}",
                payload={"seq": i},
            )
        )
    return chain


class TestLockSplitting:
    def test_split_locks_exist(self):
        chain = EventChain(concept_id="lock-test")
        assert hasattr(chain, "_events_lock")
        assert hasattr(chain, "_cache_lock")
        assert chain._events_lock.acquire()
        chain._events_lock.release()

    def test_concurrent_appends_remain_consistent(self):
        chain = EventChain(concept_id="contention-test")
        chain.append(
            Event(concept_id="contention-test", event_type=EventType.REGISTER, actor="system")
        )

        def worker(agent_id: int) -> None:
            for i in range(50):
                chain.append(
                    Event(
                        concept_id="contention-test",
                        event_type=EventType.EVIDENCE,
                        actor=f"agent-{agent_id}",
                        payload={"i": i},
                    )
                )

        with ThreadPoolExecutor(max_workers=20) as executor:
            list(executor.map(worker, range(20)))

        assert len(chain) == 1 + 20 * 50
        assert chain.verify_integrity()

    def test_status_and_confidence_under_contention(self):
        chain = EventChain(concept_id="status-contention")
        chain.append(
            Event(concept_id="status-contention", event_type=EventType.REGISTER, actor="system")
        )

        def validator(agent_id: int) -> None:
            chain.append(
                Event(
                    concept_id="status-contention",
                    event_type=EventType.VALIDATE,
                    actor=f"validator-{agent_id}",
                    payload={"confidence": 0.8},
                )
            )

        with ThreadPoolExecutor(max_workers=10) as executor:
            list(executor.map(validator, range(10)))

        assert chain.status == DiscoveryStatus.VALIDATED
        assert chain.confidence == pytest.approx(0.8)
        assert len(chain.validators) == 10


class TestIncrementalVerify:
    def test_incremental_verify_is_faster_than_initial(self):
        chain = _build_chain("incremental", 5_000)

        t0 = time.perf_counter()
        assert chain.verify_integrity()
        t1 = time.perf_counter()
        initial_ms = (t1 - t0) * 1000

        chain.append(
            Event(
                concept_id="incremental",
                event_type=EventType.EVIDENCE,
                actor="check",
                payload={"marker": True},
            )
        )
        t0 = time.perf_counter()
        assert chain.verify_integrity()
        t1 = time.perf_counter()
        incremental_ms = (t1 - t0) * 1000

        assert incremental_ms < initial_ms / 5
        assert incremental_ms < 5.0

    def test_external_deletion_invalidates_cache(self):
        chain = _build_chain("delete-invalidate", 20)
        assert chain.verify_integrity()
        del chain._events[5]
        assert not chain.verify_integrity()


class TestCompressedColdStorage:
    def test_compressed_archive_roundtrip(self, tmp_path: Path):
        chain = _build_chain("disc-compressed", 50)
        storage = ColdStorage(base_dir=tmp_path / "archives")
        archive_event = storage.archive(chain, keep_last_n=10, compressed=True)

        assert archive_event is not None
        assert archive_event.payload.get("compressed") is True
        assert len(chain) == 12

        archived = storage.unarchive("disc-compressed")
        assert len(archived) == 39

        # Reconstruct original order and verify.
        reconstructed = [chain.events[0]] + archived + list(chain.events[1:-1])
        assert len(reconstructed) == 50
        rebuilt = EventChain(concept_id="disc-compressed")
        for e in reconstructed:
            rebuilt.append(e)
        assert rebuilt.verify_integrity()

    def test_verify_archive_compressed(self, tmp_path: Path):
        chain = _build_chain("disc-compressed2", 50)
        storage = ColdStorage(base_dir=tmp_path / "archives")
        storage.archive(chain, keep_last_n=10, compressed=True)
        pointer = chain.events[-1].payload["archive_pointer"]
        archive_file = chain.events[-1].payload["archive_file"]
        assert ColdStorage.verify_archive(pointer, archive_file)

    def test_compressed_smaller_than_jsonl(self, tmp_path: Path):
        chain = _build_chain("disc-compressed3", 200)
        storage = ColdStorage(base_dir=tmp_path / "archives")
        storage.archive(chain, keep_last_n=10, compressed=True)
        compressed_path = Path(chain.events[-1].payload["archive_file"])
        jsonl_path = tmp_path / "archives" / "disc-compressed3.archive.jsonl"

        # Build an equivalent JSONL archive for size comparison.
        archived = storage.unarchive("disc-compressed3")
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for e in archived:
                f.write(json.dumps(storage._event_to_dict(e), sort_keys=True, default=str) + "\n")

        assert compressed_path.stat().st_size < jsonl_path.stat().st_size


class TestADLMemoryColdTier:
    def test_auto_archive_and_retrieve_full_chain(self, tmp_path: Path):
        fm = ADLFrontMatter(
            adl_type=ADLType.CONCEPT,
            adl_id="cold-tier-test",
            status=DiscoveryStatus.PROVISIONAL,
            confidence=0.0,
            scope="public",
        )
        actions = [
            ADLActionBlock(
                action="announce",
                actor=f"agent-{i}",
                params={"seq": i},
                exec_status=ActionExecStatus.EXECUTED,
            )
            for i in range(30)
        ]
        doc = ADLDocument(front_matter=fm, action_blocks=actions)
        original_length = len(doc.event_chain)
        assert original_length > 10

        mem = ADLMemory(
            db_path=str(tmp_path / "mem.db"),
            cold_threshold=10,
            cold_base_dir=tmp_path / "cold",
        )
        mem.store_with_events(doc)

        # Either compressed or JSONL archive should exist.
        archive_files = list((tmp_path / "cold").glob("cold-tier-test.archive.*"))
        assert archive_files

        full_chain = mem.retrieve_chain("cold-tier-test")
        assert full_chain is not None
        # Archive appends an ARCHIVE event, so the reconstructed chain is one
        # event longer than the original in-memory chain.
        assert len(full_chain) == original_length + 1
        assert full_chain.verify_integrity()
        mem.close()


class TestScaleExperiments:
    def test_e27_runs_with_small_target(self, monkeypatch: pytest.MonkeyPatch):
        import experiments.e27_1m_event_scale as e27

        monkeypatch.setattr(e27.E27OneMillionEventScale, "TARGET_N", 2_000)
        monkeypatch.setattr(e27.E27OneMillionEventScale, "FALLBACK_N", 1_000)
        result = e27.E27OneMillionEventScale()._run_wrapper()
        assert result.status in ("passed", "partial")
        assert result.metrics["integrity_ok"] is True

    def test_e28_runs_with_small_target(self, monkeypatch: pytest.MonkeyPatch):
        import experiments.e28_10k_concurrency as e28

        monkeypatch.setattr(e28.E28TenKConcurrency, "N_AGENTS", 100)
        monkeypatch.setattr(e28.E28TenKConcurrency, "N_CHAINS", 10)
        monkeypatch.setattr(e28.E28TenKConcurrency, "EVENTS_PER_AGENT", 5)
        monkeypatch.setattr(e28.E28TenKConcurrency, "MAX_WORKERS", 20)
        result = e28.E28TenKConcurrency()._run_wrapper()
        assert result.status in ("passed", "partial")
        assert result.metrics["integrity_rate"] == 1.0
