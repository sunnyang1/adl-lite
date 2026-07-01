"""
OWL 2 DL Export for ADL Lite.

Exports EventChain data to OWL 2 DL format (RDF/XML or Turtle).
Used for interoperability with semantic-web tools and formal reasoners.

Paper §6.2: "OWL 2 export is available for interoperability with Protégé
and formal reasoners."

Extensions:
    - L3 relation predicates as OWL ObjectProperty declarations
    - SWRL integrity rules (validated confidence, no self-loop)
    - SHACL/SPARQL constraint generation helpers
"""

from __future__ import annotations

from xml.etree.ElementTree import Element, SubElement, tostring

from .models import ADLDocument, ADLRelationBlock, DiscoveryStatus, EventType

OWL_NS = "http://www.w3.org/2002/07/owl#"
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"
ADL_NS = "http://adl-lite.org/ontology/"
SWRL_NS = "http://www.w3.org/2003/11/swrl#"
SWRLB_NS = "http://www.w3.org/2003/11/swrlb#"
XSD_NS = "http://www.w3.org/2001/XMLSchema#"

# L3 predicates from adl_core_ontology.yaml with OWL characteristics
L3_PREDICATES: dict[str, dict[str, bool]] = {
    "isomorphic-to": {"transitive": False, "symmetric": False, "asymmetric": False},
    "specialisation-of": {"transitive": True, "symmetric": False, "asymmetric": False},
    "co-occurs-with": {"transitive": False, "symmetric": True, "asymmetric": False},
    "related-to": {"transitive": False, "symmetric": False, "asymmetric": False},
    "analogical-to": {"transitive": False, "symmetric": False, "asymmetric": False},
    "analogical-transfer": {"transitive": False, "symmetric": False, "asymmetric": False},
    "dual-of": {"transitive": False, "symmetric": True, "asymmetric": False},
    "fork-of": {"transitive": False, "symmetric": False, "asymmetric": False},
    "mitigated-by": {"transitive": False, "symmetric": False, "asymmetric": False},
    "indexed-phrase": {"transitive": False, "symmetric": False, "asymmetric": False},
}


def _predicate_to_property_name(predicate: str) -> str:
    """Convert kebab-case predicate to camelCase OWL property name."""
    parts = predicate.split("-")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _make_uri(concept_id: str) -> str:
    """Build a URI for a concept."""
    return f"{ADL_NS}{concept_id}"


def _status_to_uri(status: DiscoveryStatus) -> str:
    """Map ADL status to OWL individual URI."""
    return f"{ADL_NS}status/{status.value}"


def _status_uri_turtle(status: DiscoveryStatus) -> str:
    """Return a Turtle-safe URI reference for status."""
    return f"<http://adl-lite.org/ontology/status/{status.value}>"


def _event_type_to_uri(event_type: EventType) -> str:
    """Map ADL event type to OWL property URI."""
    return f"adl:has{event_type.value.capitalize()}Event"


def _build_classes_rdfxml(root: Element) -> None:
    """Declare core ADL classes in RDF/XML."""
    classes = ["Concept", "Event", "discovery", "concept", "relation", "evidence", "formal_seal"]
    for cls in classes:
        c = SubElement(root, "owl:Class")
        c.set("rdf:about", f"{ADL_NS}{cls}")


def _build_core_object_properties_rdfxml(root: Element) -> None:
    """Declare core object properties used outside L3 predicates."""
    core_props = [
        (
            "hasStatus",
            "Concept",
            "Concept",
        ),  # range should be a class, but we use Concept for simplicity
        ("belongsTo", "Event", "Concept"),
        ("validatedBy", "Concept", "Concept"),
    ]
    for pname, domain, range_cls in core_props:
        prop = SubElement(root, "owl:ObjectProperty")
        prop.set("rdf:about", f"{ADL_NS}{pname}")
        d = SubElement(prop, "rdfs:domain")
        d.set("rdf:resource", f"{ADL_NS}{domain}")
        r = SubElement(prop, "rdfs:range")
        r.set("rdf:resource", f"{ADL_NS}{range_cls}")


