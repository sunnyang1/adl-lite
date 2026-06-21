"""
Calibration and aggregated confidence for ADL Lite.

Implements two confidence aggregation strategies:
  1. γ(C)     — O(1) last-VALIDATE confidence (default, matches paper §4.4)
  2. γ_agg(C) — bonus-formula aggregate with per-actor maxima
                (matches paper Appendix E; rewards distinct validators)
  3. γ_cal(C) — per-actor accuracy-weighted calibrated confidence
                (optional; weights bonus-formula by validator trustworthiness)

All three are exposed via EventChain.confidence, .aggregated_confidence(),
and .calibrated_confidence() respectively.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from .models import Event

DEFAULT_ACCURACY = 0.5
BONUS_INCREMENT = 0.05
BASE_FLOOR = 0.5
CALIBRATION_PATH = Path(".adl") / "calibration.yaml"


class CalibrationProfile(BaseModel):
    """Per-actor calibration profile."""

    actor: str
    accuracy_score: float = Field(default=DEFAULT_ACCURACY)

    @field_validator("accuracy_score")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


class MARGINCalibrator:
    """
    Calibrator that tracks per-actor accuracy scores for confidence weighting.
    Profiles are persisted as YAML in .adl/calibration.yaml.

    Supports epistemic context grouping: each actor can have different
    accuracy scores per domain (e.g., 'aml', 'fraud', 'general').
    """

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path or CALIBRATION_PATH)
        self._profiles: dict[str, CalibrationProfile] = {}
        self._context_profiles: dict[str, dict[str, CalibrationProfile]] = {}

    def load_profiles(self) -> None:
        """Load profiles from YAML."""
        if not self.path.exists():
            self._profiles = {}
            self._context_profiles = {}
            return
        with self.path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        raw = data.get("profiles", [])
        self._profiles = {
            p["actor"]: CalibrationProfile(**p) for p in raw if isinstance(p, dict) and "actor" in p
        }
        # Load context-scoped profiles: {context: {actor: profile}}
        raw_ctx = data.get("context_profiles", {})
        self._context_profiles = {
            ctx: {actor: CalibrationProfile(**prof) for actor, prof in actors.items()}
            for ctx, actors in raw_ctx.items()
            if isinstance(actors, dict)
        }

    def save_profiles(self) -> None:
        """Save profiles to YAML."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "profiles": [p.model_dump() for p in self._profiles.values()],
            "context_profiles": {
                ctx: {actor: prof.model_dump() for actor, prof in actors.items()}
                for ctx, actors in self._context_profiles.items()
            },
        }
        with self.path.open("w", encoding="utf-8") as f:
            yaml.dump(payload, f, sort_keys=False, allow_unicode=True)

    def get_accuracy(self, actor: str, context: str = "general") -> float:
        """Return accuracy score for actor; default 0.5 if unknown.

        If context != 'general' and a context-specific profile exists,
        return that; otherwise fall back to the global profile.
        """
        if actor not in self._profiles and actor not in self._context_profiles.get(context, {}):
            self.load_profiles()
        if context != "general":
            ctx_profiles = self._context_profiles.get(context, {})
            if actor in ctx_profiles:
                return ctx_profiles[actor].accuracy_score
        return self._profiles.get(actor, CalibrationProfile(actor=actor)).accuracy_score

    def update_accuracy(
        self, actor: str, observed_accuracy: float, context: str = "general"
    ) -> None:
        """Update or create a profile for actor."""
        if context == "general":
            self._profiles[actor] = CalibrationProfile(
                actor=actor, accuracy_score=observed_accuracy
            )
        else:
            if context not in self._context_profiles:
                self._context_profiles[context] = {}
            self._context_profiles[context][actor] = CalibrationProfile(
                actor=actor, accuracy_score=observed_accuracy
            )
        self.save_profiles()


# ---------------------------------------------------------------------------
# Aggregated confidence  γ_agg(C)  — matches paper Appendix E
# ---------------------------------------------------------------------------


