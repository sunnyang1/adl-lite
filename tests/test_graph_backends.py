"""
Tests for adl_lite.graph_backends — GraphBackend contract, adapter parity,
and WarmIndex graph restart consistency (P1-1).

Covers:
    - GraphBackend protocol surface (NetworkXGraphAdapter / SQLGraphAdapter)
    - Bidirectional (undirected) BFS semantics shared by all backends
    - Cross-backend parity: same store state -> same query result set
    - WarmIndex restart consistency: graph rebuilt from SQLite at init,
      clean degradation to the SQL path when the rebuild fails
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pytest

from adl_lite.graph_backends import (
    HAS_NETWORKX,
    GraphBackend,
    NetworkXGraphAdapter,
    SQLGraphAdapter,
)
from adl_lite.memory import ADLMemory, WarmIndex
from adl_lite.models import ADLRelationBlock
from adl_lite.parser import parse_text

pytestmark = pytest.mark.skipif(not HAS_NETWORKX, reason="networkx not installed")


def _doc(adl_id: str):
    """Minimal parsed ADL document with the given id."""
    return parse_text(
        f"---\nadl_type: discovery\nadl_id: {adl_id}\nstatus: provisional\n"
        f"confidence: 0.5\n---\n\n# {adl_id}\n"
    )


# ---------------------------------------------------------------------------
# NetworkXGraphAdapter
# ---------------------------------------------------------------------------


class TestNetworkXGraphAdapter:
    def test_implements_graph_backend_protocol(self):
        adapter = NetworkXGraphAdapter()
        assert isinstance(adapter, GraphBackend)

    def test_add_edge_and_contains(self):
        adapter = NetworkXGraphAdapter()
        assert "cap-a" not in adapter
        adapter.add_edge("cap-a", "cap-b", "related-to", 0.9)
        assert "cap-a" in adapter
        assert "cap-b" in adapter
        assert "cap-c" not in adapter

    def test_node_count(self):
        adapter = NetworkXGraphAdapter()
        assert adapter.node_count() == 0
        adapter.add_edge("cap-a", "cap-b", "related-to")
        adapter.add_edge("cap-b", "cap-c", "fork-of")
        assert adapter.node_count() == 3

    def test_bfs_bidirectional(self):
        """An edge connects its endpoints regardless of storage direction."""
        adapter = NetworkXGraphAdapter()
        adapter.add_edge("cap-a", "cap-b", "specialisation-of", 0.8)
        # Forward query finds the target...
        forward = adapter.bfs("cap-a", max_depth=1)
        assert forward == [("cap-b", "specialisation-of", 0.8)]
        # ...and the reverse query finds the source with the stored metadata.
        reverse = adapter.bfs("cap-b", max_depth=1)
        assert reverse == [("cap-a", "specialisation-of", 0.8)]

    def test_bfs_depth_limit(self):
        adapter = NetworkXGraphAdapter()
        adapter.add_edge("a", "b", "related-to", 0.9)
        adapter.add_edge("b", "c", "related-to", 0.8)
        assert {r[0] for r in adapter.bfs("a", max_depth=1)} == {"b"}
        assert {r[0] for r in adapter.bfs("a", max_depth=2)} == {"b", "c"}

    def test_bfs_unknown_node_returns_empty(self):
        adapter = NetworkXGraphAdapter()
        adapter.add_edge("a", "b", "related-to")
        assert adapter.bfs("unknown", max_depth=2) == []

    def test_bfs_negative_depth_returns_empty(self):
        adapter = NetworkXGraphAdapter()
        adapter.add_edge("a", "b", "related-to")
        assert adapter.bfs("a", max_depth=-1) == []

    def test_bfs_default_metadata(self):
        """Edges added without explicit metadata report defaults."""
        adapter = NetworkXGraphAdapter()
        adapter.graph.add_edge("a", "b")  # bare edge, no attributes
        assert adapter.bfs("a", max_depth=1) == [("b", "related-to", 1.0)]

    def test_close_is_noop(self):
        adapter = NetworkXGraphAdapter()
        adapter.close()  # must not raise
        assert adapter.node_count() == 0


# ---------------------------------------------------------------------------
# SQLGraphAdapter
# ---------------------------------------------------------------------------


class TestSQLGraphAdapter:
    def test_implements_graph_backend_protocol(self):
        adapter = SQLGraphAdapter()
        assert isinstance(adapter, GraphBackend)
        adapter.close()

    def test_add_edge_and_contains(self):
        adapter = SQLGraphAdapter()
        assert "cap-a" not in adapter
        adapter.add_edge("cap-a", "cap-b", "related-to", 0.9)
        assert "cap-a" in adapter
        assert "cap-b" in adapter
        assert "cap-c" not in adapter
        adapter.close()

    def test_node_count(self):
        adapter = SQLGraphAdapter()
        assert adapter.node_count() == 0
        adapter.add_edge("a", "b", "related-to")
        adapter.add_edge("b", "c", "fork-of")
        assert adapter.node_count() == 3
        adapter.close()

    def test_bfs_bidirectional(self):
        adapter = SQLGraphAdapter()
        adapter.add_edge("cap-a", "cap-b", "specialisation-of", 0.8)
        assert adapter.bfs("cap-a", max_depth=1) == [("cap-b", "specialisation-of", 0.8)]
        assert adapter.bfs("cap-b", max_depth=1) == [("cap-a", "specialisation-of", 0.8)]
        adapter.close()

    def test_bfs_depth_limit(self):
        adapter = SQLGraphAdapter()
        adapter.add_edge("a", "b", "related-to", 0.9)
        adapter.add_edge("b", "c", "related-to", 0.8)
        assert {r[0] for r in adapter.bfs("a", max_depth=1)} == {"b"}
        assert {r[0] for r in adapter.bfs("a", max_depth=2)} == {"b", "c"}
        adapter.close()

    def test_bfs_unknown_and_negative(self):
        adapter = SQLGraphAdapter()
        adapter.add_edge("a", "b", "related-to")
        assert adapter.bfs("unknown", max_depth=1) == []
        assert adapter.bfs("a", max_depth=-1) == []
        adapter.close()

    def test_persistent_db_path(self, tmp_path: Path):
        """Edges stored in a file-backed adapter survive a reconnect."""
        db = str(tmp_path / "graph.db")
        adapter = SQLGraphAdapter(db_path=db)
        adapter.add_edge("a", "b", "related-to", 0.9)
        adapter.close()

        reopened = SQLGraphAdapter(db_path=db)
        assert reopened.bfs("a", max_depth=1) == [("b", "related-to", 0.9)]
        reopened.close()


# ---------------------------------------------------------------------------
# Cross-backend parity (defect ①: same query, same result on both backends)
# ---------------------------------------------------------------------------


class TestCrossBackendParity:
    # (source, target, relation, confidence) — mixed directions on purpose:
    # b has two in-edges, one out-edge, and e is only reachable in reverse.
    EDGES = [
        ("a", "b", "related-to", 0.9),
        ("c", "b", "specialisation-of", 0.8),
        ("b", "d", "fork-of", 0.7),
        ("d", "e", "mitigated-by", 0.6),
    ]

    def _networkx(self) -> NetworkXGraphAdapter:
        adapter = NetworkXGraphAdapter()
        for src, tgt, pred, conf in self.EDGES:
            adapter.add_edge(src, tgt, pred, conf)
        return adapter

    def _sql(self) -> SQLGraphAdapter:
        adapter = SQLGraphAdapter()
        for src, tgt, pred, conf in self.EDGES:
            adapter.add_edge(src, tgt, pred, conf)
        return adapter

    def test_adapter_parity_all_starts_and_depths(self):
        nx_adapter = self._networkx()
        sql_adapter = self._sql()
        try:
            for start in ["a", "b", "c", "d", "e", "unknown"]:
                for depth in [0, 1, 2, 3]:
                    nx_result = sorted(nx_adapter.bfs(start, max_depth=depth))
                    sql_result = sorted(sql_adapter.bfs(start, max_depth=depth))
                    assert nx_result == sql_result, (
                        f"backend mismatch at start={start} depth={depth}: "
                        f"{nx_result} != {sql_result}"
                    )
        finally:
            sql_adapter.close()

    def test_warmindex_graph_and_sql_paths_agree(self, tmp_path: Path):
        """WarmIndex._graph_bfs and WarmIndex._sql_bfs return the same set."""
        warm = WarmIndex(str(tmp_path / "warm.db"))
        for src, tgt, pred, conf in self.EDGES:
            warm._add_relation(
                ADLRelationBlock(source=src, relation=pred, target=tgt, confidence=conf)
            )
        for start in ["a", "b", "c", "d", "e"]:
            for depth in [1, 2]:
                graph_result = sorted(warm._graph_bfs(start, depth))
                sql_result = sorted((cid, p, float(c)) for cid, p, c in warm._sql_bfs(start, depth))
                assert graph_result == sql_result
        # And get_related (which prefers the graph path) agrees with SQL.
        assert sorted(warm.get_related("b", 1)) == sorted(
            (cid, p, float(c)) for cid, p, c in warm._sql_bfs("b", 1)
        )
        warm.close()


# ---------------------------------------------------------------------------
# WarmIndex restart consistency (P1-1)
# ---------------------------------------------------------------------------


class TestWarmIndexRestartConsistency:
    def test_restart_history_visible(self, tmp_path: Path):
        """② A fresh WarmIndex on the same db file sees historical relations."""
        db = str(tmp_path / "warm.db")
        warm = WarmIndex(db)
        warm.insert_document(_doc("old-a"))
        warm._add_relation(
            ADLRelationBlock(source="old-a", relation="related-to", target="old-b", confidence=0.9)
        )
        warm.close()

        # "Restart": a new instance over the same database file.
        reopened = WarmIndex(db)
        # The graph must have been rebuilt from SQLite (not empty).
        assert reopened.graph is not None
        assert "old-a" in reopened.graph and "old-b" in reopened.graph
        assert reopened.get_related("old-a", depth=1) == [("old-b", "related-to", 0.9)]
        reopened.close()

    def test_restart_reverse_direction_visible(self, tmp_path: Path):
        """Historical edges are traversable in both directions after restart."""
        db = str(tmp_path / "warm.db")
        warm = WarmIndex(db)
        warm._add_relation(
            ADLRelationBlock(
                source="old-a", relation="specialisation-of", target="old-b", confidence=0.8
            )
        )
        warm.close()

        reopened = WarmIndex(db)
        assert reopened.get_related("old-b", depth=1) == [("old-a", "specialisation-of", 0.8)]
        reopened.close()

    def test_restart_then_new_edge_both_visible(self, tmp_path: Path):
        """③ After a restart, old (persisted) and new (in-session) edges coexist."""
        db = str(tmp_path / "warm.db")
        warm = WarmIndex(db)
        warm._add_relation(
            ADLRelationBlock(source="old-a", relation="related-to", target="old-b", confidence=0.9)
        )
        warm.close()

        reopened = WarmIndex(db)
        reopened._add_relation(
            ADLRelationBlock(source="old-b", relation="fork-of", target="new-c", confidence=0.7)
        )
        related = sorted(reopened.get_related("old-b", depth=1))
        assert related == [("new-c", "fork-of", 0.7), ("old-a", "related-to", 0.9)]
        # Depth-2 traversal crosses the old/new boundary.
        assert sorted(r[0] for r in reopened.get_related("old-a", depth=2)) == ["new-c", "old-b"]
        reopened.close()

    def test_graph_rebuild_failure_degrades_to_sql(
        self, tmp_path: Path, monkeypatch, caplog: pytest.LogCaptureFixture
    ):
        """④ A failed graph rebuild must not serve a partial graph: the
        instance cleanly degrades to the SQL BFS path (with a warning)."""
        db = str(tmp_path / "warm.db")
        warm = WarmIndex(db)
        warm._add_relation(
            ADLRelationBlock(source="old-a", relation="related-to", target="old-b", confidence=0.9)
        )
        warm.close()

        class _BrokenGraph:
            def __init__(self) -> None:
                pass

            def add_edge(self, *args, **kwargs) -> None:
                raise RuntimeError("simulated graph corruption")

        monkeypatch.setattr("adl_lite.memory.nx.DiGraph", _BrokenGraph)
        # The adl_lite logger sets propagate=False; lift it so caplog can
        # observe the degradation warning.
        monkeypatch.setattr(logging.getLogger("adl_lite"), "propagate", True)
        with caplog.at_level(logging.WARNING, logger="adl_lite.memory"):
            degraded = WarmIndex(db)

        assert degraded.graph is None
        assert any("degrading to SQL BFS" in rec.getMessage() for rec in caplog.records)
        # Queries still return the full history via the SQL path.
        assert degraded.get_related("old-a", depth=1) == [("old-b", "related-to", 0.9)]
        # New edges added while degraded remain queryable.
        degraded._add_relation(
            ADLRelationBlock(source="old-b", relation="fork-of", target="new-c", confidence=0.7)
        )
        assert sorted(r[0] for r in degraded.get_related("old-b", depth=1)) == ["new-c", "old-a"]
        degraded.close()

    def test_adlmemory_restart_consistency(self, tmp_path: Path):
        """ADLMemory-level: restart keeps relations, new relations join them."""
        db = str(tmp_path / "mem.db")
        mem = ADLMemory(db)
        doc_a = parse_text(
            "---\n"
            "adl_type: discovery\n"
            "adl_id: mem-a\n"
            "status: provisional\n"
            "confidence: 0.5\n"
            "---\n\n# A\n\n"
            "```adl:relation\nsource: mem-a\nrelation: related-to\ntarget: mem-b\nconfidence: 0.9\n```\n"
        )
        mem.store(doc_a)
        mem.store(_doc("mem-b"))
        mem.close()

        reopened = ADLMemory(db)
        assert reopened.find_related("mem-a", depth=1) == [("mem-b", "related-to", 0.9)]
        # Reverse direction sees the historical edge too.
        assert reopened.find_related("mem-b", depth=1) == [("mem-a", "related-to", 0.9)]

        doc_c = parse_text(
            "---\n"
            "adl_type: discovery\n"
            "adl_id: mem-c\n"
            "status: provisional\n"
            "confidence: 0.5\n"
            "---\n\n# C\n\n"
            "```adl:relation\nsource: mem-b\nrelation: fork-of\ntarget: mem-c\nconfidence: 0.7\n```\n"
        )
        reopened.store(doc_c)
        assert sorted(reopened.find_related("mem-b", depth=1)) == [
            ("mem-a", "related-to", 0.9),
            ("mem-c", "fork-of", 0.7),
        ]
        reopened.close()

    def test_sqlite_is_source_of_truth_after_close(self, tmp_path: Path):
        """The relations table persists independently of the in-memory graph."""
        db = str(tmp_path / "warm.db")
        warm = WarmIndex(db)
        warm._add_relation(
            ADLRelationBlock(source="x", relation="related-to", target="y", confidence=0.5)
        )
        warm.close()

        conn = sqlite3.connect(db)
        rows = conn.execute(
            "SELECT source, predicate, target, confidence FROM relations"
        ).fetchall()
        conn.close()
        assert rows == [("x", "related-to", "y", 0.5)]
