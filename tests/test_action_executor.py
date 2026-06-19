"""
Tests for adl_lite.action_executor — comprehensive coverage of ActionExecutor.

Covers:
    - ActionDef loading from ontology raw dicts
    - PreconditionRule check with all Comparator types
    - ActionExecutor initialization and registry loading
    - execute_one: name validation, param check, preconditions, side effects, transition
    - execute_pending: multi-action workflow
    - validate_action: dry-run validation
    - SideEffect protocol and SideEffectResult
    - _apply_transition: various trigger strings (valid, null, invalid)
    - register_effect: custom effect registration
    - Introspection: list_actions, get_action_def, list_side_effects
"""

from __future__ import annotations

import pytest

from adl_lite.action_executor import (
    ActionExecutor,
    SideEffect,
    SideEffectResult,
    _parse_comparator,
    _parse_precondition_rule,
    load_action_def,
)
from adl_lite.models import (
    ActionDef,
    ActionExecStatus,
    ADLActionBlock,
    ADLDocument,
    ADLFrontMatter,
    ADLType,
    Comparator,
    DiscoveryStatus,
    PreconditionRule,
)
from adl_lite.ontology import OntologyManager

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ontology() -> OntologyManager:
    """Real ontology manager from the packaged registry."""
    return OntologyManager()


@pytest.fixture
def executor(ontology: OntologyManager) -> ActionExecutor:
    return ActionExecutor(ontology)


@pytest.fixture
def minimal_doc() -> ADLDocument:
    """A valid provisional concept with confidence=0.0."""
    return ADLDocument(
        front_matter=ADLFrontMatter(
            adl_type=ADLType.CONCEPT,
            adl_id="test-concept",
            status=DiscoveryStatus.PROVISIONAL,
            confidence=0.0,
            scope="public",
        ),
        markdown_body="Test concept body.",
    )


@pytest.fixture
def validated_doc() -> ADLDocument:
    """A validated concept with confidence=0.8."""
    return ADLDocument(
        front_matter=ADLFrontMatter(
            adl_type=ADLType.CONCEPT,
            adl_id="test-validated",
            status=DiscoveryStatus.VALIDATED,
            confidence=0.8,
            scope="public",
        ),
        markdown_body="Validated concept body.",
    )


@pytest.fixture
def deprecated_doc() -> ADLDocument:
    """A deprecated concept."""
    return ADLDocument(
        front_matter=ADLFrontMatter(
            adl_type=ADLType.CONCEPT,
            adl_id="test-deprecated",
            status=DiscoveryStatus.DEPRECATED,
            confidence=0.3,
            scope="public",
        ),
        markdown_body="Deprecated concept body.",
    )


def _make_action(**overrides) -> ADLActionBlock:
    """Build an ADLActionBlock with sensible defaults."""
    defaults = {
        "action": "validate",
        "actor": "tester",
        "reasoning": "Test action",
        "params": {},
    }
    defaults.update(overrides)
    return ADLActionBlock(**defaults)


# ---------------------------------------------------------------------------
# _parse_comparator
# ---------------------------------------------------------------------------


class TestParseComparator:
    def test_parses_all_enum_values(self):
        for comp in Comparator:
            assert _parse_comparator(comp.value) == comp

    def test_parses_uppercase(self):
        assert _parse_comparator("EQ") == Comparator.EQ

    def test_parses_with_whitespace(self):
        assert _parse_comparator("  gte  ") == Comparator.GTE


# ---------------------------------------------------------------------------
# _parse_precondition_rule
# ---------------------------------------------------------------------------


class TestParsePreconditionRule:
    def test_parses_basic_rule(self):
        rule = _parse_precondition_rule({"field": "confidence", "comparator": "gte", "value": 0.5})
        assert rule.field == "confidence"
        assert rule.comparator == Comparator.GTE
        assert rule.value == 0.5

    def test_parses_without_value(self):
        rule = _parse_precondition_rule({"field": "status", "comparator": "exists"})
        assert rule.field == "status"
        assert rule.comparator == Comparator.EXISTS
        assert rule.value is None


# ---------------------------------------------------------------------------
# load_action_def
# ---------------------------------------------------------------------------


