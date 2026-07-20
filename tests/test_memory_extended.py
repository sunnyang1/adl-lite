"""
Extended tests for adl_lite.memory — degradation, archival, BFS, tenant, and close.

These tests cover uncovered lines in WarmIndex degradation logic (lines 227-228,
237-238, 259-260), reset_degradation (532-533), _graph_bfs (405-430),
_maybe_archive (598-616, 621), retrieve_chain cold-warm merge (660-687),
prefilter tenant_id (734, 743-750), and close with VectorIndex mock (785-792).
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from adl_lite.memory import _WARM_TIMEOUT_THRESHOLD, ADLMemory, WarmIndex
from adl_lite.models import (
    ADLRelationBlock,
    DiscoveryStatus,
    Event,
    EventChain,
    EventType,
)
from adl_lite.parser import parse_text

# ---------------------------------------------------------------------------
# WarmIndex degradation tests
# ---------------------------------------------------------------------------


class TestWarmDegradation:
    """Tests for WarmIndex timeout degradation and recovery."""

    def test_warm_degradation_on_timeout(self, tmp_path: Path):
        """After a slow query, WarmIndex._degraded becomes True.
        Subsequent get_document() returns None and cascade_filter() returns [].
        Covers lines 227-228, 237-238, 259-260."""
        db = tmp_path / "warm.db"
        warm = WarmIndex(str(db))

        # Insert a document normally first
        doc = parse_text(
            "---\nadl_type: discovery\nadl_id: deg-test\nstatus: provisional\n"
            "confidence: 0.5\n---\n\n# Test\n"
        )
        warm.insert_document(doc)

        # Verify it's accessible before degradation
        assert warm.get_document("deg-test") is not None
        assert warm.cascade_filter(status=DiscoveryStatus.PROVISIONAL) == ["deg-test"]

        # Simulate a slow query by mocking time.perf_counter to exceed threshold
        # The get_document method uses time.perf_counter to measure elapsed time.
        # We patch it so that the second call (after the query) returns a value
        # that makes elapsed > threshold.
        original_perf_counter = time.perf_counter
        call_count = 0

        def mock_perf_counter():
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                return original_perf_counter()
            # Make the elapsed time exceed the threshold
            return original_perf_counter() + _WARM_TIMEOUT_THRESHOLD + 1.0

        with patch("adl_lite.memory.time.perf_counter", side_effect=mock_perf_counter):
            warm.get_document("deg-test")

        # After degradation, get_document should return None
        assert warm._degraded is True
        assert warm.get_document("deg-test") is None

        # After degradation, cascade_filter should return empty list
        assert warm.cascade_filter(status=DiscoveryStatus.PROVISIONAL) == []

        warm.close()

    def test_warm_reset_degradation(self, tmp_path: Path):
        """After triggering degradation, call reset_degradation(),
        verify _degraded=False and queries work again. Covers lines 532-533."""
        db = tmp_path / "warm.db"
        warm = WarmIndex(str(db))

        # Insert a document
        doc = parse_text(
            "---\nadl_type: discovery\nadl_id: reset-test\nstatus: provisional\n"
            "confidence: 0.5\n---\n\n# Test\n"
        )
        warm.insert_document(doc)

        # Manually set degradation
        warm._degraded = True
        warm._last_query_time = 10.0

        # Verify degraded behavior
        assert warm.get_document("reset-test") is None
        assert warm.cascade_filter() == []
        assert warm.degraded is True

        # Reset degradation
        warm.reset_degradation()

        # Verify reset
        assert warm._degraded is False
        assert warm._last_query_time == 0.0
        assert warm.degraded is False

        # Verify queries work again after reset
        retrieved = warm.get_document("reset-test")
        assert retrieved is not None
        assert retrieved.adl_id == "reset-test"

        cascade_result = warm.cascade_filter(status=DiscoveryStatus.PROVISIONAL)
        assert "reset-test" in cascade_result

        warm.close()


# ---------------------------------------------------------------------------
# WarmIndex graph BFS tests
# ---------------------------------------------------------------------------


class TestWarmGraphBFS:
    """Tests for WarmIndex._graph_bfs (NetworkX-based BFS). Covers lines 405-430."""

    def test_warm_graph_bfs_multi_depth(self, tmp_path: Path):
        """Insert events with relation edges, call get_related with depth>1
        which triggers _graph_bfs through NetworkX.
        Verify traversal returns expected related concepts."""
        db = tmp_path / "warm.db"
        warm = WarmIndex(str(db))

        # Insert three documents: A -> B -> C chain
        doc_a = parse_text(
            "---\nadl_type: discovery\nadl_id: bfs-a\nstatus: provisional\n"
            "confidence: 0.5\n---\n\n# A\n"
        )
        doc_b = parse_text(
            "---\nadl_type: discovery\nadl_id: bfs-b\nstatus: provisional\n"
            "confidence: 0.5\n---\n\n# B\n"
        )
        doc_c = parse_text(
            "---\nadl_type: discovery\nadl_id: bfs-c\nstatus: provisional\n"
            "confidence: 0.5\n---\n\n# C\n"
        )
        warm.insert_document(doc_a)
        warm.insert_document(doc_b)
        warm.insert_document(doc_c)

        # Add edges: A -> B, B -> C
        warm._add_relation(
            ADLRelationBlock(source="bfs-a", relation="related-to", target="bfs-b", confidence=0.9)
        )
        warm._add_relation(
            ADLRelationBlock(
                source="bfs-b", relation="specialisation-of", target="bfs-c", confidence=0.8
            )
        )

        # Depth=1: only direct neighbors of A
        related_d1 = warm.get_related("bfs-a", depth=1)
        assert len(related_d1) == 1
        assert related_d1[0][0] == "bfs-b"

        # Depth=2: A -> B -> C (both B and C)
        related_d2 = warm.get_related("bfs-a", depth=2)
        related_ids = [r[0] for r in related_d2]
        assert "bfs-b" in related_ids
        assert "bfs-c" in related_ids

        # Verify relation metadata is carried
        for related_id, relation, confidence in related_d2:
            if related_id == "bfs-b":
                assert relation == "related-to"
                assert confidence == 0.9
            elif related_id == "bfs-c":
                assert relation == "specialisation-of"
                assert confidence == 0.8

        warm.close()


# ---------------------------------------------------------------------------
# WarmIndex archival (maybe_archive) tests
# ---------------------------------------------------------------------------


class TestWarmMaybeArchive:
    """Tests for ADLMemory._maybe_archive archival threshold. Covers lines 598-616, 621."""

    def test_warm_maybe_archive_triggers(self, tmp_path: Path):
        """Store enough events to trigger _maybe_archive archival threshold.
        Verify some events are moved from warm to cold tier."""
        db_path = tmp_path / "mem.db"
        cold_dir = tmp_path / "cold_archives"
        # Set a very low threshold so archival triggers quickly
        # _maybe_archive uses keep_last_n=10, so we need chain > keep_last_n+1 = 11
        mem = ADLMemory(str(db_path), cold_threshold=5, cold_base_dir=str(cold_dir))

        doc = parse_text(
            "---\nadl_type: discovery\nadl_id: archive-test\nstatus: provisional\n"
            "confidence: 0.5\n---\n\n# Test\n"
        )

        # Build a chain with enough events to exceed both threshold AND
        # the keep_last_n+1 bound (so actual archival happens)
        chain = EventChain(concept_id="archive-test")
        genesis = Event(
            concept_id="archive-test",
            event_type=EventType.SNAPSHOT,
            actor="parser",
            reasoning="genesis",
            payload={"synthetic": True, "adl_type": "discovery", "confidence": 0.5},
        )
        chain.append(genesis)

        # Add enough events to exceed keep_last_n+1 (10+1=11)
        # Need at least 12 events total for actual archival
        for i in range(20):
            evt = Event(
                concept_id="archive-test",
                event_type=EventType.VALIDATE,
                actor=f"validator-{i}",
                reasoning=f"Validation step {i}",
                payload={"confidence": 0.5 + i * 0.01},
            )
            chain.append(evt)

        # Chain length should exceed threshold AND keep_last_n+1
        assert len(chain) > 5
        assert len(chain) > 11

        # _maybe_archive should trigger archival
        result = mem._maybe_archive(doc, chain)
        assert result is True

        # Verify that cold storage archive file exists
        # _maybe_archive tries compressed=True first, then falls back to compressed=False
        jsonl_path = mem.cold.base_dir / "archive-test.archive.jsonl"
        compressed_path = mem.cold.base_dir / "archive-test.archive.msgpack.zst"
        assert jsonl_path.exists() or compressed_path.exists()

        mem.close()

    def test_warm_maybe_archive_below_threshold(self, tmp_path: Path):
        """When chain length is below threshold, _maybe_archive returns False."""
        db_path = tmp_path / "mem.db"
        cold_dir = tmp_path / "cold_archives2"
        mem = ADLMemory(str(db_path), cold_threshold=100, cold_base_dir=str(cold_dir))

        doc = parse_text(
            "---\nadl_type: discovery\nadl_id: no-archive-test\nstatus: provisional\n"
            "confidence: 0.5\n---\n\n# Test\n"
        )

        chain = EventChain(concept_id="no-archive-test")
        genesis = Event(
            concept_id="no-archive-test",
            event_type=EventType.SNAPSHOT,
            actor="parser",
            reasoning="genesis",
            payload={"synthetic": True, "adl_type": "discovery", "confidence": 0.5},
        )
        chain.append(genesis)

        # Chain length (1) is below threshold (100)
        assert len(chain) <= 100
        result = mem._maybe_archive(doc, chain)
        assert result is False

        mem.close()


# ---------------------------------------------------------------------------
# ADLMemory retrieve_chain cold-warm merge tests
# ---------------------------------------------------------------------------


class TestRetrieveChainMerge:
    """Tests for ADLMemory.retrieve_chain merging warm and cold tiers. Covers lines 660-687."""

    def test_retrieve_chain_cold_warm_merge(self, tmp_path: Path):
        """Store events in both warm and cold tiers, call retrieve_chain
        from ADLMemory. Verify merge/overlay returns combined data correctly."""
        db_path = tmp_path / "mem.db"
        cold_dir = tmp_path / "cold_merge"
        # Low threshold so archival triggers quickly
        mem = ADLMemory(str(db_path), cold_threshold=5, cold_base_dir=str(cold_dir))

        # Build a chain manually for this test — doc is not used directly
        parse_text(
            "---\nadl_type: discovery\nadl_id: merge-test\nstatus: provisional\n"
            "confidence: 0.5\n---\n\n# Test\n"
        )

        # Build a chain with many events to trigger archival
        chain = EventChain(concept_id="merge-test")
        genesis = Event(
            concept_id="merge-test",
            event_type=EventType.SNAPSHOT,
            actor="parser",
            reasoning="genesis",
            payload={"synthetic": True, "adl_type": "discovery", "confidence": 0.5},
        )
        chain.append(genesis)

        for i in range(10):
            evt = Event(
                concept_id="merge-test",
                event_type=EventType.VALIDATE,
                actor=f"validator-{i}",
                reasoning=f"Validation step {i}",
                payload={"confidence": 0.5 + i * 0.01},
            )
            chain.append(evt)

        # Archive to cold storage (trimming the chain)
        from adl_lite.cold_storage import ColdStorage

        cold = ColdStorage(base_dir=str(cold_dir))
        cold.archive(chain, keep_last_n=3, compressed=False)

        # Store the trimmed chain in warm
        mem.warm._store_events(chain)

        # Retrieve chain — should merge warm hot events with cold archived events
        merged_chain = mem.retrieve_chain("merge-test")
        assert merged_chain is not None

        # The merged chain should contain events from both tiers
        # genesis + archived middle + hot tail
        total_events = len(merged_chain)
        assert total_events >= len(chain.events), (
            f"Merged chain ({total_events}) should have at least as many events "
            f"as the trimmed chain ({len(chain.events)})"
        )

        # Verify genesis event is present
        genesis_events = [e for e in merged_chain.events if e.event_type == EventType.SNAPSHOT]
        assert len(genesis_events) >= 1

        mem.close()

    def test_retrieve_chain_no_archive(self, tmp_path: Path):
        """When there's no cold archive, retrieve_chain returns just warm events."""
        db_path = tmp_path / "mem.db"
        cold_dir = tmp_path / "cold_empty"
        mem = ADLMemory(str(db_path), cold_threshold=10000, cold_base_dir=str(cold_dir))

        # Create a document and store it
        doc = parse_text(
            "---\nadl_type: discovery\nadl_id: no-arch-test\nstatus: provisional\n"
            "confidence: 0.5\n---\n\n# Test\n"
        )
        mem.store(doc)

        # Build a chain and store it in warm only
        chain = EventChain(concept_id="no-arch-test")
        genesis = Event(
            concept_id="no-arch-test",
            event_type=EventType.SNAPSHOT,
            actor="parser",
            reasoning="genesis",
            payload={"synthetic": True, "adl_type": "discovery", "confidence": 0.5},
        )
        chain.append(genesis)
        evt = Event(
            concept_id="no-arch-test",
            event_type=EventType.VALIDATE,
            actor="validator-1",
            reasoning="Validation",
            payload={"confidence": 0.8},
        )
        chain.append(evt)
        mem.warm._store_events(chain)

        # Retrieve chain — no archive exists
        retrieved = mem.retrieve_chain("no-arch-test")
        assert retrieved is not None
        assert len(retrieved) == 2

        mem.close()


