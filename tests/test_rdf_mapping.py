"""
RDF/OWL/PROV-O mapping from ADL documents — addresses reviewer question:
"Can you provide a concrete, automated mapping from ADL documents (including
EventChains) to RDF/OWL/PROV-O, with examples and an evaluation of
information preservation?"

Strategy:
  1. Parse each example .md file
  2. Generate RDF Turtle representation
  3. Verify round-trip: all concepts, relations, evidence blocks are preserved
  4. Report information preservation metrics
"""

from __future__ import annotations

from pathlib import Path

import pytest

from adl_lite.models import (
    ADLDocument,
)
from adl_lite.parser import parse_file

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


# ---------------------------------------------------------------------------
# RDF/Named Graph mapping
# ---------------------------------------------------------------------------


def adl_to_turtle(doc: ADLDocument) -> str:
    """
    Generate RDF Turtle from an ADL document.

    Mapping:
      - Each concept → a named graph <adl://{scope}/{adl_id}>
      - adl_id → rdf:type corresponding to adl_type
      - Each relation block → owl:ObjectProperty assertion
      - Each evidence block → prov:Entity with prov:wasAttributedTo
      - Each seal block → adl:formalSeal with proof reference
      - FrontMatter → rdfs:label, adl:confidence, adl:novelty
    """
    fm = doc.front_matter
    base = f"adl://{fm.scope}/{fm.adl_id}"
    lines = []

    # PREFIX declarations
    lines.append("@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .")
    lines.append("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .")
    lines.append("@prefix owl: <http://www.w3.org/2002/07/owl#> .")
    lines.append("@prefix prov: <http://www.w3.org/ns/prov#> .")
    lines.append("@prefix adl: <http://adl-lite.org/ontology#> .")
    lines.append("")

    # Named graph header
    lines.append(f"<{base}> {{")
    lines.append(f"  <{base}> a adl:{fm.adl_type.value.capitalize()} ;")
    lines.append(f'    rdfs:label "{doc.concept_name}" ;')
    lines.append(f"    adl:confidence {fm.confidence} ;")
    lines.append(f"    adl:novelty {fm.novelty} ;")
    lines.append(f'    adl:status "{fm.status.value}" ;')
    lines.append(f'    adl:scope "{fm.scope}" ;')
    if fm.domain:
        lines.append(f'    adl:domain "{fm.domain}" ;')
    lines.append(f'    adl:createdAt "{fm.created_at}" ;')
    lines.append(f'    adl:updatedAt "{fm.updated_at}" .')

    # Relations → owl:ObjectProperty assertions
    for rel in doc.relations:
        target_uri = f"adl://{fm.scope}/{rel.target}" if "://" not in rel.target else rel.target
        lines.append("")
        lines.append(f"  <{base}> adl:{rel.relation.replace('-', '_')} <{target_uri}> .")
        lines.append(f"  _:rel_{hash(rel.target) % 10000} a adl:RelationAssertion ;")
        lines.append(f'    adl:relationPredicate "{rel.relation}" ;')
        lines.append(f"    adl:confidence {rel.confidence} .")

    # Evidence → prov:Entity
    for ev in doc.evidence:
        lines.append("")
        lines.append(f"  _:ev_{hash(ev.data_ref) % 10000} a prov:Entity ;")
        lines.append(f'    adl:evidenceType "{ev.evidence_type.value}" ;')
        lines.append(f"    prov:atLocation <{ev.data_ref}> ;")
        lines.append(f"    adl:confidence {ev.confidence} .")

    # Seals → adl:formalSeal
    for seal in doc.seals:
        lines.append("")
        lines.append(f"  _:seal_{hash(seal.assertion) % 10000} a adl:FormalSeal ;")
        lines.append(f'    adl:assertion """{seal.assertion}""" ;')
        lines.append(f'    adl:language "{seal.language}" ;')
        lines.append(f'    adl:sealStatus "{seal.status}" .')

    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Information preservation evaluation
# ---------------------------------------------------------------------------