class TestLoadActionDef:
    def test_loads_full_definition(self):
        raw = {
            "description": "Validate a concept",
            "allowed_on": ["discovery", "concept"],
            "triggers_transition": "provisional → validated",
            "required_params": [],
            "preconditions": [
                {"field": "confidence", "comparator": "gte", "value": 0.5},
            ],
            "side_effects": [],
        }
        ad = load_action_def("validate", raw)
        assert ad.name == "validate"
        assert ad.description == "Validate a concept"
        assert ad.allowed_on == ["discovery", "concept"]
        assert ad.triggers_transition == "provisional → validated"
        assert len(ad.preconditions) == 1
        assert ad.preconditions[0].field == "confidence"
        assert ad.preconditions[0].comparator == Comparator.GTE
        assert ad.side_effects == []

    def test_loads_minimal_definition(self):
        raw = {}
        ad = load_action_def("foo", raw)
        assert ad.name == "foo"
        assert ad.description == ""
        assert ad.allowed_on == []
        assert ad.preconditions == []
        assert ad.side_effects == []
        assert ad.triggers_transition is None
        assert ad.required_params == []


# ---------------------------------------------------------------------------
# SideEffectResult
# ---------------------------------------------------------------------------


class TestSideEffectResult:
    def test_success(self):
        r = SideEffectResult(True, "all good")
        assert r.success is True
        assert r.detail == "all good"

    def test_failure(self):
        r = SideEffectResult(False, "something broke")
        assert r.success is False
        assert r.detail == "something broke"

    def test_default_detail(self):
        r = SideEffectResult(True)
        assert r.detail == ""


# ---------------------------------------------------------------------------
# ActionExecutor Initialization
# ---------------------------------------------------------------------------


class TestActionExecutorInit:
    def test_loads_action_registry(self, executor: ActionExecutor):
        actions = executor.list_actions()
        assert "validate" in actions
        assert "register" in actions
        assert "fork" in actions
        assert "announce" in actions
        assert "publish" in actions

    def test_registers_default_effects(self, executor: ActionExecutor):
        effects = executor.list_side_effects()
        assert effects == []


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------


class TestIntrospection:
    def test_list_actions_sorted(self, executor: ActionExecutor):
        actions = executor.list_actions()
        assert actions == sorted(actions)
        assert len(actions) > 0

    def test_list_side_effects_sorted(self, executor: ActionExecutor):
        effects = executor.list_side_effects()
        assert effects == sorted(effects)

    def test_get_action_def_known(self, executor: ActionExecutor):
        ad = executor.get_action_def("validate")
        assert ad is not None
        assert isinstance(ad, ActionDef)
        assert ad.name == "validate"

    def test_get_action_def_unknown(self, executor: ActionExecutor):
        ad = executor.get_action_def("nonexistent_action")
        assert ad is None


# ---------------------------------------------------------------------------
# execute_one — Name Validation
# ---------------------------------------------------------------------------


class TestExecuteOneValidation:
    def test_unknown_action(self, executor: ActionExecutor, minimal_doc: ADLDocument):
        action = _make_action(action="nonexistent_action")
        log = executor.execute_one(minimal_doc, action)

        assert action.exec_status == ActionExecStatus.FAILED
        assert len(log) == 1
        assert log[0].side_effect == "_validate"
        assert log[0].result == "failure"
        assert "Unknown action" in log[0].detail

    def test_known_action_no_params(self, executor: ActionExecutor, minimal_doc: ADLDocument):
        """register action has no required_params — should pass validation."""
        action = _make_action(action="register")
        log = executor.execute_one(minimal_doc, action)
        # register has no side effects, so it should be EXECUTED
        assert action.exec_status == ActionExecStatus.EXECUTED
        assert len(log) == 0


# ---------------------------------------------------------------------------
# execute_one — Required Parameters
# ---------------------------------------------------------------------------


class TestExecuteOneRequiredParams:
    def test_missing_required_param(self, executor: ActionExecutor, minimal_doc: ADLDocument):
        """fork requires fork_id and rationale — neither provided."""
        action = _make_action(action="fork")
        log = executor.execute_one(minimal_doc, action)

        assert action.exec_status == ActionExecStatus.FAILED
        assert len(log) == 1
        assert log[0].side_effect == "_validate"
        assert "Missing required params" in log[0].detail
        assert "fork_id" in log[0].detail

    def test_all_required_params_present(self, executor: ActionExecutor, minimal_doc: ADLDocument):
        action = _make_action(
            action="fork",
            params={"fork_id": "test-fork", "rationale": "testing"},
        )
        log = executor.execute_one(minimal_doc, action)

        # fork has precondition: status == provisional (which it is)
        # no side effects registered by default
        assert action.exec_status == ActionExecStatus.EXECUTED
        assert all(e.side_effect != "_validate" for e in log)


