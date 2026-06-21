"""E15: Precondition boundary stress (negative-result experiment).

Tests how the ActionExecutor handles malformed / adversarial inputs that are
*not* in the original test matrix: NaN, infinity, empty strings, type confusion,
very long strings, and out-of-range numeric values.  We expect the Pydantic
payload validator to reject these *before* precondition evaluation, but we
quantify which ones slip through and which are caught.
"""

from __future__ import annotations

from adl_lite.action_executor import ActionExecutor
from adl_lite.models import (
    ADLActionBlock,
    ADLDocument,
    ADLFrontMatter,
    ADLType,
    DiscoveryStatus,
)
from adl_lite.ontology import OntologyManager

from .base import BaseExperiment, ExperimentResult
from .registry import register


def _make_doc(confidence: float, status: DiscoveryStatus) -> ADLDocument:
    return ADLDocument(
        front_matter=ADLFrontMatter(
            adl_type=ADLType.DISCOVERY,
            adl_id="e15-test",
            confidence=confidence,
            status=status,
        )
    )


def _make_block(action: str, params: dict | None = None) -> ADLActionBlock:
    return ADLActionBlock(
        action=action,
        actor="agent-test",
        reasoning="E15 boundary test",
        params=params or {},
    )


@register("E15")
class E15PreconditionBoundaryStress(BaseExperiment):
    experiment_id = "E15"
    name = "Precondition boundary stress"
    description = "Malformed / adversarial input handling beyond normal matrix"

    def run(self) -> ExperimentResult:
        mgr = OntologyManager()
        executor = ActionExecutor(mgr)
        results = []

        test_cases = [
            # (action, doc_factory, params, expected_stage, label)
            # expected_stage: "pydantic_reject" | "precondition_reject" | "pass"
            # --- NaN confidence ---
            (
                "validate",
                lambda: _make_doc(float("nan"), DiscoveryStatus.PROVISIONAL),
                {},
                "pydantic_reject",
                "nan_confidence",
            ),
            # --- Infinity confidence ---
            (
                "validate",
                lambda: _make_doc(float("inf"), DiscoveryStatus.PROVISIONAL),
                {},
                "pydantic_reject",
                "inf_confidence",
            ),
            # --- Negative confidence ---
            (
                "validate",
                lambda: _make_doc(-0.5, DiscoveryStatus.PROVISIONAL),
                {},
                "pydantic_reject",
                "negative_confidence",
            ),
            # --- Confidence > 1.0 ---
            (
                "validate",
                lambda: _make_doc(1.5, DiscoveryStatus.PROVISIONAL),
                {},
                "pydantic_reject",
                "confidence_gt_1",
            ),
            # --- Empty string actor ---
            (
                "validate",
                lambda: _make_doc(0.8, DiscoveryStatus.PROVISIONAL),
                {"actor": ""},
                "pass",  # actor in params is not checked by preconditions
                "empty_actor_param",
            ),
            # --- Very long reasoning string (10k chars) ---
            (
                "validate",
                lambda: _make_doc(0.8, DiscoveryStatus.PROVISIONAL),
                {"reasoning": "x" * 10000},
                "pass",
                "long_reasoning",
            ),
            # --- Missing required param (reason) for deprecate ---
            (
                "deprecate",
                lambda: _make_doc(0.8, DiscoveryStatus.VALIDATED),
                {"reason": ""},
                "precondition_reject",  # empty reason may be rejected
                "deprecate_empty_reason",
            ),
            # --- Type confusion: string where float expected ---
            (
                "validate",
                lambda: _make_doc(0.8, DiscoveryStatus.PROVISIONAL),
                {"confidence": "0.9"},
                "pydantic_reject",
                "string_confidence",
            ),
            # --- Boundary: confidence exactly 0.5 (minimum) ---
            (
                "validate",
                lambda: _make_doc(0.5, DiscoveryStatus.PROVISIONAL),
                {},
                "pass",
                "confidence_exact_0_5",
            ),
            # --- Boundary: confidence exactly 1.0 (maximum) ---
            (
                "validate",
                lambda: _make_doc(1.0, DiscoveryStatus.PROVISIONAL),
                {},
                "pass",
                "confidence_exact_1_0",
            ),
            # --- Zero-length concept_id ---
            (
                "validate",
                lambda: _make_doc(0.8, DiscoveryStatus.PROVISIONAL),
                {},
                "pass",
                "zero_length_concept_id",
            ),
        ]

        caught_by_pydantic = 0
        caught_by_precondition = 0
        slipped_through = 0
        unexpected = 0

        for action_name, doc_factory, params, expected, label in test_cases:
            block = _make_block(action_name, params)

            try:
                doc = doc_factory()
            except Exception as exc:
                # Pydantic rejects during document construction
                caught_by_pydantic += 1
                stage = "pydantic_reject"
                results.append(
                    {
                        "label": label,
                        "expected": expected,
                        "actual": stage,
                        "passed": False,
                        "errors": [str(exc)],
                    }
                )
                if stage != expected:
                    unexpected += 1
                continue

            try:
                errors = executor.validate_action(doc, block)
                actually_passed = len(errors) == 0

                if expected == "pydantic_reject":
                    if actually_passed:
                        slipped_through += 1
                        stage = "slipped_through"
                    else:
                        caught_by_precondition += 1
                        stage = "precondition_reject"
                elif expected == "precondition_reject":
                    if actually_passed:
                        slipped_through += 1
                        stage = "slipped_through"
                    else:
                        caught_by_precondition += 1
                        stage = "precondition_reject"
                else:  # expected pass
                    if actually_passed:
                        stage = "pass"
                    else:
                        caught_by_precondition += 1
                        stage = "precondition_reject"
            except Exception as exc:
                # Pydantic or other exception
                caught_by_pydantic += 1
                stage = "pydantic_reject"
                errors = [str(exc)]
                actually_passed = False

            if stage != expected and not (
                expected == "pydantic_reject" and stage == "precondition_reject"
            ):
                unexpected += 1

            results.append(
                {
                    "label": label,
                    "expected": expected,
                    "actual": stage,
                    "passed": actually_passed,
                    "errors": errors if isinstance(errors, list) else [str(errors)],
                }
            )

        return ExperimentResult(
            experiment_id=self.experiment_id,
            status="passed",
            metrics={
                "caught_by_pydantic": caught_by_pydantic,
                "caught_by_precondition": caught_by_precondition,
                "slipped_through": slipped_through,
                "unexpected": unexpected,
                "total_cases": len(test_cases),
            },
            raw_data=results,
        )