def aggregated_confidence(events: list[Event]) -> float:
    """
    Compute bonus-formula aggregate confidence from VALIDATE events.

    γ_agg(C) = min(1.0, c_base + β × (N_vals − 1))
    where  c_base = max(0.5, mean_a φ(a,V))
           φ(a,V) = max confidence reported by actor a
           N_vals = number of distinct validators
           β      = 0.05
    """
    from .models import EventType

    validate_events = [e for e in events if e.event_type == EventType.VALIDATE]
    if not validate_events:
        return 0.0

    # Per-actor maximum confidence (anti-double-counting)
    actor_max: dict[str, float] = {}
    for event in validate_events:
        actor = event.actor
        confidence = float(event.payload.get("confidence", 0.0))
        actor_max[actor] = max(actor_max.get(actor, 0.0), confidence)

    n_vals = len(actor_max)
    if n_vals == 0:
        return 0.0

    # Base confidence = mean of per-actor maxima, floored at 0.5
    c_base = max(BASE_FLOOR, sum(actor_max.values()) / n_vals)

    # Bonus per additional distinct validator beyond the first
    bonus = BONUS_INCREMENT * (n_vals - 1)

    return min(1.0, c_base + bonus)


# ---------------------------------------------------------------------------
# Calibrated confidence  γ_cal(C)  — per-actor accuracy-weighted variant
# ---------------------------------------------------------------------------


def calibrated_confidence(events: list[Event], calibrator: MARGINCalibrator) -> float:
    """
    Compute per-actor accuracy-weighted calibrated confidence.

    γ_cal = Σ (φ(a,V) × accuracy_a) / Σ accuracy_a

    where φ(a,V) is the per-actor maximum confidence.
    This is a standard weighted mean that normalises by the sum of accuracy
    scores, so high-accuracy validators dominate the aggregate.
    """
    from .models import EventType

    validate_events = [e for e in events if e.event_type == EventType.VALIDATE]
    if not validate_events:
        return 0.0

    # Per-actor maximum confidence
    actor_max: dict[str, float] = {}
    for event in validate_events:
        actor = event.actor
        confidence = float(event.payload.get("confidence", 0.0))
        actor_max[actor] = max(actor_max.get(actor, 0.0), confidence)

    if not actor_max:
        return 0.0

    total = 0.0
    total_accuracy = 0.0
    for actor, confidence in actor_max.items():
        accuracy = calibrator.get_accuracy(actor)
        total += confidence * accuracy
        total_accuracy += accuracy

    if total_accuracy == 0:
        return 0.0
    return min(1.0, total / total_accuracy)


# ---------------------------------------------------------------------------
# EWMA confidence  γ_ewma(C)  — time-decay weighted calibration
# ---------------------------------------------------------------------------


def ewma_confidence(events: list[Event], alpha: float = 0.3) -> float:
    """
    Compute EWMA-calibrated confidence with time-decay weighting.

    γ_ewma(C) = EWMA of per-actor maximum confidence values,
    ordered by event timestamp, with smoothing factor α ∈ (0, 1].

    Higher α gives more weight to recent events; α = 1.0 is equivalent
    to the O(1) last-VALIDATE strategy. The default α = 0.3 balances
    responsiveness with stability (common in financial EWMA practice).

    This addresses overconfidence in γ(C) by down-weighting stale
    self-validations and up-weighting recent cross-validations.
    """

    from .models import EventType

    validate_events = [e for e in events if e.event_type == EventType.VALIDATE]
    if not validate_events:
        return 0.0

    # Per-actor maximum confidence, then sort by timestamp
    actor_max: dict[str, tuple[str, float]] = {}  # actor -> (timestamp, confidence)
    for event in validate_events:
        actor = event.actor
        confidence = float(event.payload.get("confidence", 0.0))
        ts = event.timestamp
        if actor not in actor_max or confidence > actor_max[actor][1]:
            actor_max[actor] = (ts, confidence)

    if not actor_max:
        return 0.0

    # Sort by timestamp ascending for EWMA
    sorted_vals = sorted(actor_max.values(), key=lambda x: x[0])
    confidences = [c for _, c in sorted_vals]

    # EWMA: S_t = α * x_t + (1-α) * S_{t-1}
    ewma = confidences[0]
    for conf in confidences[1:]:
        ewma = alpha * conf + (1 - alpha) * ewma

    return min(1.0, max(0.0, ewma))


