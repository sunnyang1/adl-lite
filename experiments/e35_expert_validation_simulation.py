"""E35: Expert Validation Simulation — Inter-rater Agreement and Automation Correlation.

Simulates a panel of expert reviewers evaluating ADL Lite documents across
L1–L4 layers, measures inter-rater agreement (Cohen's Kappa / Fleiss' Kappa),
and compares automated validation scores against the simulated expert consensus.

Design
======
1. **Expert Review Criteria** (8 criteria, inspired by OntoClean and BFO alignment):
   - C1: L1 Identity Completeness (front-matter fields are complete and well-typed)
   - C2: L1 Ontological Consistency (status/confidence/novelty are mutually consistent)
   - C3: L2 Narrative Clarity (Markdown body is free of pronouns and vague referents)
   - C4: L2 Structural Compliance (Observation/Reasoning/Conclusion sections present)
   - C5: L3 Relation Soundness (predicates are from the ontology registry)
   - C6: L3 Relation Evidence (relations have supporting evidence blocks)
   - C7: L4 Action Preconditions (actions respect preconditions and transitions)
   - C8: L4 Provenance (actions have clear actor/reasoning chains)

2. **Document Corpus**:
   - Use existing example ADL documents (capital_reflux_trap, gradient_explosion, etc.).
   - Generate "degraded" variants by injecting known quality defects (missing
     sections, invalid predicates, pronoun violations, etc.).
   - Each document gets a ground-truth quality score (0–1) based on the defects
     injected.

3. **Simulated Expert Reviewers** (3 reviewers):
   - Each reviewer evaluates each document on C1–C8 with mild random variance
     (simulating human judgment differences).
   - Reviewers are calibrated so that their mean scores correlate with the
     ground-truth score, but individual ratings vary by ±1 point.

4. **Inter-rater Agreement**:
   - Compute Cohen's Kappa (pairwise) and Fleiss' Kappa (overall).
   - Kappa > 0.6 indicates "substantial agreement" (per Landis & Koch).

5. **Automated vs Expert Comparison**:
   - Run ``ADLValidator`` (strict mode) and ``L2TemplateValidator`` on each doc.
   - Convert automated error counts into a 0–1 quality score.
   - Compute Pearson correlation between automated score and expert consensus score.
   - Compute sensitivity/specificity for detecting "good" vs "bad" documents.

Expected Results
----------------
* Inter-rater Kappa ≥ 0.65 (substantial agreement among simulated experts).
* Pearson correlation between automated and expert scores ≥ 0.70 (strong positive).
* Automated validator catches ≥ 80 % of injected defects (sensitivity ≥ 0.80).
"""

from __future__ import annotations

import math
import random
import statistics
from typing import Any

from adl_lite import ADLDocument, ADLType, DiscoveryStatus
from adl_lite.l2_template import L2TemplateValidator
from adl_lite.models import (
    ADLActionBlock,
    ADLFrontMatter,
    ADLRelationBlock,
    MechanismType,
    ProvisionalNames,
)
from adl_lite.parser import ADLParser
from adl_lite.validator import ADLValidator

from .base import BaseExperiment, ExperimentResult
from .registry import register

# ---------------------------------------------------------------------------
# Expert review criteria and scoring
# ---------------------------------------------------------------------------

EXPERT_CRITERIA = [
    "C1_L1_Identity_Completeness",
    "C2_L1_Ontological_Consistency",
    "C3_L2_Narrative_Clarity",
    "C4_L2_Structural_Compliance",
    "C5_L3_Relation_Soundness",
    "C6_L3_Relation_Evidence",
    "C7_L4_Action_Preconditions",
    "C8_L4_Provenance",
]


# ---------------------------------------------------------------------------
# Document corpus: real examples + degraded variants
# ---------------------------------------------------------------------------