def _build_classes_turtle() -> list[str]:
    """Return Turtle lines for core ADL class declarations."""
    lines = [
        "",
        "# --- OWL Classes ---",
        "",
    ]
    for cls in ["Concept", "Event", "discovery", "concept", "relation", "evidence", "formal_seal"]:
        lines.append(f"adl:{cls} a owl:Class .")
    lines.append("")
    return lines


def _build_core_object_properties_turtle() -> list[str]:
    """Return Turtle lines for core object properties."""
    return [
        "",
        "# --- Core ObjectProperties ---",
        "",
        "adl:hasStatus a owl:ObjectProperty ;",
        "    rdfs:domain adl:Concept ;",
        "    rdfs:range adl:Concept .",
        "",
        "adl:belongsTo a owl:ObjectProperty ;",
        "    rdfs:domain adl:Event ;",
        "    rdfs:range adl:Concept .",
        "",
        "adl:validatedBy a owl:ObjectProperty ;",
        "    rdfs:domain adl:Concept ;",
        "    rdfs:range adl:Concept .",
        "",
    ]


def _build_l3_object_properties_rdfxml(root: Element) -> None:
    """Append L3 predicate ObjectProperty declarations to an RDF/XML root."""
    for pred, chars in L3_PREDICATES.items():
        prop_name = _predicate_to_property_name(pred)
        prop = SubElement(root, "owl:ObjectProperty")
        prop.set("rdf:about", f"{ADL_NS}{prop_name}")

        # rdfs:label
        label = SubElement(prop, "rdfs:label")
        label.text = pred.replace("-", " ")

        # rdfs:comment
        comment = SubElement(prop, "rdfs:comment")
        comment.text = f"L3 relation predicate: {pred}"

        # domain / range
        domain = SubElement(prop, "rdfs:domain")
        domain.set("rdf:resource", f"{ADL_NS}Concept")
        range_elem = SubElement(prop, "rdfs:range")
        range_elem.set("rdf:resource", f"{ADL_NS}Concept")

        # OWL characteristics
        if chars.get("transitive"):
            SubElement(prop, "rdf:type").set("rdf:resource", f"{OWL_NS}TransitiveProperty")
        if chars.get("symmetric"):
            SubElement(prop, "rdf:type").set("rdf:resource", f"{OWL_NS}SymmetricProperty")
        if chars.get("asymmetric"):
            SubElement(prop, "rdf:type").set("rdf:resource", f"{OWL_NS}AsymmetricProperty")


def _build_l3_object_properties_turtle() -> list[str]:
    """Return Turtle lines for L3 predicate ObjectProperty declarations."""
    lines: list[str] = [
        "",
        "# --- L3 Relation Predicate ObjectProperties ---",
        "",
    ]
    for pred, chars in L3_PREDICATES.items():
        prop_name = _predicate_to_property_name(pred)
        lines.append(f"adl:{prop_name} a owl:ObjectProperty ;")
        lines.append(f'    rdfs:label "{pred.replace("-", " ")}" ;')
        lines.append(f'    rdfs:comment "L3 relation predicate: {pred}" ;')
        lines.append("    rdfs:domain adl:Concept ;")
        lines.append("    rdfs:range adl:Concept")
        if chars.get("transitive"):
            lines[-1] += " ;"
            lines.append("    a owl:TransitiveProperty")
        if chars.get("symmetric"):
            lines[-1] += " ;"
            lines.append("    a owl:SymmetricProperty")
        if chars.get("asymmetric"):
            lines[-1] += " ;"
            lines.append("    a owl:AsymmetricProperty")
        lines[-1] += " ."
        lines.append("")
    return lines


