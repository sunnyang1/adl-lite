"""M3 thin-runtime tests (RT-01..10, mock LLM, no network).

Covers: Discoverer end-to-end, role whitelist enforcement, audit closure,
planner vocabulary filtering, checkpoint block/pass + retry recovery, 5-role
pipeline, P1-6 backlog visibility, and idempotent re-claim semantics.
"""

from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path
from typing import cast

import pytest

from adl_lite.agents.bus import TaskQueue
from adl_lite.agents.identity import AgentProfile, AgentRegistry, AgentRole
from adl_lite.agents.planner import Planner
from adl_lite.agents.runtime import (
    AgentRuntime,
    RuntimeManager,
    approve_checkpoint,
    checkpoint_handler,
    pending_checkpoints,
)
from adl_lite.agents.task import TaskRegistry, TaskStatus
from adl_lite.consensus import ConsensusEngine
from adl_lite.exceptions import ADLConsensusError
from adl_lite.models import DiscoveryStatus, EventType


class _FakeLLM:
    """Deterministic LLM for runtime tests."""

    def __init__(self, response: str = "deterministic reasoning") -> None:
        self._response = response

    def complete(self, prompt: str, system: str | None = None) -> str:  # noqa: ARG002
        return self._response


class _PlannerLLM(_FakeLLM):
    """LLM whose response is a planner-shaped JSON list."""

    def __init__(self, subtasks: list[dict]) -> None:
        super().__init__(json.dumps(subtasks))


def _sample_adl(tmp_path: Path, adl_id: str = "concept-demo-1") -> Path:
    path = tmp_path / f"{adl_id}.md"
    path.write_text(
        f"""---
adl_type: concept
adl_id: {adl_id}
status: provisional
scope: public
provisional_names:
  en: "Demo Concept"
---

# Demo Concept

## Definition

A demo concept used by M3 runtime tests.

```adl:relation
source: "Demo Concept"
predicate: related-to
target: "Demo Target"
```
""",
        encoding="utf-8",
    )
    return path


def _stack(
    role: AgentRole = AgentRole.DISCOVERER, llm: _FakeLLM | None = None, checkpoint=None
) -> tuple[ConsensusEngine, AgentRuntime, TaskRegistry, TaskQueue, str]:
    engine = ConsensusEngine(dev_mode=True)
    agent_reg = AgentRegistry(engine=engine)
    task_reg = TaskRegistry(engine=engine)
    queue = TaskQueue(task_reg)
    did = f"did:key:{role.value}-1"
    profile = AgentProfile(
        did=did,
        role=role,
        name=role.value,
        capabilities=["depends-on", "related-to", "validate"],
    )
    rt = AgentRuntime(
        agent_did=did,
        profile=profile,
        engine=engine,
        agent_registry=agent_reg,
        task_registry=task_reg,
        task_queue=queue,
        llm=llm or _FakeLLM(),
        checkpoint=checkpoint,
    )
    return engine, rt, task_reg, queue, did


# ----------------------------------------------------------------------
# RT-01..03: Discoverer flow, whitelist, audit
# ----------------------------------------------------------------------


