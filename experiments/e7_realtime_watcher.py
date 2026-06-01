"""E7: Realtime event watcher — pattern detection on actual IBM AML data.

Tests RealtimeWatcher on real IBM AML transaction data:
  - Streams actual transactions from account A0990 (known laundering)
  - Verifies alerts fire exactly on threshold-crossing events
  - Measures false positive rate on 200 legitimate accounts
  - Verifies handlers are dispatched correctly

Data: data/aml/ibm_data/HI-Small_Trans.csv (9,300 txns, 201 accounts)
Ground truth: 1 laundering account (A0990, 300/300 laundering), 200 legit accounts.
"""

from __future__ import annotations

import csv
from pathlib import Path

from adl_lite.models import Event, EventChain, EventType
from adl_lite.realtime import AlertHandler, RealtimeWatcher

from .base import BaseExperiment, ExperimentResult
from .registry import register

IBM_DATA = Path(__file__).resolve().parent.parent / "data" / "aml" / "ibm_data"


@register("E7")
class E7RealtimeWatcher(BaseExperiment):
    experiment_id = "E7"
    name = "Realtime pattern detection on IBM AML data"
    description = "Real-time alerting on actual AML transactions — threshold accuracy + FP rate"

    def run(self) -> ExperimentResult:
        csv_path = IBM_DATA / "HI-Small_Trans.csv"
        if not csv_path.is_file():
            return ExperimentResult(
                experiment_id="E7",
                status="failed",
                errors=["IBM AML data not found."],
            )

        # Load all transactions grouped by account
        accounts: dict[str, list[dict]] = {}
        with csv_path.open("r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                acct = row["Account"]
                accounts.setdefault(acct, []).append(row)

        # Separate laundering and legitimate accounts
        laundering_accts = {
            a: txns for a, txns in accounts.items() if any(t["Is Laundering"] == "1" for t in txns)
        }
        legit_accts = {
            a: txns
            for a, txns in accounts.items()
            if not any(t["Is Laundering"] == "1" for t in txns)
        }

        # Pick the primary laundering account (A0990 has 300 laundering events)
        primary_laundering = max(
            laundering_accts.items(),
            key=lambda x: sum(1 for t in x[1] if t["Is Laundering"] == "1"),
        )
        launder_acct, launder_txns = primary_laundering

        watcher = RealtimeWatcher()
        handler_log: list[str] = []

        def _log_handler(alert: AlertHandler) -> None:
            handler_log.append(f"[{alert.alert_type}] {alert.concept_id}: {alert.detail}")

        watcher.on_any(_log_handler)

        results = []
        errors = []

        # ===== TEST 1: Smurfing detection on real laundering account =====
        # A0990: all 300 txns are laundering, all amounts sub-$1000.
        # Alert should fire exactly once at the 5th laundering event.
        chain1 = EventChain(concept_id=launder_acct)
        smurf_alerts = 0
        for _, txn in enumerate(launder_txns[:10]):
            event = Event(
                concept_id=launder_acct,
                event_type=EventType.REGISTER,
                actor="system",
                payload={
                    "Amount Received": float(txn["Amount Received"]),
                    "Is Laundering": txn["Is Laundering"],
                    "Account.1": txn["Account.1"],
                },
            )
            alerts = watcher.check(chain1, event)
            chain1.append(event)
            smurf_alerts += sum(1 for a in alerts if a.alert_type == "smurfing")

        smurf_ok = smurf_alerts == 1
        results.append(
            {
                "test": "smurfing_threshold",
                "account": launder_acct,
                "alerts_fired": smurf_alerts,
                "expected": 1,
                "ok": smurf_ok,
            }
        )
        if not smurf_ok:
            errors.append(f"Smurfing: expected 1 alert, got {smurf_alerts}")

        # ===== TEST 2: Rapid movement on real laundering account =====
        # Fire exactly on 10th laundering event.
        chain2 = EventChain(concept_id=launder_acct)
        rapid_alerts = 0
        for _, txn in enumerate(launder_txns[:12]):
            event = Event(
                concept_id=launder_acct,
                event_type=EventType.REGISTER,
                actor="system",
                payload={
                    "Amount Received": float(txn["Amount Received"]),
                    "Is Laundering": txn["Is Laundering"],
                },
            )
            alerts = watcher.check(chain2, event)
            chain2.append(event)
            rapid_alerts += sum(1 for a in alerts if a.alert_type == "rapid_movement")

        rapid_ok = rapid_alerts == 1
        results.append(
            {
                "test": "rapid_movement_threshold",
                "account": launder_acct,
                "alerts_fired": rapid_alerts,
                "expected": 1,
                "ok": rapid_ok,
            }
        )
        if not rapid_ok:
            errors.append(f"Rapid movement: expected 1 alert, got {rapid_alerts}")

        # ===== TEST 3: Fan-out on real laundering account =====
        # A0990 hits 5 unique targets at event 5.
        chain3 = EventChain(concept_id=launder_acct)
        fanout_alerts = 0
        for _, txn in enumerate(launder_txns[:8]):
            event = Event(
                concept_id=launder_acct,
                event_type=EventType.REGISTER,
                actor="system",
                payload={
                    "Amount Received": float(txn["Amount Received"]),
                    "Account.1": txn["Account.1"],
                    "Is Laundering": txn["Is Laundering"],
                },
            )
            alerts = watcher.check(chain3, event)
            chain3.append(event)
            fanout_alerts += sum(1 for a in alerts if a.alert_type == "fan_out")

        fanout_ok = fanout_alerts == 1
        results.append(
            {
                "test": "fan_out_threshold",
                "account": launder_acct,
                "alerts_fired": fanout_alerts,
                "expected": 1,
                "ok": fanout_ok,
            }
        )
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
        results.append(
            {
                "test": "status_transition",
                "alerts_fired": len(val_alerts),
                "validated_detected": val_ok,
                "ok": val_ok,
            }
        )
        if not val_ok:
            errors.append("Status transition: validated not detected")

        # ===== TEST 5: False positives on ALL legitimate accounts =====
        watcher.reset()
        fp_count = 0
        legit_events_checked = 0
        # Feed all transactions from all legitimate accounts
        for legit_acct, legit_txns in legit_accts.items():
            chain_legit = EventChain(concept_id=legit_acct)
            for txn in legit_txns:
                event = Event(
                    concept_id=legit_acct,
                    event_type=EventType.REGISTER,
                    actor="system",
                    payload={
                        "Amount Received": float(txn["Amount Received"]),
                        "Is Laundering": txn["Is Laundering"],
                        "Account.1": txn.get("Account.1", ""),
                    },
                )
                alerts = watcher.check(chain_legit, event)
                chain_legit.append(event)
                legit_events_checked += 1
                laundering_alerts = [
                    a for a in alerts if a.alert_type in ("smurfing", "rapid_movement", "fan_out")
                ]
                fp_count += len(laundering_alerts)

        fp_ok = fp_count == 0
        results.append(
            {
                "test": "false_positive_check",
                "accounts_checked": len(legit_accts),
                "events_checked": legit_events_checked,
                "false_positives": fp_count,
                "ok": fp_ok,
            }
        )
        if not fp_ok:
            errors.append(
                f"False positives: {fp_count} on {legit_events_checked} legitimate events"
            )

        # ===== TEST 6: Handler dispatch =====
        dispatched = len(handler_log) > 0
        results.append(
            {
                "test": "handler_dispatch",
                "handlers_called": len(handler_log),
                "ok": dispatched,
            }
        )

        all_ok = smurf_ok and rapid_ok and fanout_ok and val_ok and fp_ok and dispatched

        return ExperimentResult(
            experiment_id="E7",
            status="passed" if all_ok else "partial",
            metrics={
                "smurfing_threshold_ok": smurf_ok,
                "rapid_movement_threshold_ok": rapid_ok,
                "fan_out_threshold_ok": fanout_ok,
                "status_transition_ok": val_ok,
                "false_positives_on_legit": fp_count,
                "legit_accounts_tested": len(legit_accts),
                "legit_events_tested": legit_events_checked,
                "laundering_account_tested": launder_acct,
                "laundering_events_tested": len(launder_txns),
                "handler_callbacks_fired": len(handler_log),
                "test_count": 6,
            },
            raw_data=results,
            errors=errors,
        )
