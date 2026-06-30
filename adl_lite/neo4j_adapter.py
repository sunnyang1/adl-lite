"""Neo4j graph adapter for ADL Lite WarmIndex.

Provides a Neo4j-backed graph backend that mirrors the NetworkX DiGraph interface
used by WarmIndex for relation graph traversal. Designed as a pluggable alternative
when concept counts exceed the WarmIndex NetworkX performance ceiling (~10k nodes).

Usage:
    from adl_lite.neo4j_adapter import Neo4jGraphAdapter

    adapter = Neo4jGraphAdapter(uri="bolt://localhost:7687", user="neo4j", password="...")
    adapter.add_edge("cap-a", "cap-b", "related-to", 0.9)
    results = adapter.bfs("cap-a", max_depth=2)
    adapter.close()
"""

from __future__ import annotations

from typing import Any


class Neo4jGraphAdapter:
    """Neo4j-backed graph backend for WarmIndex relation graph operations.

    Implements the same interface as the NetworkX DiGraph used by WarmIndex:
    - add_edge(source, target, relation, confidence)
    - bfs(start_node, max_depth) -> list[tuple[str, str, float]]
    - __contains__(node_id) -> bool
    - node_count() -> int
    - close()
    """

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password",
        database: str = "neo4j",
    ) -> None:
        self._uri = uri
        self._user = user
        self._password = password
        self._database = database
        self._driver: Any = None

    def _get_driver(self) -> Any:
        """Lazy-initialize the Neo4j driver."""
        if self._driver is None:
            from neo4j import GraphDatabase

            self._driver = GraphDatabase.driver(self._uri, auth=(self._user, self._password))
        return self._driver

    def add_edge(self, source: str, target: str, relation: str, confidence: float) -> None:
        """Add a directed edge from *source* to *target* with the given *relation* and *confidence*."""
        raise NotImplementedError  # T02 will implement

    def bfs(self, start_node: str, max_depth: int = 1) -> list[tuple[str, str, float]]:
        """BFS traversal returning (neighbor_id, relation, confidence) tuples."""
        raise NotImplementedError  # T02 will implement

    def __contains__(self, node_id: str) -> bool:
        """Check if a node exists in the graph."""
        raise NotImplementedError  # T02 will implement

    def node_count(self) -> int:
        """Return the total number of nodes in the graph."""
        raise NotImplementedError  # T02 will implement

    def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
