"""Pure-Python TF-IDF for Phase B retrieval (no sklearn dependency)."""

from __future__ import annotations

import math
import re
from collections import Counter


def _tokenize(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"[a-zA-Z0-9\u4e00-\u9fff]+", text) if len(w) > 1]


class TfidfIndex:
    """Minimal TF-IDF index over document id -> text."""

    def __init__(self) -> None:
        self._docs: dict[str, str] = {}
        self._df: Counter[str] = Counter()
        self._n = 0

    def add(self, doc_id: str, text: str) -> None:
        self._docs[doc_id] = text
        tokens = set(_tokenize(text))
        self._df.update(tokens)
        self._n += 1

    def score(self, query: str, doc_id: str) -> float:
        if doc_id not in self._docs:
            return 0.0
        q_tokens = _tokenize(query)
        if not q_tokens:
            return 0.0
        doc_tokens = _tokenize(self._docs[doc_id])
        tf = Counter(doc_tokens)
        doc_len = max(len(doc_tokens), 1)
        total = 0.0
        for qt in q_tokens:
            if qt not in tf:
                continue
            idf = math.log((1 + self._n) / (1 + self._df.get(qt, 0))) + 1.0
            total += (tf[qt] / doc_len) * idf
        return total / len(q_tokens)

    def rank(self, query: str, k: int = 10) -> list[tuple[str, float]]:
        scored = [(doc_id, self.score(query, doc_id)) for doc_id in self._docs]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]