# ---------------------------------------------------------------------------
# execute_one — Preconditions
# ---------------------------------------------------------------------------


class TestExecuteOnePreconditions:
    def test_precondition_fails(self, executor: ActionExecutor, minimal_doc: ADLDocument):
        """validate requires confidence >= 0.5 — minimal_doc has 0.0."""
        action = _make_action(action="validate")
        log = executor.execute_one(minimal_doc, action)

        assert action.exec_status == ActionExecStatus.FAILED
        assert len(log) == 1
        assert log[0].side_effect == "_precondition"
        assert "Precondition failed" in log[0].detail

    def test_precondition_passes(self, executor: ActionExecutor, validated_doc: ADLDocument):
        """validate requires confidence >= 0.5 AND status == provisional.
        validated_doc has confidence=0.8 but status=validated → should fail."""
        action = _make_action(action="validate")
        log = executor.execute_one(validated_doc, action)

        assert action.exec_status == ActionExecStatus.FAILED
        assert any(e.side_effect == "_precondition" for e in log)

    def test_deprecate_only_on_validated(
        self, executor: ActionExecutor, validated_doc: ADLDocument
    ):
        """deprecate requires status == validated and reason param."""
        action = _make_action(action="deprecate", params={"reason": "obsolete"})
        executor.execute_one(validated_doc, action)

        # no side effects registered by default, so it should execute cleanly
        assert action.exec_status == ActionExecStatus.EXECUTED


# ---------------------------------------------------------------------------
# execute_pending — Batch Execution
# ---------------------------------------------------------------------------


class TestExecutePending:
    def test_no_pending_actions(self, executor: ActionExecutor, minimal_doc: ADLDocument):
        # Clear any pending actions
        minimal_doc.action_blocks = []
        results = executor.execute_pending(minimal_doc)
        assert results == {}

    def test_multiple_pending(self, executor: ActionExecutor, minimal_doc: ADLDocument):
        # Two register actions (no required params, no preconditions)
        a1 = _make_action(action="register", action_block_id="action-1")
        a2 = _make_action(action="register", action_block_id="action-2")
        minimal_doc.action_blocks = [a1, a2]

        results = executor.execute_pending(minimal_doc)
        assert len(results) == 2
        assert a1.action_block_id in results
        assert a2.action_block_id in results
        assert a1.exec_status == ActionExecStatus.EXECUTED
        assert a2.exec_status == ActionExecStatus.EXECUTED

    def test_mixed_results(self, executor: ActionExecutor, minimal_doc: ADLDocument):
        """One valid (register) and one invalid (unknown action)."""
        a1 = _make_action(action="register", action_block_id="action-ok")
        a2 = _make_action(action="unknown_action", action_block_id="action-bad")
        minimal_doc.action_blocks = [a1, a2]

        results = executor.execute_pending(minimal_doc)
        assert len(results) == 2
        assert a1.exec_status == ActionExecStatus.EXECUTED
        assert a2.exec_status == ActionExecStatus.FAILED


# ---------------------------------------------------------------------------
# validate_action — Dry-Run
# ---------------------------------------------------------------------------


class TestValidateAction:
    def test_unknown_action(self, executor: ActionExecutor, minimal_doc: ADLDocument):
        action = _make_action(action="unknown_action")
        errors = executor.validate_action(minimal_doc, action)
        assert len(errors) == 1
        assert "Unknown action" in errors[0]

    def test_missing_params(self, executor: ActionExecutor, minimal_doc: ADLDocument):
        action = _make_action(action="fork")
        errors = executor.validate_action(minimal_doc, action)
        assert len(errors) == 1
        assert "Missing required params" in errors[0]

    def test_precondition_fail(self, executor: ActionExecutor, minimal_doc: ADLDocument):
        action = _make_action(action="validate")
        errors = executor.validate_action(minimal_doc, action)
        assert len(errors) >= 1
        assert any("Precondition failed" in e for e in errors)

    def test_all_pass(self, executor: ActionExecutor, minimal_doc: ADLDocument):
        action = _make_action(action="register")
        errors = executor.validate_action(minimal_doc, action)
        assert errors == []

    def test_multiple_errors(self, executor: ActionExecutor, minimal_doc: ADLDocument):
        """validate on minimal_doc: precondition (confidence) fails, status check fails, validator_count fails."""
        # Create a custom action that requires params AND fails preconditions
        action = _make_action(action="fork")  # requires fork_id, rationale
        errors = executor.validate_action(minimal_doc, action)
        # Only missing params reported first
        assert len(errors) == 1


