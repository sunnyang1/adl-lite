"""
ADL Lite - Capability-Lifecycle Registry Core Models (Pydantic)

Structured Semantic Anchoring (SSA) core data models.
Every capability is represented as an append-only EventChain.

Philosophy (Wittgenstein, Tractatus §1.1):
    "The world is the totality of facts, not of things."
    → Action is primary. Objects exist only as participants in events.
    → EventChain IS the capability. FrontMatter is a derived snapshot.

References:
    - ADL Lite Spec §7.2: Three-layer syntax (L1/L2/L3)
    - ADL Lite Spec §7.4: Consensus status badges
    - ADL Lite Milestone 2d: L4 action blocks
"""

from __future__ import annotations

import base64
import hashlib
import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal, Union
from uuid import uuid4

from pydantic import BaseModel, Field, PrivateAttr, field_validator

from .crdt import StatusOrder

if TYPE_CHECKING:
    from .calibration import MARGINCalibrator

# ---------------------------------------------------------------------------
# Canonicalization version — bump when canonicalization rules change
# ---------------------------------------------------------------------------
CANON_VERSION = "1.0"

# ---------------------------------------------------------------------------
# Canonical serialization helpers
# ---------------------------------------------------------------------------


def _round_floats(obj: Any, ndigits: int = 6) -> Any:
    """Recursively round floats to *ndigits* decimal places for canonical hashing.

    This ensures cross-platform hash determinism: the same event produces the
    same SHA-256 digest regardless of Python version, OS, or JSON library
    float-string formatting differences.
    """
    if isinstance(obj, float):
        return round(obj, ndigits)
    if isinstance(obj, dict):
        return {k: _round_floats(v, ndigits) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_floats(item, ndigits) for item in obj]
    return obj


# ---------------------------------------------------------------------------
# Enumerations — Consensus & Semantic Types
# ---------------------------------------------------------------------------


class DiscoveryStatus(str, Enum):
    """Capability lifecycle status (emoji badges)."""

    PROVISIONAL = "provisional"  # 🟡
    VALIDATED = "validated"  # 🟢
    DEPRECATED = "deprecated"  # 🔴
    FORKED = "forked"  # 🔵
    ARCHIVED = "archived"  # ⚪


class ADLType(str, Enum):
    """Top-level semantic types for ADL registry entries."""

    DISCOVERY = "discovery"
    CONCEPT = "concept"
    RELATION = "relation"
    EVIDENCE = "evidence"
    FORMAL_SEAL = "formal_seal"


class MechanismType(str, Enum):
    """Valid isomorphic / analogical mechanism tags."""

    ISOMORPHIC_MAPPING = "isomorphic_mapping"
    ANALOGICAL_TRANSFER = "analogical_transfer"
    COMPOSITIONAL_BLEND = "compositional_blend"
    ABSTRACT_GENERALISATION = "abstract_generalisation"
    EMERGENT_PATTERN = "emergent_pattern"


class EvidenceType(str, Enum):
    """Evidence taxonomy for the evidence chain."""

    VECTOR_CLUSTER = "vector_cluster"
    SIMULATOR_RUN = "simulator_run"
    HUMAN_EXPERT = "human_expert"
    CROSS_REFERENCE = "cross_reference"
    EMPIRICAL_OBSERVATION = "empirical_observation"


class EventType(str, Enum):
    """Every event type in ADL Lite. Events ARE the capability lifecycle."""

    # Lifecycle events (status transitions)
    REGISTER = "register"
    VALIDATE = "validate"
    DEPRECATE = "deprecate"
    FORK = "fork"
    ARCHIVE = "archive"
    # Calibration events (per-actor accuracy tracking)
    CALIBRATE = "calibrate"
    # Assertion events (L3 semantic blocks)
    RELATE = "relate"
    EVIDENCE = "evidence"
    SEAL = "seal"
    REVOKE = "revoke"  # Explicit relation revocation (cessation semantics)
    # Communication events (L4 action blocks)
    ANNOUNCE = "announce"
    PUBLISH = "publish"
    SYNC_DASHBOARD = "sync_dashboard"
    LISTEN = "listen"
    # Internal / derived events
    SNAPSHOT = "snapshot"  # L1 front matter as a recorded state
    # Execution attestation events (EAL Phase 1: pure observability, paper §oracle)
    # These types are NOT consumed by status LUB or confidence G-Counter
    # derivation; they carry execution evidence only.
    EXECUTE = "execute"  # Signed execution receipt (lives on ExecutionLog)
    ATTEST = "attest"  # Verdict about an execution receipt (lives on main chain)
    EXEC_ANCHOR = "exec_anchor"  # Merkle anchor of an ExecutionLog (main chain)
    # EAL Phase 3: commit–reveal challenge protocol against cached answers.
    CHALLENGE = "challenge"  # Challenge open/reveal/answer phases (main chain)


# ---------------------------------------------------------------------------
# EAL (Execution Attestation Layer) conditional axioms 13–15
# ---------------------------------------------------------------------------

# Axiom 13: required payload fields per attestation event type.
_EAL_REQUIRED_PAYLOAD_FIELDS: dict[EventType, tuple[str, ...]] = {
    EventType.EXECUTE: ("execution_id", "input_commitment", "output_commitment"),
    EventType.ATTEST: ("subject_execution", "method", "verdict"),
    EventType.EXEC_ANCHOR: ("log_merkle_root",),
    EventType.CHALLENGE: ("challenge_id", "phase"),
}

# Axiom 14: event types that must carry a W3C LD-Proof object.
_EAL_PROOF_REQUIRED_TYPES: frozenset[EventType] = frozenset(
    {EventType.EXECUTE, EventType.ATTEST, EventType.CHALLENGE}
)

# Axiom 15 extension: CHALLENGE phases and their per-phase required fields.
_CHALLENGE_PHASES: frozenset[str] = frozenset({"open", "reveal", "answer"})
_CHALLENGE_PHASE_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "open": ("seed_commitment", "reveal_deadline", "response_window_s"),
    "reveal": ("seed",),
    "answer": ("output_commitment",),
}


def _challenge_payload_well_formed(payload: dict) -> bool:
    """Axiom 15 (EAL) extension: a CHALLENGE event must carry a valid phase and
    that phase's required fields. Cross-event checks (seed commitment matching,
    deadlines, phase ordering) are inherently multi-event and live in
    ``challenge.ChallengeManager``, not in the per-event axioms."""
    phase = payload.get("phase")
    if phase not in _CHALLENGE_PHASES:
        return False
    for field_name in _CHALLENGE_PHASE_REQUIRED_FIELDS[phase]:
        value = payload.get(field_name)
        if value is None or (isinstance(value, str) and not value.strip()):
            return False
    return True


# ---------------------------------------------------------------------------
# Event — the fundamental unit (event-first ontology)
# ---------------------------------------------------------------------------


