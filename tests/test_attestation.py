"""Tests for EAL Phase 2: attestation validation, replay harness, calibration wiring.

Covers:
- AttestationValidator: subject resolution via injected lookup, cross-log
  commitment equality, self-attestation, pending vs hard issues
- AttestationIndex: distinct-scope counting (payload scope, actor fallback,
  self-attestation exclusion)
- attested_confidence: evidence-weighted factor, monotonicity (refutes never lower)
- refute_status: distinct-scope threshold → DEPRECATE proposal flag
- feed_calibrator: overturned/supported verdict feedback, method strength
- ReplayHarness: real subprocess replay (confirm/refute/inconclusive paths,
  determinism gate, timeout, non-zero exit)
- build_attest_event/append_attestation: append-then-sign ordering, axiom compliance
- CLI: adl-lite attest replay/list end-to-end
"""

from __future__ import annotations

import sys

import pytest

from adl_lite import (
    ADLExecutionBlock,
    ADLExecutionInvocation,
    ADLExecutionTestVector,
    AttestationIndex,
    AttestationValidator,
    Event,
    EventChain,
    EventType,
    ExecutionLog,
    MARGINCalibrator,
    ReplayHarness,
    append_attestation,
    attested_confidence,
    build_attest_event,
    capability_backed,
    feed_calibrator,
    refute_status,
    sha256_commitment,
)
from adl_lite.cli import main
from adl_lite.ld_proof import generate_keypair, verify_event_proof

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

PROOF = {
    "type": "Ed25519Signature2020",
    "proofPurpose": "assertionMethod",
    "verificationMethod": "a2V5",
    "proofValue": "c2ln",
}


def make_log_and_receipt(cap_id: str = "cap-a") -> tuple[ExecutionLog, Event]:
    key = generate_keypair()
    log = ExecutionLog(cap_id)
    receipt = log.record(
        executor="executor-1",
        input_commitment="sha256:in",
        output_commitment="sha256:out",
        private_key=key,
    )
    return log, receipt


def make_attest(
    cap_id: str,
    subject_id: str,
    *,
    actor: str = "attester-1",
    verdict: str = "confirm",
    method: str = "replay",
    scope: str | None = "scope/org-b",
    ts: str = "2026-07-23T12:00:00+00:00",
    replay_match: bool = True,
) -> Event:
    payload = {
        "subject_execution": subject_id,
        "method": method,
        "verdict": verdict,
        "replay": {
            "input_commitment": "sha256:in",
            "output_commitment": "sha256:out" if replay_match else "sha256:DIFFERENT",
            "match": replay_match,
            "tolerance": "exact",
        },
        "evidence_ref": "file:///ev" if verdict == "refute" else None,
    }
    if scope:
        payload["scope"] = scope
    return Event(
        concept_id=cap_id,
        event_type=EventType.ATTEST,
        actor=actor,
        timestamp=ts,
        payload=payload,
    )


# ---------------------------------------------------------------------------
# AttestationValidator
# ---------------------------------------------------------------------------


