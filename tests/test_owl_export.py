"""
Tests for adl_lite.owl_export — public export API contract tests.

Covers export_owl() (turtle + rdfxml document exports) and export_ontology()
(turtle + rdfxml schema exports), including cross-format triple equivalence
via rdflib and the lazy-[gov]-dependency ImportError guidance.
"""

from __future__ import annotations

import builtins
import xml.etree.ElementTree as ET

import pytest

from adl_lite.models import (
    ADLDocument,
    ADLFrontMatter,
    ADLType,
    DiscoveryStatus,
)
from adl_lite.owl_export import (
    ADL_NS,
    export_ontology,
    export_ontology_turtle,
    export_owl,
)


def _make_sample_doc() -> ADLDocument:
    fm = ADLFrontMatter(
        adl_type=ADLType.DISCOVERY,
        adl_id="disc-export",
        status=DiscoveryStatus.VALIDATED,
        confidence=0.85,
        validators=["agent_1", "agent_2"],
        domain="aml",
        scope="public",
    )
    return ADLDocument(front_matter=fm, markdown_body="")


# ---------------------------------------------------------------------------
# export_owl — Turtle
# ---------------------------------------------------------------------------


class TestExportOwlTurtle:
    def test_prefixes_and_concept_individual(self):
        turtle = export_owl(_make_sample_doc(), format="turtle")
        assert "@prefix owl:" in turtle
        assert "@prefix adl:" in turtle
        # Concept individual is emitted before the ontology header (importer contract).
        assert turtle.index("adl:disc-export a adl:discovery") < turtle.index("a owl:Ontology")

    def test_front_matter_triples(self):
        turtle = export_owl(_make_sample_doc(), format="turtle")
        assert "adl:hasStatus <http://adl-lite.org/ontology/status/validated>" in turtle
        assert 'adl:hasConfidence "0.85"^^xsd:float' in turtle
        assert "adl:validatedBy <http://adl-lite.org/ontology/agent/agent_1>" in turtle
        assert 'adl:hasDomain "aml"' in turtle
        assert 'adl:hasScope "public"' in turtle

    def test_class_and_property_declarations(self):
        turtle = export_owl(_make_sample_doc(), format="turtle", include_schema=True)
        assert "adl:Concept a owl:Class ." in turtle
        assert "adl:Event a owl:Class ." in turtle
        # L3 predicate declarations (kebab-case -> camelCase, with characteristics).
        assert "adl:isomorphicTo a owl:ObjectProperty" in turtle
        assert "a owl:TransitiveProperty" in turtle
        assert "a owl:SymmetricProperty" in turtle

    def test_schema_can_be_excluded(self):
        turtle = export_owl(_make_sample_doc(), format="turtle", include_schema=False)
        assert "adl:Concept a owl:Class ." not in turtle

    def test_swrl_toggle(self):
        with_swrl = export_owl(_make_sample_doc(), format="turtle", include_swrl=True)
        without_swrl = export_owl(_make_sample_doc(), format="turtle", include_swrl=False)
        assert "swrl:" in with_swrl
        assert "SWRL Integrity Rules" not in without_swrl


# ---------------------------------------------------------------------------
# export_owl — RDF/XML
# ---------------------------------------------------------------------------


class TestExportOwlRdfxml:
    def test_well_formed_xml(self):
        rdfxml = export_owl(_make_sample_doc(), format="rdfxml")
        root = ET.fromstring(rdfxml)
        assert root.tag == "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF"

    def test_concept_individual_present(self):
        rdfxml = export_owl(_make_sample_doc(), format="rdfxml")
        assert f'rdf:about="{ADL_NS}disc-export"' in rdfxml
        assert f'rdf:resource="{ADL_NS}status/validated"' in rdfxml
        assert f'rdf:resource="{ADL_NS}agent/agent_1"' in rdfxml

    def test_rdfxml_turtle_key_triple_equivalence(self):
        """Both document serializations carry the same key contract triples."""
        rdflib = pytest.importorskip("rdflib")
        doc = _make_sample_doc()
        graphs = {}
        for fmt, rdf_fmt in [("turtle", "turtle"), ("rdfxml", "xml")]:
            g = rdflib.Graph()
            g.parse(data=export_owl(doc, format=fmt), format=rdf_fmt)
            graphs[fmt] = g

        concept = rdflib.URIRef(f"{ADL_NS}disc-export")
        key_triples = [
            (concept, rdflib.RDF.type, rdflib.URIRef(f"{ADL_NS}discovery")),
            (
                concept,
                rdflib.URIRef(f"{ADL_NS}hasStatus"),
                rdflib.URIRef(f"{ADL_NS}status/validated"),
            ),
            (
                concept,
                rdflib.URIRef(f"{ADL_NS}validatedBy"),
                rdflib.URIRef(f"{ADL_NS}agent/agent_1"),
            ),
            (
                concept,
                rdflib.URIRef(f"{ADL_NS}hasScope"),
                rdflib.Literal("public"),
            ),
        ]
        for triple in key_triples:
            assert triple in graphs["turtle"], f"{triple} missing from turtle"
            assert triple in graphs["rdfxml"], f"{triple} missing from rdfxml"

        # Confidence survives as a float-typed literal in both formats.
        confidence = rdflib.URIRef(f"{ADL_NS}hasConfidence")
        for g in graphs.values():
            values = list(g.objects(concept, confidence))
            assert len(values) == 1
            assert float(values[0]) == pytest.approx(0.85)


