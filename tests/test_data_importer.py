"""
Tests for adl_lite.data_importer — CSV/JSON import and ontology discovery.

Covers:
    - import_csv: basic, with prefix, actor_field, timestamp_field, empty CSV
    - import_json_events: basic, empty file
    - discover_classes: from _id fields, no _id fields
    - discover_links: from co-occurring _id pairs, threshold filtering
    - summary: statistics, empty chains
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from adl_lite.data_importer import DataImporter
from adl_lite.models import EventType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def importer() -> DataImporter:
    return DataImporter()


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    """Create a small CSV with transaction-like data."""
    path = tmp_path / "transactions.csv"
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "transaction_id",
                "account_id",
                "amount",
                "currency",
                "timestamp",
                "actor",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "transaction_id": "tx001",
                "account_id": "acc123",
                "amount": "1000",
                "currency": "USD",
                "timestamp": "2024-01-15T10:00:00Z",
                "actor": "agent_a",
            }
        )
        writer.writerow(
            {
                "transaction_id": "tx002",
                "account_id": "acc456",
                "amount": "500",
                "currency": "EUR",
                "timestamp": "2024-01-15T11:00:00Z",
                "actor": "agent_b",
            }
        )
        writer.writerow(
            {
                "transaction_id": "tx003",
                "account_id": "acc123",
                "amount": "750",
                "currency": "USD",
                "timestamp": "2024-01-15T12:00:00Z",
                "actor": "agent_c",
            }
        )
    return path


@pytest.fixture
def simple_csv(tmp_path: Path) -> Path:
    """A CSV with only concept_id column."""
    path = tmp_path / "simple.csv"
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "value"])
        writer.writeheader()
        writer.writerow({"id": "a", "value": "1"})
        writer.writerow({"id": "b", "value": "2"})
        writer.writerow({"id": "a", "value": "3"})
    return path


# ---------------------------------------------------------------------------
# import_csv
# ---------------------------------------------------------------------------


class TestImportCsv:
    def test_basic_import(self, importer: DataImporter, sample_csv: Path):
        chains = importer.import_csv(
            sample_csv,
            event_type=EventType.REGISTER,
            concept_id_field="account_id",
        )
        assert len(chains) == 2  # acc123 and acc456
        assert "acc123" in chains
        assert "acc456" in chains
        # acc123 has 2 events
        assert chains["acc123"].length == 2
        # acc456 has 1 event
        assert chains["acc456"].length == 1

    def test_import_with_prefix(self, importer: DataImporter, sample_csv: Path):
        chains = importer.import_csv(
            sample_csv,
            event_type=EventType.REGISTER,
            concept_id_field="account_id",
            concept_prefix="acct:",
        )
        assert "acct:acc123" in chains
        assert "acct:acc456" in chains

    def test_import_with_actor_field(self, importer: DataImporter, sample_csv: Path):
        chains = importer.import_csv(
            sample_csv,
            event_type=EventType.REGISTER,
            concept_id_field="account_id",
            actor_field="actor",
        )
        chain = chains["acc123"]
        events = chain.events
        assert events[0].actor == "agent_a"
        assert events[1].actor == "agent_c"

    def test_import_with_timestamp_field(self, importer: DataImporter, sample_csv: Path):
        chains = importer.import_csv(
            sample_csv,
            event_type=EventType.REGISTER,
            concept_id_field="account_id",
            timestamp_field="timestamp",
        )
        event = chains["acc123"].events[0]
        assert event.timestamp == "2024-01-15T10:00:00Z"

    def test_import_preserves_payload(self, importer: DataImporter, sample_csv: Path):
        chains = importer.import_csv(
            sample_csv,
            event_type=EventType.REGISTER,
            concept_id_field="account_id",
        )
        event = chains["acc123"].events[0]
        assert event.payload["transaction_id"] == "tx001"
        assert event.payload["amount"] == "1000"
        assert event.payload["currency"] == "USD"

    def test_import_empty_csv(self, importer: DataImporter, tmp_path: Path):
        path = tmp_path / "empty.csv"
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["id"])
            writer.writeheader()
        chains = importer.import_csv(path, EventType.REGISTER, "id")
        assert chains == {}

    def test_import_simple(self, importer: DataImporter, simple_csv: Path):
        chains = importer.import_csv(
            simple_csv,
            event_type=EventType.REGISTER,
            concept_id_field="id",
        )
        assert len(chains) == 2
        assert chains["a"].length == 2
        assert chains["b"].length == 1

    def test_import_missing_concept_id(self, importer: DataImporter, tmp_path: Path):
        """Rows with missing concept_id_field get empty string as concept_id."""
        path = tmp_path / "missing_id.csv"
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["other_field"])
            writer.writeheader()
            writer.writerow({"other_field": "data1"})
            writer.writerow({"other_field": "data2"})
        chains = importer.import_csv(path, EventType.REGISTER, "nonexistent_field")
        # Both rows get empty concept_id — grouped into one chain
        assert len(chains) == 1
        assert "" in chains
        assert chains[""].length == 2


# ---------------------------------------------------------------------------
# import_json_events
# ---------------------------------------------------------------------------


class TestImportJsonEvents:
    def test_basic_import(self, importer: DataImporter, tmp_path: Path):
        path = tmp_path / "events.jsonl"
        lines = [
            {
                "concept_id": "c1",
                "event_type": "register",
                "actor": "system",
                "payload": {"key": "val1"},
            },
            {
                "concept_id": "c2",
                "event_type": "validate",
                "actor": "agent_x",
                "reasoning": "looks good",
                "payload": {"key": "val2"},
            },
        ]
        with open(path, "w") as f:
            for line in lines:
                f.write(json.dumps(line) + "\n")

        events = importer.import_json_events(path)
        assert len(events) == 2
        assert events[0].concept_id == "c1"
        assert events[0].event_type == EventType.REGISTER
        assert events[0].payload == {"key": "val1"}
        assert events[1].concept_id == "c2"
        assert events[1].event_type == EventType.VALIDATE

    def test_import_empty_file(self, importer: DataImporter, tmp_path: Path):
        path = tmp_path / "empty.jsonl"
        path.write_text("")
        events = importer.import_json_events(path)
        assert events == []

    def test_import_skips_blank_lines(self, importer: DataImporter, tmp_path: Path):
        path = tmp_path / "with_blanks.jsonl"
        path.write_text('\n{"concept_id": "c1", "event_type": "register", "actor": "s"}\n\n')
        events = importer.import_json_events(path)
        assert len(events) == 1


# ---------------------------------------------------------------------------
# discover_classes
# ---------------------------------------------------------------------------


class TestDiscoverClasses:
    def test_discovers_from_id_fields(self, importer: DataImporter, sample_csv: Path):
        chains = importer.import_csv(
            sample_csv,
            event_type=EventType.REGISTER,
            concept_id_field="account_id",
        )
        classes = DataImporter.discover_classes(chains)
        assert "Account" in classes
        assert "Transaction" in classes

    def test_custom_id_pattern(self, importer: DataImporter, sample_csv: Path):
        chains = importer.import_csv(
            sample_csv,
            event_type=EventType.REGISTER,
            concept_id_field="account_id",
        )
        classes = DataImporter.discover_classes(chains, id_field_pattern="_id")
        assert classes == sorted(classes)

    def test_no_id_fields(self, importer: DataImporter, simple_csv: Path):
        chains = importer.import_csv(
            simple_csv,
            event_type=EventType.REGISTER,
            concept_id_field="id",
        )
        classes = DataImporter.discover_classes(chains)
        # "id" field does exist but it's the concept_id itself, which gets
        # class name "I" (strip "_id" from "id") — actually "id" doesn't end
        # with "_id"... so it won't be detected.
        # "value" doesn't end with _id either.
        assert classes == []


# ---------------------------------------------------------------------------
# discover_links
# ---------------------------------------------------------------------------


class TestDiscoverLinks:
    def test_discovers_links(self, importer: DataImporter, sample_csv: Path):
        chains = importer.import_csv(
            sample_csv,
            event_type=EventType.REGISTER,
            concept_id_field="account_id",
        )
        links = DataImporter.discover_links(chains)
        # transaction_id and account_id co-occur in every row
        assert len(links) > 0
        # Check the link structure
        assert any("Transaction" in link and "Account" in link for link in links)

    def test_no_links_without_id_fields(self, importer: DataImporter, simple_csv: Path):
        chains = importer.import_csv(
            simple_csv,
            event_type=EventType.REGISTER,
            concept_id_field="id",
        )
        links = DataImporter.discover_links(chains)
        assert links == []

    def test_threshold_filtering(self, importer: DataImporter, tmp_path: Path):
        """Links with count < 2 should be excluded."""
        path = tmp_path / "sparse.csv"
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["a_id", "b_id", "c_id"])
            writer.writeheader()
            # Only one row — each pair appears only once (< 2)
            writer.writerow({"a_id": "1", "b_id": "2", "c_id": "3"})
        chains = importer.import_csv(path, EventType.REGISTER, "a_id")
        links = DataImporter.discover_links(chains)
        # All pairs have count=1, which is < 2 threshold
        assert links == []


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------


class TestSummary:
    def test_summary_statistics(self, importer: DataImporter, sample_csv: Path):
        chains = importer.import_csv(sample_csv, EventType.REGISTER, concept_id_field="account_id")
        s = DataImporter.summary(chains)
        assert s["total_chains"] == 2
        assert s["total_events"] == 3
        assert s["avg_chain_length"] == 1.5
        assert "classes" in s
        assert "links" in s

    def test_summary_empty(self, importer: DataImporter):
        s = DataImporter.summary({})
        assert s["total_chains"] == 0
        assert s["total_events"] == 0
        assert s["avg_chain_length"] == 0
        assert s["classes"] == []
        assert s["links"] == []
