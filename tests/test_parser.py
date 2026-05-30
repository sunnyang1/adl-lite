"""
ADL Lite — Parser & Model Tests

Run: pytest tests/test_parser.py -v
"""

from __future__ import annotations

import pytest

from adl_lite import (
    ADLDocument,
    ADLEvidenceBlock,
    ADLFormalSealBlock,
    ADLFrontMatter,
    ADLParser,
    ADLRelationBlock,
    ADLType,
    ConceptSkeleton,
    ConsensusEngine,
    DiscoveryStatus,
    EvidenceType,
    MechanismType,
    parse_text,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_DOC = """\
---
adl_type: discovery
adl_id: disc-capital-trap
status: provisional
confidence: 0.84
novelty: 0.91
domain: financial_aml
mechanism: isomorphic_mapping
scope: private/ceiec-aml
validators: []
provisional_names:
  zh: "资金注意力陷阱"
  en: "Capital Attention Trap"
evidence_refs:
  - vecdb://clusters/8912
  - tool://aml_simulator/v2
---

# Capital Attention Trap

> Status: 🟡 provisional | Confidence: 84% | Novelty: 91%

The AML transaction network exhibits an anomalous pattern where fund flows
concentrate on structurally peripheral nodes, creating attention traps which
camouflage illicit capital reflux.

## Related Concepts

- [[Gradient Explosion]] — public domain concept, topologically isomorphic source

```adl:relation
source: "Capital Attention Trap"
relation: isomorphic-to
target: "adl://public/concepts/gradient_explosion"
mapping_type: topological
confidence: 0.91
```

## Evidence

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://clusters/8912
description: "High-dimensional clustering reveals 3-sigma outliers"
confidence: 0.87
```

```adl:seal
assertion: "isomorphic_mapping_preserves_cycles"
language: lean4
status: pending
```
"""


# ---------------------------------------------------------------------------
# Parser Tests
# ---------------------------------------------------------------------------

class TestParser:
    def test_split_front_matter(self):
        parser = ADLParser()
        fm, body = parser._split_front_matter(SAMPLE_DOC)
        assert "adl_type: discovery" in fm
        assert "# Capital Attention Trap" in body

    def test_parse_front_matter(self):
        parser = ADLParser()
        fm_raw, _ = parser._split_front_matter(SAMPLE_DOC)
        fm = parser._parse_front_matter(fm_raw)

        assert isinstance(fm, ADLFrontMatter)
        assert fm.adl_type == ADLType.DISCOVERY
        assert fm.adl_id == "disc-capital-trap"
        assert fm.status == DiscoveryStatus.PROVISIONAL
        assert fm.confidence == pytest.approx(0.84)
        assert fm.novelty == pytest.approx(0.91)
        assert fm.domain == "financial_aml"
        assert fm.mechanism == MechanismType.ISOMORPHIC_MAPPING
        assert fm.scope == "private/ceiec-aml"
        assert fm.provisional_names.zh == "资金注意力陷阱"
        assert fm.provisional_names.en == "Capital Attention Trap"
        assert len(fm.evidence_refs) == 2

    def test_extract_adl_blocks(self):
        parser = ADLParser()
        _, body = parser._split_front_matter(SAMPLE_DOC)
        l3_blocks, action_blocks, clean_body = parser._extract_adl_blocks(body)

        assert len(l3_blocks) == 3
        assert len(action_blocks) == 0  # SAMPLE_DOC has no action blocks
        assert isinstance(l3_blocks[0], ADLRelationBlock)
        assert isinstance(l3_blocks[1], ADLEvidenceBlock)
        assert isinstance(l3_blocks[2], ADLFormalSealBlock)

        # Clean body should not contain adl blocks
        assert "```adl:" not in clean_body
        assert "# Capital Attention Trap" in clean_body

    def test_parse_full_document(self):
        doc = parse_text(SAMPLE_DOC)

        assert isinstance(doc, ADLDocument)
        assert doc.adl_id == "disc-capital-trap"
        assert doc.status == DiscoveryStatus.PROVISIONAL
        assert doc.scope == "private/ceiec-aml"
        assert doc.concept_name == "Capital Attention Trap"

        assert len(doc.relations) == 1
        assert len(doc.evidence) == 1
        assert len(doc.seals) == 1

        rel = doc.relations[0]
        assert rel.source == "Capital Attention Trap"
        assert rel.relation == "isomorphic-to"
        assert "gradient_explosion" in rel.target

        ev = doc.evidence[0]
        assert ev.evidence_type == EvidenceType.VECTOR_CLUSTER
        assert ev.confidence == pytest.approx(0.87)

        seal = doc.seals[0]
        assert seal.assertion == "isomorphic_mapping_preserves_cycles"
        assert seal.status == "pending"

    def test_to_skeleton(self):
        doc = parse_text(SAMPLE_DOC)
        sk = doc.to_skeleton()

        assert isinstance(sk, ConceptSkeleton)
        assert sk.adl_id == "disc-capital-trap"
        assert sk.semantic_type == ADLType.DISCOVERY
        assert sk.domain_tag == "financial_aml"
        assert sk.status == DiscoveryStatus.PROVISIONAL
        assert sk.evidence_count == 1
        assert len(sk.relation_summary) == 1

    def test_wiki_link_extraction(self):
        doc = parse_text(SAMPLE_DOC)
        assert doc.wiki_links == ["Gradient Explosion"]


# ---------------------------------------------------------------------------
# Semantic Validation Tests
# ---------------------------------------------------------------------------

class TestValidation:
    def test_pronoun_detection(self):
        """Pronouns should trigger validation errors."""
        bad_doc = """\
---
adl_type: concept
adl_id: bad-concept
status: provisional
confidence: 0.5
novelty: 0.5
domain: test
scope: public
provisional_names:
  en: "Test"
---

This is a bad concept because it uses pronouns.
"""
        doc = parse_text(bad_doc)
        errors = doc.validate_semantics()

        pronoun_errors = [e for e in errors if "pronoun" in e.lower()]
        assert len(pronoun_errors) >= 1
        assert any("this" in e.lower() for e in pronoun_errors)

    def test_relative_that_allowed(self):
        """Relative 'that' clauses should not trigger pronoun errors."""
        ok_doc = """\
---
adl_type: concept
adl_id: ok-relative
status: provisional
confidence: 0.5
novelty: 0.5
domain: test
scope: public
provisional_names:
  en: "Ok Relative"
---

Peripheral nodes that feed into sink accounts form a convergence pattern that delivers funds.
"""
        doc = parse_text(ok_doc)
        errors = doc.validate_semantics()
        pronoun_errors = [e for e in errors if "pronoun" in e.lower()]
        assert pronoun_errors == []

    def test_scope_validation(self):
        """Invalid scope format should be rejected at parse time."""
        bad_doc = """\
---
adl_type: concept
adl_id: bad-scope
status: provisional
confidence: 0.5
novelty: 0.5
domain: test
scope: invalid_scope_format
provisional_names:
  en: "Test"
---

Test document.
"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            parse_text(bad_doc)


# ---------------------------------------------------------------------------
# Consensus Engine Tests
# ---------------------------------------------------------------------------

class TestConsensus:
    def test_register_and_transition(self):
        engine = ConsensusEngine()
        doc = parse_text(SAMPLE_DOC)

        chain = engine.register(doc)
        assert chain.latest_status == DiscoveryStatus.PROVISIONAL

        entry = engine.transition(
            doc.adl_id,
            DiscoveryStatus.VALIDATED,
            actor="agent_reviewer_1",
            reason="Cross-agent agreement reached",
        )
        assert entry is not None
        assert entry.to_status == DiscoveryStatus.VALIDATED
        assert engine.get_status(doc.adl_id) == DiscoveryStatus.VALIDATED

    def test_invalid_transition(self):
        engine = ConsensusEngine()
        doc = parse_text(SAMPLE_DOC)
        engine.register(doc)

        with pytest.raises(ValueError):
            engine.transition(
                doc.adl_id,
                DiscoveryStatus.VALIDATED,  # provisional → validated is OK
                actor="test",
            )
            # Now try validated → provisional (invalid)
            engine.transition(
                doc.adl_id,
                DiscoveryStatus.PROVISIONAL,
                actor="test",
            )

    def test_chain_integrity(self):
        engine = ConsensusEngine()
        doc = parse_text(SAMPLE_DOC)
        engine.register(doc)
        engine.transition(doc.adl_id, DiscoveryStatus.VALIDATED, "a1")
        engine.transition(doc.adl_id, DiscoveryStatus.DEPRECATED, "a2", "Superseded")

        results = engine.verify_all()
        assert results[doc.adl_id] is True

    def test_fork(self):
        engine = ConsensusEngine()
        doc = parse_text(SAMPLE_DOC)
        engine.register(doc)

        fork_chain = engine.fork(
            doc.adl_id,
            "disc-capital-trap-v2",
            actor="agent_forker",
            reason="Alternative mechanism hypothesis",
        )
        assert fork_chain.latest_status == DiscoveryStatus.PROVISIONAL
        assert engine.get_status(doc.adl_id) == DiscoveryStatus.FORKED


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_end_to_end(self):
        """Full pipeline: parse → validate → skeleton → consensus."""
        doc = parse_text(SAMPLE_DOC)

        # Validation
        errors = doc.validate_semantics()
        assert len(errors) == 0, f"Unexpected errors: {errors}"

        # Skeleton
        sk = doc.to_skeleton()
        assert sk.adl_id == doc.adl_id

        # Consensus
        engine = ConsensusEngine()
        engine.register(doc)
        engine.transition(doc.adl_id, DiscoveryStatus.VALIDATED, "integration_test")
        history = engine.get_history(doc.adl_id)
        assert len(history) == 2  # register + transition

    def test_scope_access_control(self):
        """Private scope documents should not be accessible from other scopes."""
        from adl_lite.validator import ADLValidator

        validator = ADLValidator()
        # private/ceiec-aml document accessed from public
        assert validator.validate_scope_access("private/ceiec-aml", "public") is False
        # Same scope
        assert validator.validate_scope_access("private/ceiec-aml", "private/ceiec-aml") is True
        # Public accessible to anyone
        assert validator.validate_scope_access("public", "private/other") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
