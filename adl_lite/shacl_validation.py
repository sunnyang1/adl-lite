"""
SHACL validation for ADL Lite exported RDF.

Uses pyshacl to validate EventChain / ADLDocument RDF against the
SHACL shapes defined in the paper's Appendix B, plus runtime governance
extensions for L3 relations and CALIBRATE events.

Example usage:
    from adl_lite.shacl_validation import validate_adl_rdf, validate_adl_document
    from adl_lite.prov_export import to_prov_o

    conforms, report = validate_adl_rdf(to_prov_o(chain))
    conforms, report = validate_adl_document(doc)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import ADLDocument, DiscoveryStatus

if TYPE_CHECKING:
    # rdflib / pyshacl are optional dependencies (the [gov] extra). They are
    # imported lazily inside the functions below so that ``import adl_lite``
    # works in a bare (core-deps-only) installation.
    from rdflib import Graph, Literal, Namespace, URIRef

_ADL_NS = "https://adl-lite.org/ns/"


def _require_gov_deps() -> None:
    """Raise an actionable ImportError when the optional [gov] deps are missing."""
    try:
        import pyshacl  # noqa: F401
        import rdflib  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "SHACL validation requires the optional 'gov' extra. "
            "Install with: pip install adl-lite[gov]"
        ) from exc


def _adl_namespace() -> Namespace:
    """Return the ADL namespace (imports rdflib lazily)."""
    from rdflib import Namespace

    return Namespace(_ADL_NS)


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
        sh:in ("register" "validate" "deprecate" "fork" "archive" "relate" "evidence" "seal" "announce" "publish" "sync_dashboard" "listen" "snapshot" "calibrate" "revoke")
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

# Runtime governance extension: CALIBRATE events must carry a valid
# observedAccuracy value in [0, 1].
adl:CalibrateEventShape a sh:NodeShape ;
    sh:targetClass adl:CalibrateEvent ;
    sh:property [
        sh:path adl:eventType ;
        sh:hasValue "calibrate" ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
    ] ;
    sh:property [
        sh:path adl:observedAccuracy ;
        sh:datatype xsd:float ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:minInclusive 0.0 ;
        sh:maxInclusive 1.0 ;
    ] .

# Runtime governance extension: L3 relation assertions.
# Structural constraints only — lifecycle invariants (archived / dual-deprecated
# endpoints) are enforced by RelationValidator to avoid advanced SHACL features.
adl:RelationShape a sh:NodeShape ;
    sh:targetClass adl:Relation ;
    sh:property [
        sh:path adl:source ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
    ] ;
    sh:property [
        sh:path adl:target ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
    ] ;
    sh:property [
        sh:path adl:relationPredicate ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
    ] ;
    sh:property [
        sh:path adl:confidence ;
        sh:datatype xsd:float ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:minInclusive 0.0 ;
        sh:maxInclusive 1.0 ;
    ] ;
    sh:property [
        sh:path adl:sourceStatus ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:not [ sh:hasValue "archived" ] ;
    ] ;
    sh:property [
        sh:path adl:targetStatus ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:not [ sh:hasValue "archived" ] ;
    ] .

adl:ForkShape a sh:NodeShape ;
    sh:targetClass adl:ForkEvent ;
    sh:property [
        sh:path adl:eventType ;
        sh:hasValue "fork" ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
    ] ;
    sh:property [
        sh:path adl:sourceConceptId ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
    ] ;
    sh:property [
        sh:path adl:targetConceptId ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
    ] .
"""


_shapes_graph: Graph | None = None


