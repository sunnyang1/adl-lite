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
# Updated to match v0.2 ontology (paper Appendix A)
L3_PREDICATES: dict[str, dict[str, bool]] = {
    "isomorphic-to": {"transitive": True, "symmetric": True, "irreflexive": False},
    "specialisation-of": {"transitive": True, "symmetric": False, "irreflexive": True},
    "co-occurs-with": {"transitive": False, "symmetric": True, "irreflexive": False},
    "related-to": {"transitive": False, "symmetric": True, "irreflexive": False},
    "analogical-to": {"transitive": False, "symmetric": True, "irreflexive": False},
    "analogical-transfer": {"transitive": False, "symmetric": False, "irreflexive": False},
    "dual-of": {"transitive": False, "symmetric": True, "irreflexive": False},
    "fork-of": {"transitive": True, "symmetric": False, "irreflexive": True},
    "mitigated-by": {"transitive": False, "symmetric": False, "irreflexive": False},
    "indexed-phrase": {"transitive": False, "symmetric": False, "irreflexive": False},
    # Case-study-derived relations (E5 multi-agent literature review)
    "feeds-into": {"transitive": True, "symmetric": False, "irreflexive": False},
    "complements": {"transitive": False, "symmetric": False, "irreflexive": False},
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
        if chars.get("irreflexive"):
            SubElement(prop, "rdf:type").set("rdf:resource", f"{OWL_NS}IrreflexiveProperty")


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
        if chars.get("irreflexive"):
            lines[-1] += " ;"
            lines.append("    a owl:IrreflexiveProperty")
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
            # SWRL namespaces must be declared on the root element so that the
            # swrl:* / swrlb:* atoms emitted by _build_swrl_rules_rdfxml bind to
            # a prefix.  Without these, the serialized RDF/XML is invalid
            # (unbound prefix) and cannot be parsed back.
            "xmlns:swrl": SWRL_NS,
            "xmlns:swrlb": SWRLB_NS,
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

    # Concept individual — MUST be emitted BEFORE the ontology header and the
    # schema/property/class declarations.  parse_owl_turtle identifies the
    # concept as the *first* Turtle line containing " a "; if the ontology
    # header (`adl: a owl:Ontology`) or the class declarations appeared first,
    # the importer would mis-detect them as the concept and raise
    # "Could not find concept declaration".  Triple ordering is semantically
    # irrelevant in Turtle, so moving the instance data first is safe.
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

    # Events (from chain)
    for event in doc.event_chain.events:
        lines.append(f"<http://adl-lite.org/ontology/event/{event.event_id}> a adl:Event ;")
        lines.append(f"    adl:belongsTo adl:{doc.adl_id} ;")
        lines.append(f'    adl:hasActor "{event.actor}" ;')
        lines.append(f'    adl:hasTimestamp "{event.timestamp}"^^xsd:dateTime .')
        lines.append("")

    # L3 relation assertions
    _add_relation_assertions_turtle(lines, doc)

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
# Full Ontology Export (schema-only, no instance data)
# ---------------------------------------------------------------------------


def _build_ontology_header_turtle() -> list[str]:
    """Return Turtle lines for the ontology header and prefixes."""
    return [
        "@prefix : <http://adl-lite.org/ontology/> .",
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix xml: <http://www.w3.org/XML/1998/namespace> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix dc: <http://purl.org/dc/elements/1.1/> .",
        "@prefix dcterms: <http://purl.org/dc/terms/> .",
        "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
        "@prefix prov: <http://www.w3.org/ns/prov#> .",
        "@prefix bfo: <http://purl.obolibrary.org/obo/> .",
        "@prefix iao: <http://purl.obolibrary.org/obo/> .",
        "@prefix swrl: <http://www.w3.org/2003/11/swrl#> .",
        "@prefix swrlb: <http://www.w3.org/2003/11/swrlb#> .",
        "@prefix adl: <http://adl-lite.org/ontology/> .",
        "",
        "@base <http://adl-lite.org/ontology/> .",
        "",
        "<http://adl-lite.org/ontology/> a owl:Ontology ;",
        "    owl:versionIRI <http://adl-lite.org/ontology/0.5.0/> ;",
        '    dc:title "ADL Lite Ontology" ;',
        '    dc:description "OWL 2 DL module for the ADL Lite capability-lifecycle registry." ;',
        '    dcterms:creator "ADL Lite Project" ;',
        "    dcterms:license <https://opensource.org/licenses/MIT> ;",
        '    owl:versionInfo "0.5.0-alpha" ;',
        '    rdfs:comment "This ontology is intentionally scoped to OWL 2 DL expressivity. Temporal reasoning, derived-state aggregation, and cryptographic verification are handled by the ADL Lite runtime." ;',
        "    rdfs:seeAlso <https://github.com/sunnyang1/adl-lite> .",
        "",
    ]


def _build_annotation_properties_turtle() -> list[str]:
    """Return Turtle lines for annotation properties."""
    return [
        "# --- Annotation Properties ---",
        "",
        ":provenanceNote a owl:AnnotationProperty ;",
        '    rdfs:label "provenance note" ;',
        '    rdfs:comment "Human-readable provenance annotation for ontology elements." .',
        "",
        ":adlVersion a owl:AnnotationProperty ;",
        '    rdfs:label "ADL version" ;',
        "    rdfs:range xsd:string ;",
        '    rdfs:comment "Version of the ADL Lite specification that introduced this term." .',
        "",
        ":sourceFile a owl:AnnotationProperty ;",
        '    rdfs:label "source file" ;',
        "    rdfs:range xsd:anyURI ;",
        '    rdfs:comment "Path or URI to the source document that defined this term." .',
        "",
    ]


def _build_bfo_iao_alignment_turtle() -> list[str]:
    """Return Turtle lines for BFO and IAO external class declarations."""
    return [
        "# --- BFO / IAO Alignment ---",
        "",
        "bfo:BFO_0000002 a owl:Class ;",
        '    rdfs:label "continuant" ;',
        '    rdfs:comment "BFO class: continuant." .',
        "",
        "bfo:BFO_0000003 a owl:Class ;",
        '    rdfs:label "occurrent" ;',
        '    rdfs:comment "BFO class: occurrent." .',
        "",
        "bfo:BFO_0000015 a owl:Class ;",
        "    rdfs:subClassOf bfo:BFO_0000003 ;",
        '    rdfs:label "process" ;',
        '    rdfs:comment "BFO class: process." .',
        "",
        "bfo:BFO_0000031 a owl:Class ;",
        "    rdfs:subClassOf bfo:BFO_0000002 ;",
        '    rdfs:label "generically dependent continuant" ;',
        '    rdfs:comment "BFO class: GDC." .',
        "",
        "iao:IAO_0000030 a owl:Class ;",
        "    rdfs:subClassOf bfo:BFO_0000031 ;",
        '    rdfs:label "information content entity" ;',
        '    rdfs:comment "IAO class: ICE." .',
        "",
    ]


def _build_adl_classes_turtle() -> list[str]:
    """Return Turtle lines for all ADL core classes."""
    classes = [
        ("Concept", "bfo:BFO_0000031", "An ADL capability or discovery."),
        ("Event", "bfo:BFO_0000003", "An atomic occurrence in a capability's lifecycle."),
        (
            "EventChain",
            "bfo:BFO_0000015",
            "An append-only, cryptographically linked chain of events.",
        ),
        ("EventChainRecord", "iao:IAO_0000030", "An ICE that concretises an EventChain."),
        ("Actor", "prov:Agent", "An agent that participates in ADL events."),
        ("Relation", ":Concept", "A typed semantic relation between two ADL concepts."),
        ("Action", ":Event", "An L4 action event."),
        ("Evidence", ":Concept", "Structured evidence attached to a concept or relation."),
        ("FormalSeal", ":Concept", "A cryptographic or formal-verification attestation."),
        ("Discovery", ":Concept", "A newly discovered capability before full validation."),
    ]
    lines = ["# --- Core ADL Classes ---", ""]
    for cls, parent, comment in classes:
        lines.append(f"adl:{cls} a owl:Class ;")
        lines.append(f"    rdfs:subClassOf {parent} ;")
        lines.append(
            f'    rdfs:label "{cls.replace("Chain", " Chain").replace("Seal", " Seal")}" ;'
        )
        lines.append(f'    rdfs:comment "{comment}" ;')
        lines.append('    :adlVersion "0.2" .')
        lines.append("")
    return lines


def _build_disjointness_turtle() -> list[str]:
    """Return Turtle lines for disjointness axioms."""
    return [
        "# --- Disjointness Axioms ---",
        "",
        "adl:Event owl:disjointWith bfo:BFO_0000002 .",
        "adl:EventChain owl:disjointWith bfo:BFO_0000002 .",
        "adl:Concept owl:disjointWith bfo:BFO_0000003 .",
        "adl:EventChainRecord owl:disjointWith bfo:BFO_0000003 .",
        "",
    ]


def _build_core_object_properties_extended_turtle() -> list[str]:
    """Return Turtle lines for extended core object properties."""
    props = [
        ("hasStatus", "Concept", "DiscoveryStatus", "Derived lifecycle status of a concept."),
        ("belongsTo", "Event", "EventChain", "Links an event to the event chain it belongs to."),
        (
            "validatedBy",
            "Concept",
            "Actor",
            "Links a validated concept to its validating actor(s).",
        ),
        ("hasEvent", "EventChain", "Event", "Links an event chain to its constituent events."),
        ("follows", "Event", "Event", "Temporal ordering within an event chain."),
        ("hasSource", "Relation", "Concept", "Source concept of a typed relation."),
        ("hasTarget", "Relation", "Concept", "Target concept of a typed relation."),
        (
            "isAbout",
            "EventChainRecord",
            "EventChain",
            "IAO alignment: an ICE is about the event chain it records.",
        ),
        (
            "concretises",
            "EventChainRecord",
            "EventChain",
            "BFO alignment: an ICE concretises the process it records.",
        ),
        (
            "wasAssociatedWith",
            "Event",
            "Actor",
            "PROV-O alignment: the actor associated with an event.",
        ),
        (
            "wasGeneratedBy",
            "Concept",
            "Event",
            "PROV-O alignment: a concept was generated by an event in its chain.",
        ),
    ]
    lines = ["# --- Core Object Properties ---", ""]
    for pname, domain, range_cls, comment in props:
        lines.append(f"adl:{pname} a owl:ObjectProperty ;")
        lines.append(
            f'    rdfs:label "{pname.replace("has", "has ").replace("was", "was ").replace("is", "is ").replace("concretises", "concretises ")}" ;'
        )
        lines.append(f"    rdfs:domain adl:{domain} ;")
        if range_cls.startswith(("bfo:", "iao:", "prov:", ":")):
            lines.append(f"    rdfs:range {range_cls} ;")
        else:
            lines.append(f"    rdfs:range adl:{range_cls} ;")
        lines.append(f'    rdfs:comment "{comment}" .')
        lines.append("")
    return lines


def _build_data_properties_extended_turtle() -> list[str]:
    """Return Turtle lines for extended datatype properties."""
    props = [
        ("hasConfidence", "Concept", "xsd:float", "Confidence score in [0.0, 1.0]."),
        ("hasConceptId", "Concept", "xsd:string", "Unique alphanumeric identifier for a concept."),
        ("hasDomain", "Concept", "xsd:string", "Domain tag, e.g. 'financial_aml'."),
        ("hasScope", "Concept", "xsd:string", "Namespace scope."),
        ("hasActor", "Event", "xsd:string", "Identifier of the agent causing the event."),
        ("hasTimestamp", "Event", "xsd:dateTime", "ISO 8601 timestamp of the event."),
        (
            "hasEventHash",
            "Event",
            "xsd:string",
            "SHA-256 cryptographic hash of the event content (64 hex chars).",
        ),
        (
            "hasPreviousHash",
            "Event",
            "xsd:string",
            "SHA-256 hash of the predecessor event in the chain.",
        ),
        ("hasEventType", "Event", "xsd:string", "Event type: register, validate, etc."),
        ("hasActionType", "Action", "xsd:string", "L4 action type."),
        (
            "hasRelationPredicate",
            "Relation",
            "xsd:string",
            "String name of the L3 relation predicate.",
        ),
        (
            "hasMappingType",
            "Relation",
            "xsd:string",
            "Mapping type: topological, ontological, etc.",
        ),
        ("hasEvidenceType", "Evidence", "xsd:string", "Evidence taxonomy."),
        ("hasNovelty", "Concept", "xsd:float", "Novelty score in [0.0, 1.0]."),
        ("hasPayload", "Event", "xsd:string", "JSON-serialised event payload."),
        ("hasSignature", "Event", "xsd:string", "Optional Ed25519 base64 signature."),
    ]
    lines = ["# --- OWL DatatypeProperties ---", ""]
    for pname, domain, dtype, comment in props:
        lines.append(f"adl:{pname} a owl:DatatypeProperty ;")
        lines.append(f'    rdfs:label "{pname.replace("has", "has ")}" ;')
        lines.append(f"    rdfs:domain adl:{domain} ;")
        lines.append(f"    rdfs:range {dtype} ;")
        lines.append(f'    rdfs:comment "{comment}" .')
        lines.append("")
    return lines


def _build_status_individuals_turtle() -> list[str]:
    """Return Turtle lines for status named individuals."""
    statuses = [
        ("provisional", "Initial status after registration."),
        ("validated", "Approved by at least N_min validators."),
        ("deprecated", "Marked as obsolete but still queryable."),
        ("forked", "Forked into competing interpretations."),
        ("archived", "Frozen and moved to cold storage."),
    ]
    lines = ["# --- Status Named Individuals ---", ""]
    for status, comment in statuses:
        lines.append(f"adl:status_{status} a owl:NamedIndividual , adl:DiscoveryStatus ;")
        lines.append(f'    rdfs:label "{status}" ;')
        lines.append(f'    rdfs:comment "{comment}" .')
        lines.append("")
    lines.append("adl:DiscoveryStatus a owl:Class ;")
    lines.append('    rdfs:label "Discovery Status" ;')
    lines.append("    owl:equivalentClass [")
    lines.append("        a owl:Class ;")
    lines.append(
        "        owl:oneOf (adl:status_provisional adl:status_validated adl:status_deprecated adl:status_forked adl:status_archived)"
    )
    lines.append("    ] ;")
    lines.append('    rdfs:comment "Enumeration of lifecycle statuses." .')
    lines.append("")
    return lines


def export_ontology_turtle(include_swrl: bool = True) -> str:
    """
    Export the full ADL Lite OWL 2 DL ontology as Turtle (schema only, no instance data).

    Args:
        include_swrl: Whether to embed SWRL integrity rules.

    Returns:
        Complete OWL 2 DL Turtle ontology as a string.
    """
    lines: list[str] = []
    lines.extend(_build_ontology_header_turtle())
    lines.extend(_build_annotation_properties_turtle())
    lines.extend(_build_bfo_iao_alignment_turtle())
    lines.extend(_build_adl_classes_turtle())
    lines.extend(_build_disjointness_turtle())
    lines.extend(_build_core_object_properties_extended_turtle())
    lines.extend(_build_l3_object_properties_turtle())
    lines.extend(_build_data_properties_extended_turtle())
    lines.extend(_build_status_individuals_turtle())
    if include_swrl:
        lines.extend(_build_swrl_rules_turtle())
    return "\n".join(lines)


def export_ontology(format: str = "turtle", include_swrl: bool = True) -> str:
    """
    Export the full ADL Lite OWL 2 DL ontology (schema only, no instance data).

    Args:
        format: "turtle" or "rdfxml"
        include_swrl: Embed SWRL integrity rules.

    Returns:
        OWL ontology serialization as a string
    """
    if format == "turtle":
        return export_ontology_turtle(include_swrl=include_swrl)
    # For RDF/XML, return the existing schema-building approach or raise
    raise NotImplementedError(
        "RDF/XML full-ontology export is not yet implemented. Use format='turtle'."
    )


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