def _build_data_properties_rdfxml(root: Element) -> None:
    """Append OWL DatatypeProperty declarations to RDF/XML root."""
    props = [
        ("hasConfidence", "Concept", "float"),
        ("hasDomain", "Concept", "string"),
        ("hasScope", "Concept", "string"),
        ("hasActor", "Event", "string"),
        ("hasTimestamp", "Event", "dateTime"),
    ]
    for pname, domain, dtype in props:
        prop = SubElement(root, "owl:DatatypeProperty")
        prop.set("rdf:about", f"{ADL_NS}{pname}")
        d = SubElement(prop, "rdfs:domain")
        d.set("rdf:resource", f"{ADL_NS}{domain}")
        r = SubElement(prop, "rdfs:range")
        r.set("rdf:resource", f"{XSD_NS}{dtype}")


def _build_data_properties_turtle() -> list[str]:
    """Return Turtle lines for OWL DatatypeProperty declarations."""
    lines = [
        "",
        "# --- OWL DatatypeProperties ---",
        "",
        "adl:hasConfidence a owl:DatatypeProperty ;",
        "    rdfs:domain adl:Concept ;",
        "    rdfs:range xsd:float .",
        "",
        "adl:hasDomain a owl:DatatypeProperty ;",
        "    rdfs:domain adl:Concept ;",
        "    rdfs:range xsd:string .",
        "",
        "adl:hasScope a owl:DatatypeProperty ;",
        "    rdfs:domain adl:Concept ;",
        "    rdfs:range xsd:string .",
        "",
        "adl:hasActor a owl:DatatypeProperty ;",
        "    rdfs:domain adl:Event ;",
        "    rdfs:range xsd:string .",
        "",
        "adl:hasTimestamp a owl:DatatypeProperty ;",
        "    rdfs:domain adl:Event ;",
        "    rdfs:range xsd:dateTime .",
        "",
    ]
    return lines


def _build_swrl_rules_rdfxml(root: Element) -> None:
    """Append SWRL rules for ADL integrity constraints (RDF/XML)."""

    def _var_uri(var_name: str) -> str:
        return f"{ADL_NS}_var_{var_name}"

    def _val_uri(val_name: str) -> str:
        return f"{ADL_NS}_{val_name}"

    def _individual_prop_atom(predicate: str, arg1: str, arg2: str) -> Element:
        atom = Element("swrl:IndividualPropertyAtom")
        SubElement(atom, "swrl:propertyPredicate").set("rdf:resource", f"{ADL_NS}{predicate}")
        SubElement(atom, "swrl:argument1").set("rdf:resource", _var_uri(arg1))
        SubElement(atom, "swrl:argument2").set("rdf:resource", _var_uri(arg2))
        return atom

    def _datavalued_prop_atom(predicate: str, arg1: str, arg2: str) -> Element:
        atom = Element("swrl:DatavaluedPropertyAtom")
        SubElement(atom, "swrl:propertyPredicate").set("rdf:resource", f"{ADL_NS}{predicate}")
        SubElement(atom, "swrl:argument1").set("rdf:resource", _var_uri(arg1))
        SubElement(atom, "swrl:argument2").set("rdf:resource", _var_uri(arg2))
        return atom

    def _builtin_atom(builtin: str, args: list[str]) -> Element:
        atom = Element("swrl:BuiltinAtom")
        SubElement(atom, "swrl:builtin").set("rdf:resource", f"{SWRLB_NS}{builtin}")
        args_elem = SubElement(atom, "swrl:arguments")
        args_elem.set("rdf:parseType", "Collection")
        for arg in args:
            if arg.startswith("var:"):
                SubElement(args_elem, "rdf:Description").set("rdf:about", _var_uri(arg[4:]))
            elif arg.startswith("val:"):
                SubElement(args_elem, "rdf:Description").set("rdf:about", _val_uri(arg[4:]))
            else:
                SubElement(args_elem, "rdf:Description").set("rdf:about", arg)
        return atom

    # Declare swrl:varName as AnnotationProperty to satisfy OWL 2 DL profile
    varname_prop = Element("owl:AnnotationProperty")
    varname_prop.set("rdf:about", f"{SWRL_NS}varName")
    root.append(varname_prop)

    def _imp(body_atoms: list[Element], head_atoms: list[Element]) -> Element:
        imp = Element("swrl:Imp")
        body = SubElement(imp, "swrl:body")
        body.set("rdf:parseType", "Collection")
        for atom in body_atoms:
            body.append(atom)
        head = SubElement(imp, "swrl:head")
        head.set("rdf:parseType", "Collection")
        for atom in head_atoms:
            head.append(atom)
        return imp

    # Rule 1: ValidatedConfidenceRule
    # If a concept has status validated, its confidence must be >= 0.5
    root.append(
        _imp(
            body_atoms=[
                _individual_prop_atom("hasStatus", "c", "status/validated"),
                _datavalued_prop_atom("hasConfidence", "c", "conf"),
            ],
            head_atoms=[
                _builtin_atom("greaterThanOrEqual", ["var:conf", "val:0_5"]),
            ],
        )
    )

    # Rule 2: NoSelfLoopRule
    # A concept cannot be related to itself via any L3 predicate
    root.append(
        _imp(
            body_atoms=[
                _individual_prop_atom("relatedTo", "c1", "c2"),
            ],
            head_atoms=[
                _builtin_atom("notEqual", ["var:c1", "var:c2"]),
            ],
        )
    )


