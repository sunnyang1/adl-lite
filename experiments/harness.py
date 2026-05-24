"""Scripted 5-agent simulation harness (no API key required).

Roles: discoverer, reviewer, skeptic, merger, librarian

Set ``strict_ontology=True`` (or env ``ADL_STRICT_ONTOLOGY=1``) to reject unknown
L3 relation predicates during reviewer validation — logs failures for ablation.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from adl_lite import ConsensusEngine, DiscoveryStatus, parse_file
from adl_lite.consensus import ForkResolution
from adl_lite.memory import ADLMemory
from adl_lite.validator import ADLValidator

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = Path(__file__).resolve().parent / "logs"
EXAMPLES = ROOT / "examples"


@dataclass
class SimEvent:
    step: int
    role: str
    action: str
    adl_id: str
    detail: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "step": self.step,
            "role": self.role,
            "action": self.action,
            "adl_id": self.adl_id,
            **self.detail,
        }
        return json.dumps(payload, sort_keys=True)


class ScriptedHarness:
    """Deterministic multi-agent workflow over example ADL documents."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        strict_ontology: bool | None = None,
    ) -> None:
        if strict_ontology is None:
            strict_ontology = os.environ.get("ADL_STRICT_ONTOLOGY", "").lower() in (
                "1",
                "true",
                "yes",
            )
        self.strict_ontology = strict_ontology
        self.engine = ConsensusEngine()
        self.validator = ADLValidator(strict=strict_ontology)
        self.mem = ADLMemory(db_path=str(db_path or ":memory:"))
        self.events: list[SimEvent] = []
        self._step = 0

    def _log(self, role: str, action: str, adl_id: str, **detail: Any) -> None:
        self._step += 1
        self.events.append(SimEvent(self._step, role, action, adl_id, detail))

    def discoverer_emit(self, path: Path) -> str:
        doc = parse_file(path)
        self._log("discoverer", "emit", doc.adl_id, path=str(path), status=doc.status.value)
        return doc.adl_id

    def reviewer_validate_and_transition(self, path: Path) -> bool:
        doc = parse_file(path)
        errors = self.validator.validate_document(doc)
        ok = len(errors) == 0
        ontology_errors = [e for e in errors if "Unknown relation predicate" in e]
        detail: dict[str, object] = {
            "ok": ok,
            "error_count": len(errors),
            "strict_ontology": self.strict_ontology,
        }
        if ontology_errors:
            detail["ontology_errors"] = ontology_errors
        if errors and not ok:
            detail["errors"] = errors[:5]
        self._log("reviewer", "validate", doc.adl_id, **detail)
        if not ok:
            return False
        self.engine.register(doc)
        if doc.status == DiscoveryStatus.PROVISIONAL:
            self.engine.transition(
                doc.adl_id,
                DiscoveryStatus.VALIDATED,
                actor="reviewer",
                reason="Scripted validation pass",
            )
            self._log("reviewer", "transition", doc.adl_id, to="validated")
        return True

    def skeptic_fork(self, original_path: Path, fork_id: str, fork_path: Path) -> None:
        original = parse_file(original_path)
        if original.adl_id not in self.engine.chains:
            self.engine.register(original)
        self.engine.fork(
            original.adl_id,
            fork_id,
            actor="skeptic",
            reason="Scripted alternate hypothesis",
        )
        fork_doc = parse_file(fork_path)
        self._log(
            "skeptic",
            "fork",
            fork_id,
            original=original.adl_id,
            fork_status=fork_doc.status.value,
        )

    def merger_resolve(
        self,
        original_id: str,
        fork_id: str,
        similarity: float,
    ) -> str:
        resolution = self.engine.fork_manager.attempt_merge(
            original_id, fork_id, similarity=similarity
        )
        outcome = resolution.value
        if resolution == ForkResolution.MERGED:
            self.engine.transition(
                fork_id,
                DiscoveryStatus.VALIDATED,
                actor="merger",
                reason=f"Merge at similarity={similarity}",
            )
        elif resolution == ForkResolution.PARALLEL:
            self.engine.transition(
                fork_id,
                DiscoveryStatus.VALIDATED,
                actor="merger",
                reason=f"Parallel retention at similarity={similarity}",
            )
        else:
            self.engine.transition(
                fork_id,
                DiscoveryStatus.ARCHIVED,
                actor="merger",
                reason="Prune stale fork",
            )
        self._log(
            "merger",
            "resolve",
            fork_id,
            original=original_id,
            resolution=outcome,
            similarity=similarity,
        )
        return outcome

    def librarian_store(self, path: Path, requester_scope: str) -> bool:
        doc = parse_file(path)
        if not self.validator.validate_scope_access(doc.scope, requester_scope):
            self._log(
                "librarian",
                "deny_store",
                doc.adl_id,
                doc_scope=doc.scope,
                requester=requester_scope,
            )
            return False
        self.mem.store(doc)
        self._log("librarian", "store", doc.adl_id, scope=doc.scope)
        return True

    def librarian_query(
        self,
        adl_id: str,
        requester_scope: str,
        depth: int = 1,
    ) -> list[tuple[str, str, float]]:
        sk = self.mem.hot.get(adl_id)
        if sk and not self.validator.validate_scope_access(sk.scope, requester_scope):
            self._log(
                "librarian",
                "deny_read",
                adl_id,
                doc_scope=sk.scope,
                requester=requester_scope,
            )
            return []
        related = self.mem.find_related(adl_id, depth=depth)
        self._log(
            "librarian",
            "query_related",
            adl_id,
            count=len(related),
            requester=requester_scope,
        )
        return related

    def run_scripted_scenario(self) -> list[SimEvent]:
        """Full deterministic scenario using repo examples."""
        paths = [
            EXAMPLES / "capital_reflux_trap.md",
            EXAMPLES / "gradient_explosion.md",
            EXAMPLES / "attention_residual_discovery.md",
        ]
        for p in paths:
            self.discoverer_emit(p)
            self.reviewer_validate_and_transition(p)
            self.librarian_store(p, requester_scope="private/ceiec-aml")

        self.skeptic_fork(
            EXAMPLES / "matdo_original.md",
            "disc-matdo-kinetic",
            EXAMPLES / "matdo_fork_kinetic.md",
        )
        self.merger_resolve("disc-matdo-original", "disc-matdo-kinetic", similarity=0.62)

        self.librarian_store(EXAMPLES / "matdo_fork_kinetic.md", "private/materials-lab")
        self.librarian_query("Gradient Explosion", "public", depth=1)

        return self.events

    def write_log(self, path: Path | None = None) -> Path:
        out = path or LOG_DIR / "run_001.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(e.to_json() for e in self.events) + "\n", encoding="utf-8")
        return out

    def close(self) -> None:
        self.mem.close()


def run_scripted_sim(
    db_path: str | Path | None = None,
    log_path: Path | None = None,
    strict_ontology: bool | None = None,
) -> Path:
    harness = ScriptedHarness(db_path=db_path, strict_ontology=strict_ontology)
    harness.run_scripted_scenario()
    log_file = harness.write_log(log_path)
    harness.close()
    return log_file
