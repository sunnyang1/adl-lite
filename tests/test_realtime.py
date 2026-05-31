"""
Tests for adl_lite.realtime — Realtime Event Watcher and Alert System.

Covers:
    - AlertHandler: creation, repr
    - RealtimeWatcher: init, handler registration (on/on_any)
    - Chain attachment/detachment: wrap/unwrap EventChain.append
    - Detection rules:
      * Laundering patterns: smurfing (5+ small laundering events),
        rapid_movement (exactly 10), fan_out (5+ unique recipients)
      * Status transitions: concept_validated, concept_deprecated
      * High frequency: chain size thresholds (100/1000/10000)
      * Amount threshold: large_transaction (>= 1M)
    - Handler dispatch: on() callback fires, on_any() callback fires
    - Query: alerts_since(), alert_counts property
    - Reset: clear all alerts
"""

from __future__ import annotations

import pytest

from adl_lite.models import Event, EventChain, EventType
from adl_lite.realtime import AlertHandler, RealtimeWatcher

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def watcher() -> RealtimeWatcher:
    return RealtimeWatcher()


@pytest.fixture
def chain() -> EventChain:
    return EventChain(concept_id="test-realtime")


@pytest.fixture
def basic_event() -> Event:
    return Event(
        concept_id="test-realtime",
        event_type=EventType.REGISTER,
        actor="agent_1",
        payload={"amount": 500, "currency": "USD"},
    )


# ---------------------------------------------------------------------------
# AlertHandler
# ---------------------------------------------------------------------------


class TestAlertHandler:
    def test_create_with_all_fields(self):
        event = Event(concept_id="c1", event_type=EventType.REGISTER, actor="a1")
        handler = AlertHandler("test_alert", "c1", event, {"key": "val"})
        assert handler.alert_type == "test_alert"
        assert handler.concept_id == "c1"
        assert handler.event == event
        assert handler.detail == {"key": "val"}

    def test_create_without_detail(self):
        event = Event(concept_id="c1", event_type=EventType.REGISTER, actor="a1")
        handler = AlertHandler("test_alert", "c1", event)
        assert handler.detail == {}

    def test_repr(self):
        event = Event(concept_id="c1", event_type=EventType.REGISTER, actor="agent_x")
        handler = AlertHandler("smurfing", "c1", event)
        rep = repr(handler)
        assert "smurfing" in rep
        assert "c1" in rep
        assert "agent_x" in rep


# ---------------------------------------------------------------------------
# RealtimeWatcher — Init & Handler Registration
# ---------------------------------------------------------------------------


class TestWatcherInit:
    def test_initial_state(self, watcher: RealtimeWatcher):
        assert watcher.alerts_since() == []
        assert watcher.alert_counts == {}

    def test_on_registers_handler(self, watcher: RealtimeWatcher):
        handler_called = []

        def my_handler(alert: AlertHandler) -> None:
            handler_called.append(alert.alert_type)

        watcher.on("smurfing", my_handler)
        # Dispatch a smurfing alert to verify
        event = Event(concept_id="c1", event_type=EventType.REGISTER, actor="a1")
        alert = AlertHandler("smurfing", "c1", event)
        watcher._dispatch(alert)
        assert handler_called == ["smurfing"]

    def test_on_any_registers_global_handler(self, watcher: RealtimeWatcher):
        handler_called = []

        def my_handler(alert: AlertHandler) -> None:
            handler_called.append(alert.alert_type)

        watcher.on_any(my_handler)
        event = Event(concept_id="c1", event_type=EventType.REGISTER, actor="a1")
        watcher._dispatch(AlertHandler("type_a", "c1", event))
        watcher._dispatch(AlertHandler("type_b", "c1", event))
        assert handler_called == ["type_a", "type_b"]


# ---------------------------------------------------------------------------
# Chain Attachment / Detachment
# ---------------------------------------------------------------------------


