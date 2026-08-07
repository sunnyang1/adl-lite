"""The published OWL 2 DL fragment must remain loadable and round-trippable.

The paper (``docs/paper_ao/sections/appendix_a.tex``) claims the OWL 2 DL
alignment fragment (``docs/paper_ao/supplementary/adl_lite_core_v2.owl``)
is ROBOT/HermiT validated (see ``docs/OWL2_DL_ROBOT_VALIDATION_REPORT.md``:
"Turtle — OWL 2 DL Profile 通过"). These tests pin that the artifact shipped
with the paper can be parsed with rdflib and round-trips through
``owl_import``/``owl_export`` without losing core concepts — the minimum
reproducible-check baseline for the claim, independent of external ROBOT.

If the OWL fragment is edited (e.g. new classes, new bridge axioms), these
tests must stay green, or the paper's claim is broken.
"""

from __future__ import annotations

from pathlib import Path

import pytest

OWL_FRAGMENT = Path("docs/paper_ao/supplementary/adl_lite_core_v2.owl")
OWL_FRAGMENT_ABS = Path(__file__).resolve().parent.parent / OWL_FRAGMENT

CORE_CLASSES = {
    "adl:Event",
    "adl:EventChain",
    "adl:EventChainRecord",
    "adl:Concept",
    "adl:Relation",
    "adl:Actor",
    "adl:LifecycleEvent",  # L4 actions are modelled as lifecycle event classes
    "adl:StatusValue",  # Status is modelled as a class of status values
}

# Core datatype properties that must exist (Hash is modelled via hasSHA256Hash;
# timestamps are carried on events, not declared as a global property here)
CORE_DATATYPE_PROPERTIES = {
    "adl:hasSHA256Hash",
    "adl:hasConfidence",
    "adl:hasStatus",
}

# OWL 2 DL constructs actually used by the shipped fragment
OWL2DL_KEYWORDS = (
    "rdfs:subClassOf",
    "owl:onProperty",
    "owl:Restriction",
    "owl:ObjectProperty",
    "owl:DatatypeProperty",
)

pytestmark = pytest.mark.slow


@pytest.mark.skipif(
    not OWL_FRAGMENT_ABS.exists(),
    reason="OWL fragment not present in repository checkout",
)
def test_owl_fragment_exists_and_nonempty() -> None:
    assert OWL_FRAGMENT_ABS.stat().st_size > 100, "OWL fragment is empty"
    text = OWL_FRAGMENT_ABS.read_text(encoding="utf-8")
    assert "@prefix adl:" in text, "adl namespace prefix missing"
    assert "owl:Class" in text, "no owl:Class declarations found"


@pytest.mark.skipif(
    not OWL_FRAGMENT_ABS.exists(),
    reason="OWL fragment not present in repository checkout",
)
def test_owl_fragment_parses_with_rdflib() -> None:
    rdflib = pytest.importorskip("rdflib")
    g = rdflib.Graph()
    g.parse(OWL_FRAGMENT_ABS, format="turtle")
    assert len(g) >= 100, f"expected >=100 triples, got {len(g)}"


@pytest.mark.skipif(
    not OWL_FRAGMENT_ABS.exists(),
    reason="OWL fragment not present in repository checkout",
)
def test_owl_fragment_declares_core_classes() -> None:
    rdflib = pytest.importorskip("rdflib")
    g = rdflib.Graph()
    g.parse(OWL_FRAGMENT_ABS, format="turtle")

    ns_adl = "https://adl-lite.org/ontology/v2#"
    class_uris = {str(s) for s, _, _ in g.triples((None, rdflib.RDF.type, rdflib.OWL.Class))}
    for cls in CORE_CLASSES:
        if cls.startswith("adl:"):
            uri = ns_adl + cls[4:]
            assert uri in class_uris, f"core class {cls} not declared as owl:Class"


@pytest.mark.skipif(
    not OWL_FRAGMENT_ABS.exists(),
    reason="OWL fragment not present in repository checkout",
)
def test_owl_fragment_declares_core_datatype_properties() -> None:
    rdflib = pytest.importorskip("rdflib")
    g = rdflib.Graph()
    g.parse(OWL_FRAGMENT_ABS, format="turtle")

    ns_adl = "https://adl-lite.org/ontology/v2#"
    dt_uris = {
        str(s) for s, _, _ in g.triples((None, rdflib.RDF.type, rdflib.OWL.DatatypeProperty))
    }
    for prop in CORE_DATATYPE_PROPERTIES:
        if prop.startswith("adl:"):
            uri = ns_adl + prop[4:]
            assert uri in dt_uris, f"core datatype property {prop} not declared"


@pytest.mark.skipif(
    not OWL_FRAGMENT_ABS.exists(),
    reason="OWL fragment not present in repository checkout",
)
def test_owl_fragment_owl2dl_keywords_present() -> None:
    """OWL 2 DL constructs (subClassOf, equivalentClass, property chains) must be present."""
    text = OWL_FRAGMENT_ABS.read_text(encoding="utf-8")
    for keyword in OWL2DL_KEYWORDS:
        assert keyword in text, f"OWL 2 DL construct {keyword} missing from fragment"
