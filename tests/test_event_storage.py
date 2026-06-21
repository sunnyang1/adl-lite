"""
Tests for event storage — append-only audit log in WarmIndex.

Verifies that EventChain history is persisted, recoverable, and
integrity-checkable after round-tripping through SQLite.
"""

from __future__ import annotations

from pathlib import Path

from adl_lite.memory import ADLMemory, WarmIndex
from adl_lite.models import ADLDocument, Event, EventType
from adl_lite.parser import parse_text

CAPITAL_MD = """\
---
adl_type: discovery
adl_id: disc-capital-trap
status: provisional
confidence: 0.5
scope: public
domain: financial_aml
---

# Capital Reflux Trap

```adl:relation
source: disc-capital-trap
predicate: related-to
target: disc-velocity-crisis
weight: 0.9
```
"""


def _make_doc() -> ADLDocument:
    return parse_text(CAPITAL_MD)


# ---------------------------------------------------------------------------
# WarmIndex event storage
# ---------------------------------------------------------------------------


class TestWarmIndexEventStorage:
    def test_store_and_load_event_chain(self, tmp_path: Path):
        db = tmp_path / "warm.db"
        warm = WarmIndex(str(db))
        doc = _make_doc()
        chain = doc.event_chain

        warm.insert_document(doc)
        warm._store_events(chain)

        restored = warm.load_event_chain("disc-capital-trap")
        assert restored is not None
        assert restored.concept_id == "disc-capital-trap"
        assert len(restored) == len(chain)
        assert restored.verify_integrity()

    def test_history_returns_dicts(self, tmp_path: Path):
        db = tmp_path / "warm.db"
        warm = WarmIndex(str(db))
        doc = _make_doc()
        warm.insert_document(doc)
        warm._store_events(doc.event_chain)

        hist = warm.get_history("disc-capital-trap")
        assert isinstance(hist, list)
        assert len(hist) >= 1
        assert all("event_id" in e for e in hist)
        assert all("hash" in e for e in hist)

    def test_delete_removes_events(self, tmp_path: Path):
        db = tmp_path / "warm.db"
        warm = WarmIndex(str(db))
        doc = _make_doc()
        warm.insert_document(doc)
        warm._store_events(doc.event_chain)

        warm.delete_document("disc-capital-trap")
        assert warm.load_event_chain("disc-capital-trap") is None
        assert warm.get_history("disc-capital-trap") == []

    def test_version_at_cutoff(self, tmp_path: Path):
        db = tmp_path / "warm.db"
        warm = WarmIndex(str(db))
        doc = _make_doc()
        warm.insert_document(doc)
        warm._store_events(doc.event_chain)

        # Use a far-future timestamp → should include all events
        version = warm.get_version_at("disc-capital-trap", "2099-12-31T23:59:59+00:00")
        assert version is not None
        assert version.adl_id == "disc-capital-trap"

        # Use a far-past timestamp → should return None (no events before)
        old = warm.get_version_at("disc-capital-trap", "1970-01-01T00:00:00+00:00")
        assert old is None

    def test_load_event_chain_missing_concept(self, tmp_path: Path):
        db = tmp_path / "warm.db"
        warm = WarmIndex(str(db))
        assert warm.load_event_chain("nonexistent") is None


# ---------------------------------------------------------------------------
# ADLMemory unified API
# ---------------------------------------------------------------------------


class TestADLMemoryEventStorage:
    def test_store_with_events_and_retrieve_chain(self, tmp_path: Path):
        db = tmp_path / "mem.db"
        mem = ADLMemory(str(db))
        doc = _make_doc()
        mem.store_with_events(doc)

        chain = mem.retrieve_chain("disc-capital-trap")
        assert chain is not None
        assert chain.concept_id == "disc-capital-trap"
        assert chain.verify_integrity()

    def test_history_via_memory(self, tmp_path: Path):
        db = tmp_path / "mem.db"
        mem = ADLMemory(str(db))
        doc = _make_doc()
        mem.store_with_events(doc)

        hist = mem.history("disc-capital-trap")
        assert len(hist) >= 1
        assert any(e["event_type"] == "snapshot" for e in hist)

    def test_version_at_via_memory(self, tmp_path: Path):
        db = tmp_path / "mem.db"
        mem = ADLMemory(str(db))
        doc = _make_doc()
        mem.store_with_events(doc)

        version = mem.version_at("disc-capital-trap", "2099-12-31T23:59:59+00:00")
        assert version is not None
        assert version.front_matter.adl_id == "disc-capital-trap"

    def test_delete_cleans_events(self, tmp_path: Path):
        db = tmp_path / "mem.db"
        mem = ADLMemory(str(db))
        doc = _make_doc()
        mem.store_with_events(doc)
        mem.delete("disc-capital-trap")

        assert mem.retrieve_chain("disc-capital-trap") is None
        assert mem.history("disc-capital-trap") == []

    def test_multiple_events_integrity(self, tmp_path: Path):
        db = tmp_path / "mem.db"
        mem = ADLMemory(str(db))
        doc = _make_doc()
        mem.store_with_events(doc)

        # Append a synthetic transition event
        chain = mem.retrieve_chain("disc-capital-trap")
        assert chain is not None
        chain.append(
            Event(
                concept_id="disc-capital-trap",
                event_type=EventType.VALIDATE,
                actor="agent_reviewer",
                reasoning="approved",
                payload={"confidence": 0.95},
            )
        )
        mem.warm._store_events(chain)

        restored = mem.retrieve_chain("disc-capital-trap")
        assert restored is not None
        assert len(restored) == len(chain)
        assert restored.verify_integrity()
        assert restored.status.value == "validated"
