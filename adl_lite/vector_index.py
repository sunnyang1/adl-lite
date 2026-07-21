"""FAISS-backed vector index for ADL Lite semantic search.

The index stores embedding vectors alongside concept metadata in SQLite and
uses FAISS for approximate nearest-neighbour search. It is designed to be
optional: ADL Lite works without it, and it is only instantiated when the
`[embeddings]` extra is installed.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tempfile
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .logging_config import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    # numpy is an optional dependency (pulled in by the [embeddings] extra).
    # It is imported lazily inside the methods that need it so that
    # ``import adl_lite`` works in a bare (core-deps-only) installation.
    import numpy as np

    from .embeddings import EmbeddingBackend


def _require_faiss() -> Any:
    try:
        import faiss
    except ImportError as exc:
        raise ImportError(
            'faiss-cpu is required for VectorIndex. Install it with: pip install -e ".[embeddings]"'
        ) from exc
    return faiss


def _l2_normalize(vectors: np.ndarray) -> np.ndarray:
    """L2-normalize vectors in-place (returns the same array)."""
    faiss = _require_faiss()
    faiss.normalize_L2(vectors)
    return vectors


class VectorIndex:
    """Persistent FAISS vector index with SQLite metadata.

    Args:
        backend: EmbeddingBackend instance. If None, uses the default backend.
        db_path: Path to SQLite metadata store. ``:memory:`` is supported.
            For on-disk persistence, both ``db_path`` and ``index_dir`` must
            be kept together. ``save()`` writes ``index.faiss`` + ``meta.json``
            to ``index_dir`` and copies the SQLite file there as well.
        index_dir: Directory for FAISS index files. If None, uses the same
            directory as ``db_path`` (or a temporary location for ``:memory:``).
        normalize: Whether to L2-normalize vectors so that inner product equals
            cosine similarity.
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS vectors (
        adl_id      TEXT PRIMARY KEY,
        text        TEXT NOT NULL,
        text_hash   TEXT NOT NULL,
        model_name  TEXT NOT NULL,
        vector_idx  INTEGER NOT NULL,
        deleted     INTEGER DEFAULT 0
    );
    CREATE INDEX IF NOT EXISTS idx_vectors_deleted ON vectors(deleted);
    CREATE TABLE IF NOT EXISTS vector_meta (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """

    def __init__(
        self,
        backend: EmbeddingBackend | None = None,
        db_path: str | Path = ":memory:",
        index_dir: str | Path | None = None,
        normalize: bool = True,
    ) -> None:
        self._backend = backend or self._default_backend()
        self._normalize = normalize
        self._db_path = str(db_path)
        self._index_dir = Path(index_dir) if index_dir else self._default_index_dir()
        self._index_dir.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self.conn.executescript(self.SCHEMA)
        self.conn.commit()

        self._dim = self._backend.embedding_dim
        faiss = _require_faiss()
        self._index: Any = faiss.IndexFlatIP(self._dim)
        self._deleted_count = 0
        self._total_count = 0
        self._lock = threading.RLock()

        self._rebuild_threshold_ratio = 0.1
        self._rebuild_threshold_abs = 100

    @staticmethod
    def _default_backend() -> EmbeddingBackend:
        from .embeddings import get_default_embedding_backend

        return get_default_embedding_backend()

    def _default_index_dir(self) -> Path:
        if self._db_path == ":memory:":
            return Path(tempfile.mkdtemp(prefix="adl_vector_"))
        return Path(self._db_path).parent / f"{Path(self._db_path).stem}_vectors"

    def _text_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _encode(self, texts: list[str]) -> np.ndarray:
        import numpy as np

        if not texts:
            return np.zeros((0, self._dim), dtype=np.float32)
        vectors = self._backend.encode(texts)
        if self._normalize:
            vectors = _l2_normalize(vectors)
        return vectors

    def _maybe_rebuild(self) -> None:
        if self._total_count == 0:
            return
        ratio = self._deleted_count / self._total_count
        if (
            self._deleted_count >= self._rebuild_threshold_abs
            and ratio >= self._rebuild_threshold_ratio
        ):
            self._rebuild()

    def _rebuild(self) -> None:
        """Rebuild the FAISS index, dropping deleted vectors."""
        rows = self.conn.execute(
            "SELECT adl_id, text, model_name, vector_idx FROM vectors WHERE deleted = 0"
        ).fetchall()
        if not rows:
            faiss = _require_faiss()
            self._index = faiss.IndexFlatIP(self._dim)
            self._deleted_count = 0
            self._total_count = 0
            return

        texts = [row[1] for row in rows]
        vectors = self._encode(texts)

        faiss = _require_faiss()
        self._index = faiss.IndexFlatIP(self._dim)
        self._index.add(vectors)

        # Update vector_idx mappings.
        for new_idx, row in enumerate(rows):
            self.conn.execute(
                "UPDATE vectors SET vector_idx = ? WHERE adl_id = ?",
                (new_idx, row[0]),
            )
        self.conn.commit()
        self._deleted_count = 0
        self._total_count = len(rows)

    def add(self, adl_id: str, text: str) -> None:
        """Add or update a concept's vector."""
        with self._lock:
            self._add_locked(adl_id, text)

    def _add_locked(self, adl_id: str, text: str) -> None:
        text_hash = self._text_hash(text)
        row = self.conn.execute(
            "SELECT text_hash, deleted, vector_idx FROM vectors WHERE adl_id = ?",
            (adl_id,),
        ).fetchone()

        if row is not None:
            existing_hash, deleted, _ = row
            if existing_hash == text_hash and not deleted:
                return
            # Mark old vector as deleted; new vector will be appended.
            self.conn.execute("UPDATE vectors SET deleted = 1 WHERE adl_id = ?", (adl_id,))
            self.conn.commit()
            self._deleted_count += 1

        vector = self._encode([text])
        self._index.add(vector)
        vector_idx = self._total_count
        self._total_count += 1

        self.conn.execute(
            """
            INSERT OR REPLACE INTO vectors
            (adl_id, text, text_hash, model_name, vector_idx, deleted)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (adl_id, text, text_hash, self._backend.model_name, vector_idx),
        )
        self.conn.commit()
        self._maybe_rebuild()

    def add_many(self, items: dict[str, str]) -> None:
        """Batch add/update concept vectors."""
        if not items:
            return
        with self._lock:
            self._add_many_locked(items)

    def _add_many_locked(self, items: dict[str, str]) -> None:
        # Determine which items are new or changed.
        to_encode: list[str] = []
        ids: list[str] = []
        for adl_id, text in items.items():
            text_hash = self._text_hash(text)
            row = self.conn.execute(
                "SELECT text_hash, deleted FROM vectors WHERE adl_id = ?",
                (adl_id,),
            ).fetchone()
            if row is not None and row[0] == text_hash and not row[1]:
                continue
            if row is not None:
                self.conn.execute("UPDATE vectors SET deleted = 1 WHERE adl_id = ?", (adl_id,))
                self._deleted_count += 1
            to_encode.append(text)
            ids.append(adl_id)

        if not to_encode:
            return

        vectors = self._encode(to_encode)
        self._index.add(vectors)

        for i, adl_id in enumerate(ids):
            text = items[adl_id]
            text_hash = self._text_hash(text)
            vector_idx = self._total_count + i
            self.conn.execute(
                """
                INSERT OR REPLACE INTO vectors
                (adl_id, text, text_hash, model_name, vector_idx, deleted)
                VALUES (?, ?, ?, ?, ?, 0)
                """,
                (adl_id, text, text_hash, self._backend.model_name, vector_idx),
            )
        self._total_count += len(ids)
        self.conn.commit()
        self._maybe_rebuild()

    def delete(self, adl_id: str) -> None:
        """Mark a concept's vector as deleted."""
        with self._lock:
            self._delete_locked(adl_id)

    def _delete_locked(self, adl_id: str) -> None:
        row = self.conn.execute(
            "SELECT deleted FROM vectors WHERE adl_id = ?", (adl_id,)
        ).fetchone()
        if row is not None and not row[0]:
            self.conn.execute("UPDATE vectors SET deleted = 1 WHERE adl_id = ?", (adl_id,))
            self.conn.commit()
            self._deleted_count += 1
            self._maybe_rebuild()

    def search(
        self,
        query: str,
        top_k: int = 10,
        threshold: float | None = None,
        prefilter_ids: set[str] | None = None,
    ) -> list[dict]:
        """Search the index for concepts similar to ``query``.

        Thread-safe: concurrent searches are serialized around the underlying
        FAISS index and SQLite connection.
        """
        with self._lock:
            return self._search_locked(query, top_k, threshold, prefilter_ids)

    def _search_locked(
        self,
        query: str,
        top_k: int = 10,
        threshold: float | None = None,
        prefilter_ids: set[str] | None = None,
    ) -> list[dict]:
        """Search the index for concepts similar to ``query``.

        Returns a list of dicts sorted by similarity descending:
        ``{"adl_id": str, "similarity": float, "text": str}``.
        """
        import numpy as np

        query_vector = self._encode([query])
        distances, indices = self._index.search(
            query_vector, min(top_k * 4 + 10, self._total_count or 1)
        )
        distances = np.asarray(distances[0], dtype=np.float32)
        indices = np.asarray(indices[0], dtype=np.int64)

        # Resolve vector_idx -> adl_id, filtering deleted rows.
        results: list[dict] = []
        seen: set[str] = set()
        for idx, dist in zip(indices, distances, strict=False):
            if idx < 0:
                continue
            row = self.conn.execute(
                """
                SELECT adl_id, text, deleted FROM vectors
                WHERE vector_idx = ? AND deleted = 0
                """,
                (int(idx),),
            ).fetchone()
            if row is None:
                continue
            adl_id, text, _ = row
            if adl_id in seen:
                continue
            if prefilter_ids is not None and adl_id not in prefilter_ids:
                continue
            similarity = float(dist)
            if threshold is not None and similarity < threshold:
                continue
            results.append({"adl_id": adl_id, "similarity": round(similarity, 4), "text": text})
            seen.add(adl_id)
            if len(results) >= top_k:
                break

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def close(self) -> None:
        """Close the SQLite connection and release the lock."""
        try:
            self.conn.close()
        except Exception:
            logger.warning("Failed to close VectorIndex SQLite connection", exc_info=True)

    def save(self) -> None:
        """Persist the FAISS index, metadata, and a SQLite backup to disk."""
        with self._lock:
            self._save_locked()

    def _save_locked(self) -> None:
        faiss = _require_faiss()
        self._index_dir.mkdir(parents=True, exist_ok=True)
        index_path = self._index_dir / "index.faiss"
        faiss.write_index(self._index, str(index_path))
        meta = {
            "dim": self._dim,
            "model_name": self._backend.model_name,
            "normalize": self._normalize,
            "total_count": self._total_count,
            "deleted_count": self._deleted_count,
        }
        (self._index_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

        # Keep a SQLite backup alongside the FAISS index so the index can be
        # relocated without losing id→text mappings.
        if self._db_path != ":memory:":
            shutil.copy2(self._db_path, self._index_dir / "vectors.db")

    @classmethod
    def load(
        cls,
        backend: EmbeddingBackend | None = None,
        db_path: str | Path = ":memory:",
        index_dir: str | Path | None = None,
    ) -> VectorIndex:
        """Load a previously saved VectorIndex."""
        instance = cls(backend=backend, db_path=db_path, index_dir=index_dir)
        with instance._lock:
            faiss = _require_faiss()
            index_path = Path(instance._index_dir) / "index.faiss"
            meta_path = Path(instance._index_dir) / "meta.json"

            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if instance._backend.model_name != meta.get("model_name"):
                    raise ValueError(
                        f"Embedding model mismatch: index={meta.get('model_name')}, "
                        f"backend={instance._backend.model_name}"
                    )
                if instance._dim != meta.get("dim"):
                    raise ValueError(
                        f"Embedding dimension mismatch: index={meta.get('dim')}, "
                        f"backend={instance._dim}"
                    )

            # If the caller asked for an in-memory db but a saved SQLite backup
            # exists, restore it into a temporary file so metadata is available.
            if instance._db_path == ":memory:":
                backup_db = instance._index_dir / "vectors.db"
                if backup_db.exists():
                    tmp_db = Path(tempfile.mktemp(suffix=".db"))
                    shutil.copy2(str(backup_db), str(tmp_db))
                    instance.conn.close()
                    instance._db_path = str(tmp_db)
                    instance.conn = sqlite3.connect(instance._db_path, check_same_thread=False)

            if index_path.exists():
                instance._index = faiss.read_index(str(index_path))
        return instance
