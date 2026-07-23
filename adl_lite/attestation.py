"""
ADL Lite — Attestation validation and evidence integration (EAL Phase 2).

Per docs/design/execution-attestation.md:

- ``AttestationValidator`` resolves ``ATTEST.subject_execution`` against an
  injected execution lookup — the same pattern as
  ``RelationValidator.filter_valid_relations`` (chains stay self-contained;
  cross-log references are resolved at the validation layer).
- ``AttestationIndex`` is a derived, read-only view over a chain's ATTEST
  events, providing distinct-scope confirm/refute counts.
- ``attested_confidence`` implements the evidence-weighted confidence factor
  (§7.1 of the design): monotone, opt-in, and NEVER lowered by refutations
  (D3 — refutations push status forward via DEPRECATE proposals instead of
  pulling confidence down).
- ``feed_calibrator`` closes the calibration bootstrap loop (§7.3): ATTEST
  verdicts later overturned by stronger independent attestations feed
  ``MARGINCalibrator.update_from_feedback``.

Phase 2 simplifications (documented honestly):
- Scope diversity uses the ATTEST payload's optional ``scope`` field
  (self-declared org scope), degenerating to the actor id when absent.
  DID→org attestation is out of scope for Lite.
- Evidence backing is capability-level: a VALIDATE event counts as backed
  when the capability accumulates enough distinct-scope confirms, not when a
  specific execution matches the validator's own run.
"""

from __future__ import annotations

from typing import Any

from .logging_config import get_logger
from .models import Event, EventChain, EventType
from .ontology import OntologyManager

logger = get_logger(__name__)

VERDICTS = ("confirm", "refute", "inconclusive")
ATTEST_METHODS = ("replay", "property-check", "manual", "tee-quote", "zk-proof")

# Evidence strength ordering used when two attestations about the same
# execution conflict: the stronger method wins (replay beats manual, etc.).
_METHOD_STRENGTH = {
    "manual": 1,
    "property-check": 2,
    "replay": 3,
    "tee-quote": 4,
    "zk-proof": 5,
}

# Verdict as a binary claim about execution validity, for calibration feedback.
_VERDICT_CLAIM = {"confirm": 1.0, "refute": 0.0}


class AttestationValidator:
    """Validate ATTEST events against an injected execution lookup.

    Args:
        execution_lookup: Mapping ``execution_id -> receipt Event``, or an
            ``ExecutionLog`` instance, or ``None`` (every subject is "pending").
    """

    def __init__(self, execution_lookup: Any = None) -> None:
        if execution_lookup is not None and hasattr(execution_lookup, "get_receipt"):
            self._lookup = execution_lookup.get_receipt
        elif isinstance(execution_lookup, dict):
            self._lookup = execution_lookup.get
        elif execution_lookup is None:
            self._lookup = lambda _eid: None
        else:
            raise TypeError(f"Unsupported execution_lookup type: {type(execution_lookup)}")

    def scope_of(self, attest_event: Event) -> str:
        """Organizational scope credited for this attestation.

        Uses the self-declared payload ``scope`` when present, degenerating to
        the actor id (distinct-actor fallback).
        """
        scope = attest_event.payload.get("scope")
        if isinstance(scope, str) and scope.strip():
            return scope.strip()
        return attest_event.actor

    def validate(self, attest_event: Event) -> list[str]:
        """Return a list of issues (empty = valid).

        Issues are strings; ``pending:`` prefix marks a resolvable-later
        condition (subject receipt not yet synced) rather than a hard failure.
        """
        issues: list[str] = []
        if attest_event.event_type is not EventType.ATTEST:
            return ["not an ATTEST event"]

        payload = attest_event.payload
        subject_id = payload.get("subject_execution")
        subject = self._lookup(subject_id) if subject_id else None

        if subject is None:
            issues.append(f"pending: subject execution {subject_id!r} not resolvable")
            return issues  # Commitment equality cannot be checked yet.

        # Self-attestation: attester == executor does not count as independent
        # evidence (anti-collusion; see design §8).
        if attest_event.actor == subject.actor:
            issues.append("self-attestation: attester is the executor")

        method = payload.get("method")
        verdict = payload.get("verdict")
        replay = payload.get("replay")

        if method == "replay" and verdict == "confirm" and isinstance(replay, dict):
            # Cross-log equality: the attester's replayed commitments must match
            # the subject receipt's commitments (chain-local axiom 15 only
            # checks internal consistency).
            if replay.get("input_commitment") != subject.payload.get("input_commitment"):
                issues.append("replay input_commitment differs from subject receipt")
            if replay.get("output_commitment") != subject.payload.get("output_commitment"):
                issues.append("replay output_commitment differs from subject receipt")
        return issues


class AttestationIndex:
    """Derived read-only view over a chain's ATTEST events."""

    def __init__(self, events: list[Event], validator: AttestationValidator | None = None) -> None:
        self._validator = validator or AttestationValidator()
        self._by_subject: dict[str, list[Event]] = {}
        for e in events:
            if e.event_type is EventType.ATTEST:
                subject = e.payload.get("subject_execution")
                if subject:
                    self._by_subject.setdefault(subject, []).append(e)

    # ------------------------------------------------------------------
    # Counting
    # ------------------------------------------------------------------

    def _verdict_events(self, execution_id: str, verdict: str) -> list[Event]:
        return [
            e for e in self._by_subject.get(execution_id, []) if e.payload.get("verdict") == verdict
        ]

    def distinct_scope_count(self, execution_id: str, verdict: str) -> int:
        """Distinct-scope count of attestations with the given verdict.

        Self-attestations (attester == subject executor) are excluded — they
        carry no independent evidence weight.
        """
        scopes: set[str] = set()
        for e in self._verdict_events(execution_id, verdict):
            subject = self._validator._lookup(execution_id)
            if subject is not None and e.actor == subject.actor:
                continue
            scopes.add(self._validator.scope_of(e))
        return len(scopes)

    def subjects(self) -> list[str]:
        return sorted(self._by_subject)

    def summary(self) -> dict[str, dict[str, int]]:
        """Per-execution verdict counts by distinct scope."""
        return {
            subject: {verdict: self.distinct_scope_count(subject, verdict) for verdict in VERDICTS}
            for subject in self.subjects()
        }