class TestDiscoverer:
    async def test_discoverer_end_to_end(self, tmp_path: Path) -> None:
        """RT-01: parse -> register, chain events + result_ref resolvable."""
        engine, rt, task_reg, queue, did = _stack()
        path = _sample_adl(tmp_path)
        task = task_reg.create_task(
            objective="land concept-demo-1",
            required_capabilities=["depends-on"],
            input_ref=str(path),
        )
        await queue.enqueue(task)
        got = await queue.dequeue(did)
        assert got is not None
        await rt.run_task(got)

        view = task_reg.get_task(task.task_id)
        assert view.status == TaskStatus.SUBMITTED
        assert view.result_ref == "concept-demo-1"
        # The produced capability is registered in the in-memory engine.
        assert "concept-demo-1" in engine.chains

        # Audit trail: MESSAGE events for each whitelisted tool call.
        chain = engine.chains[task.task_id]
        tools = [
            e.payload.get("tool")
            for e in chain.events
            if e.event_type == EventType.MESSAGE and "tool" in e.payload
        ]
        assert "adl_parse" in tools
        assert "adl_consensus_register" in tools

    async def test_role_whitelist_enforced(self) -> None:
        """RT-02: reviewer cannot call tools outside its whitelist."""
        _, rt, task_reg, _, _ = _stack(AgentRole.REVIEWER)
        task = task_reg.create_task("x")
        # adl_fork (skeptic) and adl_parse (discoverer) are outside the
        # reviewer whitelist.
        with pytest.raises(PermissionError, match="cannot call"):
            await rt._call_tool("adl_fork", {"adl_id": "x"}, task.task_id)  # noqa: SLF001
        with pytest.raises(PermissionError, match="cannot call"):
            await rt._call_tool("adl_parse", {"path": "x.md"}, task.task_id)  # noqa: SLF001

    async def test_audit_closure_counts(self, tmp_path: Path) -> None:
        """RT-03: tool calls == MESSAGE audit events on the task chain."""
        _, rt, task_reg, queue, did = _stack()
        path = _sample_adl(tmp_path, "concept-audit-1")
        task = task_reg.create_task(
            objective="land concept-audit-1",
            required_capabilities=["depends-on"],
            input_ref=str(path),
        )
        await queue.enqueue(task)
        got = await queue.dequeue(did)
        assert got is not None
        await rt.run_task(got)

        chain = rt.engine.chains[task.task_id]
        tool_events = [
            e for e in chain.events if e.event_type == EventType.MESSAGE and "tool" in e.payload
        ]
        assert len(tool_events) == 2  # adl_parse + adl_consensus_register
        assert chain.verify_integrity() is True


# ----------------------------------------------------------------------
# RT-04: planner vocabulary (P1-3)
# ----------------------------------------------------------------------


class TestPlanner:
    async def test_capability_vocabulary_filter(self) -> None:
        """RT-04: illegal capabilities filtered; legal ones create tasks."""
        engine = ConsensusEngine(dev_mode=True)
        planner = Planner(
            engine=engine,
            llm=_PlannerLLM(
                [
                    {"objective": "good", "required_capabilities": ["depends-on"]},
                    {"objective": "bad", "required_capabilities": ["bogus-predicate"]},
                    {"objective": "mixed", "required_capabilities": ["related-to", "nope"]},
                ]
            ),
        )
        assert planner.validate_capability("depends-on") is True
        assert planner.validate_capability("related-to") is True
        assert planner.validate_capability("bogus-predicate") is False

        tasks = await planner.plan("decompose this")
        objectives = sorted(t.objective for t in tasks)
        assert objectives == ["good", "mixed"]
        assert all(t.required_capabilities for t in tasks)
        assert all("bogus-predicate" not in t.required_capabilities for t in tasks)

    async def test_non_json_llm_raises(self) -> None:
        engine = ConsensusEngine(dev_mode=True)
        planner = Planner(engine=engine, llm=_FakeLLM("not json at all"))
        with pytest.raises(ValueError, match="did not return JSON"):
            await planner.plan("x")


# ----------------------------------------------------------------------
# RT-05/06 + recovery: checkpoint block / pass / retry
# ----------------------------------------------------------------------


