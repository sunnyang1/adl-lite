"""
ADL Lite — Hybrid Memory Index

Three-tier storage architecture:
    Hot  : in-memory HashMap  (< 1 ms)  — ConceptSkeleton only
    Warm : SQLite + NetworkX  (5-20 ms) — full documents + relation graph
    Cold : file-backed archive (50-500 ms) — historical / large objects

Implements cascade filtering:
    100M concepts → status bitmap → 10M → type inverted index → 100K
    → namespace trie → 10K → vector ANN → 100 → graph traversal → result

References:
    - ADL Lite Spec §8.2: Concept Skeleton
    - ADL Lite Spec §8.3: Cascade Filtering
"""

from __future__ import annotations

import json
import sqlite3
import threading

from .models import ADLDocument, ADLRelationBlock, ConceptSkeleton, DiscoveryStatus

# Optional NetworkX — gracefully degrade if absent
try:
    import networkx as nx

    HAS_NETWORKX = True
except ImportError:  # pragma: no cover
    HAS_NETWORKX = False


# ---------------------------------------------------------------------------
# Hot Layer — In-Memory Skeleton Index
# ---------------------------------------------------------------------------


class HotIndex:
    """
    O(1) lookup for concept skeletons.
    Thread-safe via RLock.
    """

    def __init__(self) -> None:
        self._store: dict[str, ConceptSkeleton] = {}
        self._lock = threading.RLock()

    # CRUD

    def put(self, skeleton: ConceptSkeleton) -> None:
        with self._lock:
            self._store[skeleton.adl_id] = skeleton

    def get(self, adl_id: str) -> ConceptSkeleton | None:
        with self._lock:
            return self._store.get(adl_id)

    def remove(self, adl_id: str) -> None:
        with self._lock:
            self._store.pop(adl_id, None)

    def keys(self) -> set[str]:
        with self._lock:
            return set(self._store.keys())

    def filter(
        self,
        status: DiscoveryStatus | None = None,
        domain: str | None = None,
        scope_prefix: str | None = None,
    ) -> list[ConceptSkeleton]:
        """Fast pre-filter before hitting Warm layer."""
        with self._lock:
            results = list(self._store.values())

        if status:
            results = [s for s in results if s.status == status]
        if domain:
            results = [s for s in results if s.domain_tag == domain]
        if scope_prefix:
            results = [s for s in results if s.scope.startswith(scope_prefix)]

        return results

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)


# ---------------------------------------------------------------------------
# Warm Layer — SQLite + Relation Graph
# ---------------------------------------------------------------------------


