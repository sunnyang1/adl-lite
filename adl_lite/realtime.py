"""ADL Lite — Realtime Event Watcher for Capability Registry

Triggers pattern detection on every newly appended event.
Connects to EventChain.append() to fire alerts without batch processing.

Philosophy: Event-first means detection should happen at the moment
an event is appended, not when a batch job runs.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from .logging_config import get_logger
from .models import Event, EventChain, EventType

logger = get_logger(__name__)


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
        return f"Alert({self.alert_type}, concept={self.concept_id}, actor={self.event.actor})"


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
        self._handlers: dict[str, list[Callable[[AlertHandler], None]]] = defaultdict(list)
        self._alerts: list[AlertHandler] = []
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def on(
        self,
        alert_type: str,
        handler: Callable[[AlertHandler], None],
    ) -> None:
        """Register a callback for a specific alert type. Thread-safe."""
        with self._lock:
            self._handlers[alert_type].append(handler)

    def on_any(
        self,
        handler: Callable[[AlertHandler], None],
    ) -> None:
        """Register a callback for all alert types. Thread-safe."""
        with self._lock:
            self._handlers["*"].append(handler)

    # ------------------------------------------------------------------
    # Chain attachment (auto-fire on append)
    # ------------------------------------------------------------------

    def attach(self, chain: EventChain) -> EventChain:
        """
        Wrap a chain so that every append() triggers detection.

        Supports stacking: multiple watchers can attach to the same chain.
        Each watcher's wrapper calls the previous watcher's wrapper (or the
        original append if this is the first).
        """
        # Save the current append as the "previous" in the chain
        previous_append = chain.append

        # Store in a stack on the chain itself so detach() can unwind
        if not hasattr(chain, "_wrapped_appends"):
            chain._wrapped_appends = []  # type: ignore[attr-defined]
        chain._wrapped_appends.append(previous_append)  # type: ignore[attr-defined]

        def _wrapped_append(event: Event) -> None:
            previous_append(event)
            self.check(chain, event)

        chain.append = _wrapped_append  # type: ignore[method-assign]
        return chain

    @staticmethod
    def detach(chain: EventChain) -> None:
        """Restore the append from before the most recent attach()."""
        if hasattr(chain, "_wrapped_appends") and chain._wrapped_appends:  # type: ignore[attr-defined]
            chain.append = chain._wrapped_appends.pop()  # type: ignore[attr-defined, method-assign]
        elif hasattr(chain, "_original_append"):
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

        with self._lock:
            self._alerts.extend(alerts)
        for alert in alerts:
            logger.info(
                "Alert raised: %s on concept %s (actor=%s)",
                alert.alert_type,
                alert.concept_id,
                event.actor,
            )
            self._dispatch(alert)

        return alerts

    # ------------------------------------------------------------------
    # Detection rules (private)
    # ------------------------------------------------------------------

    @staticmethod
    def _check_laundering_patterns(chain: EventChain, event: Event) -> list[AlertHandler]:
        """Detect AML patterns from laundering-flagged events."""
        alerts: list[AlertHandler] = []
        is_laundering = str(event.payload.get("Is Laundering", "0")).strip()
        if is_laundering != "1":
            return alerts

        ld_events = [
            e for e in chain.events if str(e.payload.get("Is Laundering", "0")).strip() == "1"
        ]

        # Smurfing: at least 5 recent laundering events, ALL under $1,000
        # Uses a sliding window over the 5 most recent laundering events.
        # Fires on first window formation and again when the pattern re-emerges
        # after being broken by a large transaction.
        amounts = [float(e.payload.get("Amount Received", 0)) for e in ld_events]
        window_size = 5
        if len(amounts) >= window_size:
            recent_window = amounts[-window_size:]
            if all(a < 1000 for a in recent_window):
                # Only fire if this is the first time the window qualifies, or if
                # the previous window did NOT qualify (pattern re-emerged).
                prev_window = amounts[-(window_size + 1) : -1] if len(amounts) > window_size else []
                should_fire = len(prev_window) < window_size or not all(
                    a < 1000 for a in prev_window
                )
                if should_fire:
                    alerts.append(
                        AlertHandler(
                            "smurfing",
                            chain.concept_id,
                            event,
                            {
                                "event_count": len(ld_events),
                                "window_size": window_size,
                                "window_avg_amount": round(
                                    sum(recent_window) / len(recent_window), 2
                                ),
                            },
                        )
                    )

        # Rapid movement: 10+ laundering events
        if len(ld_events) == 10:  # fire exactly on threshold cross
            alerts.append(
                AlertHandler(
                    "rapid_movement",
                    chain.concept_id,
                    event,
                    {"event_count": len(ld_events)},
                )
            )

        # Fan-out: 5+ unique recipients
        targets = set()
        for e in ld_events:
            tgt = e.payload.get("Account.1", "")
            if tgt:
                targets.add(tgt)
        if len(targets) == 5:
            alerts.append(
                AlertHandler(
                    "fan_out",
                    chain.concept_id,
                    event,
                    {"unique_targets": len(targets)},
                )
            )

        return alerts

    @staticmethod
    def _check_status_transition(chain: EventChain, event: Event) -> list[AlertHandler]:
        """Alert on status transitions between certain thresholds."""
        alerts: list[AlertHandler] = []

        if event.event_type == EventType.VALIDATE:
            alerts.append(
                AlertHandler(
                    "concept_validated",
                    chain.concept_id,
                    event,
                    {"new_status": "validated", "actor": event.actor},
                )
            )
        elif event.event_type == EventType.DEPRECATE:
            alerts.append(
                AlertHandler(
                    "concept_deprecated",
                    chain.concept_id,
                    event,
                    {"new_status": "deprecated", "actor": event.actor},
                )
            )

        return alerts

    @staticmethod
    def _check_high_frequency(chain: EventChain, event: Event) -> list[AlertHandler]:
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
                alerts.append(
                    AlertHandler(
                        label,
                        chain.concept_id,
                        event,
                        {"chain_length": size},
                    )
                )

        return alerts

    @staticmethod
    def _check_amount_threshold(chain: EventChain, event: Event) -> list[AlertHandler]:
        """Alert on unusually large transaction amounts."""
        alerts: list[AlertHandler] = []
        amount = float(event.payload.get("Amount Received", 0))

        if amount >= 1_000_000:
            alerts.append(
                AlertHandler(
                    "large_transaction",
                    chain.concept_id,
                    event,
                    {"amount": amount, "currency": event.payload.get("Receiving Currency", "?")},
                )
            )
        return alerts

    # ------------------------------------------------------------------
    # Dispatch + query
    # ------------------------------------------------------------------

    def _dispatch(self, alert: AlertHandler) -> None:
        """Fire registered handlers for this alert type. Thread-safe."""
        with self._lock:
            handlers = self._handlers.get(alert.alert_type, []) + self._handlers.get("*", [])
        logger.debug(
            "Dispatching alert %s for concept %s to %d handler(s)",
            alert.alert_type,
            alert.concept_id,
            len(handlers),
        )
        for handler in handlers:
            handler(alert)

    def alerts_since(self, alert_type: str | None = None) -> list[AlertHandler]:
        """All alerts collected since watcher creation, optionally filtered."""
        with self._lock:
            if alert_type is None:
                return list(self._alerts)
            return [a for a in self._alerts if a.alert_type == alert_type]

    @property
    def alert_counts(self) -> dict[str, int]:
        with self._lock:
            counts: dict[str, int] = {}
            for a in self._alerts:
                counts[a.alert_type] = counts.get(a.alert_type, 0) + 1
            return dict(sorted(counts.items()))

    def reset(self) -> None:
        with self._lock:
            self._alerts.clear()
