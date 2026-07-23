"""
Extended tests for adl_lite.ontology — invalid YAML, mapping_type edge cases,
action registry queries, class-based action filtering, preconditions,
side effects, and validator count edge cases.

Covers uncovered lines: 35, 69, 72, 90-91, 95-96, 104-105, 109-115,
119-121, 125-127.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from adl_lite.exceptions import ADLOntologyError
from adl_lite.ontology import OntologyManager

# ---------------------------------------------------------------------------
# Invalid YAML loading tests
# ---------------------------------------------------------------------------


class TestOntologyLoading:
    """Tests for OntologyManager._load with invalid inputs. Covers line 35."""

    def test_load_invalid_yaml(self, tmp_path: Path):
        """Create an OntologyManager with invalid YAML content.
        Verify appropriate exception is raised."""
        bad_yaml_file = tmp_path / "bad_ontology.yaml"
        # Write YAML that parses to a non-dict (e.g., a list)
        bad_yaml_file.write_text("- item1\n- item2\n", encoding="utf-8")

        with pytest.raises(ADLOntologyError, match="Invalid ontology YAML"):
            OntologyManager(path=str(bad_yaml_file))

    def test_load_missing_file(self, tmp_path: Path):
        """Create an OntologyManager with a non-existent path.
        Verify ADLOntologyError is raised."""
        missing_file = tmp_path / "nonexistent.yaml"
        with pytest.raises(ADLOntologyError, match="Core ontology not found"):
            OntologyManager(path=str(missing_file))

    def test_load_valid_yaml(self, tmp_path: Path):
        """Create an OntologyManager with valid YAML content.
        Verify it loads correctly."""
        valid_yaml_file = tmp_path / "valid_ontology.yaml"
        data = {
            "version": "0.1",
            "classes": {"concept": None},
            "predicates": {"related-to": {"description": "Generic relation"}},
            "status_transitions": {"provisional": ["validated"]},
            "scopes": {"prefixes": ["public"]},
            "mapping_types": ["topological"],
            "actions": {},
            "collusion_resistance": {"min_distinct_validators": 1},
        }
        valid_yaml_file.write_text(yaml.dump(data), encoding="utf-8")

        mgr = OntologyManager(path=str(valid_yaml_file))
        assert mgr.version == "0.1"
        assert "related-to" in mgr.list_predicates()


# ---------------------------------------------------------------------------
# Mapping type validation edge cases
# ---------------------------------------------------------------------------


class TestMappingTypeValidation:
    """Tests for validate_mapping_type with None and empty allowed. Covers lines 69, 72."""

    def test_validate_mapping_type_none(self):
        """Call validate_mapping_type with None as mapping_type.
        Verify it returns False. Covers line 69."""
        mgr = OntologyManager()
        result = mgr.validate_mapping_type("isomorphic-to", None)
        assert result is False

    def test_validate_mapping_type_empty_allowed(self):
        """Call with predicate that has no allowed_mapping_types defined.
        Verify it returns True (no restriction). Covers line 72."""
        mgr = OntologyManager()
        # "related-to" has allowed_mapping_types defined in the YAML,
        # so we need a predicate without them. Use "fork-of" which
        # has allowed_mapping_types in the YAML. Actually, all predicates
        # in the default ontology have allowed_mapping_types.
        # Let's create a custom ontology with a predicate without mapping_types.
        custom_yaml = {
            "version": "0.1",
            "classes": {"concept": None},
            "predicates": {
                "custom-rel": {"description": "No mapping types defined"},
            },
            "status_transitions": {"provisional": ["validated"]},
            "scopes": {"prefixes": ["public"]},
            "mapping_types": [],
            "actions": {},
            "collusion_resistance": {"min_distinct_validators": 1},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml.dump(custom_yaml))
            custom_path = f.name

        mgr = OntologyManager(path=custom_path)
        # With no allowed_mapping_types, any mapping_type should be valid
        result = mgr.validate_mapping_type("custom-rel", "anything")
        assert result is True

        # None should still return False
        result_none = mgr.validate_mapping_type("custom-rel", None)
        assert result_none is False

        Path(custom_path).unlink(missing_ok=True)

    def test_validate_mapping_type_valid(self):
        """Verify valid mapping_type passes for isomorphic-to."""
        mgr = OntologyManager()
        assert mgr.validate_mapping_type("isomorphic-to", "topological") is True

    def test_validate_mapping_type_invalid(self):
        """Verify invalid mapping_type fails for isomorphic-to."""
        mgr = OntologyManager()
        assert mgr.validate_mapping_type("isomorphic-to", "not-a-type") is False


# ---------------------------------------------------------------------------
# Action registry tests
# ---------------------------------------------------------------------------


class TestActionRegistry:
    """Tests for list_actions, get_action_def, and related methods.
    Covers lines 90-91, 95-96, 109-115, 119-121, 125-127."""

    def test_list_actions(self):
        """Call list_actions() on the default OntologyManager.
        Verify all expected action definitions are returned.
        Covers lines 90-91."""
        mgr = OntologyManager()
        actions = mgr.list_actions()

        # The YAML defines these actions
        expected_actions = [
            "announce",
            "archive",
            "attest",
            "calibrate",
            "deprecate",
            "evidence",
            "exec_anchor",
            "execute",
            "fork",
            "listen",
            "publish",
            "register",
            "relate",
            "revoke",
            "seal",
            "sync_dashboard",
            "validate",
        ]
        # list_actions returns sorted keys
        assert actions == sorted(expected_actions)
        assert len(actions) >= 17

    def test_get_action_def_found(self):
        """Call get_action_def("REGISTER") — note: actions are keyed by
        their YAML key (lowercase). Verify it returns the correct dict.
        Covers lines 95-96."""
        mgr = OntologyManager()
        # Action keys in YAML are lowercase: "register", "validate", etc.
        action_def = mgr.get_action_def("register")
        assert action_def is not None
        assert "description" in action_def
        assert action_def["description"] == "Register a new concept into the ontology"
        assert "allowed_on" in action_def
        assert "discovery" in action_def["allowed_on"] or "concept" in action_def["allowed_on"]

    def test_get_action_def_validate(self):
        """Call get_action_def("validate"). Verify it includes preconditions."""
        mgr = OntologyManager()
        action_def = mgr.get_action_def("validate")
        assert action_def is not None
        assert "preconditions" in action_def
        assert len(action_def["preconditions"]) >= 2

    def test_get_action_def_not_found(self):
        """Call get_action_def("NONEXISTENT_ACTION").
        Verify it returns None. Covers lines 95-96."""
        mgr = OntologyManager()
        result = mgr.get_action_def("NONEXISTENT_ACTION")
        assert result is None

    def test_min_distinct_validators_type_error(self):
        """Call min_distinct_validators with non-integer input in YAML.
        Verify TypeError is handled and returns 1. Covers lines 104-105."""
        custom_yaml = {
            "version": "0.1",
            "classes": {"concept": None},
            "predicates": {},
            "status_transitions": {},
            "scopes": {"prefixes": ["public"]},
            "mapping_types": [],
            "actions": {},
            "collusion_resistance": {"min_distinct_validators": "not-an-int"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml.dump(custom_yaml))
            custom_path = f.name

        mgr = OntologyManager(path=custom_path)
        # With a non-integer value, should return 1 (default)
        result = mgr.min_distinct_validators()
        assert result == 1

        Path(custom_path).unlink(missing_ok=True)

    def test_min_distinct_validators_value_error(self):
        """Call with zero or negative value. Verify ValueError is handled
        and returns 1 (via max(1, ...)). Covers lines 104-105."""
        # Test with 0 — should return max(1, 0) = 1
        custom_yaml_zero = {
            "version": "0.1",
            "classes": {"concept": None},
            "predicates": {},
            "status_transitions": {},
            "scopes": {"prefixes": ["public"]},
            "mapping_types": [],
            "actions": {},
            "collusion_resistance": {"min_distinct_validators": 0},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml.dump(custom_yaml_zero))
            custom_path = f.name

        mgr = OntologyManager(path=custom_path)
        result = mgr.min_distinct_validators()
        assert result == 1  # max(1, 0) = 1

        Path(custom_path).unlink(missing_ok=True)

        # Test with negative value — should return max(1, -5) = 1
        custom_yaml_neg = {
            "version": "0.1",
            "classes": {"concept": None},
            "predicates": {},
            "status_transitions": {},
            "scopes": {"prefixes": ["public"]},
            "mapping_types": [],
            "actions": {},
            "collusion_resistance": {"min_distinct_validators": -5},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml.dump(custom_yaml_neg))
            custom_path2 = f.name

        mgr2 = OntologyManager(path=custom_path2)
        result2 = mgr2.min_distinct_validators()
        assert result2 == 1  # max(1, int(-5)) = max(1, -5) = 1

        Path(custom_path2).unlink(missing_ok=True)

    def test_allowed_actions_for_class(self):
        """Call allowed_actions_for_class for known class ("concept").
        Verify action list includes expected actions.
        Covers lines 109-115."""
        mgr = OntologyManager()
        actions = mgr.allowed_actions_for_class("concept")

        # "concept" appears in allowed_on for many actions:
        # register, validate, fork, deprecate, archive, announce, publish,
        # sync_dashboard, listen, relate, evidence, seal, calibrate, revoke
        assert "register" in actions
        assert "validate" in actions
        assert "fork" in actions
        assert "deprecate" in actions
        assert len(actions) >= 10

    def test_allowed_actions_for_class_discovery(self):
        """Call for 'discovery' class. Verify actions are returned."""
        mgr = OntologyManager()
        actions = mgr.allowed_actions_for_class("discovery")
        assert "register" in actions
        assert "validate" in actions

    def test_allowed_actions_for_class_unknown(self):
        """Call for unknown class name. Verify empty list or appropriate response.
        Covers lines 109-115."""
        mgr = OntologyManager()
        actions = mgr.allowed_actions_for_class("nonexistent_class")
        assert actions == []

    def test_action_preconditions(self):
        """Call action_preconditions("validate"). Verify precondition
        rules are returned. Covers lines 119-121."""
        mgr = OntologyManager()
        preconditions = mgr.action_preconditions("validate")
        assert isinstance(preconditions, list)
        assert len(preconditions) >= 2
        # Check that preconditions have expected fields
        for rule in preconditions:
            assert "field" in rule
            assert "comparator" in rule

    def test_action_preconditions_no_preconditions(self):
        """Call action_preconditions for an action with no preconditions.
        Verify empty list is returned."""
        mgr = OntologyManager()
        preconditions = mgr.action_preconditions("register")
        assert preconditions == []

    def test_action_preconditions_nonexistent(self):
        """Call action_preconditions for a nonexistent action.
        Verify empty list is returned."""
        mgr = OntologyManager()
        preconditions = mgr.action_preconditions("nonexistent_action")
        assert preconditions == []

    def test_action_side_effects(self):
        """Call action_side_effects("validate"). Verify side effects
        (empty for validate). Covers lines 125-127."""
        mgr = OntologyManager()
        side_effects = mgr.action_side_effects("validate")
        assert isinstance(side_effects, list)
        # "validate" has no side_effects in the YAML
        assert side_effects == []

    def test_action_side_effects_calibrate(self):
        """Call action_side_effects("calibrate"). Verify 'calibrate_actor'
        is returned as a side effect."""
        mgr = OntologyManager()
        side_effects = mgr.action_side_effects("calibrate")
        assert "calibrate_actor" in side_effects

    def test_action_side_effects_nonexistent(self):
        """Call action_side_effects for nonexistent action.
        Verify empty list is returned."""
        mgr = OntologyManager()
        side_effects = mgr.action_side_effects("nonexistent_action")
        assert side_effects == []