# ---------------------------------------------------------------------------
# Evidence-weighted confidence (design §7.1) — opt-in, monotone
# ---------------------------------------------------------------------------


def capability_backed(
    chain: EventChain,
    index: AttestationIndex,
    ontology: OntologyManager | None = None,
) -> bool:
    """Whether a capability's validation is backed by enough distinct-scope confirms."""
    ontology = ontology or OntologyManager()
    required = ontology.min_distinct_scopes()
    for subject in index.subjects():
        if index.distinct_scope_count(subject, "confirm") >= required:
            return True
    return False


def attested_confidence(
    chain: EventChain,
    index: AttestationIndex,
    ontology: OntologyManager | None = None,
) -> float:
    """Evidence-weighted confidence: max over VALIDATE of (confidence × factor).

    factor = 1.0 when the capability is attestation-backed, else α
    (``attestation.evidence_factor_unbacked``, default 0.5). Monotone: confirm
    attestations only accumulate, and refutations never lower the result (D3).
    This function is opt-in — ``EventChain.confidence`` is unchanged.
    """
    ontology = ontology or OntologyManager()
    alpha = ontology.evidence_factor_unbacked()
    factor = 1.0 if capability_backed(chain, index, ontology) else alpha
    best = 0.0
    for event in chain:
        if event.event_type is EventType.VALIDATE:
            conf = min(1.0, max(0.0, float(event.payload.get("confidence", 0.0))))
            best = max(best, conf * factor)
    return best


# ---------------------------------------------------------------------------
# Refutation → DEPRECATE proposal (design §7.2)
# ---------------------------------------------------------------------------


def refute_status(
    chain: EventChain,
    index: AttestationIndex,
    ontology: OntologyManager | None = None,
) -> dict[str, Any]:
    """Aggregate distinct-scope refutations against the DEPRECATE threshold.

    Returns ``{"refute_scopes": n, "threshold": r, "proposal": bool, "subjects": {...}}``.
    ``proposal=True`` means a DEPRECATE transition SHOULD be proposed through
    the normal consensus flow — never applied automatically.
    """
    ontology = ontology or OntologyManager()
    threshold = ontology.refute_threshold()
    per_subject = {
        subject: index.distinct_scope_count(subject, "refute") for subject in index.subjects()
    }
    worst = max(per_subject.values(), default=0)
    return {
        "refute_scopes": worst,
        "threshold": threshold,
        "proposal": worst >= threshold,
        "subjects": per_subject,
    }


# ---------------------------------------------------------------------------
# Calibration bootstrap (design §7.3)
# ---------------------------------------------------------------------------


def feed_calibrator(
    events: list[Event],
    calibrator: Any,
    *,
    context: str = "attestation",
    alpha: float = 0.3,
) -> int:
    """Feed overturned/supported ATTEST verdicts into a MARGINCalibrator.

    For each ATTEST ``a1`` about execution X, find the *latest* attestation
    ``a2`` about X from a different actor with method strength >= a1's. If
    a2's verdict conflicts with a1's binary claim, a1 is considered
    overturned and its actor receives a feedback update
    (predicted=claim, ground_truth=a2's claim). Supported verdicts receive a
    reinforcing update. ``inconclusive`` verdicts never generate feedback.

    Returns the number of feedback updates applied.
    """
    by_subject: dict[str, list[Event]] = {}
    for e in events:
        if e.event_type is EventType.ATTEST:
            subject = e.payload.get("subject_execution")
            if subject:
                by_subject.setdefault(subject, []).append(e)

    updates = 0
    for subject_events in by_subject.values():
        ordered = sorted(subject_events, key=lambda e: e.timestamp)
        for i, a1 in enumerate(ordered):
            verdict1 = a1.payload.get("verdict")
            claim1 = _VERDICT_CLAIM.get(str(verdict1)) if verdict1 is not None else None
            if claim1 is None:
                continue
            strength1 = _METHOD_STRENGTH.get(a1.payload.get("method", "manual"), 0)
            # Latest independent attestation of at-equal-or-stronger method.
            a2 = None
            for cand in reversed(ordered[i + 1 :]):
                if cand.actor == a1.actor:
                    continue
                if cand.payload.get("verdict") not in _VERDICT_CLAIM:
                    continue
                strength2 = _METHOD_STRENGTH.get(cand.payload.get("method", "manual"), 0)
                if strength2 >= strength1:
                    a2 = cand
                    break
            if a2 is None:
                continue
            claim2 = _VERDICT_CLAIM[str(a2.payload["verdict"])]
            calibrator.update_from_feedback(
                a1.actor,
                predicted_confidence=claim1,
                ground_truth=claim2,
                context=context,
                alpha=alpha,
            )
            updates += 1
    return updates