class TestAttestationValidator:
    def test_valid_confirm_no_issues(self):
        log, receipt = make_log_and_receipt()
        v = AttestationValidator(execution_lookup=log)
        attest = make_attest("cap-a", receipt.payload["execution_id"])
        assert v.validate(attest) == []

    def test_pending_when_subject_unresolvable(self):
        v = AttestationValidator(execution_lookup={})
        attest = make_attest("cap-a", "exec-missing")
        issues = v.validate(attest)
        assert len(issues) == 1
        assert issues[0].startswith("pending:")

    def test_none_lookup_is_pending(self):
        v = AttestationValidator()
        attest = make_attest("cap-a", "exec-x")
        assert v.validate(attest)[0].startswith("pending:")

    def test_self_attestation_flagged(self):
        log, receipt = make_log_and_receipt()
        v = AttestationValidator(execution_lookup=log)
        attest = make_attest("cap-a", receipt.payload["execution_id"], actor="executor-1")
        assert any("self-attestation" in i for i in v.validate(attest))

    def test_confirm_with_mismatched_replay_commitments(self):
        log, receipt = make_log_and_receipt()
        v = AttestationValidator(execution_lookup=log)
        attest = make_attest("cap-a", receipt.payload["execution_id"])
        attest.payload["replay"]["output_commitment"] = "sha256:DIFFERENT"
        attest.payload["replay"]["match"] = True  # internally consistent, cross-log wrong
        issues = v.validate(attest)
        assert any("output_commitment differs" in i for i in issues)

    def test_dict_lookup(self):
        log, receipt = make_log_and_receipt()
        eid = receipt.payload["execution_id"]
        v = AttestationValidator(execution_lookup={eid: receipt})
        assert v.validate(make_attest("cap-a", eid)) == []

    def test_scope_of_payload_and_fallback(self):
        v = AttestationValidator()
        with_scope = make_attest("cap-a", "x", scope="scope/org-b")
        assert v.scope_of(with_scope) == "scope/org-b"
        without = make_attest("cap-a", "x", scope=None, actor="attester-9")
        assert v.scope_of(without) == "attester-9"

    def test_invalid_lookup_type_raises(self):
        with pytest.raises(TypeError):
            AttestationValidator(execution_lookup=42)


# ---------------------------------------------------------------------------
# AttestationIndex
# ---------------------------------------------------------------------------


class TestAttestationIndex:
    def test_distinct_scope_counting(self):
        log, receipt = make_log_and_receipt()
        eid = receipt.payload["execution_id"]
        events = [
            make_attest("cap-a", eid, actor="a1", scope="scope/org-b"),
            make_attest("cap-a", eid, actor="a2", scope="scope/org-c"),
            make_attest("cap-a", eid, actor="a3", scope="scope/org-b"),  # duplicate scope
        ]
        index = AttestationIndex(events, validator=AttestationValidator(log))
        assert index.distinct_scope_count(eid, "confirm") == 2

    def test_self_attestation_excluded(self):
        log, receipt = make_log_and_receipt()
        eid = receipt.payload["execution_id"]
        events = [
            make_attest("cap-a", eid, actor="executor-1", scope="scope/org-self"),
            make_attest("cap-a", eid, actor="a2", scope="scope/org-b"),
        ]
        index = AttestationIndex(events, validator=AttestationValidator(log))
        assert index.distinct_scope_count(eid, "confirm") == 1

    def test_actor_fallback_diversity(self):
        log, receipt = make_log_and_receipt()
        eid = receipt.payload["execution_id"]
        events = [
            make_attest("cap-a", eid, actor="a1", scope=None),
            make_attest("cap-a", eid, actor="a2", scope=None),
        ]
        index = AttestationIndex(events, validator=AttestationValidator(log))
        assert index.distinct_scope_count(eid, "confirm") == 2

    def test_summary(self):
        log, receipt = make_log_and_receipt()
        eid = receipt.payload["execution_id"]
        events = [make_attest("cap-a", eid, verdict="refute", scope="scope/org-b")]
        index = AttestationIndex(events, validator=AttestationValidator(log))
        summary = index.summary()
        assert summary[eid]["refute"] == 1
        assert summary[eid]["confirm"] == 0


# ---------------------------------------------------------------------------
# attested_confidence + capability_backed
# ---------------------------------------------------------------------------


def _validated_chain(cap_id: str = "cap-a", confidence: float = 0.9) -> EventChain:
    chain = EventChain(cap_id)
    chain.append(Event(concept_id=cap_id, event_type=EventType.REGISTER, actor="d", payload={}))
    chain.append(
        Event(
            concept_id=cap_id,
            event_type=EventType.VALIDATE,
            actor="v1",
            payload={"confidence": confidence},
        )
    )
    return chain


