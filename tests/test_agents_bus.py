"""M2 bus tests: pub/sub, request/reply, at-most-one claim, lease expiry,
cross-thread atomicity, and the P0-1 no-task-loss guarantee.
"""

from __future__ import annotations

import asyncio
import threading

import pytest

from adl_lite.agents.bus import MessageBus, TaskQueue
from adl_lite.agents.task import TaskRegistry


class TestMessageBus:
    async def test_publish_subscribe(self) -> None:
        """BS-01: handler receives the message dict."""
        bus = MessageBus()
        received: list[dict] = []

        async def handler(msg: dict) -> None:
            received.append(msg)

        await bus.subscribe("tasks", handler)
        await bus.publish("tasks", {"kind": "hello"})
        assert received == [{"kind": "hello"}]

    async def test_request_reply(self) -> None:
        """BS-02: request/reply round-trip (in-process Future)."""
        bus = MessageBus()

        async def responder(req: dict) -> dict:
            return {"echo": req.get("payload")}

        await bus.reply_loop("calc", responder)
        reply = await bus.request("calc", {"payload": 42})
        assert reply["echo"] == 42

    async def test_publish_no_handlers_is_noop(self) -> None:
        bus = MessageBus()
        await bus.publish("empty", {"x": 1})  # must not raise


class TestTaskQueue:
    @pytest.fixture()
    def reg(self) -> TaskRegistry:
        return TaskRegistry()

    async def test_at_most_one_claim(self, reg: TaskRegistry) -> None:
        """BS-03: second agent cannot claim while the first holds the lease."""
        task = reg.create_task("x")
        q = TaskQueue(reg, lease_ttl=60)
        await q.enqueue(task)
        got = await q.dequeue("a1")
        assert got is not None and got.task_id == task.task_id
        assert q.claim(task.task_id, "a2") is False

    async def test_claim_failed_is_requeued(self, reg: TaskRegistry) -> None:
        """P0-1: a held task is never lost — it lives in the holder's lease,
        and a second agent's dequeue does not consume it."""
        task = reg.create_task("x")
        q = TaskQueue(reg, lease_ttl=60)
        await q.enqueue(task)
        got1 = await q.dequeue("a1")
        assert got1 is not None
        got2 = await q.dequeue("a2")
        assert got2 is None  # task is held by a1's lease, not silently lost
        assert q.pending_count() == 1  # queued + leased accounting intact

    async def test_lease_expiry_requeue(self, reg: TaskRegistry) -> None:
        """BS-10/P0-1 (slow): expired lease -> task is re-enqueued and
        claimable again."""
        task = reg.create_task("x")
        q = TaskQueue(reg, lease_ttl=0.1)
        await q.enqueue(task)
        got = await q.dequeue("a1")
        assert got is not None
        assert q.claim(task.task_id, "a2") is False  # lease unexpired

        # Reaper: release expired leases and re-enqueue (awaited, P0-1).
        await asyncio.sleep(0.15)
        expired = await q.requeue_expired()
        assert task.task_id in expired
        got_again = await q.dequeue("a2")
        assert got_again is not None and got_again.task_id == task.task_id  # P0-1

    async def test_release(self, reg: TaskRegistry) -> None:
        """BS-06: release frees the lease for another agent."""
        task = reg.create_task("x")
        q = TaskQueue(reg)
        await q.enqueue(task)
        got = await q.dequeue("a1")
        assert got is not None
        q.release(task.task_id, "a1")
        assert q.claim(task.task_id, "a2") is True

    def test_cross_thread_atomicity(self, reg: TaskRegistry) -> None:
        """BS-09/P1-5: concurrent claims from multiple threads — exactly one wins."""
        task = reg.create_task("x")
        q = TaskQueue(reg, lease_ttl=60)
        results: list[bool] = []
        lock = threading.Lock()

        def worker(i: int) -> None:
            ok = q.claim(task.task_id, f"agent-{i}")
            with lock:
                results.append(ok)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert results.count(True) == 1

    async def test_pending_count(self, reg: TaskRegistry) -> None:
        """P1-6: pending = queued + leased."""
        task = reg.create_task("x")
        q = TaskQueue(reg, lease_ttl=60)
        assert q.pending_count() == 0
        await q.enqueue(task)
        assert q.pending_count() == 1
        await q.dequeue("a1")
        assert q.pending_count() == 1  # lease held


class TestRedisLazyLoad:
    def test_redis_import_error_hint(self, monkeypatch) -> None:
        """BS-08: redis backend without the [v1] extra raises a hint ImportError."""
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name.startswith("redis"):
                raise ImportError("No module named 'redis'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        with pytest.raises(ImportError, match="adl-lite\\[v1\\]"):
            MessageBus(backend="redis")