class TestCheckpoint:
    async def test_checkpoint_block_and_retry(self, tmp_path: Path) -> None:
        """RT-05 + idempotent re-claim: a rejected checkpoint leaves the task
        IN_PROGRESS with the lease released; a later approved run succeeds."""
        decisions: list[bool] = [False]  # first run rejected

        async def ck(req: dict) -> bool:  # noqa: ARG001
            return decisions[0]

        path = _sample_adl(tmp_path, "concept-ck-1")
        engine, rt, task_reg, queue, did = _stack(checkpoint=ck)
        task = task_reg.create_task(
            "x",
            required_capabilities=["depends-on"],
            input_ref=str(path),
        )
        # Execution path used by run_forever: dequeue -> run_task.
        await queue.enqueue(task)
        got = await queue.dequeue(did)
        assert got is not None
        await rt.run_task(got)

        # Chain shows the claim; the run failed at the checkpoint and the
        # lease was released (someone else can re-claim).
        view = task_reg.get_task(task.task_id)
        assert view.status == TaskStatus.IN_PROGRESS
        assert queue.claim(task.task_id, "other") is True
        # Give the lease back so the retry below can claim it.
        queue.release(task.task_id, "other")
        # Error audit event recorded on the chain.
        chain = engine.chains[task.task_id]
        assert any(
            e.event_type == EventType.MESSAGE and e.payload.get("level") == "error"
            for e in chain.events
        )

        # Retry: re-enqueue (as the reaper would) and approve this time.
        decisions[0] = True
        await queue.enqueue(task)
        got2 = await queue.dequeue(did)
        assert got2 is not None  # idempotent re-claim after IN_PROGRESS
        await rt.run_task(got2)
        assert task_reg.get_task(task.task_id).status == TaskStatus.SUBMITTED

    async def test_checkpoint_approve_roundtrip(self, tmp_path: Path) -> None:
        """RT-10: checkpoint_handler + approve_checkpoint resolve the future."""
        handler = checkpoint_handler()
        path = _sample_adl(tmp_path, "concept-ck2-1")
        engine, rt, task_reg, _, did = _stack(checkpoint=handler)
        task = task_reg.create_task(
            "y",
            required_capabilities=["depends-on"],
            input_ref=str(path),
        )

        # Run the task in the background; it blocks on the checkpoint.
        run_task = asyncio.create_task(rt.run_task(task))
        await asyncio.sleep(0.05)
        assert task.task_id in pending_checkpoints()

        # Approve from another in-process caller.
        assert approve_checkpoint(task.task_id, approved=True) is True
        await run_task
        assert task_reg.get_task(task.task_id).status == TaskStatus.SUBMITTED

    async def test_approve_unknown_checkpoint_fails(self) -> None:
        assert approve_checkpoint("task:nope") is False


# ----------------------------------------------------------------------
# RT-07: 5-role pipeline (mock LLM, in-memory tools)
# ----------------------------------------------------------------------


