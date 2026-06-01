"""
ADL Lite - Semantic Type Models (Pydantic)

Structured Semantic Anchoring (SSA) core data models.
Every ADL document decomposes into typed slots that constrain
the interpretive space of natural language.

Philosophy (Wittgenstein, Tractatus §1.1):
    "The world is the totality of facts, not of things."
    → Action is primary. Objects exist only as participants in events.
    → EventChain IS the concept. FrontMatter is a derived snapshot.

References:
    - ADL Lite Spec §7.2: Three-layer syntax (L1/L2/L3)
    - ADL Lite Spec §7.4: Consensus status badges
    - ADL Lite Milestone 2d: L4 action blocks
"""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, PrivateAttr, field_validator


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
    """Concept lifecycle status (emoji badges)."""

    PROVISIONAL = "provisional"  # 🟡
    VALIDATED = "validated"  # 🟢
    DEPRECATED = "deprecated"  # 🔴
    FORKED = "forked"  # 🔵
    ARCHIVED = "archived"  # ⚪


class ADLType(str, Enum):
    """Top-level semantic types for ADL documents."""

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
    """Every event type in ADL Lite. Events ARE the ontology."""

    # Lifecycle events
    REGISTER = "register"
    VALIDATE = "validate"
    DEPRECATE = "deprecate"
    FORK = "fork"
    ARCHIVE = "archive"
    # Assertion events (L3 blocks)
    RELATE = "relate"
    EVIDENCE = "evidence"
    SEAL = "seal"
    # Communication events (L4 actions)
    ANNOUNCE = "announce"
    PUBLISH = "publish"
    SYNC_DASHBOARD = "sync_dashboard"
    LISTEN = "listen"
    # Internal
    SNAPSHOT = "snapshot"  # L1 front matter as a recorded state


# ---------------------------------------------------------------------------
# Event — the fundamental unit (event-first ontology)
# ---------------------------------------------------------------------------


