"""Tests for the EAL Phase 3 commit–reveal challenge protocol.

Covers:
- Axiom 13/14/15 enforcement for CHALLENGE events (models.py)
- ChallengeManager cross-event state machine, timing, response metrics
- Local seed stubs (0600, never on-chain until reveal)
- CLI challenge open/reveal/answer/status end-to-end
- E33 experiment smoke
"""

from __future__ import annotations

import json
import os
import stat
from datetime import datetime, timedelta, timezone

import pytest

from adl_lite import Event, EventChain, EventType
from adl_lite.challenge import (
    delete_seed_stub,
    generate_seed,
    load_seed_stub,
    replay_challenges,
    save_seed_stub,
    seed_commitment,
    seed_stub_path,
)

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)
FAKE_PROOF = {"type": "Ed25519Signature2020", "proofValue": "zTEST"}


def _ts(seconds: float) -> str:
    return (BASE + timedelta(seconds=seconds)).isoformat()


def _open_payload(
    cid: str,
    seed: str | None = None,
    deadline_s: float = 300.0,
    window: float = 60.0,
    **overrides,
) -> dict:
    seed = seed if seed is not None else generate_seed()
    payload = {
        "challenge_id": cid,
        "phase": "open",
        "seed_commitment": seed_commitment(seed),
        "reveal_deadline": (BASE + timedelta(seconds=deadline_s)).isoformat(),
        "response_window_s": window,
    }
    payload.update(overrides)
    return payload


def _event(payload: dict, actor: str = "challenger", ts: float = 0.0, proof=True) -> Event:
    return Event(
        concept_id="cap-x",
        event_type=EventType.CHALLENGE,
        actor=actor,
        timestamp=_ts(ts),
        payload=payload,
        proof=dict(FAKE_PROOF) if proof else None,
    )


def _chain_with(*events: Event) -> EventChain:
    chain = EventChain(concept_id="cap-x")
    chain.append(
        Event(
            concept_id="cap-x",
            event_type=EventType.REGISTER,
            actor="registry",
            timestamp=_ts(-10),
        )
    )
    for e in events:
        chain.append(e)
    return chain


def _full_lifecycle(cid: str = "chl-1") -> tuple[EventChain, str]:
    """A valid open → reveal → answer chain."""
    seed = generate_seed()
    chain = _chain_with(
        _event(_open_payload(cid, seed), ts=0.0),
        _event({"challenge_id": cid, "phase": "reveal", "seed": seed}, ts=10.0),
        _event(
            {"challenge_id": cid, "phase": "answer", "output_commitment": "sha256:out"},
            actor="exec-1",
            ts=30.0,
        ),
    )
    return chain, seed


# ---------------------------------------------------------------------------
# Axioms 13/14/15 for CHALLENGE
# ---------------------------------------------------------------------------


class TestChallengeAxioms:
    def test_valid_open_passes(self):
        chain, _ = _full_lifecycle()
        assert chain.verify_integrity()

    def test_missing_challenge_id_fails(self):
        payload = _open_payload("chl-1")
        del payload["challenge_id"]
        chain = _chain_with(_event(payload))
        assert not chain.verify_integrity()
        report = chain.well_formedness_report()
        assert report["axiom_13_evidence_schema"]

    def test_missing_phase_fails(self):
        payload = _open_payload("chl-1")
        del payload["phase"]
        chain = _chain_with(_event(payload))
        assert not chain.verify_integrity()

    def test_bad_phase_fails_axiom15(self):
        payload = _open_payload("chl-1", phase="bogus")
        chain = _chain_with(_event(payload))
        assert not chain.verify_integrity()
        report = chain.well_formedness_report()
        assert report["axiom_15_verdict_consistency"]

    @pytest.mark.parametrize("missing", ["seed_commitment", "reveal_deadline", "response_window_s"])
    def test_open_missing_phase_field_fails(self, missing):
        payload = _open_payload("chl-1")
        del payload[missing]
        chain = _chain_with(_event(payload))
        assert not chain.verify_integrity()
        assert chain.well_formedness_report()["axiom_15_verdict_consistency"]

    def test_reveal_missing_seed_fails(self):
        chain = _chain_with(_event({"challenge_id": "c", "phase": "reveal"}))
        assert not chain.verify_integrity()

    def test_answer_missing_output_commitment_fails(self):
        chain = _chain_with(_event({"challenge_id": "c", "phase": "answer"}, actor="e"))
        assert not chain.verify_integrity()

    def test_missing_proof_fails_axiom14(self):
        chain = _chain_with(_event(_open_payload("chl-1"), proof=False))
        assert not chain.verify_integrity()
        assert chain.well_formedness_report()["axiom_14_proof_presence"]


