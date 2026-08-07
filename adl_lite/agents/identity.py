"""Agent identity registry: agents as cryptographically-signed EventChains.

M1a of the native multi-agent plan. Agents are first-class EventChains whose
genesis event is AGENT_REGISTER (actor = the agent's own DID). Status, profile
and validator sets are DERIVED from the chain — never stored as mutable fields.

Design invariants (see plans/toasty-vortex-babbage-impl.md §1.4):
- AGENT_* events are deliberately absent from the discovery lattice
  (type_to_status / StatusOrder): agent chains never drive DiscoveryStatus.
- Private keys are held by the caller (P2-10); the registry only accepts
  public keys / base64 signatures.
- Admin attestation (P0-1/P0-3) requires a verifiable DID signature from a
  REGISTERED admin public key AND the internal ``_admin_calls_allowed`` guard,
  which only the admin-gated API layer may enable.
"""

from __future__ import annotations

import base64
from enum import Enum
from typing import Any

from cryptography.hazmat.primitives.asymmetric import ed25519
from pydantic import BaseModel, Field

from ..consensus import ConsensusEngine
from ..did_resolver import create_did_key, verify_did_signature
from ..exceptions import ADLConsensusError
from ..models import Event, EventChain, EventType


class AgentRole(str, Enum):
    """Role taxonomy for registered agents (mirrors experiments/harness.py)."""

    DISCOVERER = "discoverer"
    REVIEWER = "reviewer"
    SKEPTIC = "skeptic"
    MERGER = "merger"
    LIBRARIAN = "librarian"
    PLANNER = "planner"


class AgentStatus(str, Enum):
    """Agent lifecycle status derived from the agent chain."""

    PENDING = "pending"  # registered, not yet validated
    ACTIVE = "active"  # validator_count >= n_min (or admin-attested)
    DEPRECATED = "deprecated"


class AgentProfile(BaseModel):
    """Identity document for an agent. Stored in the genesis event payload."""

    did: str
    role: AgentRole
    name: str
    model: str = ""
    capabilities: list[str] = Field(default_factory=list)
    mcp_endpoint: str | None = None
    scope: str = "public"  # reuses ADLFrontMatter scope taxonomy
    tenant: str | None = None
    org_id: str | None = None  # M4 uses; M1 never treats self-declared org as trust


def chain_kind(chain: EventChain) -> str:
    """Derive the chain type marker from the genesis event_type (P0-2).

    Returns "agent", "task" (M2+), "discovery", or "unknown". Discovery
    endpoints must filter on this marker so agent/task chains never surface
    as provisional concepts.
    """
    if not chain.events:
        return "unknown"
    et = chain.events[0].event_type
    if et == EventType.AGENT_REGISTER:
        return "agent"
    # TASK_CREATE lands in M2; guard with getattr so M1a stays import-safe.
    if et == getattr(EventType, "TASK_CREATE", None):
        return "task"
    return "discovery"


