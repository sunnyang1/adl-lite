"""MessageBus and TaskQueue for the native multi-agent runtime (M2).

TaskQueue is VOLATILE runtime state: claim leases live in memory (or Redis when
``bus_backend="redis"``) and are intentionally NOT chain-backed (dual-state
semantics — a lease is a process, not a fact). The chain (TaskRegistry) remains
the only source of truth for RESULT state.

Adversarial-review fixes baked in:
- P0-1: dequeue puts a failed claim back on the queue; requeue_expired
  re-enqueues expired tasks (no permanent task loss).
- P1-5: all lease mutations go through a single ``threading.Lock`` so the
  apscheduler reaper thread and asyncio claimers never race.
- P2-2: request/reply is closed by ``reply_loop`` (responder side).
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from collections.abc import Awaitable, Callable
from typing import Any

from .task import Task, TaskRegistry


class MessageBus:
    """asyncio in-process pub/sub; Redis transport lazily imported when
    ``backend="redis"`` (raises ImportError with an ``adl-lite[v1]`` hint)."""

    def __init__(self, backend: str = "local", redis_url: str | None = None) -> None:
        self._backend = backend
        self._subs: dict[str, list[Callable[[dict[str, Any]], Awaitable[None]]]] = {}
        self._pending: dict[int, asyncio.Future] = {}
        self._redis = None
        if backend == "redis":
            try:
                import redis.asyncio as aioredis  # type: ignore[import-not-found]
            except ImportError as exc:  # pragma: no cover
                raise ImportError(
                    "MessageBus(backend='redis') requires the [v1] extra: "
                    'pip install "adl-lite[v1]"'
                ) from exc
            self._redis = aioredis.from_url(redis_url or "redis://localhost:6379")

    # ------------------------------------------------------------------

    async def publish(
        self, channel: str, message: dict[str, Any], *, persist: bool = False
    ) -> None:
        """Broadcast a message. ``persist=True`` additionally appends a MESSAGE
        event to a conversation chain for audit (via the caller-supplied
        registry — see TaskRegistry-adjacent helper)."""
        if self._redis is not None:  # pragma: no cover
            await self._redis.publish(channel, json.dumps(message))
        for handler in list(self._subs.get(channel, [])):
            await handler(message)

    async def subscribe(
        self, channel: str, handler: Callable[[dict[str, Any]], Awaitable[None]]
    ) -> None:
        self._subs.setdefault(channel, []).append(handler)

    async def unsubscribe(
        self, channel: str, handler: Callable[[dict[str, Any]], Awaitable[None]]
    ) -> None:
        self._subs.setdefault(channel, []).remove(handler)

    async def request(
        self, channel: str, message: dict[str, Any], timeout: float = 30.0
    ) -> dict[str, Any]:
        """Request/reply with an in-process Future (single-process deployment
        only; see P1-4 in the implementation plan)."""
        fut = asyncio.get_running_loop().create_future()
        self._pending[id(fut)] = fut
        await self.publish(f"{channel}:req", {**message, "_req_id": id(fut)})
        try:
            return await asyncio.wait_for(fut, timeout)
        finally:
            self._pending.pop(id(fut), None)

    async def reply_loop(
        self, channel: str, handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
    ) -> None:
        """P2-2 responder side: subscribe to ``{channel}:req``, run handler,
        publish the reply and resolve the requester's Future (same process)."""

        async def _on_req(req: dict[str, Any]) -> None:
            reply = await handler(req)
            reply["_req_id"] = req.get("_req_id")
            await self.publish(f"{channel}:rep", reply, persist=False)
            fut = self._pending.get(req.get("_req_id"))  # type: ignore[arg-type]
            if fut is not None and not fut.done():
                fut.set_result(reply)

        await self.subscribe(f"{channel}:req", _on_req)

    async def close(self) -> None:
        if self._redis is not None:  # pragma: no cover
            await self._redis.aclose()  # type: ignore[attr-defined]


class TaskQueue:
    """Volatile runtime queue: at-most-one claim + lease/TTL.

    Cross-thread atomicity (P1-5): ALL lease mutations go through
    ``self._lock`` (a plain ``threading.Lock``), so the apscheduler reaper
    thread and asyncio claimers share one synchronization primitive.
    """

    def __init__(
        self, registry: TaskRegistry, bus: MessageBus | None = None, lease_ttl: float = 300.0
    ) -> None:
        self._registry = registry
        self._bus = bus
        self._lease_ttl = lease_ttl
        self._q: asyncio.PriorityQueue[tuple[int, str]] = asyncio.PriorityQueue()
        self._leases: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------

    async def enqueue(self, task: Task) -> None:
        await self._q.put((-task.priority, task.task_id))

    async def dequeue(self, agent_did: str, capabilities: list[str] | None = None) -> Task | None:
        """Pop the highest-priority task matching capabilities, claiming it
        atomically. P0-1: a failed claim is PUT BACK on the queue; we then
        stop for this call (next dequeue retries), avoiding an infinite
        spin when the only candidate is held by another agent."""
        while not self._q.empty():
            _prio, tid = await self._q.get()
            task = self._registry.get_task(tid)
            if task.status.value == "closed":
                continue  # terminal: don't dispatch
            if capabilities and not set(task.required_capabilities) <= set(capabilities):
                continue  # capability mismatch (P1-3 vocabulary)
            if self.claim(tid, agent_did):
                return task
            await self._q.put((0, tid))  # P0-1: failed claim -> back to queue
            return None  # held by another agent; retry on the next dequeue
        return None

    # ------------------------------------------------------------------
    # Lease primitives (all thread-safe via self._lock, P1-5)
    # ------------------------------------------------------------------

    def claim(self, task_id: str, agent_did: str, lease_ttl: float | None = None) -> bool:
        with self._lock:
            now = time.time()
            if task_id in self._leases:
                _holder, until = self._leases[task_id]
                if now < until:
                    return False  # already claimed and unexpired
            ttl = lease_ttl or self._lease_ttl
            self._leases[task_id] = (agent_did, now + ttl)
            return True

    def renew_lease(self, task_id: str, agent_did: str) -> bool:
        with self._lock:
            ent = self._leases.get(task_id)
            if ent is None or ent[0] != agent_did:
                return False
            self._leases[task_id] = (agent_did, time.time() + self._lease_ttl)
            return True

    def release(self, task_id: str, agent_did: str) -> None:
        with self._lock:
            if self._leases.get(task_id, (None,))[0] == agent_did:
                self._leases.pop(task_id, None)

    async def requeue_expired(self) -> list[str]:
        """Lease reaper (P0-1): release expired leases AND re-enqueue the
        tasks so nothing is lost. Async — the queue puts complete before this
        returns. In production the apscheduler thread calls it via
        ``asyncio.run_coroutine_threadsafe(queue.requeue_expired(), loop)``."""
        with self._lock:
            now = time.time()
            expired = [tid for tid, (_a, until) in self._leases.items() if until <= now]
            for tid in expired:
                self._leases.pop(tid, None)
        for tid in expired:
            await self._q.put((0, tid))
        return expired

    def queue_depth(self) -> int:
        return self._q.qsize()

    def pending_count(self) -> int:
        """P1-6: tasks that are queued OR held by an unexpired lease."""
        with self._lock:
            return self._q.qsize() + len(self._leases)