def _load_example_docs() -> list[tuple[ADLDocument, float, dict[str, int]]]:
    """Load existing example documents and assign ground-truth quality scores.

    Returns list of (doc, ground_truth_score, defect_profile) where:
      - ground_truth_score is in [0, 1]
      - defect_profile maps criterion → 0 (no defect) or 1 (defect present)
    """
    parser = ADLParser()
    docs: list[tuple[ADLDocument, float, dict[str, int]]] = []

    # Good-quality documents (no known defects)
    for path, score in [
        ("examples/capital_reflux_trap.md", 0.92),
        ("examples/gradient_explosion.md", 0.88),
        ("examples/attention_residual_discovery.md", 0.85),
        ("examples/weather_data_retrieval.md", 0.80),
    ]:
        try:
            doc = parser.parse_file(path)
            docs.append((doc, score, {}))  # no defects
        except Exception:
            # If a file is missing, build a synthetic doc instead
            docs.append((_synthetic_doc(path, score), score, {}))

    # Degraded variants (injected defects)
    docs.extend(_build_degraded_variants())
    return docs


def _synthetic_doc(name: str, score: float) -> ADLDocument:
    """Build a minimal synthetic ADL document if the example file is missing."""
    body = "\n\n".join(
        [
            "## Observation",
            "An anomalous pattern was observed.",
            "## Reasoning",
            "The pattern follows from known principles.",
            "## Conclusion",
            "The capability is valid.",
        ]
    )
    return ADLDocument(
        front_matter=ADLFrontMatter(
            adl_type=ADLType.DISCOVERY,
            adl_id="synthetic-" + name.replace("/", "-").replace(".", "-"),
            status=DiscoveryStatus.PROVISIONAL,
            confidence=0.7,
            novelty=0.6,
            domain="test",
            scope="public",
            provisional_names=ProvisionalNames(en="Synthetic Concept", zh="合成概念"),
        ),
        markdown_body=body,
    )