def _get_shapes_graph() -> Graph:
    """Lazy-load the ADL SHACL shapes graph."""
    from rdflib import Graph

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

    Raises:
        ImportError: If pyshacl/rdflib are not installed (the [gov] extra).
    """
    _require_gov_deps()

    from pyshacl import validate
    from rdflib import Graph

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


def _as_rdf_term(value: str, adl: Namespace) -> URIRef | Literal:
    """Convert a relation source/target string to an RDF term."""
    from rdflib import URIRef

    stripped = value.strip()
    if stripped.startswith(("http://", "https://", "adl://")):
        return URIRef(stripped)
    safe = stripped.replace(" ", "_").lower()
    return adl[safe]


def _document_to_rdf_graph(doc: ADLDocument) -> Graph:
    """Build an RDF data graph from an ADLDocument for SHACL validation."""
    from rdflib import BNode, Graph, Literal
    from rdflib.namespace import RDF, XSD

    from .models import EventType
    from .prov_export import to_prov_o

    g = Graph()
    g.parse(data=to_prov_o(doc.event_chain), format="turtle")

    adl = _adl_namespace()

    # Status lookup: at minimum we know the document's own status.
    status_lookup: dict[str, DiscoveryStatus] = {
        doc.adl_id: doc.front_matter.status,
    }

    # Emit L3 relation assertions as typed Relation resources.
    for rel in doc.relations:
        bnode = BNode()
        g.add((bnode, RDF.type, adl.Relation))

        src_term = _as_rdf_term(rel.source, adl)
        tgt_term = _as_rdf_term(rel.target, adl)
        g.add((bnode, adl.source, src_term))
        g.add((bnode, adl.target, tgt_term))
        g.add((bnode, adl.relationPredicate, Literal(rel.relation)))
        g.add((bnode, adl.confidence, Literal(float(rel.confidence), datatype=XSD.float)))

        src_status = status_lookup.get(rel.source, doc.front_matter.status.__class__.PROVISIONAL)
        tgt_status = status_lookup.get(rel.target, doc.front_matter.status.__class__.PROVISIONAL)
        g.add((bnode, adl.sourceStatus, Literal(src_status.value)))
        g.add((bnode, adl.targetStatus, Literal(tgt_status.value)))

    # Enrich CALIBRATE events with typed observedAccuracy for shape validation.
    # Action-block payloads nest params under "params"; direct CALIBRATE events
    # may put the value at the top level.
    for idx, event in enumerate(doc.event_chain.events):
        if event.event_type == EventType.CALIBRATE:
            evt_uri = adl[f"evt-{doc.adl_id}-{event.event_type.value}-{idx:03d}"]
            observed = event.payload.get("observed_accuracy")
            if observed is None:
                observed = event.payload.get("params", {}).get("observed_accuracy")
            if observed is not None:
                g.add(
                    (
                        evt_uri,
                        adl.observedAccuracy,
                        Literal(float(observed), datatype=XSD.float),
                    )
                )

    # Enrich FORK events with source/target concept IDs for ForkShape validation
    for idx, event in enumerate(doc.event_chain.events):
        if event.event_type == EventType.FORK:
            evt_uri = adl[f"evt-{doc.adl_id}-{event.event_type.value}-{idx:03d}"]
            source = event.payload.get("source_concept_id") or event.payload.get("params", {}).get(
                "source_concept_id"
            )
            target = event.payload.get("target_concept_id") or event.payload.get("params", {}).get(
                "target_concept_id"
            )
            if source:
                g.add((evt_uri, adl.sourceConceptId, Literal(source, datatype=XSD.string)))
            if target:
                g.add((evt_uri, adl.targetConceptId, Literal(target, datatype=XSD.string)))

    return g


def validate_adl_document(doc: ADLDocument) -> tuple[bool, str]:
    """
    Validate an ADLDocument against the built-in SHACL shapes.

    The document's EventChain is exported to PROV-O and L3 relation blocks are
    added as typed Relation resources before validation.

    Args:
        doc: Parsed ADLDocument

    Returns:
        (conforms, report_text)

    Raises:
        ImportError: If pyshacl/rdflib are not installed (the [gov] extra).
    """
    _require_gov_deps()

    from pyshacl import validate

    data_graph = _document_to_rdf_graph(doc)
    conforms, _, results_text = validate(
        data_graph,
        shacl_graph=_get_shapes_graph(),
        inference="rdfs",
        abort_on_first=False,
        meta_shacl=False,
        advanced=False,
        js=False,
    )
    return conforms, results_text