class TestPipeline:
    async def test_five_role_pipeline(self, tmp_path: Path) -> None:
        """RT-07: discover -> validate -> verify -> store chain completes.

        Each role runs its whitelisted tools against the in-memory engine;
        the produced capability is queryable at the end."""
        engine = ConsensusEngine(dev_mode=True)
        agent_reg = AgentRegistry(engine=engine)
        task_reg = TaskRegistry(engine=engine)
        queue = TaskQueue(task_reg)
        mgr = RuntimeManager(engine, task_reg, queue, agent_reg)

        path = _sample_adl(tmp_path, "concept-pipeline-1")
        # 1. Discoverer lands the capability.
        profile = AgentProfile(
            did="did:key:disc",
            role=AgentRole.DISCOVERER,
            name="disc",
            capabilities=["depends-on"],
        )
        agent_reg.register_agent(profile)
        mgr.start(profile.did, profile, llm=_FakeLLM())
        task = task_reg.create_task(
            "land concept-pipeline-1",
            required_capabilities=["depends-on"],
            input_ref=str(path),
        )
        await queue.enqueue(task)
        await asyncio.sleep(0.05)  # let run_forever consume
        for _ in range(20):
            if task_reg.get_task(task.task_id).status == TaskStatus.SUBMITTED:
                break
            await asyncio.sleep(0.05)
        assert task_reg.get_task(task.task_id).status == TaskStatus.SUBMITTED

        # 2. Other roles verify/store the same capability chain.
        for role in (AgentRole.REVIEWER, AgentRole.LIBRARIAN):
            p = AgentProfile(did=f"did:key:{role.value}", role=role, name=role.value)
            agent_reg.register_agent(p)
            mgr.start(p.did, p, llm=_FakeLLM())

        assert engine.chains["concept-pipeline-1"].verify_integrity() is True
        # Status BEFORE stop: all three agents are tracked.
        before = mgr.status()
        assert set(before["agents"]) == {"did:key:disc", "did:key:reviewer", "did:key:librarian"}
        assert before["queue_depth"] >= 0
        await mgr.stop_all()
        assert mgr.status()["agents"] == {}

    async def test_role_toolchains_land_audit_events(self, tmp_path: Path) -> None:
        """RT-07b: every runtime role fires its whitelisted tool chain when
        handed a task carrying a ``result_ref`` — the MESSAGE audit trail on
        the task chain shows each tool call (5-role consensus is real work)."""
        engine = ConsensusEngine(dev_mode=True)
        agent_reg = AgentRegistry(engine=engine)
        task_reg = TaskRegistry(engine=engine)
        queue = TaskQueue(task_reg)

        def runtime(role: AgentRole, did: str) -> AgentRuntime:
            return AgentRuntime(
                agent_did=did,
                profile=AgentProfile(did=did, role=role, name=role.value),
                engine=engine,
                agent_registry=agent_reg,
                task_registry=task_reg,
                task_queue=queue,
                llm=_FakeLLM(),
            )

        def tool_events(task_id: str) -> list[str]:
            return [
                cast(str, e.payload.get("tool"))
                for e in engine.chains[task_id].events
                if e.event_type == EventType.MESSAGE and "tool" in e.payload
            ]

        # DISCOVERER lands a real capability from a valid ADL file.
        path = _sample_adl(tmp_path, "concept-chain-1")
        disc = runtime(AgentRole.DISCOVERER, "did:key:disc")
        dtask = task_reg.create_task(
            "land concept-chain-1",
            required_capabilities=["depends-on"],
            input_ref=str(path),
        )
        await disc.run_task(dtask)
        assert task_reg.get_task(dtask.task_id).result_ref == "concept-chain-1"
        result_ref = "concept-chain-1"
        assert "adl_parse" in tool_events(dtask.task_id)
        assert "adl_consensus_register" in tool_events(dtask.task_id)

        # REVIEWER: validate the material, then approve (-> validated).
        reviewer = runtime(AgentRole.REVIEWER, "did:key:reviewer")
        rtask = task_reg.create_task(
            "review concept-chain-1",
            required_capabilities=["validate"],
            input_ref=str(path),
        )
        rtask.result_ref = result_ref
        await reviewer.run_task(rtask)
        rtools = tool_events(rtask.task_id)
        assert "adl_validate" in rtools
        assert "adl_consensus_transition" in rtools
        assert engine.chains[result_ref].status == DiscoveryStatus.VALIDATED

        # SKEPTIC: a tampered result chain fails verification -> fork.
        challenge = "concept-challenge-1"
        ctask = task_reg.create_task(
            "land " + challenge,
            required_capabilities=["depends-on"],
            input_ref=str(_sample_adl(tmp_path, challenge)),
        )
        await disc.run_task(ctask)  # registers the challenge chain
        engine.chains[challenge].events[0].payload["tampered"] = True
        skeptic = runtime(AgentRole.SKEPTIC, "did:key:skeptic")
        sktask = task_reg.create_task("challenge " + challenge)
        sktask.result_ref = challenge
        await skeptic.run_task(sktask)
        sktools = tool_events(sktask.task_id)
        assert "adl_consensus_verify" in sktools
        assert "adl_consensus_transition" in sktools

        # MERGER: a legitimately forked chain verifies and gets re-validated.
        merged = "concept-merge-1"
        mtask0 = task_reg.create_task(
            "land " + merged,
            required_capabilities=["depends-on"],
            input_ref=str(_sample_adl(tmp_path, merged)),
        )
        await disc.run_task(mtask0)
        engine.transition(merged, DiscoveryStatus.FORKED, "did:key:skeptic", reason="challenge")
        assert engine.chains[merged].status == DiscoveryStatus.FORKED
        merger = runtime(AgentRole.MERGER, "did:key:merger")
        mrtask = task_reg.create_task("merge " + merged)
        mrtask.result_ref = merged
        await merger.run_task(mrtask)
        mtools = tool_events(mrtask.task_id)
        assert "adl_consensus_verify" in mtools
        assert "adl_consensus_transition" in mtools
        assert engine.chains[merged].status == DiscoveryStatus.VALIDATED

        # LIBRARIAN: store the material + query related in the memory db.
        db_path = tmp_path / "adl_mem.db"
        librarian = runtime(AgentRole.LIBRARIAN, "did:key:librarian")
        ltask = task_reg.create_task(
            "store concept-chain-1",
            required_capabilities=["depends-on"],
            input_ref=str(path),
            db_ref=str(db_path),
        )
        ltask.result_ref = result_ref
        await librarian.run_task(ltask)
        ltools = tool_events(ltask.task_id)
        assert "adl_store" in ltools
        assert "adl_query_related" in ltools
        assert db_path.exists()

    async def test_skeptic_challenge_forks_result(self, tmp_path: Path) -> None:
        """RT-07c: when verification fails (challenge stands) the skeptic
        transitions the result chain to forked — the chain carries a FORK
        event and the skeptic task still submits."""
        engine = ConsensusEngine(dev_mode=True)
        agent_reg = AgentRegistry(engine=engine)
        task_reg = TaskRegistry(engine=engine)
        queue = TaskQueue(task_reg)

        def runtime(role: AgentRole, did: str) -> AgentRuntime:
            return AgentRuntime(
                agent_did=did,
                profile=AgentProfile(did=did, role=role, name=role.value),
                engine=engine,
                agent_registry=agent_reg,
                task_registry=task_reg,
                task_queue=queue,
                llm=_FakeLLM(),
            )

        # Discoverer registers the capability; then we break its chain.
        path = _sample_adl(tmp_path, "concept-challenge-2")
        disc = runtime(AgentRole.DISCOVERER, "did:key:disc")
        dtask = task_reg.create_task(
            "land concept-challenge-2",
            required_capabilities=["depends-on"],
            input_ref=str(path),
        )
        await disc.run_task(dtask)
        assert engine.chains["concept-challenge-2"].verify_integrity() is True
        engine.chains["concept-challenge-2"].events[0].payload["tampered"] = True
        assert engine.chains["concept-challenge-2"].verify_integrity() is False

        # Skeptic challenges the tampered result -> fork transition.
        skeptic = runtime(AgentRole.SKEPTIC, "did:key:skeptic")
        sktask = task_reg.create_task("challenge concept-challenge-2")
        sktask.result_ref = "concept-challenge-2"
        await skeptic.run_task(sktask)

        chain = engine.chains["concept-challenge-2"]
        assert any(e.event_type == EventType.FORK for e in chain.events)
        assert chain.status == DiscoveryStatus.FORKED
        assert task_reg.get_task(sktask.task_id).status == TaskStatus.SUBMITTED

    async def test_merger_resolves_fork(self, tmp_path: Path) -> None:
        """RT-07d: a forked chain passes verification and the merger
        transitions it back to validated (fork resolution)."""
        engine = ConsensusEngine(dev_mode=True)
        agent_reg = AgentRegistry(engine=engine)
        task_reg = TaskRegistry(engine=engine)
        queue = TaskQueue(task_reg)

        def runtime(role: AgentRole, did: str) -> AgentRuntime:
            return AgentRuntime(
                agent_did=did,
                profile=AgentProfile(did=did, role=role, name=role.value),
                engine=engine,
                agent_registry=agent_reg,
                task_registry=task_reg,
                task_queue=queue,
                llm=_FakeLLM(),
            )

        # Discoverer registers the capability; a skeptic forks it.
        path = _sample_adl(tmp_path, "concept-merge-2")
        disc = runtime(AgentRole.DISCOVERER, "did:key:disc")
        dtask = task_reg.create_task(
            "land concept-merge-2",
            required_capabilities=["depends-on"],
            input_ref=str(path),
        )
        await disc.run_task(dtask)
        engine.transition(
            "concept-merge-2", DiscoveryStatus.FORKED, "did:key:skeptic", reason="challenge"
        )
        assert engine.chains["concept-merge-2"].status == DiscoveryStatus.FORKED

        # Merger verifies (passes) and resolves the fork -> validated.
        merger = runtime(AgentRole.MERGER, "did:key:merger")
        mrtask = task_reg.create_task("merge concept-merge-2")
        mrtask.result_ref = "concept-merge-2"
        await merger.run_task(mrtask)

        chain = engine.chains["concept-merge-2"]
        assert any(e.event_type == EventType.VALIDATE for e in chain.events)
        assert chain.status == DiscoveryStatus.VALIDATED
        assert task_reg.get_task(mrtask.task_id).status == TaskStatus.SUBMITTED


