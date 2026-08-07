#!/usr/bin/env python3
"""Competency Question (CQ) verification for the ADL Lite OWL~2 DL fragment.

Reproducibility guard for the Applied Ontology paper's claim (appendix_a.tex,
lines 442) that "All fourteen competency questions (CQ1--CQ14) were executed as
SPARQL queries against a populated test dataset ... All queries returned
expected results."

What this script does
---------------------
1. Hard-codes the 14 SPARQL queries exactly as printed in appendix_a.tex
   (lines 227-387) and *cross-checks* them against the verbatim blocks
   extracted from the .tex, so the queries are provably the ones in the paper.
2. Loads the published OWL fragment (supplementary/adl_lite_core_v2.owl).
3. Executes each CQ:
     - TBox CQs (CQ1-CQ8, CQ14) run against the pure ontology graph.
     - ABox CQs (CQ9-CQ13) run against a minimal, documented synthetic
       dataset that is *consistent* with the fragment's axioms, mirroring the
       paper's "populated test dataset" methodology.
4. Asserts the result matches the expectation stated in the paper, prints a
   pass/fail table, and exits 0 iff all 14 pass.

Usage
-----
    python scripts/verify_competency_questions.py
    python scripts/verify_competency_questions.py --json   # machine-readable

Exit code 0 = all CQs pass; 1 = at least one CQ fails (drift/claim broken).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import OWL, RDF, RDFS, XSD

ROOT = Path(__file__).resolve().parent.parent
ONTOLOGY = ROOT / "docs" / "paper_ao" / "supplementary" / "adl_lite_core_v2.owl"
APPENDIX_A = ROOT / "docs" / "paper_ao" / "sections" / "appendix_a.tex"

ADL = Namespace("https://adl-lite.org/ontology/v2#")
BFO = Namespace("http://purl.obolibrary.org/obo/BFO_")
IAO = Namespace("http://purl.obolibrary.org/obo/IAO_")


# ---------------------------------------------------------------------------
# CQ definitions -- queries transcribed verbatim from appendix_a.tex.
# The `expected` spec is read directly from the paper's "=> answered by" note.
# ---------------------------------------------------------------------------
CQS: list[dict] = [
    {
        "id": "CQ1",
        "question": "Which BFO category does an ADL Lite Event belong to?",
        "mode": "tbox",
        "query": """PREFIX adl: <https://adl-lite.org/ontology/v2#>
PREFIX bfo: <http://purl.obolibrary.org/obo/BFO_>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?superclass
WHERE {
    adl:Event rdfs:subClassOf ?superclass .
}""",
        "expected": {"kind": "contains", "values": [BFO["0000003"]]},
        "paper_note": "adl:Event sqsubseteq bfo:occurrent (BFO_0000003)",
    },
    {
        "id": "CQ2",
        "question": "Which BFO category does an ADL Lite Concept belong to?",
        "mode": "tbox",
        "query": """PREFIX adl: <https://adl-lite.org/ontology/v2#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?superclass
WHERE {
    adl:Concept rdfs:subClassOf ?superclass .
}""",
        "expected": {"kind": "contains", "values": [BFO["0000031"]]},
        "paper_note": "adl:Concept sqsubseteq bfo:GDC (BFO_0000031)",
    },
    {
        "id": "CQ3",
        "question": "Is the isomorphic-to relation symmetric?",
        "mode": "tbox",
        "query": """PREFIX adl: <https://adl-lite.org/ontology/v2#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
ASK
WHERE {
    adl:isomorphicTo rdf:type owl:SymmetricProperty .
}""",
        "expected": {"kind": "ask", "value": True},
        "paper_note": "owl:SymmetricProperty",
    },
    {
        "id": "CQ4",
        "question": "Is the specialisation-of relation transitive?",
        "mode": "tbox",
        "query": """PREFIX adl: <https://adl-lite.org/ontology/v2#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
