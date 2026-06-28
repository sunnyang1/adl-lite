"""
ADL Lite — Action Executor for Capability-Lifecycle Registry (Milestone 2d)

Loads action definitions from the core ontology, validates L4 action blocks
against preconditions, and dispatches declared side_effects to registered
backend plugins.

Architecture:
    1. Parser extracts L4 ```adl:action blocks → ADLActionBlock list
    2. ActionExecutor loads ontology actions registry
    3. For each PENDING action block:
       a. Validate action name against registry
       b. Check preconditions against document front_matter
       c. Execute side_effects in declared order
       d. Update exec_status + execution_log
       e. If triggers_transition: call ConsensusEngine.transition()
"""

from __future__ import annotations

from typing import Any, Protocol

from .calibration import MARGINCalibrator
from .models import (
    ActionDef,
    ActionExecStatus,
    ADLActionBlock,
    ADLDocument,
    Comparator,
    ExecutionEntry,
    PreconditionRule,
)

# ---------------------------------------------------------------------------
# Side-effect plugin protocol
# ---------------------------------------------------------------------------


class SideEffectResult:
    """Outcome of a single side-effect execution."""

    def __init__(self, success: bool, detail: str = "") -> None:
        self.success = success
        self.detail = detail


# ---------------------------------------------------------------------------
# Built-in side effects
# ---------------------------------------------------------------------------


class CalibrationSideEffect:
    """Side effect for the 'calibrate' action: update actor accuracy profile."""

    name = "calibrate_actor"

    def __init__(self, calibrator: MARGINCalibrator | None = None) -> None:
        self.calibrator = calibrator or MARGINCalibrator()

    def execute(
        self,
        doc: ADLDocument,
        action: ADLActionBlock,
        params: dict[str, Any],
    ) -> SideEffectResult:
        observed = params.get("observed_accuracy")
        if observed is None:
            return SideEffectResult(False, "Missing observed_accuracy")
        try:
            observed_f = float(observed)
        except (TypeError, ValueError):
            return SideEffectResult(False, f"Invalid observed_accuracy: {observed}")
        if not (0.0 <= observed_f <= 1.0):
            return SideEffectResult(False, f"observed_accuracy must be in [0, 1], got {observed_f}")

        context = str(params.get("context", "general"))
        alpha = float(params.get("alpha", 0.3))
        actor = action.actor or "system"
        self.calibrator.update_accuracy_ewma(actor, observed_f, context=context, alpha=alpha)
        return SideEffectResult(
            True,
            f"Updated {actor} accuracy in context '{context}' with observed {observed_f}",
        )


class SideEffect(Protocol):
    """Plug-in interface for action side effects."""

    name: str

    def execute(
        self,
        doc: ADLDocument,
        action: ADLActionBlock,
        params: dict[str, Any],
    ) -> SideEffectResult: ...


# ---------------------------------------------------------------------------
# ActionDef loading
# ---------------------------------------------------------------------------


def _parse_comparator(raw: str) -> Comparator:
    return Comparator(raw.strip().lower())


def _parse_precondition_rule(raw: dict) -> PreconditionRule:
    return PreconditionRule(
        field=raw["field"],
        comparator=_parse_comparator(raw["comparator"]),
        value=raw.get("value"),
    )


def load_action_def(name: str, raw: dict) -> ActionDef:
    """Build an ActionDef from a raw ontology entry."""
    preconditions = [_parse_precondition_rule(r) for r in raw.get("preconditions", [])]
    return ActionDef(
        name=name,
        description=raw.get("description", ""),
        allowed_on=raw.get("allowed_on", []),
        triggers_transition=raw.get("triggers_transition"),
        required_params=raw.get("required_params", []),
        preconditions=preconditions,
        side_effects=raw.get("side_effects", []),
    )


# ---------------------------------------------------------------------------
# Action Executor
# ---------------------------------------------------------------------------


