"""Tests for Neo4jGraphAdapter — uses mocked driver (no live Neo4j needed)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from adl_lite.neo4j_adapter import Neo4jGraphAdapter


class TestNeo4jGraphAdapter:
    """Mock-based tests for Neo4jGraphAdapter."""

    @pytest.fixture
    def adapter(self) -> Neo4jGraphAdapter:
        """Create an adapter with a mocked driver."""
        a = Neo4jGraphAdapter(uri="bolt://localhost:7687", user="neo4j", password="test")
        a._driver = MagicMock()
        return a

    # --- add_edge ---

    def test_add_edge(self, adapter: Neo4jGraphAdapter) -> None:
        """Verify add_edge sends correct Cypher query with parameters."""
        mock_session = MagicMock()
        adapter._driver.session.return_value.__enter__.return_value = mock_session

        adapter.add_edge("cap-a", "cap-b", "related-to", 0.9)

        adapter._driver.session.assert_called_once_with(database="neo4j")
        mock_session.run.assert_called_once()
        call_args = mock_session.run.call_args
        assert "MERGE (s:ADLConcept {id: $source})" in call_args[0][0]
        assert call_args[1] == {
            "source": "cap-a",
            "target": "cap-b",
            "relation": "related-to",
            "confidence": 0.9,
        }

    # --- bfs ---

    def _make_record(self, node_id: str, relation: str, confidence: float) -> MagicMock:
        """Helper to create a mock Neo4j record."""
        record = MagicMock()
        record.__getitem__.side_effect = lambda key: {
            "node_id": node_id,
            "relation": relation,
            "confidence": confidence,
        }[key]
        return record

    def test_bfs(self, adapter: Neo4jGraphAdapter) -> None:
        """Verify bfs returns correct tuples from Neo4j records."""
        mock_session = MagicMock()
        adapter._driver.session.return_value.__enter__.return_value = mock_session

        mock_session.run.return_value = [
            self._make_record("cap-b", "related-to", 0.9),
            self._make_record("cap-c", "depends-on", 0.8),
        ]

        results = adapter.bfs("cap-a", max_depth=2)

        assert results == [
            ("cap-b", "related-to", 0.9),
            ("cap-c", "depends-on", 0.8),
        ]
        mock_session.run.assert_called_once()
        call_args = mock_session.run.call_args
        assert "MATCH path = (start)-[*1..$depth]->(other:ADLConcept)" in call_args[0][0]
        assert call_args[1] == {"cid": "cap-a", "depth": 2}

    def test_bfs_depth_zero(self, adapter: Neo4jGraphAdapter) -> None:
        """Verify bfs with depth=0 returns empty (no traversal)."""
        mock_session = MagicMock()
        adapter._driver.session.return_value.__enter__.return_value = mock_session
        mock_session.run.return_value = []

        results = adapter.bfs("cap-a", max_depth=0)

        assert results == []
        mock_session.run.assert_called_once()
        call_args = mock_session.run.call_args
        assert call_args[1] == {"cid": "cap-a", "depth": 0}

    def test_bfs_no_results(self, adapter: Neo4jGraphAdapter) -> None:
        """Verify bfs returns empty list when no matching nodes."""
        mock_session = MagicMock()
        adapter._driver.session.return_value.__enter__.return_value = mock_session
        mock_session.run.return_value = []

        results = adapter.bfs("nonexistent", max_depth=2)

        assert results == []

    # --- __contains__ ---

    def test_contains_true(self, adapter: Neo4jGraphAdapter) -> None:
        """Verify __contains__ returns True when node count > 0."""
        mock_session = MagicMock()
        adapter._driver.session.return_value.__enter__.return_value = mock_session

        record = MagicMock()
        record.__getitem__.return_value = 1
        mock_session.run.return_value.single.return_value = record

        result = "cap-a" in adapter

        assert result is True

    def test_contains_false(self, adapter: Neo4jGraphAdapter) -> None:
        """Verify __contains__ returns False when node count is 0."""
        mock_session = MagicMock()
        adapter._driver.session.return_value.__enter__.return_value = mock_session

        record = MagicMock()
        record.__getitem__.return_value = 0
        mock_session.run.return_value.single.return_value = record

        result = "unknown" in adapter

        assert result is False

    def test_contains_missing_driver(self) -> None:
        """Verify __contains__ triggers lazy driver init when driver is None."""
        a = Neo4jGraphAdapter(uri="bolt://localhost:7687", user="neo4j", password="test")
        # Driver is None — should trigger _get_driver which raises ImportError
        # since neo4j is not installed in test environment
        with pytest.raises(ImportError, match="Neo4j support requires the 'neo4j' extra"):
            _ = "anything" in a

    # --- node_count ---

    def test_node_count(self, adapter: Neo4jGraphAdapter) -> None:
        """Verify node_count returns the count from Neo4j."""
        mock_session = MagicMock()
        adapter._driver.session.return_value.__enter__.return_value = mock_session

        record = MagicMock()
        record.__getitem__.return_value = 5
        mock_session.run.return_value.single.return_value = record

        count = adapter.node_count()

        assert count == 5

    def test_node_count_zero(self, adapter: Neo4jGraphAdapter) -> None:
        """Verify node_count returns 0 when graph is empty."""
        mock_session = MagicMock()
        adapter._driver.session.return_value.__enter__.return_value = mock_session

        record = MagicMock()
        record.__getitem__.return_value = 0
        mock_session.run.return_value.single.return_value = record

        count = adapter.node_count()

        assert count == 0

    def test_node_count_no_record(self, adapter: Neo4jGraphAdapter) -> None:
        """Verify node_count returns 0 when single() returns None."""
        mock_session = MagicMock()
        adapter._driver.session.return_value.__enter__.return_value = mock_session

        mock_session.run.return_value.single.return_value = None

        count = adapter.node_count()

        assert count == 0

    # --- close ---

    def test_close(self, adapter: Neo4jGraphAdapter) -> None:
        """Verify close calls driver.close() and resets driver to None."""
        mock_driver = adapter._driver
        adapter.close()

        mock_driver.close.assert_called_once()
        assert adapter._driver is None

    def test_close_idempotent(self, adapter: Neo4jGraphAdapter) -> None:
        """Verify calling close twice does not error."""
        mock_driver = adapter._driver
        adapter.close()
        adapter.close()  # Second call should be a no-op

        mock_driver.close.assert_called_once()

    # --- rebuild_from_relations ---

    def test_rebuild_from_relations(self, adapter: Neo4jGraphAdapter) -> None:
        """Verify rebuild_from_relations clears graph and creates edges."""
        mock_session = MagicMock()
        adapter._driver.session.return_value.__enter__.return_value = mock_session
        mock_session.run.return_value = MagicMock()  # returns an iterable

        relations = [
            {"source": "cap-a", "predicate": "related-to", "target": "cap-b", "confidence": 0.9},
            {"source": "cap-b", "predicate": "depends-on", "target": "cap-c", "confidence": 0.8},
        ]

        count = adapter.rebuild_from_relations(relations)

        assert count == 2
        # First call should be DETACH DELETE
        detach_call = mock_session.run.call_args_list[0]
        assert "DETACH DELETE" in detach_call[0][0]
        # Should have 3 total run calls: 1 DETACH + 2 MERGE
        assert mock_session.run.call_count == 3

    def test_rebuild_from_relations_empty(self, adapter: Neo4jGraphAdapter) -> None:
        """Verify rebuild_from_relations with empty list only clears graph."""
        mock_session = MagicMock()
        adapter._driver.session.return_value.__enter__.return_value = mock_session
        mock_session.run.return_value = MagicMock()

        count = adapter.rebuild_from_relations([])

        assert count == 0
        # Only the DETACH DELETE call
        mock_session.run.assert_called_once()
        assert "DETACH DELETE" in mock_session.run.call_args[0][0]

    # --- ImportError graceful handling ---

    def test_import_error_graceful(self) -> None:
        """Verify _get_driver raises ImportError when neo4j package is missing."""
        a = Neo4jGraphAdapter(uri="bolt://localhost:7687", user="neo4j", password="test")
        with patch.object(a, "_driver", None):
            # Simulate import failure by mocking __import__ to raise
            import builtins

            original_import = builtins.__import__

            def fake_import(name, *args, **kwargs):
                if name == "neo4j":
                    raise ImportError("No module named neo4j")
                return original_import(name, *args, **kwargs)

            with patch.object(builtins, "__import__", side_effect=fake_import):
                with pytest.raises(ImportError, match="Neo4j support requires the 'neo4j' extra"):
                    a._get_driver()