def context_calibrated_confidence(
    events: list[Event],
    calibrator: MARGINCalibrator,
    context: str = "general",
) -> float:
    """
    Calibrate confidence within a specific epistemic context.

    γ_ctx(C) = Σ (φ(a,V) × accuracy_a|ctx) / |A|

    where accuracy_a|ctx is the per-actor accuracy score for the given
    epistemic context (e.g., 'aml', 'fraud', 'general'). Unknown contexts
    fall back to the global accuracy score. This enables domain-specific
    calibration: an actor may be accurate in fraud detection but
    overconfident in AML pattern matching.
    """
    from .models import EventType

    validate_events = [e for e in events if e.event_type == EventType.VALIDATE]
    if not validate_events:
        return 0.0

    actor_max: dict[str, float] = {}
    for event in validate_events:
        actor = event.actor
        confidence = float(event.payload.get("confidence", 0.0))
        actor_max[actor] = max(actor_max.get(actor, 0.0), confidence)

    if not actor_max:
        return 0.0

    total = 0.0
    for actor, confidence in actor_max.items():
        accuracy = calibrator.get_accuracy(actor, context=context)
        total += confidence * accuracy

    return min(1.0, total / len(actor_max))


# ---------------------------------------------------------------------------
# Epistemic-band calibration  γ_band(C)  — per-confidence-band correction
# ---------------------------------------------------------------------------

DEFAULT_BANDS: list[tuple[float, float, float]] = [
    (0.0, 0.3, 0.15),  # low-confidence band: underconfidence → boost
    (0.3, 0.7, 0.0),  # mid band: no correction
    (0.7, 1.0, -0.10),  # high-confidence band: overconfidence → dampen
]


def band_calibrated_confidence(
    events: list[Event],
    calibrator: MARGINCalibrator | None = None,
    bands: list[tuple[float, float, float]] | None = None,
) -> float:
    """
    Per-band calibrated confidence to address systematic over/under-confidence.

    For each actor's maximum confidence, identify its band and apply a
    correction offset. The default bands are:
      [0.0, 0.3) → +0.15  (underconfidence boost)
      [0.3, 0.7) → +0.00  (no correction)
      [0.7, 1.0] → -0.10  (overconfidence dampening)

    If a calibrator is provided, the correction is further weighted by
    per-actor accuracy: correction × accuracy_a.

    This directly addresses the "overconfidence in γ(C)" limitation
    identified in §6 Discussion (L3) by applying domain-agnostic
    epistemic band correction before actor-weighted aggregation.
    """
    from .models import EventType

    bands = bands or DEFAULT_BANDS
    validate_events = [e for e in events if e.event_type == EventType.VALIDATE]
    if not validate_events:
        return 0.0

    actor_max: dict[str, float] = {}
    for event in validate_events:
        actor = event.actor
        confidence = float(event.payload.get("confidence", 0.0))
        actor_max[actor] = max(actor_max.get(actor, 0.0), confidence)

    if not actor_max:
        return 0.0

    total = 0.0
    for actor, confidence in actor_max.items():
        correction = 0.0
        for low, high, offset in bands:
            if low <= confidence < high or (high == 1.0 and low <= confidence <= high):
                correction = offset
                break

        if calibrator is not None:
            correction *= calibrator.get_accuracy(actor)

        adjusted = max(0.0, min(1.0, confidence + correction))
        total += adjusted

    return min(1.0, total / len(actor_max))
