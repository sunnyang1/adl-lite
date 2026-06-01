"""
SHACL validation for ADL Lite exported RDF.

Uses pyshacl to validate EventChain / ADLDocument RDF against the
SHACL shapes defined in the paper's Appendix B.

Example usage:
    from adl_lite.shacl_validation import validate_adl_rdf
    from adl_lite.prov_export import to_prov_o
    conforms, report = validate_adl_rdf(to_prov_o(chain))
"""

from __future__ import annotations

from pyshacl import validate
from rdflib import Graph, Namespace

ADL = Namespace("https://adl-lite.org/ns/")

# Inline SHACL shape graph (extracted from Appendix B of the paper)
_ADL_SHAPES_TURTLE = """
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix adl:  <https://adl-lite.org/ns/> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix prov: <http://www.w3.org/ns/prov#> .

adl:EventShape a sh:NodeShape ;
    sh:targetClass prov:Activity ;
    sh:property [
        sh:path adl:eventType ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:in ("register" "validate" "deprecate" "fork" "archive" "relate" "evidence" "seal" "announce" "publish" "sync_dashboard" "listen" "snapshot")
    ] ;
    sh:property [
        sh:path adl:eventHash ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:pattern "^[a-f0-9]{64}$"
    ] ;
    sh:property [
        sh:path prov:wasAssociatedWith ;
        sh:class prov:Agent ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
    ] ;
    sh:property [
        sh:path prov:startedAtTime ;
        sh:datatype xsd:dateTime ;
        sh:maxCount 1 ;
    ] .

adl:ConceptShape a sh:NodeShape ;
    sh:targetClass prov:Entity ;
    sh:property [
        sh:path adl:conceptId ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
    ] ;
    sh:property [
        sh:path adl:status ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:in ("provisional" "validated" "deprecated" "forked" "archived")
    ] ;
    sh:property [
        sh:path adl:confidence ;
        sh:datatype xsd:float ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:minInclusive 0.0 ;
        sh:maxInclusive 1.0 ;
    ] .

adl:AgentShape a sh:NodeShape ;
    sh:targetClass prov:Agent ;
    sh:property [
        sh:path rdfs:label ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
    ] .
"""


_shapes_graph: Graph | None = None


def _get_shapes_graph() -> Graph:
    """Lazy-load the ADL SHACL shapes graph."""
    global _shapes_graph
    if _shapes_graph is None:
        _shapes_graph = Graph()
        _shapes_graph.parse(data=_ADL_SHAPES_TURTLE, format="turtle")
    return _shapes_graph


def validate_adl_rdf(rdf_data: str, rdf_format: str = "turtle") -> tuple[bool, str]:
    """
    Validate ADL RDF data against the built-in SHACL shapes.

    Args:
        rdf_data: RDF serialization string (Turtle by default)
        rdf_format: Format passed to rdflib.parse

    Returns:
        (conforms, report_text)
    """
    data_graph = Graph()
    data_graph.parse(data=rdf_data, format=rdf_format)

    conforms, results_graph, results_text = validate(
        data_graph,
        shacl_graph=_get_shapes_graph(),
        inference="rdfs",
        abort_on_first=False,
        meta_shacl=False,
        advanced=False,
        js=False,
    )
    return conforms, results_text
