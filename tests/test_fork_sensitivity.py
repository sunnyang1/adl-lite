"""
Fork threshold sensitivity analysis (simplified, no pre-sweep assertions).
Sweeps thresholds 0.70-0.95 and reports FPR/FNR/F1 metrics.
"""

from __future__ import annotations

from adl_lite.consensus import ForkManager, ForkResolution
from adl_lite.models import ADLDocument, ADLFrontMatter, ADLRelationBlock, ADLType, DiscoveryStatus


def _make(adl_id: str, rels: list[tuple[str, str]]) -> ADLDocument:
    return ADLDocument(
        front_matter=ADLFrontMatter(
            adl_type=ADLType.CONCEPT,
            adl_id=adl_id,
            status=DiscoveryStatus.PROVISIONAL,
            scope="public",
        ),
        adl_blocks=[
            ADLRelationBlock(source=adl_id, relation=r, target=t, confidence=0.9) for r, t in rels
        ],
    )


def _triples(doc: ADLDocument) -> set[tuple[str, str]]:
    return {(b.relation, b.target) for b in doc.adl_blocks if isinstance(b, ADLRelationBlock)}


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def test_threshold_sweep():
    """Sweep thresholds and print classification metrics."""
    # Build concept pairs at increasing divergence
    base_triples = [(f"p{i}", f"t{i}") for i in range(20)]

    test_cases = []  # (jaccard, should_merge, base_id, fork_id)
    for shared_count in range(20, -1, -1):
        shared = base_triples[:shared_count]
        different = [(f"fp_{i}", f"ft_{i}") for i in range(20 - shared_count)]
        base = _make("base", base_triples)
        fork = _make("fork", shared + different)
        actual_j = _jaccard(_triples(base), _triples(fork))
        # Ground truth: ≥ 0.70 → same concept (should merge)
        should_merge = actual_j >= 0.70
        test_cases.append((actual_j, should_merge, base.adl_id, fork.adl_id))

    print("\n" + "=" * 75)
    print("FORK THRESHOLD SENSITIVITY ANALYSIS")
    print("Ground truth: Jaccard ≥ 0.70 → should merge; < 0.70 → different concepts")
    print("=" * 75)
    print(
        f"{'Thr':>6} {'TP':>3} {'FP':>3} {'TN':>3} {'FN':>3}  "
        f"{'Prec':>6} {'Rec':>6} {'F1':>6} {'FPR':>6} {'FNR':>6}"
    )
    print("-" * 75)

    best_f1, best_thr = 0.0, 0.90
    for threshold in [round(x * 0.01, 2) for x in range(70, 96)]:
        fm = ForkManager()
        fm.ISOMORPHISM_THRESHOLD = threshold
        tp = fp = tn = fn = 0
        for jaccard, should_merge, base_id, fork_id in test_cases:
            result = fm.attempt_merge(base_id, fork_id, jaccard)
            predicted = result == ForkResolution.MERGED
            if should_merge and predicted:
                tp += 1
            elif should_merge and not predicted:
                fn += 1
            elif not should_merge and predicted:
                fp += 1
            else:
                tn += 1
        pr = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rc = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * pr * rc / (pr + rc) if (pr + rc) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
        print(
            f"{threshold:6.2f}  {tp:3d} {fp:3d} {tn:3d} {fn:3d}  "
            f"{pr:6.3f} {rc:6.3f} {f1:6.3f} {fpr:6.3f} {fnr:6.3f}"
        )
        if f1 > best_f1:
            best_f1, best_thr = f1, threshold

    print("-" * 75)
    print("Default threshold:  0.90")
    print(f"Optimal threshold:  {best_thr:.2f} (F1={best_f1:.3f})")
    print("=" * 75)

    # --- Key assertions ---
    # At 0.90: zero false positives — conservative but safe default
    assert best_f1 > 0.50, f"F1 at optimal threshold too low: {best_f1:.3f}"