class Event(BaseModel):
    """
    An Event is an atomic occurrence in a concept's life.

    Every event:
    - belongs to exactly one concept (concept_id)
    - links to the previous event (previous_event_id → forms the chain)
    - carries a typed payload (L3 block, L4 action params, etc.)
    - is cryptographically hashed (chain integrity)

    This IS the ontology. Objects don't have events — events ARE the world.
    """

    event_id: str = Field(
        default_factory=lambda: uuid4().hex,
        description="Unique event identifier (full 128-bit UUID)",
    )
    concept_id: str = Field(..., description="adl_id of the concept this event belongs to")
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
    _prev_hash: str = PrivateAttr(default="")

    def model_post_init(self, __context) -> None:
        if not self.hash:
            self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Return a deterministic SHA-256 hash of this event's canonical content.

        Canonicalization rules (platform-independent):
          1. Include: event_id, concept_id, event_type, actor, timestamp,
             payload, previous_event_id, prev_hash.
          2. Exclude: the hash field itself (to avoid circular self-reference).
          3. Recursively sort all object keys.
          4. Recursively round all floating-point values to 6 decimal places.
          5. Encode as UTF-8 JSON.

        The timestamp is intentionally INCLUDED in the hash input so that
        post-hoc timestamp edits are detectable as integrity violations.
        Clock-skew tolerance is handled at the application layer (event
        ordering uses previous_event_id linkage, not timestamp comparison).
        """
        content = {
            "event_id": self.event_id,
            "concept_id": self.concept_id,
            "event_type": self.event_type.value,
            "actor": self.actor,
            "timestamp": self.timestamp,
            "payload": _round_floats(self.payload),
            "previous_event_id": self.previous_event_id,
            "prev_hash": self._prev_hash,
        }
        return hashlib.sha256(
            json.dumps(content, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()


class EventChain:
    """
    An append-only, cryptographically linked chain of events.

    THIS IS THE CONCEPT. The concept does not "have" status or confidence.
    Status and confidence are computed from the chain.

    The chain is the digital twin — not a static model, but the live
    accumulation of all facts about a concept.
    """

    def __init__(
        self,
        concept_id: str,
        events: list[Event] | None = None,
        markdown_body: str = "",
        source_path: str | None = None,
    ) -> None:
        self.concept_id = concept_id
        self._events: list[Event] = []
        self._lock = threading.Lock()
        self.markdown_body = markdown_body
        self.source_path = source_path

        if events:
            for e in events:
                self.append(e)

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def append(self, event: Event) -> None:
        """Append an event, linking to the previous tail. Thread-safe."""
        with self._lock:
            if event.concept_id != self.concept_id:
                raise ValueError(
                    f"Event concept_id {event.concept_id} != chain concept_id {self.concept_id}"
                )
            if self._events:
                event.previous_event_id = self._events[-1].event_id
                event._prev_hash = self._events[-1].hash
                event.hash = ""  # Force re-computation with new chaining
                event.model_post_init(None)
            else:
                # First event in chain: reset to genesis state
                event.previous_event_id = None
                event._prev_hash = ""
                event.hash = ""
                event.model_post_init(None)
            self._events.append(event)

    @property
    def events(self) -> list[Event]:
        with self._lock:
            return list(self._events)

    @property
    def length(self) -> int:
        with self._lock:
            return len(self._events)

    def __len__(self) -> int:
        with self._lock:
            return len(self._events)

    def __iter__(self):
        with self._lock:
            return iter(list(self._events))

    def __getitem__(self, index: int) -> Event:
        with self._lock:
            return self._events[index]

    # ------------------------------------------------------------------
    # Computed properties (derived from events, NOT stored)
    # ------------------------------------------------------------------

    @property
    def status(self) -> DiscoveryStatus:
        """Status computed from the chain — the latest lifecycle event."""
        with self._lock:
            for event in reversed(self._events):
                if event.event_type in (
                    EventType.REGISTER,
                    EventType.VALIDATE,
                    EventType.DEPRECATE,
                    EventType.FORK,
                    EventType.ARCHIVE,
                ):
                    type_to_status = {
                        EventType.REGISTER: DiscoveryStatus.PROVISIONAL,
                        EventType.VALIDATE: DiscoveryStatus.VALIDATED,
                        EventType.DEPRECATE: DiscoveryStatus.DEPRECATED,
                        EventType.FORK: DiscoveryStatus.FORKED,
                        EventType.ARCHIVE: DiscoveryStatus.ARCHIVED,
                    }
                    return type_to_status[event.event_type]
            return DiscoveryStatus.PROVISIONAL

    @property
    def confidence(self) -> float:
        """Confidence derived from validate events or last snapshot."""
        with self._lock:
            for event in reversed(self._events):
                if event.event_type == EventType.VALIDATE:
                    return float(event.payload.get("confidence", 0.0))
                if event.event_type == EventType.SNAPSHOT:
                    return float(event.payload.get("confidence", 0.0))
            return 0.0

    @property
    def validators(self) -> list[str]:
        with self._lock:
            actors = []
            for event in self._events:
                if event.event_type == EventType.VALIDATE:
                    actors.append(event.actor)
            return actors

    @property
    def created_at(self) -> str:
        """Concept creation time = first event timestamp."""
        with self._lock:
            if self._events:
                return self._events[0].timestamp
            return datetime.now(timezone.utc).isoformat()

    @property
    def updated_at(self) -> str:
        """Last modification = last event timestamp."""
        with self._lock:
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

    def verify_integrity(self) -> bool:
        """Verify chain integrity: prev-id linking + cryptographic hash chaining. Thread-safe."""
        with self._lock:
            # Verify id linking
            for i in range(1, len(self._events)):
                if self._events[i].previous_event_id != self._events[i - 1].event_id:
                    return False
            # Verify each event's hash (includes its own content + predecessor's hash)
            for i, event in enumerate(self._events):
                expected_prev = self._events[i - 1].hash if i > 0 else ""
                if event._prev_hash != expected_prev:
                    return False
                if event.hash != event._compute_hash():
                    return False
            return True

    def history(self) -> list[dict[str, Any]]:
        """Full chain history as a list of dicts. Synthetic events flagged. Thread-safe."""
        with self._lock:
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
    L1 Header — derived snapshot of a concept's current state.

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


# ---------------------------------------------------------------------------
# L3: ADL Block Models (embedded ```adl:* code blocks)
# ---------------------------------------------------------------------------


class ADLRelationBlock(BaseModel):
    """
    L3 Relation Block — typed edge between concepts.
    Syntax: ```adl:relation ... ```
    """

    block_type: Literal["relation"] = "relation"
    source: str = Field(..., description="Source concept name or URI")
    relation: str = Field(..., description="Relation predicate, e.g. 'isomorphic-to'")
    target: str = Field(..., description="Target concept URI or name")
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


# Union type for all L3 blocks
ADLBlock = ADLRelationBlock | ADLEvidenceBlock | ADLFormalSealBlock


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
            Comparator.EQ: lambda a, v: a == v,
            Comparator.NEQ: lambda a, v: a != v,
            Comparator.GT: lambda a, v: a > v,
            Comparator.GTE: lambda a, v: a >= v,
            Comparator.LT: lambda a, v: a < v,
            Comparator.LTE: lambda a, v: a <= v,
        }
        return _ops[self.comparator](actual, self.value)


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

    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
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


# Union type for all blocks (L3 + L4)
AllBlocks = ADLRelationBlock | ADLEvidenceBlock | ADLFormalSealBlock | ADLActionBlock


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

    Philosophy: The EventChain IS the concept. FrontMatter is a derived snapshot.
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
        return sk

    def validate_semantics(self) -> list[str]:
        """Run semantic validation and return list of errors."""
        from .validator import ADLValidator

        validator = ADLValidator()
        return validator.validate_document(self)
