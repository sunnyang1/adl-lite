"""
ADL Lite — Phase-1 Trust Model (independent validation layer).

This module Hardens the consensus layer with a production-grade trust model:

    B1  N_min           — enforce a minimum number of *distinct* validators,
                           derived per mode (prod >= 2, dev >= 1).
    B2  DID binding      — verify that DID-signed events carry a valid signature
                           over ``event.hash`` (reusing the existing
                           :mod:`~adl_lite.did_resolver` crypto paths).
    B3  Basic Sybil      — collapse the same key family / same DID into a single
                           identity (so duplicate validators do not inflate N_min)
                           and forbid the discoverer from self-validating.
    B4  Diversity (P1 placeholder)
                         — optionally require validators from distinct DID
                           methods / key families. In Phase 1 the diversity gate
                           is conservative (see
                           :meth:`TrustValidator._identity_keys`): the diversity
                           key is identity-scoped, so the B4 check only fires
                           when identity-merge (B3) would have collapsed
                           validators. True method-level diversity is deferred to
                           a later phase.

Design notes
------------
* This layer is **additive** and reuses existing infrastructure
  (:class:`~adl_lite.did_resolver.DIDResolver`,
  :func:`~adl_lite.did_resolver.verify_did_signature`). It does **not** modify
  :class:`~adl_lite.consensus.ConsensusEngine` or its ``_effective_n_min`` logic.
* ``ConsensusConfig`` is the single source of truth for the trust layer's N_min
  threshold (kept separate from ``ConsensusEngine._effective_n_min`` so that the
  legacy transition guard and this layer can evolve independently).
* ``did:ethr`` is explicitly *unsupported* by the Phase-1 trust layer and raises
  :class:`~adl_lite.exceptions.ADLUnsupportedDIDMethodError` (the existing
  ``did_resolver`` keeps full ethr support for other callers).
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass, field
from typing import Literal

from .did_resolver import DIDResolver, is_did, resolve_did_key, verify_did_signature
from .exceptions import ADLUnsupportedDIDMethodError  # type: ignore[attr-defined]
from .models import Event, EventChain, EventType

logger = logging.getLogger("adl_lite.trust_model")

# Effective minimum distinct validators per mode.
_PROD_MIN_VALIDATORS = 2
_DEV_MIN_VALIDATORS = 1


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class ConsensusConfig:
    """Configuration for the Phase-1 trust-model validation layer.

    This is the single source of truth for the trust layer's N_min threshold and
    DID-binding requirements. It is intentionally independent from
    :class:`~adl_lite.consensus.ConsensusEngine` (which keeps its own
    ``_effective_n_min`` for the VALIDATE-transition guard).
    """

    mode: Literal["dev", "prod"] = "prod"
    min_distinct_validators: int | None = None
    require_did_binding: bool = True
    enforce_validator_diversity: bool = False

    def resolve(self) -> ResolvedConsensusConfig:
        """Derive the effective configuration from the declared *mode*.

        * ``mode="prod"`` forces ``require_did_binding=True`` and a minimum of 2
          distinct validators (unless an explicit, higher value is given).
        * ``mode="dev"`` allows a relaxed minimum of 1 validator for local
          development and logs a non-production marker.
        * A low explicit threshold in prod only emits a warning — it never raises.
        """
        min_val = self.min_distinct_validators
        if min_val is None:
            min_val = _PROD_MIN_VALIDATORS if self.mode == "prod" else _DEV_MIN_VALIDATORS

        require_did = self.require_did_binding
        if self.mode == "prod":
            # In production, DID binding is always mandatory.
            require_did = True
            if min_val < _PROD_MIN_VALIDATORS:
                logger.warning(
                    "ConsensusConfig(prod) with min_distinct_validators=%s is below the "
                    "recommended production minimum of %s. Continuing with the explicit value.",
                    min_val,
                    _PROD_MIN_VALIDATORS,
                )
        else:
            logger.info(
                "ConsensusConfig running in DEV mode (min_distinct_validators=%s). "
                "This is NOT a production-safe configuration.",
                min_val,
            )

        return ResolvedConsensusConfig(
            mode=self.mode,
            min_distinct_validators=min_val,
            require_did_binding=require_did,
            enforce_validator_diversity=self.enforce_validator_diversity,
        )


@dataclass
class ResolvedConsensusConfig:
    """Effective, mode-resolved consensus configuration."""

    mode: Literal["dev", "prod"]
    min_distinct_validators: int
    require_did_binding: bool
    enforce_validator_diversity: bool


@dataclass
class ValidationResult:
    """Outcome of :meth:`TrustValidator.validate_event_chain`."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    distinct_validators: int = 0
    did_bound: bool = True
    sybil_filtered: bool = False
    diversity_satisfied: bool = True


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class TrustValidator:
    """Independent trust-model validation layer for event chains.

    Implements B1 (N_min), B2 (DID binding), B3 (basic Sybil resistance), and
    B4 (validator diversity, P1). It deliberately reuses the existing
    :mod:`~adl_lite.did_resolver` and :mod:`~adl_lite.key_registry`
    infrastructure rather than re-implementing signature verification.
    """

    def __init__(self, resolver: DIDResolver | None = None) -> None:
        self._resolver = resolver or DIDResolver()

    def validate_event_chain(
        self, chain: EventChain, config: ConsensusConfig | None = None
    ) -> ValidationResult:
        """Validate *chain* against *config* (defaults to prod mode).

        Raises:
            ADLUnsupportedDIDMethodError: if a ``did:ethr`` actor is encountered
                (explicitly unsupported by the Phase-1 trust layer).
        """
        config = config or ConsensusConfig()
        resolved = config.resolve()
        errors: list[str] = []

        events = list(chain.events)
        if not events:
            return ValidationResult(valid=False, errors=["chain is empty"])

        # B3 (part 1): the discoverer is the actor of the first
        # REGISTER/SNAPSHOT event. The discoverer may not also validate itself.
        discoverer = self._find_discoverer(events)

        # Collect VALIDATE events — these are the validators.
        validate_events = [e for e in events if e.event_type == EventType.VALIDATE]

        # B3 (part 2): identity-merge keys + self-validation loop detection.
        identity_keys: set[str] = set()
        diversity_keys: set[tuple[str, str]] = set()
        sybil_filtered = False
        for ev in validate_events:
            actor = ev.actor
            if actor == discoverer:
                # Self-validation loop: discoverer validating its own concept.
                sybil_filtered = True
                errors.append(
                    f"self-validation loop: validator '{actor}' is the discoverer of "
                    f"concept '{chain.concept_id}' and may not validate its own concept"
                )
                continue
            try:
                ident, diversity = self._identity_keys(actor)
            except ADLUnsupportedDIDMethodError:
                # Propagate explicitly-unsupported DID methods.
                raise
            except Exception as exc:  # pragma: no cover - defensive
                errors.append(f"could not resolve identity for validator '{actor}': {exc}")
                continue
            identity_keys.add(ident)
            diversity_keys.add(diversity)

        distinct_validators = len(identity_keys)

        # B1: N_min threshold.
        if distinct_validators < resolved.min_distinct_validators:
            errors.append(
                f"insufficient distinct validators: got {distinct_validators}, "
                f"need at least {resolved.min_distinct_validators} (mode={resolved.mode})"
            )

        # B2: DID binding — verify signatures for every DID-signed event.
        did_bound = True
        for ev in events:
            actor = ev.actor
            if not is_did(actor):
                continue
            if not ev.signature:
                did_bound = False
                errors.append(f"event {ev.event_id} by DID actor '{actor}' has no signature")
                continue
            try:
                self._verify_did_event(ev)
            except ADLUnsupportedDIDMethodError:
                # did:ethr is explicitly unsupported by the Phase-1 trust layer.
                raise
            except Exception as exc:
                did_bound = False
                errors.append(
                    f"DID binding failed for actor '{actor}' on event {ev.event_id}: {exc}"
                )

        # B4: validator diversity (Phase-1 placeholder — known limitation).
        # The diversity key is derived from the validator's *identity* (see
        # _identity_keys), so len(diversity_keys) always equals
        # distinct_validators and this gate is effectively a no-op: in Phase-1
        # B4 does NOT prevent collusion by same-family / same-organisation
        # validators. Phase-2 will source diversity keys from real
        # organisational affiliation (e.g. verified DID service endpoints or
        # an out-of-band institution registry), at which point this branch
        # becomes active. The check is retained now to document and pin the
        # intended later-phase semantics.
        diversity_satisfied = True
        if resolved.enforce_validator_diversity and distinct_validators > 0:
            if len(diversity_keys) < distinct_validators:
                diversity_satisfied = False
                errors.append(
                    f"validator diversity not satisfied: {len(diversity_keys)} distinct "
                    f"identity families for {distinct_validators} validators"
                )

        valid = (
            not errors
            and distinct_validators >= resolved.min_distinct_validators
            and did_bound
            and diversity_satisfied
        )

        return ValidationResult(
            valid=valid,
            errors=errors,
            distinct_validators=distinct_validators,
            did_bound=did_bound,
            sybil_filtered=sybil_filtered,
            diversity_satisfied=diversity_satisfied,
        )

    # -- helpers -------------------------------------------------------------

    def _find_discoverer(self, events: list[Event]) -> str | None:
        """Return the actor of the first REGISTER/SNAPSHOT (the discoverer)."""
        for ev in events:
            if ev.event_type in (EventType.REGISTER, EventType.SNAPSHOT):
                return ev.actor
        return None

    def _identity_keys(self, actor: str) -> tuple[str, tuple[str, str]]:
        """Return ``(identity_merge_key, diversity_key)`` for a validator actor.

        * identity_merge_key collapses the same key family / same DID into a
          single identity so duplicate validators do not inflate N_min (Sybil
          resistance, B3).
        * diversity_key captures the DID method / key family for B4.

          NOTE (Phase-1 placeholder — known limitation): the diversity key is
          currently derived from the validator's *identity* (one distinct key
          per validator), so ``len(diversity_keys)`` equals
          ``distinct_validators`` and the B4 gate
          (``len(diversity_keys) < distinct_validators``) is effectively a no-op
          for did:key-only chains. Consequently, **Phase-1 B4 does not block
          validators from the same key family or organisation** — N
          controllers of one institution all satisfy the gate. Phase-2 will
          derive diversity keys from real organisational affiliation (e.g.
          verified DID service endpoints or an out-of-band institution
          registry) instead of identity. Method-level diversity — collapsing
          this key to the DID *method* (e.g. ``("method", "key")`` /
          ``("method", "web")``) — was also considered but deferred, because
          the Phase-1 validator set is effectively all did:key
          (did:web needs network resolution; did:ethr is explicitly
          unsupported).
        """
        if not is_did(actor):
            return (f"actor:{actor}", ("actor", actor))

        method = DIDResolver._method(actor)
        if method == "ethr":
            raise ADLUnsupportedDIDMethodError(
                f"DID method 'did:ethr' is not supported by the Phase-1 trust layer "
                f"(actor='{actor}')"
            )
        if method == "key":
            # Identity = public key bytes (same key => same identity).
            doc = resolve_did_key(actor)
            pk = doc.verification_methods[0].public_key_bytes
            ident = "key:" + base64.b64encode(pk).decode("ascii")
            return (ident, ("key", ident))
        if method == "web":
            # Identity = method + id (the DID itself); no network resolution needed.
            ident = "web:" + actor
            return (ident, ("web", actor))
        # Unknown method (future extension): fall back to actor string.
        return (f"actor:{actor}", ("actor", actor))

    def _verify_did_event(self, event: Event) -> None:
        """Verify the DID signature of a single event. Raises on failure."""
        actor = event.actor
        method = DIDResolver._method(actor)
        if method == "ethr":
            raise ADLUnsupportedDIDMethodError(
                f"DID method 'did:ethr' is not supported by the Phase-1 trust layer "
                f"(actor='{actor}')"
            )
        signature = base64.b64decode(event.signature)
        message = event.hash.encode("utf-8")
        # Reuse the existing resolver's signature verification (handles did:key
        # locally and did:web over HTTPS using the already-implemented crypto).
        if not verify_did_signature(actor, message, signature):
            raise ValueError("signature verification failed")