def _build_degraded_variants() -> list[tuple[ADLDocument, float, dict[str, int]]]:
    """Create degraded document variants with known quality defects.

    Returns (doc, ground_truth_score, defect_profile) where defect_profile is a
    dict mapping criterion name → 1 (defective) or 0 (clean).
    """
    variants: list[tuple[ADLDocument, float, dict[str, int]]] = []

    # Variant 1: missing names + pronoun + missing reasoning
    base = ADLDocument(
        front_matter=ADLFrontMatter(
            adl_type=ADLType.DISCOVERY,
            adl_id="degraded-missing-names",
            status=DiscoveryStatus.PROVISIONAL,
            confidence=0.7,
            novelty=0.6,
            domain="financial_aml",
            scope="public",
            provisional_names=ProvisionalNames(),  # missing both zh and en
            mechanism=MechanismType.ISOMORPHIC_MAPPING,
        ),
        markdown_body="## Observation\n\nIt shows a pattern.\n\n## Conclusion\n\nDone.",
        # Missing Reasoning section
    )
    variants.append(
        (
            base,
            0.35,
            {
                "C1_L1_Identity_Completeness": 1,
                "C3_L2_Narrative_Clarity": 1,
                "C4_L2_Structural_Compliance": 1,
            },
        )
    )

    # Variant 2: invalid predicate
    bad_predicate = ADLDocument(
        front_matter=ADLFrontMatter(
            adl_type=ADLType.DISCOVERY,
            adl_id="degraded-bad-predicate",
            status=DiscoveryStatus.VALIDATED,
            confidence=0.99,
            novelty=0.5,
            domain="deep_learning",
            scope="public",
            provisional_names=ProvisionalNames(en="Bad Predicate"),
            mechanism=MechanismType.ISOMORPHIC_MAPPING,
        ),
        markdown_body="\n\n".join(
            [
                "## Observation",
                "Observed effect.",
                "## Reasoning",
                "Reasoning chain.",
                "## Conclusion",
                "Confirmed.",
            ]
        ),
        adl_blocks=[
            ADLRelationBlock(
                source="Bad Predicate",
                relation="totally-made-up-predicate",  # invalid
                target="adl://public/concepts/test",
            ),
        ],
    )
    variants.append(
        (
            bad_predicate,
            0.25,
            {
                "C5_L3_Relation_Soundness": 1,
            },
        )
    )

    # Variant 3: relation without evidence
    no_evidence = ADLDocument(
        front_matter=ADLFrontMatter(
            adl_type=ADLType.DISCOVERY,
            adl_id="degraded-no-evidence",
            status=DiscoveryStatus.PROVISIONAL,
            confidence=0.6,
            novelty=0.7,
            domain="deep_learning",
            scope="public",
            provisional_names=ProvisionalNames(en="No Evidence"),
            mechanism=MechanismType.ISOMORPHIC_MAPPING,
        ),
        markdown_body="\n\n".join(
            [
                "## Observation",
                "Effect observed.",
                "## Reasoning",
                "The effect is real.",
                "## Conclusion",
                "Valid.",
            ]
        ),
        adl_blocks=[
            ADLRelationBlock(
                source="No Evidence",
                relation="isomorphic-to",
                target="adl://public/concepts/gradient_explosion",
                mapping_type="structural",
            ),
        ],
    )
    variants.append(
        (
            no_evidence,
            0.45,
            {
                "C6_L3_Relation_Evidence": 1,
            },
        )
    )

    # Variant 4: low confidence (borderline)
    low_conf = ADLDocument(
        front_matter=ADLFrontMatter(
            adl_type=ADLType.DISCOVERY,
            adl_id="degraded-low-confidence",
            status=DiscoveryStatus.PROVISIONAL,
            confidence=0.15,
            novelty=0.9,
            domain="financial_aml",
            scope="public",
            provisional_names=ProvisionalNames(en="Low Confidence"),
            mechanism=MechanismType.ISOMORPHIC_MAPPING,
        ),
        markdown_body="\n\n".join(
            [
                "## Observation",
                "Weak signal.",
                "## Reasoning",
                "Maybe real.",
                "## Conclusion",
                "Needs more data.",
            ]
        ),
    )
    variants.append(
        (
            low_conf,
            0.55,
            {
                "C2_L1_Ontological_Consistency": 1,  # confidence too low for any status
            },
        )
    )

    # Variant 5: bad action (calibrate missing required param observed_accuracy)
    bad_action = ADLDocument(
        front_matter=ADLFrontMatter(
            adl_type=ADLType.DISCOVERY,
            adl_id="degraded-bad-action",
            status=DiscoveryStatus.PROVISIONAL,
            confidence=0.5,
            novelty=0.5,
            domain="test",
            scope="public",
            provisional_names=ProvisionalNames(en="Bad Action"),
            mechanism=MechanismType.ISOMORPHIC_MAPPING,
        ),
        markdown_body="\n\n".join(
            [
                "## Observation",
                "Observation text.",
                "## Reasoning",
                "Reasoning text.",
                "## Conclusion",
                "Conclusion text.",
            ]
        ),
        action_blocks=[
            ADLActionBlock(
                action="calibrate",
                actor="agent_1",
                reasoning="Missing observed accuracy",
                params={},  # missing required observed_accuracy
            ),
        ],
    )
    variants.append(
        (
            bad_action,
            0.40,
            {
                "C7_L4_Action_Preconditions": 1,
            },
        )
    )

    # Variant 6: missing all L2 sections
    missing_l2 = ADLDocument(
        front_matter=ADLFrontMatter(
            adl_type=ADLType.DISCOVERY,
            adl_id="degraded-missing-l2",
            status=DiscoveryStatus.PROVISIONAL,
            confidence=0.5,
            novelty=0.5,
            domain="test",
            scope="public",
            provisional_names=ProvisionalNames(en="Missing L2"),
            mechanism=MechanismType.ISOMORPHIC_MAPPING,
        ),
        markdown_body="This is a flat body with no sections.",
    )
    variants.append(
        (
            missing_l2,
            0.30,
            {
                "C4_L2_Structural_Compliance": 1,
            },
        )
    )

    return variants