# ---------------------------------------------------------------------------
# export_ontology — Turtle
# ---------------------------------------------------------------------------


class TestExportOntologyTurtle:
    def test_ontology_header(self):
        turtle = export_ontology(format="turtle")
        assert "<http://adl-lite.org/ontology/> a owl:Ontology ;" in turtle
        assert 'dc:title "ADL Lite Ontology"' in turtle

    def test_status_enumeration(self):
        turtle = export_ontology(format="turtle")
        assert "adl:DiscoveryStatus a owl:Class ;" in turtle
        assert "owl:oneOf" in turtle
        for status in ("provisional", "validated", "deprecated", "forked", "archived"):
            assert f"adl:status_{status} a owl:NamedIndividual" in turtle

    def test_swrl_toggle(self):
        with_swrl = export_ontology(format="turtle", include_swrl=True)
        without_swrl = export_ontology(format="turtle", include_swrl=False)
        # The header always declares the swrl prefixes; the rules block only
        # appears when include_swrl=True.
        assert "SWRL Integrity Rules" in with_swrl
        assert "SWRL Integrity Rules" not in without_swrl

    def test_matches_export_ontology_turtle(self):
        assert export_ontology(format="turtle") == export_ontology_turtle()


# ---------------------------------------------------------------------------
# export_ontology — RDF/XML (P2-6a)
# ---------------------------------------------------------------------------


class TestExportOntologyRdfxml:
    def test_well_formed_xml(self):
        pytest.importorskip("rdflib")
        rdfxml = export_ontology(format="rdfxml")
        root = ET.fromstring(rdfxml)
        assert root.tag.endswith("RDF")

    def test_rdfxml_turtle_triple_equivalence(self):
        """RDF/XML is serialized from the same triple set as Turtle."""
        rdflib = pytest.importorskip("rdflib")
        g_turtle = rdflib.Graph()
        g_turtle.parse(data=export_ontology(format="turtle"), format="turtle")
        g_xml = rdflib.Graph()
        g_xml.parse(data=export_ontology(format="rdfxml"), format="xml")
        assert len(g_xml) == len(g_turtle) > 0

        status_cls = rdflib.URIRef(f"{ADL_NS}DiscoveryStatus")
        validated = rdflib.URIRef(f"{ADL_NS}status_validated")
        assert (status_cls, rdflib.RDF.type, rdflib.OWL.Class) in g_xml
        assert (validated, rdflib.RDF.type, rdflib.OWL.NamedIndividual) in g_xml

    def test_swrl_toggle_changes_triple_count(self):
        rdflib = pytest.importorskip("rdflib")
        g_with = rdflib.Graph()
        g_with.parse(data=export_ontology(format="rdfxml", include_swrl=True), format="xml")
        g_without = rdflib.Graph()
        g_without.parse(data=export_ontology(format="rdfxml", include_swrl=False), format="xml")
        assert len(g_with) > len(g_without)

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Unsupported ontology export format"):
            export_ontology(format="jsonld")

    def test_missing_rdflib_raises_actionable_error(self, monkeypatch: pytest.MonkeyPatch):
        """Without the [gov] extra, rdfxml export fails with install guidance."""
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "rdflib":
                raise ImportError("No module named 'rdflib'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        with pytest.raises(ImportError, match=r"pip install adl-lite\[gov\]"):
            export_ontology(format="rdfxml")
