"""
Wiki namespace mapping: ADL scope prefixes → Feishu wiki space ids.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def scope_to_adl_uri(scope: str) -> str:
    """Map ADL scope string to adl:// URI prefix for namespace lookup."""
    if scope == "public":
        return "adl://public/"
    if scope.startswith("private/"):
        return f"adl://private/{scope.split('/', 1)[1]}/"
    if scope.startswith("shared/"):
        return f"adl://shared/{scope.split('/', 1)[1]}/"
    if scope.startswith("user/"):
        return f"adl://user/{scope.split('/', 1)[1]}/"
    return f"adl://{scope}/"


class LarkNamespaceRegistry:
    """
    Scope → wiki_space mapping.

    Stored in ``.adl_lark_namespaces.json`` or a ``namespaces`` section inside
    the Lark publish registry JSON.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "namespaces": {}}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if "namespaces" in data:
            return data
        return {"version": 1, "namespaces": data}

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def list_mappings(self) -> dict[str, str]:
        return dict(self.load().get("namespaces", {}))

    def set_mapping(self, adl_uri: str, wiki_space: str) -> None:
        uri = adl_uri if adl_uri.endswith("/") else f"{adl_uri}/"
        data = self.load()
        ns = data.setdefault("namespaces", {})
        ns[uri] = wiki_space
        self.save(data)

    def remove_mapping(self, adl_uri: str) -> bool:
        uri = adl_uri if adl_uri.endswith("/") else f"{adl_uri}/"
        data = self.load()
        ns = data.get("namespaces", {})
        if uri in ns:
            del ns[uri]
            self.save(data)
            return True
        return False

    def resolve_wiki_space(self, scope: str) -> str | None:
        """Longest-prefix match on adl:// URIs."""
        uri = scope_to_adl_uri(scope)
        mappings = self.list_mappings()
        if not mappings:
            return None
        best: tuple[int, str] | None = None
        for prefix, wiki_space in mappings.items():
            norm = prefix if prefix.endswith("/") else f"{prefix}/"
            if uri.startswith(norm):
                length = len(norm)
                if best is None or length > best[0]:
                    best = (length, wiki_space)
        return best[1] if best else None


def namespaces_from_registry(registry_data: dict[str, Any]) -> dict[str, str]:
    """Read namespaces embedded in ``.adl_lark_registry.json``."""
    return dict(registry_data.get("namespaces", {}))


def resolve_wiki_space_for_scope(
    scope: str,
    *,
    namespaces_path: Path | None = None,
    registry_data: dict[str, Any] | None = None,
) -> str | None:
    """Resolve wiki space from standalone file and/or registry section."""
    mappings: dict[str, str] = {}
    if registry_data:
        mappings.update(namespaces_from_registry(registry_data))
    if namespaces_path and namespaces_path.exists():
        mappings.update(LarkNamespaceRegistry(namespaces_path).list_mappings())
    if not mappings:
        return None
    uri = scope_to_adl_uri(scope)
    best: tuple[int, str] | None = None
    for prefix, wiki_space in mappings.items():
        norm = prefix if prefix.endswith("/") else f"{prefix}/"
        if uri.startswith(norm):
            length = len(norm)
            if best is None or length > best[0]:
                best = (length, wiki_space)
    return best[1] if best else None