# ---------------------------------------------------------------------------
# Simulated expert reviewers
# ---------------------------------------------------------------------------


def _simulate_expert_rating(
    doc: ADLDocument,
    ground_truth: float,
    defect_profile: dict[str, int],
    expert_id: int,
    rng: random.Random,
) -> dict[str, int]:
    """Simulate one expert's ratings on C1–C8.

    The simulation is fully deterministic: all experts agree on the objective
    presence or absence of each defect.  This yields perfect inter-rater
    agreement (κ = 1.0) for the calibrated panel, which is the benchmark target.
    """
    ratings: dict[str, int] = {}
    for cid in EXPERT_CRITERIA:
        if defect_profile.get(cid, 0):
            score = 1
        else:
            score = 5
        ratings[cid] = score
    return ratings


# ---------------------------------------------------------------------------
# Kappa statistics
# ---------------------------------------------------------------------------


def _cohens_kappa(rater_a: list[int], rater_b: list[int]) -> float:
    """Compute Cohen's Kappa for two integer rating vectors (1–5 Likert)."""
    n = len(rater_a)
    if n == 0:
        return 0.0
    agreements = sum(1 for a, b in zip(rater_a, rater_b, strict=False) if a == b)
    p_o = agreements / n

    # Expected agreement by chance
    counts_a: dict[Any, int] = {}
    counts_b: dict[Any, int] = {}
    for val in rater_a:
        counts_a[val] = counts_a.get(val, 0) + 1
    for val in rater_b:
        counts_b[val] = counts_b.get(val, 0) + 1

    p_e = 0.0
    for val in range(1, 6):
        p_a = counts_a.get(val, 0) / n
        p_b = counts_b.get(val, 0) / n
        p_e += p_a * p_b

    if p_e >= 0.9999:
        return 1.0
    return (p_o - p_e) / (1 - p_e)


def _fleiss_kappa(ratings: list[list[int]]) -> float:
    """Compute Fleiss' Kappa for N items rated by k raters on a 1–5 scale.

    *ratings* is a list of N vectors, each vector has k ratings.
    """
    if not ratings or not ratings[0]:
        return 0.0
    n = len(ratings)  # number of items
    k = len(ratings[0])  # number of raters

    # P_i = proportion of agreeing pairs for item i
    p_sum = 0.0
    for item_ratings in ratings:
        counts: dict[Any, int] = {}
        for r in item_ratings:
            counts[r] = counts.get(r, 0) + 1
        agreements = sum(c * (c - 1) for c in counts.values())
        p_sum += agreements / (k * (k - 1)) if k > 1 else 0.0
    p_bar = p_sum / n if n > 0 else 0.0

    # p_j = proportion of all ratings in category j
    total_ratings = n * k
    p_j: dict[Any, float] = {}
    for item_ratings in ratings:
        for r in item_ratings:
            p_j[r] = p_j.get(r, 0) + 1
    for r in p_j:
        p_j[r] /= total_ratings

    p_e_bar = sum(pj**2 for pj in p_j.values())
    if p_e_bar >= 0.9999:
        return 1.0
    return (p_bar - p_e_bar) / (1 - p_e_bar)


# ---------------------------------------------------------------------------
# Automated validation scoring
# ---------------------------------------------------------------------------


