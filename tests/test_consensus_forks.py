"""
Consensus fork scenarios: merge, parallel, and prune paths.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from adl_lite import ConsensusEngine, DiscoveryStatus, ForkResolution, parse_file
from adl_lite.consensus import ForkManager

EXAMPLES = __import__("pathlib").Path(__file__).resolve().parent.parent / "examples"


class TestForkManagerResolution:
    def test_merge_when_high_similarity(self):
        fm = ForkManager()
        result = fm.attempt_merge("concept-a", "concept-b", similarity=0.92)
        assert result == ForkResolution.MERGED

    def test_parallel_when_low_similarity(self):
        fm = ForkManager()
        result = fm.attempt_merge("concept-a", "concept-b", similarity=0.55)
        assert result == ForkResolution.PARALLEL

    def test_prune_when_idle_and_old(self):
        fm = ForkManager()
        fm.register_fork("root", "stale-fork", reason="test")
        old_created = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
        fm.creation_times["stale-fork"] = old_created

        old_access = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
        assert fm.should_prune("stale-fork", last_accessed=old_access) is True

    def test_no_prune_without_access_record(self):
        fm = ForkManager()
        fm.register_fork("root", "new-fork", reason="test")
        assert fm.should_prune("new-fork", last_accessed=None) is False


class TestConsensusEngineForks:
    @pytest.fixture
    def engine_with_fork(self):
        engine = ConsensusEngine()
        doc = parse_file(EXAMPLES / "matdo_original.md")
        engine.register(doc)
        engine.transition(
            doc.adl_id,
            DiscoveryStatus.VALIDATED,
            actor="reviewer",
            reason="Initial validation",
        )
        engine.fork(
            doc.adl_id,
            "disc-matdo-kinetic",
            actor="skeptic",
            reason="Kinetic nucleation alternative",
        )
        return engine, doc.adl_id

    def test_fork_marks_original_and_creates_chain(self, engine_with_fork):
        engine, original_id = engine_with_fork
        # Under CRDT LUB semantics, VALIDATED(3) > FORKED(2), so parent stays VALIDATED
        assert engine.get_status(original_id) == DiscoveryStatus.VALIDATED
        assert engine.get_status("disc-matdo-kinetic") == DiscoveryStatus.PROVISIONAL
        assert engine.verify_all()[original_id] is True
        assert engine.verify_all()["disc-matdo-kinetic"] is True

    def test_fork_tree_registration(self, engine_with_fork):
        engine, original_id = engine_with_fork
        tree = engine.fork_manager.get_fork_tree(original_id)
        assert tree["root"] == original_id
        assert "disc-matdo-kinetic" in tree["forks"]
        assert tree["count"] == 1

    def test_merge_path_transitions_fork_to_validated(self, engine_with_fork):
        engine, original_id = engine_with_fork
        resolution = engine.fork_manager.attempt_merge(
            original_id, "disc-matdo-kinetic", similarity=0.93
        )
        assert resolution == ForkResolution.MERGED
        engine.transition(
            "disc-matdo-kinetic",
            DiscoveryStatus.VALIDATED,
            actor="merger",
            reason="Merge: relation graphs 93% isomorphic",
        )
        assert engine.get_status("disc-matdo-kinetic") == DiscoveryStatus.VALIDATED

    def test_parallel_path_keeps_both_active(self, engine_with_fork):
        engine, original_id = engine_with_fork
        resolution = engine.fork_manager.attempt_merge(
            original_id, "disc-matdo-kinetic", similarity=0.62
        )
        assert resolution == ForkResolution.PARALLEL
        engine.transition(
            "disc-matdo-kinetic",
            DiscoveryStatus.VALIDATED,
            actor="merger",
            reason="Parallel: distinct domain metaphors retained",
        )
        # Under CRDT LUB, VALIDATED(3) > FORKED(2); parent stays VALIDATED
        assert engine.get_status(original_id) == DiscoveryStatus.VALIDATED
        assert engine.get_status("disc-matdo-kinetic") == DiscoveryStatus.VALIDATED

    def test_prune_path_archives_stale_fork(self, engine_with_fork):
        engine, original_id = engine_with_fork
        fork_id = "disc-matdo-kinetic"
        old_created = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
        engine.fork_manager.creation_times[fork_id] = old_created
        old_access = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
        assert engine.fork_manager.should_prune(fork_id, last_accessed=old_access)
        engine.transition(
            fork_id,
            DiscoveryStatus.ARCHIVED,
            actor="merger",
            reason="Prune: unreferenced fork archived",
        )
        assert engine.get_status(fork_id) == DiscoveryStatus.ARCHIVED

    def test_example_files_parse_cleanly(self):
        for name in ("matdo_original.md", "matdo_fork_kinetic.md"):
            doc = parse_file(EXAMPLES / name)
            errors = doc.validate_semantics()
            assert errors == [], f"{name}: {errors}"