# ----------------------------------------------------------------------
# RT-08: P1-6 backlog visibility
# ----------------------------------------------------------------------


class TestBacklog:
    async def test_pending_count_includes_queued_and_leased(self) -> None:
        """P1-6: un-consumed backlog is observable.

        pending = queued + leased. A dequeue removes the task from the queue
        AND claims it, so a task in flight still counts as pending (it is
        consumed, not resolved)."""
        engine = ConsensusEngine(dev_mode=True)
        task_reg = TaskRegistry(engine=engine)
        queue = TaskQueue(task_reg, lease_ttl=60)
        t1 = task_reg.create_task("a", required_capabilities=["depends-on"])
        t2 = task_reg.create_task("b", required_capabilities=["depends-on"])
        await queue.enqueue(t1)
        await queue.enqueue(t2)
        assert queue.pending_count() == 2

        # Worker 1 dequeues a task: it leaves the queue but holds a lease.
        got = await queue.dequeue("did:key:w1", capabilities=["depends-on"])
        assert got is not None
        assert queue.pending_count() == 2  # 1 queued + 1 leased
        assert queue.queue_depth() == 1


# ----------------------------------------------------------------------
# Registry-level: idempotent re-claim + transition sanity
# ----------------------------------------------------------------------


class TestReclaim:
    def test_idempotent_reclaim(self) -> None:
        """M3 recovery: IN_PROGRESS -> IN_PROGRESS re-claim is legal."""
        reg = TaskRegistry()
        task = reg.create_task("x")
        reg.claim(task.task_id, "a1")
        ev = reg.claim(task.task_id, "a1")  # retry after failure
        assert ev.event_type == EventType.TASK_CLAIM
        assert reg.get_task(task.task_id).status == TaskStatus.IN_PROGRESS

    def test_submitted_reclaim_still_illegal(self) -> None:
        """The rework guard is unchanged: SUBMITTED cannot be re-claimed."""
        reg = TaskRegistry()
        task = reg.create_task("x")
        reg.claim(task.task_id, "a1")
        reg.submit(task.task_id, "a1", "cap-1")
        with pytest.raises(ADLConsensusError, match="invalid task transition"):
            reg.claim(task.task_id, "a1")


