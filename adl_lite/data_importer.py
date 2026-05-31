"""ADL Lite — Data Importer (Milestone 2e)

Ingests structured data (CSV, JSON, SQL) as ADL Event objects.
Each row becomes an Event. Ontology is derived from event payloads,
not pre-defined.

Philosophy: Don't model first. Import first. The ontology emerges
from the data, not the other way around.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Event, EventChain, EventType


class DataImporter:
    """Ingest raw structured data as ADL Events."""

    def import_csv(
        self,
        path: str | Path,
        event_type: EventType,
        concept_id_field: str,
        concept_prefix: str = "",
        actor_field: str | None = None,
        timestamp_field: str | None = None,
    ) -> dict[str, EventChain]:
        """
        Import a CSV file as EventChains.

        Args:
            path: CSV file path
            event_type: EventType for all rows (e.g., SUBMITTED for transactions)
            concept_id_field: Column used as concept_id (e.g., 'Account')
            concept_prefix: Optional prefix for concept IDs
            actor_field: Column used as actor (default: 'system')
            timestamp_field: Column used as timestamp (default: now)

        Returns:
            dict mapping concept_id → EventChain
        """
        chains: dict[str, EventChain] = {}

        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                concept_id = row.get(concept_id_field, "")
                if concept_prefix and not concept_id.startswith(concept_prefix):
                    concept_id = f"{concept_prefix}{concept_id}"

                if concept_id not in chains:
                    chains[concept_id] = EventChain(concept_id=concept_id)

                actor = row.get(actor_field, "system") if actor_field else "system"
                ts = row.get(timestamp_field, "") if timestamp_field else ""
                if not ts:
                    ts = datetime.now(timezone.utc).isoformat()

                event = Event(
                    concept_id=concept_id,
                    event_type=event_type,
                    actor=actor,
                    timestamp=ts,
                    payload=dict(row),
                )
                chains[concept_id].append(event)

        return chains

    def import_json_events(self, path: str | Path) -> list[Event]:
        """Import a JSON Lines file where each line is an Event dict."""
        events: list[Event] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    events.append(Event(**data))
        return events

    # ------------------------------------------------------------------
    # Ontology discovery (derived from events, not pre-defined)
    # ------------------------------------------------------------------

    @staticmethod
    def discover_classes(
        chains: dict[str, EventChain],
        id_field_pattern: str = "_id",
        *,
        smart: bool = False,
    ) -> list[str]:
        """
        Discover entity classes from event payload fields.

        Two modes:
          - Default (_id suffix): Any field ending with `id_field_pattern`.
            Fast, precise on clean schemas, fails on dot-notation (e.g., "Account.1").
          - Smart mode (smart=True): Multi-strategy heuristic combining:
            (a) _id suffix fields (existing)
            (b) Cardinality filtering: fields with 15-500 unique values,
                representing 2-50% of total rows → entity-like
            (c) Paired columns: "X" and "X.1" → entity "X" (sender/receiver)
            (d) Common entity-indicator column names
        """
        classes: set[str] = set()

        # Strategy (a): _id suffix fields
        for chain in chains.values():
            for event in chain.events:
                for field in event.payload:
                    if field.lower().endswith(id_field_pattern):
                        class_name = field.replace("_id", "").replace(".", "_").title()
                        classes.add(class_name)

        if smart:
            from collections import Counter

            total_events = sum(c.length for c in chains.values())

            # Strategy (b): cardinality-based detection
            field_cardinality: dict[str, Counter] = {}
            for chain in chains.values():
                for event in chain.events:
                    for field, value in event.payload.items():
                        if field not in field_cardinality:
                            field_cardinality[field] = Counter()
                        field_cardinality[field][value] += 1

            for field, counter in field_cardinality.items():
                n_unique = len(counter)
                uniqueness_ratio = n_unique / total_events
                # Entity columns: moderate cardinality (not too few, not too many)
                if 15 <= n_unique <= 500 and 0.02 <= uniqueness_ratio <= 0.50:
                    # Exclude obvious non-entity columns
                    lower = field.lower()
                    if not any(
                        keyword in lower
                        for keyword in ("amount", "currency", "timestamp", "date", "time")
                    ):
                        # Normalize dot-notation: "Account.1" → "Account"
                        base = field.split(".")[0] if "." in field else field
                        class_name = base.replace(".", "_").title()
                        classes.add(class_name)

            # Strategy (c): paired columns pattern (e.g., Account / Account.1)
            paired_bases: set[str] = set()
            all_fields = set(field_cardinality.keys())
            for field in all_fields:
                if "." in field:
                    base = field.split(".")[0]
                    if base in all_fields:
                        paired_bases.add(base)
            for base in paired_bases:
                class_name = base.replace(".", "_").title()
                classes.add(class_name)

            # Strategy (d): common entity indicator names (whole-word match only)
            entity_indicators = {
                "account",
                "bank",
                "customer",
                "merchant",
                "branch",
                "user",
                "agent",
                "counterparty",
                "beneficiary",
            }
            # Directional prefixes to strip for normalization
            _directional_prefixes = {"from ", "to ", "sending ", "receiving ", "source ", "target "}
            for field in field_cardinality:
                lower = field.lower().strip()
                # Strip directional prefixes: "From Bank" → "Bank"
                normalized = lower
                for prefix in _directional_prefixes:
                    if lower.startswith(prefix):
                        normalized = lower[len(prefix) :]
                        break
                for indicator in entity_indicators:
                    if normalized == indicator:
                        class_name = indicator.title()
                        classes.add(class_name)
                        break

        return sorted(classes)

    @staticmethod
    def discover_links(chains: dict[str, EventChain]) -> list[tuple[str, str, str]]:
        """
        Discover relationships from co-occurring fields in event payloads.

        Returns list of (source_class, predicate, target_class) tuples.
        """
        field_pairs: Counter = Counter()
        for chain in chains.values():
            for event in chain.events:
                id_fields = [k for k in event.payload if k.lower().endswith("_id")]
                for i in range(len(id_fields)):
                    for j in range(i + 1, len(id_fields)):
                        pair = (id_fields[i], id_fields[j])
                        field_pairs[pair] += 1

        links = []
        seen = set()
        for (f1, f2), count in field_pairs.most_common(50):
            if count < 2:
                continue
            key = tuple(sorted([f1, f2]))
            if key in seen:
                continue
            seen.add(key)
            src = f1.replace("_id", "").replace(".", "_").title()
            tgt = f2.replace("_id", "").replace(".", "_").title()
            links.append((src, f"{f1}-to-{f2}", tgt))

        return links

    @staticmethod
    def summary(chains: dict[str, EventChain]) -> dict[str, Any]:
        """Compute summary statistics over imported event chains."""
        total_events = sum(c.length for c in chains.values())
        total_chains = len(chains)
        return {
            "total_chains": total_chains,
            "total_events": total_events,
            "avg_chain_length": round(total_events / total_chains, 1) if total_chains else 0,
            "classes": DataImporter.discover_classes(chains),
            "links": DataImporter.discover_links(chains),
        }
