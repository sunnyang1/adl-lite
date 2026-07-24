"""E33: Challenge–response game — break-even challenge frequency (EAL Phase 3).

Motivation (docs/design/execution-attestation.md §5.6): replay attestation
catches fabricated receipts, but a deterministic capability can pass replay by
caching ONE honest answer forever. The CHALLENGE commit–reveal protocol makes
the input unpredictable (a secret seed revealed only at challenge time), so a
cached answer cannot match. This experiment quantifies the game theory:

- Honest executor earns R - C per round (reward minus execution cost).
- Lazy executor (always caches) earns G per unchallenged round, and loses P
  when challenged (penalty: forfeited reward + reputation damage via the
  MARGIN EWMA calibrator's asymmetric down-weighting).
- E_lazy(f) = (1 - f)·G - f·P;  break-even f* = (G - (R - C)) / (G + P).

Two arms:
1. Analytic arm — closed-form f* from the payoff parameters.
2. Simulation arm — T rounds per challenge frequency f, using the REAL
   ChallengeManager state machine (open → reveal → answer/timeout) and the
   REAL MARGINCalibrator for reputation trajectories. The lazy executor's
   cached answer never matches the independently recomputed seed output, so
   every challenge is a catch (refute) or a timeout.

Metrics: f* analytic vs simulated, per-round payoffs at key frequencies,
protocol overhead per challenge event, reputation trajectory, and
ChallengeManager derivation accuracy vs simulation ground truth.
"""

from __future__ import annotations

import random
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from adl_lite.calibration import MARGINCalibrator
from adl_lite.challenge import ChallengeManager, generate_seed, seed_commitment
from adl_lite.models import Event, EventChain, EventType
from adl_lite.replay import sha256_commitment

from .base import BaseExperiment, ExperimentResult
from .registry import register

# Payoff parameters (normalized reward R = 1.0).
REWARD = 1.0
COST_HONEST = 0.3
GAIN_LAZY = 1.0
PENALTY_CAUGHT = 2.0
E_HONEST = REWARD - COST_HONEST  # 0.7 per round

T_ROUNDS = 1000
Q_TIMEOUT = 0.10  # among challenged rounds, fraction the lazy executor skips
FREQUENCIES = [round(0.02 * i, 2) for i in range(16)]  # 0.00 .. 0.30

_FAKE_PROOF = {"type": "Ed25519Signature2020", "proofValue": "zSIMULATED"}


def _f_star_analytic() -> float:
    """Closed-form break-even frequency: E_lazy(f*) = E_honest."""
    return (GAIN_LAZY - E_HONEST) / (GAIN_LAZY + PENALTY_CAUGHT)


class _SimClock:
    """Strictly increasing simulated event clock (Axiom 7 friendly)."""

    def __init__(self) -> None:
        self.t = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def tick(self, seconds: float = 1.0) -> datetime:
        self.t += timedelta(seconds=seconds)
        return self.t


def _challenge_event(cap_id: str, actor: str, ts: datetime, payload: dict) -> Event:
    return Event(
        concept_id=cap_id,
        event_type=EventType.CHALLENGE,
        actor=actor,
        timestamp=ts.isoformat(),
        payload=payload,
        proof=dict(_FAKE_PROOF),
    )


def _simulate_frequency(f: float, rng: random.Random, tmp_dir: Path) -> dict:
    """Run T rounds at challenge frequency f against one lazy executor."""
    cap_id = "cap-lazy-sim"
    chain = EventChain(concept_id=cap_id)
    clock = _SimClock()
    chain.append(
        Event(
            concept_id=cap_id,
            event_type=EventType.REGISTER,
            actor="registry",
            timestamp=clock.tick().isoformat(),
        )
    )

    # MARGINCalibrator persists on every EWMA update; keep that I/O in a
    # throwaway tmp dir so the experiment leaves no residue.
    calibrator = MARGINCalibrator(tmp_dir / f"calibration-{f}.yaml")
    lazy_payoff = 0.0
    n_challenged = 0
    n_answered = 0  # answered (wrong) at protocol level
    n_timeout = 0
    challenge_events = 0
    append_ms = 0.0

    for _ in range(T_ROUNDS):
        if rng.random() >= f:
            lazy_payoff += GAIN_LAZY  # unchallenged: cached answer passes
            continue

        n_challenged += 1
        lazy_payoff -= PENALTY_CAUGHT
        # Challenger commits to a seed the lazy executor cannot predict.
        seed = generate_seed()
        cid = f"chl-{n_challenged:05d}"
        open_ts = clock.tick()
        deadline = open_ts + timedelta(seconds=300)

        t0 = time.monotonic()
        chain.append(
            _challenge_event(
                cap_id,
                "challenger",
                open_ts,
                {
                    "challenge_id": cid,
                    "phase": "open",
                    "seed_commitment": seed_commitment(seed),
                    "reveal_deadline": deadline.isoformat(),
                    "response_window_s": 60.0,
                    "target_executor": "lazy-exec",
                },
            )
        )
        reveal_ts = clock.tick()
        chain.append(
            _challenge_event(
                cap_id,
                "challenger",
                reveal_ts,
                {"challenge_id": cid, "phase": "reveal", "seed": seed},
            )
        )

        if rng.random() < Q_TIMEOUT:
            n_timeout += 1  # no answer event; derived as timed_out at audit
            challenge_events += 2
        else:
            # Lazy executor answers with a CACHED commitment — never the true
            # sha256 of the seed output, so independent verification refutes it.
            n_answered += 1
            chain.append(
                _challenge_event(
                    cap_id,
                    "lazy-exec",
                    clock.tick(),
                    {
                        "challenge_id": cid,
                        "phase": "answer",
                        "output_commitment": sha256_commitment(b"CACHED-STALE-OUTPUT"),
                    },
                )
            )
            challenge_events += 3
        append_ms += (time.monotonic() - t0) * 1000

        # Verifier independently recomputes on the revealed seed: mismatch.
        calibrator.update_from_feedback(
            "lazy-exec", predicted_confidence=1.0, ground_truth=0.0, context="challenge"
        )

    # Post-hoc audit: well past every deadline/window.
    audit_as_of = clock.tick(3600)
    manager = ChallengeManager()
    issues = manager.apply_chain(chain)
    metrics = manager.response_metrics(executor="lazy-exec", as_of=audit_as_of)

    return {
        "f": f,
        "lazy_payoff_per_round": round(lazy_payoff / T_ROUNDS, 4),
        "honest_payoff_per_round": E_HONEST,
        "n_challenged": n_challenged,
        "n_answered_wrong": n_answered,
        "n_timeout": n_timeout,
        "chain_events": len(chain.events),
        "chain_integrity": chain.verify_integrity(),
        "manager_issues": len(issues),
        "manager_answered": metrics["overall"]["answered"],
        "manager_timed_out": metrics["overall"]["timed_out"],
        "manager_response_rate": metrics["overall"]["response_rate"],
        "lazy_accuracy": round(calibrator.get_accuracy("lazy-exec", context="challenge"), 4),
        "append_ms_per_challenge_event": round(append_ms / max(1, challenge_events), 4),
    }