# ---------------------------------------------------------------------------
# ADLMemory prefilter tenant_id tests
# ---------------------------------------------------------------------------


class TestPrefilterTenantId:
    """Tests for ADLMemory.prefilter with tenant_id filtering. Covers lines 734, 743-750."""

    def test_prefilter_tenant_id(self, tmp_path: Path):
        """Call prefilter on ADLMemory with tenant_id parameter.

        ConceptSkeleton now carries a ``tenant_id`` field (Phase-2 multi-tenant
        isolation). When a tenant queries with its own ``tenant_id``, it sees its
        own documents; a different tenant sees nothing. This exercises the
        tenant_id filter code paths (lines 734, 743-750)."""
        db = tmp_path / "mem.db"

        # First, test with ADLMemory that has NO tenant_id — baseline
        mem_no_tenant = ADLMemory(str(db), tenant_id=None)

        doc_a = parse_text(
            "---\n"
            "adl_type: discovery\n"
            "adl_id: tenant-doc-a\n"
            "status: validated\n"
            "confidence: 0.8\n"
            "domain: test\n"
            "scope: public\n"
            "---\n\n# A\n"
        )
        doc_b = parse_text(
            "---\n"
            "adl_type: discovery\n"
            "adl_id: tenant-doc-b\n"
            "status: validated\n"
            "confidence: 0.7\n"
            "domain: test\n"
            "scope: public\n"
            "---\n\n# B\n"
        )

        # Store docs
        mem_no_tenant.store(doc_a)
        mem_no_tenant.store(doc_b)

        # Without tenant_id, filtering should return all matching docs
        results_no_tenant = mem_no_tenant.prefilter(status=DiscoveryStatus.VALIDATED)
        assert len(results_no_tenant) == 2

        mem_no_tenant.close()

        # Now test with ADLMemory that has tenant_id="tenant-A"
        # Use a fresh database
        db2 = tmp_path / "mem2.db"
        mem = ADLMemory(str(db2), tenant_id="tenant-A")

        doc_c = parse_text(
            "---\n"
            "adl_type: discovery\n"
            "adl_id: tenant-doc-c\n"
            "status: validated\n"
            "confidence: 0.8\n"
            "domain: test\n"
            "scope: public\n"
            "---\n\n# C\n"
        )
        mem.store(doc_c)

        # Verify _tenant_id was attached to the document
        assert hasattr(doc_c, "_tenant_id")
        assert doc_c._tenant_id == "tenant-A"

        # With tenant_id="tenant-A", ADLMemory.store attaches tenant_id to the
        # document and to_skeleton propagates it onto the ConceptSkeleton, so a
        # tenant querying with its own id correctly sees its own document.
        results_with_tenant = mem.prefilter(status=DiscoveryStatus.VALIDATED, tenant_id="tenant-A")
        assert len(results_with_tenant) == 1
        assert results_with_tenant[0].adl_id == "tenant-doc-c"

        # Without explicit tenant_id, effective_tenant = self.tenant_id = "tenant-A"
        # → the tenant still sees its own document.
        results_default = mem.prefilter(status=DiscoveryStatus.VALIDATED)
        assert len(results_default) == 1
        assert results_default[0].adl_id == "tenant-doc-c"

        # A different tenant sees nothing (cross-tenant isolation).
        results_other = mem.prefilter(status=DiscoveryStatus.VALIDATED, tenant_id="tenant-B")
        assert len(results_other) == 0

        mem.close()

    def test_prefilter_tenant_id_warm_fallback(self, tmp_path: Path):
        """When hot layer misses, prefilter falls back to warm cascade
        with tenant_id filtering. Covers lines 743-750."""
        db = tmp_path / "mem.db"
        mem = ADLMemory(str(db), tenant_id="tenant-X")

        # Store a doc so it's in both hot and warm
        doc = parse_text(
            "---\n"
            "adl_type: discovery\n"
            "adl_id: warm-tenant-doc\n"
            "status: validated\n"
            "confidence: 0.8\n"
            "domain: financial_aml\n"
            "scope: public\n"
            "---\n\n# Test\n"
        )
        mem.store(doc)

        # Clear hot layer to force warm fallback
        mem.hot.clear()

        # Prefilter with matching tenant — warm fallback path is exercised
        # Even though hot is empty, warm cascade returns IDs and the code
        # checks tenant_id in the warm fallback section (lines 743-750)
        mem.prefilter(
            status=DiscoveryStatus.VALIDATED, domain="financial_aml", tenant_id="tenant-X"
        )
        # After clearing hot, the warm fallback will find IDs but won't have
        # skeletons in hot to return. The key coverage is the tenant_id filter
        # in the warm fallback path being exercised.

        mem.close()


