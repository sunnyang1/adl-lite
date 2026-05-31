"""
ADL Lite — Action Executor (Milestone 2d)

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
# Built-in side effects — dispatched to Lark bridge
# ---------------------------------------------------------------------------


class LarkAnnounceEffect(SideEffect):
    """Broadcast concept to an IM chat room via lark-cli."""

    name = "lark_announce"

    def execute(self, doc, action, params):
        chat_id = params.get("chat_id", "")
        if not chat_id:
            return SideEffectResult(False, "Missing chat_id for lark_announce")
        try:
            from .lark.announce import announce

            announce(
                concept_id=doc.adl_id,
                chat_id=chat_id,
                template=params.get("template", "discovery_broadcast"),
                title=doc.concept_name,
            )
            return SideEffectResult(True, f"Announced {doc.adl_id} to {chat_id}")
        except Exception as exc:
            return SideEffectResult(False, f"lark_announce failed: {exc}")


class LarkPublishEffect(SideEffect):
    """Publish concept document to Feishu knowledge base via lark-cli."""

    name = "lark_publish"

    def execute(self, doc, action, params):
        wiki_space = params.get("wiki_space", "")
        if not wiki_space:
            return SideEffectResult(False, "Missing wiki_space for lark_publish")
        source_path = doc.source_path
        if not source_path:
            return SideEffectResult(False, "No source_path on document, cannot publish")
        try:
            from .lark.publish import publish_file

            publish_file(
                source_path,
                wiki_space=wiki_space,
            )
            return SideEffectResult(True, f"Published {doc.adl_id} to {wiki_space}")
        except Exception as exc:
            return SideEffectResult(False, f"lark_publish failed: {exc}")


class LarkDashboardEffect(SideEffect):
    """Sync concept status to a Feishu dashboard sheet via lark-cli."""

    name = "lark_dashboard"

    def execute(self, doc, action, params):
        sheet_id = params.get("sheet_id", "")
        if not sheet_id:
            return SideEffectResult(False, "Missing sheet_id for lark_dashboard")
        try:
            from .lark.dashboard import sync_dashboard_row

            sync_dashboard_row(
                adl_id=doc.adl_id,
                status=doc.front_matter.status.value,
                confidence=doc.front_matter.confidence,
                sheet_id=sheet_id,
            )
            return SideEffectResult(True, f"Synced {doc.adl_id} to dashboard {sheet_id}")
        except Exception as exc:
            return SideEffectResult(False, f"lark_dashboard failed: {exc}")


class ConsensusUpdateEffect(SideEffect):
    """Apply consensus update from external feedback (listen ingest)."""

    name = "consensus_update"

    def execute(self, doc, action, params):
        feedback_file = params.get("feedback_file", "")
        if not feedback_file:
            return SideEffectResult(False, "Missing feedback_file for consensus_update")
        try:
            from .lark.listen import listen

            listen(
                feedback_file=feedback_file,
                adl_id=doc.adl_id,
            )
            return SideEffectResult(True, f"Processed feedback from {feedback_file}")
        except Exception as exc:
            return SideEffectResult(False, f"consensus_update failed: {exc}")


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

    def __init__(self, ontology_manager) -> None:
        self._om = ontology_manager
        self._action_defs: dict[str, ActionDef] = {}
        self._side_effects: dict[str, SideEffect] = {}
        self._load_registry()
        self._register_default_effects()

    # ------------------------------------------------------------------
    # Registry
    # ------------------------------------------------------------------

    def _load_registry(self) -> None:
        raw_actions = self._om._data.get("actions", {})
        for name, raw in raw_actions.items():
            self._action_defs[name] = load_action_def(name, raw)

    def _register_default_effects(self) -> None:
        for cls in [
            LarkAnnounceEffect,
            LarkPublishEffect,
            LarkDashboardEffect,
            ConsensusUpdateEffect,
        ]:
            instance = cls()
            self._side_effects[instance.name] = instance

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
            self._apply_transition(doc, action_def)

        # 6. Update status
        action.exec_status = ActionExecStatus.EXECUTED if all_ok else ActionExecStatus.FAILED
        action.execution_log = log
        return log

    def _apply_transition(self, doc: ADLDocument, action_def: ActionDef) -> None:
        """Append a lifecycle Event to the concept's EventChain (NOT mutate front_matter)."""
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
                actor="action-executor",
                reasoning=f"Action '{action_def.name}' triggered transition {transition}",
                payload={"new_status": new_status.value},
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
        for rule in action_def.preconditions:
            if not rule.check(doc.front_matter):
                errors.append(
                    f"Precondition failed: {rule.field} " f"{rule.comparator.value} {rule.value}"
                )
        return errors