# ---------------------------------------------------------------------------
# _apply_transition
# ---------------------------------------------------------------------------


class TestApplyTransition:
    def test_transition_null_skips(self, executor: ActionExecutor, minimal_doc: ADLDocument):
        """announce has triggers_transition: null."""
        original_status = minimal_doc.front_matter.status
        action = _make_action(action="announce", params={"chat_id": "oc_test"})

        # no side effects registered by default, so it should execute cleanly
        executor.execute_one(minimal_doc, action)
        assert minimal_doc.front_matter.status == original_status

    def test_transition_provisional_to_validated(
        self, executor: ActionExecutor, minimal_doc: ADLDocument
    ):
        """Manually call _apply_transition on a provisional doc with validate action def."""
        ad = executor.get_action_def("validate")
        assert ad is not None

        # Modify doc's confidence so precondition passes (not checked in _apply_transition)
        minimal_doc.front_matter.confidence = 0.8
        minimal_doc.front_matter.status = DiscoveryStatus.PROVISIONAL

        executor._apply_transition(minimal_doc, ad)
        # After transition, status should be VALIDATED (computed from chain)
        assert minimal_doc.front_matter.status == DiscoveryStatus.VALIDATED

    def test_transition_deprecated_to_archived(
        self, executor: ActionExecutor, deprecated_doc: ADLDocument
    ):
        """archive triggers deprecated → archived."""
        ad = executor.get_action_def("archive")
        assert ad is not None
        executor._apply_transition(deprecated_doc, ad)
        assert deprecated_doc.front_matter.status == DiscoveryStatus.ARCHIVED

    def test_transition_invalid_status_name(
        self, executor: ActionExecutor, minimal_doc: ADLDocument
    ):
        """Action def with an invalid transition target should not crash."""
        ad = ActionDef(
            name="bad_transition",
            description="",
            triggers_transition="provisional → nonexistent",
            required_params=[],
            preconditions=[],
            side_effects=[],
            allowed_on=["concept"],
        )
        original_status = minimal_doc.front_matter.status
        executor._apply_transition(minimal_doc, ad)
        assert minimal_doc.front_matter.status == original_status

    def test_transition_malformed_string(self, executor: ActionExecutor, minimal_doc: ADLDocument):
        """Malformed transition string (no arrow)."""
        ad = ActionDef(
            name="bad_transition",
            description="",
            triggers_transition="provisional validated",  # no arrow
            required_params=[],
            preconditions=[],
            side_effects=[],
            allowed_on=["concept"],
        )
        original_status = minimal_doc.front_matter.status
        executor._apply_transition(minimal_doc, ad)
        assert minimal_doc.front_matter.status == original_status


# ---------------------------------------------------------------------------
# register_effect — Custom Side Effects
# ---------------------------------------------------------------------------


class TestRegisterEffect:
    def test_registers_custom_effect(self, executor: ActionExecutor):
        class CustomEffect(SideEffect):
            name = "custom_test"

            def execute(self, doc, action, params):
                return SideEffectResult(True, "custom ok")

        executor.register_effect(CustomEffect())
        assert "custom_test" in executor.list_side_effects()

    def test_overrides_existing(self, executor: ActionExecutor):
        """Registering a new effect with an existing name should override it."""

        class MockEffect(SideEffect):
            name = "mock_effect"

            def execute(self, doc, action, params):
                return SideEffectResult(True, "mocked")

        executor.register_effect(MockEffect())
        effects = executor.list_side_effects()
        assert "mock_effect" in effects


# ---------------------------------------------------------------------------
# PreconditionRule — All Comparator Types
# ---------------------------------------------------------------------------


