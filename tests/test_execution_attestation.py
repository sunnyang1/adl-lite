"""Tests for the Execution Attestation Layer (EAL, Phase 1).

Covers:
- New EventType members (EXECUTE / ATTEST / EXEC_ANCHOR)
- EAL conditional axioms 13–15 in EventChain.verify_integrity
- ExecutionLog: record / sign / verify / Merkle anchor / JSONL round-trip / tamper detection
- adl:execution L3 block parsing (YAML body, nested spec)
- Ontology registry sync (classes / predicates / actions / attestation policy)
- Consensus register hook: execution-spec requirement (production only, existing exempt)
- Derivation untouched: EAL events do not affect status LUB / confidence G-Counter
"""

from __future__ import annotations

import json

import pytest

from adl_lite import (
    ADLDocument,
    ADLExecutionBlock,
    ADLFrontMatter,
    ADLType,
    ConsensusEngine,
    DiscoveryStatus,
    Event,
    EventChain,
    EventType,
    ExecutionLog,
    OntologyManager,
    parse_text,
)
from adl_lite.exceptions import ADLConsensusError, ADLParseError
from adl_lite.ld_proof import generate_keypair, verify_event_proof
from adl_lite.models import ProvisionalNames
from adl_lite.parser import ADLParser

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_PROOF = {
    "type": "Ed25519Signature2020",
    "proofPurpose": "assertionMethod",
    "verificationMethod": "a2V5",  # base64 placeholder (presence-level tests only)
    "proofValue": "c2ln",  # base64 placeholder
}

# Sentinel distinguishing "argument omitted" from an explicit None.
_UNSET = object()


def make_execute_event(
    concept_id: str = "execlog-cap-1", proof=_UNSET, **payload_overrides
) -> Event:
    payload = {
        "execution_id": "exec-1",
        "capability": concept_id.removeprefix("execlog-"),
        "occurred_at": "2026-07-23T12:00:00+00:00",
        "input_commitment": "sha256:aa11",
        "output_commitment": "sha256:bb22",
        "env": {"runtime": "python3.12"},
        "duration_ms": 42,
        "assurance": "self-report",
        "artifacts_ref": None,
    }
    payload.update(payload_overrides)
    event = Event(
        concept_id=concept_id,
        event_type=EventType.EXECUTE,
        actor="agent-1",
        payload=payload,
    )
    event.proof = FAKE_PROOF if proof is _UNSET else proof
    return event


def make_attest_event(concept_id: str = "cap-1", proof=_UNSET, **payload_overrides) -> Event:
    payload = {
        "subject_execution": "exec-1",
        "subject_log_root": "sha256:cc33",
        "method": "replay",
        "verdict": "confirm",
        "replay": {
            "input_commitment": "sha256:aa11",
            "output_commitment": "sha256:bb22",
            "match": True,
            "tolerance": "exact",
        },
        "evidence_ref": None,
    }
    payload.update(payload_overrides)
    event = Event(
        concept_id=concept_id,
        event_type=EventType.ATTEST,
        actor="agent-2",
        payload=payload,
    )
    event.proof = FAKE_PROOF if proof is _UNSET else proof
    return event


def make_anchor_event(concept_id: str = "cap-1", **payload_overrides) -> Event:
    payload = {
        "log_id": f"execlog-{concept_id}",
        "log_merkle_root": "ab" * 32,
        "execution_count": 2,
        "executor_set": ["agent-1"],
        "window": {"from": "2026-07-01", "to": "2026-07-31"},
    }
    payload.update(payload_overrides)
    return Event(
        concept_id=concept_id,
        event_type=EventType.EXEC_ANCHOR,
        actor="registry",
        payload=payload,
    )


# ---------------------------------------------------------------------------
# EventType members
# ---------------------------------------------------------------------------


class TestEventTypeMembers:
    def test_new_members_exist(self):
        assert EventType.EXECUTE.value == "execute"
        assert EventType.ATTEST.value == "attest"
        assert EventType.EXEC_ANCHOR.value == "exec_anchor"

    def test_parse_from_string(self):
        assert EventType("execute") is EventType.EXECUTE
        assert EventType("attest") is EventType.ATTEST
        assert EventType("exec_anchor") is EventType.EXEC_ANCHOR


# ---------------------------------------------------------------------------
# Axiom 13 — evidence schema
# ---------------------------------------------------------------------------