ASK
WHERE {
    adl:specialisationOf rdf:type owl:TransitiveProperty .
}""",
        "expected": {"kind": "ask", "value": True},
        "paper_note": "owl:TransitiveProperty",
    },
    {
        "id": "CQ5",
        "question": "Is the specialisation-of relation irreflexive?",
        "mode": "tbox",
        "query": """PREFIX adl: <https://adl-lite.org/ontology/v2#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
ASK
WHERE {
    adl:specialisationOf rdf:type owl:IrreflexiveProperty .
}""",
        "expected": {"kind": "ask", "value": True},
        "paper_note": "owl:IrreflexiveProperty",
    },
    {
        "id": "CQ6",
        "question": "Can a concept be related to itself via isomorphic-to?",
        "mode": "tbox",
        "query": """PREFIX adl: <https://adl-lite.org/ontology/v2#>
SELECT ?concept
WHERE {
    ?concept adl:isomorphicTo ?concept .
}""",
        "expected": {"kind": "empty"},
        "paper_note": "not constrained in the fragment; SHACL shape prevents self-relation",
    },
    {
        "id": "CQ7",
        "question": "Which class represents the serialized chain record?",
        "mode": "tbox",
        "query": """PREFIX adl: <https://adl-lite.org/ontology/v2#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?class ?superclass
WHERE {
    adl:EventChainRecord rdfs:subClassOf ?superclass .
    BIND(adl:EventChainRecord AS ?class)
}""",
        "expected": {"kind": "contains", "values": [IAO["0000030"]]},
        "paper_note": "adl:EventChainRecord sqsubseteq iao:information_content_entity (IAO_0000030)",
    },
    {
        "id": "CQ8",
        "question": "Are the process and record layers disjoint?",
        "mode": "tbox",
        "query": """PREFIX adl: <https://adl-lite.org/ontology/v2#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
ASK
WHERE {
    [] rdf:type owl:AllDisjointClasses ;
       owl:members (adl:EventChain adl:EventChainRecord) .
}""",
        "expected": {"kind": "ask", "value": True},
        "paper_note": "owl:AllDisjointClasses on adl:EventChain and adl:EventChainRecord",
    },
    {
        "id": "CQ9",
        "question": "Which concepts have a status of validated with confidence >= 0.5?",
        "mode": "abox",
        "query": """PREFIX adl: <https://adl-lite.org/ontology/v2#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?chain ?confidence
WHERE {
    ?chain adl:hasStatus adl:validated ;
           adl:hasConfidence ?confidence .
    FILTER (?confidence >= 0.5)
}""",
        "expected": {"kind": "contains_uri", "values": [ADL["chain_validated_ok"]]},
        "paper_note": "tests the validated_min_confidence constraint",
    },
    {
        "id": "CQ10",
        "question": "Which events have a SHA-256 hash linking them to a previous event?",
        "mode": "abox",
        "query": """PREFIX adl: <https://adl-lite.org/ontology/v2#>
SELECT ?event ?hash ?previous
WHERE {
    ?event adl:hasSHA256Hash ?hash ;
           adl:hasPreviousEvent ?previous .
}""",
        "expected": {"kind": "contains_uri", "values": [ADL["evt_validate"]]},
        "paper_note": "tests the cryptographic chain linkage",
    },
    {
        "id": "CQ11",
        "question": "What is the genesis hash of a given concept?",
        "mode": "abox",
        "query": """PREFIX adl: <https://adl-lite.org/ontology/v2#>
SELECT ?concept ?hash
WHERE {
    ?concept a adl:Concept ;
             adl:hasGenesisHash ?hash .
}""",
        "expected": {"kind": "contains_uri", "values": [ADL["concept_alpha"], ADL["concept_beta"]]},
        "paper_note": "tests the functional identity criterion; each concept has exactly one hash",
    },
    {
        "id": "CQ12",
        "question": "Which concept is the parent of a forked concept?",
        "mode": "abox",
        "query": """PREFIX adl: <https://adl-lite.org/ontology/v2#>
