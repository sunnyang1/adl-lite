"""
ADL Lite — Core ontology registry (Path A, Milestone 2a).

Loads adl_core_ontology.yaml and exposes predicate / transition / scope queries
for validator integration and future agent introspection (2c).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_ONTOLOGY_PATH = Path(__file__).resolve().parent / "adl_core_ontology.yaml"


class OntologyManager:
    """Load and query the ADL core ontology YAML registry."""

    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path else _DEFAULT_ONTOLOGY_PATH
        self._data: dict[str, Any] = self._load(self._path)

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        if not path.is_file():
            raise FileNotFoundError(f"Core ontology not found: {path}")
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            raise ValueError(f"Invalid ontology YAML (expected mapping): {path}")
        return data

    @property
    def path(self) -> Path:
        return self._path

    @property
    def version(self) -> str:
        return str(self._data.get("version", ""))

    def list_predicates(self) -> list[str]:
        predicates = self._data.get("predicates", {})
        return sorted(predicates.keys())

    def allowed_transitions(self, status: str) -> list[str]:
        graph = self._data.get("status_transitions", {})
        targets = graph.get(status, [])
        return list(targets)

    def is_valid_transition(self, from_status: str, to_status: str) -> bool:
        return to_status in self.allowed_transitions(from_status)

    def status_transition_graph(self) -> dict[str, list[str]]:
        graph = self._data.get("status_transitions", {})
        return {status: list(targets) for status, targets in graph.items()}

    def allowed_mapping_types(self, predicate: str) -> list[str]:
        predicates = self._data.get("predicates", {})
        entry = predicates.get(predicate, {})
        return list(entry.get("allowed_mapping_types", []))

    def validate_mapping_type(self, predicate: str, mapping_type: str | None) -> bool:
        if mapping_type is None:
            return False
        allowed = self.allowed_mapping_types(predicate)
        if not allowed:
            return True
        return mapping_type in allowed

    def scope_prefixes(self) -> list[str]:
        scopes = self._data.get("scopes", {})
        prefixes = scopes.get("prefixes", [])
        return list(prefixes)

    def validate_predicate(self, name: str) -> bool:
        predicates = self._data.get("predicates", {})
        return name in predicates

    def list_classes(self) -> list[str]:
        classes = self._data.get("classes", {})
        return sorted(classes.keys())

    def list_mapping_types(self) -> list[str]:
        return list(self._data.get("mapping_types", []))

    def query_schema(
        self,
        predicate: str | None = None,
        from_status: str | None = None,
        to_status: str | None = None,
    ) -> dict[str, Any]:
        """JSON-serializable schema snapshot with optional filters (Milestone 2c)."""
        predicates = self.list_predicates()
        if predicate is not None:
            predicates = [predicate] if self.validate_predicate(predicate) else []

        transitions = self.status_transition_graph()
        if from_status is not None:
            transitions = {from_status: transitions.get(from_status, [])}

        result: dict[str, Any] = {
            "version": self.version,
            "path": str(self.path),
            "predicates": predicates,
            "allowed_transitions": transitions,
            "scope_prefixes": self.scope_prefixes(),
            "mapping_types": self.list_mapping_types(),
            "classes": self.list_classes(),
        }

        if predicate is not None:
            result["predicate_valid"] = self.validate_predicate(predicate)
            if self.validate_predicate(predicate):
                result["allowed_mapping_types"] = self.allowed_mapping_types(predicate)

        if from_status is not None and to_status is not None:
            result["is_valid_transition"] = self.is_valid_transition(from_status, to_status)

        return result


@lru_cache(maxsize=1)
def default_ontology() -> OntologyManager:
    """Shared OntologyManager for strict validation (loads once per process)."""
    return OntologyManager()