class ActionExecutor:
    """
    Validate and execute L4 action blocks against the ontology registry.

    Usage:
        from adl_lite.action_executor import ActionExecutor
        from adl_lite.ontology import default_ontology

        mgr = default_ontology()
        executor = ActionExecutor(mgr)
        results = executor.execute_pending(doc)
    """

    def __init__(self, ontology_manager, calibrator: MARGINCalibrator | None = None) -> None:
        self._om = ontology_manager
        self._action_defs: dict[str, ActionDef] = {}
        self._side_effects: dict[str, SideEffect] = {}
        self._calibrator = calibrator or MARGINCalibrator()
        self._load_registry()
        self.register_effect(CalibrationSideEffect(self._calibrator))

    # ------------------------------------------------------------------
    # Registry
    # ------------------------------------------------------------------

    def _load_registry(self) -> None:
        raw_actions = self._om._data.get("actions", {})
        for name, raw in raw_actions.items():
            self._action_defs[name] = load_action_def(name, raw)

    def register_effect(self, effect: SideEffect) -> None:
        """Plug in a custom side-effect handler."""
        self._side_effects[effect.name] = effect

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute_pending(self, doc: ADLDocument) -> dict[str, list[ExecutionEntry]]:
        """
        Execute all pending action blocks in a document.

        Returns a mapping of action_block_id → execution_log entries.
        """
        results: dict[str, list[ExecutionEntry]] = {}

        for action in doc.pending_actions:
            entries = self._execute_one(doc, action)
            results[action.action_block_id] = entries

        return results

    def execute_one(self, doc: ADLDocument, action: ADLActionBlock) -> list[ExecutionEntry]:
        """Execute a single action block (public API)."""
        return self._execute_one(doc, action)

    def _execute_one(self, doc: ADLDocument, action: ADLActionBlock) -> list[ExecutionEntry]:
        """Internal: validate + dispatch + update status."""
        log: list[ExecutionEntry] = []

        # 1. Validate action name
        action_def = self._action_defs.get(action.action)
        if action_def is None:
            action.exec_status = ActionExecStatus.FAILED
            log.append(
                ExecutionEntry(
                    side_effect="_validate",
                    result="failure",
                    detail=f"Unknown action: {action.action}",
                )
            )
            action.execution_log = log
            return log

        # 2. Check parameters
        missing = [p for p in action_def.required_params if p not in action.params]
        if missing:
            action.exec_status = ActionExecStatus.FAILED
            log.append(
                ExecutionEntry(
                    side_effect="_validate",
                    result="failure",
                    detail=f"Missing required params: {missing}",
                )
            )
            action.execution_log = log
            return log

        # 3. Check preconditions
        for rule in action_def.preconditions:
            if not rule.check(doc.front_matter):
                action.exec_status = ActionExecStatus.FAILED
                log.append(
                    ExecutionEntry(
                        side_effect="_precondition",
                        result="failure",
                        detail=(
                            f"Precondition failed: {rule.field} "
                            f"{rule.comparator.value} {rule.value}"
                        ),
                    )
                )
                action.execution_log = log
                return log

        # 3b. Dynamic collusion-resistance check for validate actions
        if action_def.name == "validate":
            n_min = self._om.min_distinct_validators()
            current_validators = set(doc.front_matter.validators)
            effective_count = len(current_validators)
            if action.actor and action.actor not in current_validators:
                effective_count += 1
            if effective_count < n_min:
                action.exec_status = ActionExecStatus.FAILED
                log.append(
                    ExecutionEntry(
                        side_effect="_collusion_resistance",
                        result="failure",
                        detail=(
                            f"VALIDATE requires at least {n_min} distinct validators, "
                            f"but only {effective_count} would be present"
                        ),
                    )
                )
                action.execution_log = log
                return log

        # 4. Execute side effects
        all_ok = True
        for effect_name in action_def.side_effects:
            effect = self._side_effects.get(effect_name)
            if effect is None:
                log.append(
                    ExecutionEntry(
                        side_effect=effect_name,
                        result="failure",
                        detail=f"Unknown side_effect: {effect_name}",
                    )
                )
                all_ok = False
                continue

            result = effect.execute(doc, action, action.params)
            log.append(
                ExecutionEntry(
                    side_effect=effect_name,
                    result="success" if result.success else "failure",
                    detail=result.detail,
                )
            )
            if not result.success:
                all_ok = False

        # 5. Trigger status transition if declared
        if action_def.triggers_transition:
            self._apply_transition(doc, action, action_def)

        # 5b. Calibration feedback: if the transition was VALIDATE, trigger
        #     an implicit EWMA accuracy update for the action's actor.
        #     The observed_accuracy is derived from the confidence payload
        #     attached to the VALIDATE event, providing a continuous feedback
        #     loop between validation outcomes and per-actor trust scores.
        if action_def.triggers_transition and "validated" in action_def.triggers_transition:
            confidence = float(action.params.get("confidence", 0.5))
            actor = action.actor or "system"
            context = str(action.params.get("context", "general"))
            alpha = float(action.params.get("alpha", 0.3))
            self._calibrator.update_accuracy_ewma(actor, confidence, context=context, alpha=alpha)

        # 6. Update status
        action.exec_status = ActionExecStatus.EXECUTED if all_ok else ActionExecStatus.FAILED
        action.execution_log = log
        return log

    def _apply_transition(
        self, doc: ADLDocument, action: ADLActionBlock, action_def: ActionDef
    ) -> None:
        """Append a lifecycle Event to the capability's EventChain (NOT mutate front_matter)."""
        transition = action_def.triggers_transition
        if not transition or transition == "null":
            return

        parts = transition.split("→")
        if len(parts) != 2:
            return

        to_st = parts[1].strip()
        from .models import DiscoveryStatus, Event, EventType

        try:
            new_status = DiscoveryStatus(to_st)
        except ValueError:
            return  # Invalid status name, skip

        # Build the EventChain and append the lifecycle event
        chain = doc.event_chain
        event_type_map = {
            DiscoveryStatus.PROVISIONAL: EventType.REGISTER,
            DiscoveryStatus.VALIDATED: EventType.VALIDATE,
            DiscoveryStatus.DEPRECATED: EventType.DEPRECATE,
            DiscoveryStatus.FORKED: EventType.FORK,
            DiscoveryStatus.ARCHIVED: EventType.ARCHIVE,
        }
        event_type = event_type_map.get(new_status, EventType.REGISTER)

        chain.append(
            Event(
                concept_id=doc.adl_id,
                event_type=event_type,
                actor=action.actor or "action-executor",
                reasoning=action.reasoning
                or f"Action '{action_def.name}' triggered transition {transition}",
                payload={"new_status": new_status.value, **action.params},
            )
        )

        # Sync front_matter FROM the chain (derived, not stored)
        doc.refresh_snapshot(chain)

    # ------------------------------------------------------------------
    # Introspection (for agent query tools)
    # ------------------------------------------------------------------

    def list_actions(self) -> list[str]:
        """All registered action names."""
        return sorted(self._action_defs.keys())

    def get_action_def(self, name: str) -> ActionDef | None:
        """Look up a single action definition."""
        return self._action_defs.get(name)

    def list_side_effects(self) -> list[str]:
        """All registered side-effect names."""
        return sorted(self._side_effects.keys())

    def validate_action(self, doc: ADLDocument, action: ADLActionBlock) -> list[str]:
        """Dry-run validation: return list of errors without executing."""
        errors: list[str] = []
        action_def = self._action_defs.get(action.action)
        if action_def is None:
            errors.append(f"Unknown action: {action.action}")
            return errors
        missing = [p for p in action_def.required_params if p not in action.params]
        if missing:
            errors.append(f"Missing required params: {missing}")
        # Evaluate preconditions in the context of the action's actor, who would
        # become a validator if the action executes. This lets the first VALIDATE
        # on a concept satisfy the validator_count >= N_min precondition.
        fm_for_check = doc.front_matter
        if action.actor and action.actor.strip() and action.actor not in fm_for_check.validators:
            fm_for_check = fm_for_check.model_copy()
            fm_for_check.validators = list(fm_for_check.validators) + [action.actor]

        for rule in action_def.preconditions:
            if not rule.check(fm_for_check):
                errors.append(
                    f"Precondition failed: {rule.field} {rule.comparator.value} {rule.value}"
                )

        # Dynamic collusion-resistance check for validate actions
        if action_def.name == "validate":
            n_min = self._om.min_distinct_validators()
            current_validators = set(doc.front_matter.validators)
            effective_count = len(current_validators)
            if action.actor and action.actor not in current_validators:
                effective_count += 1
            if effective_count < n_min:
                errors.append(
                    f"VALIDATE requires at least {n_min} distinct validators, "
                    f"but only {effective_count} would be present"
                )

        return errors
