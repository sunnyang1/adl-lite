"""
SSA Pronoun Ambiguity Benchmark — addresses reviewer questions:
"What is the empirical effect of SSA on ambiguity reduction? Do you have
a benchmark showing how often SSA prevents cross-agent reference errors?"

Dataset: 30 sentences covering 3 categories:
  - AMBIGUOUS (should be flagged): demonstrative pronouns, vague "it", Chinese pronouns
  - COMPLEMENTIZER (should NOT be flagged): legitimate "that" as complementizer
  - CLEAN (should NOT be flagged): explicit references with no pronouns

Metrics: precision, recall, F1 on ambiguity detection.
"""

from __future__ import annotations

from adl_lite.validator import find_pronoun_violations

# ---------------------------------------------------------------------------
# Benchmark dataset: (text, expectation)
#   "ambiguous"  = should trigger SSA violation
#   "clean"      = should NOT trigger any violation
# ---------------------------------------------------------------------------

SENTENCES = [
    # --- Category 1: AMBIGUOUS — should be flagged ---
    # Demonstrative pronoun starts sentence
    ("This mechanism shows strong alignment with attention patterns.", "ambiguous"),
    ("This demonstrates the isomorphic nature of the relationship.", "ambiguous"),
    ("That pattern appears consistently across domains.", "ambiguous"),
    ("These concepts share structural properties.", "ambiguous"),
    ("Those findings confirm the hypothesis.", "ambiguous"),
    # Vague "it" — cannot resolve referent
    ("It demonstrates a clear pattern.", "ambiguous"),
    ("When analyzing the data, it shows unexpected correlations.", "ambiguous"),
    ("Because it violates the expected distribution, we flag this.", "ambiguous"),
    # Chinese pronouns
    ("这个机制展示了跨领域对齐。", "ambiguous"),
    ("那个模式需要进一步验证。", "ambiguous"),
    ("它违反了预期的分布。", "ambiguous"),
    # Pronoun in predicate position
    ("This is a novel discovery in the AML domain.", "ambiguous"),
    # "that" as pronoun (not complementizer) — ambiguous
    ("That indicates a problem with the model.", "ambiguous"),
    # --- Category 2: COMPLEMENTIZER "that" — should NOT be flagged ---
    ("The data shows that the pattern is consistent.", "clean"),
    ("We understand that this limitation is inherent.", "clean"),
    ("This demonstrates that the isomorphic mapping holds.", "clean"),
    ("The simulator indicates that trap formation occurs.", "clean"),
    ("We note that the concept requires further validation.", "clean"),
    ("The results prove that event-first design eliminates race conditions.", "clean"),
    ("It is important that agents use explicit references.", "clean"),
    # --- Category 3: CLEAN — explicit references, no pronouns ---
    ("The capital reflux trap concept was discovered through cross-domain analysis.", "clean"),
    ("Agent A proposed the isomorphic relation based on topological similarity.", "clean"),
    ("The attention residual pattern exhibits structural alignment with financial flows.", "clean"),
    ("Validation was performed by three independent reviewer agents.", "clean"),
    ("The EventChain provides cryptographic integrity for all concept states.", "clean"),
    ("We compare the proposed method with existing RDF/OWL approaches.", "clean"),
    ("Structured Semantic Anchoring constrains natural language ambiguity.", "clean"),
    ("The fork resolution strategy uses Jaccard similarity over relation triples.", "clean"),
    ("All experiments were conducted using the harness.py simulation framework.", "clean"),
]


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


class TestSSAAmbiguityBenchmark:
    """Evaluate SSA pronoun detection precision/recall."""

    def test_benchmark(self):
        tp = fp = tn = fn = 0
        false_positives: list[str] = []
        false_negatives: list[str] = []

        for text, expected in SENTENCES:
            violations = find_pronoun_violations(text)
            predicted_ambiguous = len(violations) > 0
            actually_ambiguous = expected == "ambiguous"

            if actually_ambiguous and predicted_ambiguous:
                tp += 1
            elif actually_ambiguous and not predicted_ambiguous:
                fn += 1
                false_negatives.append(f"MISSED: {text[:60]}")
            elif not actually_ambiguous and predicted_ambiguous:
                fp += 1
                false_positives.append(f"FALSE+: {text[:60]} → {violations[0][:80]}")
            else:
                tn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        print("\n" + "=" * 60)
        print("SSA PRONOUN AMBIGUITY BENCHMARK")
        print("=" * 60)
        print(f"Sentences:         {len(SENTENCES)} total")
        print(f"  Ambiguous (pos): {sum(1 for _, e in SENTENCES if e == 'ambiguous')}")
        print(f"  Clean     (neg): {sum(1 for _, e in SENTENCES if e == 'clean')}")
        print()
        print(f"TP={tp}  FP={fp}  TN={tn}  FN={fn}")
        print(f"Precision: {precision:.3f}")
        print(f"Recall:    {recall:.3f}")
        print(f"F1:        {f1:.3f}")

        if false_positives:
            print(f"\nFalse positives ({len(false_positives)}):")
            for fp_msg in false_positives:
                print(f"  {fp_msg}")
        if false_negatives:
            print(f"\nFalse negatives ({len(false_negatives)}):")
            for fn_msg in false_negatives:
                print(f"  {fn_msg}")
        print("=" * 60)

        # Assertions
        assert precision >= 0.70, f"Precision {precision:.2f} < 0.70"
        assert recall >= 0.70, f"Recall {recall:.2f} < 0.70"
        assert f1 >= 0.70, f"F1 {f1:.2f} < 0.70"