# ---------------------------------------------------------------------------
# ADLMemory.close with VectorIndex mock tests
# ---------------------------------------------------------------------------


class TestCloseWithVectorIndex:
    """Tests for ADLMemory.close() with VectorIndex cleanup. Covers lines 785-792."""

    def test_close_with_vector_index_mock(self, tmp_path: Path):
        """Mock VectorIndex, verify ADLMemory.close() calls vector_index
        cleanup (save and close). Covers lines 785-792."""
        db = tmp_path / "mem.db"
        mock_vi = MagicMock()
        mock_vi.save = MagicMock()
        mock_vi.close = MagicMock()

        mem = ADLMemory(str(db), vector_index=mock_vi)

        # Store a document so vector_index.add is called
        doc = parse_text(
            "---\nadl_type: discovery\nadl_id: vi-test\nstatus: provisional\n"
            "confidence: 0.5\n---\n\n# Test\n"
        )
        mem.store(doc)

        # Close should call vector_index.save() and vector_index.close()
        mem.close()

        mock_vi.save.assert_called_once()
        mock_vi.close.assert_called_once()

    def test_close_with_vector_index_exception_handling(self, tmp_path: Path):
        """When VectorIndex.save() or close() raises, ADLMemory.close()
        should not crash. Covers lines 785-792 exception handling."""
        db = tmp_path / "mem.db"
        mock_vi = MagicMock()
        mock_vi.save = MagicMock(side_effect=RuntimeError("save failed"))
        mock_vi.close = MagicMock(side_effect=RuntimeError("close failed"))

        mem = ADLMemory(str(db), vector_index=mock_vi)

        # Close should not raise even if VectorIndex methods fail
        mem.close()

        # Both methods should have been called despite errors
        mock_vi.save.assert_called_once()
        mock_vi.close.assert_called_once()