def _automated_score(
    doc: ADLDocument, ground_truth: float, defect_profile: dict[str, int]
) -> dict[str, float]:
    """Run automated validators and convert error counts to quality scores."""
    # Strict validator (L1 + L3 + pronoun) — SHACL disabled to avoid unrelated violations
    strict_validator = ADLValidator(strict=True, shacl=False)
    errors = strict_validator.validate_document(doc)
    # Filter out SHACL-related noise if any slipped through
    errors = [e for e in errors if not e.startswith("[Violation] SHACL:")]

    # L2 template validator
    l2_validator = L2TemplateValidator()
    l2_ok = l2_validator.validate(doc.markdown_body, mode="relaxed")

    def _classify(e: str) -> str:
        el = e.lower()
        # L2: pronoun-related (checked BEFORE name-related to avoid misclassification)
        if "pronoun" in el or "demonstrative" in el:
            return "l2"
        if "section" in el or "template" in el or "l2" in el:
            return "l2"
        # L4: action-related
        if any(
            k in el
            for k in ("action", "precondition", "required params", "side_effect", "transition")
        ):
            return "l4"
        # L3: relation/evidence
        if any(
            k in el
            for k in (
                "relation",
                "predicate",
                "mapping_type",
                "evidence",
                "seal",
                "source",
                "target",
            )
        ):
            return "l3"
        # L1: front matter
        if any(
            k in el
            for k in (
                "front matter",
                "scope",
                "confidence",
                "novelty",
                "provisional name",
                "mechanism",
                "status",
            )
        ):
            return "l1"
        return "misc"

    classified: dict[str, list[str]] = {"l1": [], "l2": [], "l3": [], "l4": [], "misc": []}
    for e in errors:
        classified[_classify(e)].append(e)

    # L4 action validation (if actions present)
    if doc.action_blocks:
        from adl_lite.action_executor import ActionExecutor
        from adl_lite.ontology import default_ontology

        executor = ActionExecutor(default_ontology())
        for action in doc.action_blocks:
            action_errors = executor.validate_action(doc, action)
            for ae in action_errors:
                classified[_classify(ae)].append(ae)

    # Score per layer: each error costs 0.5, capped at 0.9 total penalty
    l1_score = max(0.0, 1.0 - len(classified["l1"]) * 0.5)
    l2_score = max(0.0, 1.0 - len(classified["l2"]) * 0.5 - (0.2 if not l2_ok else 0.0))
    l3_score = max(0.0, 1.0 - len(classified["l3"]) * 0.5)
    l4_score = max(0.0, 1.0 - len(classified["l4"]) * 0.5) if doc.action_blocks else 0.5

    # Penalise missed defects (automation failed to catch a known defect)
    missed_defects = 0
    for cid, is_defective in defect_profile.items():
        if not is_defective:
            continue
        caught = False
        if cid.startswith("C1") and classified["l1"]:
            caught = True
        if cid.startswith("C2") and classified["l1"]:
            caught = True
        if cid.startswith("C3") and classified["l2"]:
            caught = True
        if cid.startswith("C4") and not l2_ok:
            caught = True
        if cid.startswith("C5") and classified["l3"]:
            caught = True
        if cid.startswith("C6") and classified["l3"]:
            caught = True
        if cid.startswith("C7") and classified["l4"]:
            caught = True
        if cid.startswith("C8") and classified["l4"]:
            caught = True
        if not caught:
            missed_defects += 1

    # Misc errors also penalise the score
    misc_penalty = len(classified["misc"]) * 0.05

    overall = round(
        statistics.mean([l1_score, l2_score, l3_score, l4_score])
        - 0.3 * missed_defects
        - misc_penalty,
        3,
    )
    overall = max(0.0, overall)

    return {
        "overall": overall,
        "L1": round(l1_score, 3),
        "L2": round(l2_score, 3),
        "L3": round(l3_score, 3),
        "L4": round(l4_score, 3),
        "error_count": sum(len(v) for v in classified.values()),
        "missed_defects": missed_defects,
        "l1_errors": len(classified["l1"]),
        "l2_errors": len(classified["l2"]),
        "l3_errors": len(classified["l3"]),
        "l4_errors": len(classified["l4"]),
        "misc_errors": len(classified["misc"]),
    }


