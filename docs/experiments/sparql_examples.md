# SPARQL Examples over ADL Lite RDF-star Export

These queries operate on the RDF-star serialization produced by `adl_lite.prov_export.to_rdfstar()`.

## Prerequisites

```bash
pip install rdflib
```

## Q1 — Relation Provenance

**Question:** For a given concept, list all its L3 relation assertions together with the event hash, actor, and timestamp that generated them.

```sparql
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX adl:  <https://adl-lite.org/ns/>

SELECT ?source ?relation ?target ?eventHash ?actor ?timestamp
WHERE {
  ?qt << ?source ?relation ?target >> .
  ?qt adl:eventHash ?eventHash ;
      prov:wasGeneratedBy ?event .
  ?event prov:wasAssociatedWith ?actor ;
         prov:startedAtTime ?timestamp .
}
```

## Q2 — Status Derivation from Event Chain

**Question:** Compute the current status of a concept by finding the most advanced lifecycle event in its chain.

```sparql
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX adl:  <https://adl-lite.org/ns/>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?concept (MAX(?statusOrder) AS ?currentStatusOrder)
WHERE {
  ?concept a prov:Entity ;
           prov:wasGeneratedBy ?event .
  ?event a adl:RegisterEvent .
  BIND(1 AS ?statusOrder)
}
UNION
{
  ?concept a prov:Entity ;
           prov:wasGeneratedBy ?event .
  ?event a adl:ValidateEvent .
  BIND(3 AS ?statusOrder)
}
UNION
{
  ?concept a prov:Entity ;
           prov:wasGeneratedBy ?event .
  ?event a adl:DeprecateEvent .
  BIND(4 AS ?statusOrder)
}
GROUP BY ?concept
```

## Q3 — Actor Influence

**Question:** Count how many concepts each actor has validated.

```sparql
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX adl:  <https://adl-lite.org/ns/>

SELECT ?actor (COUNT(DISTINCT ?concept) AS ?validatedConcepts)
WHERE {
  ?event a adl:ValidateEvent ;
         prov:wasAssociatedWith ?actor .
  ?concept prov:wasGeneratedBy ?event .
}
GROUP BY ?actor
ORDER BY DESC(?validatedConcepts)
```

## Q4 — Tamper Detection via Hash Mismatch

**Question:** Find all events where the stored hash does not match a recomputed hash (simulated integrity violation).

```sparql
PREFIX adl: <https://adl-lite.org/ns/>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?event ?storedHash
WHERE {
  ?event a prov:Activity ;
         adl:eventHash ?storedHash .
  # In a real endpoint, a custom SPARQL extension or
  # post-processing would recompute SHA-256(canonical(event))
  # and compare against ?storedHash.
  FILTER(STRLEN(?storedHash) != 64)
}
```

## Running the Examples

```python
from rdflib import Graph
from adl_lite.parser import parse_file
from adl_lite.prov_export import to_rdfstar

doc = parse_file("examples/capital_reflux_trap.md")
g = Graph()
g.parse(data=to_rdfstar(doc.event_chain), format="turtle")

# Q1
q1 = open("docs/experiments/sparql_examples.md").read().split("```sparql")[1].split("```")[0]
for row in g.query(q1):
    print(row)
```
