"""
ADL Lite — Hybrid Memory Index for Capability Registry

Three-tier storage architecture:
    Hot  : in-memory HashMap  (< 1 ms)  — ConceptSkeleton only
    Warm : SQLite + NetworkX  (5-20 ms) — full documents + relation graph
    Cold : file-backed archive (50-500 ms) — historical / large objects

Implements cascade filtering:
    100M capabilities → status bitmap → 10M → type inverted index → 100K
    → namespace trie → 10K → vector ANN → 100 → graph traversal → result

References:
    - ADL Lite Spec §8.2: Capability Skeleton
    - ADL Lite Spec §8.3: Cascade Filtering
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .cold_storage import ColdStorage

if TYPE_CHECKING:
    from .vector_index import VectorIndex
from .exceptions import ADLMemoryError
from .models import (
    ADLDocument,
    ADLRelationBlock,
    ConceptSkeleton,
    DiscoveryStatus,
    Event,
    EventChain,
    EventType,
)

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
    O(1) lookup for capability skeletons.
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

    CREATE TABLE IF NOT EXISTS events (
        event_id         TEXT PRIMARY KEY,
        concept_id       TEXT NOT NULL,
        event_type       TEXT NOT NULL,
        actor            TEXT,
        reasoning        TEXT,
        timestamp        TEXT,
        previous_event_id TEXT,
        prev_hash        TEXT,
        hash             TEXT,
        payload_json     TEXT,
        synthetic        INTEGER DEFAULT 0
    );

    CREATE INDEX IF NOT EXISTS idx_doc_status ON documents(status);
    CREATE INDEX IF NOT EXISTS idx_doc_scope  ON documents(scope);
    CREATE INDEX IF NOT EXISTS idx_doc_domain ON documents(domain);
    CREATE INDEX IF NOT EXISTS idx_rel_src    ON relations(source);
    CREATE INDEX IF NOT EXISTS idx_rel_tgt    ON relations(target);
    CREATE INDEX IF NOT EXISTS idx_events_concept ON events(concept_id);
    CREATE INDEX IF NOT EXISTS idx_events_concept_seq ON events(concept_id, timestamp);
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
            self.conn.execute("DELETE FROM events WHERE concept_id = ?", (adl_id,))
            self.conn.commit()

            if self.graph and HAS_NETWORKX:
                if adl_id in self.graph:
                    self.graph.remove_node(adl_id)

    # ------------------------------------------------------------------
    # Event storage (append-only audit log)
    # ------------------------------------------------------------------

    def _store_events(self, chain: EventChain) -> None:
        """Persist every event in an EventChain. Thread-safe."""
        with self._lock:
            for event in chain.events:
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO events
                    (event_id, concept_id, event_type, actor, reasoning,
                     timestamp, previous_event_id, prev_hash, hash,
                     payload_json, synthetic)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.concept_id,
                        event.event_type.value,
                        event.actor,
                        event.reasoning,
                        event.timestamp,
                        event.previous_event_id,
                        event._prev_hash,
                        event.hash,
                        json.dumps(event.payload, default=str),
                        1 if event.payload.get("synthetic", False) else 0,
                    ),
                )
            self.conn.commit()

    def load_event_chain(self, concept_id: str) -> EventChain | None:
        """Reconstruct an EventChain from the events table. Thread-safe."""
        with self._lock:
            rows = self.conn.execute(
                """
                SELECT event_id, event_type, actor, reasoning, timestamp,
                       previous_event_id, prev_hash, hash, payload_json, synthetic
                FROM events
                WHERE concept_id = ?
                ORDER BY timestamp ASC
                """,
                (concept_id,),
            ).fetchall()

        if not rows:
            return None

        chain = EventChain(concept_id=concept_id)
        for row in rows:
            event = Event(
                event_id=row["event_id"],
                concept_id=concept_id,
                event_type=EventType(row["event_type"]),
                actor=row["actor"] or "system",
                reasoning=row["reasoning"] or "",
                timestamp=row["timestamp"],
                previous_event_id=row["previous_event_id"],
                hash=row["hash"] or "",
                payload=json.loads(row["payload_json"]) if row["payload_json"] else {},
            )
            # Restore prev_hash (PrivateAttr) manually
            object.__setattr__(event, "_prev_hash", row["prev_hash"] or "")
            chain.append(event)

        return chain

    def get_history(self, concept_id: str) -> list[dict]:
        """Return full event history as plain dicts. Thread-safe."""
        chain = self.load_event_chain(concept_id)
        if chain is None:
            return []
        return chain.history()

    def get_version_at(self, concept_id: str, timestamp: str) -> ADLDocument | None:
        """
        Reconstruct the document state as it existed *at or before* the
        given ISO timestamp by replaying events up to that point.
        """
        chain = self.load_event_chain(concept_id)
        if chain is None:
            return None

        # Filter events up to the cutoff timestamp
        cutoff_events = [e for e in chain.events if e.timestamp <= timestamp]
        if not cutoff_events:
            return None

        replay = EventChain(concept_id=concept_id)
        for e in cutoff_events:
            replay.append(e)

        # Derive front matter from replayed chain
        from .models import ADLFrontMatter, ADLType

        # We need identity fields to rebuild front matter; fall back to
        # the latest stored document snapshot for identity constants.
        latest_doc = self.get_document(concept_id)
        identity = (
            latest_doc.front_matter.identity_dict()
            if latest_doc
            else {"scope": "public", "domain": ""}
        )

        # Determine adl_type from first snapshot event or default to CONCEPT
        adl_type = ADLType.CONCEPT
        for e in replay.events:
            if e.event_type == EventType.SNAPSHOT and "adl_type" in e.payload:
                adl_type = ADLType(e.payload["adl_type"])
                break

        fm = ADLFrontMatter.from_chain(replay, adl_type, identity)
        return ADLDocument(front_matter=fm)

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
        Returns list of (related_capability, relation, confidence).
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

    Hot  : in-memory skeleton index
    Warm : SQLite full documents + relation graph
    Cold : file-backed compressed archive (zstd+msgpack) for large chains

    Usage:
        mem = ADLMemory(db_path="adl_memory.db")
        mem.store(doc)
        skeleton = mem.hot.get("disc-7f3a9b")
        doc = mem.warm.get_document("disc-7f3a9b")
        related = mem.warm.get_related("disc-7f3a9b", depth=2)
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        tenant_id: str | None = None,
        cold_threshold: int | None = 100_000,
        cold_base_dir: str | Path | None = None,
        vector_index: VectorIndex | None = None,
    ) -> None:
        self.hot = HotIndex()
        self.warm = WarmIndex(db_path)
        self.tenant_id = tenant_id
        self.cold_threshold = cold_threshold
        self.cold = ColdStorage(cold_base_dir) if cold_base_dir else ColdStorage()
        self.vector_index = vector_index

    def _index_vector(self, doc: ADLDocument) -> None:
        """Add the document's semantic text to the optional vector index."""
        if self.vector_index is None:
            return
        try:
            from .near_duplicate import _extract_embedding_text

            text = _extract_embedding_text(doc)
            if text:
                self.vector_index.add(doc.adl_id, text)
        except Exception:
            # Vector indexing is best-effort; document storage must not fail.
            pass

    def store(self, doc: ADLDocument) -> None:
        """Store a document in all tiers."""
        # Attach tenant_id if set
        if self.tenant_id is not None and not hasattr(doc, "_tenant_id"):
            object.__setattr__(doc, "_tenant_id", self.tenant_id)
        # Hot: skeleton only
        self.hot.put(doc.to_skeleton())
        # Warm: full document + relations
        self.warm.insert_document(doc)
        # Vector tier (optional)
        self._index_vector(doc)

    def _maybe_archive(self, doc: ADLDocument, chain: EventChain) -> bool:
        """Archive *chain* to cold storage if it exceeds the configured threshold.

        Falls back to uncompressed JSONL if compressed zstd+msgpack is unavailable.
        Returns True if an archive was performed.
        """
        if not self.cold_threshold or len(chain) <= self.cold_threshold:
            return False

        try:
            archive_event = self.cold.archive(chain, keep_last_n=10, compressed=True)
        except ImportError:
            # Scale extras missing — fall back to standard-library JSONL archive.
            archive_event = self.cold.archive(chain, keep_last_n=10, compressed=False)

        if archive_event is not None:
            doc.refresh_snapshot(chain)
            return True
        return False

    def store_with_events(self, doc: ADLDocument) -> None:
        """Store document snapshot *and* its full event chain for audit."""
        if self.tenant_id is not None and not hasattr(doc, "_tenant_id"):
            object.__setattr__(doc, "_tenant_id", self.tenant_id)
        chain = doc.event_chain
        self._maybe_archive(doc, chain)
        self.hot.put(doc.to_skeleton())
        self.warm.insert_document(doc)
        self.warm._store_events(chain)
        # Vector tier (optional)
        self._index_vector(doc)

    def _load_hot_events_raw(self, concept_id: str) -> list[Event]:
        """Load the hot events from Warm storage without re-linking hashes."""
        rows = self.warm.conn.execute(
            """
            SELECT event_id, event_type, actor, reasoning, timestamp,
                   previous_event_id, prev_hash, hash, payload_json
            FROM events
            WHERE concept_id = ?
            ORDER BY timestamp ASC
            """,
            (concept_id,),
        ).fetchall()

        events: list[Event] = []
        for row in rows:
            event = Event(
                event_id=row["event_id"],
                concept_id=concept_id,
                event_type=EventType(row["event_type"]),
                actor=row["actor"] or "system",
                reasoning=row["reasoning"] or "",
                timestamp=row["timestamp"],
                previous_event_id=row["previous_event_id"],
                hash=row["hash"] or "",
                payload=json.loads(row["payload_json"]) if row["payload_json"] else {},
            )
            object.__setattr__(event, "_prev_hash", row["prev_hash"] or "")
            events.append(event)
        return events

    def retrieve_chain(self, adl_id: str) -> EventChain | None:
        """Retrieve the full event chain, merging Warm hot events with Cold archive."""
        hot_events = self._load_hot_events_raw(adl_id)
        if not hot_events:
            return None

        try:
            archived = self.cold.unarchive(adl_id)
        except FileNotFoundError:
            archived = []

        if not archived:
            chain = EventChain(concept_id=adl_id)
            with chain._events_lock:
                chain._events = list(hot_events)
                chain._invalidate_caches()
                chain._rebuild_crdt_caches()
            return chain

        # Reconstruct full chronological order:
        # genesis + archived middle + hot tail (which ends with the ARCHIVE event)
        full_events = [hot_events[0]] + archived + hot_events[1:]
        chain = EventChain(concept_id=adl_id)
        with chain._events_lock:
            chain._events = full_events
            chain._invalidate_caches()
            chain._rebuild_crdt_caches()
        return chain

    def history(self, adl_id: str) -> list[dict]:
        """Return full event history for a capability."""
        return self.warm.get_history(adl_id)

    def version_at(self, adl_id: str, timestamp: str) -> ADLDocument | None:
        """Reconstruct document state at a specific point in time."""
        return self.warm.get_version_at(adl_id, timestamp)

    def retrieve(self, adl_id: str) -> ADLDocument | None:
        """Retrieve full document from Warm layer."""
        return self.warm.get_document(adl_id)

    def delete(self, adl_id: str) -> None:
        """Remove from all tiers."""
        self.hot.remove(adl_id)
        self.warm.delete_document(adl_id)
        if self.vector_index is not None:
            try:
                self.vector_index.delete(adl_id)
            except Exception:
                pass

    def find_related(self, adl_id: str, depth: int = 1) -> list[tuple[str, str, float]]:
        """Graph traversal for related capabilities."""
        return self.warm.get_related(adl_id, depth)

    def prefilter(
        self,
        status: DiscoveryStatus | None = None,
        domain: str | None = None,
        scope_prefix: str | None = None,
        tenant_id: str | None = None,
    ) -> list[ConceptSkeleton]:
        """
        Fast pre-filter using Hot layer.
        Falls back to Warm layer if Hot miss.

        When `tenant_id` is provided (or set on the ADLMemory instance),
        results are filtered to only include documents belonging to that tenant.
        """
        effective_tenant = tenant_id or self.tenant_id

        hot_results = self.hot.filter(status, domain, scope_prefix)
        if hot_results:
            if effective_tenant is not None:
                hot_results = [
                    s for s in hot_results if getattr(s, "tenant_id", None) == effective_tenant
                ]
            return hot_results

        # Fallback: warm cascade
        ids = self.warm.cascade_filter(status, domain, scope_prefix)
        results: list[ConceptSkeleton] = []
        for i in ids:
            sk = self.hot.get(i)
            if sk is not None:
                if (
                    effective_tenant is not None
                    and getattr(sk, "tenant_id", None) != effective_tenant
                ):
                    continue
                results.append(sk)
        return results

    def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        threshold: float | None = None,
        status: DiscoveryStatus | None = None,
        domain: str | None = None,
        scope_prefix: str | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search over the vector index with optional pre-filtering.

        Returns a list of dicts sorted by similarity descending:
        ``{"adl_id": str, "similarity": float, "text": str}``.
        """
        if self.vector_index is None:
            raise ADLMemoryError(
                "VectorIndex is not configured. Create ADLMemory with vector_index=VectorIndex(...)"
            )

        prefilter_ids = None
        if status is not None or domain is not None or scope_prefix is not None:
            skeletons = self.prefilter(status, domain, scope_prefix)
            prefilter_ids = {s.adl_id for s in skeletons}

        return self.vector_index.search(
            query, top_k=top_k, threshold=threshold, prefilter_ids=prefilter_ids
        )

    def close(self) -> None:
        self.hot.clear()
        self.warm.close()
        if self.vector_index is not None:
            try:
                self.vector_index.save()
            except Exception:
                pass
            try:
                self.vector_index.close()
            except Exception:
                pass
