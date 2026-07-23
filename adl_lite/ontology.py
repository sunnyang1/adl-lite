"""
ADL Lite — Core ontology registry for the capability-lifecycle model (Path A, Milestone 2a).

Loads adl_core_ontology.yaml and exposes predicate / transition / scope queries
for validator integration and future agent introspection (2c).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .exceptions import ADLOntologyError

_DEFAULT_ONTOLOGY_PATH = Path(__file__).resolve().parent / "adl_core_ontology.yaml"


class OntologyManager:
    """Load and query the ADL core ontology YAML registry for capability-lifecycle operations."""

    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path else _DEFAULT_ONTOLOGY_PATH
        self._data: dict[str, Any] = self._load(self._path)

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        if not path.is_file():
            raise ADLOntologyError(f"Core ontology not found: {path}")
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            raise ADLOntologyError(f"Invalid ontology YAML (expected mapping): {path}")
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

    def list_actions(self) -> list[str]:
        """All action names registered in the ontology."""
        actions = self._data.get("actions", {})
        return sorted(actions.keys())

    def get_action_def(self, name: str) -> dict[str, Any] | None:
        """Raw action definition dict from the ontology."""
        actions: dict[str, Any] = self._data.get("actions", {})
        return actions.get(name)

    def min_distinct_validators(self) -> int:
        """Minimum distinct validators required for a VALIDATE transition."""
        cfg = self._data.get("collusion_resistance", {})
        value = cfg.get("min_distinct_validators", 1)
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return 1

    # ------------------------------------------------------------------
    # Execution Attestation Layer (EAL) policy accessors
    # ------------------------------------------------------------------

    def attestation_policy(self) -> dict[str, Any]:
        """Raw EAL policy section (``attestation:``) from the ontology."""
        return dict(self._data.get("attestation", {}))

    def min_distinct_scopes(self) -> int:
        """Minimum distinct organizational scopes whose attestations count (EAL)."""
        value = self.attestation_policy().get("min_distinct_scopes", 2)
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return 2

    def evidence_factor_unbacked(self) -> float:
        """Confidence discount factor α for VALIDATE events lacking attestations."""
        value = self.attestation_policy().get("evidence_factor_unbacked", 0.5)
        try:
            return min(1.0, max(0.0, float(value)))
        except (TypeError, ValueError):
            return 0.5

    def refute_threshold(self) -> int:
        """Distinct-scope refutations that trigger a DEPRECATE proposal (EAL Phase 2)."""
        value = self.attestation_policy().get("refute_threshold", 2)
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return 2

    def require_execution_spec_on_register(self) -> bool:
        """Whether new capability registrations must declare an execution spec (D5)."""
        return bool(self.attestation_policy().get("require_execution_spec_on_register", False))

    def allowed_actions_for_class(self, adl_class: str) -> list[str]:
        """Which actions are allowed on a given ADL class."""
        actions = self._data.get("actions", {})
        result = []
        for name, raw in actions.items():
            allowed = raw.get("allowed_on", [])
            if adl_class in allowed:
                result.append(name)
        return sorted(result)

    def action_preconditions(self, name: str) -> list[dict[str, Any]]:
        """Precondition rules for a given action."""
        actions = self._data.get("actions", {})
        entry = actions.get(name, {})
        return list(entry.get("preconditions", []))

    def action_side_effects(self, name: str) -> list[str]:
        """Side-effect names for a given action."""
        actions = self._data.get("actions", {})
        entry = actions.get(name, {})
        return list(entry.get("side_effects", []))

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


class UnityCriterion:
    """OntoClean unity meta-property annotations (forward compatibility)."""

    UNIFIED = "unified"
    NON_UNIFIED = "non_unified"


class DependenceMetaProperty:
    """OntoClean dependence meta-property annotations (forward compatibility)."""

    RIGID_EXISTENTIAL = "rigid_existential"
    GENERIC = "generic"
    HISTORICAL = "historical"


class OntoCleanEvaluator:
    """Minimal OntoClean evaluator for ADL Lite concepts (forward compatibility)."""

    @staticmethod
    def evaluate_rigidity(concept: Any) -> bool:
        """Return True: a concept's genesis hash is rigid (essential identity)."""
        return True

    @staticmethod
    def evaluate_unity(concept: Any) -> bool:
        """Return True: a concept is individuated by a single genesis hash."""
        return True

    @staticmethod
    def evaluate_dependence(concept: Any) -> bool:
        """Return True: a concept depends on its EventChain record."""
        return True


@lru_cache(maxsize=1)
def default_ontology() -> OntologyManager:
    """Shared OntologyManager for strict validation (loads once per process)."""
    return OntologyManager()
