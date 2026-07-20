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

import logging
from typing import Any

logger = logging.getLogger("adl_lite.neo4j_adapter")


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
        driver: Any = None,
    ) -> None:
        self._uri = uri
        self._user = user
        self._password = password
        self._database = database
        # Allow driver injection for testing / connection reuse. When ``driver`` is
        # provided it is used as-is; otherwise it is lazily created on first use.
        self._driver: Any = driver

    def _get_driver(self) -> Any:
        """Lazy-initialize the Neo4j driver."""
        if self._driver is None:
            try:
                from neo4j import GraphDatabase

                self._driver = GraphDatabase.driver(self._uri, auth=(self._user, self._password))
            except ImportError:
                raise ImportError(
                    "Neo4j support requires the 'neo4j' extra. "
                    "Install with: pip install adl-lite[neo4j]"
                ) from None
        return self._driver

    def verify_connectivity(self) -> bool:
        """Verify the Neo4j driver can reach the server.

        Returns True on success, False on any connectivity failure. If the
        ``neo4j`` driver library is not installed this raises ``ImportError``
        (graceful degradation is the caller's responsibility).
        """
        driver = self._get_driver()
        try:
            driver.verify_connectivity()
            return True
        except Exception:
            logger.exception("Neo4j connectivity verification failed")
            return False

    def add_edge(self, source: str, target: str, relation: str, confidence: float) -> None:
        """Add a directed edge from *source* to *target* with the given *relation* and *confidence*."""
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            session.run(
                """
                MERGE (s:ADLConcept {id: $source})
                MERGE (t:ADLConcept {id: $target})
                MERGE (s)-[r:RELATES {relation: $relation}]->(t)
                SET r.confidence = $confidence
                """,
                source=source,
                target=target,
                relation=relation,
                confidence=confidence,
            )

    def bfs(self, start_node: str, max_depth: int = 1) -> list[tuple[str, str, float]]:
        """BFS traversal returning (neighbor_id, relation, confidence) tuples."""
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            result = session.run(
                """
                MATCH (start:ADLConcept {id: $cid})
                MATCH path = (start)-[*1..$depth]->(other:ADLConcept)
                WHERE start <> other
                RETURN DISTINCT other.id AS node_id,
                       last(relationships(path)).relation AS relation,
                       last(relationships(path)).confidence AS confidence
                """,
                cid=start_node,
                depth=max_depth,
            )
            return [
                (record["node_id"], record["relation"], record["confidence"]) for record in result
            ]

    def __contains__(self, node_id: str) -> bool:
        """Check if a node exists in the graph."""
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            result = session.run(
                "MATCH (n:ADLConcept {id: $id}) RETURN count(n) AS cnt",
                id=node_id,
            )
            record = result.single()
            return record is not None and record["cnt"] > 0

    def node_count(self) -> int:
        """Return the total number of nodes in the graph."""
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            result = session.run("MATCH (n:ADLConcept) RETURN count(n) AS cnt")
            record = result.single()
            return record["cnt"] if record else 0

    def rebuild_from_relations(self, relations: list[dict]) -> int:
        """Rebuild the Neo4j graph from a list of relation dicts.

        Each dict: {"source": str, "predicate": str, "target": str, "confidence": float}
        Clears the graph first, then batch-creates all nodes and edges.
        Returns the number of edges created.
        """
        driver = self._get_driver()
        count = 0
        with driver.session(database=self._database) as session:
            # Clear existing graph
            session.run("MATCH (n:ADLConcept) DETACH DELETE n")
            # Create all edges
            for rel in relations:
                session.run(
                    """
                    MERGE (s:ADLConcept {id: $source})
                    MERGE (t:ADLConcept {id: $target})
                    MERGE (s)-[r:RELATES {relation: $predicate}]->(t)
                    SET r.confidence = $confidence
                    """,
                    source=rel["source"],
                    target=rel["target"],
                    predicate=rel["predicate"],
                    confidence=rel.get("confidence", 1.0),
                )
                count += 1
        return count

    def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
