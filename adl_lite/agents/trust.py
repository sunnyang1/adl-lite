"""M4: trust closure — B4 validator diversity (did:web org affiliation) +
reputation signals (discovery events v1 + task component v2).

Weak-signal declaration (P1-7): reputation is ONLY for ranking/visibility —
it must never gate security admission. ``min_validator_reputation`` in
``ConsensusConfig`` defaults to 0.0 (disabled).

did:web affiliation is SELF-ATTESTED weak trust (the org claims its own
domain); it only stops *unintentional* same-org concentration, NOT deliberate
collusion — see P1-2 note in the implementation plan.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ..consensus import ConsensusEngine
from ..did_resolver import resolve_did_web
from ..models import EventType
from .identity import AgentRegistry, chain_kind

# ---------------------------------------------------------------------------
# DidWeb affiliation resolver (offline-first, never hard-fails)
# ---------------------------------------------------------------------------


class DidWebAffiliationResolver:
    """Resolve a did:web actor's organisational affiliation.

    Offline cache first (keyed by sha256(did)); a network miss with
    ``offline=True`` falls back to the cached value or None — never raises,
    so tests stay deterministic and the trust layer never hard-fails on a
    flaky network (M4 design rule).
    """

    def __init__(
        self,
        cache_path: str | Path | None = None,
        timeout: int = 10,
        offline: bool = True,
        ttl_days: int = 7,
    ) -> None:
        self._cache_path = Path(cache_path) if cache_path else None
        self._cache: dict[str, dict[str, Any]] = self._load_cache()
        self._offline = offline
        self._timeout = timeout
        self._ttl = timedelta(days=ttl_days)

    # ------------------------------------------------------------------

    def organization_of(self, did: str) -> str | None:
        """Organisation for a did:web actor, or None (offline miss)."""
        if not did.startswith("did:web:"):
            return None
        key = hashlib.sha256(did.encode()).hexdigest()
        hit = self._cache.get(key)
        if hit and datetime.now() - hit["ts"] < self._ttl:
            return hit.get("org")
        try:
            doc = resolve_did_web(did, timeout=self._timeout)
            org = self._extract_org(doc, did)
        except Exception:  # noqa: BLE001 — never hard-fail
            if self._offline:
                return hit.get("org") if hit else None
            raise
        self._cache[key] = {"org": org, "ts": datetime.now().isoformat()}
        self._save_cache()
        return org

    def diversity_key(self, actor: str) -> tuple[str, str]:
        """did:web → ("org", org or actor); anything else → ("key", actor)
        (unchanged Phase-1 behaviour)."""
        if actor.startswith("did:web:"):
            org = self.organization_of(actor)
            return ("org", org or actor)
        return ("key", actor)

    def _extract_org(self, doc: Any, did: str) -> str | None:
        """Priority: explicit organizationId > alsoKnownAs[0] host >
        service[].id host > did:web domain fallback.

        ``resolve_did_web`` returns a normalized ``DIDDocument`` (dataclass
        without org fields), so access goes through a dict/dataclass adapter
        and usually falls back to the did:web domain — sufficient for B4."""
        get = doc.get if isinstance(doc, dict) else (lambda k, d=None: getattr(doc, k, d))
        if get("organizationId"):
            return str(get("organizationId"))
        for aka in get("alsoKnownAs", []) or []:
            if isinstance(aka, str) and "://" in aka:
                return "org:" + aka.split("://")[1].split("/")[0]
        for svc in get("service", []) or []:
            sid = svc.get("id", "") if isinstance(svc, dict) else ""
            if "://" in sid:
                return "org:" + sid.split("://")[1].split("/")[0]
        if did.startswith("did:web:"):
            return "org:" + did.split(":", 3)[-1].split("/")[0]
        return None

    # -- cache persistence ----------------------------------------------

    def _load_cache(self) -> dict[str, dict[str, Any]]:
        if self._cache_path and self._cache_path.exists():
            try:
                raw = json.loads(self._cache_path.read_text(encoding="utf-8"))
                data: dict[str, dict[str, Any]] = dict(raw or {})
                for _k, v in data.items():
                    if isinstance(v.get("ts"), str):
                        v["ts"] = datetime.fromisoformat(v["ts"])
                return data
            except (json.JSONDecodeError, OSError, ValueError):
                return {}
        return {}

    def _save_cache(self) -> None:
        if not self._cache_path:
            return
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                k: {"org": v.get("org"), "ts": v["ts"].isoformat()} for k, v in self._cache.items()
            }
            self._cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:  # pragma: no cover — best effort
            pass


# ---------------------------------------------------------------------------
# Reputation (weak signal)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReputationScore:
    validate_count: int = 0
    submit_count: int = 0
    accepted_count: int = 0
    fork_count: int = 0
    merged_fork_count: int = 0
    deprecate_count: int = 0
    task_success_rate: float = 0.0
    fork_merge_rate: float = 0.0
    deprecation_rate: float = 0.0


class Reputation:
    """Read-only derivation of an agent's behavioural stats over the chain
    set. Weights are configurable policy guesses (P1-7) — to be validated
    against real data before any production use.

    M4v1: discovery-event component only. M4v2: task component, counted at
    TASK level (per-task dedup — a rework loop's repeated submits must not
    dilute ``task_success_rate``).
    """

    def __init__(
        self,
        engine: ConsensusEngine,
        registry: AgentRegistry,
        weights: dict[str, float] | None = None,
    ) -> None:
        self.engine = engine
        self.registry = registry
        self._weights = weights or {
            "w_validate": 0.05,
            "w_task": 0.20,
            "w_fork_merge": 0.10,
            "w_deprecate": -0.20,
        }

    # ------------------------------------------------------------------

    def score(self, agent_did: str) -> ReputationScore:
        s = ReputationScore()
        for chain in self.engine.chains.values():
            if chain_kind(chain) == "agent":
                continue  # agent chains are identities, not behaviour
            for e in chain.events:
                if e.actor != agent_did:
                    continue
                if e.event_type == EventType.VALIDATE:
                    s = replace(s, validate_count=s.validate_count + 1)
                elif e.event_type == EventType.FORK:
                    s = replace(s, fork_count=s.fork_count + 1)
                elif e.event_type == EventType.DEPRECATE:
                    s = replace(s, deprecate_count=s.deprecate_count + 1)
        # M4v2: task component (per-task dedup).
        s = replace(
            s,
            submit_count=len(self._submitted_tasks(agent_did)),
            accepted_count=len(self._accepted_tasks(agent_did)),
        )
        s = replace(
            s,
            merged_fork_count=self._count_merged_forks(agent_did),
            task_success_rate=s.accepted_count / max(1, s.submit_count),
            fork_merge_rate=s.merged_fork_count / max(1, s.fork_count),
            deprecation_rate=s.deprecate_count / max(1, s.validate_count + s.deprecate_count),
        )
        return s

    # ------------------------------------------------------------------

    def formula_v1(self, s: ReputationScore) -> float:
        w = self._weights
        return _clamp01(
            0.5
            + w["w_validate"] * min(s.validate_count, 10)
            + w["w_fork_merge"] * s.fork_merge_rate
            + w["w_deprecate"] * s.deprecation_rate
        )

    def formula_v2(self, s: ReputationScore) -> float:
        w = self._weights
        return _clamp01(
            0.5
            + w["w_validate"] * min(s.validate_count, 10)
            + w["w_task"] * s.task_success_rate
            + w["w_fork_merge"] * s.fork_merge_rate
            + w["w_deprecate"] * s.deprecation_rate
        )

    # -- helpers ---------------------------------------------------------

    def _submitted_tasks(self, agent_did: str) -> set[str]:
        """Task-level dedup: one entry per task the agent submitted."""
        out: set[str] = set()
        for cid, chain in self.engine.chains.items():
            if chain_kind(chain) != "task":
                continue
            if any(
                e.event_type == EventType.TASK_SUBMIT and e.actor == agent_did for e in chain.events
            ):
                out.add(cid)
        return out

    def _accepted_tasks(self, agent_did: str) -> set[str]:
        out: set[str] = set()
        for cid, chain in self.engine.chains.items():
            if chain_kind(chain) != "task":
                continue
            submitters = [e.actor for e in chain.events if e.event_type == EventType.TASK_SUBMIT]
            if not submitters or submitters[-1] != agent_did:
                continue
            if any(
                e.event_type == EventType.TASK_CLOSE and e.payload.get("outcome") == "accepted"
                for e in chain.events
            ):
                out.add(cid)
        return out

    def _count_merged_forks(self, agent_did: str) -> int:
        """Weak approximation: a fork counts as "resolved/merged" when the
        agent initiated it AND the fork_id chain exists with intact integrity.
        The engine does not persist a MERGED resolution on the chain, so this
        is deliberately a conservative proxy (P1-7 weak signal)."""
        count = 0
        for _cid, chain in self.engine.chains.items():
            if chain_kind(chain) != "discovery":
                continue
            for e in chain.events:
                if e.event_type == EventType.FORK and e.actor == agent_did:
                    fork_id = e.payload.get("fork_id") or e.payload.get("target_concept_id")
                    fchain = self.engine.chains.get(fork_id or "")
                    if fchain is not None and fchain.verify_integrity():
                        count += 1
        return count


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))