class TestAttestedConfidence:
    def test_unbacked_discounted(self):
        chain = _validated_chain()
        index = AttestationIndex([], validator=AttestationValidator())
        assert attested_confidence(chain, index) == pytest.approx(0.9 * 0.5)

    def test_backed_full_weight(self):
        log, receipt = make_log_and_receipt()
        eid = receipt.payload["execution_id"]
        chain = _validated_chain()
        events = [
            make_attest("cap-a", eid, actor="a1", scope="scope/org-b"),
            make_attest("cap-a", eid, actor="a2", scope="scope/org-c"),
        ]
        index = AttestationIndex(events, validator=AttestationValidator(log))
        assert capability_backed(chain, index)
        assert attested_confidence(chain, index) == pytest.approx(0.9)

    def test_single_scope_insufficient(self):
        log, receipt = make_log_and_receipt()
        eid = receipt.payload["execution_id"]
        events = [make_attest("cap-a", eid, actor="a1", scope="scope/org-b")]
        index = AttestationIndex(events, validator=AttestationValidator(log))
        chain = _validated_chain()
        assert not capability_backed(chain, index)

    def test_refutes_never_lower_confidence(self):
        log, receipt = make_log_and_receipt()
        eid = receipt.payload["execution_id"]
        chain = _validated_chain()
        backed_events = [
            make_attest("cap-a", eid, actor="a1", scope="scope/org-b"),
            make_attest("cap-a", eid, actor="a2", scope="scope/org-c"),
        ]
        index = AttestationIndex(backed_events, validator=AttestationValidator(log))
        before = attested_confidence(chain, index)
        refuted = backed_events + [
            make_attest("cap-a", eid, actor="r1", verdict="refute", scope="scope/org-d"),
            make_attest("cap-a", eid, actor="r2", verdict="refute", scope="scope/org-e"),
        ]
        index2 = AttestationIndex(refuted, validator=AttestationValidator(log))
        assert attested_confidence(chain, index2) == before  # monotone (D3)


# ---------------------------------------------------------------------------
# refute_status
# ---------------------------------------------------------------------------


class TestRefuteStatus:
    def test_below_threshold_no_proposal(self):
        log, receipt = make_log_and_receipt()
        eid = receipt.payload["execution_id"]
        chain = _validated_chain()
        events = [make_attest("cap-a", eid, verdict="refute", scope="scope/org-b")]
        index = AttestationIndex(events, validator=AttestationValidator(log))
        status = refute_status(chain, index)
        assert status["refute_scopes"] == 1
        assert status["threshold"] == 2
        assert status["proposal"] is False

    def test_threshold_crossed_proposal(self):
        log, receipt = make_log_and_receipt()
        eid = receipt.payload["execution_id"]
        chain = _validated_chain()
        events = [
            make_attest("cap-a", eid, verdict="refute", actor="r1", scope="scope/org-b"),
            make_attest("cap-a", eid, verdict="refute", actor="r2", scope="scope/org-c"),
            make_attest("cap-a", eid, verdict="refute", actor="r3", scope="scope/org-b"),
        ]
        index = AttestationIndex(events, validator=AttestationValidator(log))
        status = refute_status(chain, index)
        assert status["refute_scopes"] == 2
        assert status["proposal"] is True


# ---------------------------------------------------------------------------
# feed_calibrator
# ---------------------------------------------------------------------------