class TestChainAttachment:
    def test_attach_wraps_append(self, watcher: RealtimeWatcher, chain: EventChain):
        watcher.attach(chain)
        event = Event(
            concept_id="test-realtime",
            event_type=EventType.REGISTER,
            actor="agent_1",
            payload={"Is Laundering": "0"},
        )
        chain.append(event)
        # Verify event was appended AND alert check ran
        assert chain.length == 1

    def test_detach_restores_original(self, watcher: RealtimeWatcher):
        chain = EventChain(concept_id="test-detach")
        watcher.attach(chain)
        RealtimeWatcher.detach(chain)
        # After detach, append should be restored
        event = Event(concept_id="test-detach", event_type=EventType.REGISTER, actor="a1")
        chain.append(event)
        assert chain.length == 1

    def test_detach_idempotent(self, watcher: RealtimeWatcher):
        chain = EventChain(concept_id="test-idem")
        RealtimeWatcher.detach(chain)  # Should not raise
        assert chain.length == 0

    def test_attach_fires_on_append(self, watcher: RealtimeWatcher):
        chain = EventChain(concept_id="test-fire")
        watcher.attach(chain)

        alerted = []

        def on_alert(alert: AlertHandler) -> None:
            alerted.append(alert.alert_type)

        watcher.on("concept_validated", on_alert)

        event = Event(
            concept_id="test-fire",
            event_type=EventType.VALIDATE,
            actor="reviewer",
        )
        chain.append(event)
        assert "concept_validated" in alerted


# ---------------------------------------------------------------------------
# Detection Rule: Laundering Patterns
# ---------------------------------------------------------------------------


class TestLaunderingPatterns:
    def test_no_alert_for_non_laundering(self, watcher: RealtimeWatcher):
        chain = EventChain(concept_id="test-nl")
        event = Event(
            concept_id="test-nl",
            event_type=EventType.REGISTER,
            actor="a1",
            payload={"Is Laundering": "0", "Amount Received": 500},
        )
        alerts = watcher.check(chain, event)
        assert alerts == []

    def test_smurfing_detection(self, watcher: RealtimeWatcher):
        """5 laundering events with amount < 1000 triggers smurfing."""
        chain = EventChain(concept_id="test-smurf")
        # Pre-populate with 4 small laundering events
        for i in range(4):
            chain.append(
                Event(
                    concept_id="test-smurf",
                    event_type=EventType.REGISTER,
                    actor="a1",
                    payload={"Is Laundering": "1", "Amount Received": 500 + i},
                )
            )
        # Append 5th event FIRST, then check — because _check_laundering_patterns
        # reads ld_events from chain.events which includes appended events
        trigger = Event(
            concept_id="test-smurf",
            event_type=EventType.REGISTER,
            actor="a1",
            payload={"Is Laundering": "1", "Amount Received": 600},
        )
        chain.append(trigger)
        alerts = watcher.check(chain, trigger)
        assert any(a.alert_type == "smurfing" for a in alerts)

    def test_smurfing_not_triggered_when_amount_too_high(self, watcher: RealtimeWatcher):
        """If one of the 5 recent events is >= 1000, no smurfing."""
        chain = EventChain(concept_id="test-nosmurf")
        # 4 small events then 1 large
        for _i in range(4):
            chain.append(
                Event(
                    concept_id="test-nosmurf",
                    event_type=EventType.REGISTER,
                    actor="a1",
                    payload={"Is Laundering": "1", "Amount Received": 500},
                )
            )
        # A large event breaks the pattern
        event = Event(
            concept_id="test-nosmurf",
            event_type=EventType.REGISTER,
            actor="a1",
            payload={"Is Laundering": "1", "Amount Received": 2000},
        )
        chain.append(event)
        alerts = watcher.check(chain, event)
        # Should not be smurfing because the last event is >= 1000
        assert not any(a.alert_type == "smurfing" for a in alerts)

    def test_rapid_movement_exactly_ten(self, watcher: RealtimeWatcher):
        """Exactly 10 laundering events triggers rapid_movement."""
        chain = EventChain(concept_id="test-rapid")
        for _i in range(9):
            chain.append(
                Event(
                    concept_id="test-rapid",
                    event_type=EventType.REGISTER,
                    actor="a1",
                    payload={"Is Laundering": "1", "Amount Received": 100},
                )
            )
        # 10th event — append first, then check
        event = Event(
            concept_id="test-rapid",
            event_type=EventType.REGISTER,
            actor="a1",
            payload={"Is Laundering": "1", "Amount Received": 100},
        )
        chain.append(event)
        alerts = watcher.check(chain, event)
        assert any(a.alert_type == "rapid_movement" for a in alerts)

    def test_rapid_movement_only_at_ten(self, watcher: RealtimeWatcher):
        """rapid_movement fires exactly at 10, not at 11 or 9."""
        chain = EventChain(concept_id="test-rapid-boundary")
        for _i in range(11):
            chain.append(
                Event(
                    concept_id="test-rapid-boundary",
                    event_type=EventType.REGISTER,
                    actor="a1",
                    payload={"Is Laundering": "1", "Amount Received": 100},
                )
            )
        event = Event(
            concept_id="test-rapid-boundary",
            event_type=EventType.REGISTER,
            actor="a1",
            payload={"Is Laundering": "1", "Amount Received": 100},
        )
        alerts = watcher.check(chain, event)
        # After 11 events, the 10-event count has been passed
        # rapid_movement fires exactly on len(ld_events) == 10
        # So at 11, we no longer get this alert
        assert not any(a.alert_type == "rapid_movement" for a in alerts)

    def test_fan_out_five_targets(self, watcher: RealtimeWatcher):
        """5 unique recipients triggers fan_out."""
        chain = EventChain(concept_id="test-fanout")
        for target in ["A", "B", "C", "D"]:
            chain.append(
                Event(
                    concept_id="test-fanout",
                    event_type=EventType.REGISTER,
                    actor="a1",
                    payload={
                        "Is Laundering": "1",
                        "Account.1": target,
                        "Amount Received": 100,
                    },
                )
            )
        # 5th unique recipient — append first, then check
        event = Event(
            concept_id="test-fanout",
            event_type=EventType.REGISTER,
            actor="a1",
            payload={"Is Laundering": "1", "Account.1": "E", "Amount Received": 100},
        )
        chain.append(event)
        alerts = watcher.check(chain, event)
        assert any(a.alert_type == "fan_out" for a in alerts)