class AgentRegistry:
    """Agent identity lifecycle over a ConsensusEngine.

    Agents are stored as EventChains inside ``engine.chains`` keyed by DID.
    Chain integrity is covered by ``EventChain.verify_integrity()``; the
    discovery lattice is untouched (see invariants above).
    """

    def __init__(
        self,
        engine: ConsensusEngine | None = None,
        admin_public_keys: dict[str, str] | None = None,
        admin_calls_allowed: bool = False,
    ) -> None:
        self.engine = engine or ConsensusEngine(dev_mode=True)
        # P0-3: admin DID -> public key (base64). Registered via the admin API
        # layer; the registry never accepts arbitrary admin identities.
        self.admin_public_keys: dict[str, str] = dict(admin_public_keys or {})
        # P0-3: internal guard — only the admin-gated API may flip this on.
        self._admin_calls_allowed = admin_calls_allowed

    # ------------------------------------------------------------------
    # N_min / validator derivation (mirrors ConsensusEngine._effective_n_min)
    # ------------------------------------------------------------------

    def _effective_n_min(self) -> int:
        """dev mode -> 1; production -> max(ontology_min, 2)."""
        if self.engine.dev_mode:
            return 1
        return max(int(self.engine._ontology.min_distinct_validators()), 2)

    def _agent_validators(self, chain: EventChain) -> list[str]:
        """Distinct AGENT_VALIDATE actors.

        ``EventChain.validators`` only tracks discovery VALIDATE events, so the
        agent validator set is derived here without touching models.py.
        """
        seen: list[str] = []
        for e in chain.events:
            if e.event_type == EventType.AGENT_VALIDATE and e.actor not in seen:
                seen.append(e.actor)
        return seen

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def register_agent(
        self,
        profile: AgentProfile,
        public_key: Any | None = None,
        genesis_signature: str = "",
        genesis_proof: dict | None = None,
    ) -> EventChain:
        """Register an agent identity.

        The private key stays with the caller (P2-10); the registry only
        receives the public key and an optional base64 genesis signature.
        ``public_key`` may be an Ed25519 public-key object or a base64 string
        (API/MCP surfaces pass base64).
        """
        if isinstance(public_key, str):
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key))
        did = profile.did
        if not did:
            if public_key is None:
                raise ValueError("register_agent requires did or public_key")
            did = create_did_key(public_key)
            profile.did = did
        # Sybil defense (P0-3, key dimension): same DID cannot re-register.
        if did in self.engine.chains:
            raise ADLConsensusError(f"agent already registered: {did}")
        genesis = Event(
            concept_id=did,
            event_type=EventType.AGENT_REGISTER,
            actor=did,  # identity self-attestation
            payload={
                "profile": profile.model_dump(),
                # Top-level scope so _chain_scope() (api.py/mcp_server.py) can
                # enforce the scope ACL on agent chains (P0-2).
                "scope": profile.scope,
            },
        )
        if genesis_signature:
            genesis.signature = genesis_signature
        if genesis_proof:
            genesis.proof = genesis_proof
        chain = EventChain(concept_id=did)
        chain.append(genesis)
        self.engine.chains[did] = chain
        return chain

    def validate_agent(
        self,
        agent_did: str,
        validator_actor: str,
        reason: str = "",
        confidence: float = 0.9,
        signature: str = "",
        admin: bool = False,
    ) -> Event:
        """Validate an agent identity.

        - ``admin=True`` is the trust-root bootstrap path (P0-1): requires a
          verifiable DID signature from a REGISTERED admin public key and the
          internal admin guard; N_min is skipped (external root of trust).
        - Regular path: no self-validation, validator must be a registered
          ACTIVE agent, and N_min distinct validators must be met.
        """
        if agent_did not in self.engine.chains:
            raise ADLConsensusError(f"unknown agent: {agent_did}")
        chain = self.engine.chains[agent_did]

        if admin:
            # P0-1/P0-3: admin attestation must verify against a registered
            # admin public key; magic strings like "admin" are rejected by
            # construction (actor must be a DID with a known key).
            if not self._admin_calls_allowed:
                raise ADLConsensusError("admin attestation is only allowed via the admin-gated API")
            if not signature:
                raise ADLConsensusError("admin attestation requires a signature")
            if not self._verify_admin_signature(chain, validator_actor, signature):
                raise ADLConsensusError("admin signature verification failed")
            actor = validator_actor
        else:
            if validator_actor == agent_did:
                raise ADLConsensusError("self-validation is forbidden (B3 analog)")
            if (
                validator_actor not in self.engine.chains
                or self.agent_status(validator_actor) != AgentStatus.ACTIVE
            ):
                raise ADLConsensusError("validator must be a registered ACTIVE agent")
            n_min = self._effective_n_min()
            existing = self._agent_validators(chain)
            prospective = len(existing) + (0 if validator_actor in existing else 1)
            if prospective < n_min:
                raise ADLConsensusError(
                    f"AGENT_VALIDATE requires at least {n_min} distinct validators, "
                    f"got {len(existing)} existing + prospective={prospective}"
                )
            actor = validator_actor

        event = Event(
            concept_id=agent_did,
            event_type=EventType.AGENT_VALIDATE,
            actor=actor,
            reasoning=reason,
            payload={"confidence": confidence, "admin": admin},
        )
        if signature:
            event.signature = signature
        chain.append(event)
        return event

    def update_agent(self, agent_did: str, actor: str, **fields: Any) -> Event:
        """Mutate a profile (capabilities/model/scope etc.). Owner or admin only."""
        self._assert_actor_can_write(agent_did, actor)
        event = Event(
            concept_id=agent_did,
            event_type=EventType.AGENT_UPDATE,
            actor=actor,
            payload={"fields": fields},
        )
        self.engine.chains[agent_did].append(event)
        return event

    def deprecate_agent(self, agent_did: str, actor: str, reason: str) -> Event:
        """Decommission an agent. Owner or admin only."""
        self._assert_actor_can_write(agent_did, actor)
        event = Event(
            concept_id=agent_did,
            event_type=EventType.AGENT_DEPRECATE,
            actor=actor,
            reasoning=reason,
        )
        self.engine.chains[agent_did].append(event)
        return event

    # ------------------------------------------------------------------
    # Derived queries (profile/status from chain, never stored fields)
    # ------------------------------------------------------------------

    def resolve_profile(self, chain: EventChain) -> AgentProfile:
        genesis = chain.events[0]
        return AgentProfile(**genesis.payload["profile"])

    def get_agent(self, agent_did: str) -> AgentProfile | None:
        chain = self.engine.chains.get(agent_did)
        if chain is None or chain_kind(chain) != "agent":
            return None
        return self.resolve_profile(chain)

    def list_agents(self, scope: str | None = None) -> list[AgentProfile]:
        out: list[AgentProfile] = []
        for _cid, chain in self.engine.chains.items():
            if chain_kind(chain) != "agent":
                continue
            p = self.resolve_profile(chain)
            if scope and p.scope != scope:
                continue
            out.append(p)
        return sorted(out, key=lambda p: p.did)

    def agent_status(self, agent_did: str) -> AgentStatus:
        chain = self.engine.chains.get(agent_did)
        if chain is None:
            return AgentStatus.PENDING
        if any(e.event_type == EventType.AGENT_DEPRECATE for e in chain.events):
            return AgentStatus.DEPRECATED
        # Admin attestation is an external root of trust: it satisfies N_min
        # regardless of the production threshold (P0-1 bootstrap path).
        if any(
            e.event_type == EventType.AGENT_VALIDATE and e.payload.get("admin")
            for e in chain.events
        ):
            return AgentStatus.ACTIVE
        validators = self._agent_validators(chain)
        return (
            AgentStatus.ACTIVE
            if len(validators) >= self._effective_n_min()
            else AgentStatus.PENDING
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _verify_admin_signature(self, chain: EventChain, admin_did: str, signature: str) -> bool:
        """P0-3: verify against the REGISTERED admin public key whitelist.

        Uses the same scheme as trust_model B2 (message = event hash utf-8,
        signature = base64). did:key self-resolves its public key; did:web
        goes through the resolver (offline-safe for tests via did:key).
        """
        if admin_did not in self.admin_public_keys:
            return False  # admin DID has no registered key -> reject
        try:
            sig_bytes = base64.b64decode(signature)
        except Exception:
            return False
        return bool(
            verify_did_signature(admin_did, chain.events[-1].hash.encode("utf-8"), sig_bytes)
        )

    def _assert_actor_can_write(self, agent_did: str, actor: str) -> None:
        """Write policy: the owning agent, or a registered admin DID."""
        if actor != agent_did and actor not in self.admin_public_keys:
            raise ADLConsensusError(
                "only the owning agent (or a registered admin) may write to an agent chain"
            )
