"""Tests for Neo4jGraphAdapter — uses mocked driver (no live Neo4j needed)."""

from __future__ import annotations

import argparse
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

    # ------------------------------------------------------------------
    # WarmIndex Integration
    # ------------------------------------------------------------------


class TestWarmIndexIntegration:
    """WarmIndex with Neo4jGraphAdapter integration."""

    def test_warmindex_with_neo4j_backend(self) -> None:
        """Verify WarmIndex dispatches to Neo4j when graph_backend is provided."""
        from unittest.mock import MagicMock

        from adl_lite.memory import WarmIndex
        from adl_lite.models import (
            ADLDocument,
            ADLFrontMatter,
            ADLRelationBlock,
            ADLType,
            DiscoveryStatus,
            ProvisionalNames,
        )
        from adl_lite.neo4j_adapter import Neo4jGraphAdapter

        mock_backend = MagicMock(spec=Neo4jGraphAdapter)
        warm = WarmIndex(db_path=":memory:", graph_backend=mock_backend)

        # Verify no NetworkX graph initialized
        assert warm.graph is None
        assert warm.graph_backend is mock_backend

        # Insert a doc with relations
        doc = ADLDocument(
            front_matter=ADLFrontMatter(
                adl_type=ADLType.CONCEPT,
                adl_id="test-concept",
                status=DiscoveryStatus.VALIDATED,
                confidence=0.9,
                scope="public",
                provisional_names=ProvisionalNames(en="test-concept"),
            ),
            markdown_body="Test",
            adl_blocks=[],
        )
        warm.insert_document(doc)

        # Verify add_edge was NOT called (no relations in the doc)
        mock_backend.add_edge.assert_not_called()

        # Now test with a relation
        doc2 = ADLDocument(
            front_matter=ADLFrontMatter(
                adl_type=ADLType.CONCEPT,
                adl_id="test-rel",
                status=DiscoveryStatus.VALIDATED,
                confidence=0.9,
                scope="public",
                provisional_names=ProvisionalNames(en="test-rel"),
            ),
            markdown_body="Test with relations",
            adl_blocks=[
                ADLRelationBlock(
                    source="test-rel",
                    relation="related-to",
                    target="other-concept",
                    confidence=0.8,
                )
            ],
        )
        warm.insert_document(doc2)
        mock_backend.add_edge.assert_called_once_with(
            "test-rel", "other-concept", "related-to", 0.8
        )

    def test_warmindex_falls_back_to_networkx(self) -> None:
        """Verify WarmIndex uses NetworkX when no graph_backend is given."""
        from adl_lite.memory import HAS_NETWORKX, WarmIndex

        warm = WarmIndex()
        assert warm.graph_backend is None
        if HAS_NETWORKX:
            assert warm.graph is not None
        else:
            assert warm.graph is None

    def test_warmindex_get_related_dispatches_to_backend(self) -> None:
        """Verify get_related() calls graph_backend.bfs when configured."""
        from unittest.mock import MagicMock

        from adl_lite.memory import WarmIndex
        from adl_lite.neo4j_adapter import Neo4jGraphAdapter

        mock_backend = MagicMock(spec=Neo4jGraphAdapter)
        mock_backend.bfs.return_value = [
            ("related-cap", "related-to", 0.9),
        ]

        warm = WarmIndex(db_path=":memory:", graph_backend=mock_backend)

        results = warm.get_related("test-concept", depth=2)

        mock_backend.bfs.assert_called_once_with("test-concept", max_depth=2)
        assert results == [("related-cap", "related-to", 0.9)]


class TestCliNeo4jCommands:
    """Test neo4j CLI command name resolution."""

    @staticmethod
    def _find_subparser(
        parser: argparse.ArgumentParser, name: str
    ) -> argparse.ArgumentParser | None:
        """Find a subparser by name from an argparse parser."""
        sub = parser._subparsers
        if sub is None:
            return None
        for action in sub._actions:
            choices = getattr(action, "choices", None)
            if choices is not None and name in choices:
                result: object = choices[name]
                assert isinstance(result, argparse.ArgumentParser)
                return result
        return None

    def test_neo4j_subcommand_registered(self) -> None:
        """Verify the neo4j subcommand exists in argparse."""
        from adl_lite.cli import _build_parser

        parser = _build_parser()
        neo4j_parser = self._find_subparser(parser, "neo4j")
        assert neo4j_parser is not None, "neo4j subcommand not found"

    def test_neo4j_status_subcommand_registered(self) -> None:
        """Verify the neo4j status subcommand exists."""
        from adl_lite.cli import _build_parser

        parser = _build_parser()
        neo4j_parser = self._find_subparser(parser, "neo4j")
        assert neo4j_parser is not None, "neo4j subcommand not found"

        status_parser = self._find_subparser(neo4j_parser, "status")
        assert status_parser is not None, "neo4j status subcommand not found"

    def test_neo4j_rebuild_subcommand_registered(self) -> None:
        """Verify the neo4j rebuild subcommand exists."""
        from adl_lite.cli import _build_parser

        parser = _build_parser()
        neo4j_parser = self._find_subparser(parser, "neo4j")
        assert neo4j_parser is not None, "neo4j subcommand not found"

        rebuild_parser = self._find_subparser(neo4j_parser, "rebuild")
        assert rebuild_parser is not None, "neo4j rebuild subcommand not found"

    def test_neo4j_status_has_connection_args(self) -> None:
        """Verify neo4j status has --uri, --user, --password arguments."""
        from adl_lite.cli import _build_parser

        parser = _build_parser()
        neo4j_parser = self._find_subparser(parser, "neo4j")
        assert neo4j_parser is not None

        status_parser = self._find_subparser(neo4j_parser, "status")
        assert status_parser is not None

        # Verify expected args are present
        parsed = status_parser.parse_args(
            ["--uri", "bolt://test:7687", "--user", "u", "--password", "p"]
        )
        assert parsed.uri == "bolt://test:7687"
        assert parsed.user == "u"
        assert parsed.password == "p"

    def test_neo4j_rebuild_has_state_and_connection_args(self) -> None:
        """Verify neo4j rebuild has --state, --uri, --user, --password arguments."""
        from adl_lite.cli import _build_parser

        parser = _build_parser()
        neo4j_parser = self._find_subparser(parser, "neo4j")
        assert neo4j_parser is not None

        rebuild_parser = self._find_subparser(neo4j_parser, "rebuild")
        assert rebuild_parser is not None

        # Verify expected args are present
        parsed = rebuild_parser.parse_args(
            [
                "--state",
                "state.json",
                "--uri",
                "bolt://test:7687",
                "--user",
                "u",
                "--password",
                "p",
            ]
        )
        assert parsed.state == "state.json"
        assert parsed.uri == "bolt://test:7687"
        assert parsed.user == "u"
        assert parsed.password == "p"

    def test_neo4j_status_func_is_callable(self) -> None:
        """Verify the status subcommand has a callable func."""
        from adl_lite.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["neo4j", "status"])
        assert callable(args.func)

    def test_neo4j_rebuild_func_is_callable(self) -> None:
        """Verify the rebuild subcommand has a callable func."""
        from adl_lite.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["neo4j", "rebuild"])
        assert callable(args.func)