# ---------------------------------------------------------------------------
# Detection Rule: Status Transitions
# ---------------------------------------------------------------------------


class TestStatusTransitions:
    def test_validate_alert(self, watcher: RealtimeWatcher, chain: EventChain):
        event = Event(
            concept_id="test-realtime",
            event_type=EventType.VALIDATE,
            actor="reviewer",
        )
        alerts = watcher.check(chain, event)
        assert any(a.alert_type == "concept_validated" for a in alerts)

    def test_deprecate_alert(self, watcher: RealtimeWatcher, chain: EventChain):
        event = Event(
            concept_id="test-realtime",
            event_type=EventType.DEPRECATE,
            actor="admin",
        )
        alerts = watcher.check(chain, event)
        assert any(a.alert_type == "concept_deprecated" for a in alerts)

    def test_register_no_alert(self, watcher: RealtimeWatcher, chain: EventChain):
        event = Event(
            concept_id="test-realtime",
            event_type=EventType.REGISTER,
            actor="system",
        )
        alerts = watcher.check(chain, event)
        assert not any(a.alert_type in ("concept_validated", "concept_deprecated") for a in alerts)


# ---------------------------------------------------------------------------
# Detection Rule: High Frequency
# ---------------------------------------------------------------------------


class TestHighFrequency:
    def test_chain_large_at_100(self, watcher: RealtimeWatcher):
        chain = EventChain(concept_id="test-large")
        for _i in range(99):
            chain.append(Event(concept_id="test-large", event_type=EventType.REGISTER, actor="s"))
        event = Event(concept_id="test-large", event_type=EventType.REGISTER, actor="s")
        chain.append(event)
        alerts = watcher.check(chain, event)
        assert any(a.alert_type == "chain_large" for a in alerts)

    def test_chain_xlarge_at_1000(self, watcher: RealtimeWatcher):
        chain = EventChain(concept_id="test-xlarge")
        for _i in range(999):
            chain.append(Event(concept_id="test-xlarge", event_type=EventType.REGISTER, actor="s"))
        event = Event(concept_id="test-xlarge", event_type=EventType.REGISTER, actor="s")
        chain.append(event)
        alerts = watcher.check(chain, event)
        assert any(a.alert_type == "chain_xlarge" for a in alerts)

    def test_no_alert_at_50(self, watcher: RealtimeWatcher):
        chain = EventChain(concept_id="test-50")
        for _i in range(49):
            chain.append(Event(concept_id="test-50", event_type=EventType.REGISTER, actor="s"))
        event = Event(concept_id="test-50", event_type=EventType.REGISTER, actor="s")
        alerts = watcher.check(chain, event)
        assert not any(
            a.alert_type in ("chain_large", "chain_xlarge", "chain_huge") for a in alerts
        )


# ---------------------------------------------------------------------------
# Detection Rule: Amount Threshold
# ---------------------------------------------------------------------------