class WarmIndex:
    """
    Persistent storage for full ADL documents and their relation graph.
    Uses SQLite for documents, NetworkX for graph (optional).
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS documents (
        adl_id      TEXT PRIMARY KEY,
        adl_type    TEXT NOT NULL,
        status      TEXT NOT NULL,
        scope       TEXT NOT NULL,
        domain      TEXT,
        confidence  REAL,
        novelty     REAL,
        created_at  TEXT,
        updated_at  TEXT,
        raw_json    TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS relations (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        source      TEXT NOT NULL,
        predicate   TEXT NOT NULL,
        target      TEXT NOT NULL,
        confidence  REAL DEFAULT 1.0,
        UNIQUE(source, predicate, target)
    );

    CREATE INDEX IF NOT EXISTS idx_doc_status ON documents(status);
    CREATE INDEX IF NOT EXISTS idx_doc_scope  ON documents(scope);
    CREATE INDEX IF NOT EXISTS idx_doc_domain ON documents(domain);
    CREATE INDEX IF NOT EXISTS idx_rel_src    ON relations(source);
    CREATE INDEX IF NOT EXISTS idx_rel_tgt    ON relations(target);
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(self.SCHEMA)
        self.conn.commit()

        # Relation graph (optional NetworkX)
        self.graph: nx.DiGraph | None = nx.DiGraph() if HAS_NETWORKX else None

    # Document storage

    def insert_document(self, doc: ADLDocument) -> None:
        with self._lock:
            fm = doc.front_matter
            self.conn.execute(
                """
                INSERT OR REPLACE INTO documents
                (adl_id, adl_type, status, scope, domain, confidence, novelty, created_at, updated_at, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fm.adl_id,
                    fm.adl_type.value,
                    fm.status.value,
                    fm.scope,
                    fm.domain,
                    fm.confidence,
                    fm.novelty,
                    fm.created_at,
                    fm.updated_at,
                    doc.model_dump_json(),
                ),
            )
            self.conn.commit()

            # Index relations into graph
            for rel in doc.relations:
                self._add_relation(rel)

    def get_document(self, adl_id: str) -> ADLDocument | None:
        with self._lock:
            row = self.conn.execute(
                "SELECT raw_json FROM documents WHERE adl_id = ?", (adl_id,)
            ).fetchone()
            if row is None:
                return None
            data = json.loads(row["raw_json"])
            return ADLDocument(**data)

    def delete_document(self, adl_id: str) -> None:
        with self._lock:
            self.conn.execute("DELETE FROM documents WHERE adl_id = ?", (adl_id,))
            self.conn.execute(
                "DELETE FROM relations WHERE source = ? OR target = ?", (adl_id, adl_id)
            )
            self.conn.commit()

            if self.graph and HAS_NETWORKX:
                if adl_id in self.graph:
                    self.graph.remove_node(adl_id)

    # Relation graph

    def _add_relation(self, rel: ADLRelationBlock) -> None:
        self.conn.execute(
            """
            INSERT OR IGNORE INTO relations (source, predicate, target, confidence)
            VALUES (?, ?, ?, ?)
            """,
            (rel.source, rel.relation, rel.target, rel.confidence),
        )
        self.conn.commit()

        if self.graph and HAS_NETWORKX:
            self.graph.add_edge(
                rel.source, rel.target, relation=rel.relation, confidence=rel.confidence
            )

    def get_related(self, concept_id: str, depth: int = 1) -> list[tuple[str, str, float]]:
        """
        BFS traversal of the relation graph. Thread-safe.
        Returns list of (related_concept, relation, confidence).
        """
        with self._lock:
            if self.graph and HAS_NETWORKX:
                return self._graph_bfs(concept_id, depth)
            return self._sql_bfs(concept_id, depth)

    def _graph_bfs(self, concept_id: str, depth: int) -> list[tuple[str, str, float]]:
        if not HAS_NETWORKX or self.graph is None:
            return []

        results: list[tuple[str, str, float]] = []
        visited = {concept_id}
        queue = [(concept_id, 0)]

        while queue:
            current, d = queue.pop(0)
            if d >= depth:
                continue

            for neighbor in self.graph.successors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    edge_data = self.graph.edges[current, neighbor]
                    results.append(
                        (
                            neighbor,
                            edge_data.get("relation", "related-to"),
                            edge_data.get("confidence", 1.0),
                        )
                    )
                    queue.append((neighbor, d + 1))

        return results

    def _sql_bfs(self, concept_id: str, depth: int) -> list[tuple[str, str, float]]:
        results: list[tuple[str, str, float]] = []
        visited = {concept_id}
        current_level = {concept_id}

        for _ in range(depth):
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

            next_level = set()
            for row in rows:
                cid = row["concept"]
                if cid not in visited:
                    visited.add(cid)
                    next_level.add(cid)
                    results.append((cid, row["predicate"], row["confidence"]))
            current_level = next_level

        return results

    # Cascade filtering queries

    def cascade_filter(
        self,
        status: DiscoveryStatus | None = None,
        domain: str | None = None,
        scope_prefix: str | None = None,
    ) -> list[str]:
        """
        Multi-stage pre-filtering returning candidate adl_ids. Thread-safe.
        Scope prefix is escaped to prevent LIKE wildcard injection.
        """
        conditions = []
        params: list = []

        if status:
            conditions.append("status = ?")
            params.append(status.value)
        if domain:
            conditions.append("domain = ?")
            params.append(domain)
        if scope_prefix:
            conditions.append("scope LIKE ? ESCAPE '\\'")
            # Escape LIKE wildcards: % → \%, _ → \_
            escaped = scope_prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            params.append(f"{escaped}%")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with self._lock:
            rows = self.conn.execute(
                f"SELECT adl_id FROM documents WHERE {where_clause}",
                params,
            ).fetchall()

        return [row["adl_id"] for row in rows]

    def close(self) -> None:
        self.conn.close()


# ---------------------------------------------------------------------------
# Unified Memory Interface
# ---------------------------------------------------------------------------


class ADLMemory:
    """
    Unified three-tier memory for ADL Lite.

    Usage:
        mem = ADLMemory(db_path="adl_memory.db")
        mem.store(doc)
        skeleton = mem.hot.get("disc-7f3a9b")
        doc = mem.warm.get_document("disc-7f3a9b")
        related = mem.warm.get_related("disc-7f3a9b", depth=2)
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.hot = HotIndex()
        self.warm = WarmIndex(db_path)

    def store(self, doc: ADLDocument) -> None:
        """Store a document in all tiers."""
        # Hot: skeleton only
        self.hot.put(doc.to_skeleton())
        # Warm: full document + relations
        self.warm.insert_document(doc)

    def retrieve(self, adl_id: str) -> ADLDocument | None:
        """Retrieve full document from Warm layer."""
        return self.warm.get_document(adl_id)

    def delete(self, adl_id: str) -> None:
        """Remove from all tiers."""
        self.hot.remove(adl_id)
        self.warm.delete_document(adl_id)

    def find_related(self, adl_id: str, depth: int = 1) -> list[tuple[str, str, float]]:
        """Graph traversal for related concepts."""
        return self.warm.get_related(adl_id, depth)

    def prefilter(
        self,
        status: DiscoveryStatus | None = None,
        domain: str | None = None,
        scope_prefix: str | None = None,
    ) -> list[ConceptSkeleton]:
        """
        Fast pre-filter using Hot layer.
        Falls back to Warm layer if Hot miss.
        """
        hot_results = self.hot.filter(status, domain, scope_prefix)
        if hot_results:
            return hot_results

        # Fallback: warm cascade
        ids = self.warm.cascade_filter(status, domain, scope_prefix)
        results: list[ConceptSkeleton] = []
        for i in ids:
            sk = self.hot.get(i)
            if sk is not None:
                results.append(sk)
        return results

    def close(self) -> None:
        self.hot.clear()
        self.warm.close()
