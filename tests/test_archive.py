"""Tests for ADL Lite cold storage (ARCHIVE event type)."""

from __future__ import annotations

from pathlib import Path

import pytest

from adl_lite.cold_storage import ColdStorage
from adl_lite.models import Event, EventChain, EventType


def _build_chain(concept_id: str, n_events: int) -> EventChain:
    """Build a chain with a genesis REGISTER event and n_events-1 VALIDATE events."""
    chain = EventChain(concept_id=concept_id)
    chain.append(
        Event(
            concept_id=concept_id,
            event_type=EventType.REGISTER,
            actor="system",
            reasoning="Genesis",
            payload={"seq": 0},
        )
    )
    for i in range(1, n_events):
        chain.append(
            Event(
                concept_id=concept_id,
                event_type=EventType.VALIDATE,
                actor="agent",
                reasoning=f"Event {i}",
                payload={"seq": i},
            )
        )
    return chain


class TestColdStorageArchive:
    def test_verify_archive_missing_file(self) -> None:
        assert ColdStorage.verify_archive("sha256:abc", "/nonexistent/file.jsonl") is False

    def test_unarchive_ignores_blank_lines(self, tmp_path: Path) -> None:
        chain = _build_chain("disc-blank", 15)
        storage = ColdStorage(base_dir=tmp_path / "archives")
        storage.archive(chain, keep_last_n=10)
        archive_path = Path(chain.events[-1].payload["archive_file"])
        content = archive_path.read_text()
        archive_path.write_text("\n\n" + content + "\n\n")
        unarchived = storage.unarchive("disc-blank")
        assert len(unarchived) == 4  # 15 - genesis - 10 kept = 4 archived

    def test_archive_migrates_events(self, tmp_path: Path) -> None:
        chain = _build_chain("disc-test", 50)
        storage = ColdStorage(base_dir=tmp_path / "archives")
        archive_event = storage.archive(chain, keep_last_n=10)
        assert archive_event is not None
        assert archive_event.event_type == EventType.ARCHIVE
        assert archive_event.payload["archived_count"] == 39
        assert len(chain) == 12  # genesis + 10 + ARCHIVE
        archive_file = Path(archive_event.payload["archive_file"])
        assert archive_file.exists()

    def test_unarchive_reconstructs_events(self, tmp_path: Path) -> None:
        chain = _build_chain("disc-test", 50)
        original_events = chain.events
        storage = ColdStorage(base_dir=tmp_path / "archives")
        storage.archive(chain, keep_last_n=10)
        unarchived = storage.unarchive("disc-test")
        assert len(unarchived) == 39
        for i, ue in enumerate(unarchived):
            orig = original_events[i + 1]
            assert ue.event_id == orig.event_id
            assert ue.event_type == orig.event_type
            assert ue.actor == orig.actor
            assert ue.reasoning == orig.reasoning
            assert ue.timestamp == orig.timestamp
            assert ue.payload == orig.payload
            assert ue.previous_event_id == orig.previous_event_id
            assert ue.hash == orig.hash
            assert ue._prev_hash == orig._prev_hash

    def test_verify_integrity_full_passes(self, tmp_path: Path) -> None:
        chain = _build_chain("disc-test", 50)
        storage = ColdStorage(base_dir=tmp_path / "archives")
        storage.archive(chain, keep_last_n=10)
        assert chain.verify_integrity(full=True) is True

    def test_corrupt_archive_breaks_verification(self, tmp_path: Path) -> None:
        chain = _build_chain("disc-test", 50)
        storage = ColdStorage(base_dir=tmp_path / "archives")
        storage.archive(chain, keep_last_n=10)
        archive_file = Path(chain.events[-1].payload["archive_file"])
        content = archive_file.read_text()
        corrupted = content.replace("agent", "hacker")
        archive_file.write_text(corrupted)
        assert chain.verify_integrity(full=True) is False

    def test_verify_integrity_without_full_skips_archive(self, tmp_path: Path) -> None:
        chain = _build_chain("disc-test", 50)
        storage = ColdStorage(base_dir=tmp_path / "archives")
        storage.archive(chain, keep_last_n=10)
        archive_file = Path(chain.events[-1].payload["archive_file"])
        content = archive_file.read_text()
        corrupted = content.replace("agent", "hacker")
        archive_file.write_text(corrupted)
        assert chain.verify_integrity() is True
        assert chain.verify_integrity(full=False) is True

    def test_archive_nothing_to_archive(self, tmp_path: Path) -> None:
        chain = _build_chain("disc-test", 5)
        storage = ColdStorage(base_dir=tmp_path / "archives")
        archive_event = storage.archive(chain, keep_last_n=10)
        assert archive_event.payload["archived_count"] == 0
        assert len(chain) == 6
        assert chain.verify_integrity(full=True) is True

    def test_verify_archive_static(self, tmp_path: Path) -> None:
        chain = _build_chain("disc-test", 50)
        storage = ColdStorage(base_dir=tmp_path / "archives")
        storage.archive(chain, keep_last_n=10)
        archive_file = chain.events[-1].payload["archive_file"]
        pointer = chain.events[-1].payload["archive_pointer"]
        assert ColdStorage.verify_archive(pointer, archive_file) is True
        assert ColdStorage.verify_archive("sha256:badhash", archive_file) is False

    def test_unarchive_file_not_found(self, tmp_path: Path) -> None:
        storage = ColdStorage(base_dir=tmp_path / "archives")
        with pytest.raises(FileNotFoundError):
            storage.unarchive("nonexistent")

    def test_event_chain_archive_wrapper(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        chain = _build_chain("disc-test", 50)
        archive_event = chain.archive(keep_last_n=10)
        assert archive_event is not None
        assert len(chain) == 12
        unarchived = chain.unarchive()
        assert len(unarchived) == 39

    def test_archive_subchain_integrity(self, tmp_path: Path) -> None:
        chain = _build_chain("disc-test", 50)
        storage = ColdStorage(base_dir=tmp_path / "archives")
        storage.archive(chain, keep_last_n=10)
        archived = storage.unarchive("disc-test")
        for i in range(1, len(archived)):
            assert archived[i].previous_event_id == archived[i - 1].event_id
        for i, ae in enumerate(archived):
            expected_prev = archived[i - 1].hash if i > 0 else chain.events[0].hash
            assert ae._prev_hash == expected_prev
            assert ae.hash == ae._compute_hash()

    def test_cross_link_integrity(self, tmp_path: Path) -> None:
        chain = _build_chain("disc-test", 50)
        storage = ColdStorage(base_dir=tmp_path / "archives")
        storage.archive(chain, keep_last_n=10)
        # The first hot event after genesis must link to the last archived event
        hot_next = chain.events[1]
        archived = storage.unarchive("disc-test")
        last_archived = archived[-1]
        assert hot_next.previous_event_id == last_archived.event_id
        assert hot_next._prev_hash == last_archived.hash

    def test_keep_last_n_zero(self, tmp_path: Path) -> None:
        chain = _build_chain("disc-test", 10)
        storage = ColdStorage(base_dir=tmp_path / "archives")
        storage.archive(chain, keep_last_n=0)
        assert len(chain) == 2  # genesis + ARCHIVE
        assert chain.verify_integrity(full=True) is True

    def test_multiple_archives(self, tmp_path: Path) -> None:
        chain = _build_chain("disc-test", 50)
        storage = ColdStorage(base_dir=tmp_path / "archives")
        storage.archive(chain, keep_last_n=10)
        # Append a few more events, then archive again
        for i in range(50, 55):
            chain.append(
                Event(
                    concept_id="disc-test",
                    event_type=EventType.VALIDATE,
                    actor="agent",
                    reasoning=f"Event {i}",
                    payload={"seq": i},
                )
            )
        storage.archive(chain, keep_last_n=2)
        # Should still verify
        assert chain.verify_integrity(full=True) is True
        # The first archive file should still be intact
        first_archive = Path(tmp_path / "archives" / "disc-test.archive.jsonl")
        assert first_archive.exists()

    def test_verify_integrity_gap_without_archive(self) -> None:
        chain = _build_chain("disc-test", 5)
        # Remove a middle event to create a gap without an ARCHIVE event
        del chain._events[2]
        assert chain.verify_integrity() is False

    def test_verify_integrity_cross_link_failure(self, tmp_path: Path) -> None:
        chain = _build_chain("disc-test", 50)
        storage = ColdStorage(base_dir=tmp_path / "archives")
        storage.archive(chain, keep_last_n=10)
        # Tamper with the first hot event after genesis so cross-link breaks
        chain._events[1]._prev_hash = "tampered"
        assert chain.verify_integrity(full=True) is False