# ---------------------------------------------------------------------------
# ChallengeManager state machine
# ---------------------------------------------------------------------------


class TestChallengeManager:
    def test_full_lifecycle_answered(self):
        chain, _ = _full_lifecycle()
        mgr = replay_challenges(chain)
        assert mgr.issues == []
        assert mgr.derived_phase("chl-1") == "answered"
        overall = mgr.response_metrics()["overall"]
        assert overall["answered"] == 1
        assert overall["response_rate"] == 1.0

    def test_seed_commitment_mismatch_voids(self):
        seed = generate_seed()
        chain = _chain_with(
            _event(_open_payload("chl-1", seed), ts=0.0),
            _event(
                {"challenge_id": "chl-1", "phase": "reveal", "seed": generate_seed()},
                ts=10.0,
            ),
        )
        mgr = replay_challenges(chain)
        assert any("seed-commitment-mismatch" in i for i in mgr.issues)
        assert mgr.derived_phase("chl-1") == "void"

    def test_reveal_after_deadline_voids(self):
        seed = generate_seed()
        chain = _chain_with(
            _event(_open_payload("chl-1", seed, deadline_s=5.0), ts=0.0),
            _event({"challenge_id": "chl-1", "phase": "reveal", "seed": seed}, ts=10.0),
        )
        mgr = replay_challenges(chain)
        assert any("reveal-after-deadline" in i for i in mgr.issues)
        assert mgr.derived_phase("chl-1") == "void"

    def test_reveal_by_non_challenger_rejected(self):
        seed = generate_seed()
        chain = _chain_with(
            _event(_open_payload("chl-1", seed), ts=0.0),
            _event(
                {"challenge_id": "chl-1", "phase": "reveal", "seed": seed},
                actor="impostor",
                ts=10.0,
            ),
        )
        mgr = replay_challenges(chain)
        assert any("reveal-by-non-challenger" in i for i in mgr.issues)
        assert mgr.derived_phase("chl-1") == "open"

    def test_answer_after_window_times_out(self):
        seed = generate_seed()
        chain = _chain_with(
            _event(_open_payload("chl-1", seed, window=5.0), ts=0.0),
            _event({"challenge_id": "chl-1", "phase": "reveal", "seed": seed}, ts=10.0),
            _event(
                {"challenge_id": "chl-1", "phase": "answer", "output_commitment": "sha256:x"},
                actor="exec-1",
                ts=100.0,
            ),
        )
        mgr = replay_challenges(chain)
        assert any("answer-after-window" in i for i in mgr.issues)
        assert mgr.derived_phase("chl-1") == "timed_out"

    def test_answer_before_reveal_rejected(self):
        chain = _chain_with(
            _event(_open_payload("chl-1"), ts=0.0),
            _event(
                {"challenge_id": "chl-1", "phase": "answer", "output_commitment": "sha256:x"},
                actor="exec-1",
                ts=10.0,
            ),
        )
        mgr = replay_challenges(chain)
        assert any("answer-out-of-phase" in i for i in mgr.issues)
        assert mgr.derived_phase("chl-1") == "open"

    def test_unrevealed_challenge_derives_void_as_of(self):
        chain = _chain_with(_event(_open_payload("chl-1", deadline_s=50.0), ts=0.0))
        mgr = replay_challenges(chain)
        # Chain-internal time (latest event = t0) is before the deadline.
        assert mgr.derived_phase("chl-1") == "open"
        # An auditor at t=100 sees it lapsed to void.
        assert mgr.derived_phase("chl-1", as_of=BASE + timedelta(seconds=100)) == "void"

    def test_unanswered_challenge_derives_timed_out_as_of(self):
        seed = generate_seed()
        chain = _chain_with(
            _event(_open_payload("chl-1", seed, window=20.0), ts=0.0),
            _event({"challenge_id": "chl-1", "phase": "reveal", "seed": seed}, ts=10.0),
        )
        mgr = replay_challenges(chain)
        assert mgr.derived_phase("chl-1") == "revealed"
        assert mgr.derived_phase("chl-1", as_of=BASE + timedelta(seconds=100)) == "timed_out"

    def test_answer_by_non_target_rejected(self):
        seed = generate_seed()
        chain = _chain_with(
            _event(_open_payload("chl-1", seed, target_executor="exec-9"), ts=0.0),
            _event({"challenge_id": "chl-1", "phase": "reveal", "seed": seed}, ts=10.0),
            _event(
                {"challenge_id": "chl-1", "phase": "answer", "output_commitment": "sha256:x"},
                actor="exec-1",
                ts=20.0,
            ),
        )
        mgr = replay_challenges(chain)
        assert any("answer-by-non-target" in i for i in mgr.issues)
        assert mgr.derived_phase("chl-1") == "revealed"

    def test_duplicate_open_rejected(self):
        seed = generate_seed()
        chain = _chain_with(
            _event(_open_payload("chl-1", seed), ts=0.0),
            _event(_open_payload("chl-1", generate_seed()), ts=5.0),
        )
        mgr = replay_challenges(chain)
        assert any("duplicate-challenge-open" in i for i in mgr.issues)
        # First open wins.
        assert mgr.challenges["chl-1"].seed_commitment == seed_commitment(seed)

    def test_response_metrics_executor_filter_and_void_exclusion(self):
        # chl-1 answered by exec-1 (targeted), chl-2 times out (targeted exec-1),
        # chl-3 void (challenger fault) — void must not hurt exec-1's rate.
        c1, _ = _full_lifecycle("chl-1")
        mgr = replay_challenges(c1)

        seed2 = generate_seed()
        for e in (
            _event(_open_payload("chl-2", seed2, window=5.0, target_executor="exec-1"), ts=100.0),
            _event({"challenge_id": "chl-2", "phase": "reveal", "seed": seed2}, ts=110.0),
        ):
            c1.append(e)
        seed3 = generate_seed()
        c1.append(_event(_open_payload("chl-3", seed3, deadline_s=150.0), ts=120.0))

        mgr = replay_challenges(c1)
        audit = BASE + timedelta(seconds=1000)
        overall = mgr.response_metrics(as_of=audit)["overall"]
        assert overall["answered"] == 1
        assert overall["timed_out"] == 1
        assert overall["void"] == 1
        assert overall["response_rate"] == 0.5

        filtered = mgr.response_metrics(executor="exec-1", as_of=audit)["overall"]
        assert filtered["total"] == 2  # chl-1 (answered by) + chl-2 (targeted)
        assert filtered["response_rate"] == 0.5

        nobody = mgr.response_metrics(executor="ghost", as_of=audit)["overall"]
        assert nobody["total"] == 0

    def test_metrics_by_capability(self):
        chain, _ = _full_lifecycle("chl-1")
        other = EventChain(concept_id="cap-y")
        other.append(
            Event(
                concept_id="cap-y",
                event_type=EventType.REGISTER,
                actor="registry",
                timestamp=_ts(-10),
            )
        )
        mgr = replay_challenges(chain)
        # Incremental apply (apply_chain would reset the projection).
        for e in other.events:
            mgr.apply(e)
        by_cap = mgr.response_metrics()["by_capability"]
        assert set(by_cap) == {"cap-x"}