class TestFeedCalibrator:
    def test_overturned_attester_accuracy_drops(self, tmp_path):
        cal = MARGINCalibrator(tmp_path / "cal.yaml")
        events = [
            make_attest(
                "cap-a",
                "exec-1",
                actor="lazy-attester",
                method="manual",
                verdict="confirm",
                ts="2026-07-01T00:00:00+00:00",
            ),
            make_attest(
                "cap-a",
                "exec-1",
                actor="diligent",
                method="replay",
                verdict="refute",
                ts="2026-07-02T00:00:00+00:00",
            ),
        ]
        updates = feed_calibrator(events, cal)
        assert updates == 1
        # Overturned: predicted 1.0, truth 0.0 → observed 0 → EWMA pulls below default 0.5
        assert cal.get_accuracy("lazy-attester", context="attestation") < 0.5

    def test_supported_verdict_reinforced(self, tmp_path):
        cal = MARGINCalibrator(tmp_path / "cal.yaml")
        events = [
            make_attest(
                "cap-a",
                "exec-1",
                actor="a1",
                verdict="refute",
                ts="2026-07-01T00:00:00+00:00",
            ),
            make_attest(
                "cap-a",
                "exec-1",
                actor="a2",
                verdict="refute",
                ts="2026-07-02T00:00:00+00:00",
            ),
        ]
        updates = feed_calibrator(events, cal)
        assert updates == 1
        assert cal.get_accuracy("a1", context="attestation") > 0.5

    def test_stronger_method_required_to_overturn(self, tmp_path):
        cal = MARGINCalibrator(tmp_path / "cal.yaml")
        # a1 replay-confirm; a2 later manual-refute is WEAKER → no feedback for a1.
        events = [
            make_attest(
                "cap-a",
                "exec-1",
                actor="a1",
                method="replay",
                verdict="confirm",
                ts="2026-07-01T00:00:00+00:00",
            ),
            make_attest(
                "cap-a",
                "exec-1",
                actor="a2",
                method="manual",
                verdict="refute",
                ts="2026-07-02T00:00:00+00:00",
            ),
        ]
        assert feed_calibrator(events, cal) == 0

    def test_inconclusive_generates_no_feedback(self, tmp_path):
        cal = MARGINCalibrator(tmp_path / "cal.yaml")
        events = [
            make_attest("cap-a", "exec-1", actor="a1", verdict="inconclusive"),
            make_attest(
                "cap-a",
                "exec-1",
                actor="a2",
                verdict="refute",
                ts="2026-07-02T00:00:00+00:00",
            ),
        ]
        assert feed_calibrator(events, cal) == 0


# ---------------------------------------------------------------------------
# ReplayHarness (real subprocess)
# ---------------------------------------------------------------------------


def _spec(command: str, determinism: str = "deterministic", timeout_ms: int = 5000):
    return ADLExecutionBlock(
        invocation=ADLExecutionInvocation(type="cli", command=command, timeout_ms=timeout_ms),
        determinism=determinism,  # type: ignore[arg-type]
    )