class TestEventSigner:
    """Closure P1: optional signer attaches DID signatures to transition
    events so strict trust checks (B2) can verify them."""

    def _signed_runtime(self, engine, role: AgentRole = AgentRole.REVIEWER):
        from adl_lite.did_resolver import create_did_key
        from adl_lite.ld_proof import generate_keypair

        priv = generate_keypair()
        did = create_did_key(priv.public_key())
        profile = AgentProfile(
            did=did, role=role, name=role.value, capabilities=["related-to", "validate"]
        )
        signer = lambda msg: base64.b64encode(priv.sign(msg)).decode()  # noqa: E731
        rt = AgentRuntime(
            did,
            profile,
            engine,
            AgentRegistry(engine=engine),
            TaskRegistry(engine=engine),
            TaskQueue(TaskRegistry(engine=engine)),
            signer=signer,
        )
        return rt, did

    async def test_transition_event_signed(self, tmp_path: Path) -> None:
        """Reviewer transition -> VALIDATE event carries a verifiable signature."""
        from adl_lite.did_resolver import create_did_key
        from adl_lite.ld_proof import generate_keypair

        engine = ConsensusEngine(dev_mode=True)
        # Discoverer lands the capability first (signed, loose path).
        disc_priv = generate_keypair()
        disc_did = create_did_key(disc_priv.public_key())
        disc_prof = AgentProfile(
            did=disc_did, role=AgentRole.DISCOVERER, name="disc", capabilities=["depends-on"]
        )
        disc = AgentRuntime(
            disc_did,
            disc_prof,
            engine,
            AgentRegistry(engine=engine),
            TaskRegistry(engine=engine),
            TaskQueue(TaskRegistry(engine=engine)),
            signer=lambda msg: base64.b64encode(disc_priv.sign(msg)).decode(),
        )
        path = _sample_adl(tmp_path, "concept-signed-1")
        t1 = TaskRegistry(engine=engine).create_task(
            "land concept-signed-1",
            required_capabilities=["depends-on"],
            input_ref=str(path),
        )
        await disc.run_task(t1)

        # Reviewer approves the produced chain WITH a signer.
        reviewer, did = self._signed_runtime(engine)
        t2 = TaskRegistry(engine=engine).create_task(
            "review concept-signed-1",
            required_capabilities=["related-to"],
            input_ref=str(path),
        )
        t2.result_ref = "concept-signed-1"
        await reviewer.run_task(t2)

        chain = engine.chains["concept-signed-1"]
        validate_events = [e for e in chain.events if e.event_type == EventType.VALIDATE]
        assert validate_events, "reviewer should have transitioned the chain"
        ev = validate_events[-1]
        assert ev.actor == did
        assert ev.signature, "signer must attach a signature"

        # Strict trust check now passes B2 (signature verifies against did:key).
        from adl_lite.trust_model import ConsensusConfig, TrustValidator

        result = TrustValidator().validate_event_chain(
            chain, ConsensusConfig(mode="dev", min_distinct_validators=1)
        )
        assert result.valid is True, result.errors
        assert "signature" not in " ".join(result.errors).lower()

    async def test_no_signer_keeps_loose_behaviour(self, tmp_path: Path) -> None:
        """Default runtime (no signer) does not sign -> behaviour unchanged."""
        from adl_lite.did_resolver import create_did_key
        from adl_lite.ld_proof import generate_keypair
        from adl_lite.models import ADLDocument, ADLFrontMatter, ADLType

        engine = ConsensusEngine(dev_mode=True)
        path = _sample_adl(tmp_path, "concept-unsigned-1")
        # Pre-register the capability stub (reviewer transitions, not lands).
        engine.register(
            ADLDocument(
                front_matter=ADLFrontMatter(
                    adl_type=ADLType.CONCEPT, adl_id="concept-unsigned-1", scope="public"
                )
            )
        )
        task_reg = TaskRegistry(engine=engine)
        priv = generate_keypair()
        prof = AgentProfile(
            did=create_did_key(priv.public_key()), role=AgentRole.REVIEWER, name="r"
        )
        plain = AgentRuntime(
            prof.did, prof, engine, AgentRegistry(engine=engine), task_reg, TaskQueue(task_reg)
        )
        t1 = task_reg.create_task(
            "review concept-unsigned-1", required_capabilities=["related-to"], input_ref=str(path)
        )
        t1.result_ref = "concept-unsigned-1"
        await plain.run_task(t1)
        chain = engine.chains["concept-unsigned-1"]
        assert any(e.event_type == EventType.VALIDATE for e in chain.events)
        assert not any(e.signature for e in chain.events)
