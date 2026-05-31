"""E6: IBM AML data → EventChain → Ontology Discovery pipeline.

End-to-end: import transactions as events, discover object types and link
types from event payloads, detect laundering patterns, verify import integrity
of freshly-constructed chains (not tamper detection), and cross-reference with
existing AML concept files.
"""

from __future__ import annotations

from pathlib import Path

from adl_lite.data_importer import DataImporter
from adl_lite.models import EventChain, EventType

from .base import BaseExperiment, ExperimentResult
from .registry import register

IBM_DATA = Path(__file__).resolve().parent.parent / "data" / "aml" / "ibm_data"
AML_CONCEPTS = Path(__file__).resolve().parent.parent / "data" / "aml" / "concepts"

PATTERN_TO_CONCEPT = {
    "smurfing_threshold": "aml-smurfing",
    "high_frequency": "aml-rapid-move",
    "fan_out": "aml-fan-out-pattern",
    "cyclic": "aml-cyclic-pattern",
}


@register("E6")
class E6AMLPipeline(BaseExperiment):
    experiment_id = "E6"
    name = "IBM AML data → ontology pipeline"
    description = "Import AML txns as Events, discover ontology, detect patterns"

    def run(self) -> ExperimentResult:
        csv_path = IBM_DATA / "HI-Small_Trans.csv"
        if not csv_path.is_file():
            return ExperimentResult(
                experiment_id="E6",
                status="failed",
                errors=[f"Data file not found: {csv_path}"],
            )

        importer = DataImporter()

        # 1. Import: each account → EventChain with all its transactions
        chains = importer.import_csv(
            str(csv_path),
            event_type=EventType.REGISTER,
            concept_id_field="Account",
            concept_prefix="acct-",
            timestamp_field="Timestamp",
        )
        n_chains = len(chains)
        n_events = sum(c.length for c in chains.values())

        # 2. Discover ontology from event payloads
        classes = DataImporter.discover_classes(chains)
        links = DataImporter.discover_links(chains)

        # 3. Flag suspicious accounts (any laundering event)
        suspicious: dict[str, EventChain] = {}
        laundering_count = 0
        for cid, chain in chains.items():
            has = any(str(e.payload.get("Is Laundering", "0")).strip() == "1" for e in chain.events)
            if has:
                suspicious[cid] = chain
                laundering_count += sum(
                    1
                    for e in chain.events
                    if str(e.payload.get("Is Laundering", "0")).strip() == "1"
                )

        # 4. Chain integrity check (suspicious chains are the critical ones)
        suspicious_integrity = sum(1 for c in suspicious.values() if c.verify_integrity())
        total_integrity = sum(1 for c in chains.values() if c.verify_integrity())

        # 5. Detect laundering patterns from event sequences
        patterns = self._detect_patterns(suspicious)
        concepts_matched = self._match_concepts(patterns)

        # 6. Summary by suspicious account (top 20)
        raw = []
        for acct_id, chain in list(suspicious.items())[:20]:
            ld = sum(
                1 for e in chain.events if str(e.payload.get("Is Laundering", "0")).strip() == "1"
            )
            acct_patterns = patterns.get(acct_id, [])
            raw.append(
                {
                    "account": acct_id,
                    "chain_length": chain.length,
                    "integrity_ok": chain.verify_integrity(),
                    "laundering_events": ld,
                    "laundering_pct": round(ld / max(chain.length, 1), 3),
                    "detected_patterns": acct_patterns,
                    "matched_concepts": [
                        PATTERN_TO_CONCEPT[p] for p in acct_patterns if p in PATTERN_TO_CONCEPT
                    ],
                }
            )

        all_ok = suspicious_integrity == len(suspicious) and total_integrity == n_chains

        return ExperimentResult(
            experiment_id="E6",
            status="passed" if all_ok else "partial",
            metrics={
                "total_accounts": n_chains,
                "total_transactions": n_events,
                "avg_txns_per_account": round(n_events / n_chains, 1),
                "chains_import_integrity": f"{total_integrity}/{n_chains}",
                "suspicious_accounts": len(suspicious),
                "suspicious_chains_import_integrity": f"{suspicious_integrity}/{len(suspicious)}",
                "laundering_events_total": laundering_count,
                "laundering_pct": round(laundering_count / n_events * 100, 2) if n_events else 0,
                "discovered_classes": ", ".join(classes[:8]),
                "discovered_links": ", ".join(f"{s}-{t}" for s, _, t in links[:5]),
                "detected_pattern_count": len(patterns),
                "concepts_matched": ", ".join(concepts_matched),
            },
            raw_data=raw,
        )

    @staticmethod
    def _detect_patterns(
        suspicious: dict[str, EventChain],
    ) -> dict[str, list[str]]:
        patterns: dict[str, list[str]] = {}
        for acct_id, chain in suspicious.items():
            detected: list[str] = []
            ld_events = [
                e for e in chain.events if str(e.payload.get("Is Laundering", "0")).strip() == "1"
            ]
            amounts = [float(e.payload.get("Amount Received", 0)) for e in ld_events]
            targets = set()
            for e in ld_events:
                tgt = e.payload.get("Account.1", "")
                if tgt:
                    targets.add(tgt)

            if len(amounts) >= 5 and all(a < 1000 for a in amounts[-5:]):
                detected.append("smurfing_threshold")
            if len(ld_events) >= 10:
                detected.append("high_frequency")
            if len(targets) >= 5:
                detected.append("fan_out")

            senders = set()
            receivers = set()
            for e in chain.events:
                senders.add(e.payload.get("Account", ""))
                receivers.add(e.payload.get("Account.1", ""))
            if senders & receivers:
                detected.append("cyclic")

            if detected:
                patterns[acct_id] = detected

        return patterns

    @staticmethod
    def _match_concepts(patterns: dict[str, list[str]]) -> list[str]:
        concepts: set[str] = set()
        for pat_list in patterns.values():
            for p in pat_list:
                c = PATTERN_TO_CONCEPT.get(p)
                if c:
                    concepts.add(c)
        return sorted(concepts)