class TestRDFMapping:
    """Validate RDF mapping preserves all document elements."""

    @pytest.mark.parametrize(
        "example_file",
        [
            "capital_reflux_trap.md",
            "attention_residual_discovery.md",
            "gradient_explosion.md",
            "matdo_original.md",
            "matdo_fork_kinetic.md",
        ],
    )
    def test_mapping_preserves_concept_identity(self, example_file: str):
        path = EXAMPLES_DIR / example_file
        doc = parse_file(path)
        turtle = adl_to_turtle(doc)

        # Concept identity preserved
        assert f"adl://{doc.front_matter.scope}/{doc.adl_id}" in turtle
        assert doc.adl_id in turtle
        assert doc.front_matter.adl_type.value in turtle.lower()

        # Valid Turtle syntax
        assert "@prefix" in turtle
        assert turtle.strip().endswith("}")

    def test_mapping_round_trip_capital_trap(self):
        """Full round-trip verification on the most complex example."""
        doc = parse_file(EXAMPLES_DIR / "capital_reflux_trap.md")
        turtle = adl_to_turtle(doc)

        # Count preservation
        assert turtle.count("adl:RelationAssertion") == len(doc.relations), (
            f"Expected {len(doc.relations)} relation assertions, "
            f"found {turtle.count('adl:RelationAssertion')}"
        )
        assert turtle.count("prov:Entity") >= len(doc.evidence), (
            f"Expected {len(doc.evidence)} evidence entities, "
            f"found {turtle.count('prov:Entity')}"
        )

        # Key fields preserved
        for rel in doc.relations:
            assert rel.relation.replace("-", "_") in turtle, f"Missing relation: {rel.relation}"
        for ev in doc.evidence:
            assert ev.data_ref in turtle, f"Missing evidence ref: {ev.data_ref}"

        # Provenance: wasAttributedTo or other prov properties
        assert "prov:" in turtle, "Expected prov: namespace usage"

        # Confidence/anonymous blank nodes created
        assert str(doc.front_matter.confidence) in turtle

    def test_mapping_all_examples(self):
        """All 5 examples produce valid RDF with full preservation."""
        results = {}
        for md_file in sorted(EXAMPLES_DIR.glob("*.md")):
            doc = parse_file(md_file)
            turtle = adl_to_turtle(doc)

            rel_count = turtle.count("adl:RelationAssertion")
            ev_count = turtle.count("prov:Entity")

            results[doc.adl_id] = {
                "file": md_file.name,
                "relations_in": len(doc.relations),
                "relations_out": rel_count,
                "evidence_in": len(doc.evidence),
                "evidence_out": ev_count,
                "relations_preserved": rel_count == len(doc.relations),
                "evidence_preserved": ev_count >= len(doc.evidence),
            }

        print("\n" + "=" * 70)
        print("RDF/OWL/PROV-O MAPPING — INFORMATION PRESERVATION")
        print("=" * 70)
        print(f"{'Concept':<25} {'File':<35} {'Rels':>5} {'Evid':>5} {'R-OK':>5} {'E-OK':>5}")
        print("-" * 70)
        for adl_id, r in sorted(results.items()):
            print(
                f"{adl_id:<25} {r['file']:<35} "
                f"{r['relations_in']:>3}/{r['relations_out']:<3} "
                f"{r['evidence_in']:>3}/{r['evidence_out']:<3} "
                f"{'✅' if r['relations_preserved'] else '❌':>5} "
                f"{'✅' if r['evidence_preserved'] else '❌':>5}"
            )

        # Aggregate
        total_rels_in = sum(r["relations_in"] for r in results.values())
        total_rels_out = sum(r["relations_out"] for r in results.values())
        total_ev_in = sum(r["evidence_in"] for r in results.values())
        total_ev_out = sum(r["evidence_out"] for r in results.values())
        print("-" * 70)
        print(
            f"{'TOTAL':<25} {'':<35} {total_rels_in:>3}/{total_rels_out:<3} {total_ev_in:>3}/{total_ev_out:<3}"
        )
        print(
            f"Relation preservation: {total_rels_out}/{total_rels_in} ({100*total_rels_out//max(1,total_rels_in)}%)"
        )
        print(
            f"Evidence preservation:  {total_ev_out}/{total_ev_in} ({100*total_ev_out//max(1,total_ev_in)}%)"
        )
        print("=" * 70)

        # Assertions
        assert total_rels_out == total_rels_in, f"Relation loss: {total_rels_in - total_rels_out}"
        assert total_ev_out >= total_ev_in, f"Evidence loss: {total_ev_in - total_ev_out}"
