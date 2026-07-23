"""
ADL Lite — ExecutionLog (Execution Attestation Layer, Phase 1).

Per docs/design/execution-attestation.md (D1, hybrid architecture):

- Raw EXECUTE receipts live on a per-capability ``ExecutionLog``: an
  append-only, hash-chained log (built on :class:`EventChain`) that is
  cold-storage friendly and grows independently of the governance chain.
- The governance (main) chain only carries ``EXEC_ANCHOR`` events committing
  the log's Merkle root, plus ``ATTEST`` verdicts (Phase 2 wiring; the event
  type and axioms already exist).
- Phase 1 is pure observability: status LUB and confidence G-Counter
  derivation do not consume EAL event types (see ``EventChain._update_crdt_caches``).

Chain-local integrity is enforced by Definition 5 axioms 1–12 plus EAL
conditional axioms 13–15 (models.py). Cross-log references
(``ATTEST.subject_execution`` → a receipt on an ExecutionLog) are resolved at
the validation layer via an injected lookup, following the precedent of
``RelationValidator.filter_valid_relations``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from .logging_config import get_logger
from .merkle import compute_chain_merkle_root
from .models import Event, EventChain, EventType

logger = get_logger(__name__)

# Payload field defaults
ASSURANCE_SELF_REPORT = "self-report"  # L1: executor-signed claim, no independent check


class ExecutionLog:
    """Append-only, hash-chained log of EXECUTE receipts for one capability.

    The log is a full EventChain (concept_id = ``execlog-<capability_id>``),
    so hashing, chaining, incremental integrity verification, and the split
    lock design are all reused. Only EXECUTE events may be appended.
    """

    def __init__(self, capability_id: str, events: list[Event] | None = None) -> None:
        self.capability_id = capability_id
        self._chain = EventChain(concept_id=self.log_id)
        if events:
            for e in events:
                self._chain.append(e)

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def log_id(self) -> str:
        return f"execlog-{self.capability_id}"

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(
        self,
        *,
        executor: str,
        input_commitment: str,
        output_commitment: str,
        occurred_at: str | None = None,
        env: dict[str, Any] | None = None,
        duration_ms: int | None = None,
        assurance: str = ASSURANCE_SELF_REPORT,
        artifacts_ref: str | None = None,
        execution_id: str | None = None,
        reasoning: str = "",
        private_key: Any = None,
        verification_method: str | None = None,
    ) -> Event:
        """Append a signed EXECUTE receipt to the log.

        The receipt is hash-chained on append; if ``private_key`` (Ed25519) is
        supplied, a W3C LD-Proof is created *after* chaining so the proof
        covers the final event hash. Axiom 14 requires EXECUTE events to carry
        a proof, so unsigned receipts will fail ``verify_integrity`` — signing
        here is strongly recommended (and enforced by the CLI).
        """
        execution_id = execution_id or f"exec-{uuid4().hex}"
        payload: dict[str, Any] = {
            "execution_id": execution_id,
            "capability": self.capability_id,
            "occurred_at": occurred_at,
            "input_commitment": input_commitment,
            "output_commitment": output_commitment,
            "env": env or {},
            "duration_ms": duration_ms,
            "assurance": assurance,
            "artifacts_ref": artifacts_ref,
        }
        event = Event(
            concept_id=self.log_id,
            event_type=EventType.EXECUTE,
            actor=executor,
            reasoning=reasoning,
            payload=payload,
        )
        self._chain.append(event)

        if private_key is not None:
            from .ld_proof import create_event_proof

            event.proof = create_event_proof(
                event, private_key, verification_method=verification_method
            )
        else:
            logger.warning(
                "EXECUTE receipt %s recorded without a proof; axiom 14 will fail",
                execution_id,
            )
        return event

    # ------------------------------------------------------------------
    # Derived views
    # ------------------------------------------------------------------

    @property
    def receipts(self) -> list[Event]:
        return self._chain.events

    @property
    def count(self) -> int:
        return len(self._chain)

    @property
    def executors(self) -> list[str]:
        """Distinct executor actor identifiers, in first-seen order."""
        seen: dict[str, None] = {}
        for e in self._chain.events:
            seen[e.actor] = None
        return list(seen)

    def get_receipt(self, execution_id: str) -> Event | None:
        """Resolve a receipt by execution_id (for attestation lookup)."""
        for e in self._chain.events:
            if e.payload.get("execution_id") == execution_id:
                return e
        return None

    def merkle_root(self) -> str:
        """Merkle root over the event hashes of all receipts ("" if empty)."""
        leaves = [e.hash for e in self._chain]
        if not leaves:
            return ""
        return compute_chain_merkle_root(leaves)

    # ------------------------------------------------------------------
    # Anchoring into the governance chain
    # ------------------------------------------------------------------

    def build_anchor_event(
        self,
        *,
        actor: str,
        window_from: str | None = None,
        window_to: str | None = None,
        reasoning: str = "",
    ) -> Event:
        """Build an EXEC_ANCHOR event for the capability's *governance* chain.

        The returned event is NOT appended anywhere; the caller appends it to
        the main EventChain (or emits it as JSON). Its concept_id is the
        capability id, not the log id.
        """
        receipts = self.receipts
        if window_from is None and receipts:
            window_from = receipts[0].payload.get("occurred_at") or receipts[0].timestamp
        if window_to is None and receipts:
            window_to = receipts[-1].payload.get("occurred_at") or receipts[-1].timestamp
        payload: dict[str, Any] = {
            "log_id": self.log_id,
            "log_merkle_root": self.merkle_root(),
            "execution_count": self.count,
            "executor_set": self.executors,
            "window": {"from": window_from, "to": window_to},
        }
        return Event(
            concept_id=self.capability_id,
            event_type=EventType.EXEC_ANCHOR,
            actor=actor,
            reasoning=reasoning,
            payload=payload,
        )

    # ------------------------------------------------------------------
    # Integrity
    # ------------------------------------------------------------------

    def verify_integrity(self, registry: Any = None) -> bool:
        """Verify chain integrity (axioms 1–15) and the EXECUTE-only invariant."""
        for e in self._chain:
            if e.event_type is not EventType.EXECUTE:
                return False
        return self._chain.verify_integrity(registry=registry)

    # ------------------------------------------------------------------
    # JSONL persistence (proof fields included, unlike cold-storage archives)
    # ------------------------------------------------------------------

    @staticmethod
    def _event_to_dict(event: Event) -> dict[str, Any]:
        return {
            "event_id": event.event_id,
            "concept_id": event.concept_id,
            "event_type": event.event_type.value,
            "actor": event.actor,
            "reasoning": event.reasoning,
            "timestamp": event.timestamp,
            "payload": event.payload,
            "previous_event_id": event.previous_event_id,
            "hash": event.hash,
            "_prev_hash": event._prev_hash,
            "signature": event.signature,
            "proof": event.proof,
        }

    @staticmethod
    def _event_from_dict(data: dict[str, Any]) -> Event:
        e = Event(
            event_id=data["event_id"],
            concept_id=data["concept_id"],
            event_type=EventType(data["event_type"]),
            actor=data["actor"],
            reasoning=data.get("reasoning", ""),
            timestamp=data["timestamp"],
            payload=data["payload"],
            previous_event_id=data["previous_event_id"],
            hash=data["hash"],
        )
        e._prev_hash = data.get("_prev_hash", "")
        e.signature = data.get("signature", "") or ""
        e.proof = data.get("proof")
        return e

    def to_jsonl(self, path: str | Path) -> Path:
        """Write all receipts to a JSONL file (one event dict per line)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for event in self._chain:
                f.write(json.dumps(self._event_to_dict(event), sort_keys=True) + "\n")
        return path

    def append_jsonl(self, path: str | Path, event: Event) -> None:
        """Append a single receipt to an existing JSONL file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(self._event_to_dict(event), sort_keys=True) + "\n")

    @classmethod
    def from_jsonl(cls, path: str | Path, capability_id: str | None = None) -> ExecutionLog:
        """Load an ExecutionLog from a JSONL file written by :meth:`to_jsonl`."""
        path = Path(path)
        events: list[Event] = []
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(cls._event_from_dict(json.loads(line)))
        if capability_id is None:
            if not events:
                raise ValueError(f"Empty execution log and no capability_id given: {path}")
            capability_id = events[0].payload.get("capability") or events[
                0
            ].concept_id.removeprefix("execlog-")
        return cls(capability_id=capability_id, events=events)


def log_path_for(log_dir: str | Path, capability_id: str) -> Path:
    """Conventional JSONL path for a capability's execution log."""
    return Path(log_dir) / f"{capability_id}.execlog.jsonl"


def load_log(log_dir: str | Path, capability_id: str) -> ExecutionLog:
    """Load a capability's ExecutionLog from ``log_dir`` (empty log if absent)."""
    path = log_path_for(log_dir, capability_id)
    if not path.exists():
        return ExecutionLog(capability_id)
    return ExecutionLog.from_jsonl(path, capability_id=capability_id)
