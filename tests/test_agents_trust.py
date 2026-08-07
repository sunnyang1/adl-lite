"""M4 trust-closure tests (TR-01..11, offline deterministic, no network).

Covers: B4 org diversity (same-org reject / cross-org pass), offline cache
determinism, default zero-change, formula bounds, reputation ordering,
did:ethr rejection, CLI trust-check, and the task-component reputation
statistics (M4v2, per-task dedup).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from adl_lite.agents.identity import AgentRegistry
from adl_lite.agents.task import TaskRegistry
from adl_lite.agents.trust import (
    DidWebAffiliationResolver,
    Reputation,
    ReputationScore,
    _clamp01,
)
from adl_lite.consensus import ConsensusEngine
from adl_lite.exceptions import ADLUnsupportedDIDMethodError
from adl_lite.models import ADLDocument, ADLFrontMatter, ADLType, Event, EventChain, EventType
from adl_lite.trust_model import ConsensusConfig, TrustValidator


class _StubProvider:
    """Deterministic diversity provider for B4 tests (no network)."""

    def __init__(self, mapping: dict[str, tuple[str, str]]) -> None:
        self._mapping = mapping

    def diversity_key(self, actor: str) -> tuple[str, str]:
        return self._mapping.get(actor, ("key", actor))


def _discovery_chain(
    validators: list[str],
    discoverer: str = "alice",
    cid: str = "cap-trust-1",
) -> EventChain:
    chain = EventChain(concept_id=cid)
    chain.append(Event(concept_id=cid, event_type=EventType.REGISTER, actor=discoverer, payload={}))
    for v in validators:
        chain.append(Event(concept_id=cid, event_type=EventType.VALIDATE, actor=v, payload={}))
    return chain


def _engine_with_discovery(
    adl_id: str = "cap-rep-1",
    validator: str = "did:key:v1",
) -> ConsensusEngine:
    from adl_lite.models import DiscoveryStatus

    engine = ConsensusEngine(dev_mode=True)
    doc = ADLDocument(
        front_matter=ADLFrontMatter(
            adl_type=ADLType.CONCEPT,
            adl_id=adl_id,
            scope="public",
        )
    )
    engine.register(doc)
    if validator:
        engine.transition(adl_id, DiscoveryStatus.VALIDATED, actor=validator)
    return engine


# ----------------------------------------------------------------------
# TR-01..04: B4 diversity + zero-change
# ----------------------------------------------------------------------


class TestB4Diversity:
    def test_same_org_rejected(self) -> None:
        """TR-01: two same-org validators collapse to one diversity key."""
        provider = _StubProvider(
            {
                "v1": ("org", "acme"),
                "v2": ("org", "acme"),
            }
        )
        chain = _discovery_chain(validators=["v1", "v2"])
        result = TrustValidator(diversity_provider=provider).validate_event_chain(
            chain,
            ConsensusConfig(
                mode="dev",
                min_distinct_validators=2,
                enforce_validator_diversity=True,
            ),
        )
        assert result.valid is False
        assert any("diversity" in e.lower() for e in result.errors)

    def test_cross_org_passes(self) -> None:
        """TR-02: two different-org validators satisfy diversity."""
        provider = _StubProvider(
            {
                "v1": ("org", "acme"),
                "v2": ("org", "globex"),
            }
        )
        chain = _discovery_chain(validators=["v1", "v2"])
        result = TrustValidator(diversity_provider=provider).validate_event_chain(
            chain,
            ConsensusConfig(
                mode="dev",
                min_distinct_validators=2,
                enforce_validator_diversity=True,
            ),
        )
        assert result.valid is True
        assert result.diversity_satisfied is True

    def test_default_zero_change(self) -> None:
        """TR-04: no provider/reputation -> behaviour identical to Phase-1."""
        # Same-org validators WITHOUT a provider are NOT collapsed (Phase-1
        # identity-scoped diversity key): chain is valid.
        chain = _discovery_chain(validators=["v1", "v2"])
        result = TrustValidator().validate_event_chain(
            chain,
            ConsensusConfig(
                mode="dev", min_distinct_validators=2, enforce_validator_diversity=True
            ),
        )
        assert result.valid is True  # identity keys are distinct

    def test_offline_cache_determinism(self, tmp_path: Path) -> None:
        """TR-03: preset cache + offline=True -> org from cache, no network."""
        import hashlib

        did = "did:web:example.com:agent1"
        key = hashlib.sha256(did.encode()).hexdigest()
        cache = tmp_path / "affil.json"
        cache.write_text(
            json.dumps(
                {
                    key: {"org": "org:example.com", "ts": "2099-01-01T00:00:00"},
                }
            ),
            encoding="utf-8",
        )
        resolver = DidWebAffiliationResolver(cache_path=cache, offline=True)
        assert resolver.organization_of(did) == "org:example.com"
        assert resolver.diversity_key(did) == ("org", "org:example.com")
        assert key in resolver._cache  # noqa: SLF001

    def test_ethr_still_rejected(self) -> None:
        """TR-07: did:ethr validators raise (Phase-1 behaviour preserved)."""
        chain = _discovery_chain(validators=["did:ethr:0xabc"])
        with pytest.raises(ADLUnsupportedDIDMethodError):
            TrustValidator().validate_event_chain(
                chain, ConsensusConfig(mode="dev", min_distinct_validators=1)
            )


# ----------------------------------------------------------------------
# TR-05/06: formula bounds + ordering
# ----------------------------------------------------------------------


class TestReputation:
    def test_formula_bounds(self) -> None:
        """TR-05: _clamp01 hard bounds; formula_v1 floor/cap sane."""
        rep = Reputation(ConsensusEngine(), AgentRegistry())
        assert _clamp01(-1.0) == 0.0
        assert _clamp01(2.0) == 1.0
        s0 = ReputationScore()
        assert 0.0 <= rep.formula_v1(s0) <= 1.0
        # All-positive stats push above the neutral 0.5 baseline.
        s_high = ReputationScore(validate_count=10, fork_merge_rate=1.0)
        assert rep.formula_v1(s_high) > rep.formula_v1(s0)
        # Heavy deprecation drags the score down.
        s_bad = ReputationScore(validate_count=0, deprecate_count=5, deprecation_rate=1.0)
        assert rep.formula_v1(s_bad) < rep.formula_v1(s0)

    def test_ordering_intuitive(self) -> None:
        """TR-06: more validators > fewer > heavy deprecation."""
        rep = Reputation(ConsensusEngine(), AgentRegistry())
        good = rep.formula_v2(
            ReputationScore(validate_count=8, task_success_rate=1.0, fork_merge_rate=1.0)
        )
        mid = rep.formula_v2(ReputationScore(validate_count=2, task_success_rate=0.5))
        bad = rep.formula_v2(ReputationScore(deprecate_count=9, deprecation_rate=1.0))
        assert good > mid > bad

    def test_task_component_dedup(self) -> None:
        """TR-09 + P1-6: rework submits count ONCE per task."""
        engine = ConsensusEngine(dev_mode=True)
        reg = TaskRegistry(engine=engine)
        task = reg.create_task("x")
        # Rework loop: claim -> submit -> reject -> claim -> submit -> accept.
        reg.claim(task.task_id, "a1")
        reg.submit(task.task_id, "a1", "cap-1")
        reg.validate_result(task.task_id, "r1", accepted=False)
        reg.claim(task.task_id, "a1")
        reg.submit(task.task_id, "a1", "cap-1")
        reg.validate_result(task.task_id, "r2", accepted=True)
        reg.close(task.task_id, "r2", "accepted")

        rep = Reputation(engine, AgentRegistry(engine=engine))
        s = rep.score("a1")
        assert s.submit_count == 1  # deduped despite two submits
        assert s.accepted_count == 1
        assert s.task_success_rate == 1.0

    def test_all_rejected_no_task_credit(self) -> None:
        """TR-10: 2 submits 0 accepted -> rate 0.0, formula_v2 no task boost."""
        engine = ConsensusEngine(dev_mode=True)
        reg = TaskRegistry(engine=engine)
        t1 = reg.create_task("x1")
        reg.claim(t1.task_id, "a1")
        reg.submit(t1.task_id, "a1", "cap-1")
        reg.validate_result(t1.task_id, "r1", accepted=False)
        t2 = reg.create_task("x2")
        reg.claim(t2.task_id, "a1")
        reg.submit(t2.task_id, "a1", "cap-2")
        reg.validate_result(t2.task_id, "r2", accepted=False)

        rep = Reputation(engine, AgentRegistry(engine=engine))
        s = rep.score("a1")
        assert s.submit_count == 2
        assert s.accepted_count == 0
        assert s.task_success_rate == 0.0
        base = rep.formula_v2(ReputationScore())
        assert rep.formula_v2(s) == base  # no task credit, no penalty

    def test_discovery_stats_counted(self) -> None:
        """M4v1: VALIDATE/FORK/DEPRECATE events feed the discovery component."""
        from adl_lite.models import DiscoveryStatus

        engine = _engine_with_discovery("cap-a", validator="did:key:agent-x")
        # A FORK event initiated by the same agent.
        engine.transition("cap-a", DiscoveryStatus.FORKED, actor="did:key:agent-x")
        # Register a fork chain so it counts as "resolved" (proxy).
        fork_doc = ADLDocument(
            front_matter=ADLFrontMatter(
                adl_type=ADLType.CONCEPT, adl_id="cap-a-fork", scope="public"
            )
        )
        engine.register(fork_doc)
        engine.fork_manager.register_fork("cap-a", "cap-a-fork")

        rep = Reputation(engine, AgentRegistry(engine=engine))
        s = rep.score("did:key:agent-x")
        assert s.validate_count >= 1
        assert s.fork_count >= 1
        assert s.deprecation_rate == 0.0


# ----------------------------------------------------------------------
# TR-08: CLI trust-check
# ----------------------------------------------------------------------


class TestCliTrustCheck:
    def test_trust_check_cli(self, tmp_path: Path) -> None:
        """TR-08: `adl-lite agent trust-check --diversity` prints valid/errors."""
        from adl_lite.cli import _build_parser

        state = str(tmp_path / "tc.json")
        # Non-DID validator: B2 signature check is skipped, so the single
        # validator is valid under diversity mode (min_distinct_validators=1).
        engine = _engine_with_discovery("cap-tc-1", validator="validator-1")
        from adl_lite.cli import _save_engine

        _save_engine(engine, Path(state))
        parser = _build_parser()
        ns = parser.parse_args(
            ["agent", "trust-check", "cap-tc-1", "--diversity", "--state", state]
        )
        assert ns.func(ns) == 0  # single validator, diversity satisfied
        # Without --diversity, prod N_min=2 -> single validator is invalid.
        ns2 = parser.parse_args(["agent", "trust-check", "cap-tc-1", "--state", state])
        assert ns2.func(ns2) == 1  # insufficient validators -> exit 1