def _interpolate_f_star(rows: list[dict]) -> float | None:
    """First crossing of lazy payoff below the honest payoff (linear interp)."""
    prev = None
    for row in rows:
        if row["lazy_payoff_per_round"] <= E_HONEST:
            if prev is None:
                return row["f"]
            f0, y0 = prev["f"], prev["lazy_payoff_per_round"]
            f1, y1 = row["f"], row["lazy_payoff_per_round"]
            if y1 == y0:
                return f1
            return round(f0 + (E_HONEST - y0) * (f1 - f0) / (y1 - y0), 4)
        prev = row
    return None


@register("E33")
class E33ChallengeGame(BaseExperiment):
    experiment_id = "E33"
    name = "Challenge–response game: break-even challenge frequency"
    description = (
        "Analytic vs simulated break-even challenge frequency for rational lazy "
        "executors, using the real ChallengeManager state machine and MARGIN "
        "calibrator reputation trajectories"
    )

    def run(self) -> ExperimentResult:
        rng = random.Random(33)
        f_star = _f_star_analytic()

        with tempfile.TemporaryDirectory(prefix="adl-e33-") as tmp:
            rows = [_simulate_frequency(f, rng, Path(tmp)) for f in FREQUENCIES]
        f_star_sim = _interpolate_f_star(rows)

        at = {row["f"]: row for row in rows}
        f0 = at[0.0]
        f_mid = at[0.10]
        f_hi = at[0.20]

        # ChallengeManager derivations must match simulation ground truth on
        # every row: answered (protocol level) and timed_out counts, and zero
        # cross-event issues.
        derivations_ok = all(
            row["manager_answered"] == row["n_answered_wrong"]
            and row["manager_timed_out"] == row["n_timeout"]
            and row["manager_issues"] == 0
            and row["chain_integrity"]
            for row in rows
        )

        metrics = {
            "payoff_params": {
                "reward": REWARD,
                "cost_honest": COST_HONEST,
                "gain_lazy": GAIN_LAZY,
                "penalty_caught": PENALTY_CAUGHT,
            },
            "e_honest_per_round": E_HONEST,
            "f_star_analytic": round(f_star, 4),
            "f_star_simulated": f_star_sim,
            "f_star_abs_error": (
                round(abs(f_star_sim - f_star), 4) if f_star_sim is not None else None
            ),
            "lazy_payoff_f0": f0["lazy_payoff_per_round"],
            "lazy_payoff_f10": f_mid["lazy_payoff_per_round"],
            "lazy_payoff_f20": f_hi["lazy_payoff_per_round"],
            "lazy_accuracy_after_f10": f_mid["lazy_accuracy"],
            "manager_derivations_match_ground_truth": derivations_ok,
            "append_ms_per_challenge_event": f_hi["append_ms_per_challenge_event"],
            "chain_events_at_f20": f_hi["chain_events"],
        }

        ok = (
            f_star_sim is not None
            and abs(f_star_sim - f_star) <= 0.03
            and f0["lazy_payoff_per_round"] > E_HONEST  # unchallenged: lazy wins
            and f_hi["lazy_payoff_per_round"] < E_HONEST  # challenged enough: honest wins
            and derivations_ok
        )
        return ExperimentResult(
            experiment_id="E33",
            status="passed" if ok else "failed",
            metrics=metrics,
            raw_data=rows,
        )
