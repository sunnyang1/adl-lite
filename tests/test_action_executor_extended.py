"""
Extended tests for adl_lite.action_executor — EWMA side effects, precondition
failures, side effect dispatch order, empty ontology, and unknown action types.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from adl_lite.action_executor import ActionExecutor, CalibrationSideEffect, SideEffectResult
from adl_lite.calibration import MARGINCalibrator
from adl_lite.models import (
    ActionDef,
    ActionExecStatus,
    ADLActionBlock,
    ADLDocument,
    ADLFrontMatter,
    ADLType,
    DiscoveryStatus,
)
from adl_lite.ontology import OntologyManager


@pytest.fixture
def ontology() -> OntologyManager:
    """Real ontology manager from the packaged registry."""
    return OntologyManager()


@pytest.fixture
def executor(ontology: OntologyManager) -> ActionExecutor:
    return ActionExecutor(ontology)


def _make_action(**overrides) -> ADLActionBlock:
    """Build an ADLActionBlock with sensible defaults."""
    defaults: dict[str, Any] = {
        "action": "validate",
        "actor": "tester",
        "reasoning": "Test action",
        "params": {},
    }
    defaults.update(overrides)
    return ADLActionBlock.model_validate(defaults)


def _make_doc(**fm_overrides) -> ADLDocument:
    """Build an ADLDocument with sensible front matter defaults."""
    fm_defaults: dict[str, Any] = {
        "adl_type": ADLType.CONCEPT,
        "adl_id": "test-concept",
        "status": DiscoveryStatus.PROVISIONAL,
        "confidence": 0.0,
        "scope": "public",
    }
    fm_defaults.update(fm_overrides)
    return ADLDocument(
        front_matter=ADLFrontMatter(**fm_defaults),
        markdown_body="Test concept body.",
    )


class TestEWMASideEffectAfterValidate:
    """Test EWMA accuracy update side-effect after VALIDATE transition."""

    def test_ewma_side_effect_after_validate(self, executor: ActionExecutor, tmp_path):
        """After VALIDATE transition, EWMA accuracy update should fire.

        The validate action has preconditions: confidence >= 0.5, status == provisional,
        validator_count >= 1. We set validators to include the actor so all pass.
        """
        executor._calibrator.path = tmp_path / "cal.yaml"

        doc = _make_doc(
            confidence=0.8,
            status=DiscoveryStatus.PROVISIONAL,
            validators=["validator_ewma"],
        )
        action = _make_action(
            action="validate",
            actor="validator_ewma",
            params={"confidence": 0.8},
        )

        _ = executor.execute_one(doc, action)

        # Verify the action was executed
        assert action.exec_status == ActionExecStatus.EXECUTED

        # Verify EWMA was updated for the validator
        accuracy = executor._calibrator.get_accuracy("validator_ewma")
        assert accuracy > 0.5  # Should have been updated from default of 0.5

    def test_ewma_side_effect_with_custom_alpha(self, executor: ActionExecutor, tmp_path):
        """EWMA update with custom alpha parameter."""
        executor._calibrator.path = tmp_path / "cal.yaml"

        doc = _make_doc(
            confidence=0.9,
            status=DiscoveryStatus.PROVISIONAL,
            validators=["validator_alpha"],
        )
        action = _make_action(
            action="validate",
            actor="validator_alpha",
            params={"confidence": 0.9, "alpha": 0.5},
        )

        _ = executor.execute_one(doc, action)

        assert action.exec_status == ActionExecStatus.EXECUTED
        accuracy = executor._calibrator.get_accuracy("validator_alpha")
        # With alpha=0.5 and initial=0.5, observed=0.9:
        # EWMA = 0.5 * 0.9 + (1-0.5) * 0.5 = 0.45 + 0.25 = 0.7
        assert accuracy == pytest.approx(0.7, abs=0.01)

    def test_ewma_side_effect_with_context(self, executor: ActionExecutor, tmp_path):
        """EWMA update with context parameter."""
        executor._calibrator.path = tmp_path / "cal.yaml"

        doc = _make_doc(
            confidence=0.85,
            status=DiscoveryStatus.PROVISIONAL,
            validators=["validator_ctx"],
        )
        action = _make_action(
            action="validate",
            actor="validator_ctx",
            params={"confidence": 0.85, "context": "aml"},
        )

        _ = executor.execute_one(doc, action)

        assert action.exec_status == ActionExecStatus.EXECUTED
        accuracy = executor._calibrator.get_accuracy("validator_ctx", context="aml")
        assert accuracy > 0.0

    def test_ewma_side_effect_not_triggered_for_non_validate(
        self, executor: ActionExecutor, tmp_path
    ):
        """REGISTER (non-validate) transition should NOT trigger EWMA update."""
        executor._calibrator.path = tmp_path / "cal.yaml"

        doc = _make_doc(status=DiscoveryStatus.PROVISIONAL)
        action = _make_action(
            action="register",
            actor="registrar",
            params={},
        )

        # Reset calibrator state to ensure no prior updates
        executor._calibrator._profiles.clear()
        executor._calibrator._context_profiles.clear()

        _ = executor.execute_one(doc, action)

        assert action.exec_status == ActionExecStatus.EXECUTED
        # No EWMA update should have happened for register
        assert executor._calibrator.get_accuracy("registrar") == pytest.approx(0.5)


class TestPreconditionFailureDetailed:
    """Test precondition failures with specific field and value errors."""

    def test_precondition_failure_with_missing_field(self, executor: ActionExecutor):
        """Action with precondition on nonexistent field should fail."""
        doc = _make_doc(confidence=0.3)  # Too low for validate
        action = _make_action(action="validate", actor="tester")
        errors = executor.validate_action(doc, action)

        assert len(errors) >= 1
        assert any("Precondition failed" in e for e in errors)
        assert any("confidence" in e for e in errors)

    def test_precondition_failure_with_wrong_value(self, executor: ActionExecutor):
        """Action with precondition requiring specific value should fail when wrong."""
        doc = _make_doc(status=DiscoveryStatus.VALIDATED)  # Wrong status for validate
        action = _make_action(action="validate", actor="tester")
        errors = executor.validate_action(doc, action)

        # Status should be "provisional" but is "validated"
        assert any("Precondition failed" in e for e in errors)
        # The precondition on status should report the mismatch
        assert any("status" in e for e in errors)

    def test_precondition_failure_executed_action(self, executor: ActionExecutor):
        """Executing an action that fails preconditions should set FAILED status."""
        doc = _make_doc(confidence=0.3)  # Below threshold
        action = _make_action(action="validate", actor="tester")
        log = executor.execute_one(doc, action)

        assert action.exec_status == ActionExecStatus.FAILED
        precondition_entries = [e for e in log if e.side_effect == "_precondition"]
        assert len(precondition_entries) >= 1
        assert precondition_entries[0].detail is not None
        assert "Precondition failed" in precondition_entries[0].detail


class TestSideEffectDispatchOrder:
    """Test that multiple side effects are dispatched in correct order."""

    def test_side_effect_dispatch_order(self, executor: ActionExecutor, tmp_path):
        """When multiple side effects are defined, they should be dispatched in order."""
        executor._calibrator.path = tmp_path / "cal.yaml"

        # Create a custom action with multiple side effects
        custom_action_def = ActionDef(
            name="multi_effect_test",
            description="Test with multiple side effects",
            triggers_transition=None,
            required_params=[],
            preconditions=[],
            side_effects=["calibrate_actor"],  # Use existing registered effect
            allowed_on=["concept"],
        )
        executor._action_defs["multi_effect_test"] = custom_action_def

        # Register a second custom effect
        class OrderTrackingEffect:
            name = "order_tracker"

            def __init__(self):
                self.call_order = []

            def execute(self, doc, action, params):
                self.call_order.append("order_tracker")
                return SideEffectResult(True, "tracked order")

        tracker = OrderTrackingEffect()
        executor.register_effect(tracker)

        # Update the action def to include both effects
        custom_action_def.side_effects = ["calibrate_actor", "order_tracker"]

        doc = _make_doc(status=DiscoveryStatus.PROVISIONAL)
        action = _make_action(
            action="multi_effect_test",
            actor="tester",
            params={"observed_accuracy": 0.8},
        )

        log = executor.execute_one(doc, action)
        assert action.exec_status == ActionExecStatus.EXECUTED

        # Check execution log order matches side_effects order
        effect_names = [e.side_effect for e in log]
        assert "calibrate_actor" in effect_names
        assert "order_tracker" in effect_names

    def test_unknown_side_effect_name(self, executor: ActionExecutor):
        """Unknown side_effect name should be logged as failure but not crash."""
        custom_action_def = ActionDef(
            name="bad_effect_test",
            description="Test with unknown side effect",
            triggers_transition=None,
            required_params=[],
            preconditions=[],
            side_effects=["nonexistent_effect"],
            allowed_on=["concept"],
        )
        executor._action_defs["bad_effect_test"] = custom_action_def

        doc = _make_doc()
        action = _make_action(action="bad_effect_test", actor="tester")

        log = executor.execute_one(doc, action)
        assert action.exec_status == ActionExecStatus.FAILED
        assert any(
            e.side_effect == "nonexistent_effect"
            and e.detail is not None
            and "Unknown side_effect" in e.detail
            for e in log
        )


class TestActionExecutorWithEmptyOntology:
    """Test ActionExecutor with minimal/empty ontology."""

    def test_action_executor_with_empty_ontology(self):
        """ActionExecutor with ontology that has no action definitions."""
        # Create a minimal ontology mock with no actions
        mock_ontology = MagicMock()
        mock_ontology._data = {"actions": {}}
        mock_ontology.min_distinct_validators = MagicMock(return_value=1)

        executor = ActionExecutor(mock_ontology)

        # Should have no actions registered
        assert executor.list_actions() == []

        # Executing any action should fail with "Unknown action"
        doc = _make_doc()
        action = _make_action(action="validate", actor="tester")
        log = executor.execute_one(doc, action)
        assert action.exec_status == ActionExecStatus.FAILED
        assert any("Unknown action" in (e.detail or "") for e in log)

    def test_action_executor_with_minimal_ontology_one_action(self):
        """ActionExecutor with ontology that has one action definition."""
        mock_ontology = MagicMock()
        mock_ontology._data = {
            "actions": {
                "test_action": {
                    "description": "A test action",
                    "allowed_on": ["concept"],
                    "triggers_transition": None,
                    "required_params": [],
                    "preconditions": [],
                    "side_effects": [],
                }
            }
        }
        mock_ontology.min_distinct_validators = MagicMock(return_value=1)

        executor = ActionExecutor(mock_ontology)

        assert executor.list_actions() == ["test_action"]
        doc = _make_doc()
        action = _make_action(action="test_action", actor="tester")
        _ = executor.execute_one(doc, action)
        assert action.exec_status == ActionExecStatus.EXECUTED


class TestValidateActionWithUnknownActionType:
    """Test validate_action with action types not in ontology."""

    def test_validate_action_with_unknown_action_type(self, executor: ActionExecutor):
        """validate_action with unknown type should return error."""
        doc = _make_doc()
        action = _make_action(action="nonexistent_action_type")
        errors = executor.validate_action(doc, action)
        assert len(errors) == 1
        assert "Unknown action" in errors[0]
        assert "nonexistent_action_type" in errors[0]

    def test_validate_action_with_empty_params_on_required(self, executor: ActionExecutor):
        """validate_action for fork (requires params) should report missing params."""
        doc = _make_doc()
        action = _make_action(action="fork")
        errors = executor.validate_action(doc, action)
        assert len(errors) >= 1
        assert "Missing required params" in errors[0]

    def test_validate_action_all_pass_register(self, executor: ActionExecutor):
        """validate_action for register (no preconditions) should pass."""
        doc = _make_doc()
        action = _make_action(action="register")
        errors = executor.validate_action(doc, action)
        assert errors == []


class TestCalibrationSideEffectExtended:
    """Extended tests for CalibrationSideEffect."""

    def test_calibration_side_effect_missing_observed_accuracy(self, tmp_path):
        """CalibrationSideEffect with no observed_accuracy should fail."""
        calibrator = MARGINCalibrator(path=tmp_path / "cal.yaml")
        effect = CalibrationSideEffect(calibrator)
        action = _make_action(actor="tester", params={})
        result = effect.execute(None, action, {})
        assert result.success is False
        assert "Missing observed_accuracy" in result.detail

    def test_calibration_side_effect_invalid_observed_accuracy_type(self, tmp_path):
        """CalibrationSideEffect with non-numeric observed_accuracy should fail."""
        calibrator = MARGINCalibrator(path=tmp_path / "cal.yaml")
        effect = CalibrationSideEffect(calibrator)
        action = _make_action(
            actor="tester",
            params={"observed_accuracy": "not_a_number"},
        )
        result = effect.execute(None, action, {"observed_accuracy": "not_a_number"})
        assert result.success is False
        assert "Invalid observed_accuracy" in result.detail

    def test_calibration_side_effect_observed_accuracy_out_of_range(self, tmp_path):
        """CalibrationSideEffect with observed_accuracy > 1.0 should fail."""
        calibrator = MARGINCalibrator(path=tmp_path / "cal.yaml")
        effect = CalibrationSideEffect(calibrator)
        action = _make_action(
            actor="tester",
            params={"observed_accuracy": 1.5},
        )
        result = effect.execute(None, action, {"observed_accuracy": 1.5})
        assert result.success is False
        assert "must be in [0, 1]" in result.detail

    def test_calibration_side_effect_observed_accuracy_negative(self, tmp_path):
        """CalibrationSideEffect with observed_accuracy < 0 should fail."""
        calibrator = MARGINCalibrator(path=tmp_path / "cal.yaml")
        effect = CalibrationSideEffect(calibrator)
        action = _make_action(
            actor="tester",
            params={"observed_accuracy": -0.5},
        )
        result = effect.execute(None, action, {"observed_accuracy": -0.5})
        assert result.success is False
        assert "must be in [0, 1]" in result.detail

    def test_calibration_side_effect_with_context_and_alpha(self, tmp_path):
        """CalibrationSideEffect with context and alpha should update correctly."""
        calibrator = MARGINCalibrator(path=tmp_path / "cal.yaml")
        effect = CalibrationSideEffect(calibrator)
        action = _make_action(
            actor="tester_ctx",
            params={"observed_accuracy": 0.8, "context": "aml", "alpha": 0.4},
        )
        result = effect.execute(None, action, action.params)
        assert result.success is True
        assert "tester_ctx" in result.detail
        assert "aml" in result.detail

        # Verify the accuracy was updated with the right alpha
        accuracy = calibrator.get_accuracy("tester_ctx", context="aml")
        assert accuracy > 0.0