class Event(BaseModel):
    """
    An Event is an atomic occurrence in a capability's lifecycle.

    Every event:
    - belongs to exactly one capability (concept_id)
    - links to the previous event (previous_event_id → forms the chain)
    - carries a typed payload (L3 block, L4 action params, etc.)
    - is cryptographically hashed (chain integrity)

    This IS the capability lifecycle. Objects don't have events — events ARE the world.
    """

    event_id: str = Field(
        default_factory=lambda: uuid4().hex,
        description="Unique event identifier (full 128-bit UUID)",
    )
    concept_id: str = Field(..., description="adl_id of the capability this event belongs to")
    event_type: EventType = Field(..., description="What happened")
    actor: str = Field(default="system", description="Who caused this event")
    reasoning: str = Field(default="", description="Why this event happened")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="When this event occurred",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Event-specific data (block fields, action params, etc.)"
    )
    previous_event_id: str | None = Field(
        default=None, description="Previous event in the chain (None for genesis event)"
    )
    hash: str = Field(
        default="", description="SHA-256 hash chaining event content with predecessor"
    )
    signature: str = Field(
        default="", description="Optional Ed25519 signature (base64) for DID-authenticated events"
    )
    proof: dict[str, Any] | None = Field(
        default=None,
        description="Optional W3C Linked Data Proof object (type, verificationMethod, proofValue)",
    )
    _prev_hash: str = PrivateAttr(default="")

    def model_post_init(self, __context) -> None:
        if not self.hash:
            self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Return a deterministic SHA-256 hash of this event's canonical content.

        Canonicalization rules (platform-independent):
          1. Include: event_id, concept_id, event_type, actor, timestamp,
             payload, previous_event_id, prev_hash, canon_version.
          2. Exclude: the hash field itself (to avoid circular self-reference).
          3. Recursively sort all object keys.
          4. Recursively round all floating-point values to 6 decimal places.
          5. Encode as UTF-8 JSON.

        The timestamp is intentionally INCLUDED in the hash input so that
        post-hoc timestamp edits are detectable as integrity violations.
        Clock-skew tolerance is handled at the application layer (event
        ordering uses previous_event_id linkage, not timestamp comparison).

        canon_version is included so that future canonicalization algorithm
        changes (e.g., new fields, different rounding rules) are detectable
        as hash mismatches, prompting chain re-anchoring.
        """
        event_type_value = (
            self.event_type.value
            if isinstance(self.event_type, EventType)
            else str(self.event_type)
        )
        content = {
            "event_id": self.event_id,
            "concept_id": self.concept_id,
            "event_type": event_type_value,
            "actor": self.actor,
            "timestamp": self.timestamp,
            "payload": _round_floats(self.payload),
            "previous_event_id": self.previous_event_id,
            "prev_hash": self._prev_hash,
            "canon_version": CANON_VERSION,
        }
        return hashlib.sha256(
            json.dumps(content, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()


class EventChain:
    """
    An append-only, cryptographically linked chain of events.

    THIS IS THE CAPABILITY. The capability does not "have" status or confidence.
    Status and confidence are computed from the chain.

    The chain is the digital twin — not a static model, but the live
    accumulation of all facts about a capability.
    """

    def __init__(
        self,
        concept_id: str,
        events: list[Event] | None = None,
        markdown_body: str = "",
        source_path: str | None = None,
    ) -> None:
        self.concept_id = concept_id
        # Split lock design for Phase 3 scale:
        #   _events_lock protects the append-only _events list.
        #   _cache_lock protects CRDT caches and the integrity verification cache.
        # Always acquire in the order _events_lock -> _cache_lock to avoid deadlock.
        # RLock avoids a macOS deadlock when cryptography (OpenSSL) and torch/
        # sentence-transformers (OpenMP) are loaded in the same process.
        self._events_lock = threading.RLock()
        self._cache_lock = threading.RLock()
        self.markdown_body = markdown_body
        self.source_path = source_path

        # CRDT incremental caches: updated on every append, O(1) query
        self._cached_status: DiscoveryStatus = DiscoveryStatus.PROVISIONAL
        self._cached_status_order: int = 0
        self._cached_confidence: float = 0.0

        # Incremental integrity verification cache (Definition 5: 12 base axioms
        # + EAL conditional axioms 13–15 for attestation event types)
        self._verified_index: int = -1
        self._verified_hash: str = ""
        self._verified_seen: set[str] = set()
        self._verified_event_ids: list[str] = []
        self._verified_last_dt: datetime | None = None

        # Set _events last so that caches are already in place when __setattr__
        # resets the integrity verification cache.
        self._events: list[Event] = []

        if events:
            for e in events:
                self.append(e)

    def __setattr__(self, name: str, value: Any) -> None:
        """Reset the integrity cache when the _events list is replaced directly."""
        if name == "_events":
            try:
                with self._cache_lock:
                    self._verified_index = -1
                    self._verified_hash = ""
                    self._verified_seen.clear()
                    self._verified_event_ids.clear()
                    self._verified_last_dt = None
            except AttributeError:
                # Caches are not yet initialized during the early stages of __init__.
                pass
        object.__setattr__(self, name, value)

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def append(self, event: Event) -> None:
        """Append an event, linking to the previous tail. Thread-safe."""
        with self._events_lock:
            if event.concept_id != self.concept_id:
                raise ValueError(
                    f"Event concept_id {event.concept_id} != chain concept_id {self.concept_id}"
                )
            if self._events:
                prev_event = self._events[-1]
                event.previous_event_id = prev_event.event_id
                event._prev_hash = prev_event.hash
                # Preserve weak timestamp monotonicity under contention: if the
                # event was created before the current tail, inherit the tail
                # timestamp.  The hash is recomputed below.
                if event.timestamp < prev_event.timestamp:
                    event.timestamp = prev_event.timestamp
                event.hash = ""  # Force re-computation with new chaining
                event.model_post_init(None)
            else:
                # First event in chain: reset to genesis state
                event.previous_event_id = None
                event._prev_hash = ""
                event.hash = ""
                event.model_post_init(None)
            self._events.append(event)
            # Incremental CRDT cache update
            self._update_crdt_caches(event)

    def _update_crdt_caches(self, event: Event) -> None:
        """Update _cached_status and _cached_confidence incrementally.

        Must be called while already holding _events_lock; this method acquires
        _cache_lock internally.
        """
        with self._cache_lock:
            # Status LUB: max over lifecycle lattice
            type_to_status = {
                EventType.REGISTER: DiscoveryStatus.PROVISIONAL,
                EventType.VALIDATE: DiscoveryStatus.VALIDATED,
                EventType.DEPRECATE: DiscoveryStatus.DEPRECATED,
                EventType.FORK: DiscoveryStatus.FORKED,
                EventType.ARCHIVE: DiscoveryStatus.ARCHIVED,
            }
            if event.event_type in type_to_status:
                status = type_to_status[event.event_type]
                order = StatusOrder[status.name.upper()].value
                if order > self._cached_status_order:
                    self._cached_status_order = order
                    self._cached_status = DiscoveryStatus[StatusOrder(order).name]

            # Confidence G-Counter: max over VALIDATE / SNAPSHOT
            if event.event_type in (EventType.VALIDATE, EventType.SNAPSHOT):
                val = min(1.0, max(0.0, float(event.payload.get("confidence", 0.0))))
                if val > self._cached_confidence:
                    self._cached_confidence = val

    def _invalidate_caches(self) -> None:
        """Reset CRDT and integrity caches after direct _events mutation.

        Must be called while already holding _events_lock; this method acquires
        _cache_lock internally.
        """
        with self._cache_lock:
            self._cached_status = DiscoveryStatus.PROVISIONAL
            self._cached_status_order = 0
            self._cached_confidence = 0.0
            self._verified_index = -1
            self._verified_hash = ""
            self._verified_seen.clear()
            self._verified_event_ids.clear()
            self._verified_last_dt = None

    def _rebuild_crdt_caches(self) -> None:
        """Rebuild CRDT caches from the full _events list.

        Must be called while already holding _events_lock; this method acquires
        _cache_lock internally.
        """
        with self._cache_lock:
            self._cached_status = DiscoveryStatus.PROVISIONAL
            self._cached_status_order = 0
            self._cached_confidence = 0.0
            for event in self._events:
                self._update_crdt_caches(event)

    @property
    def events(self) -> list[Event]:
        with self._events_lock:
            return list(self._events)

    @property
    def length(self) -> int:
        with self._events_lock:
            return len(self._events)

    def __len__(self) -> int:
        with self._events_lock:
            return len(self._events)

    def __iter__(self):
        with self._events_lock:
            return iter(list(self._events))

    def __getitem__(self, index: int) -> Event:
        with self._events_lock:
            return self._events[index]

    # ------------------------------------------------------------------
    # Computed properties (derived from events, NOT stored)
    # ------------------------------------------------------------------

    @property
    def status(self) -> DiscoveryStatus:
        """Status derived as LUB (max) over the lifecycle lattice (CRDT semantics).

        The status lattice is:
            provisional < forked < validated < deprecated < archived
        Once a concept reaches a higher-status state, it never regresses.
        This is the CRDT join-semilattice property (Theorem 9).

        O(1) — reads from the incremental cache updated on every append.
        """
        with self._events_lock:
            with self._cache_lock:
                # Defensive: if _events was mutated directly (bypassing append()),
                # the cache may be stale. Recompute when events exist but cache
                # is still at its default (order == 0).
                if self._events and self._cached_status_order == 0:
                    return self._compute_status_from_events()
                return self._cached_status

    def _compute_status_from_events(self) -> DiscoveryStatus:
        """Recompute status from all events (fallback when cache is stale)."""
        max_order = 0
        type_to_status = {
            EventType.REGISTER: DiscoveryStatus.PROVISIONAL,
            EventType.VALIDATE: DiscoveryStatus.VALIDATED,
            EventType.DEPRECATE: DiscoveryStatus.DEPRECATED,
            EventType.FORK: DiscoveryStatus.FORKED,
            EventType.ARCHIVE: DiscoveryStatus.ARCHIVED,
        }
        for event in self._events:
            if event.event_type in type_to_status:
                status = type_to_status[event.event_type]
                order = StatusOrder[status.name.upper()].value
                if order > max_order:
                    max_order = order
        if max_order == 0:
            return DiscoveryStatus.PROVISIONAL
        return DiscoveryStatus[StatusOrder(max_order).name]

    @property
    def confidence(self) -> float:
        """G-Counter: max confidence across all VALIDATE events (CRDT semantics).

        Unlike the previous LWW (last-writer-wins) O(1) implementation, this
        uses a G-Counter (max) semantics: once a validator asserts a high
        confidence, lower subsequent assertions cannot decrease the aggregate.
        This prevents malicious or erroneous validators from downgrading a
        concept's confidence after it has been validated.  See Theorem 9.

        O(1) — reads from the incremental cache updated on every append.
        """
        with self._events_lock:
            with self._cache_lock:
                # Defensive: if _events was mutated directly, recompute.
                if self._events and self._cached_confidence == 0.0:
                    return self._compute_confidence_from_events()
                return self._cached_confidence

    def _compute_confidence_from_events(self) -> float:
        """Recompute confidence from all events (fallback when cache is stale)."""
        max_conf = 0.0
        for event in self._events:
            if event.event_type in (EventType.VALIDATE, EventType.SNAPSHOT):
                val = min(1.0, max(0.0, float(event.payload.get("confidence", 0.0))))
                if val > max_conf:
                    max_conf = val
        return max_conf

    def calibrated_confidence(self, calibrator: MARGINCalibrator) -> float:
        """Return mean confidence calibrated by per-actor accuracy scores."""
        from .calibration import calibrated_confidence as _calibrated_confidence

        return _calibrated_confidence(self.events, calibrator)

    def ewma_confidence(self, alpha: float = 0.3) -> float:
        """Return EWMA-calibrated confidence with time-decay weighting."""
        from .calibration import ewma_confidence as _ewma_confidence

        return _ewma_confidence(self.events, alpha=alpha)

    def context_calibrated_confidence(
        self, calibrator: MARGINCalibrator, context: str = "general"
    ) -> float:
        """Return confidence calibrated within a specific epistemic context."""
        from .calibration import context_calibrated_confidence as _ctx_cal

        return _ctx_cal(self.events, calibrator, context=context)

    def band_calibrated_confidence(
        self,
        calibrator: MARGINCalibrator | None = None,
        bands: list[tuple[float, float, float]] | None = None,
    ) -> float:
        """Return per-band calibrated confidence addressing over/under-confidence."""
        from .calibration import band_calibrated_confidence as _band_cal

        return _band_cal(self.events, calibrator=calibrator, bands=bands)

    def aggregated_confidence(self) -> float:
        """
        Bonus-formula aggregate confidence (paper Appendix E).

        γ_agg = min(1.0, c_base + 0.05 × (N_vals − 1))
        where  c_base = max(0.5, mean_a φ(a,V))
               φ(a,V) = max confidence per actor
               N_vals = number of distinct validators
        """
        from .calibration import aggregated_confidence as _aggregated_confidence

        return _aggregated_confidence(self.events)

    @property
    def validators(self) -> list[str]:
        """Distinct actors who have performed VALIDATE events."""
        with self._events_lock:
            return list(
                dict.fromkeys(e.actor for e in self._events if e.event_type == EventType.VALIDATE)
            )

    @property
    def validator_count(self) -> int:
        """Number of distinct validators."""
        with self._events_lock:
            return len(self.validators)

    @property
    def created_at(self) -> str:
        """Capability creation time = first event timestamp."""
        with self._events_lock:
            if self._events:
                return self._events[0].timestamp
            return datetime.now(timezone.utc).isoformat()

    @property
    def updated_at(self) -> str:
        """Last modification = last event timestamp."""
        with self._events_lock:
            if self._events:
                return self._events[-1].timestamp
            return self.created_at

    # ------------------------------------------------------------------
    # Derived snapshot
    # ------------------------------------------------------------------

    def snapshot(self, adl_type: ADLType, identity_fields: dict) -> ADLFrontMatter:
        """
        Derive current front matter from the event chain.

        identity_fields must provide: adl_id, scope, domain, mechanism,
        provisional_names, novelty, evidence_refs — fields that are identity
        constants or set at registration, not mutated by events.
        """
        return ADLFrontMatter(
            adl_type=adl_type,
            adl_id=self.concept_id,
            status=self.status,
            confidence=self.confidence,
            validators=self.validators,
            created_at=self.created_at,
            updated_at=self.updated_at,
            **identity_fields,
        )

    def _check_wf5_distinct_event_ids(self) -> list[str]:
        """Axiom 5: all event_id values in the chain must be distinct."""
        seen: set[str] = set()
        duplicates: list[str] = []
        for event in self._events:
            if event.event_id in seen:
                duplicates.append(event.event_id)
            seen.add(event.event_id)
        return duplicates

    def _check_wf6_non_empty_actor(self) -> list[str]:
        """Axiom 6: every event must have a non-empty actor identifier."""
        return [e.event_id for e in self._events if not e.actor or not str(e.actor).strip()]

    def _check_wf7_timestamp_monotonicity(self) -> list[str]:
        """Axiom 7: event timestamps must be weakly monotonic (non-decreasing)."""
        violations: list[str] = []
        prev_ts: datetime | None = None
        for event in self._events:
            try:
                ts = datetime.fromisoformat(event.timestamp)
            except (ValueError, TypeError):
                ts = datetime.min.replace(tzinfo=timezone.utc)
            if prev_ts is not None and ts < prev_ts:
                violations.append(event.event_id)
            prev_ts = ts
        return violations

    def _check_wf8_payload_schema(self) -> list[str]:
        """Axiom 8: payload must be a dict (JSON object)."""
        return [e.event_id for e in self._events if not isinstance(e.payload, dict)]

    def _check_wf9_action_preconditions(self) -> list[str]:
        """Axiom 9: L4 action events must have 'action' field in payload."""
        action_types = {
            EventType.ANNOUNCE,
            EventType.PUBLISH,
            EventType.SYNC_DASHBOARD,
            EventType.LISTEN,
        }
        violations: list[str] = []
        for event in self._events:
            if event.event_type in action_types:
                action = event.payload.get("action")
                if not action:
                    violations.append(event.event_id)
        return violations

    def _check_wf10_hash_algorithm(self) -> list[str]:
        """Axiom 10: hash values must be 64-character hex (SHA-256)."""
        return [e.event_id for e in self._events if e.hash and len(e.hash) != 64]

    def _check_wf11_canonical_fields(self) -> list[str]:
        """Axiom 11: every non-genesis event must link to previous event."""
        violations: list[str] = []
        for i, event in enumerate(self._events):
            if i > 0 and not event.previous_event_id:
                violations.append(event.event_id)
            if i > 0 and not event.hash:
                violations.append(event.event_id)
        return violations

    def _check_wf12_event_type_valid(self) -> list[str]:
        """Axiom 12: event_type must be a known EventType enum member."""
        return [e.event_id for e in self._events if not isinstance(e.event_type, EventType)]

    def _check_wf13_evidence_schema(self) -> list[str]:
        """Axiom 13 (EAL): attestation events carry required payload fields."""
        violations: list[str] = []
        for event in self._events:
            required = _EAL_REQUIRED_PAYLOAD_FIELDS.get(event.event_type)
            if required is None:
                continue
            for field_name in required:
                value = event.payload.get(field_name)
                if value is None or (isinstance(value, str) and not value.strip()):
                    violations.append(event.event_id)
                    break
        return violations

    def _check_wf14_proof_presence(self) -> list[str]:
        """Axiom 14 (EAL): EXECUTE/ATTEST events must carry an LD-Proof object."""
        violations: list[str] = []
        for event in self._events:
            if event.event_type not in _EAL_PROOF_REQUIRED_TYPES:
                continue
            proof = event.proof
            if not isinstance(proof, dict) or not proof.get("type") or not proof.get("proofValue"):
                violations.append(event.event_id)
        return violations

    def _check_wf15_verdict_consistency(self) -> list[str]:
        """Axiom 15 (EAL): ATTEST verdicts and CHALLENGE phases must be self-consistent."""
        violations: list[str] = []
        for event in self._events:
            if event.event_type is EventType.CHALLENGE:
                if not _challenge_payload_well_formed(event.payload):
                    violations.append(event.event_id)
                continue
            if event.event_type is not EventType.ATTEST:
                continue
            verdict = event.payload.get("verdict")
            if verdict not in ("confirm", "refute", "inconclusive"):
                violations.append(event.event_id)
                continue
            method = event.payload.get("method")
            replay = event.payload.get("replay")
            if method == "replay" and verdict == "confirm":
                if not isinstance(replay, dict) or replay.get("match") is not True:
                    violations.append(event.event_id)
                    continue
                if not replay.get("input_commitment") or not replay.get("output_commitment"):
                    violations.append(event.event_id)
                    continue
            if verdict == "refute":
                has_evidence = bool(event.payload.get("evidence_ref"))
                has_mismatch = isinstance(replay, dict) and replay.get("match") is False
                if not has_evidence and not has_mismatch:
                    violations.append(event.event_id)
        return violations

    def _parse_event_dt(self, ts: str) -> datetime:
        """Parse an ISO timestamp, returning a minimal datetime on failure."""
        try:
            return datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            return datetime.min.replace(tzinfo=timezone.utc)

    def _verify_prefix(self, registry=None) -> bool:
        """Incrementally verify events from _verified_index+1 to the tail.

        Assumes both _events_lock and _cache_lock are already held.

        - If the chain has grown since the last check, only the newly appended
          events are verified, giving O(k) cost for k new events.
        - If the chain length is unchanged, the whole chain is revalidated so
          that tampering with any previously verified event is still detected.
          This keeps the security guarantees identical to the non-incremental
          implementation for the "no new events" case.
        - If events were inserted, deleted, or replaced in the verified prefix,
          the cache is invalidated and a full verification is performed.
        """
        events = self._events
        n = len(events)
        verified_ids = self._verified_event_ids

        # Check whether the previously verified prefix still matches the current
        # events in both length and event_id order.  A mismatch means the chain
        # was modified in the middle (insert/delete/replace), so we fall back to
        # a full verification.
        prefix_match = True
        prefix_len = min(len(verified_ids), n)
        for i in range(prefix_len):
            if verified_ids[i] != events[i].event_id:
                prefix_match = False
                break

        if not prefix_match or len(verified_ids) > n:
            # External direct modification of the prefix: invalidate cache.
            self._verified_index = -1
            self._verified_hash = ""
            self._verified_seen.clear()
            verified_ids.clear()
            self._verified_last_dt = None
            start = 0
        elif len(verified_ids) == n:
            # No new events: revalidate everything to detect tampering.
            self._verified_index = -1
            self._verified_hash = ""
            self._verified_seen.clear()
            verified_ids.clear()
            self._verified_last_dt = None
            start = 0
        else:
            # Normal append path: trust the verified prefix and verify the suffix.
            start = len(verified_ids)

        last_dt = self._verified_last_dt
        if start > 0 and start <= n:
            last_dt = self._parse_event_dt(events[start - 1].timestamp)

        action_types = {
            EventType.ANNOUNCE,
            EventType.PUBLISH,
            EventType.SYNC_DASHBOARD,
            EventType.LISTEN,
        }

        for i in range(start, n):
            event = events[i]

            if i == 0:
                # Axiom 1: genesis anchoring
                if event.previous_event_id is not None:
                    has_archive = any(e.event_type == EventType.ARCHIVE for e in events)
                    if not has_archive:
                        return False
            else:
                prev_event = events[i - 1]
                # Axiom 3: cryptographic linkage
                if event.previous_event_id == prev_event.event_id:
                    if event._prev_hash != prev_event.hash:
                        return False
                else:
                    # An archive is the only allowed discontinuity, and it may
                    # only appear between the genesis event and the first hot event.
                    if i != 1 or not any(e.event_type == EventType.ARCHIVE for e in events):
                        return False

            # Axiom 2: shared concept_id
            if event.concept_id != self.concept_id:
                return False

            # Axiom 4: hash correctness
            if event.hash != event._compute_hash():
                return False

            # Optional signature / LD-Proof verification
            if registry is not None:
                if event.signature:
                    message = event.hash.encode("utf-8")
                    sig_bytes = base64.b64decode(event.signature)
                    if not registry.verify_signature(event.actor, message, sig_bytes):
                        return False
                if event.proof:
                    from .ld_proof import verify_event_proof

                    if not verify_event_proof(event, resolver=registry):
                        return False

            # Axiom 5: distinct event_ids
            if event.event_id in self._verified_seen:
                return False
            self._verified_seen.add(event.event_id)
            self._verified_event_ids.append(event.event_id)

            # Axiom 6: non-empty actor
            if not event.actor or not str(event.actor).strip():
                return False

            # Axiom 7: weakly monotonic timestamps
            ts = self._parse_event_dt(event.timestamp)
            if last_dt is not None and ts < last_dt:
                return False
            last_dt = ts

            # Axiom 8: payload is a dict
            if not isinstance(event.payload, dict):
                return False

            # Axiom 9: L4 action events carry an action field
            if event.event_type in action_types:
                if not event.payload.get("action"):
                    return False

            # Axiom 10: hash algorithm (64-char hex)
            if event.hash and len(event.hash) != 64:
                return False

            # Axiom 11: canonical fields for non-genesis events
            if i > 0 and not event.previous_event_id:
                return False
            if not event.hash:
                return False

            # Axiom 12: valid event type
            if not isinstance(event.event_type, EventType):
                return False

            # Axiom 13 (EAL): evidence schema — attestation events carry their
            # required commitment/reference fields.
            required = _EAL_REQUIRED_PAYLOAD_FIELDS.get(event.event_type)
            if required is not None:
                for field_name in required:
                    value = event.payload.get(field_name)
                    if value is None or (isinstance(value, str) and not value.strip()):
                        return False

            # Axiom 14 (EAL): proof presence — EXECUTE and ATTEST events must
            # carry a W3C LD-Proof object. Evidence without non-repudiation is
            # worthless; these are new event types with no legacy chains, so the
            # constraint is hard. Cryptographic verification of the proof itself
            # happens above when a registry is supplied.
            if event.event_type in _EAL_PROOF_REQUIRED_TYPES:
                proof = event.proof
                if (
                    not isinstance(proof, dict)
                    or not proof.get("type")
                    or not proof.get("proofValue")
                ):
                    return False

            # Axiom 15 (EAL): verdict consistency for ATTEST events.
            if event.event_type is EventType.ATTEST:
                verdict = event.payload.get("verdict")
                if verdict not in ("confirm", "refute", "inconclusive"):
                    return False
                method = event.payload.get("method")
                replay = event.payload.get("replay")
                if method == "replay" and verdict == "confirm":
                    # A confirming replay must report a positive match with
                    # non-empty commitments. Cross-chain equality with the
                    # subject execution's commitments is checked at the
                    # validation layer (execution_lookup), not here.
                    if not isinstance(replay, dict) or replay.get("match") is not True:
                        return False
                    if not replay.get("input_commitment") or not replay.get("output_commitment"):
                        return False
                if verdict == "refute":
                    # A refutation must cite evidence or report a replay mismatch.
                    has_evidence = bool(event.payload.get("evidence_ref"))
                    has_mismatch = isinstance(replay, dict) and replay.get("match") is False
                    if not has_evidence and not has_mismatch:
                        return False

            # Axiom 15 (EAL) extension: phase consistency for CHALLENGE events.
            if event.event_type is EventType.CHALLENGE:
                if not _challenge_payload_well_formed(event.payload):
                    return False

        self._verified_index = n - 1
        if events:
            self._verified_hash = events[-1].hash
        self._verified_last_dt = last_dt
        return True

    def verify_integrity(self, full: bool = False, registry=None) -> bool:
        """
        Verify that the chain is well-formed per Definition 5 (12 base axioms
        plus EAL conditional axioms 13–15 for EXECUTE/ATTEST/EXEC_ANCHOR/CHALLENGE
        events).

        This method is incremental: after a full verification, subsequent calls
        only examine events appended since the last check, giving O(k) cost for
        k new events and O(1) cost when nothing has changed.

        Args:
            full: If True, also verify archive file hashes and archived subchain integrity.
            registry: Optional KeyRegistry for Ed25519 signature verification on events
                      that carry a non-empty signature field (paper §4.3).
        """
        with self._events_lock:
            with self._cache_lock:
                if not self._events:
                    return True

                if not self._verify_prefix(registry):
                    return False

                if not full:
                    return True

                # full=True: verify archive file hashes and archived subchain integrity
                from pathlib import Path

                from .cold_storage import ColdStorage

                for event in self._events:
                    if event.event_type != EventType.ARCHIVE:
                        continue
                    pointer = event.payload.get("archive_pointer", "")
                    file_path = event.payload.get("archive_file", "")
                    if not pointer or not file_path:
                        continue
                    if not ColdStorage.verify_archive(pointer, file_path):
                        return False
                    archived_events = ColdStorage._read_events(Path(file_path))
                    for i, ae in enumerate(archived_events):
                        if i > 0:
                            if ae.previous_event_id != archived_events[i - 1].event_id:
                                return False
                            if ae._prev_hash != archived_events[i - 1].hash:
                                return False
                        if ae.hash != ae._compute_hash():
                            return False
                    if len(self._events) > 1:
                        hot_next = self._events[1]
                        if hot_next.event_type != EventType.ARCHIVE and archived_events:
                            last_archived = archived_events[-1]
                            if hot_next.previous_event_id != last_archived.event_id:
                                return False
                            if hot_next._prev_hash != last_archived.hash:
                                return False
                return True

    def well_formedness_report(self) -> dict[str, list[str]]:
        """
        Return a detailed report of which axioms pass/fail.
        Useful for debugging integrity violations.
        """
        with self._events_lock:
            return {
                "axiom_1_genesis_anchoring": [],
                "axiom_2_shared_concept": [],
                "axiom_3_cryptographic_linkage": [],
                "axiom_4_hash_correctness": [],
                "axiom_5_distinct_event_ids": self._check_wf5_distinct_event_ids(),
                "axiom_6_non_empty_actor": self._check_wf6_non_empty_actor(),
                "axiom_7_timestamp_monotonicity": self._check_wf7_timestamp_monotonicity(),
                "axiom_8_payload_schema": self._check_wf8_payload_schema(),
                "axiom_9_action_preconditions": self._check_wf9_action_preconditions(),
                "axiom_10_hash_algorithm": self._check_wf10_hash_algorithm(),
                "axiom_11_canonical_fields": self._check_wf11_canonical_fields(),
                "axiom_12_event_type_valid": self._check_wf12_event_type_valid(),
                "axiom_13_evidence_schema": self._check_wf13_evidence_schema(),
                "axiom_14_proof_presence": self._check_wf14_proof_presence(),
                "axiom_15_verdict_consistency": self._check_wf15_verdict_consistency(),
            }

    def integrity_violations(self) -> list[str]:
        """Return a human-readable list of all integrity violations."""
        report = self.well_formedness_report()
        violations: list[str] = []
        for axiom, event_ids in report.items():
            if event_ids:
                violations.append(f"{axiom}: event_ids={event_ids}")
        return violations

    def history(self) -> list[dict[str, Any]]:
        """Full chain history as a list of dicts. Synthetic events flagged. Thread-safe."""
        with self._events_lock:
            return [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type.value,
                    "actor": e.actor,
                    "reasoning": e.reasoning,
                    "timestamp": e.timestamp,
                    "hash": e.hash,
                    "_prev_hash": e._prev_hash,
                    "synthetic": e.payload.get("synthetic", False),
                    "payload": e.payload,
                }
                for e in self._events
            ]

    def archive(self, keep_last_n: int = 10, compressed: bool = False) -> Event | None:
        """Migrate historical events to cold storage and append an ARCHIVE event."""
        from .cold_storage import ColdStorage

        return ColdStorage().archive(self, keep_last_n=keep_last_n, compressed=compressed)

    def unarchive(self) -> list[Event]:
        """Return archived events from cold storage."""
        from .cold_storage import ColdStorage

        return ColdStorage().unarchive(self.concept_id)

    # ------------------------------------------------------------------
    # Factory: build chain from parsed blocks + front matter
    # ------------------------------------------------------------------

    @classmethod
    def from_parsed(
        cls,
        concept_id: str,
        front_matter: ADLFrontMatter,
        l3_blocks: list[ADLBlock],
        action_blocks: list[ADLActionBlock],
        markdown_body: str = "",
        source_path: str | None = None,
    ) -> EventChain:
        """Build an EventChain from parsed document components."""
        chain = cls(concept_id=concept_id, markdown_body=markdown_body, source_path=source_path)

        # Genesis event: snapshot captures L1 identity.
        # Tagged synthetic=True — this event was not authored by an agent,
        # it was synthesized from the YAML front matter during parsing.
        chain.append(
            Event(
                concept_id=concept_id,
                event_type=EventType.SNAPSHOT,
                actor="parser",
                reasoning="Document parsed — initial L1 snapshot (synthetic)",
                payload={
                    "adl_type": front_matter.adl_type.value,
                    "confidence": front_matter.confidence,
                    "novelty": front_matter.novelty,
                    "domain": front_matter.domain,
                    "scope": front_matter.scope,
                    "synthetic": True,
                    "provisional_names": {
                        "zh": front_matter.provisional_names.zh,
                        "en": front_matter.provisional_names.en,
                    },
                },
            )
        )

        # If status != provisional, add the appropriate lifecycle event.
        # Tagged synthetic=True — this event was not authored by an agent
        # action; it is a reconstruction from the YAML front matter status field.
        if front_matter.status != DiscoveryStatus.PROVISIONAL:
            status_to_type = {
                DiscoveryStatus.VALIDATED: EventType.VALIDATE,
                DiscoveryStatus.DEPRECATED: EventType.DEPRECATE,
                DiscoveryStatus.FORKED: EventType.FORK,
                DiscoveryStatus.ARCHIVED: EventType.ARCHIVE,
            }
            evt = status_to_type.get(front_matter.status)
            if evt:
                chain.append(
                    Event(
                        concept_id=concept_id,
                        event_type=evt,
                        actor=front_matter.validators[-1] if front_matter.validators else "unknown",
                        reasoning="Status restored from parsed document (synthetic)",
                        payload={"confidence": front_matter.confidence, "synthetic": True},
                    )
                )

        # L3 blocks → assertion events
        for block in l3_blocks:
            if isinstance(block, ADLRelationBlock):
                chain.append(
                    Event(
                        concept_id=concept_id,
                        event_type=EventType.RELATE,
                        actor="author",
                        reasoning=f"Relation asserted: {block.relation}",
                        payload=block.model_dump(),
                    )
                )
            elif isinstance(block, ADLEvidenceBlock):
                chain.append(
                    Event(
                        concept_id=concept_id,
                        event_type=EventType.EVIDENCE,
                        actor="author",
                        payload=block.model_dump(),
                    )
                )
            elif isinstance(block, ADLFormalSealBlock):
                chain.append(
                    Event(
                        concept_id=concept_id,
                        event_type=EventType.SEAL,
                        actor="author",
                        payload=block.model_dump(),
                    )
                )

        # L4 action blocks → action events
        for ab in action_blocks:
            chain.append(
                Event(
                    concept_id=concept_id,
                    event_type=EventType(ab.action)
                    if ab.action in EventType._value2member_map_
                    else EventType.ANNOUNCE,
                    actor=ab.actor,
                    reasoning=ab.reasoning,
                    payload={
                        "action": ab.action,
                        "params": ab.params,
                        "exec_status": ab.exec_status.value,
                    },
                )
            )

        return chain


# ---------------------------------------------------------------------------
# L1: YAML Front Matter Model
# ---------------------------------------------------------------------------


class ProvisionalNames(BaseModel):
    """Multilingual provisional naming."""

    zh: str | None = None
    en: str | None = None


class ADLFrontMatter(BaseModel):
    """
    L1 Header — derived snapshot of a capability's current state.

    IMPORTANT (event-first ontology): FrontMatter is a SNAPSHOT derived from
    the EventChain, NOT the source of truth. Status, confidence, and validators
    are computed from the chain. Mutating front_matter.status directly is
    discouraged; use EventChain.append(Event(...)) and then re-snapshot.
    """

    adl_type: ADLType = Field(..., description="Semantic type of the document")
    adl_id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$", description="Unique identifier")
    status: DiscoveryStatus = Field(default=DiscoveryStatus.PROVISIONAL)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    novelty: float = Field(default=0.0, ge=0.0, le=1.0)
    domain: str = Field(default="", description="Domain tag, e.g. 'financial_aml'")
    mechanism: MechanismType | None = None
    scope: str = Field(default="public", description="Namespace scope")
    validators: list[str] = Field(default_factory=list)
    provisional_names: ProvisionalNames = Field(default_factory=ProvisionalNames)
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None
    l2_template: str | bool | None = None

    @classmethod
    def from_chain(cls, chain: EventChain, adl_type: ADLType, identity: dict) -> ADLFrontMatter:
        """Derive front matter from an EventChain (the source of truth)."""
        return ADLFrontMatter(
            adl_type=adl_type,
            adl_id=chain.concept_id,
            status=chain.status,
            confidence=chain.confidence,
            validators=chain.validators,
            created_at=chain.created_at,
            updated_at=chain.updated_at,
            domain=identity.get("domain", ""),
            mechanism=identity.get("mechanism"),
            scope=identity.get("scope", "public"),
            novelty=identity.get("novelty", 0.0),
            provisional_names=identity.get("provisional_names", ProvisionalNames()),
            evidence_refs=identity.get("evidence_refs", []),
        )

    def identity_dict(self) -> dict:
        """Return the identity fields (not computed from chain)."""
        return {
            "domain": self.domain,
            "mechanism": self.mechanism,
            "scope": self.scope,
            "novelty": self.novelty,
            "provisional_names": self.provisional_names,
            "evidence_refs": self.evidence_refs,
        }

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: str) -> str:
        valid_prefixes = ("public", "private/", "user/", "shared/")
        if not any(v.startswith(p) for p in valid_prefixes):
            raise ValueError(f"Scope must start with one of {valid_prefixes}, got: {v}")
        return v

    @property
    def status_badge(self) -> str:
        badges = {
            DiscoveryStatus.PROVISIONAL: "🟡",
            DiscoveryStatus.VALIDATED: "🟢",
            DiscoveryStatus.DEPRECATED: "🔴",
            DiscoveryStatus.FORKED: "🔵",
            DiscoveryStatus.ARCHIVED: "⚪",
        }
        return badges.get(self.status, "⬜")

    @property
    def is_public(self) -> bool:
        return self.scope == "public" or self.scope.startswith("public/")

    @property
    def is_private(self) -> bool:
        return self.scope.startswith("private/")

    @property
    def validator_count(self) -> int:
        """Number of distinct validators (derived from validators list)."""
        return len(self.validators)


# ---------------------------------------------------------------------------
# L3: ADL Block Models (embedded ```adl:* code blocks)
# ---------------------------------------------------------------------------


class ADLRelationBlock(BaseModel):
    """
    L3 Relation Block — typed edge between capabilities.
    Syntax: ```adl:relation ... ```
    """

    block_type: Literal["relation"] = "relation"
    source: str = Field(..., description="Source capability name or URI")
    relation: str = Field(..., description="Relation predicate, e.g. 'isomorphic-to'")
    target: str = Field(..., description="Target capability URI or name")
    mapping_type: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("source", "target")
    @classmethod
    def validate_no_pronouns(cls, v: str) -> str:
        forbidden = {"this", "that", "it", "these", "those", "这个", "那个", "它", "它们"}
        lowered = v.lower().strip()
        if lowered in forbidden:
            raise ValueError(f"Pronouns are forbidden in ADL slots: '{v}'")
        return v


class ADLEvidenceBlock(BaseModel):
    """
    L3 Evidence Block — structured evidence entry.
    Syntax: ```adl:evidence ... ```
    """

    block_type: Literal["evidence"] = "evidence"
    evidence_type: EvidenceType
    data_ref: str = Field(..., description="Pointer to data (vecdb://, file://, etc.)")
    description: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    observed_at: str | None = None


class ADLFormalSealBlock(BaseModel):
    """
    L3 Formal Seal — formal verification reference.
    Syntax: ```adl:seal ... ```
    """

    block_type: Literal["seal"] = "seal"
    assertion: str = Field(..., description="Formal assertion statement")
    language: Literal["lean4", "coq", "z3", "fol"] = "lean4"
    proof_ref: str | None = None
    status: Literal["pending", "verified", "failed"] = "pending"
    verified_by: str | None = None


class ADLExecutionInvocation(BaseModel):
    """How to invoke a capability for execution/replay (EAL Phase 1)."""

    type: Literal["cli", "http", "python"] = "cli"
    command: str = Field(default="", description="Invocation template, may use {input_file}")
    endpoint: str | None = Field(default=None, description="URL for type=http")
    timeout_ms: int = Field(default=5000, gt=0)


class ADLExecutionTestVector(BaseModel):
    """A replay benchmark: committed input → expected committed output."""

    input_commitment: str = Field(..., description="sha256 commitment of the input")
    expected_output_commitment: str = Field(
        ..., description="sha256 commitment of the expected output"
    )


class ADLExecutionBlock(BaseModel):
    """
    L3 Execution Spec — declares how a capability is invoked and replayed so
    that validators can independently re-execute and attest (EAL Phase 1).

    Unlike other L3 blocks (flat KV lines), the body is parsed as YAML because
    the spec is nested (invocation / properties / test_vectors).

    Syntax: ```adl:execution ... ```
    """

    block_type: Literal["execution"] = "execution"
    invocation: ADLExecutionInvocation = Field(default_factory=ADLExecutionInvocation)
    determinism: Literal["deterministic", "stochastic", "side-effecting"] = "deterministic"
    properties: list[str] = Field(
        default_factory=list,
        description="Declarative property assertions checked by property-check attestations",
    )
    test_vectors: list[ADLExecutionTestVector] = Field(default_factory=list)


# Union type for all L3 blocks  # noqa: UP007 — Python 3.9 compat
ADLBlock = Union[ADLRelationBlock, ADLEvidenceBlock, ADLFormalSealBlock, ADLExecutionBlock]  # noqa: UP007


# ---------------------------------------------------------------------------
# L4: Action Blocks (embedded ```adl:action blocks, Milestone 2d)
# ---------------------------------------------------------------------------


class ActionExecStatus(str, Enum):
    """Execution status for L4 action blocks."""

    PENDING = "pending"
    EXECUTED = "executed"
    FAILED = "failed"
    REVERTED = "reverted"


class Comparator(str, Enum):
    """Comparison operators for precondition rules."""

    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    EXISTS = "exists"


class PreconditionRule(BaseModel):
    """
    A single precondition rule in the action ontology registry.
    Checked against ADLFrontMatter fields at execution time.
    """

    field: str = Field(..., description="ADLFrontMatter field name, e.g. 'confidence'")
    comparator: Comparator = Field(..., description="Comparison operator")
    value: Any = Field(default=None, description="Expected value (ignored for EXISTS)")

    def check(self, fm: ADLFrontMatter) -> bool:
        """Evaluate this rule against a front-matter instance."""
        actual = getattr(fm, self.field, None)

        if self.comparator == Comparator.EXISTS:
            return actual is not None

        if self.comparator == Comparator.IN:
            target_list = self.value if isinstance(self.value, list) else [self.value]
            return actual in target_list

        if actual is None:
            return False

        _ops = {
            Comparator.EQ: lambda a, v: bool(a == v),
            Comparator.NEQ: lambda a, v: bool(a != v),
            Comparator.GT: lambda a, v: bool(a > v),
            Comparator.GTE: lambda a, v: bool(a >= v),
            Comparator.LT: lambda a, v: bool(a < v),
            Comparator.LTE: lambda a, v: bool(a <= v),
        }
        op = _ops[self.comparator]

        # Guard against non-scalar / incompatible comparisons that would either
        # raise (e.g. dict > int) or produce confusing NEQ truths (e.g. dict != 0).
        if self.comparator in {Comparator.EQ, Comparator.NEQ}:
            if isinstance(actual, dict | list | tuple | set | frozenset):
                return False

        try:
            return op(actual, self.value)
        except TypeError:
            return False


class ActionDef(BaseModel):
    """Canonical action definition loaded from adl_core_ontology.yaml."""

    name: str
    description: str = ""
    allowed_on: list[str] = Field(default_factory=list)
    triggers_transition: str | None = None
    required_params: list[str] = Field(default_factory=list)
    preconditions: list[PreconditionRule] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)


class ExecutionEntry(BaseModel):
    """A single execution log entry for an action block."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    executor: str = "system"
    side_effect: str
    result: str = "success"  # success | failure
    detail: str | None = None