class TestAxiom13EvidenceSchema:
    def test_execute_valid(self):
        chain = EventChain("execlog-cap-1")
        chain.append(make_execute_event())
        assert chain.verify_integrity()

    def test_execute_missing_output_commitment(self):
        chain = EventChain("execlog-cap-1")
        chain.append(make_execute_event(output_commitment=""))
        assert not chain.verify_integrity()

    def test_execute_missing_execution_id(self):
        chain = EventChain("execlog-cap-1")
        event = make_execute_event()
        del event.payload["execution_id"]
        event.hash = ""
        event.model_post_init(None)
        chain.append(event)
        assert not chain.verify_integrity()

    def test_attest_missing_verdict(self):
        chain = EventChain("cap-1")
        chain.append(make_anchor_event())
        event = make_attest_event()
        del event.payload["verdict"]
        event.hash = ""
        event.model_post_init(None)
        chain.append(event)
        assert not chain.verify_integrity()

    def test_anchor_missing_merkle_root(self):
        chain = EventChain("cap-1")
        chain.append(make_anchor_event(log_merkle_root=""))
        assert not chain.verify_integrity()

    def test_report_names_failing_axiom(self):
        chain = EventChain("execlog-cap-1")
        chain.append(make_execute_event(output_commitment=""))
        report = chain.well_formedness_report()
        assert report["axiom_13_evidence_schema"]


# ---------------------------------------------------------------------------
# Axiom 14 — proof presence
# ---------------------------------------------------------------------------


class TestAxiom14ProofPresence:
    def test_execute_without_proof_fails(self):
        chain = EventChain("execlog-cap-1")
        chain.append(make_execute_event(proof=None))
        assert not chain.verify_integrity()

    def test_execute_with_proof_passes(self):
        chain = EventChain("execlog-cap-1")
        chain.append(make_execute_event())
        assert chain.verify_integrity()

    def test_attest_without_proof_fails(self):
        chain = EventChain("cap-1")
        chain.append(make_attest_event(proof=None))
        assert not chain.verify_integrity()

    def test_proof_missing_proofvalue_fails(self):
        chain = EventChain("execlog-cap-1")
        chain.append(make_execute_event(proof={"type": "Ed25519Signature2020"}))
        assert not chain.verify_integrity()

    def test_anchor_does_not_require_proof(self):
        chain = EventChain("cap-1")
        chain.append(make_anchor_event())
        assert chain.verify_integrity()

    def test_report_names_failing_axiom(self):
        chain = EventChain("execlog-cap-1")
        chain.append(make_execute_event(proof=None))
        report = chain.well_formedness_report()
        assert report["axiom_14_proof_presence"]


# ---------------------------------------------------------------------------
# Axiom 15 — verdict consistency
# ---------------------------------------------------------------------------


class TestAxiom15VerdictConsistency:
    def test_replay_confirm_with_match_passes(self):
        chain = EventChain("cap-1")
        chain.append(make_attest_event())
        assert chain.verify_integrity()

    def test_replay_confirm_without_match_fails(self):
        chain = EventChain("cap-1")
        chain.append(
            make_attest_event(
                replay={
                    "input_commitment": "sha256:aa11",
                    "output_commitment": "sha256:bb22",
                    "match": False,
                }
            )
        )
        assert not chain.verify_integrity()

    def test_replay_confirm_missing_replay_block_fails(self):
        chain = EventChain("cap-1")
        event = make_attest_event()
        del event.payload["replay"]
        event.hash = ""
        event.model_post_init(None)
        chain.append(event)
        assert not chain.verify_integrity()

    def test_refute_with_evidence_ref_passes(self):
        chain = EventChain("cap-1")
        chain.append(make_attest_event(verdict="refute", evidence_ref="file:///logs/replay-7.json"))
        assert chain.verify_integrity()

    def test_refute_with_replay_mismatch_passes(self):
        chain = EventChain("cap-1")
        chain.append(
            make_attest_event(
                verdict="refute",
                evidence_ref=None,
                replay={
                    "input_commitment": "sha256:aa11",
                    "output_commitment": "sha256:ff99",
                    "match": False,
                },
            )
        )
        assert chain.verify_integrity()

    def test_refute_without_evidence_fails(self):
        chain = EventChain("cap-1")
        chain.append(make_attest_event(verdict="refute", evidence_ref=None, replay=None))
        assert not chain.verify_integrity()

    def test_inconclusive_passes(self):
        chain = EventChain("cap-1")
        chain.append(make_attest_event(verdict="inconclusive", method="property-check"))
        assert chain.verify_integrity()

    def test_unknown_verdict_fails(self):
        chain = EventChain("cap-1")
        chain.append(make_attest_event(verdict="maybe"))
        assert not chain.verify_integrity()

    def test_report_names_failing_axiom(self):
        chain = EventChain("cap-1")
        chain.append(make_attest_event(verdict="refute", evidence_ref=None, replay=None))
        report = chain.well_formedness_report()
        assert report["axiom_15_verdict_consistency"]