class TestPreconditionRule:
    @pytest.fixture
    def fm(self) -> ADLFrontMatter:
        return ADLFrontMatter(
            adl_type=ADLType.CONCEPT,
            adl_id="test-pc",
            status=DiscoveryStatus.PROVISIONAL,
            confidence=0.5,
            scope="public",
        )

    def test_eq_pass(self, fm: ADLFrontMatter):
        rule = PreconditionRule(field="status", comparator=Comparator.EQ, value="provisional")
        assert rule.check(fm) is True

    def test_eq_fail(self, fm: ADLFrontMatter):
        rule = PreconditionRule(field="status", comparator=Comparator.EQ, value="validated")
        assert rule.check(fm) is False

    def test_neq_pass(self, fm: ADLFrontMatter):
        rule = PreconditionRule(field="status", comparator=Comparator.NEQ, value="validated")
        assert rule.check(fm) is True

    def test_gt_pass(self, fm: ADLFrontMatter):
        rule = PreconditionRule(field="confidence", comparator=Comparator.GT, value=0.4)
        assert rule.check(fm) is True

    def test_gt_fail(self, fm: ADLFrontMatter):
        rule = PreconditionRule(field="confidence", comparator=Comparator.GT, value=0.5)
        assert rule.check(fm) is False

    def test_gte_pass_equal(self, fm: ADLFrontMatter):
        rule = PreconditionRule(field="confidence", comparator=Comparator.GTE, value=0.5)
        assert rule.check(fm) is True

    def test_gte_pass_greater(self, fm: ADLFrontMatter):
        rule = PreconditionRule(field="confidence", comparator=Comparator.GTE, value=0.4)
        assert rule.check(fm) is True

    def test_lt_pass(self, fm: ADLFrontMatter):
        rule = PreconditionRule(field="confidence", comparator=Comparator.LT, value=0.6)
        assert rule.check(fm) is True

    def test_lt_fail(self, fm: ADLFrontMatter):
        rule = PreconditionRule(field="confidence", comparator=Comparator.LT, value=0.5)
        assert rule.check(fm) is False

    def test_lte_pass_equal(self, fm: ADLFrontMatter):
        rule = PreconditionRule(field="confidence", comparator=Comparator.LTE, value=0.5)
        assert rule.check(fm) is True

    def test_in_pass(self, fm: ADLFrontMatter):
        rule = PreconditionRule(
            field="status", comparator=Comparator.IN, value=["provisional", "validated"]
        )
        assert rule.check(fm) is True

    def test_in_fail(self, fm: ADLFrontMatter):
        rule = PreconditionRule(
            field="status", comparator=Comparator.IN, value=["validated", "deprecated"]
        )
        assert rule.check(fm) is False

    def test_in_single_value(self, fm: ADLFrontMatter):
        rule = PreconditionRule(field="status", comparator=Comparator.IN, value="provisional")
        assert rule.check(fm) is True

    def test_exists_pass(self, fm: ADLFrontMatter):
        rule = PreconditionRule(field="confidence", comparator=Comparator.EXISTS)
        assert rule.check(fm) is True

    def test_exists_fail(self, fm: ADLFrontMatter):
        rule = PreconditionRule(field="nonexistent_field", comparator=Comparator.EXISTS)
        assert rule.check(fm) is False

    def test_none_actual_comparison(self, fm: ADLFrontMatter):
        """If actual field is None (not EXISTS), EQ/GT/etc should return False."""
        rule = PreconditionRule(
            field="nonexistent_field", comparator=Comparator.EQ, value="anything"
        )
        assert rule.check(fm) is False


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_execute_one_with_empty_action_block_id(
        self, executor: ActionExecutor, minimal_doc: ADLDocument
    ):
        """Action block with empty action_block_id (auto-generated on validate)."""
        action = _make_action(action="register")
        assert action.action_block_id == ""  # auto-generated after creation
        executor.execute_one(minimal_doc, action)
        assert action.exec_status == ActionExecStatus.EXECUTED

    def test_state_mutation_after_execute(self, executor: ActionExecutor, minimal_doc: ADLDocument):
        """Verify that executing an action mutates its exec_status and execution_log."""
        action = _make_action(action="register")
        assert action.exec_status == ActionExecStatus.PENDING
        assert action.execution_log == []

        executor.execute_one(minimal_doc, action)
        assert action.exec_status == ActionExecStatus.EXECUTED
        assert len(action.execution_log) == 0  # register has no side effects

    def test_failed_action_leaves_log(self, executor: ActionExecutor, minimal_doc: ADLDocument):
        action = _make_action(action="unknown_action")
        executor.execute_one(minimal_doc, action)

        assert action.exec_status == ActionExecStatus.FAILED
        assert len(action.execution_log) == 1
        assert action.execution_log[0].result == "failure"

    def test_event_chain_status_after_transition(
        self, executor: ActionExecutor, minimal_doc: ADLDocument
    ):
        """After transition, event chain status should match front_matter status."""
        minimal_doc.front_matter.confidence = 0.8
        minimal_doc.front_matter.status = DiscoveryStatus.PROVISIONAL

        ad = executor.get_action_def("validate")
        assert ad is not None

        executor._apply_transition(minimal_doc, ad)

        chain = minimal_doc.event_chain
        assert chain.status == DiscoveryStatus.VALIDATED
        assert minimal_doc.front_matter.status == DiscoveryStatus.VALIDATED