class ADLActionBlock(BaseModel):
    """
    L4 Action Block — typed action with side effects.

    Syntax: ```adl:action
    id: validate
    actor: agent_3
    reasoning: "..."
    params:
      ...
    ```
    """

    block_type: Literal["action"] = "action"
    action_block_id: str = Field(
        default="", description="Unique idempotency key (auto-generated or explicit)"
    )
    action: str = Field(..., description="Action name, must be in ontology registry")
    actor: str = Field(..., description="Agent or human identifier")
    reasoning: str = ""
    timestamp: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    exec_status: ActionExecStatus = Field(default=ActionExecStatus.PENDING)
    execution_log: list[ExecutionEntry] = Field(default_factory=list)


# Union type for all blocks (L3 + L4)  # noqa: UP007 — Python 3.9 compat
AllBlocks = Union[ADLRelationBlock, ADLEvidenceBlock, ADLFormalSealBlock, ADLActionBlock]  # noqa: UP007


# ---------------------------------------------------------------------------
# Concept Skeleton (Hot Storage)
# ---------------------------------------------------------------------------


class ConceptSkeleton(BaseModel):
    """
    Lightweight summary for fast retrieval (< 500 bytes).
    Stored in Hot layer (in-memory HashMap).
    """

    adl_id: str
    semantic_type: ADLType
    domain_tag: str
    status: DiscoveryStatus
    scope: str
    relation_summary: list[str] = Field(default_factory=list)
    evidence_count: int = 0
    confidence: float = 0.0
    novelty: float = 0.0
    tenant_id: str | None = None  # Owning tenant (set from doc._tenant_id)

    @classmethod
    def from_front_matter(cls, fm: ADLFrontMatter) -> ConceptSkeleton:
        return cls(
            adl_id=fm.adl_id,
            semantic_type=fm.adl_type,
            domain_tag=fm.domain,
            status=fm.status,
            scope=fm.scope,
            confidence=fm.confidence,
            novelty=fm.novelty,
        )


