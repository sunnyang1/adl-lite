"""E4: Precondition enforcement precision/recall.

Tests that ActionExecutor.validate_action() correctly:
  a) Allows valid actions (no false positives)
  b) Blocks invalid preconditions (no false negatives)
  c) Rejects unknown actions
  d) Rejects actions missing required params

Method: For each registered action, generate a passing and failing document,
then measure validate_action() results.
"""

from __future__ import annotations

from .base import BaseExperiment, ExperimentResult
from .registry import register

from adl_lite.action_executor import ActionExecutor
from adl_lite.models import (
    ADLActionBlock, ADLDocument, ADLFrontMatter, ADLType, DiscoveryStatus,
)
from adl_lite.ontology import OntologyManager


def _make_doc(confidence: float, status: DiscoveryStatus) -> ADLDocument:
    return ADLDocument(
        front_matter=ADLFrontMatter(
            adl_type=ADLType.DISCOVERY,
            adl_id="e4-test",
            confidence=confidence,
            status=status,
        )
    )


def _make_block(action: str, params: dict | None = None) -> ADLActionBlock:
    return ADLActionBlock(
        action=action,
        actor="agent-test",
        reasoning="E4 test",
        params=params or {},
    )


@register("E4")
class E4PreconditionEnforcement(BaseExperiment):
    experiment_id = "E4"
    name = "Precondition enforcement"
    description = "Precision/recall of ActionExecutor precondition validation"

    def run(self) -> ExperimentResult:
        mgr = OntologyManager()
        executor = ActionExecutor(mgr)
        results = []

        true_positive = 0
        false_positive = 0
        true_negative = 0
        false_negative = 0

        # For each action in the registry, generate pass/fail fixtures
        test_cases = [
            # (action_name, doc_factory, params, should_pass, label)
            # --- validate (requires confidence>=0.5, status=provisional) ---
            ("validate", lambda: _make_doc(0.8, DiscoveryStatus.PROVISIONAL), {}, True, "validate_pass"),
            ("validate", lambda: _make_doc(0.3, DiscoveryStatus.PROVISIONAL), {}, False, "validate_low_confidence"),
            ("validate", lambda: _make_doc(0.8, DiscoveryStatus.VALIDATED), {}, False, "validate_wrong_status"),
            # --- deprecate (requires status=validated) ---
            ("deprecate", lambda: _make_doc(0.8, DiscoveryStatus.VALIDATED), {"reason": "obsolete"}, True, "deprecate_pass"),
            ("deprecate", lambda: _make_doc(0.8, DiscoveryStatus.PROVISIONAL), {"reason": "obsolete"}, False, "deprecate_wrong_status"),
            ("deprecate", lambda: _make_doc(0.8, DiscoveryStatus.VALIDATED), {}, False, "deprecate_missing_reason"),
            # --- fork (requires status=provisional, requires fork_id + rationale) ---
            ("fork", lambda: _make_doc(0.5, DiscoveryStatus.PROVISIONAL), {"fork_id": "f1", "rationale": "alt"}, True, "fork_pass"),
            ("fork", lambda: _make_doc(0.5, DiscoveryStatus.VALIDATED), {"fork_id": "f1", "rationale": "alt"}, False, "fork_wrong_status"),
            # --- announce (no preconditions, requires chat_id) ---
            ("announce", lambda: _make_doc(0.0, DiscoveryStatus.PROVISIONAL), {"chat_id": "oc_test"}, True, "announce_pass"),
            ("announce", lambda: _make_doc(0.0, DiscoveryStatus.PROVISIONAL), {}, False, "announce_missing_chat_id"),
            # --- archive (requires status=deprecated) ---
            ("archive", lambda: _make_doc(0.0, DiscoveryStatus.DEPRECATED), {}, True, "archive_pass"),
            ("archive", lambda: _make_doc(0.0, DiscoveryStatus.PROVISIONAL), {}, False, "archive_wrong_status"),
            # --- unknown action ---
            ("nonexistent_action", lambda: _make_doc(0.0, DiscoveryStatus.PROVISIONAL), {}, False, "unknown_action"),
        ]

        for action_name, doc_factory, params, should_pass, label in test_cases:
            doc = doc_factory()
            block = _make_block(action_name, params)
            errors = executor.validate_action(doc, block)

            actually_passed = len(errors) == 0

            if should_pass and actually_passed:
                true_positive += 1
            elif should_pass and not actually_passed:
                false_negative += 1
            elif not should_pass and actually_passed:
                false_positive += 1
            else:
                true_negative += 1

            results.append({
                "label": label,
                "should_pass": should_pass,
                "actually_passed": actually_passed,
                "errors": errors,
            })

        precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 0.0
        recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        all_ok = precision == 1.0 and recall == 1.0

        return ExperimentResult(
            experiment_id=self.experiment_id,
            status="passed" if all_ok else "partial",
            metrics={
                "true_positive": true_positive,
                "false_positive": false_positive,
                "true_negative": true_negative,
                "false_negative": false_negative,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
            },
            raw_data=results,
        )