def _build_swrl_rules_turtle() -> list[str]:
    """Return Turtle lines for SWRL integrity rules."""
    return [
        "",
        "# --- SWRL Integrity Rules ---",
        "",
        "@prefix swrl: <http://www.w3.org/2003/11/swrl#> .",
        "@prefix swrlb: <http://www.w3.org/2003/11/swrlb#> .",
        "",
        "swrl:varName a owl:AnnotationProperty .",
        "",
        "# Rule 1: ValidatedConfidenceRule",
        "# If a concept has status validated, then confidence >= 0.5",
        "[ rdf:type swrl:Imp ;",
        "  swrl:body (",
        "    [ rdf:type swrl:IndividualPropertyAtom ;",
        "      swrl:propertyPredicate adl:hasStatus ;",
        '      swrl:argument1 [ rdf:type swrl:Variable ; swrl:varName "c" ] ;',
        "      swrl:argument2 <http://adl-lite.org/ontology/status/validated>",
        "    ]",
        "    [ rdf:type swrl:DatavaluedPropertyAtom ;",
        "      swrl:propertyPredicate adl:hasConfidence ;",
        '      swrl:argument1 [ rdf:type swrl:Variable ; swrl:varName "c" ] ;',
        '      swrl:argument2 [ rdf:type swrl:Variable ; swrl:varName "conf" ]',
        "    ]",
        "  ) ;",
        "  swrl:head (",
        "    [ rdf:type swrl:BuiltinAtom ;",
        "      swrl:builtin swrlb:greaterThanOrEqual ;",
        "      swrl:arguments (",
        '        [ rdf:type swrl:Variable ; swrl:varName "conf" ]',
        '        "0.5"^^xsd:float',
        "      )",
        "    ]",
        "  )",
        "] .",
        "",
        "# Rule 2: NoSelfLoopRule",
        "# A concept cannot be related to itself via any L3 predicate",
        "[ rdf:type swrl:Imp ;",
        "  swrl:body (",
        "    [ rdf:type swrl:IndividualPropertyAtom ;",
        "      swrl:propertyPredicate adl:relatedTo ;",
        '      swrl:argument1 [ rdf:type swrl:Variable ; swrl:varName "c1" ] ;',
        '      swrl:argument2 [ rdf:type swrl:Variable ; swrl:varName "c2" ]',
        "    ]",
        "  ) ;",
        "  swrl:head (",
        "    [ rdf:type swrl:BuiltinAtom ;",
        "      swrl:builtin swrlb:notEqual ;",
        "      swrl:arguments (",
        '        [ rdf:type swrl:Variable ; swrl:varName "c1" ]',
        '        [ rdf:type swrl:Variable ; swrl:varName "c2" ]',
        "      )",
        "    ]",
        "  )",
        "] .",
        "",
    ]