# ---------------------------------------------------------------------------
# Full Parsed ADL Document
# ---------------------------------------------------------------------------


class ADLDocument(BaseModel):
    """
    Complete in-memory representation of an ADL Lite document.

    L1 (front_matter) + L2 (markdown_body) + L3 (adl_blocks) + L4 (action_blocks).

    Philosophy: The EventChain IS the capability. FrontMatter is a derived snapshot.
    Status/confidence are computed from the chain, not stored as mutable fields.
    """

    front_matter: ADLFrontMatter
    markdown_body: str = ""
    adl_blocks: list[ADLBlock] = Field(default_factory=list)
    action_blocks: list[ADLActionBlock] = Field(default_factory=list)
    source_path: str | None = None

    # --- Computed properties ---

    @property
    def adl_id(self) -> str:
        return self.front_matter.adl_id

    @property
    def event_chain(self) -> EventChain:
        return EventChain.from_parsed(
            concept_id=self.adl_id,
            front_matter=self.front_matter,
            l3_blocks=self.adl_blocks,
            action_blocks=self.action_blocks,
            markdown_body=self.markdown_body,
            source_path=self.source_path,
        )

    @property
    def status(self) -> DiscoveryStatus:
        return self.front_matter.status

    @property
    def scope(self) -> str:
        return self.front_matter.scope

    @property
    def concept_name(self) -> str:
        """Return the English or Chinese provisional name."""
        names = self.front_matter.provisional_names
        return names.en or names.zh or self.adl_id

    @property
    def relations(self) -> list[ADLRelationBlock]:
        return [b for b in self.adl_blocks if isinstance(b, ADLRelationBlock)]

    @property
    def evidence(self) -> list[ADLEvidenceBlock]:
        return [b for b in self.adl_blocks if isinstance(b, ADLEvidenceBlock)]

    @property
    def seals(self) -> list[ADLFormalSealBlock]:
        return [b for b in self.adl_blocks if isinstance(b, ADLFormalSealBlock)]

    @property
    def execution_spec(self) -> ADLExecutionBlock | None:
        """The declared execution spec (```adl:execution block), if present."""
        for b in self.adl_blocks:
            if isinstance(b, ADLExecutionBlock):
                return b
        return None

    @property
    def actions(self) -> list[ADLActionBlock]:
        return self.action_blocks

    @property
    def pending_actions(self) -> list[ADLActionBlock]:
        return [a for a in self.action_blocks if a.exec_status == ActionExecStatus.PENDING]

    @property
    def wiki_links(self) -> list[str]:
        """L2 wiki-link slugs extracted from markdown body."""
        from .parser import extract_wiki_links

        return extract_wiki_links(self.markdown_body)

    def refresh_snapshot(self, chain: EventChain | None = None) -> None:
        c = chain or self.event_chain
        self.front_matter = ADLFrontMatter.from_chain(
            c,
            adl_type=self.front_matter.adl_type,
            identity=self.front_matter.identity_dict(),
        )

    def to_skeleton(self) -> ConceptSkeleton:
        """Derive the Hot-storage skeleton from this document."""
        sk = ConceptSkeleton.from_front_matter(self.front_matter)
        sk.relation_summary = [f"{r.source}--{r.relation}-->{r.target}" for r in self.relations]
        sk.evidence_count = len(self.evidence)
        sk.tenant_id = getattr(self, "_tenant_id", None)
        return sk

    def validate_semantics(self) -> list[str]:
        """Run semantic validation and return list of errors."""
        from .validator import ADLValidator

        validator = ADLValidator()
        return validator.validate_document(self)


# ---------------------------------------------------------------------------
# Validation Result (structured SHACL / SSA validation output)
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Structured output from SHACL or SSA validation.

    Fields:
        path: The property path or component that failed (e.g. "adl:eventType", "L1 scope")
        severity: Severity level — one of "Violation", "Warning", "Info"
        message: Human-readable description of the validation issue
    """

    path: str
    severity: str  # "Violation" | "Warning" | "Info"
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.path}: {self.message}"