SELECT ?child ?parent
WHERE {
    ?child a adl:Concept ;
           adl:hasParentConcept ?parent .
}""",
        "expected": {"kind": "contains_uri", "values": [ADL["concept_beta"]]},
        "paper_note": "tests the FORK lineage subproperty chain; parent is the immediate ancestor",
    },
    {
        "id": "CQ13",
        "question": "Which event chains were merged to produce a given chain?",
        "mode": "abox",
        "query": """PREFIX adl: <https://adl-lite.org/ontology/v2#>
SELECT ?merged ?source
WHERE {
    ?merged adl:mergedFrom ?source .
    ?source a adl:EventChain .
}""",
        "expected": {"kind": "contains_uri", "values": [ADL["chain_merged"]]},
        "paper_note": "tests the CRDT merge structural linkage; sources are the pre-merge branches",
    },
    {
        "id": "CQ14",
        "question": "Is the fork-of relation a subproperty of was-derived-from?",
        "mode": "tbox",
        "query": """PREFIX adl: <https://adl-lite.org/ontology/v2#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
ASK
WHERE {
    adl:forkOf rdfs:subPropertyOf adl:wasDerivedFrom .
}""",
        "expected": {"kind": "ask", "value": True},
        "paper_note": "answered by rdfs:subPropertyOf; PROV-O alignment",
    },
]


# ---------------------------------------------------------------------------
# Remediation axioms (OPT-IN, --remediation)
#
# The published supplementary fragment (adl_lite_core_v2.owl) is missing the
# FORK-lineage / identity / CRDT-merge axioms that appendix_a.tex claims are
# present (coverage table lines 415-417; CQ11-CQ14). Those axioms DO exist in
# the canonical formal ontology formal/owl/adl_lite_ontology.ttl (lines
# 550-599). This patch reproduces them verbatim (namespace mapped : -> adl:)
# so that the paper's "all fourteen CQs pass" claim can be checked against the
# *intended* fragment. It is applied to a COPY of the graph only; the
# published .owl file is never modified.
# ---------------------------------------------------------------------------
REMEDIATION_AXIOMS: list[tuple] = [
    # I2: functional identity criterion (formal/owl lines 551-557)
    (ADL.hasGenesisHash, RDF.type, OWL.DatatypeProperty),
    (ADL.hasGenesisHash, RDF.type, OWL.FunctionalProperty),
    (ADL.hasGenesisHash, RDFS.domain, ADL.Concept),
    (ADL.hasGenesisHash, RDFS.range, XSD.string),
    # PROV-O alignment: wasDerivedFrom (formal/owl lines 560-566)
    (ADL.wasDerivedFrom, RDF.type, OWL.ObjectProperty),
    (ADL.wasDerivedFrom, RDFS.domain, ADL.Concept),
    (ADL.wasDerivedFrom, RDFS.range, ADL.Concept),
    # CQ14 axiom: forkOf is a subproperty of wasDerivedFrom (line 568)
    (ADL.forkOf, RDFS.subPropertyOf, ADL.wasDerivedFrom),
    # hasParentConcept: immediate-parent link, subproperty of forkOf (571-577)
    (ADL.hasParentConcept, RDF.type, OWL.ObjectProperty),
    (ADL.hasParentConcept, RDFS.domain, ADL.Concept),
    (ADL.hasParentConcept, RDFS.range, ADL.Concept),
    (ADL.hasParentConcept, RDFS.subPropertyOf, ADL.forkOf),
    # mergedFrom: CRDT merge structural linkage (586-591)
    (ADL.mergedFrom, RDF.type, OWL.ObjectProperty),
    (ADL.mergedFrom, RDFS.domain, ADL.EventChain),
    (ADL.mergedFrom, RDFS.range, ADL.EventChain),
]


def apply_remediation(graph: Graph) -> Graph:
    g = Graph()
    g += graph
    for s, p, o in REMEDIATION_AXIOMS:
        g.add((s, p, o))
    return g


# ---------------------------------------------------------------------------
# Minimal synthetic ABox (CQ9-CQ13) -- documented in the paper's methodology
# as a "populated test dataset". The dataset is consistent with the fragment:
# every validated chain carries confidence >= 0.5, events chain via
# hasPreviousEvent, and concepts carry exactly one genesis hash.
# ---------------------------------------------------------------------------
def build_abox() -> Graph:
    g = Graph()
    g.bind("adl", ADL)

    # --- lifecycle events (CQ10) ---
    g.add((ADL["evt_register"], RDF.type, ADL.RegisterEvent))
    g.add(
        (
            ADL["evt_register"],
            ADL.hasSHA256Hash,
            Literal("a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2", datatype=XSD.hexBinary),
        )
    )
    g.add((ADL["evt_validate"], RDF.type, ADL.ValidateEvent))
    g.add(
        (
            ADL["evt_validate"],
            ADL.hasSHA256Hash,
            Literal("f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5", datatype=XSD.hexBinary),
        )
    )
    g.add((ADL["evt_validate"], ADL.hasPreviousEvent, ADL["evt_register"]))

    # --- event chains (CQ9, CQ13) ---
    g.add((ADL["chain_validated_ok"], RDF.type, ADL.EventChain))
    g.add((ADL["chain_validated_ok"], ADL.hasStatus, ADL.validated))
    g.add((ADL["chain_validated_ok"], ADL.hasConfidence, Literal("0.87", datatype=XSD.float)))

    g.add((ADL["chain_provisional_low"], RDF.type, ADL.EventChain))
    g.add((ADL["chain_provisional_low"], ADL.hasStatus, ADL.provisional))
    g.add((ADL["chain_provisional_low"], ADL.hasConfidence, Literal("0.42", datatype=XSD.float)))

    g.add((ADL["chain_merged"], RDF.type, ADL.EventChain))
    g.add((ADL["chain_merged"], ADL.mergedFrom, ADL["chain_validated_ok"]))
    g.add((ADL["chain_merged"], ADL.mergedFrom, ADL["chain_provisional_low"]))

    # --- event chain records (CQ9 chain -> record production) ---
    g.add((ADL["record_ok"], RDF.type, ADL.EventChainRecord))
    g.add((ADL["chain_validated_ok"], ADL.causallyProduces, ADL["record_ok"]))

    # --- concepts (CQ11, CQ12) ---
    g.add((ADL["concept_alpha"], RDF.type, ADL.Concept))
    g.add(
        (
            ADL["concept_alpha"],
            ADL.hasGenesisHash,
            Literal("aaaa1111bbbb2222cccc3333dddd4444", datatype=XSD.hexBinary),
        )
    )
    g.add((ADL["concept_alpha"], ADL.dependsOnRecord, ADL["record_ok"]))

    g.add((ADL["concept_beta"], RDF.type, ADL.Concept))
    g.add(
        (
            ADL["concept_beta"],
            ADL.hasGenesisHash,
            Literal("bbbb2222cccc3333dddd4444eeee5555", datatype=XSD.hexBinary),
        )
    )
    g.add((ADL["concept_beta"], ADL.hasParentConcept, ADL["concept_alpha"]))
    g.add((ADL["concept_beta"], ADL.forkOf, ADL["concept_alpha"]))
    return g


# ---------------------------------------------------------------------------
# Verbatim cross-check against appendix_a.tex
# ---------------------------------------------------------------------------
def extract_paper_queries() -> dict[str, str]:
    """Extract SPARQL blocks from the CQ enumerate in appendix_a.tex."""
    text = APPENDIX_A.read_text(encoding="utf-8")
    start = text.find(r"\begin{enumerate}[label=CQ")
    end = text.find(r"\end{enumerate}", start)
    if start < 0 or end < 0:
        return {}
    section = text[start:end]
    blocks = re.findall(r"\\begin\{verbatim\}(.*?)\\end\{verbatim\}", section, re.S)
    # Skip the first verbatim block if it predates CQ1 (there is none) --
    # appendix_a has exactly 14 verbatim blocks inside the CQ enumerate.
    return {f"CQ{i + 1}": b for i, b in enumerate(blocks[: len(CQS)])}


def normalize_sparql(q: str) -> str:
    """Collapse whitespace and strip trailing punctuation for comparison."""
    norm = re.sub(r"\s+", " ", q).strip()
    return norm.rstrip(".")


def check_verbatim() -> dict[str, bool]:
    paper_queries = extract_paper_queries()
    results: dict[str, bool] = {}
    for cq in CQS:
        paper_q = paper_queries.get(cq["id"])
        results[cq["id"]] = bool(paper_q) and normalize_sparql(paper_q or "") == normalize_sparql(
            cq["query"]
        )
    return results


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------
def _rows_contain(result, values: list) -> bool:
    flat = {str(v) for row in result for v in row}
    return all(str(v) in flat for v in values)


def _query_form(query: str) -> str:
    """Return the SPARQL query form (ASK/SELECT/CONSTRUCT/...) ignoring PREFIX lines."""
    for token in query.split():
        if token.upper() in {"SELECT", "ASK", "CONSTRUCT", "DESCRIBE"}:
            return token.upper()
    return ""


def evaluate(cq: dict, graph: Graph) -> tuple[bool, str]:
    """Run one CQ and return (pass, detail)."""
    try:
        if _query_form(cq["query"]) == "ASK":
            ans = graph.query(cq["query"])
            outcome = bool(ans) if isinstance(ans, bool) else bool(ans.askAnswer)
            detail = f"ASK -> {outcome}"
            if cq["expected"]["kind"] == "ask":
                return outcome == cq["expected"]["value"], detail
            return False, f"unexpected spec {cq['expected']}"
        rows = list(graph.query(cq["query"]))
        exp = cq["expected"]
        if exp["kind"] == "empty":
            return len(rows) == 0, f"SELECT -> {len(rows)} row(s)"
        if exp["kind"] == "contains":
            return _rows_contain(rows, exp["values"]), (
                f"SELECT -> {len(rows)} row(s); expected {len(exp['values'])} target(s)"
            )
        if exp["kind"] == "contains_uri":
            return _rows_contain(rows, exp["values"]), (
                f"SELECT -> {len(rows)} row(s); expected instance(s) present"
            )
        return False, f"unexpected spec {exp}"
    except Exception as exc:  # noqa: BLE001 - report query failure as CQ failure
        return False, f"ERROR: {type(exc).__name__}: {exc}"


def run_verification(remediate: bool = False) -> list[dict]:
    # Load the published fragment.
    onto = Graph()
    onto.parse(ONTOLOGY, format="turtle")
    abox = build_abox()
    populated = Graph()
    populated += onto
    populated += abox

    if remediate:
        onto = apply_remediation(onto)
        populated = apply_remediation(populated)

    verbatim_ok = check_verbatim()
    results: list[dict] = []
    for cq in CQS:
        graph = populated if cq["mode"] == "abox" else onto
        passed, detail = evaluate(cq, graph)
        results.append(
            {
                "id": cq["id"],
                "question": cq["question"],
                "paper_note": cq["paper_note"],
                "verbatim_match": verbatim_ok.get(cq["id"], False),
                "pass": passed,
                "detail": detail,
            }
        )
    return results


# ---------------------------------------------------------------------------
# Bonus: corrupted-data constraint checks (mirrors the paper's ROBOT-verify
# data-quality claim, appendix_a lines 389-390, 440). The paper's
# validated_min_confidence constraint is the *negative* pattern: a validated
# chain whose confidence is below 0.5 is a violation and must be flagged.
# CQ9 (the positive query) filters FOR valid chains; the constraint query
# below is the one that detects violations.
# ---------------------------------------------------------------------------
VALIDATED_MIN_CONFIDENCE_VIOLATION = """PREFIX adl: <https://adl-lite.org/ontology/v2#>
SELECT ?chain ?confidence
WHERE {
    ?chain adl:hasStatus adl:validated ;
           adl:hasConfidence ?confidence .
    FILTER (?confidence < 0.5)
}"""


def check_corrupted_data() -> tuple[bool, dict]:
    onto = Graph()
    onto.parse(ONTOLOGY, format="turtle")

    # (a) valid dataset must show zero violations
    valid = Graph()
    valid += onto
    valid += build_abox()
    valid_rows = list(valid.query(VALIDATED_MIN_CONFIDENCE_VIOLATION))
    valid_clean = len(valid_rows) == 0

    # (b) corrupted dataset must flag the violating chain
    bad = Graph()
    bad += onto
    bad.add((ADL["chain_bad"], RDF.type, ADL.EventChain))
    bad.add((ADL["chain_bad"], ADL.hasStatus, ADL.validated))
    bad.add((ADL["chain_bad"], ADL.hasConfidence, Literal("0.30", datatype=XSD.float)))
    bad_rows = list(bad.query(VALIDATED_MIN_CONFIDENCE_VIOLATION))
    flagged = any(str(r[0]) == str(ADL["chain_bad"]) for r in bad_rows)

    info = {
        "valid_data_violations": len(valid_rows),
        "valid_data_clean": valid_clean,
        "corrupted_data_flagged": flagged,
    }
    return valid_clean and flagged, info


def print_table(results: list[dict]) -> None:
    header = f"{'CQ':<6}{'Status':<9}{'Verbatim':<10}{'Result detail':<66}Paper expectation"
    print(header)
    print("-" * len(header))
    for r in results:
        status = "PASS" if r["pass"] else "FAIL"
        verb = "exact" if r["verbatim_match"] else ("MISMATCH" if not r["pass"] else "n/a")
        print(f"{r['id']:<6}{status:<9}{verb:<10}{r['detail']:<66}{r['paper_note']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    ap.add_argument(
        "--remediation",
        action="store_true",
        help="also verify against the fragment plus the FORK/identity/CRDT axioms "
        "that appendix_a.tex claims but the published .owl omits (see REMEDIATION_AXIOMS)",
    )
    args = ap.parse_args()

    results = run_verification(remediate=args.remediation)
    n_pass = sum(1 for r in results if r["pass"])
    n_verbatim = sum(1 for r in results if r["verbatim_match"])
    constraint_ok, constraint_info = check_corrupted_data()

    if args.json:
        print(
            json.dumps(
                {
                    "ontology": str(ONTOLOGY),
                    "remediation": args.remediation,
                    "total_cqs": len(results),
                    "passed": n_pass,
                    "verbatim_matched": n_verbatim,
                    "constraint_validated_min_confidence": constraint_info,
                    "results": results,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(f"Ontology: {ONTOLOGY}")
        if args.remediation:
            print(
                "REMEDIATION MODE: applying FORK/identity/CRDT axioms from "
                "formal/owl/adl_lite_ontology.ttl (see REMEDIATION_AXIOMS)"
            )
        print(
            f"CQ queries cross-checked against {APPENDIX_A.name}: "
            f"{n_verbatim}/{len(results)} verbatim matches"
        )
        print_table(results)
        print(f"\nSUMMARY: {n_pass}/{len(results)} competency questions passed")
        print(
            f"Constraint check validated_min_confidence: valid data -> "
            f"{constraint_info['valid_data_violations']} violation(s) "
            f"{'PASS' if constraint_info['valid_data_clean'] else 'FAIL'}; "
            f"corrupted data -> "
            f"{'flagged' if constraint_info['corrupted_data_flagged'] else 'NOT flagged'} "
            f"{'PASS' if constraint_info['corrupted_data_flagged'] else 'FAIL'}"
        )

    return 0 if n_pass == len(results) and constraint_ok else 1


if __name__ == "__main__":
    sys.exit(main())