# ---------------------------------------------------------------------------
# Seed stubs
# ---------------------------------------------------------------------------


class TestSeedStubs:
    def test_roundtrip_and_permissions(self, tmp_path):
        seed = generate_seed()
        path = save_seed_stub(
            tmp_path,
            "chl-1",
            seed=seed,
            seed_commitment_value=seed_commitment(seed),
            reveal_deadline=_ts(300),
            response_window_s=60.0,
            target_executor="exec-1",
        )
        assert path == seed_stub_path(tmp_path, "chl-1")
        mode = stat.S_IMODE(os.stat(path).st_mode)
        assert mode == 0o600

        stub = load_seed_stub(tmp_path, "chl-1")
        assert stub is not None
        assert stub["seed"] == seed
        assert stub["target_executor"] == "exec-1"

        assert delete_seed_stub(tmp_path, "chl-1")
        assert load_seed_stub(tmp_path, "chl-1") is None
        assert not delete_seed_stub(tmp_path, "chl-1")

    def test_malformed_stub_returns_none(self, tmp_path):
        path = seed_stub_path(tmp_path, "chl-bad")
        path.parent.mkdir(parents=True)
        path.write_text("{not json", encoding="utf-8")
        assert load_seed_stub(tmp_path, "chl-bad") is None


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------


