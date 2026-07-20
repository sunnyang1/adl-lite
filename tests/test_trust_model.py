"""Tests for the Phase-1 trust model (adl_lite.trust_model).

Covers:
    * ConsensusConfig / ResolvedConsensusConfig derivation (B1 threshold)
    * TrustValidator B1 (N_min distinct validators)
    * TrustValidator B2 (DID binding / signature verification)
    * TrustValidator B3 (Sybil identity-merge + self-validation loop)
    * TrustValidator B4 (validator diversity flag)
    * Explicit rejection of did:ethr by the Phase-1 trust layer

All DID signing uses did:key (local Ed25519) so no network is required.

IMPORTANT signing contract: ``EventChain.append`` recomputes each event's
canonical ``hash`` to include the previous event's hash (chaining). Therefore an
event MUST be signed *after* it has been appended to the chain — the signature
is computed over the final ``event.hash``.
"""

from __future__ import annotations

import base64
import logging

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from adl_lite.did_resolver import create_did_key
from adl_lite.exceptions import ADLUnsupportedDIDMethodError
from adl_lite.models import Event, EventChain, EventType
from adl_lite.trust_model import (
    ConsensusConfig,
    TrustValidator,
    ValidationResult,
)


class _Signer:
    """Helper that owns an Ed25519 key pair and a matching did:key DID."""

    def __init__(self) -> None:
        self.priv = ed25519.Ed25519PrivateKey.generate()
        self.did = create_did_key(self.priv.public_key())

    def sign(self, event: Event) -> Event:
        """Attach a base64 Ed25519 signature over the (final) ``event.hash``."""
        sig = self.priv.sign(event.hash.encode("utf-8"))
        event.signature = base64.b64encode(sig).decode("ascii")
        return event


def _ev(cid: str, etype: EventType, actor: str) -> Event:
    """Build an UNSIGNED event (signing happens after chain construction)."""
    return Event(concept_id=cid, event_type=etype, actor=actor)


def _build(cid: str, events: list[Event]) -> EventChain:
    return EventChain(concept_id=cid, events=events)


def _sign_chain(chain: EventChain, signers: dict[str, _Signer]) -> EventChain:
    """Sign every event whose actor matches a did in *signers* (post-append)."""
    for ev in chain.events:
        signer = signers.get(ev.actor)
        if signer is not None:
            signer.sign(ev)
    return chain


# ---------------------------------------------------------------------------
# ConsensusConfig / resolve()
# ---------------------------------------------------------------------------


class TestConsensusConfig:
    def test_prod_default_min_is_two(self) -> None:
        resolved = ConsensusConfig(mode="prod").resolve()
        assert resolved.min_distinct_validators == 2
        assert resolved.require_did_binding is True
        assert resolved.mode == "prod"

    def test_dev_default_min_is_one(self) -> None:
        resolved = ConsensusConfig(mode="dev").resolve()
        assert resolved.min_distinct_validators == 1
        assert resolved.mode == "dev"

    def test_explicit_min_overrides_default(self) -> None:
        resolved = ConsensusConfig(mode="prod", min_distinct_validators=3).resolve()
        assert resolved.min_distinct_validators == 3

    def test_prod_forces_did_binding_even_if_false(self) -> None:
        resolved = ConsensusConfig(mode="prod", require_did_binding=False).resolve()
        # Production always mandates DID binding regardless of the input flag.
        assert resolved.require_did_binding is True

    def test_dev_allows_did_binding_disabled(self) -> None:
        resolved = ConsensusConfig(mode="dev", require_did_binding=False).resolve()
        assert resolved.require_did_binding is False

    def test_low_prod_min_warns_but_does_not_raise(self) -> None:
        import logging

        logger = logging.getLogger("adl_lite.trust_model")

        class _RecordHandler(logging.Handler):
            def __init__(self) -> None:
                super().__init__()
                self.records: list[logging.LogRecord] = []

            def emit(self, record: logging.LogRecord) -> None:
                self.records.append(record)

        handler = _RecordHandler()
        prev_propagate = logger.propagate
        logger.addHandler(handler)
        try:
            resolved = ConsensusConfig(mode="prod", min_distinct_validators=1).resolve()
        finally:
            logger.removeHandler(handler)
            logger.propagate = prev_propagate
        # The explicit (low) value is preserved; only a warning is emitted.
        assert resolved.min_distinct_validators == 1
        assert any("below the recommended production minimum" in r.message for r in handler.records)

    def test_resolved_exposes_effective_fields(self) -> None:
        resolved = ConsensusConfig(mode="prod", enforce_validator_diversity=True).resolve()
        # The resolved config is the single source of truth consumed by the validator.
        assert resolved.min_distinct_validators == 2
        assert resolved.require_did_binding is True
        assert resolved.enforce_validator_diversity is True
        assert resolved.mode == "prod"


# ---------------------------------------------------------------------------
# B1 — N_min distinct validators
# ---------------------------------------------------------------------------