class TestReplayHarness:
    def test_confirm_on_matching_output(self, tmp_path):
        content = b"hello replay"
        input_file = tmp_path / "input.txt"
        input_file.write_bytes(content)
        spec = _spec("cat {input_file}")
        outcome = ReplayHarness(spec).replay_against_commitments(
            input_commitment=sha256_commitment(content),
            expected_output_commitment=sha256_commitment(content),
            input_file=input_file,
        )
        assert outcome.verdict == "confirm"
        assert outcome.replay["match"] is True
        assert outcome.duration_ms >= 0

    def test_refute_on_mismatched_output(self, tmp_path):
        input_file = tmp_path / "input.txt"
        input_file.write_bytes(b"actual")
        spec = _spec("cat {input_file}")
        outcome = ReplayHarness(spec).replay_against_commitments(
            input_commitment=sha256_commitment(b"actual"),
            expected_output_commitment=sha256_commitment(b"different"),
            input_file=input_file,
        )
        assert outcome.verdict == "refute"
        assert outcome.replay["match"] is False

    def test_inconclusive_on_input_commitment_mismatch(self, tmp_path):
        input_file = tmp_path / "input.txt"
        input_file.write_bytes(b"actual")
        spec = _spec("cat {input_file}")
        outcome = ReplayHarness(spec).replay_against_commitments(
            input_commitment=sha256_commitment(b"other-input"),
            expected_output_commitment="sha256:anything",
            input_file=input_file,
        )
        assert outcome.verdict == "inconclusive"
        assert "input_commitment" in outcome.reason

    @pytest.mark.parametrize("determinism", ["stochastic", "side-effecting"])
    def test_determinism_gate(self, determinism, tmp_path):
        input_file = tmp_path / "input.txt"
        input_file.write_bytes(b"x")
        spec = _spec("cat {input_file}", determinism=determinism)
        outcome = ReplayHarness(spec).replay_against_commitments(
            input_commitment="sha256:x",
            expected_output_commitment="sha256:y",
            input_file=input_file,
        )
        assert outcome.verdict == "inconclusive"

    def test_timeout_inconclusive(self, tmp_path):
        input_file = tmp_path / "input.txt"
        content = b"x"
        input_file.write_bytes(content)
        spec = _spec(
            f'{sys.executable} -c "import time; time.sleep(3)"',
            timeout_ms=200,
        )
        outcome = ReplayHarness(spec).replay_against_commitments(
            input_commitment=sha256_commitment(content),
            expected_output_commitment="sha256:y",
            input_file=input_file,
        )
        assert outcome.verdict == "inconclusive"
        assert "timeout" in outcome.reason

    def test_nonzero_exit_inconclusive(self, tmp_path):
        input_file = tmp_path / "input.txt"
        content = b"x"
        input_file.write_bytes(content)
        spec = _spec(f'{sys.executable} -c "import sys; sys.exit(3)"')
        outcome = ReplayHarness(spec).replay_against_commitments(
            input_commitment=sha256_commitment(content),
            expected_output_commitment="sha256:y",
            input_file=input_file,
        )
        assert outcome.verdict == "inconclusive"
        assert "exited 3" in outcome.reason

    def test_replay_test_vector(self, tmp_path):
        content = b"vector-input"
        input_file = tmp_path / "v.txt"
        input_file.write_bytes(content)
        spec = _spec("cat {input_file}")
        vector = ADLExecutionTestVector(
            input_commitment=sha256_commitment(content),
            expected_output_commitment=sha256_commitment(content),
        )
        outcome = ReplayHarness(spec).replay_test_vector(vector, input_file)
        assert outcome.verdict == "confirm"


# ---------------------------------------------------------------------------
# build/append attestation
# ---------------------------------------------------------------------------


class TestAppendAttestation:
    def test_append_then_sign_verifies(self):
        _, receipt = make_log_and_receipt()
        key = generate_keypair()
        chain = _validated_chain()
        outcome = type(
            "O",
            (),
            {
                "verdict": "confirm",
                "reason": "match",
                "duration_ms": 5,
                "replay": {
                    "input_commitment": "sha256:in",
                    "output_commitment": "sha256:out",
                    "match": True,
                    "tolerance": "exact",
                },
            },
        )()
        event = build_attest_event(
            capability_id="cap-a",
            subject_receipt=receipt,
            outcome=outcome,  # type: ignore[arg-type]
            actor="attester-1",
            scope="scope/org-b",
        )
        append_attestation(chain, event, private_key=key)
        assert verify_event_proof(event)  # proof covers final chaining fields
        assert chain.verify_integrity()

    def test_unsigned_attestation_fails_axiom14(self):
        _, receipt = make_log_and_receipt()
        chain = _validated_chain()
        outcome = type(
            "O",
            (),
            {
                "verdict": "confirm",
                "reason": "m",
                "duration_ms": 1,
                "replay": {
                    "input_commitment": "sha256:in",
                    "output_commitment": "sha256:out",
                    "match": True,
                },
            },
        )()
        event = build_attest_event(
            capability_id="cap-a",
            subject_receipt=receipt,
            outcome=outcome,
            actor="a",  # type: ignore[arg-type]
        )
        append_attestation(chain, event)  # no key
        assert not chain.verify_integrity()


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------


