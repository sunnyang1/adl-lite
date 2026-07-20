"""Tests for tenant isolation in WarmIndex / ADLMemory (logical isolation)."""

from __future__ import annotations

import sqlite3

from adl_lite.memory import ADLMemory, HotIndex, WarmIndex
from adl_lite.models import (
    ADLDocument,
    ADLFrontMatter,
    ADLType,
    ConceptSkeleton,
    DiscoveryStatus,
)
from adl_lite.tenant import _safe_tenant_id


def _make_doc(adl_id: str, tenant_id: str | None = None) -> ADLDocument:
    doc = ADLDocument(
        front_matter=ADLFrontMatter(
            adl_type=ADLType.CONCEPT,
            adl_id=adl_id,
            scope="public",
            domain="test",
            status=DiscoveryStatus.PROVISIONAL,
        )
    )
    if tenant_id is not None:
        object.__setattr__(doc, "_tenant_id", tenant_id)
    return doc


def test_warm_index_has_tenant_id_column() -> None:
    warm = WarmIndex(":memory:")
    cols = [r["name"] for r in warm.conn.execute("PRAGMA table_info(documents)").fetchall()]
    assert "tenant_id" in cols
    cols_e = [r["name"] for r in warm.conn.execute("PRAGMA table_info(events)").fetchall()]
    assert "tenant_id" in cols_e
    # Tenant indexes exist.
    idx = warm.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_doc_tenant'"
    ).fetchone()
    assert idx is not None
    idx2 = warm.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_events_tenant'"
    ).fetchone()
    assert idx2 is not None
    idx3 = warm.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_doc_tenant_status'"
    ).fetchone()
    assert idx3 is not None


def test_warm_index_migrates_existing_db(tmp_path) -> None:
    # An old-style db (no tenant_id column) must be migrated on open.
    db = str(tmp_path / "old.db")
    conn = sqlite3.connect(db)
    # Realistic legacy schema: full pre-tenant column set (minus tenant_id),
    # so WarmIndex.SCHEMA's indexes succeed and _ensure_column migrates it.
    conn.execute(
        """
        CREATE TABLE documents (
            adl_id TEXT PRIMARY KEY,
            adl_type TEXT NOT NULL,
            status TEXT NOT NULL,
            scope TEXT NOT NULL,
            domain TEXT,
            confidence REAL,
            novelty REAL,
            created_at TEXT,
            updated_at TEXT,
            raw_json TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE events (
            event_id TEXT PRIMARY KEY,
            concept_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            actor TEXT,
            reasoning TEXT,
            timestamp TEXT,
            previous_event_id TEXT,
            prev_hash TEXT,
            hash TEXT,
            payload_json TEXT,
            synthetic INTEGER
        )
        """
    )
    conn.commit()
    conn.close()
    warm = WarmIndex(db)
    cols = [r["name"] for r in warm.conn.execute("PRAGMA table_info(documents)").fetchall()]
    assert "tenant_id" in cols
    cols_e = [r["name"] for r in warm.conn.execute("PRAGMA table_info(events)").fetchall()]
    assert "tenant_id" in cols_e


def test_same_tenant_read_write() -> None:
    warm = WarmIndex(":memory:", tenant_id="acme")
    warm.insert_document(_make_doc("cap-1"), tenant_id="acme")
    got = warm.get_document("cap-1")
    assert got is not None
    assert got.adl_id == "cap-1"


def test_cross_tenant_filter_isolation() -> None:
    warm = WarmIndex(":memory:")
    warm.insert_document(_make_doc("acme-1"), tenant_id="acme")
    warm.insert_document(_make_doc("beta-1"), tenant_id="beta")
    # Without a tenant filter, both docs are visible.
    all_ids = warm.cascade_filter()
    assert set(all_ids) == {"acme-1", "beta-1"}
    # With a tenant filter, only that tenant's docs are returned.
    assert warm.cascade_filter(tenant_id="acme") == ["acme-1"]
    assert warm.cascade_filter(tenant_id="beta") == ["beta-1"]


def test_delete_respects_tenant() -> None:
    warm = WarmIndex(":memory:", tenant_id="acme")
    warm.insert_document(_make_doc("acme-1"), tenant_id="acme")
    warm.insert_document(_make_doc("acme-2"), tenant_id="acme")
    warm.delete_document("acme-1", tenant_id="acme")
    remaining = warm.cascade_filter(tenant_id="acme")
    assert remaining == ["acme-2"]


def test_adlmemory_tenant_filter() -> None:
    mem = ADLMemory(":memory:", tenant_id="acme")
    mem.store(_make_doc("acme-1", tenant_id="acme"))
    mem.store(_make_doc("acme-2", tenant_id="acme"))
    results = mem.prefilter(tenant_id="acme")
    assert {s.adl_id for s in results} == {"acme-1", "acme-2"}


def test_hot_index_filter_tenant() -> None:
    hot = HotIndex()
    s1 = ConceptSkeleton(
        adl_id="a",
        semantic_type=ADLType.CONCEPT,
        domain_tag="",
        status=DiscoveryStatus.PROVISIONAL,
        scope="public",
        tenant_id="acme",
    )
    s2 = ConceptSkeleton(
        adl_id="b",
        semantic_type=ADLType.CONCEPT,
        domain_tag="",
        status=DiscoveryStatus.PROVISIONAL,
        scope="public",
        tenant_id="beta",
    )
    hot.put(s1)
    hot.put(s2)
    assert [s.adl_id for s in hot.filter(tenant_id="acme")] == ["a"]
    assert [s.adl_id for s in hot.filter(tenant_id="beta")] == ["b"]
    assert {s.adl_id for s in hot.filter()} == {"a", "b"}


def test_safe_tenant_id() -> None:
    assert _safe_tenant_id("acme") == "acme"
    assert _safe_tenant_id("a/b\\c") == "a_b_c"
    assert _safe_tenant_id("key@x!") == "key_x_"
    assert _safe_tenant_id("") == "default"
