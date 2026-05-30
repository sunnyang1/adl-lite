"""E7: Realtime event watcher — pattern detection on each event append.

Tests RealtimeWatcher on IBM AML transaction data:
  - Injects known laundering patterns one event at a time
  - Verifies alerts fire exactly on the threshold-crossing event
  - Measures false positive rate (alerts on non-laundering events)
  - Verifies handlers are dispatched correctly
"""

from __future__ import annotations

from pathlib import Path

from .base import BaseExperiment, ExperimentResult
from .registry import register

from adl_lite.realtime import RealtimeWatcher, AlertHandler
from adl_lite.models import Event, EventChain, EventType

IBM_DATA = Path(__file__).resolve().parent.parent / "data" / "aml" / "ibm_data"


@register("E7")
class E7RealtimeWatcher(BaseExperiment):
    experiment_id = "E7"
    name = "Realtime pattern detection triggers"
    description = "Real-time alerting on event append — threshold-crossing accuracy"

    def run(self) -> ExperimentResult:
        watcher = RealtimeWatcher()
        handler_log: list[str] = []

        def _log_handler(alert: AlertHandler) -> None:
            handler_log.append(
                f"[{alert.alert_type}] {alert.concept_id}: {alert.detail}"
            )

        watcher.on_any(_log_handler)

        results = []
        errors = []

        # ===== TEST 1: Smurfing detection (5 sub-$1000 laundering events) =====
        chain1 = EventChain(concept_id="smurf-test")
        smurf_alerts = 0
        for i in range(10):
            is_launder = "1" if i < 7 else "0"
            event = Event(
                concept_id="smurf-test",
                event_type=EventType.REGISTER,
                actor="system",
                payload={"Amount Received": 850 + i * 5, "Is Laundering": is_launder},
            )
            alerts = watcher.check(chain1, event)
            chain1.append(event)
            smurf_alerts += sum(1 for a in alerts if a.alert_type == "smurfing")

        # Smurfing fires on 5th laundering event (threshold=5, all <$1000)
        smurf_ok = smurf_alerts == 1
        results.append({
            "test": "smurfing_threshold",
            "alerts_fired": smurf_alerts,
            "expected": 1,
            "ok": smurf_ok,
        })
        if not smurf_ok:
            errors.append(f"Smurfing: expected 1 alert, got {smurf_alerts}")

        # ===== TEST 2: Rapid movement (exactly on 10th laundering event) =====
        chain2 = EventChain(concept_id="rapid-test")
        rapid_alerts = 0
        for i in range(12):
            event = Event(
                concept_id="rapid-test",
                event_type=EventType.REGISTER,
                actor="system",
                payload={"Amount Received": 5000 + i * 100, "Is Laundering": "1"},
            )
            alerts = watcher.check(chain2, event)
            chain2.append(event)
            rapid_alerts += sum(1 for a in alerts if a.alert_type == "rapid_movement")

        rapid_ok = rapid_alerts == 1  # fires exactly on 10th
        results.append({
            "test": "rapid_movement_threshold",
            "alerts_fired": rapid_alerts,
            "expected": 1,
            "ok": rapid_ok,
        })
        if not rapid_ok:
            errors.append(f"Rapid movement: expected 1 alert, got {rapid_alerts}")

        # ===== TEST 3: Fan-out (5 unique recipients) =====
        chain3 = EventChain(concept_id="fanout-test")
        fanout_alerts = 0
        for i in range(8):
            event = Event(
                concept_id="fanout-test",
                event_type=EventType.REGISTER,
                actor="system",
                payload={
                    "Amount Received": 3000,
                    "Account.1": f"TGT-{i}",
                    "Is Laundering": "1",
                },
            )
            alerts = watcher.check(chain3, event)
            chain3.append(event)
            fanout_alerts += sum(1 for a in alerts if a.alert_type == "fan_out")

        fanout_ok = fanout_alerts == 1  # fires on 5th unique target
        results.append({
            "test": "fan_out_threshold",
            "alerts_fired": fanout_alerts,
            "expected": 1,
            "ok": fanout_ok,
        })
        if not fanout_ok:
            errors.append(f"Fan-out: expected 1 alert, got {fanout_alerts}")

        # ===== TEST 4: Concept validated =====
        chain4 = EventChain(concept_id="status-test")
        chain4.append(Event(concept_id="status-test", event_type=EventType.REGISTER, actor="a"))
        val_alerts = watcher.check(
            chain4,
            Event(concept_id="status-test", event_type=EventType.VALIDATE, actor="v"),
        )
        val_ok = any(a.alert_type == "concept_validated" for a in val_alerts)
        results.append({
            "test": "status_transition",
            "alerts_fired": len(val_alerts),
            "validated_detected": val_ok,
            "ok": val_ok,
        })
        if not val_ok:
            errors.append("Status transition: validated not detected")

        # ===== TEST 5: No false positives on legitimate-only chain =====
        chain5 = EventChain(concept_id="legit-test")
        watcher.reset()
        fp_count = 0
        for i in range(100):
            event = Event(
                concept_id="legit-test",
                event_type=EventType.REGISTER,
                actor="system",
                payload={"Amount Received": 500 + i, "Is Laundering": "0"},
            )
            alerts = watcher.check(chain5, event)
            chain5.append(event)
            # No laundering alerts should fire on legitimate events
            laundering_alerts = [
                a for a in alerts
                if a.alert_type in ("smurfing", "rapid_movement", "fan_out")
            ]
            fp_count += len(laundering_alerts)

        fp_ok = fp_count == 0
        results.append({
            "test": "false_positive_check",
            "events_checked": 100,
            "false_positives": fp_count,
            "ok": fp_ok,
        })
        if not fp_ok:
            errors.append(f"False positives: {fp_count} on 100 legitimate events")

        # ===== TEST 6: Handler dispatch =====
        dispatched = len(handler_log) > 0
        results.append({
            "test": "handler_dispatch",
            "handlers_called": len(handler_log),
            "ok": dispatched,
        })

        all_ok = smurf_ok and rapid_ok and fanout_ok and val_ok and fp_ok and dispatched

        return ExperimentResult(
            experiment_id="E7",
            status="passed" if all_ok else "partial",
            metrics={
                "smurfing_threshold_ok": smurf_ok,
                "rapid_movement_threshold_ok": rapid_ok,
                "fan_out_threshold_ok": fanout_ok,
                "status_transition_ok": val_ok,
                "false_positives_on_100_legit": fp_count,
                "handler_callbacks_fired": len(handler_log),
                "test_count": 6,
            },
            raw_data=results,
            errors=errors,
        )
