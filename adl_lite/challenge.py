"""
ADL Lite — EAL Phase 3: commit–reveal challenge protocol (CHALLENGE events).

Motivation (docs/design/execution-attestation.md §5.6): a deterministic
capability can pass replay attestation by caching one honest answer and
replaying it forever. The CHALLENGE protocol closes that hole with a
commit–reveal scheme:

1. ``open``   — a challenger commits to a secret seed
   (``seed_commitment = "sha256:" + H(seed)``), sets a ``reveal_deadline``
   and a ``response_window_s``. The plaintext seed stays LOCAL (see
   ``save_seed_stub``) and never touches the chain until reveal.
2. ``reveal`` — the same challenger publishes the plaintext seed before the
   deadline. The revealed seed IS the challenge input: the executor runs the
   capability on it (convention: seed text as the input payload).
3. ``answer`` — the executor posts an ``output_commitment`` over the result
   within ``response_window_s`` of the reveal.

Derived terminal phases (NOT stored — recomputed from the chain, event-first):
- ``answered``  — a valid answer arrived in time.
- ``timed_out`` — reveal happened but no in-window answer exists as of
  ``as_of`` (or an answer event arrived after its window).
- ``void``      — the challenger failed to reveal in time, revealed a seed
  that does not match the commitment, or revealed after the deadline.
  Void challenges are the challenger's fault and are excluded from response
  rates.

Determinism / CRDT friendliness: time-dependent derivations take an explicit
``as_of`` instant. The default is the latest event timestamp the manager has
seen (chain-internal time), so replaying the same chain always yields the same
verdicts; callers that want wall-clock semantics (e.g. ``adl-lite challenge
status``) pass ``as_of=datetime.now(timezone.utc)`` explicitly.

Cross-event checks live here; per-event payload shape is enforced on-chain by
Axiom 15 (``models._challenge_payload_well_formed``).
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .logging_config import get_logger
from .models import Event, EventChain, EventType

logger = get_logger(__name__)

CHALLENGE_PHASES = ("open", "reveal", "answer")
# Derived terminal/intermediate states of a challenge lifecycle.
DERIVED_STATES = ("open", "revealed", "answered", "timed_out", "void")


def generate_seed() -> str:
    """Return a fresh 256-bit hex seed."""
    return secrets.token_hex(32)


def seed_commitment(seed: str) -> str:
    """Return the on-chain commitment for a plaintext seed."""
    return "sha256:" + hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _parse_dt(value: Any) -> datetime | None:
    """Parse an ISO timestamp (str or datetime) into an aware datetime.

    Naive values are interpreted as UTC. Returns None on failure.
    """
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class ChallengeState:
    """Mutable per-challenge projection, rebuilt by replaying CHALLENGE events."""

    challenge_id: str
    concept_id: str
    challenger: str
    seed_commitment: str
    reveal_deadline: datetime
    response_window_s: float
    opened_at: datetime
    target_executor: str | None = None
    phase: str = "open"  # open | revealed | answered | timed_out | void
    seed: str | None = None
    revealed_at: datetime | None = None
    answer_actor: str | None = None
    answered_at: datetime | None = None
    output_commitment: str | None = None
    void_reason: str | None = None


class ChallengeManager:
    """Replay CHALLENGE events into per-challenge states and response metrics.

    The manager is a derived, read-only view: it never mutates the chain.
    Use ``apply_chain`` for a fresh full replay, or ``apply`` incrementally
    when streaming events.
    """

    def __init__(self) -> None:
        self.challenges: dict[str, ChallengeState] = {}
        self.issues: list[str] = []
        self._max_seen_dt: datetime | None = None

    # ------------------------------------------------------------------
    # Event application
    # ------------------------------------------------------------------

    def apply(self, event: Event) -> list[str]:
        """Fold one event into the projection; return issues raised by it."""
        if event.event_type is not EventType.CHALLENGE:
            return []
        event_dt = _parse_dt(event.timestamp)
        if event_dt is not None and (self._max_seen_dt is None or event_dt > self._max_seen_dt):
            self._max_seen_dt = event_dt

        payload = event.payload
        challenge_id = str(payload.get("challenge_id", ""))
        phase = payload.get("phase")
        before = len(self.issues)

        if phase == "open":
            self._apply_open(event, challenge_id, event_dt)
        elif phase == "reveal":
            self._apply_reveal(event, challenge_id, event_dt)
        elif phase == "answer":
            self._apply_answer(event, challenge_id, event_dt)
        else:
            self.issues.append(f"{event.event_id}: unknown-challenge-phase:{phase}")
        return self.issues[before:]

    def _apply_open(self, event: Event, challenge_id: str, event_dt: datetime | None) -> None:
        if challenge_id in self.challenges:
            self.issues.append(f"{event.event_id}: duplicate-challenge-open:{challenge_id}")
            return
        deadline = _parse_dt(event.payload.get("reveal_deadline"))
        if deadline is None:
            self.issues.append(f"{event.event_id}: bad-reveal-deadline:{challenge_id}")
            return
        raw_window = event.payload.get("response_window_s")
        if raw_window is None or isinstance(raw_window, bool):
            self.issues.append(f"{event.event_id}: bad-response-window:{challenge_id}")
            return
        try:
            window = float(raw_window)
        except (TypeError, ValueError):
            self.issues.append(f"{event.event_id}: bad-response-window:{challenge_id}")
            return
        if window <= 0:
            self.issues.append(f"{event.event_id}: non-positive-response-window:{challenge_id}")
            return
        self.challenges[challenge_id] = ChallengeState(
            challenge_id=challenge_id,
            concept_id=event.concept_id,
            challenger=event.actor,
            seed_commitment=str(event.payload.get("seed_commitment", "")),
            reveal_deadline=deadline,
            response_window_s=window,
            opened_at=event_dt or deadline,
            target_executor=event.payload.get("target_executor") or None,
        )

    def _apply_reveal(self, event: Event, challenge_id: str, event_dt: datetime | None) -> None:
        state = self.challenges.get(challenge_id)
        if state is None:
            self.issues.append(f"{event.event_id}: reveal-before-open:{challenge_id}")
            return
        if state.phase != "open":
            self.issues.append(f"{event.event_id}: duplicate-reveal:{challenge_id}")
            return
        if event.actor != state.challenger:
            self.issues.append(
                f"{event.event_id}: reveal-by-non-challenger:{challenge_id}:{event.actor}"
            )
            return
        seed = str(event.payload.get("seed", ""))
        if seed_commitment(seed) != state.seed_commitment:
            state.phase = "void"
            state.void_reason = "seed-commitment-mismatch"
            self.issues.append(f"{event.event_id}: seed-commitment-mismatch:{challenge_id}")
            return
        reveal_dt = event_dt or state.reveal_deadline
        if reveal_dt > state.reveal_deadline:
            state.phase = "void"
            state.void_reason = "reveal-after-deadline"
            self.issues.append(f"{event.event_id}: reveal-after-deadline:{challenge_id}")
            return
        state.phase = "revealed"
        state.seed = seed
        state.revealed_at = reveal_dt

    def _apply_answer(self, event: Event, challenge_id: str, event_dt: datetime | None) -> None:
        state = self.challenges.get(challenge_id)
        if state is None:
            self.issues.append(f"{event.event_id}: answer-before-open:{challenge_id}")
            return
        if state.phase == "answered":
            # Idempotent: extra answers after resolution carry no information.
            return
        if state.phase != "revealed":
            self.issues.append(
                f"{event.event_id}: answer-out-of-phase:{challenge_id}:{state.phase}"
            )
            return
        assert state.revealed_at is not None
        answer_dt = event_dt or state.revealed_at
        deadline = state.revealed_at + timedelta(seconds=state.response_window_s)
        if answer_dt > deadline:
            state.phase = "timed_out"
            self.issues.append(f"{event.event_id}: answer-after-window:{challenge_id}")
            return
        if state.target_executor is not None and event.actor != state.target_executor:
            self.issues.append(
                f"{event.event_id}: answer-by-non-target:{challenge_id}:{event.actor}"
            )
            return
        state.phase = "answered"
        state.answer_actor = event.actor
        state.answered_at = answer_dt
        state.output_commitment = str(event.payload.get("output_commitment", ""))

    # ------------------------------------------------------------------
    # Chain replay and derived views
    # ------------------------------------------------------------------

    def apply_chain(self, chain: EventChain, as_of: datetime | None = None) -> list[str]:
        """Reset and replay all CHALLENGE events of a chain; return all issues."""
        self.challenges.clear()
        self.issues.clear()
        self._max_seen_dt = None
        for event in chain.events:
            self.apply(event)
        return list(self.issues)

    def _default_as_of(self) -> datetime:
        """Chain-internal 'now': the newest event timestamp seen, or wall clock."""
        return self._max_seen_dt or datetime.now(timezone.utc)

    def derived_phase(self, challenge_id: str, as_of: datetime | None = None) -> str:
        """Return the derived phase of a challenge at ``as_of``.

        Terminal phases (answered/timed_out/void) are sticky once event-driven;
        open/revealed challenges derive timeouts against ``as_of``.
        """
        state = self.challenges[challenge_id]
        now = as_of or self._default_as_of()
        if state.phase in ("answered", "timed_out", "void"):
            return state.phase
        if state.phase == "open" and now > state.reveal_deadline:
            return "void"
        if state.phase == "revealed":
            assert state.revealed_at is not None
            if now > state.revealed_at + timedelta(seconds=state.response_window_s):
                return "timed_out"
        return state.phase

    def response_metrics(
        self,
        executor: str | None = None,
        as_of: datetime | None = None,
    ) -> dict[str, Any]:
        """Aggregate response rates, overall and per capability.

        ``executor`` filters to challenges targeting that executor (or answered
        by them when no target was set). Void challenges (challenger fault) are
        excluded from the response-rate denominator.
        """
        now = as_of or self._default_as_of()

        def _eligible(state: ChallengeState) -> bool:
            if executor is None:
                return True
            if state.target_executor is not None:
                return state.target_executor == executor
            return state.answer_actor == executor

        def _bucket(states: list[ChallengeState]) -> dict[str, Any]:
            counts = dict.fromkeys(DERIVED_STATES, 0)
            for st in states:
                counts[self.derived_phase(st.challenge_id, now)] += 1
            answered = counts["answered"]
            timed_out = counts["timed_out"]
            denom = answered + timed_out
            return {
                "total": len(states),
                **counts,
                "response_rate": (answered / denom) if denom else None,
            }

        eligible = [st for st in self.challenges.values() if _eligible(st)]
        by_capability: dict[str, list[ChallengeState]] = {}
        for st in eligible:
            by_capability.setdefault(st.concept_id, []).append(st)
        return {
            "executor": executor,
            "as_of": now.isoformat(),
            "overall": _bucket(eligible),
            "by_capability": {
                cid: _bucket(states) for cid, states in sorted(by_capability.items())
            },
        }


def replay_challenges(chain: EventChain, as_of: datetime | None = None) -> ChallengeManager:
    """Convenience: build a ChallengeManager from a full chain replay."""
    manager = ChallengeManager()
    manager.apply_chain(chain, as_of=as_of)
    return manager


# ----------------------------------------------------------------------
# Local seed stubs (plaintext seeds live ONLY here until reveal)
# ----------------------------------------------------------------------


def seed_stub_path(log_dir: str | Path, challenge_id: str) -> Path:
    """Return the local stub path for a challenge's plaintext seed."""
    return Path(log_dir) / "challenges" / f"{challenge_id}.json"


def save_seed_stub(
    log_dir: str | Path,
    challenge_id: str,
    *,
    seed: str,
    seed_commitment_value: str,
    reveal_deadline: str,
    response_window_s: float,
    target_executor: str | None = None,
) -> Path:
    """Persist the plaintext seed locally with 0600 permissions.

    The stub is the ONLY place the seed exists before reveal; it must never
    be written to the chain or any shared store.
    """
    path = seed_stub_path(log_dir, challenge_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "challenge_id": challenge_id,
        "seed": seed,
        "seed_commitment": seed_commitment_value,
        "reveal_deadline": reveal_deadline,
        "response_window_s": response_window_s,
        "target_executor": target_executor,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def load_seed_stub(log_dir: str | Path, challenge_id: str) -> dict[str, Any] | None:
    """Load a local seed stub; return None when absent or malformed."""
    path = seed_stub_path(log_dir, challenge_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not data.get("seed"):
        return None
    return data


def delete_seed_stub(log_dir: str | Path, challenge_id: str) -> bool:
    """Delete a local seed stub (e.g. after a successful reveal)."""
    path = seed_stub_path(log_dir, challenge_id)
    if not path.exists():
        return False
    path.unlink()
    return True