# ---------------------------------------------------------------------------
# Derivation untouched: EAL events do not feed status/confidence
# ---------------------------------------------------------------------------


class TestDerivationUntouched:
    def test_status_ignores_eal_events(self):
        chain = EventChain("cap-1")
        chain.append(
            Event(concept_id="cap-1", event_type=EventType.REGISTER, actor="a", payload={})
        )
        assert chain.status == DiscoveryStatus.PROVISIONAL
        chain.append(make_anchor_event())
        chain.append(make_attest_event())
        assert chain.status == DiscoveryStatus.PROVISIONAL
        assert chain.confidence == 0.0

    def test_confidence_ignores_eal_payload_confidence(self):
        chain = EventChain("cap-1")
        anchor = make_anchor_event()
        anchor.payload["confidence"] = 0.99  # must NOT feed the G-Counter
        anchor.hash = ""
        anchor.model_post_init(None)
        chain.append(anchor)
        assert chain.confidence == 0.0


# ---------------------------------------------------------------------------
# ExecutionLog
# ---------------------------------------------------------------------------


class TestExecutionLog:
    def test_record_and_verify(self):
        key = generate_keypair()
        log = ExecutionLog("disc-demo")
        log.record(
            executor="agent-1",
            input_commitment="sha256:in1",
            output_commitment="sha256:out1",
            private_key=key,
        )
        log.record(
            executor="agent-1",
            input_commitment="sha256:in2",
            output_commitment="sha256:out2",
            private_key=key,
        )
        assert log.count == 2
        assert log.verify_integrity()

    def test_record_requires_payload_fields(self):
        log = ExecutionLog("disc-demo")
        event = log.record(
            executor="agent-1",
            input_commitment="sha256:in1",
            output_commitment="sha256:out1",
        )
        assert event.payload["execution_id"].startswith("exec-")
        assert event.payload["assurance"] == "self-report"
        # Unsigned receipt fails axiom 14
        assert not log.verify_integrity()

    def test_signed_receipt_proof_verifies(self):
        key = generate_keypair()
        log = ExecutionLog("disc-demo")
        event = log.record(
            executor="agent-1",
            input_commitment="sha256:in1",
            output_commitment="sha256:out1",
            private_key=key,
        )
        # Cryptographic verification (base64 verificationMethod fallback).
        assert verify_event_proof(event)

    def test_proof_covers_final_chained_hash(self):
        key = generate_keypair()
        log = ExecutionLog("disc-demo")
        log.record(
            executor="a",
            input_commitment="sha256:i1",
            output_commitment="sha256:o1",
            private_key=key,
        )
        second = log.record(
            executor="a",
            input_commitment="sha256:i2",
            output_commitment="sha256:o2",
            private_key=key,
        )
        assert second.previous_event_id == log.receipts[0].event_id
        assert verify_event_proof(second)

    def test_tamper_detection(self):
        key = generate_keypair()
        log = ExecutionLog("disc-demo")
        event = log.record(
            executor="agent-1",
            input_commitment="sha256:in1",
            output_commitment="sha256:out1",
            private_key=key,
        )
        event.payload["output_commitment"] = "sha256:FORGED"
        assert not log.verify_integrity()

    def test_merkle_root_stable_and_changes_on_append(self):
        key = generate_keypair()
        log = ExecutionLog("disc-demo")
        log.record(executor="a", input_commitment="i1", output_commitment="o1", private_key=key)
        root1 = log.merkle_root()
        assert len(root1) == 64
        assert log.merkle_root() == root1
        log.record(executor="a", input_commitment="i2", output_commitment="o2", private_key=key)
        assert log.merkle_root() != root1

    def test_executors_distinct(self):
        key = generate_keypair()
        log = ExecutionLog("disc-demo")
        for actor in ("a", "b", "a"):
            log.record(
                executor=actor,
                input_commitment="i",
                output_commitment="o",
                private_key=key,
            )
        assert log.executors == ["a", "b"]

    def test_get_receipt(self):
        key = generate_keypair()
        log = ExecutionLog("disc-demo")
        event = log.record(
            executor="a", input_commitment="i", output_commitment="o", private_key=key
        )
        found = log.get_receipt(event.payload["execution_id"])
        assert found is event
        assert log.get_receipt("exec-nonexistent") is None

    def test_anchor_event_fields(self):
        key = generate_keypair()
        log = ExecutionLog("disc-demo")
        log.record(executor="a", input_commitment="i", output_commitment="o", private_key=key)
        anchor = log.build_anchor_event(actor="registry")
        assert anchor.event_type is EventType.EXEC_ANCHOR
        assert anchor.concept_id == "disc-demo"  # governance chain id, not log id
        assert anchor.payload["log_merkle_root"] == log.merkle_root()
        assert anchor.payload["execution_count"] == 1
        assert anchor.payload["executor_set"] == ["a"]
        # Anchor must be appendable to the governance chain and pass axioms.
        chain = EventChain("disc-demo")
        chain.append(anchor)
        assert chain.verify_integrity()

    def test_jsonl_round_trip(self, tmp_path):
        key = generate_keypair()
        log = ExecutionLog("disc-demo")
        log.record(executor="a", input_commitment="i1", output_commitment="o1", private_key=key)
        log.record(executor="b", input_commitment="i2", output_commitment="o2", private_key=key)
        path = log.to_jsonl(tmp_path / "log.jsonl")

        loaded = ExecutionLog.from_jsonl(path)
        assert loaded.capability_id == "disc-demo"
        assert loaded.count == 2
        assert loaded.merkle_root() == log.merkle_root()
        assert loaded.verify_integrity()
        # Proofs survive the round trip (unlike cold-storage archives).
        assert all(e.proof for e in loaded.receipts)
        assert verify_event_proof(loaded.receipts[0])

    def test_jsonl_rejects_non_execute_events(self, tmp_path):
        log = ExecutionLog("disc-demo")
        path = log.to_jsonl(tmp_path / "log.jsonl")
        # Inject a foreign event type into the file.
        foreign = Event(
            concept_id="execlog-disc-demo",
            event_type=EventType.REGISTER,
            actor="x",
            payload={},
        )
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ExecutionLog._event_to_dict(foreign)) + "\n")
        loaded = ExecutionLog.from_jsonl(path, capability_id="disc-demo")
        assert not loaded.verify_integrity()