def _write_doc(tmp_path, adl_id: str = "cap-chl"):
    doc = tmp_path / "cap.md"
    doc.write_text(
        f"""---
adl_type: concept
adl_id: {adl_id}
status: provisional
confidence: 0.0
scope: public
provisional_names:
  en: "Challenge CLI Cap"
---

## Overview

Capability under challenge CLI test.

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
    return doc


def _write_key(tmp_path):
    from cryptography.hazmat.primitives import serialization

    from adl_lite.ld_proof import generate_keypair

    key = generate_keypair()
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    path = tmp_path / "k.pem"
    path.write_bytes(pem)
    return path


class TestCliChallenge:
    def _register(self, doc, state, capsys):
        from adl_lite.cli import main

        with pytest.raises(SystemExit) as e:
            main(["consensus", "register", str(doc), "--state", str(state)])
        assert e.value.code == 0
        capsys.readouterr()  # flush "registered ..." so later JSON stdout parses clean

    def test_full_challenge_flow(self, tmp_path, capsys):
        from adl_lite.cli import _load_engine, main

        doc = _write_doc(tmp_path)
        key_file = _write_key(tmp_path)
        state = tmp_path / "state.json"
        log_dir = tmp_path / "logs"
        adl_id = "cap-chl"
        self._register(doc, state, capsys)

        with pytest.raises(SystemExit) as e:
            main(
                [
                    "challenge",
                    "open",
                    str(doc),
                    "--actor",
                    "challenger-1",
                    "--key-file",
                    str(key_file),
                    "--challenge-id",
                    "chl-e2e",
                    "--target-executor",
                    "exec-1",
                    "--state",
                    str(state),
                    "--log-dir",
                    str(log_dir),
                    "--json",
                ]
            )
        assert e.value.code == 0
        opened = json.loads(capsys.readouterr().out)
        assert opened["challenge_id"] == "chl-e2e"
        stub = seed_stub_path(log_dir, "chl-e2e")
        assert stub.exists()
        assert stat.S_IMODE(os.stat(stub).st_mode) == 0o600

        with pytest.raises(SystemExit) as e:
            main(
                [
                    "challenge",
                    "reveal",
                    str(doc),
                    "--challenge-id",
                    "chl-e2e",
                    "--actor",
                    "challenger-1",
                    "--key-file",
                    str(key_file),
                    "--state",
                    str(state),
                    "--log-dir",
                    str(log_dir),
                    "--json",
                ]
            )
        assert e.value.code == 0
        revealed = json.loads(capsys.readouterr().out)
        assert revealed["seed"]
        assert not stub.exists()  # stub removed after successful reveal

        with pytest.raises(SystemExit) as e:
            main(
                [
                    "challenge",
                    "answer",
                    str(doc),
                    "--challenge-id",
                    "chl-e2e",
                    "--actor",
                    "exec-1",
                    "--key-file",
                    str(key_file),
                    "--auto-run",
                    "--state",
                    str(state),
                    "--log-dir",
                    str(log_dir),
                    "--json",
                ]
            )
        assert e.value.code == 0
        answered = json.loads(capsys.readouterr().out)
        assert answered["auto_run"] is True
        assert answered["output_commitment"].startswith("sha256:")

        with pytest.raises(SystemExit) as e:
            main(["challenge", "status", adl_id, "--state", str(state), "--json"])
        assert e.value.code == 0
        status = json.loads(capsys.readouterr().out)
        row = status["challenges"][0]
        assert row["derived_phase"] == "answered"
        assert status["response_metrics"]["overall"]["response_rate"] == 1.0
        assert status["issues"] == []

        chain = _load_engine(state).chains[adl_id]
        assert chain.verify_integrity()

    def test_answer_with_output_hash(self, tmp_path, capsys):
        from adl_lite.cli import main

        doc = _write_doc(tmp_path)
        key_file = _write_key(tmp_path)
        state = tmp_path / "state.json"
        log_dir = tmp_path / "logs"
        self._register(doc, state, capsys)

        for cmd in (
            [
                "challenge",
                "open",
                str(doc),
                "--actor",
                "c",
                "--key-file",
                str(key_file),
                "--challenge-id",
                "chl-h",
                "--state",
                str(state),
                "--log-dir",
                str(log_dir),
            ],
            [
                "challenge",
                "reveal",
                str(doc),
                "--challenge-id",
                "chl-h",
                "--actor",
                "c",
                "--key-file",
                str(key_file),
                "--state",
                str(state),
                "--log-dir",
                str(log_dir),
            ],
            [
                "challenge",
                "answer",
                str(doc),
                "--challenge-id",
                "chl-h",
                "--actor",
                "exec-1",
                "--key-file",
                str(key_file),
                "--output-hash",
                "sha256:deadbeef",
                "--state",
                str(state),
                "--log-dir",
                str(log_dir),
            ],
        ):
            with pytest.raises(SystemExit) as e:
                main(cmd)
            assert e.value.code == 0, capsys.readouterr().err

    def test_answer_before_reveal_refused(self, tmp_path, capsys):
        from adl_lite.cli import main

        doc = _write_doc(tmp_path)
        key_file = _write_key(tmp_path)
        state = tmp_path / "state.json"
        log_dir = tmp_path / "logs"
        self._register(doc, state, capsys)

        with pytest.raises(SystemExit) as e:
            main(
                [
                    "challenge",
                    "open",
                    str(doc),
                    "--actor",
                    "c",
                    "--key-file",
                    str(key_file),
                    "--challenge-id",
                    "chl-pending",
                    "--state",
                    str(state),
                    "--log-dir",
                    str(log_dir),
                ]
            )
        assert e.value.code == 0

        with pytest.raises(SystemExit) as e:
            main(
                [
                    "challenge",
                    "answer",
                    str(doc),
                    "--challenge-id",
                    "chl-pending",
                    "--actor",
                    "exec-1",
                    "--key-file",
                    str(key_file),
                    "--output-hash",
                    "sha256:x",
                    "--state",
                    str(state),
                    "--log-dir",
                    str(log_dir),
                ]
            )
        assert e.value.code == 1
        assert "not awaiting an answer" in capsys.readouterr().err

    def test_reveal_without_stub_refused(self, tmp_path, capsys):
        from adl_lite.cli import main

        doc = _write_doc(tmp_path)
        key_file = _write_key(tmp_path)
        state = tmp_path / "state.json"
        self._register(doc, state, capsys)

        with pytest.raises(SystemExit) as e:
            main(
                [
                    "challenge",
                    "open",
                    str(doc),
                    "--actor",
                    "c",
                    "--key-file",
                    str(key_file),
                    "--challenge-id",
                    "chl-nostub",
                    "--state",
                    str(state),
                    "--log-dir",
                    str(tmp_path / "logs"),
                ]
            )
        assert e.value.code == 0

        with pytest.raises(SystemExit) as e:
            main(
                [
                    "challenge",
                    "reveal",
                    str(doc),
                    "--challenge-id",
                    "chl-nostub",
                    "--actor",
                    "c",
                    "--key-file",
                    str(key_file),
                    "--state",
                    str(state),
                    "--log-dir",
                    str(tmp_path / "other-logs"),
                ]
            )
        assert e.value.code == 1
        assert "no local seed stub" in capsys.readouterr().err

    def test_open_unregistered_capability_refused(self, tmp_path, capsys):
        from adl_lite.cli import main

        doc = _write_doc(tmp_path)
        key_file = _write_key(tmp_path)
        with pytest.raises(SystemExit) as e:
            main(
                [
                    "challenge",
                    "open",
                    str(doc),
                    "--actor",
                    "c",
                    "--key-file",
                    str(key_file),
                    "--state",
                    str(tmp_path / "s.json"),
                    "--log-dir",
                    str(tmp_path / "logs"),
                ]
            )
        assert e.value.code == 1
        assert "not registered" in capsys.readouterr().err

    def test_status_unregistered(self, tmp_path, capsys):
        from adl_lite.cli import main

        with pytest.raises(SystemExit) as e:
            main(["challenge", "status", "cap-ghost", "--state", str(tmp_path / "s.json")])
        assert e.value.code == 1


# ---------------------------------------------------------------------------
# E33 smoke
# ---------------------------------------------------------------------------


class TestE33:
    def test_e33_runs_and_passes(self):
        from experiments.e33_challenge_game import E33ChallengeGame

        result = E33ChallengeGame().run()
        assert result.status == "passed"
        m = result.metrics
        assert m["f_star_analytic"] == 0.1
        assert m["f_star_abs_error"] <= 0.03
        assert m["manager_derivations_match_ground_truth"] is True
