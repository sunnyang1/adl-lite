"""
ADL Lite — Pluggable graph backend abstraction.

Defines a small :class:`GraphBackend` interface so that :class:`~adl_lite.memory.WarmIndex`
can be driven by different relation-graph stores (in-memory NetworkX, optional Neo4j,
or a raw SQLite BFS) behind a single, uniform API.

The BFS contract is intentionally identical across all backends:

    ``bfs(start, max_depth) -> list[(capability_id, relation, confidence)]``

so that results are comparable and the trust/query layers can swap backends without
changing call sites (see ``tests/test_neo4j_adapter.py`` for a cross-backend parity
test).

References:
    - ADL Lite PRD §5.1 / §5.2 (pluggable graph backend)
    - ADL Lite PRD §A1–A3 (Neo4j adapter + WarmIndex integration)
"""

from __future__ import annotations

import logging
import sqlite3
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger("adl_lite.graph_backends")

# Optional NetworkX dependency — gracefully degrade to a clear error only when the
# NetworkX adapter is actually instantiated.
try:
    import networkx as nx

    HAS_NETWORKX = True
except ImportError:  # pragma: no cover
    HAS_NETWORKX = False


# ---------------------------------------------------------------------------
# Abstract backend
# ---------------------------------------------------------------------------


class GraphBackend(ABC):
    """Uniform interface for relation-graph traversal backends.

    A backend stores directed edges ``(source, target, relation, confidence)`` and
    supports a bounded BFS returning ``(capability_id, relation, confidence)``
    triples.  Implementations: :class:`NetworkXGraphAdapter`,
    :class:`SQLGraphAdapter`, and :class:`~adl_lite.neo4j_adapter.Neo4jGraphAdapter`.
    """

    @abstractmethod
    def add_edge(self, source: str, target: str, relation: str, confidence: float = 1.0) -> None:
        """Add a directed edge *source* → *target* with *relation* and *confidence*."""

    @abstractmethod
    def bfs(self, start_node: str, max_depth: int = 1) -> list[tuple[str, str, float]]:
        """Bounded BFS from *start_node* returning ``(capability, relation, confidence)``."""

    @abstractmethod
    def __contains__(self, node_id: str) -> bool:
        """Return True if *node_id* exists in the graph."""

    @abstractmethod
    def node_count(self) -> int:
        """Return the total number of distinct nodes in the graph."""

    @abstractmethod
    def close(self) -> None:
        """Release any resources held by the backend."""


# ---------------------------------------------------------------------------
# NetworkX adapter (in-memory, default WarmIndex backend)
# ---------------------------------------------------------------------------


class NetworkXGraphAdapter(GraphBackend):
    """NetworkX ``DiGraph`` implementation of :class:`GraphBackend`.

    This mirrors the BFS semantics historically used by
    :meth:`~adl_lite.memory.WarmIndex._graph_bfs` so that results are identical to
    the legacy NetworkX code path and comparable to the Neo4j backend.
    """

    def __init__(self, graph: Any | None = None) -> None:
        if not HAS_NETWORKX:  # pragma: no cover
            raise ImportError(
                "NetworkX support requires the 'networkx' dependency. "
                "Install with: pip install networkx"
            )
        # ``graph`` may be a networkx.DiGraph or None (a fresh graph is created).
        self.graph = graph if graph is not None else nx.DiGraph()

    def add_edge(self, source: str, target: str, relation: str, confidence: float = 1.0) -> None:
        self.graph.add_edge(source, target, relation=relation, confidence=confidence)

    def bfs(self, start_node: str, max_depth: int = 1) -> list[tuple[str, str, float]]:
        if max_depth < 0 or start_node not in self.graph:
            return []

        results: list[tuple[str, str, float]] = []
        visited = {start_node}
        queue: list[tuple[str, int]] = [(start_node, 0)]

        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            for neighbor in self.graph.successors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    edge = self.graph.edges[current, neighbor]
                    results.append(
                        (
                            neighbor,
                            edge.get("relation", "related-to"),
                            float(edge.get("confidence", 1.0)),
                        )
                    )
                    queue.append((neighbor, depth + 1))
        return results

    def __contains__(self, node_id: str) -> bool:
        return node_id in self.graph

    def node_count(self) -> int:
        return int(self.graph.number_of_nodes())

    def close(self) -> None:
        # NetworkX graphs are in-memory; nothing to release.
        return None


# ---------------------------------------------------------------------------
# SQLite adapter (raw relations table BFS — no extra dependency)
# ---------------------------------------------------------------------------


class SQLGraphAdapter(GraphBackend):
    """SQLite-backed :class:`GraphBackend` wrapping the ``relations`` table.

    Useful as a dependency-free persistence backend and as a regression baseline
    for the NetworkX / Neo4j backends.  Edges are stored in a
    ``(source, predicate, target, confidence)`` table; BFS is performed with
    iterative SQL ``UNION`` queries over both directions.
    """

    def __init__(self, conn: sqlite3.Connection | None = None, db_path: str = ":memory:") -> None:
        if conn is None:
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.execute("PRAGMA busy_timeout=5000")
            self._owns = True
        else:
            self._owns = False
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                source      TEXT NOT NULL,
                predicate   TEXT NOT NULL,
                target      TEXT NOT NULL,
                confidence  REAL DEFAULT 1.0,
                UNIQUE(source, predicate, target)
            )
            """
        )
        self.conn.commit()

    def add_edge(self, source: str, target: str, relation: str, confidence: float = 1.0) -> None:
        self.conn.execute(
            """
            INSERT OR IGNORE INTO relations (source, predicate, target, confidence)
            VALUES (?, ?, ?, ?)
            """,
            (source, target, relation, confidence),
        )
        self.conn.commit()

    def bfs(self, start_node: str, max_depth: int = 1) -> list[tuple[str, str, float]]:
        if max_depth < 0:
            return []

        results: list[tuple[str, str, float]] = []
        visited = {start_node}
        current_level = {start_node}

        for _ in range(max_depth):
            if not current_level:
                break
            placeholders = ",".join("?" * len(current_level))
            rows = self.conn.execute(
                f"""
                SELECT target AS concept, predicate, confidence FROM relations
                WHERE source IN ({placeholders})
                UNION
                SELECT source AS concept, predicate, confidence FROM relations
                WHERE target IN ({placeholders})
                """,
                list(current_level) * 2,
            ).fetchall()

            next_level: set[str] = set()
            for row in rows:
                cid = row["concept"]
                if cid not in visited:
                    visited.add(cid)
                    next_level.add(cid)
                    results.append((cid, row["predicate"], float(row["confidence"])))
            current_level = next_level

        return results

    def __contains__(self, node_id: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM relations WHERE source=? OR target=? LIMIT 1",
            (node_id, node_id),
        ).fetchone()
        return row is not None

    def node_count(self) -> int:
        row = self.conn.execute(
            """
            SELECT COUNT(DISTINCT node) AS cnt FROM (
                SELECT source AS node FROM relations
                UNION
                SELECT target AS node FROM relations
            )
            """
        ).fetchone()
        return int(row["cnt"]) if row else 0

    def close(self) -> None:
        if self._owns:
            self.conn.close()