# ---------------------------------------------------------------------------
# adl:execution L3 block parsing
# ---------------------------------------------------------------------------

_EXEC_DOC = """---
adl_type: concept
adl_id: cap-exec-1
status: provisional
confidence: 0.0
scope: public
provisional_names:
  en: "Replayable Capability"
---

## Overview

A capability with an execution spec.

```adl:execution
invocation:
  type: cli
  command: "python -m mycap.score --input {input_file}"
  timeout_ms: 5000
determinism: deterministic
properties:
  - "output.confidence in [0, 1]"
  - "p95_latency_ms < 200"
test_vectors:
  - input_commitment: "sha256:aa11"
    expected_output_commitment: "sha256:bb22"
```
"""


class TestExecutionBlockParsing:
    def test_parse_execution_block(self):
        doc = parse_text(_EXEC_DOC)
        spec = doc.execution_spec
        assert spec is not None
        assert spec.invocation.type == "cli"
        assert "mycap.score" in spec.invocation.command
        assert spec.invocation.timeout_ms == 5000
        assert spec.determinism == "deterministic"
        assert spec.properties == ["output.confidence in [0, 1]", "p95_latency_ms < 200"]
        assert len(spec.test_vectors) == 1
        assert spec.test_vectors[0].input_commitment == "sha256:aa11"

    def test_block_removed_from_markdown_body(self):
        doc = parse_text(_EXEC_DOC)
        assert "adl:execution" not in doc.markdown_body
        assert "invocation" not in doc.markdown_body

    def test_doc_without_spec_returns_none(self):
        doc = parse_text(
            _EXEC_DOC.replace("```adl:execution", "```adl:evidence").replace(
                "invocation:", "evidence_type: empirical_observation\ndata_ref: file:///x\n#"
            )
        )
        # Above mutation is only to create a doc lacking an execution block.
        assert doc.execution_spec is None

    def test_invalid_yaml_raises(self):
        bad = _EXEC_DOC.replace("determinism: deterministic", "determinism: [unclosed")
        with pytest.raises(ADLParseError):
            parse_text(bad)

    def test_invalid_determinism_raises(self):
        bad = _EXEC_DOC.replace("determinism: deterministic", "determinism: chaotic")
        with pytest.raises(ADLParseError):
            parse_text(bad)

    def test_non_mapping_body_raises(self):
        text = _EXEC_DOC.replace(
            'invocation:\n  type: cli\n  command: "python -m mycap.score --input {input_file}"\n  timeout_ms: 5000\ndeterminism: deterministic',
            "- just\n- a\n- list",
        )
        with pytest.raises(ADLParseError):
            parse_text(text)

    def test_parser_exports_block_type(self):
        doc = ADLParser().parse_text(_EXEC_DOC)
        blocks = [b for b in doc.adl_blocks if isinstance(b, ADLExecutionBlock)]
        assert len(blocks) == 1


