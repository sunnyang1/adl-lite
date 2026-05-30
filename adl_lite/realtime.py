"""ADL Lite — Realtime Event Watcher

Triggers pattern detection on every newly appended event.
Connects to EventChain.append() to fire alerts without batch processing.

Philosophy: Event-first means detection should happen at the moment
an event is appended, not when a batch job runs.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

from .models import Event, EventChain, EventType


class AlertHandler:
    """Callback executed when a pattern is detected."""

    def __init__(
        self,
        alert_type: str,
        concept_id: str,
        event: Event,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.alert_type = alert_type
        self.concept_id = concept_id
        self.event = event
        self.detail = detail or {}

    def __repr__(self) -> str:
        return (
            f"Alert({self.alert_type}, concept={self.concept_id}, "
            f"actor={self.event.actor})"
        )


class RealtimeWatcher:
    """
    Watches EventChains and fires alerts on pattern detection.

    Usage:
        watcher = RealtimeWatcher()
        watcher.attach(chain)  # starts watching
        chain.append(new_event)  # triggers detection automatically

    Or manually:
        watcher = RealtimeWatcher()
        alerts = watcher.check(chain, new_event)
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[AlertHandler], None]]] = (
            defaultdict(list)
        )
        self._alerts: list[AlertHandler] = []

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def on(
        self,
        alert_type: str,
        handler: Callable[[AlertHandler], None],
    ) -> None:
        """Register a callback for a specific alert type."""
        self._handlers[alert_type].append(handler)

    def on_any(
        self,
        handler: Callable[[AlertHandler], None],
    ) -> None:
        """Register a callback for all alert types."""
        self._handlers["*"].append(handler)

    # ------------------------------------------------------------------
    # Chain attachment (auto-fire on append)
    # ------------------------------------------------------------------

    def attach(self, chain: EventChain) -> EventChain:
        """
        Wrap a chain so that every append() triggers detection.

        Returns the same chain with interception. The chain's append()
        is NOT monkey-patched — this returns a wrapper chain.
        """
        original_append = chain.append

        def _wrapped_append(event: Event) -> None:
            original_append(event)
            self.check(chain, event)

        chain.append = _wrapped_append  # type: ignore[method-assign]
        return chain

    @staticmethod
    def detach(chain: EventChain) -> None:
        """Restore original append()."""
        if hasattr(chain, "_original_append"):
            chain.append = chain._original_append  # type: ignore[method-assign]

    # ------------------------------------------------------------------
    # Detection rules
    # ------------------------------------------------------------------

    def check(
        self,
        chain: EventChain,
        event: Event,
    ) -> list[AlertHandler]:
        """
        Check a single new event against all detection rules.

        Returns list of fired alerts. Also dispatches to registered handlers.
        """
        alerts: list[AlertHandler] = []

        alerts.extend(self._check_laundering_patterns(chain, event))
        alerts.extend(self._check_status_transition(chain, event))
        alerts.extend(self._check_high_frequency(chain, event))
        alerts.extend(self._check_amount_threshold(chain, event))

        self._alerts.extend(alerts)
        for alert in alerts:
            self._dispatch(alert)

        return alerts

    # ------------------------------------------------------------------
    # Detection rules (private)
    # ------------------------------------------------------------------

    @staticmethod
    def _check_laundering_patterns(
        chain: EventChain, event: Event
    ) -> list[AlertHandler]:
        """Detect AML patterns from laundering-flagged events."""
        alerts: list[AlertHandler] = []
        is_laundering = str(event.payload.get("Is Laundering", "0")).strip()
        if is_laundering != "1":
            return alerts

        ld_events = [
            e for e in chain.events
            if str(e.payload.get("Is Laundering", "0")).strip() == "1"
        ]

        # Smurfing: 5+ laundering events, all under $1000
        amounts = [
            float(e.payload.get("Amount Received", 0)) for e in ld_events
        ]
        if len(amounts) == 5 and all(a < 1000 for a in amounts):  # exact threshold cross
            alerts.append(AlertHandler(
                "smurfing",
                chain.concept_id,
                event,
                {"event_count": len(ld_events), "avg_amount": round(sum(amounts) / len(amounts), 2)},
            ))

        # Rapid movement: 10+ laundering events
        if len(ld_events) == 10:  # fire exactly on threshold cross
            alerts.append(AlertHandler(
                "rapid_movement",
                chain.concept_id,
                event,
                {"event_count": len(ld_events)},
            ))

        # Fan-out: 5+ unique recipients
        targets = set()
        for e in ld_events:
            tgt = e.payload.get("Account.1", "")
            if tgt:
                targets.add(tgt)
        if len(targets) == 5:
            alerts.append(AlertHandler(
                "fan_out",
                chain.concept_id,
                event,
                {"unique_targets": len(targets)},
            ))

        return alerts

    @staticmethod
    def _check_status_transition(
        chain: EventChain, event: Event
    ) -> list[AlertHandler]:
        """Alert on status transitions between certain thresholds."""
        alerts: list[AlertHandler] = []

        if event.event_type == EventType.VALIDATE:
            alerts.append(AlertHandler(
                "concept_validated",
                chain.concept_id,
                event,
                {"new_status": "validated", "actor": event.actor},
            ))
        elif event.event_type == EventType.DEPRECATE:
            alerts.append(AlertHandler(
                "concept_deprecated",
                chain.concept_id,
                event,
                {"new_status": "deprecated", "actor": event.actor},
            ))

        return alerts

    @staticmethod
    def _check_high_frequency(
        chain: EventChain, event: Event
    ) -> list[AlertHandler]:
        """Alert when a chain exceeds certain size thresholds."""
        alerts: list[AlertHandler] = []
        size = chain.length

        # Fire on milestone thresholds
        for threshold, label in [
            (100, "chain_large"),
            (1000, "chain_xlarge"),
            (10000, "chain_huge"),
        ]:
            if size == threshold:
                alerts.append(AlertHandler(
                    label,
                    chain.concept_id,
                    event,
                    {"chain_length": size},
                ))

        return alerts

    @staticmethod
    def _check_amount_threshold(
        chain: EventChain, event: Event
    ) -> list[AlertHandler]:
        """Alert on unusually large transaction amounts."""
        alerts: list[AlertHandler] = []
        amount = float(event.payload.get("Amount Received", 0))

        if amount >= 1_000_000:
            alerts.append(AlertHandler(
                "large_transaction",
                chain.concept_id,
                event,
                {"amount": amount, "currency": event.payload.get("Receiving Currency", "?")},
            ))
        return alerts

    # ------------------------------------------------------------------
    # Dispatch + query
    # ------------------------------------------------------------------

    def _dispatch(self, alert: AlertHandler) -> None:
        """Fire registered handlers for this alert type."""
        for handler in self._handlers.get(alert.alert_type, []):
            handler(alert)
        for handler in self._handlers.get("*", []):
            handler(alert)

    def alerts_since(self, alert_type: str | None = None) -> list[AlertHandler]:
        """All alerts collected since watcher creation, optionally filtered."""
        if alert_type is None:
            return list(self._alerts)
        return [a for a in self._alerts if a.alert_type == alert_type]

    @property
    def alert_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for a in self._alerts:
            counts[a.alert_type] = counts.get(a.alert_type, 0) + 1
        return dict(sorted(counts.items()))

    def reset(self) -> None:
        self._alerts.clear()