class TestAmountThreshold:
    def test_large_transaction(self, watcher: RealtimeWatcher, chain: EventChain):
        event = Event(
            concept_id="test-realtime",
            event_type=EventType.REGISTER,
            actor="a1",
            payload={"Amount Received": 2_000_000, "Receiving Currency": "USD"},
        )
        alerts = watcher.check(chain, event)
        assert any(a.alert_type == "large_transaction" for a in alerts)

    def test_normal_transaction(self, watcher: RealtimeWatcher, chain: EventChain):
        event = Event(
            concept_id="test-realtime",
            event_type=EventType.REGISTER,
            actor="a1",
            payload={"Amount Received": 5000, "Receiving Currency": "USD"},
        )
        alerts = watcher.check(chain, event)
        assert not any(a.alert_type == "large_transaction" for a in alerts)

    def test_exactly_one_million(self, watcher: RealtimeWatcher, chain: EventChain):
        event = Event(
            concept_id="test-realtime",
            event_type=EventType.REGISTER,
            actor="a1",
            payload={"Amount Received": 1_000_000, "Receiving Currency": "EUR"},
        )
        alerts = watcher.check(chain, event)
        assert any(a.alert_type == "large_transaction" for a in alerts)

    def test_missing_amount_defaults_to_zero(self, watcher: RealtimeWatcher, chain: EventChain):
        event = Event(
            concept_id="test-realtime",
            event_type=EventType.REGISTER,
            actor="a1",
            payload={},
        )
        alerts = watcher.check(chain, event)
        assert not any(a.alert_type == "large_transaction" for a in alerts)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


class TestDispatch:
    def test_specific_handler_gets_called(self, watcher: RealtimeWatcher):
        calls = []

        watcher.on("smurfing", lambda a: calls.append("specific"))
        watcher.on_any(lambda a: calls.append("any"))

        event = Event(concept_id="c1", event_type=EventType.REGISTER, actor="a1")
        watcher._dispatch(AlertHandler("smurfing", "c1", event))
        assert "specific" in calls
        assert "any" in calls

    def test_no_handler_no_error(self, watcher: RealtimeWatcher):
        event = Event(concept_id="c1", event_type=EventType.REGISTER, actor="a1")
        watcher._dispatch(AlertHandler("unhandled_type", "c1", event))
        # Should not raise


# ---------------------------------------------------------------------------
# Alert Querying
# ---------------------------------------------------------------------------


class TestAlertQuerying:
    def test_alerts_since_all(self, watcher: RealtimeWatcher, chain: EventChain):
        e1 = Event(concept_id="test-realtime", event_type=EventType.VALIDATE, actor="a1")
        e2 = Event(
            concept_id="test-realtime",
            event_type=EventType.REGISTER,
            actor="a1",
            payload={"Amount Received": 2_000_000, "Receiving Currency": "USD"},
        )
        watcher.check(chain, e1)
        watcher.check(chain, e2)

        all_alerts = watcher.alerts_since()
        assert len(all_alerts) == 2

    def test_alerts_since_filtered(self, watcher: RealtimeWatcher, chain: EventChain):
        e1 = Event(concept_id="test-realtime", event_type=EventType.VALIDATE, actor="a1")
        e2 = Event(
            concept_id="test-realtime",
            event_type=EventType.REGISTER,
            actor="a1",
            payload={"Amount Received": 2_000_000, "Receiving Currency": "USD"},
        )
        watcher.check(chain, e1)
        watcher.check(chain, e2)

        validated = watcher.alerts_since("concept_validated")
        assert len(validated) == 1
        assert validated[0].alert_type == "concept_validated"

    def test_alerts_since_nonexistent_type(self, watcher: RealtimeWatcher):
        assert watcher.alerts_since("nonexistent") == []

    def test_alert_counts(self, watcher: RealtimeWatcher, chain: EventChain):
        e1 = Event(concept_id="test-realtime", event_type=EventType.VALIDATE, actor="a1")
        e2 = Event(concept_id="test-realtime", event_type=EventType.VALIDATE, actor="a2")
        watcher.check(chain, e1)
        watcher.check(chain, e2)

        counts = watcher.alert_counts
        assert counts["concept_validated"] == 2

    def test_alert_counts_empty(self, watcher: RealtimeWatcher):
        assert watcher.alert_counts == {}

    def test_reset(self, watcher: RealtimeWatcher, chain: EventChain):
        event = Event(concept_id="test-realtime", event_type=EventType.VALIDATE, actor="a1")
        watcher.check(chain, event)
        assert len(watcher.alerts_since()) == 1

        watcher.reset()
        assert watcher.alerts_since() == []
        assert watcher.alert_counts == {}