# ---------------------------------------------------------------------------
# Ontology registry sync
# ---------------------------------------------------------------------------


class TestOntologySync:
    def test_new_classes(self):
        mgr = OntologyManager()
        assert "execution" in mgr.list_classes()
        assert "attestation" in mgr.list_classes()

    def test_new_predicates(self):
        mgr = OntologyManager()
        for pred in ("attests", "executed-by", "anchored-by"):
            assert mgr.validate_predicate(pred), pred

    def test_new_actions(self):
        mgr = OntologyManager()
        actions = mgr.list_actions()
        for action in ("execute", "attest", "exec_anchor"):
            assert action in actions, action

    def test_execute_action_def(self):
        mgr = OntologyManager()
        action_def = mgr.get_action_def("execute")
        assert action_def is not None
        assert set(action_def["required_params"]) == {"input_commitment", "output_commitment"}
        assert action_def["triggers_transition"] is None

    def test_policy_accessors(self):
        mgr = OntologyManager()
        assert mgr.min_distinct_scopes() == 2
        assert mgr.evidence_factor_unbacked() == 0.5
        assert mgr.refute_threshold() == 2
        assert mgr.require_execution_spec_on_register() is True

    def test_policy_defaults_when_section_missing(self, tmp_path):
        import yaml

        mgr = OntologyManager()
        data = dict(mgr._data)
        data.pop("attestation", None)
        path = tmp_path / "onto.yaml"
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
        bare = OntologyManager(path)
        assert bare.min_distinct_scopes() == 2
        assert bare.evidence_factor_unbacked() == 0.5
        assert bare.refute_threshold() == 2
        assert bare.require_execution_spec_on_register() is False


# ---------------------------------------------------------------------------
# Consensus register hook (D5)
# ---------------------------------------------------------------------------


def _doc_without_spec(adl_id: str = "cap-nospec") -> ADLDocument:
    return ADLDocument(
        front_matter=ADLFrontMatter(
            adl_type=ADLType.CONCEPT,
            adl_id=adl_id,
            scope="public",
            provisional_names=ProvisionalNames(en=adl_id),
        )
    )


class TestRegisterExecutionSpecHook:
    def test_dev_mode_allows_missing_spec(self):
        engine = ConsensusEngine(dev_mode=True)
        chain = engine.register(_doc_without_spec())
        assert chain.status == DiscoveryStatus.PROVISIONAL

    def test_production_rejects_missing_spec(self):
        engine = ConsensusEngine(dev_mode=False)
        with pytest.raises(ADLConsensusError, match="adl:execution"):
            engine.register(_doc_without_spec())

    def test_production_accepts_doc_with_spec(self):
        engine = ConsensusEngine(dev_mode=False)
        doc = parse_text(_EXEC_DOC)
        chain = engine.register(doc)
        assert chain.concept_id == "cap-exec-1"

    def test_existing_capability_exempt(self):
        engine = ConsensusEngine(dev_mode=False)
        engine.register(parse_text(_EXEC_DOC))  # first registration (has spec)
        # Re-registering an existing id without a spec is a no-op, not an error.
        chain = engine.register(_doc_without_spec(adl_id="cap-exec-1"))
        assert chain.concept_id == "cap-exec-1"

    def test_production_respects_policy_disabled(self, tmp_path):
        import yaml

        mgr = OntologyManager()
        data = dict(mgr._data)
        data["attestation"] = {"require_execution_spec_on_register": False}
        path = tmp_path / "onto.yaml"
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
        engine = ConsensusEngine(ontology=OntologyManager(path), dev_mode=False)
        chain = engine.register(_doc_without_spec())
        assert chain.concept_id == "cap-nospec"
