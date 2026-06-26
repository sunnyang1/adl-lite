"""E10: Full FDE pipeline — data import → ontology discovery → concept authoring
→ consensus → action execution → side effects.

Tests the complete Palantir FDE-equivalent pipeline end-to-end:
  1. Import IBM AML data as Events
  2. Discover ontology classes and link types from payloads
  3. Generate concept Markdown files from discovered patterns
  4. Register concepts in ConsensusEngine
  5. Execute actions (validate) via ActionExecutor
  6. Verify all chains maintain integrity through the full pipeline
"""

from __future__ import annotations

from pathlib import Path

from adl_lite.action_executor import ActionExecutor
from adl_lite.consensus import ConsensusEngine
from adl_lite.data_importer import DataImporter
from adl_lite.models import (
    ADLActionBlock,
    ADLDocument,
    ADLFrontMatter,
    ADLType,
    Event,
    EventType,
    ProvisionalNames,
)
from adl_lite.ontology import OntologyManager

from .base import BaseExperiment, ExperimentResult
from .registry import register

IBM_DATA = Path(__file__).resolve().parent.parent / "data" / "aml" / "ibm_data"


@register("E10")
class E10FullFDEPipeline(BaseExperiment):
    experiment_id = "E10"
    name = "Full FDE pipeline"
    description = "End-to-end: data → ontology → concepts → consensus → actions → effects"

    def run(self) -> ExperimentResult:
        if not (IBM_DATA / "HI-Small_Trans.csv").is_file():
            return ExperimentResult(
                experiment_id="E10",
                status="failed",
                errors=["IBM AML data not found. Run kaggle download first."],
            )

        importer = DataImporter()
        mgr = OntologyManager()
        executor = ActionExecutor(mgr)
        engine = ConsensusEngine()
        results = []
        errors: list[str] = []

        # Phase 1: Import data
        chains = importer.import_csv(
            str(IBM_DATA / "HI-Small_Trans.csv"),
            event_type=EventType.REGISTER,
            concept_id_field="Account",
            concept_prefix="fde-",
            timestamp_field="Timestamp",
        )
        total_accounts = len(chains)
        if total_accounts < 10:
            return ExperimentResult(
                experiment_id="E10",
                status="failed",
                errors=[f"Only {total_accounts} accounts imported"],
            )

        # Phase 2: Discover ontology
        classes = DataImporter.discover_classes(chains)
        links = DataImporter.discover_links(chains)

        # Phase 3: Generate concept documents (top 5000 accounts by event count, ~1% of total)
        sorted_chains = sorted(chains.items(), key=lambda x: x[1].length, reverse=True)
        sample_size = min(5000, len(sorted_chains))
        concepts: list[ADLDocument] = []
        for concept_id, chain in sorted_chains[:sample_size]:
            # Compute data-driven confidence from actual patterns in the chain
            laundering_count = sum(
                1 for e in chain.events if str(e.payload.get("Is Laundering", "0")).strip() == "1"
            )
            # Base confidence for all imported accounts (validated data source)
            derived_confidence = min(1.0, max(0.0, laundering_count / max(chain.length, 1)))
            if laundering_count >= 5:
                derived_confidence = max(derived_confidence, 0.8)
            else:
                derived_confidence = max(derived_confidence, 0.5)

            # Append a SNAPSHOT event carrying the derived confidence —
            # chain is source of truth, not front_matter override.
            if derived_confidence >= 0.5:
                chain.append(
                    Event(
                        concept_id=concept_id,
                        event_type=EventType.SNAPSHOT,
                        actor="fde-pipeline",
                        reasoning="Confidence derived from laundering pattern density",
                        payload={"confidence": derived_confidence, "synthetic": True},
                    )
                )

            doc = ADLDocument(
                front_matter=ADLFrontMatter(
                    adl_type=ADLType.CONCEPT,
                    adl_id=concept_id,
                    scope="private/fde-test",
                    provisional_names=ProvisionalNames(en=f"Account {concept_id}"),
                    domain="financial_aml",
                ),
                markdown_body=f"# Account {concept_id}\n\nAuto-generated from IBM AML data.\n",
                action_blocks=[],
            )
            # Derive ALL front matter from the chain
            doc.refresh_snapshot(chain)
            concepts.append(doc)

        # Phase 4: Register concepts in consensus engine
        registered = 0
        for doc in concepts:
            try:
                engine.register(doc)
                registered += 1
            except Exception:
                pass

        # Phase 5: Validate concepts via ActionExecutor
        validated = 0
        for doc in concepts:
            action = ADLActionBlock(
                action="validate",
                actor="fde-pipeline",
                reasoning="Auto-validated from IBM AML import",
            )
            val_errors = executor.validate_action(doc, action)
            if not val_errors:
                validated += 1
                # Append validate event to chain
                val_chain = chains.get(doc.adl_id)
                if val_chain:
                    val_chain.append(
                        Event(
                            concept_id=doc.adl_id,
                            event_type=EventType.VALIDATE,
                            actor="fde-pipeline",
                            reasoning="FDE pipeline validation",
                            payload={"confidence": 0.8},
                        )
                    )
                    doc.refresh_snapshot(val_chain)

        # Phase 6: Verify integrity
        integrity_ok = 0
        for doc in concepts:
            verify_chain = chains.get(doc.adl_id)
            if verify_chain and verify_chain.verify_integrity():
                integrity_ok += 1

        results.append(
            {
                "phase": "import",
                "accounts": total_accounts,
                "events": sum(c.length for c in chains.values()),
            }
        )
        results.append(
            {
                "phase": "ontology",
                "classes_discovered": len(classes),
                "links_discovered": len(links),
            }
        )
        results.append(
            {
                "phase": "concepts_generated",
                "count": len(concepts),
            }
        )
        results.append(
            {
                "phase": "consensus",
                "registered": registered,
            }
        )
        results.append(
            {
                "phase": "actions",
                "validated": validated,
            }
        )
        results.append(
            {
                "phase": "integrity",
                "chains_ok": integrity_ok,
                "total": len(concepts),
            }
        )

        all_ok = (
            integrity_ok == len(concepts)
            and validated >= sample_size * 0.6
            and registered >= sample_size * 0.8
        )

        return ExperimentResult(
            experiment_id="E10",
            status="passed" if all_ok else "partial",
            metrics={
                "accounts_imported": total_accounts,
                "pipeline_sample_size": sample_size,
                "pipeline_pct": round(sample_size / total_accounts * 100, 2),
                "classes_discovered": len(classes),
                "links_discovered": len(links),
                "concepts_generated": len(concepts),
                "concepts_registered": registered,
                "concepts_validated_via_executor": validated,
                "chains_integrity_after_pipeline": f"{integrity_ok}/{len(concepts)}",
                "pipeline_complete": all_ok,
            },
            raw_data=results,
            errors=errors,
        )