class TestNMin:
    def test_prod_two_distinct_validators_pass(self) -> None:
        cid = "cap-b1-ok"
        s1, s2 = _Signer(), _Signer()
        chain = _build(
            cid,
            [
                _ev(cid, EventType.REGISTER, "alice"),
                _ev(cid, EventType.VALIDATE, s1.did),
                _ev(cid, EventType.VALIDATE, s2.did),
            ],
        )
        _sign_chain(chain, {s1.did: s1, s2.did: s2})
        result = TrustValidator().validate_event_chain(chain)
        assert result.valid is True
        assert result.distinct_validators == 2
        assert result.did_bound is True

    def test_prod_single_validator_fails(self) -> None:
        cid = "cap-b1-single"
        s1 = _Signer()
        chain = _build(
            cid,
            [
                _ev(cid, EventType.REGISTER, "alice"),
                _ev(cid, EventType.VALIDATE, s1.did),
            ],
        )
        _sign_chain(chain, {s1.did: s1})
        result = TrustValidator().validate_event_chain(chain)
        assert result.valid is False
        assert result.distinct_validators == 1
        assert any("insufficient distinct validators" in e for e in result.errors)

    def test_dev_single_validator_passes(self) -> None:
        cid = "cap-b1-dev"
        s1 = _Signer()
        chain = _build(
            cid,
            [
                _ev(cid, EventType.REGISTER, "alice"),
                _ev(cid, EventType.VALIDATE, s1.did),
            ],
        )
        _sign_chain(chain, {s1.did: s1})
        result = TrustValidator().validate_event_chain(chain, ConsensusConfig(mode="dev"))
        assert result.valid is True
        assert result.distinct_validators == 1

    def test_prod_non_did_single_validator_fails(self) -> None:
        cid = "cap-b1-nondid"
        chain = _build(
            cid,
            [
                _ev(cid, EventType.REGISTER, "alice"),
                _ev(cid, EventType.VALIDATE, "bob"),
            ],
        )
        result = TrustValidator().validate_event_chain(chain)
        assert result.valid is False
        assert result.distinct_validators == 1

    def test_dev_non_did_single_validator_passes(self) -> None:
        cid = "cap-b1-nondid-dev"
        chain = _build(
            cid,
            [
                _ev(cid, EventType.REGISTER, "alice"),
                _ev(cid, EventType.VALIDATE, "bob"),
            ],
        )
        result = TrustValidator().validate_event_chain(chain, ConsensusConfig(mode="dev"))
        assert result.valid is True

    def test_same_key_family_counts_once(self) -> None:
        """Two VALIDATE events from the same did:key collapse to one identity."""
        cid = "cap-b1-sybil"
        s1 = _Signer()
        chain = _build(
            cid,
            [
                _ev(cid, EventType.REGISTER, "alice"),
                _ev(cid, EventType.VALIDATE, s1.did),
                _ev(cid, EventType.VALIDATE, s1.did),
            ],
        )
        _sign_chain(chain, {s1.did: s1})
        result = TrustValidator().validate_event_chain(chain)
        assert result.distinct_validators == 1
        assert result.valid is False
        assert any("insufficient distinct validators" in e for e in result.errors)

    def test_empty_chain_invalid(self) -> None:
        chain = _build("cap-empty", [])
        result = TrustValidator().validate_event_chain(chain)
        assert result.valid is False
        assert any("chain is empty" in e for e in result.errors)


# ---------------------------------------------------------------------------
# B2 — DID binding / signature verification
# ---------------------------------------------------------------------------


class TestDidBinding:
    def test_forged_signature_rejected(self) -> None:
        cid = "cap-b2-forged"
        s1 = _Signer()
        s_other = _Signer()
        chain = _build(
            cid,
            [
                _ev(cid, EventType.REGISTER, "alice"),
                _ev(cid, EventType.VALIDATE, s1.did),
            ],
        )
        # Sign the VALIDATE event with the WRONG key (after append).
        s_other.sign(chain.events[1])
        result = TrustValidator().validate_event_chain(chain)
        assert result.valid is False
        assert result.did_bound is False
        assert any("DID binding failed" in e for e in result.errors)

    def test_missing_signature_rejected(self) -> None:
        cid = "cap-b2-missing"
        s1 = _Signer()
        # Build the chain but deliberately do NOT sign the VALIDATE event.
        chain = _build(
            cid,
            [
                _ev(cid, EventType.REGISTER, "alice"),
                _ev(cid, EventType.VALIDATE, s1.did),
            ],
        )
        result = TrustValidator().validate_event_chain(chain)
        assert result.valid is False
        assert result.did_bound is False
        assert any("has no signature" in e for e in result.errors)


# ---------------------------------------------------------------------------
# B3 — Sybil resistance (identity merge + self-validation loop)
# ---------------------------------------------------------------------------


