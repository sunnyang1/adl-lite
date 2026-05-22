"""Tests for AML dataset loader and memory indexing."""

from __future__ import annotations

import tempfile
from pathlib import Path

from adl_lite import parse_file
from adl_lite.validator import ADLValidator
from data.aml.loader import (
    CONCEPT_TOPICS,
    ensure_dataset,
    index_all,
    load_manifest,
    load_queries,
)

DATA = Path(__file__).resolve().parent.parent / "data" / "aml"


class TestAMLDataset:
    def test_ensure_generates_twenty_concepts(self):
        ensure_dataset()
        manifest = load_manifest()
        assert manifest["count"] == 20
        assert len(manifest["concepts"]) == 20

    def test_queries_count(self):
        ensure_dataset()
        queries = load_queries()
        assert len(queries) == 15

    def test_concept_files_validate(self):
        ensure_dataset()
        validator = ADLValidator()
        for entry in load_manifest()["concepts"]:
            doc = parse_file(DATA / entry["path"])
            errors = validator.validate_document(doc)
            assert errors == [], f"{entry['adl_id']}: {errors}"

    def test_index_all_populates_memory(self):
        ensure_dataset()
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "test.db")
            mem = index_all(db)
            assert len(mem.hot) == 20
            mem.close()

    def test_manifest_matches_topics(self):
        ensure_dataset()
        ids = {c["adl_id"] for c in load_manifest()["concepts"]}
        expected = {t[0] for t in CONCEPT_TOPICS}
        assert ids == expected

    def test_queries_have_relevant_ids(self):
        ensure_dataset()
        concept_ids = {c["adl_id"] for c in load_manifest()["concepts"]}
        for q in load_queries():
            assert "relevant" in q
            assert all(r in concept_ids for r in q["relevant"])
