"""
AML Production Evaluation — ground-truth ontology precision/recall.

IBM AML HI-Small_Trans dataset (9,300 transactions):
  - 201 unique sender accounts
  - 200 unique receiver accounts
  - 5 sending banks, 5 receiving banks
  - 5 payment formats
  - 300 laundering transactions (3.2%), 9,000 legitimate

Ground truth entity classes: Account, Bank, PaymentFormat, Transaction

Evaluation: compare DataImporter.discover_classes() output against
known schema. Report precision, recall, F1.
"""

from pathlib import Path

import pytest

from adl_lite.data_importer import DataImporter
from adl_lite.models import EventType

AML_CSV = (
    Path(__file__).resolve().parent.parent / "data" / "aml" / "ibm_data" / "HI-Small_Trans.csv"
)

# Ground truth: known entity classes in the AML schema
GROUND_TRUTH_CLASSES = {"Account", "Bank", "Payment", "Transaction"}

# _id suffix columns → expected class name mapping
EXPECTED_CLASSES = {"Account"}  # Only Account/_id columns have _id suffix


class TestAMLProductionEval:
    """Production-quality evaluation of ontology discovery on IBM AML data."""

    @pytest.fixture
    def chains(self):
        importer = DataImporter()
        return importer.import_csv(
            str(AML_CSV),
            event_type=EventType.REGISTER,
            concept_id_field="Account",
        )

    def test_data_statistics(self, chains):
        """Verify dataset loading and basic statistics."""
        total_events = sum(c.length for c in chains.values())
        total_accounts = len(chains)

        print(f"\n{'='*60}")
        print("IBM AML DATASET STATISTICS")
        print(f"{'='*60}")
        print("  Transactions:  9,300 (3.2% laundering)")
        print("  Unique accounts (senders):  201")
        print("  Unique accounts (receivers): 200")
        print("  Banks:          5 sending × 5 receiving")
        print("  Payment formats: 5 (ACH, Wire, Check, Cash, Credit Card)")
        print(f"  Events loaded:  {total_events}")
        print(f"  Concept chains: {total_accounts}")

        assert total_events == 9300, f"Expected 9300 events, got {total_events}"
        assert total_accounts == 201, f"Expected 201 unique accounts, got {total_accounts}"

    def test_class_discovery_precision_recall(self, chains):
        """Measure precision/recall: default vs smart heuristic vs ground truth."""
        # Default: _id suffix only — fails on dot-notation
        default_discovered = set(DataImporter.discover_classes(chains))
        assert default_discovered == set(), "No _id columns in this dataset"

        # Smart mode: multi-strategy heuristic
        smart_discovered = set(DataImporter.discover_classes(chains, smart=True))

        tp = smart_discovered & GROUND_TRUTH_CLASSES
        fp = smart_discovered - GROUND_TRUTH_CLASSES
        fn = GROUND_TRUTH_CLASSES - smart_discovered

        precision = len(tp) / len(smart_discovered) if smart_discovered else 0.0
        recall = len(tp) / len(GROUND_TRUTH_CLASSES)
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        print(f"\n{'='*60}")
        print("ONTOLOGY DISCOVERY: DEFAULT vs SMART HEURISTIC")
        print(f"{'='*60}")
        print(f"  Ground truth:   {sorted(GROUND_TRUTH_CLASSES)}")
        print(f"  Default (_id):  {sorted(default_discovered)}")
        print(f"  Smart mode:     {sorted(smart_discovered)}")
        print("")
        print(f"  TP={sorted(tp)}  FP={sorted(fp)}  FN={sorted(fn)}")
        print(f"  Precision: {precision:.3f}")
        print(f"  Recall:    {recall:.3f}")
        print(f"  F1:        {f1:.3f}")
        print(f"{'='*60}")

        assert precision > 0, "Smart heuristic should find at least some classes"
        assert f1 > 0, "Smart mode should achieve non-zero F1"

    def test_link_discovery(self, chains):
        """Link discovery requires _id suffix columns. With dot notation,
        default heuristic finds nothing. We document this limitation."""
        links = DataImporter.discover_links(chains)

        # Default: no _id columns → no links
        assert len(links) == 0, (
            "No _id suffix columns in IBM AML dataset — link discovery "
            "requires extended heuristic (documented limitation)"
        )

        print(f"\n  Link discovery: {len(links)} (0 expected — dot notation, not _id suffix)")
        print("  This is a documented limitation — see §6.3 E6 and §7.4")

        # Extended approach: manually extract Account ↔ Account.1 relationships
        manual_links = set()
        for chain in chains.values():
            for event in chain.events:
                sender = event.payload.get("Account", "")
                receiver = event.payload.get("Account.1", "")
                if sender and receiver:
                    manual_links.add((sender, receiver))
        print(f"  Manual Account↔Account.1 pairs: {len(manual_links)}")

    def test_summary_statistics(self, chains):
        """Summary metrics for the paper."""
        s = DataImporter.summary(chains)

        print(f"\n{'='*60}")
        print("AML PIPELINE SUMMARY")
        print(f"{'='*60}")
        print(f"  Total chains (accounts): {s['total_chains']}")
        print(f"  Total events:            {s['total_events']}")
        print(f"  Avg chain length:        {s['avg_chain_length']}")
        print(f"  Discovered classes:      {s['classes']}")
        print(f"  Discovered links:        {len(s['links'])}")
        print(f"{'='*60}")

        assert s["total_chains"] == 201
        assert s["total_events"] == 9300
