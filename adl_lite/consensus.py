"""
ADL Lite — Concept Consensus Chain & Fork Management

Manages the lifecycle of concepts:
    provisional → validated → deprecated (or archived)
                    ↓
                  forked ──→ merged / parallel / pruned

Deeply isomorphic to blockchain:
    Transaction  → Discovery
    Block        → Concept Bundle
    PoW/PoS      → Structural Arbitration
    Prev Hash    → Concept Lineage
    Fork         → Concept Fork

References:
    - ADL Lite Spec §6.3: Concept Consensus Chain
    - ADL Lite Spec §6.4: Fork management (merge/parallel/prune)
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum

from .models import ADLDocument, DiscoveryStatus
from .ontology import OntologyManager, default_ontology

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ForkResolution(str, Enum):
    """Outcome of a fork convergence attempt."""
    MERGED = "merged"       # Relation graphs >90% isomorphic
    PARALLEL = "parallel"   # Different domains need different metaphors
    PRUNED = "pruned"       # Long-term unreferenced → archived


# ---------------------------------------------------------------------------
# Consensus Entry (a single "block" in the chain)
# ---------------------------------------------------------------------------

class ConsensusEntry:
    """
    One entry in the Concept Consensus Chain.
    Analogous to a blockchain transaction.
    """

    def __init__(
        self,
        adl_id: str,
        from_status: DiscoveryStatus,
        to_status: DiscoveryStatus,
        actor: str,           # who triggered the transition
        reason: str = "",
        parent_hash: str = "0" * 64,
    ) -> None:
        self.adl_id = adl_id
        self.from_status = from_status
        self.to_status = to_status
        self.actor = actor
        self.reason = reason
        self.parent_hash = parent_hash
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self._hash = self._compute_hash()

    def _compute_hash(self) -> str:
        payload = {
            "adl_id": self.adl_id,
            "from": self.from_status.value,
            "to": self.to_status.value,
            "actor": self.actor,
            "reason": self.reason,
            "parent": self.parent_hash,
            "time": self.timestamp,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    @property
    def hash(self) -> str:
        return self._hash

    def to_dict(self) -> dict:
        return {
            "adl_id": self.adl_id,
            "from_status": self.from_status.value,
            "to_status": self.to_status.value,
            "actor": self.actor,
            "reason": self.reason,
            "parent_hash": self.parent_hash,
            "hash": self.hash,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Concept Chain (per-concept blockchain)
# ---------------------------------------------------------------------------

class ConceptChain:
    """
    A linked chain of consensus entries for a single concept.
    Immutable append-only log.
    """

    def __init__(self, adl_id: str) -> None:
        self.adl_id = adl_id
        self.entries: list[ConsensusEntry] = []

    def append(self, entry: ConsensusEntry) -> None:
        """Append a new entry, linking its parent hash to the previous tail."""
        if self.entries:
            entry.parent_hash = self.entries[-1].hash
        self.entries.append(entry)

    @property
    def latest_status(self) -> DiscoveryStatus:
        if not self.entries:
            return DiscoveryStatus.PROVISIONAL
        return self.entries[-1].to_status

    @property
    def latest_hash(self) -> str:
        if not self.entries:
            return "0" * 64
        return self.entries[-1].hash

    def history(self) -> list[dict]:
        return [e.to_dict() for e in self.entries]

    def verify_integrity(self) -> bool:
        """Verify chain integrity (parent hashes link correctly)."""
        for i in range(1, len(self.entries)):
            if self.entries[i].parent_hash != self.entries[i - 1].hash:
                return False
        return True


# ---------------------------------------------------------------------------
# Fork Manager
# ---------------------------------------------------------------------------

class ForkManager:
    """
    Manages concept forks: divergence of interpretations for the same phenomenon.

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
        # concept_id → list of forked concept_ids
        self.forks: dict[str, list[str]] = {}
        # concept_id → creation timestamp
        self.creation_times: dict[str, str] = {}

    def register_fork(
        self,
        original_id: str,
        fork_id: str,
        reason: str = "",
    ) -> None:
        """Register a new fork from an original concept."""
        if original_id not in self.forks:
            self.forks[original_id] = []
        self.forks[original_id].append(fork_id)
        self.creation_times[fork_id] = datetime.now(timezone.utc).isoformat()

    def attempt_merge(self, concept_a: str, concept_b: str, similarity: float) -> ForkResolution:
        """
        Attempt to merge two forked concepts.

        Args:
            concept_a: first concept ID
            concept_b: second concept ID
            similarity: structural similarity score [0, 1]

        Returns:
            ForkResolution outcome
        """
        if similarity >= self.ISOMORPHISM_THRESHOLD:
            return ForkResolution.MERGED
        return ForkResolution.PARALLEL

    def should_prune(self, concept_id: str, last_accessed: str | None = None) -> bool:
        """
        Check if a concept should be pruned (archived).

        Args:
            concept_id: concept to check
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
        """Return the fork tree rooted at concept_id."""
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
    Central engine managing consensus chains for all concepts.

    Usage:
        engine = ConsensusEngine()
        engine.transition("disc-7f3a9b", DiscoveryStatus.VALIDATED, actor="agent_1")
        history = engine.get_history("disc-7f3a9b")
    """

    def __init__(self, ontology: OntologyManager | None = None) -> None:
        self.chains: dict[str, ConceptChain] = {}
        self.fork_manager = ForkManager()
        self._ontology = ontology or default_ontology()

    # -- Chain lifecycle --

    def register(self, doc: ADLDocument) -> ConceptChain:
        """Register a new concept document, starting its chain."""
        cid = doc.adl_id
        if cid not in self.chains:
            self.chains[cid] = ConceptChain(cid)
            entry = ConsensusEntry(
                adl_id=cid,
                from_status=DiscoveryStatus.PROVISIONAL,
                to_status=DiscoveryStatus.PROVISIONAL,
                actor="system",
                reason="Document registered",
            )
            self.chains[cid].append(entry)
        return self.chains[cid]

    def transition(
        self,
        adl_id: str,
        to_status: DiscoveryStatus,
        actor: str,
        reason: str = "",
    ) -> ConsensusEntry | None:
        """
        Transition a concept to a new status.
        Validates the transition is legal.
        """
        if adl_id not in self.chains:
            raise KeyError(f"Concept '{adl_id}' not registered")

        chain = self.chains[adl_id]
        current = chain.latest_status

        if not self._is_valid_transition(current, to_status, self._ontology):
            raise ValueError(
                f"Invalid transition: {current.value} → {to_status.value}"
            )

        entry = ConsensusEntry(
            adl_id=adl_id,
            from_status=current,
            to_status=to_status,
            actor=actor,
            reason=reason,
            parent_hash=chain.latest_hash,
        )
        chain.append(entry)
        return entry

    def fork(
        self,
        original_id: str,
        fork_id: str,
        actor: str,
        reason: str = "",
    ) -> ConceptChain:
        """Create a fork of an existing concept."""
        if original_id not in self.chains:
            raise KeyError(f"Original concept '{original_id}' not found")

        # Mark original as forked
        self.transition(original_id, DiscoveryStatus.FORKED, actor, reason)

        # Create new chain for fork
        self.chains[fork_id] = ConceptChain(fork_id)
        entry = ConsensusEntry(
            adl_id=fork_id,
            from_status=DiscoveryStatus.PROVISIONAL,
            to_status=DiscoveryStatus.PROVISIONAL,
            actor=actor,
            reason=f"Forked from {original_id}: {reason}",
        )
        self.chains[fork_id].append(entry)

        self.fork_manager.register_fork(original_id, fork_id, reason)
        return self.chains[fork_id]

    # -- Queries --

    def get_history(self, adl_id: str) -> list[dict]:
        if adl_id not in self.chains:
            return []
        return self.chains[adl_id].history()

    def get_status(self, adl_id: str) -> DiscoveryStatus:
        if adl_id not in self.chains:
            return DiscoveryStatus.PROVISIONAL
        return self.chains[adl_id].latest_status

    def verify_all(self) -> dict[str, bool]:
        """Verify integrity of all chains."""
        return {cid: chain.verify_integrity() for cid, chain in self.chains.items()}

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