def _add_relation_assertions_rdfxml(root: Element, doc: ADLDocument) -> None:
    """Add L3 relation block assertions as OWL object-property assertions."""
    for block in doc.adl_blocks:
        if isinstance(block, ADLRelationBlock):
            prop_name = _predicate_to_property_name(block.relation)
            source_uri = _make_uri(block.source.replace(" ", "_").lower())
            target_uri = _make_uri(block.target.replace(" ", "_").lower())
            ind = SubElement(root, "owl:NamedIndividual")
            ind.set("rdf:about", source_uri)
            rel = SubElement(ind, f"adl:{prop_name}")
            rel.set("rdf:resource", target_uri)


def _add_relation_assertions_turtle(lines: list[str], doc: ADLDocument) -> None:
    """Add L3 relation block assertions as Turtle object-property triples."""
    rel_lines: list[str] = ["", "# --- L3 Relation Assertions ---", ""]
    for block in doc.adl_blocks:
        if isinstance(block, ADLRelationBlock):
            prop_name = _predicate_to_property_name(block.relation)
            source = (
                block.source.replace(" ", "_")
                .replace("adl://", "http://adl-lite.org/ontology/")
                .lower()
            )
            target = (
                block.target.replace(" ", "_")
                .replace("adl://", "http://adl-lite.org/ontology/")
                .lower()
            )
            # Ensure valid URI references
            if not source.startswith("http://") and not source.startswith("adl:"):
                source = f"<http://adl-lite.org/ontology/{source}>"
            elif source.startswith("http://"):
                source = f"<{source}>"
            if not target.startswith("http://") and not target.startswith("adl:"):
                target = f"<http://adl-lite.org/ontology/{target}>"
            elif target.startswith("http://"):
                target = f"<{target}>"
            rel_lines.append(f"{source} adl:{prop_name} {target} .")
            if block.confidence < 1.0:
                rel_lines.append(
                    f"# confidence={block.confidence}, mapping_type={block.mapping_type}"
                )
    rel_lines.append("")
    lines.extend(rel_lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def document_to_owl_rdfxml(
    doc: ADLDocument, include_schema: bool = True, include_swrl: bool = True
) -> str:
    """
    Convert an ADLDocument to OWL 2 DL RDF/XML.

    Args:
        doc: The ADLDocument to export.
        include_schema: Whether to include ObjectProperty / DatatypeProperty
            declarations for L3 predicates and data properties.
        include_swrl: Whether to embed SWRL integrity rules.

    Returns:
        OWL 2 DL RDF/XML as a string.
    """
    root = Element(
        "rdf:RDF",
        {
            "xmlns:owl": OWL_NS,
            "xmlns:rdf": RDF_NS,
            "xmlns:rdfs": RDFS_NS,
            "xmlns:adl": ADL_NS,
            "xmlns:xsd": XSD_NS,
        },
    )

    # Ontology declaration
    onto = SubElement(root, "owl:Ontology")
    onto.set("rdf:about", ADL_NS)

    comment = SubElement(onto, "rdfs:comment")
    comment.text = f"OWL 2 DL export of ADL concept {doc.adl_id} generated by adl-lite"

    # Schema declarations
    if include_schema:
        _build_classes_rdfxml(root)
        _build_core_object_properties_rdfxml(root)
        _build_l3_object_properties_rdfxml(root)
        _build_data_properties_rdfxml(root)

    # Concept individual
    concept_uri = _make_uri(doc.adl_id)
    concept = SubElement(root, "owl:NamedIndividual")
    concept.set("rdf:about", concept_uri)

    # Type assertion
    type_assertion = SubElement(concept, "rdf:type")
    type_assertion.set("rdf:resource", f"{ADL_NS}{doc.front_matter.adl_type.value}")

    # Status
    status_elem = SubElement(concept, "adl:hasStatus")
    status_elem.set("rdf:resource", _status_to_uri(doc.front_matter.status))

    # Confidence
    confidence_elem = SubElement(concept, "adl:hasConfidence")
    confidence_elem.set("rdf:datatype", f"{XSD_NS}float")
    confidence_elem.text = str(doc.front_matter.confidence)

    # Validators
    for validator in doc.front_matter.validators:
        val_elem = SubElement(concept, "adl:validatedBy")
        val_elem.set("rdf:resource", f"{ADL_NS}agent/{validator}")

    # Domain
    if doc.front_matter.domain:
        domain_elem = SubElement(concept, "adl:hasDomain")
        domain_elem.text = doc.front_matter.domain

    # Scope
    scope_elem = SubElement(concept, "adl:hasScope")
    scope_elem.text = doc.front_matter.scope

    # Events (from chain)
    for event in doc.event_chain.events:
        event_uri = f"{ADL_NS}event/{event.event_id}"
        event_ind = SubElement(root, "owl:NamedIndividual")
        event_ind.set("rdf:about", event_uri)

        event_type = SubElement(event_ind, "rdf:type")
        event_type.set("rdf:resource", f"{ADL_NS}Event")

        event_concept = SubElement(event_ind, "adl:belongsTo")
        event_concept.set("rdf:resource", concept_uri)

        event_actor = SubElement(event_ind, "adl:hasActor")
        event_actor.text = event.actor

        event_ts = SubElement(event_ind, "adl:hasTimestamp")
        event_ts.text = event.timestamp

        # Link concept to event
        prop = _event_type_to_uri(event.event_type)
        event_prop = SubElement(concept, prop)
        event_prop.set("rdf:resource", event_uri)

    # L3 relation assertions
    _add_relation_assertions_rdfxml(root, doc)

    # SWRL rules
    if include_swrl:
        _build_swrl_rules_rdfxml(root)

    return tostring(root, encoding="unicode")


def document_to_owl_turtle(
    doc: ADLDocument, include_schema: bool = True, include_swrl: bool = True
) -> str:
    """
    Convert an ADLDocument to OWL 2 DL Turtle syntax.

    Args:
        doc: The ADLDocument to export.
        include_schema: Whether to include ObjectProperty / DatatypeProperty
            declarations for L3 predicates and data properties.
        include_swrl: Whether to embed SWRL integrity rules.

    Returns:
        OWL 2 DL Turtle as a string.
    """
    lines: list[str] = [
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix adl: <http://adl-lite.org/ontology/> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "",
    ]

    # Ontology header
    lines.extend(
        [
            "adl: a owl:Ontology ;",
            f'    rdfs:comment "OWL 2 DL export of ADL concept {doc.adl_id} generated by adl-lite" .',
            "",
        ]
    )

    # Schema declarations
    if include_schema:
        lines.extend(_build_classes_turtle())
        lines.extend(_build_core_object_properties_turtle())
        lines.extend(_build_l3_object_properties_turtle())
        lines.extend(_build_data_properties_turtle())

    # Concept individual
    lines.append(f"adl:{doc.adl_id} a adl:{doc.front_matter.adl_type.value} ;")
    lines.append(
        f"    adl:hasStatus <http://adl-lite.org/ontology/status/{doc.front_matter.status.value}> ;"
    )
    lines.append(f'    adl:hasConfidence "{doc.front_matter.confidence}"^^xsd:float ;')

    for validator in doc.front_matter.validators:
        lines.append(f"    adl:validatedBy <http://adl-lite.org/ontology/agent/{validator}> ;")

    if doc.front_matter.domain:
        lines.append(f'    adl:hasDomain "{doc.front_matter.domain}" ;')

    lines.append(f'    adl:hasScope "{doc.front_matter.scope}" .')
    lines.append("")

    for event in doc.event_chain.events:
        lines.append(f"<http://adl-lite.org/ontology/event/{event.event_id}> a adl:Event ;")
        lines.append(f"    adl:belongsTo adl:{doc.adl_id} ;")
        lines.append(f'    adl:hasActor "{event.actor}" ;')
        lines.append(f'    adl:hasTimestamp "{event.timestamp}"^^xsd:dateTime .')
        lines.append("")

    # L3 relation assertions
    _add_relation_assertions_turtle(lines, doc)

    # SWRL rules
    if include_swrl:
        lines.extend(_build_swrl_rules_turtle())

    return "\n".join(lines)


def export_owl(
    doc: ADLDocument, format: str = "turtle", include_schema: bool = True, include_swrl: bool = True
) -> str:
    """
    Export an ADLDocument to OWL 2 DL.

    Args:
        doc: The ADLDocument to export
        format: "turtle" or "rdfxml"
        include_schema: Include L3 ObjectProperty / DatatypeProperty declarations.
        include_swrl: Embed SWRL integrity rules.

    Returns:
        OWL serialization as a string
    """
    if format == "rdfxml":
        return document_to_owl_rdfxml(doc, include_schema=include_schema, include_swrl=include_swrl)
    return document_to_owl_turtle(doc, include_schema=include_schema, include_swrl=include_swrl)


# ---------------------------------------------------------------------------
# SPARQL constraint helpers (for ROBOT verify / external SHACL engines)
# ---------------------------------------------------------------------------


def sparql_confidence_range() -> str:
    """Return a SPARQL query that finds concepts with confidence outside [0,1]."""
    return """# ADL Integrity: Confidence Range Check
PREFIX adl: <http://adl-lite.org/ontology/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?concept ?confidence
WHERE {
  ?concept adl:hasConfidence ?confidence .
  FILTER (?confidence < 0.0 || ?confidence > 1.0)
}
"""


def sparql_no_self_loop() -> str:
    """Return a SPARQL query that finds self-looping L3 relations."""
    return """# ADL Integrity: No Self-Loop Check
PREFIX adl: <http://adl-lite.org/ontology/>

SELECT ?source ?predicate ?target
WHERE {
  ?source ?predicate ?target .
  FILTER (str(?source) = str(?target))
  FILTER (strStarts(str(?predicate), str(adl:)))
}
"""


def sparql_validated_min_confidence() -> str:
    """Return a SPARQL query that finds validated concepts with confidence < 0.5."""
    return """# ADL Integrity: Validated Concept Minimum Confidence
PREFIX adl: <http://adl-lite.org/ontology/>

SELECT ?concept ?confidence
WHERE {
  ?concept adl:hasStatus <http://adl-lite.org/ontology/status/validated> ;
          adl:hasConfidence ?confidence .
  FILTER (?confidence < 0.5)
}
"""


def generate_sparql_constraints(output_dir: str | None = None) -> dict[str, str]:
    """
    Generate all SPARQL constraint queries and optionally write them to disk.

    Args:
        output_dir: If provided, write .sparql files to this directory.

    Returns:
        Mapping of query name -> SPARQL string.
    """
    queries = {
        "confidence_range": sparql_confidence_range(),
        "no_self_loop": sparql_no_self_loop(),
        "validated_min_confidence": sparql_validated_min_confidence(),
    }
    if output_dir:
        from pathlib import Path

        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        for name, query in queries.items():
            (out / f"{name}.sparql").write_text(query, encoding="utf-8")
    return queries
