"""ADL Lite — Cold Storage for EventChain archival.

Migrates historical events to a JSONL archive while preserving genesis and the last N hot
events. Archive files are SHA-256 hashed; the hash is stored in the chain's ARCHIVE event.

Standard-library only: json, hashlib, pathlib.
"""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Any

from .models import Event, EventChain, EventType

# Scale extras are imported lazily so that base tests never depend on them.
_SCALE_INSTALL_HINT = "Install the scale extras: pip install 'adl-lite[scale]'"


class ColdStorage:
    """Manages JSONL and compressed (zstd+msgpack) cold-storage archives."""

    JSONL_SUFFIX = ".archive.jsonl"
    COMPRESSED_SUFFIX = ".archive.msgpack.zst"

    def __init__(self, base_dir: Path | str = Path(".adl/archives")) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _archive_path(self, concept_id: str, compressed: bool = False) -> Path:
        suffix = self.COMPRESSED_SUFFIX if compressed else self.JSONL_SUFFIX
        return self.base_dir / f"{concept_id}{suffix}"

    @staticmethod
    def _ensure_scale_libs() -> tuple[Any, Any]:
        """Return (zstandard, msgpack) or raise a clear ImportError."""
        try:
            import msgpack
            import zstandard

            return zstandard, msgpack
        except ImportError as exc:
            raise ImportError(
                f"Compressed cold storage requires zstandard and msgpack. {_SCALE_INSTALL_HINT}"
            ) from exc

    @staticmethod
    def _hash_file(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def verify_archive(archive_pointer: str, archive_file: str | Path) -> bool:
        """Recompute SHA-256 of *archive_file* and compare with *archive_pointer*."""
        path = Path(archive_file)
        if not path.exists():
            return False
        expected = archive_pointer
        if expected.startswith("sha256:"):
            expected = expected[7:]
        return expected == ColdStorage._hash_file(path)

    def _event_to_dict(self, event: Event) -> dict[str, Any]:
        return {
            "event_id": event.event_id,
            "concept_id": event.concept_id,
            "event_type": event.event_type.value,
            "actor": event.actor,
            "reasoning": event.reasoning,
            "timestamp": event.timestamp,
            "payload": event.payload,
            "previous_event_id": event.previous_event_id,
            "hash": event.hash,
            "_prev_hash": event._prev_hash,
        }

    @staticmethod
    def _event_from_dict(data: dict[str, Any]) -> Event:
        e = Event(
            event_id=data["event_id"],
            concept_id=data["concept_id"],
            event_type=EventType(data["event_type"]),
            actor=data["actor"],
            reasoning=data["reasoning"],
            timestamp=data["timestamp"],
            payload=data["payload"],
            previous_event_id=data["previous_event_id"],
            hash=data["hash"],
        )
        e._prev_hash = data.get("_prev_hash", "")
        return e

    def _write_jsonl(self, path: Path, events: list[Event]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for e in events:
                f.write(json.dumps(self._event_to_dict(e), sort_keys=True, default=str) + "\n")

    def _write_compressed(self, path: Path, events: list[Event]) -> None:
        """Write events as a zstd-compressed stream of msgpack objects."""
        zstandard, msgpack = self._ensure_scale_libs()
        buf = io.BytesIO()
        for e in events:
            buf.write(msgpack.packb(self._event_to_dict(e), use_bin_type=True, default=str))
        compressed = zstandard.ZstdCompressor().compress(buf.getvalue())
        path.write_bytes(compressed)

    def archive(
        self,
        chain: EventChain,
        keep_last_n: int = 10,
        compressed: bool = False,
    ) -> Event | None:
        """Migrate events to cold storage, trim the hot chain, and append an ARCHIVE event.

        Args:
            chain: The EventChain to archive.
            keep_last_n: Number of recent events to retain in the hot chain.
            compressed: If True, write a zstd+msgpack archive; otherwise JSONL.
        """
        events = chain.events
        total = len(events)
        archive_path = self._archive_path(chain.concept_id, compressed=compressed)

        if total <= keep_last_n + 1:
            archive_event = Event(
                concept_id=chain.concept_id,
                event_type=EventType.ARCHIVE,
                actor="system",
                reasoning="Cold storage migration — nothing to archive",
                payload={
                    "archive_pointer": "",
                    "archive_file": str(archive_path),
                    "archived_count": 0,
                    "compressed": compressed,
                },
            )
            with chain._events_lock:
                if chain._events:
                    last = chain._events[-1]
                    archive_event.previous_event_id = last.event_id
                    archive_event._prev_hash = last.hash
                    archive_event.hash = ""
                    archive_event.model_post_init(None)
                chain._events.append(archive_event)
                chain._invalidate_caches()
            return archive_event

        if keep_last_n == 0:
            archived_events = events[1:]
            keep_events = [events[0]]
        else:
            archived_events = events[1:-keep_last_n]
            keep_events = [events[0]] + events[-keep_last_n:]

        if compressed:
            self._write_compressed(archive_path, archived_events)
        else:
            self._write_jsonl(archive_path, archived_events)

        file_hash = self._hash_file(archive_path)
        archive_pointer = f"sha256:{file_hash}"

        with chain._events_lock:
            chain._events = list(keep_events)
            archive_event = Event(
                concept_id=chain.concept_id,
                event_type=EventType.ARCHIVE,
                actor="system",
                reasoning="Cold storage migration",
                payload={
                    "archive_pointer": archive_pointer,
                    "archive_file": str(archive_path),
                    "archived_count": len(archived_events),
                    "compressed": compressed,
                },
            )
            if chain._events:
                last = chain._events[-1]
                archive_event.previous_event_id = last.event_id
                archive_event._prev_hash = last.hash
                archive_event.hash = ""
                archive_event.model_post_init(None)
            chain._events.append(archive_event)
            chain._invalidate_caches()

        return archive_event

    def unarchive(self, concept_id: str) -> list[Event]:
        """Read the archive for *concept_id* and reconstruct Event objects."""
        compressed_path = self._archive_path(concept_id, compressed=True)
        if compressed_path.exists():
            return self._read_events(compressed_path)
        jsonl_path = self._archive_path(concept_id, compressed=False)
        if not jsonl_path.exists():
            raise FileNotFoundError(f"Archive not found: {jsonl_path}")
        return self._read_events(jsonl_path)

    @classmethod
    def _read_events(cls, path: Path) -> list[Event]:
        if path.name.endswith(cls.COMPRESSED_SUFFIX):
            return cls._read_events_compressed(path)

        events: list[Event] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                events.append(cls._event_from_dict(data))
        return events

    @classmethod
    def _read_events_compressed(cls, path: Path) -> list[Event]:
        """Stream-decompress a zstd+msgpack archive into Event objects."""
        zstandard, msgpack = cls._ensure_scale_libs()
        events: list[Event] = []
        with open(path, "rb") as f:
            decompressor = zstandard.ZstdDecompressor()
            with decompressor.stream_reader(f) as reader:
                unpacker = msgpack.Unpacker(reader, raw=False)
                for obj in unpacker:
                    events.append(cls._event_from_dict(obj))
        return events
