"""
RDF-star / SPARQL-star Export for ADL Lite (FW8).

RDF-star extends RDF with embedded triples (annotations on triples).
This enables representing ADL events as annotated statements:
  <<adl:concept adl:hasStatus adl:validated>> adl:hasActor "agent_1" ;
                                            adl:hasConfidence 0.85 .

SPARQL-star extends SPARQL to query these embedded triples.

Paper §7.2: "Semantic Web interoperability through OWL 2 DL, SHACL,
PROV-O, and JSON-LD pathways." RDF-star/SPARQL-star is the fifth
pathway, enabling reified event provenance.
"""

from __future__ import annotations

from .models import ADLDocument, EventType

ADL_NS = "http://adl-lite.org/ontology/"
XSD_NS = "http://www.w3.org/2001/XMLSchema#"


def event_to_rdfstar_triple(event) -> str:
    """
    Convert a single ADL event to an RDF-star triple annotation.

    For VALIDATE events:
      <<adl:{concept_id} adl:hasStatus adl:status/validated>>
          adl:hasActor "{actor}" ;
          adl:hasConfidence {confidence} ;
          adl:hasTimestamp "{timestamp}"^^xsd:dateTime .

    For REGISTER events:
      <<adl:{concept_id} rdf:type adl:discovery>>
          adl:hasActor "{actor}" ;
          adl:hasTimestamp "{timestamp}"^^xsd:dateTime .
    """
    concept_uri = f"adl:{event.concept_id}"
    actor = event.actor
    timestamp = event.timestamp
    confidence = float(event.payload.get("confidence", 0.0))

    if event.event_type == EventType.VALIDATE:
        status = "adl:status/validated"
        lines = [
            f'    <<{concept_uri} adl:hasStatus {status}>>',
            f'        adl:hasActor "{actor}" ;',
            f'        adl:hasConfidence {confidence} ;',
            f'        adl:hasTimestamp "{timestamp}"^^xsd:dateTime .',
        ]
    elif event.event_type == EventType.REGISTER:
        lines = [
            f'    <<{concept_uri} rdf:type adl:discovery>>',
            f'        adl:hasActor "{actor}" ;',
            f'        adl:hasTimestamp "{timestamp}"^^xsd:dateTime .',
        ]
    elif event.event_type == EventType.DEPRECATE:
        lines = [
            f'    <<{concept_uri} adl:hasStatus adl:status/deprecated>>',
            f'        adl:hasActor "{actor}" ;',
            f'        adl:hasTimestamp "{timestamp}"^^xsd:dateTime .',
        ]
    elif event.event_type == EventType.ARCHIVE:
        lines = [
            f'    <<{concept_uri} adl:hasStatus adl:status/archived>>',
            f'        adl:hasActor "{actor}" ;',
            f'        adl:hasTimestamp "{timestamp}"^^xsd:dateTime .',
        ]
    else:
        # Generic fallback for other event types
        evt_name = event.event_type.value
        lines = [
            f'    <<{concept_uri} adl:hasEventType adl:eventType/{evt_name}>>',
            f'        adl:hasActor "{actor}" ;',
            f'        adl:hasTimestamp "{timestamp}"^^xsd:dateTime .',
        ]

    return "\n".join(lines)


def document_to_rdfstar_turtle(doc: ADLDocument) -> str:
    """
    Convert an ADLDocument to RDF-star Turtle syntax.

    Returns a Turtle string with embedded triples for each event,
    suitable for ingestion into RDF-star enabled triple stores
    (e.g., Apache Jena, GraphDB, Stardog).
    """
    lines: list[str] = [
        "@prefix adl: <http://adl-lite.org/ontology/> .",
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "",
        f"adl:{doc.adl_id} a adl:{doc.front_matter.adl_type.value} ;",
        f'    adl:hasStatus adl:status/{doc.front_matter.status.value} ;',
        f'    adl:hasConfidence "{doc.front_matter.confidence}"^^xsd:float ;',
    ]

    for validator in doc.front_matter.validators:
        lines.append(f'    adl:validatedBy adl:agent/{validator} ;')

    if doc.front_matter.domain:
        lines.append(f'    adl:hasDomain "{doc.front_matter.domain}" ;')

    lines.append(f'    adl:hasScope "{doc.front_matter.scope}" .')
    lines.append("")

    # RDF-star annotations for each event
    for event in doc.event_chain.events:
        if event.event_type in (EventType.SNAPSHOT,):
            # Skip synthetic snapshot events — not meaningful as RDF-star annotations
            continue
        lines.append(event_to_rdfstar_triple(event))
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# SPARQL-star Query Scaffold
# ---------------------------------------------------------------------------


def sparqlstar_query_template(concept_id: str, event_type: EventType | None = None) -> str:
    """
    Generate a SPARQL-star query template for an ADL concept.

    Example output:
      SELECT ?actor ?confidence ?timestamp
      WHERE {
        <<adl:disc-test adl:hasStatus adl:status/validated>>
            adl:hasActor ?actor ;
            adl:hasConfidence ?confidence ;
            adl:hasTimestamp ?timestamp .
      }

    This is a scaffold — not a full query engine. It generates the
    SPARQL-star syntax for ingestion into a real triple store.
    """
    concept_uri = f"adl:{concept_id}"

    if event_type == EventType.VALIDATE:
        embedded = f"<<{concept_uri} adl:hasStatus adl:status/validated>>"
    elif event_type == EventType.REGISTER:
        embedded = f"<<{concept_uri} rdf:type adl:discovery>>"
    elif event_type == EventType.DEPRECATE:
        embedded = f"<<{concept_uri} adl:hasStatus adl:status/deprecated>>"
    elif event_type == EventType.ARCHIVE:
        embedded = f"<<{concept_uri} adl:hasStatus adl:status/archived>>"
    else:
        embedded = f"<<{concept_uri} ?p ?o>>"

    query = f"""SELECT ?actor ?confidence ?timestamp
WHERE {{
    {embedded}
        adl:hasActor ?actor ;
        adl:hasConfidence ?confidence ;
        adl:hasTimestamp ?timestamp .
}}"""
    return query
