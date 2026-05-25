"""
Local mapping: ADL concept id ↔ Feishu document id (for pull/sync later).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class LarkRegistry:
    """JSON file registry: adl_id -> {doc_id, doc_url, ...}."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "entries": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def record_publish(
        self,
        adl_id: str,
        *,
        doc_id: str,
        doc_url: str,
        source_path: str,
        title: str,
    ) -> None:
        data = self.load()
        entries = data.setdefault("entries", {})
        entries[adl_id] = {
            "adl_id": adl_id,
            "doc_id": doc_id,
            "doc_url": doc_url,
            "title": title,
            "source_path": source_path,
            "published_at": _utc_now(),
        }
        self.save(data)

    def get(self, adl_id: str) -> dict[str, Any] | None:
        return self.load().get("entries", {}).get(adl_id)

    def set_base_token(self, name: str, base_token: str) -> None:
        data = self.load()
        bases = data.setdefault("bases", {})
        bases[name] = base_token
        self.save(data)

    def get_base_token(self, name: str) -> str | None:
        return self.load().get("bases", {}).get(name)

    def set_namespace(self, adl_uri: str, wiki_space: str) -> None:
        data = self.load()
        ns = data.setdefault("namespaces", {})
        uri = adl_uri if adl_uri.endswith("/") else f"{adl_uri}/"
        ns[uri] = wiki_space
        self.save(data)

    def list_namespaces(self) -> dict[str, str]:
        return dict(self.load().get("namespaces", {}))