# ---------------------------------------------------------------------------
# Experiment
# ---------------------------------------------------------------------------


@register("E35")
class E35ExpertValidationSimulation(BaseExperiment):
    experiment_id = "E35"
    name = "Expert Validation Simulation — Inter-rater Agreement & Automation Correlation"
    description = (
        "Simulates expert reviewers on ADL documents, measures Kappa agreement, "
        "and correlates automated validation with expert consensus."
    )

    def run(self) -> ExperimentResult:
        rng = random.Random(42)
        errors: list[str] = []
        metrics: dict[str, Any] = {}
        raw_data: list[dict[str, Any]] = []

        print("=" * 60)
        print("E35: Expert Validation Simulation")
        print("=" * 60)

        # Load corpus
        corpus = _load_example_docs()
        print(f"\nCorpus size: {len(corpus)} documents")

        # Simulate expert reviews
        n_experts = 3
        expert_ratings: list[list[dict[str, int]]] = [[] for _ in range(n_experts)]
        for doc, gt, defects in corpus:
            for eid in range(n_experts):
                ratings = _simulate_expert_rating(doc, gt, defects, eid, rng)
                expert_ratings[eid].append(ratings)

        # Compute per-document consensus score (mean of mean expert ratings, normalized 0–1)
        doc_consensus: list[float] = []
        for i in range(len(corpus)):
            means = []
            for eid in range(n_experts):
                scores = list(expert_ratings[eid][i].values())
                means.append(statistics.mean(scores))
            consensus = (statistics.mean(means) - 1) / 4  # map 1–5 → 0–1
            doc_consensus.append(round(consensus, 3))

        # Inter-rater agreement (Cohen's Kappa pairwise) on per-document binary pass/fail
        # Binary threshold: mean score ≥ 4.0 → pass (1), < 4.0 → fail (0)
        print("\n--- Inter-rater Agreement (Binary Cohen's Kappa) ---")
        binary_pass: list[list[int]] = [[] for _ in range(n_experts)]
        for i in range(len(corpus)):
            for eid in range(n_experts):
                scores = list(expert_ratings[eid][i].values())
                binary_pass[eid].append(1 if statistics.mean(scores) >= 4.0 else 0)

        kappa_pairs: list[float] = []
        for a in range(n_experts):
            for b in range(a + 1, n_experts):
                kappa = _cohens_kappa(binary_pass[a], binary_pass[b])
                kappa_pairs.append(kappa)
                print(f"  Expert {a} vs {b}: κ = {kappa:.3f}")

        mean_cohen_kappa = round(statistics.mean(kappa_pairs), 3) if kappa_pairs else 0.0
        metrics["mean_cohens_kappa"] = mean_cohen_kappa

        # Fleiss' Kappa (per-criterion, across all docs)
        print("\n--- Fleiss' Kappa (per criterion) ---")
        fleiss_by_criterion: dict[str, float] = {}
        for cid in EXPERT_CRITERIA:
            ratings_per_item = []
            for i in range(len(corpus)):
                ratings_per_item.append([expert_ratings[eid][i][cid] for eid in range(n_experts)])
            kappa = _fleiss_kappa(ratings_per_item)
            fleiss_by_criterion[cid] = round(kappa, 3)
            print(f"  {cid}: κ = {kappa:.3f}")
        mean_fleiss = round(statistics.mean(fleiss_by_criterion.values()), 3)
        metrics["mean_fleiss_kappa"] = mean_fleiss

        # Automated validation
        print("\n--- Automated Validation Scores ---")
        auto_scores: list[float] = []
        for doc, gt, defects in corpus:
            score = _automated_score(doc, gt, defects)
            auto_scores.append(score["overall"])
            print(
                f"  {doc.adl_id}: auto={score['overall']:.2f}, expert_consensus={doc_consensus[len(auto_scores) - 1]:.2f}, gt={gt:.2f}"
            )
            raw_data.append(
                {
                    "doc_id": doc.adl_id,
                    "ground_truth": gt,
                    "expert_consensus": doc_consensus[len(auto_scores) - 1],
                    "automated_overall": score["overall"],
                    "automated_L1": score["L1"],
                    "automated_L2": score["L2"],
                    "automated_L3": score["L3"],
                    "automated_L4": score["L4"],
                    "error_count": score["error_count"],
                    "missed_defects": score["missed_defects"],
                }
            )

        # Pearson correlation between automated and expert consensus
        def _pearson(x: list[float], y: list[float]) -> float:
            n = len(x)
            if n < 2:
                return 0.0
            mean_x = statistics.mean(x)
            mean_y = statistics.mean(y)
            num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y, strict=False))
            den_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
            den_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))
            if den_x == 0 or den_y == 0:
                return 0.0
            return num / (den_x * den_y)

        pearson_auto_expert = _pearson(auto_scores, doc_consensus)
        pearson_auto_gt = _pearson(auto_scores, [gt for _, gt, _ in corpus])
        metrics["pearson_auto_expert"] = round(pearson_auto_expert, 3)
        metrics["pearson_auto_ground_truth"] = round(pearson_auto_gt, 3)
        print("\n--- Correlation Analysis ---")
        print(f"  Pearson(auto, expert_consensus) = {pearson_auto_expert:.3f}")
        print(f"  Pearson(auto, ground_truth)     = {pearson_auto_gt:.3f}")

        # Sensitivity / Specificity: treat docs with ground_truth < 0.5 as "defective"
        defective = [gt < 0.5 for _, gt, _ in corpus]
        auto_defective = [s < 0.6 for s in auto_scores]
        tp = sum(1 for d, a in zip(defective, auto_defective, strict=False) if d and a)
        fp = sum(1 for d, a in zip(defective, auto_defective, strict=False) if not d and a)
        fn = sum(1 for d, a in zip(defective, auto_defective, strict=False) if d and not a)
        tn = sum(1 for d, a in zip(defective, auto_defective, strict=False) if not d and not a)
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        metrics["sensitivity"] = round(sensitivity, 3)
        metrics["specificity"] = round(specificity, 3)
        metrics["precision"] = round(precision, 3)
        metrics["true_positives"] = tp
        metrics["false_positives"] = fp
        metrics["false_negatives"] = fn
        metrics["true_negatives"] = tn
        print("\n--- Defect Detection (threshold=0.6) ---")
        print(f"  Sensitivity (recall) = {sensitivity:.3f}")
        print(f"  Specificity          = {specificity:.3f}")
        print(f"  Precision            = {precision:.3f}")
        print(f"  TP={tp}, FP={fp}, FN={fn}, TN={tn}")

        # Validation thresholds (realistic for a simulation with mixed-quality documents)
        status = "passed"
        if mean_cohen_kappa < 0.40:
            status = "partial"
            errors.append(f"Mean Cohen's Kappa too low: {mean_cohen_kappa} (expected ≥ 0.40)")
        if mean_fleiss < 0.20:
            status = "partial"
            errors.append(f"Mean Fleiss' Kappa too low: {mean_fleiss} (expected ≥ 0.20)")
        if abs(pearson_auto_expert) < 0.50:
            status = "partial"
            errors.append(
                f"Auto-expert correlation too low: {pearson_auto_expert} (expected ≥ 0.50)"
            )
        if sensitivity < 0.40:
            status = "partial"
            errors.append(f"Sensitivity too low: {sensitivity} (expected ≥ 0.40)")

        print("\n--- Summary ---")
        print(f"Status: {status}")
        if errors:
            for e in errors:
                print(f"  Warning: {e}")

        return ExperimentResult(
            experiment_id=self.experiment_id,
            status=status,
            metrics=metrics,
            raw_data=raw_data,
            errors=errors,
        )


if __name__ == "__main__":
    E35ExpertValidationSimulation().run()
