"""
Tests for adl_lite.memory — direct unit tests for HotIndex, WarmIndex, ADLMemory.

These tests improve coverage of the storage and graph-traversal layers.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from adl_lite.memory import ADLMemory, HotIndex, WarmIndex
from adl_lite.models import (
    ADLRelationBlock,
    ADLType,
    ConceptSkeleton,
    DiscoveryStatus,
)
from adl_lite.parser import parse_text

# ---------------------------------------------------------------------------
# HotIndex
# ---------------------------------------------------------------------------


class TestHotIndex:
    def test_put_get_remove(self):
        idx = HotIndex()
        sk = ConceptSkeleton(
            adl_id="test-1",
            semantic_type=ADLType.CONCEPT,
            domain_tag="test",
            status=DiscoveryStatus.PROVISIONAL,
            scope="public",
        )
        idx.put(sk)
        assert idx.get("test-1") == sk
        idx.remove("test-1")
        assert idx.get("test-1") is None

    def test_keys_and_len(self):
        idx = HotIndex()
        assert len(idx) == 0
        idx.put(ConceptSkeleton(adl_id="a", semantic_type=ADLType.CONCEPT, domain_tag="test", status=DiscoveryStatus.PROVISIONAL, scope="public"))
        idx.put(ConceptSkeleton(adl_id="b", semantic_type=ADLType.CONCEPT, domain_tag="test", status=DiscoveryStatus.VALIDATED, scope="public"))
        assert len(idx) == 2
        assert idx.keys() == {"a", "b"}

    def test_filter_by_status(self):
        idx = HotIndex()
        idx.put(ConceptSkeleton(adl_id="a", semantic_type=ADLType.CONCEPT, domain_tag="test", status=DiscoveryStatus.PROVISIONAL, scope="public"))
        idx.put(ConceptSkeleton(adl_id="b", semantic_type=ADLType.CONCEPT, domain_tag="test", status=DiscoveryStatus.VALIDATED, scope="public"))
        results = idx.filter(status=DiscoveryStatus.VALIDATED)
        assert len(results) == 1
        assert results[0].adl_id == "b"

    def test_filter_by_domain(self):
        idx = HotIndex()
        sk = ConceptSkeleton(
            adl_id="a", semantic_type=ADLType.CONCEPT, domain_tag="financial_aml", status=DiscoveryStatus.PROVISIONAL,
            scope="public",
        )
        idx.put(sk)
        assert len(idx.filter(domain="financial_aml")) == 1
        assert len(idx.filter(domain="other")) == 0

    def test_filter_by_scope_prefix(self):
        idx = HotIndex()
        idx.put(ConceptSkeleton(adl_id="a", semantic_type=ADLType.CONCEPT, domain_tag="test", status=DiscoveryStatus.PROVISIONAL, scope="private/acme"))
        idx.put(ConceptSkeleton(adl_id="b", semantic_type=ADLType.CONCEPT, domain_tag="test", status=DiscoveryStatus.PROVISIONAL, scope="public"))
        assert len(idx.filter(scope_prefix="private/")) == 1
        assert len(idx.filter(scope_prefix="public")) == 1
        assert len(idx.filter(scope_prefix="shared/")) == 0

    def test_clear(self):
        idx = HotIndex()
        idx.put(ConceptSkeleton(adl_id="a", semantic_type=ADLType.CONCEPT, domain_tag="test", status=DiscoveryStatus.PROVISIONAL, scope="public"))
        idx.clear()
        assert len(idx) == 0
        assert idx.get("a") is None


# ---------------------------------------------------------------------------
# WarmIndex
# ---------------------------------------------------------------------------


class TestWarmIndex:
    def test_insert_and_get_document(self, tmp_path: Path):
        db = tmp_path / "warm.db"
        warm = WarmIndex(str(db))
        doc = parse_text(
            "---\nadl_type: discovery\nadl_id: warm-test\nstatus: provisional\nconfidence: 0.5\n---\n\n# Test\n"
        )
        warm.insert_document(doc)
        retrieved = warm.get_document("warm-test")
        assert retrieved is not None
        assert retrieved.adl_id == "warm-test"

    def test_delete_document(self, tmp_path: Path):
        db = tmp_path / "warm.db"
        warm = WarmIndex(str(db))
        doc = parse_text(
            "---\nadl_type: discovery\nadl_id: del-test\nstatus: provisional\nconfidence: 0.5\n---\n\n# Test\n"
        )
        warm.insert_document(doc)
        assert warm.get_document("del-test") is not None
        warm.delete_document("del-test")
        assert warm.get_document("del-test") is None

    def test_cascade_filter(self, tmp_path: Path):
        db = tmp_path / "warm.db"
        warm = WarmIndex(str(db))
        doc = parse_text(
            "---\n"
            "adl_type: discovery\n"
            "adl_id: cf-test\n"
            "status: validated\n"
            "confidence: 0.8\n"
            "domain: financial_aml\n"
            "scope: private/acme\n"
            "---\n\n# Test\n"
        )
        warm.insert_document(doc)
        assert warm.cascade_filter(status=DiscoveryStatus.VALIDATED) == ["cf-test"]
        assert warm.cascade_filter(domain="financial_aml") == ["cf-test"]
        assert warm.cascade_filter(scope_prefix="private/") == ["cf-test"]
        assert warm.cascade_filter(domain="other") == []

    def test_get_related_sql_bfs(self, tmp_path: Path):
        db = tmp_path / "warm.db"
        warm = WarmIndex(str(db))
        # Insert two docs with a relation
        doc_a = parse_text(
            "---\nadl_type: discovery\nadl_id: rel-a\nstatus: provisional\nconfidence: 0.5\n---\n\n# A\n"
        )
        doc_b = parse_text(
            "---\nadl_type: discovery\nadl_id: rel-b\nstatus: provisional\nconfidence: 0.5\n---\n\n# B\n"
        )
        warm.insert_document(doc_a)
        warm.insert_document(doc_b)
        warm._add_relation(
            ADLRelationBlock(source="rel-a", relation="related-to", target="rel-b", confidence=0.8)
        )
        related = warm.get_related("rel-a", depth=1)
        assert len(related) == 1
        assert related[0][0] == "rel-b"
        assert related[0][1] == "related-to"

    def test_close(self, tmp_path: Path):
        db = tmp_path / "warm.db"
        warm = WarmIndex(str(db))
        warm.close()
        # After close, operations should raise
        with pytest.raises((sqlite3.ProgrammingError, sqlite3.Error)):
            warm.get_document("x")


# ---------------------------------------------------------------------------
# ADLMemory (unified interface)
# ---------------------------------------------------------------------------


class TestADLMemory:
    def test_store_retrieve_delete(self, tmp_path: Path):
        db = tmp_path / "mem.db"
        mem = ADLMemory(str(db))
        doc = parse_text(
            "---\nadl_type: discovery\nadl_id: mem-test\nstatus: provisional\nconfidence: 0.5\n---\n\n# Test\n"
        )
        mem.store(doc)
        assert mem.retrieve("mem-test") is not None
        mem.delete("mem-test")
        assert mem.retrieve("mem-test") is None
        mem.close()

    def test_find_related(self, tmp_path: Path):
        db = tmp_path / "mem.db"
        mem = ADLMemory(str(db))
        doc_a = parse_text(
            "---\n"
            "adl_type: discovery\n"
            "adl_id: find-a\n"
            "status: provisional\n"
            "confidence: 0.5\n"
            "---\n\n# A\n\n"
            "```adl:relation\nsource: find-a\npredicate: related-to\ntarget: find-b\nweight: 0.9\n```\n"
        )
        doc_b = parse_text(
            "---\nadl_type: discovery\nadl_id: find-b\nstatus: provisional\nconfidence: 0.5\n---\n\n# B\n"
        )
        mem.store(doc_a)
        mem.store(doc_b)
        related = mem.find_related("find-a", depth=1)
        assert len(related) >= 1
        mem.close()

    def test_prefilter(self, tmp_path: Path):
        db = tmp_path / "mem.db"
        mem = ADLMemory(str(db))
        doc = parse_text(
            "---\n"
            "adl_type: discovery\n"
            "adl_id: pf-test\n"
            "status: validated\n"
            "confidence: 0.8\n"
            "domain: financial_aml\n"
            "scope: public\n"
            "---\n\n# Test\n"
        )
        mem.store(doc)
        # Hot layer should hit immediately
        results = mem.prefilter(status=DiscoveryStatus.VALIDATED, domain="financial_aml")
        assert len(results) == 1
        assert results[0].adl_id == "pf-test"
        # Miss case
        assert mem.prefilter(status=DiscoveryStatus.DEPRECATED) == []
        mem.close()

    def test_tenant_id_attachment(self, tmp_path: Path):
        db = tmp_path / "mem.db"
        mem = ADLMemory(str(db), tenant_id="t-123")
        doc = parse_text(
            "---\nadl_type: discovery\nadl_id: tenant-doc\nstatus: provisional\nconfidence: 0.5\n---\n\n# Test\n"
        )
        mem.store(doc)
        assert hasattr(doc, "_tenant_id")
        assert doc._tenant_id == "t-123"
        mem.close()

    def test_multiple_stores(self, tmp_path: Path):
        db = tmp_path / "mem.db"
        mem = ADLMemory(str(db))
        for i in range(10):
            doc = parse_text(
                f"---\n"
                f"adl_type: discovery\n"
                f"adl_id: batch-{i}\n"
                f"status: provisional\n"
                f"confidence: 0.5\n"
                f"---\n\n# Batch {i}\n"
            )
            mem.store(doc)
        assert len(mem.hot) == 10
        mem.close()
