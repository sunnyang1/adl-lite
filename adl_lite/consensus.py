"""
ADL Lite — Capability Lifecycle Consensus Chain & Fork Management

Manages the lifecycle of capabilities:
    provisional → validated → deprecated (or archived)
                    ↓
                  forked ──→ merged / parallel / pruned

Philosophy (event-first):
    ConsensusEngine is a thin wrapper over EventChain.
    All lifecycle state is derived from the chain — not stored.
    ConceptChain and ConsensusEntry are removed in v0.3.

References:
    - ADL Lite Spec §6.3: Capability Lifecycle Consensus Chain
    - ADL Lite Spec §6.4: Fork management (merge/parallel/prune)
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from enum import Enum

from .exceptions import ADLConsensusError
from .models import ADLDocument, DiscoveryStatus, Event, EventChain, EventType
from .ontology import OntologyManager, default_ontology

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ForkResolution(str, Enum):
    """Outcome of a fork convergence attempt."""

    MERGED = "merged"  # Relation graphs >90% isomorphic
    PARALLEL = "parallel"  # Different domains need different metaphors
    PRUNED = "pruned"  # Long-term unreferenced → archived


# ---------------------------------------------------------------------------
# Backward-compat: ConsensusEntry as a dict factory (no longer a class)
# ---------------------------------------------------------------------------


def _status_to_event_type(status: DiscoveryStatus) -> EventType:
    """Map DiscoveryStatus to the corresponding lifecycle EventType."""
    _map = {
        DiscoveryStatus.PROVISIONAL: EventType.REGISTER,
        DiscoveryStatus.VALIDATED: EventType.VALIDATE,
        DiscoveryStatus.DEPRECATED: EventType.DEPRECATE,
        DiscoveryStatus.FORKED: EventType.FORK,
        DiscoveryStatus.ARCHIVED: EventType.ARCHIVE,
    }
    return _map[status]


# ---------------------------------------------------------------------------
# Fork Manager
# ---------------------------------------------------------------------------


class ForkManager:
    """
    Manages capability forks: divergence of interpretations for the same phenomenon.

    Strategies:
        MERGE   : relation graphs >90% isomorphic
        PARALLEL: different domains need different metaphors
        PRUNE   : long-term unreferenced → archived
    """

    # Thresholds
    ISOMORPHISM_THRESHOLD = 0.90
    PRUNE_AGE_DAYS = 180
    PRUNE_MIN_ENTRIES = 3

    def __init__(self) -> None:
        # capability_id → list of forked capability_ids
        self.forks: dict[str, list[str]] = {}
        # capability_id → creation timestamp
        self.creation_times: dict[str, str] = {}

    def register_fork(
        self,
        original_id: str,
        fork_id: str,
        reason: str = "",
    ) -> None:
        """Register a new fork from an original capability."""
        if original_id not in self.forks:
            self.forks[original_id] = []
        self.forks[original_id].append(fork_id)
        self.creation_times[fork_id] = datetime.now(timezone.utc).isoformat()

    def attempt_merge(self, concept_a: str, concept_b: str, similarity: float) -> ForkResolution:
        """
        Attempt to merge two forked capabilities.

        Args:
            concept_a: first capability ID
            concept_b: second capability ID
            similarity: structural similarity score [0, 1]

        Returns:
            ForkResolution outcome
        """
        if similarity >= self.ISOMORPHISM_THRESHOLD:
            return ForkResolution.MERGED
        return ForkResolution.PARALLEL

    def should_prune(self, concept_id: str, last_accessed: str | None = None) -> bool:
        """
        Check if a capability should be pruned (archived).

        Args:
            concept_id: capability to check
            last_accessed: ISO timestamp of last access
        """
        if concept_id not in self.creation_times:
            return False

        if last_accessed is None:
            return False

        created = datetime.fromisoformat(self.creation_times[concept_id].replace("Z", "+00:00"))
        accessed = datetime.fromisoformat(last_accessed.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)

        age_days = (now - created).days
        idle_days = (now - accessed).days

        return age_days > self.PRUNE_MIN_ENTRIES and idle_days > self.PRUNE_AGE_DAYS

    def get_fork_tree(self, concept_id: str) -> dict:
        """Return the fork tree rooted at the given capability."""
        return {
            "root": concept_id,
            "forks": self.forks.get(concept_id, []),
            "count": len(self.forks.get(concept_id, [])),
        }


# ---------------------------------------------------------------------------
# Global Consensus Engine
# ---------------------------------------------------------------------------


class ConsensusEngine:
    """
    Central engine managing consensus chains for all capabilities.

    v0.3: Now uses EventChain as the sole chain representation.
    Status is computed from the chain, not stored.

    Usage:
        engine = ConsensusEngine()
        engine.register(doc)  # uses doc.event_chain
        engine.transition("disc-7f3a9b", DiscoveryStatus.VALIDATED, actor="agent_1")
        history = engine.get_history("disc-7f3a9b")
    """

    def __init__(self, ontology: OntologyManager | None = None, dev_mode: bool = True) -> None:
        self.chains: dict[str, EventChain] = {}
        self._lock = threading.RLock()
        self.fork_manager = ForkManager()
        self._ontology = ontology or default_ontology()
        self._dev_mode = dev_mode

    # -- Chain lifecycle --

    def register(self, doc: ADLDocument) -> EventChain:
        """Register a new capability document, starting its EventChain. Thread-safe."""
        cid = doc.adl_id
        with self._lock:
            if cid not in self.chains:
                chain = doc.event_chain
                # Ensure at least a genesis REGISTER event
                if chain.length == 0:
                    chain.append(
                        Event(
                            concept_id=cid,
                            event_type=EventType.REGISTER,
                            actor="system",
                            reasoning="Document registered",
                        )
                    )
                self.chains[cid] = chain
            return self.chains[cid]

    def transition(
        self,
        adl_id: str,
        to_status: DiscoveryStatus,
        actor: str,
        reason: str = "",
        payload: dict | None = None,
    ) -> Event | None:
        """
        Transition a capability to a new status by appending a lifecycle Event.
        Thread-safe.
        """
        with self._lock:
            if adl_id not in self.chains:
                raise ADLConsensusError(f"Capability '{adl_id}' not registered")

            chain = self.chains[adl_id]
            current = chain.status  # computed from chain

            if not self._is_valid_transition(current, to_status, self._ontology):
                raise ADLConsensusError(f"Invalid transition: {current.value} → {to_status.value}")

            # Enforce dynamic minimum distinct validators for VALIDATE transitions
            # BEFORE appending the event — prevents chain mutation when the guard fails.
            # The prospective validator (current actor) is counted since they will be a
            # distinct validator once the event is appended, so we check:
            #   existing_validators + (1 if actor is new) >= n_min
            if to_status == DiscoveryStatus.VALIDATED:
                n_min = self._effective_n_min()
                existing = chain.validators  # distinct VALIDATE actors already in chain
                prospective = len(existing) + (0 if actor in existing else 1)
                if prospective < n_min:
                    raise ADLConsensusError(
                        f"VALIDATE transition requires at least {n_min} distinct validators, "
                        f"but only {len(existing)} existing + prospective={prospective} present"
                    )

            event_type = _status_to_event_type(to_status)
            event = Event(
                concept_id=adl_id,
                event_type=event_type,
                actor=actor,
                reasoning=reason,
                payload=payload or {},
            )
            chain.append(event)

            return event

    def fork(
        self,
        original_id: str,
        fork_id: str,
        actor: str,
        reason: str = "",
    ) -> EventChain:
        """Create a fork of an existing capability. Idempotent: skips transition if already forked."""
        if original_id not in self.chains:
            raise KeyError(f"Original capability '{original_id}' not found")

        with self._lock:
            # Only transition if not already forked
            current_status = self.chains[original_id].status
            if current_status != DiscoveryStatus.FORKED:
                self.transition(original_id, DiscoveryStatus.FORKED, actor, reason)

            # Create new chain for fork
            new_chain = EventChain(concept_id=fork_id)
            new_chain.append(
                Event(
                    concept_id=fork_id,
                    event_type=EventType.REGISTER,
                    actor=actor,
                    reasoning=f"Forked from {original_id}: {reason}",
                )
            )
            self.chains[fork_id] = new_chain
            self.fork_manager.register_fork(original_id, fork_id, reason)
            return new_chain

    # -- Queries --

    def get_history(self, adl_id: str) -> list[dict]:
        """Get full chain history. Thread-safe."""
        with self._lock:
            if adl_id not in self.chains:
                return []
            return self.chains[adl_id].history()

    def get_status(self, adl_id: str) -> DiscoveryStatus:
        """Get current capability status. Thread-safe."""
        with self._lock:
            if adl_id not in self.chains:
                return DiscoveryStatus.PROVISIONAL
            return self.chains[adl_id].status  # computed from chain

    def verify_all(self) -> dict[str, bool]:
        """Verify integrity of all chains. Thread-safe."""
        with self._lock:
            return {cid: chain.verify_integrity() for cid, chain in self.chains.items()}

    # -- Dynamic N_min threshold --

    def _effective_n_min(self) -> int:
        """Compute effective N_min: dev_mode allows 1, production requires >= 2.

        In dev_mode (dev_mode=True), N_min is relaxed to 1 to enable
        single-agent development and testing workflows. In production
        (dev_mode=False), the minimum is enforced as max(ontology_value, 2)
        to ensure collusion resistance with at least two distinct validators.
        """
        ontology_min = self._ontology.min_distinct_validators()
        if self._dev_mode:
            return 1
        return max(ontology_min, 2)

    def set_production_mode(self) -> None:
        """Switch to production mode: N_min >= 2 (collusion-safe)."""
        self._dev_mode = False

    def set_dev_mode(self) -> None:
        """Switch to development mode: N_min = 1 (single-validator allowed)."""
        self._dev_mode = True

    @property
    def dev_mode(self) -> bool:
        """Whether the engine is in development mode."""
        return self._dev_mode

    # -- Internal --

    @staticmethod
    def _is_valid_transition(
        current: DiscoveryStatus,
        target: DiscoveryStatus,
        ontology: OntologyManager | None = None,
    ) -> bool:
        """Valid state transitions from adl_core_ontology.yaml."""
        mgr = ontology or default_ontology()
        return mgr.is_valid_transition(current.value, target.value)
