"""Tests for OntoClean meta-property extensions (Milestone 2a)."""

from __future__ import annotations

from adl_lite.ontology import (
    DependenceMetaProperty,
    OntoCleanEvaluator,
    UnityCriterion,
)


class TestUnityCriterion:
    def test_values(self) -> None:
        assert UnityCriterion.UNIFIED == "unified"
        assert UnityCriterion.NON_UNIFIED == "non_unified"


class TestDependenceMetaProperty:
    def test_values(self) -> None:
        assert DependenceMetaProperty.RIGID_EXISTENTIAL == "rigid_existential"
        assert DependenceMetaProperty.GENERIC == "generic"
        assert DependenceMetaProperty.HISTORICAL == "historical"


class TestOntoCleanEvaluator:
    def test_evaluate_rigidity(self) -> None:
        assert OntoCleanEvaluator.evaluate_rigidity(None) is True
        assert OntoCleanEvaluator.evaluate_rigidity("dummy") is True

    def test_evaluate_unity(self) -> None:
        assert OntoCleanEvaluator.evaluate_unity(None) is True
        assert OntoCleanEvaluator.evaluate_unity("dummy") is True

    def test_evaluate_dependence(self) -> None:
        assert OntoCleanEvaluator.evaluate_dependence(None) is True
        assert OntoCleanEvaluator.evaluate_dependence("dummy") is True