class TestSybil:
    def test_self_validation_loop_detected(self) -> None:
        """The discoverer (first REGISTER) must not validate its own concept."""
        cid = "cap-b3-loop"
        s1 = _Signer()
        chain = _build(
            cid,
            [
                _ev(cid, EventType.REGISTER, s1.did),
                _ev(cid, EventType.VALIDATE, s1.did),
            ],
        )
        _sign_chain(chain, {s1.did: s1})
        result = TrustValidator().validate_event_chain(chain)
        assert result.sybil_filtered is True
        assert result.valid is False
        assert any("self-validation loop" in e for e in result.errors)

    def test_distinct_discoverer_and_validator_ok(self) -> None:
        cid = "cap-b3-ok"
        s1, s2 = _Signer(), _Signer()
        chain = _build(
            cid,
            [
                _ev(cid, EventType.REGISTER, s1.did),
                _ev(cid, EventType.VALIDATE, s2.did),
            ],
        )
        _sign_chain(chain, {s1.did: s1, s2.did: s2})
        # dev mode so a single distinct validator is sufficient.
        result = TrustValidator().validate_event_chain(chain, ConsensusConfig(mode="dev"))
        assert result.sybil_filtered is False
        assert result.valid is True


# ---------------------------------------------------------------------------
# B4 — validator diversity
# ---------------------------------------------------------------------------


class TestDiversity:
    def test_diversity_satisfied_with_distinct_dids(self) -> None:
        cid = "cap-b4-ok"
        s1, s2 = _Signer(), _Signer()
        chain = _build(
            cid,
            [
                _ev(cid, EventType.REGISTER, "alice"),
                _ev(cid, EventType.VALIDATE, s1.did),
                _ev(cid, EventType.VALIDATE, s2.did),
            ],
        )
        _sign_chain(chain, {s1.did: s1, s2.did: s2})
        cfg = ConsensusConfig(
            mode="prod", enforce_validator_diversity=True, min_distinct_validators=2
        )
        result = TrustValidator().validate_event_chain(chain, cfg)
        assert result.diversity_satisfied is True
        assert result.valid is True


# ---------------------------------------------------------------------------
# did:ethr explicitly unsupported by the Phase-1 trust layer
# ---------------------------------------------------------------------------


class TestUnsupportedDID:
    def test_did_ethr_raises(self) -> None:
        cid = "cap-ethr"
        # A non-empty signature forces the validator down the DID-binding path,
        # where did:ethr is explicitly rejected by the Phase-1 trust layer.
        reg = _ev(
            cid,
            EventType.REGISTER,
            "did:ethr:0x1234567890123456789012345678901234567890",
        )
        reg.signature = "x"
        chain = _build(cid, [reg])
        with pytest.raises(ADLUnsupportedDIDMethodError):
            TrustValidator().validate_event_chain(chain)

    def test_did_ethr_validator_raises(self) -> None:
        cid = "cap-ethr-val"
        s1 = _Signer()
        val_ethr = _ev(
            cid,
            EventType.VALIDATE,
            "did:ethr:0x1234567890123456789012345678901234567890",
        )
        val_ethr.signature = "x"
        chain = _build(
            cid,
            [
                _ev(cid, EventType.REGISTER, "alice"),
                _ev(cid, EventType.VALIDATE, s1.did),
                val_ethr,
            ],
        )
        _sign_chain(chain, {s1.did: s1})
        with pytest.raises(ADLUnsupportedDIDMethodError):
            TrustValidator().validate_event_chain(chain)


# ---------------------------------------------------------------------------
# Integration with ConsensusEngine convenience wrapper
# ---------------------------------------------------------------------------


class TestConsensusEngineBridge:
    def test_consensus_engine_validate_event_chain(self) -> None:
        from adl_lite.consensus import validate_event_chain as ce_validate

        cid = "cap-bridge"
        s1, s2 = _Signer(), _Signer()
        chain = _build(
            cid,
            [
                _ev(cid, EventType.REGISTER, "alice"),
                _ev(cid, EventType.VALIDATE, s1.did),
                _ev(cid, EventType.VALIDATE, s2.did),
            ],
        )
        _sign_chain(chain, {s1.did: s1, s2.did: s2})
        # Defaults to prod mode (ADL_ENV unset) -> valid with 2 validators.
        result = ce_validate(chain)
        assert isinstance(result, ValidationResult)
        assert result.valid is True
        assert result.distinct_validators == 2

    def test_consensus_engine_bridge_dev_single(self) -> None:
        from adl_lite.consensus import validate_event_chain as ce_validate

        cid = "cap-bridge-dev"
        s1 = _Signer()
        chain = _build(
            cid,
            [
                _ev(cid, EventType.REGISTER, "alice"),
                _ev(cid, EventType.VALIDATE, s1.did),
            ],
        )
        _sign_chain(chain, {s1.did: s1})
        result = ce_validate(chain, ConsensusConfig(mode="dev"))
        assert result.valid is True