def _write_doc(tmp_path, adl_id: str = "cap-cli"):
    content = b"cli-replay-input"
    input_file = tmp_path / "input.bin"
    input_file.write_bytes(content)
    doc = tmp_path / "cap.md"
    doc.write_text(
        f"""---
adl_type: concept
adl_id: {adl_id}
status: provisional
confidence: 0.0
scope: public
provisional_names:
  en: "CLI Replay Cap"
---

## Overview

Capability under CLI test.

```adl:execution
invocation:
  type: cli
  command: "cat {{input_file}}"
  timeout_ms: 5000
determinism: deterministic
```
""",
        encoding="utf-8",
    )
    return doc, input_file, content


def _write_key(tmp_path):
    from cryptography.hazmat.primitives import serialization

    key = generate_keypair()
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    path = tmp_path / "k.pem"
    path.write_bytes(pem)
    return path


class TestCliAttest:
    def test_full_replay_flow(self, tmp_path, capsys):
        doc, input_file, content = _write_doc(tmp_path)
        key_file = _write_key(tmp_path)
        state = tmp_path / "state.json"
        log_dir = tmp_path / "logs"
        adl_id = "cap-cli"

        with pytest.raises(SystemExit) as e:
            main(["consensus", "register", str(doc), "--state", str(state)])
        assert e.value.code == 0

        in_c = sha256_commitment(content)
        out_c = sha256_commitment(content)
        with pytest.raises(SystemExit) as e:
            main(
                [
                    "execute",
                    "record",
                    str(doc),
                    "--log-dir",
                    str(log_dir),
                    "--actor",
                    "executor-1",
                    "--key-file",
                    str(key_file),
                    "--input-hash",
                    in_c,
                    "--output-hash",
                    out_c,
                ]
            )
        assert e.value.code == 0

        from adl_lite.execution_log import load_log

        receipt = load_log(log_dir, adl_id).receipts[0]
        eid = receipt.payload["execution_id"]

        with pytest.raises(SystemExit) as e:
            main(
                [
                    "attest",
                    "replay",
                    str(doc),
                    "--execution-id",
                    eid,
                    "--input-file",
                    str(input_file),
                    "--actor",
                    "attester-1",
                    "--key-file",
                    str(key_file),
                    "--scope",
                    "scope/org-b",
                    "--state",
                    str(state),
                    "--log-dir",
                    str(log_dir),
                ]
            )
        assert e.value.code == 0
        assert "confirm" in capsys.readouterr().out

        with pytest.raises(SystemExit) as e:
            main(["attest", "list", adl_id, "--state", str(state), "--log-dir", str(log_dir)])
        assert e.value.code == 0
        out = capsys.readouterr().out
        assert "confirm" in out
        assert "0/2 distinct scopes" in out

        # Chain-level: the appended ATTEST satisfies axioms 13–15.
        from adl_lite.cli import _load_engine

        chain = _load_engine(state).chains[adl_id]
        assert chain.verify_integrity()

    def test_replay_missing_execution_id(self, tmp_path, capsys):
        doc, input_file, _ = _write_doc(tmp_path)
        key_file = _write_key(tmp_path)
        state = tmp_path / "state.json"
        with pytest.raises(SystemExit) as e:
            main(
                [
                    "attest",
                    "replay",
                    str(doc),
                    "--execution-id",
                    "exec-nope",
                    "--input-file",
                    str(input_file),
                    "--actor",
                    "a",
                    "--key-file",
                    str(key_file),
                    "--state",
                    str(state),
                    "--log-dir",
                    str(tmp_path / "logs"),
                ]
            )
        assert e.value.code == 1
        assert "not found" in capsys.readouterr().err

    def test_list_unregistered(self, tmp_path, capsys):
        with pytest.raises(SystemExit) as e:
            main(["attest", "list", "cap-ghost", "--state", str(tmp_path / "s.json")])
        assert e.value.code == 1
