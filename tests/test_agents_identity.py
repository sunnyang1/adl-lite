"""M1a identity tests: agent registration, DID signing, N_min, admin bootstrap,
Sybil defense, profile derivation, state round-trip, deprecation.
"""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from adl_lite import chain_kind
from adl_lite.agents.identity import AgentProfile, AgentRegistry, AgentRole, AgentStatus
from adl_lite.cli import _load_engine, _save_engine
from adl_lite.did_resolver import create_did_key
from adl_lite.exceptions import ADLConsensusError
from adl_lite.ld_proof import create_event_proof, generate_keypair, verify_event_proof
from adl_lite.models import EventType


def _pubkey_b64(priv) -> str:
    return base64.b64encode(priv.public_key().public_bytes_raw()).decode("ascii")


def _sign_bytes(priv, message: bytes) -> str:
    return base64.b64encode(priv.sign(message)).decode("ascii")


def _register(
    registry: AgentRegistry,
    name: str,
    role: AgentRole = AgentRole.DISCOVERER,
    priv=None,
    did: str = "",
) -> tuple[AgentProfile, str, str]:
    """Register an agent; returns (profile, did, private_key or "")."""
    profile = AgentProfile(
        did=did or (create_did_key(priv.public_key()) if priv else name),
        role=role,
        name=name,
        capabilities=["parse", "register"],
    )
    chain = registry.register_agent(profile)
    if priv:
        # P2-10: caller holds the key; attach genesis signature + proof.
        genesis = chain.events[0]
        genesis.signature = _sign_bytes(priv, genesis.hash.encode("utf-8"))
        genesis.proof = create_event_proof(genesis, priv, verification_method=profile.did)
    return profile, profile.did, (priv if priv else "")


# ---------------------------------------------------------------------------
# Trust-root bootstrap helpers: the FIRST agent is admin-attested (external
# root of trust, P0-1); later agents are validated by ACTIVE agents.
# ---------------------------------------------------------------------------


def _make_admin_registry() -> tuple[AgentRegistry, object, str]:
    admin_priv = generate_keypair()
    admin_did = create_did_key(admin_priv.public_key())
    reg = AgentRegistry(
        admin_public_keys={admin_did: _pubkey_b64(admin_priv)},
        admin_calls_allowed=True,
    )
    return reg, admin_priv, admin_did


def _admin_attest(reg: AgentRegistry, admin_priv, admin_did: str, agent_did: str) -> None:
    chain = reg.engine.chains[agent_did]
    sig = _sign_bytes(admin_priv, chain.events[-1].hash.encode("utf-8"))
    reg.validate_agent(agent_did, admin_did, admin=True, signature=sig)


def _active_pair() -> tuple[AgentRegistry, str, str]:
    """A admin-attested; B validated by A; C validated by B (C is ACTIVE)."""
    reg, admin_priv, admin_did = _make_admin_registry()
    _, did_a, _ = _register(reg, "a", priv=generate_keypair())
    _admin_attest(reg, admin_priv, admin_did, did_a)
    _, did_b, _ = _register(reg, "b", priv=generate_keypair())
    reg.validate_agent(did_b, did_a)  # dev N_min=1
    _, did_c, _ = _register(reg, "c", priv=generate_keypair())
    reg.validate_agent(did_c, did_b)
    assert reg.agent_status(did_c) == AgentStatus.ACTIVE
    return reg, did_a, did_c


@pytest.fixture()
def registry() -> AgentRegistry:
    return AgentRegistry()


class TestRegistration:
    def test_register_creates_did_key_chain(self, registry: AgentRegistry) -> None:
        """ID-01: genesis AGENT_REGISTER, actor == did, integrity holds."""
        priv = generate_keypair()
        did = create_did_key(priv.public_key())
        profile = AgentProfile(did=did, role=AgentRole.DISCOVERER, name="alice")
        chain = registry.register_agent(profile)
        assert chain.events[0].event_type == EventType.AGENT_REGISTER
        assert chain.events[0].actor == did
        assert chain.verify_integrity() is True
        assert did.startswith("did:key:")
        assert chain_kind(chain) == "agent"

    def test_register_without_did_derives_from_public_key(self, registry: AgentRegistry) -> None:
        """DID derivation when only the public key is supplied."""
        priv = generate_keypair()
        profile = AgentProfile(did="", role=AgentRole.REVIEWER, name="bob")
        chain = registry.register_agent(profile, public_key=priv.public_key())
        assert profile.did == create_did_key(priv.public_key())
        assert chain.concept_id == profile.did

    def test_duplicate_did_rejected(self, registry: AgentRegistry) -> None:
        """ID-09: same DID cannot re-register (Sybil, key dimension)."""
        priv = generate_keypair()
        did = create_did_key(priv.public_key())
        registry.register_agent(AgentProfile(did=did, role=AgentRole.DISCOVERER, name="a"))
        with pytest.raises(ADLConsensusError, match="already registered"):
            registry.register_agent(AgentProfile(did=did, role=AgentRole.REVIEWER, name="a2"))


class TestSigning:
    def test_genesis_signature_and_proof(self, registry: AgentRegistry) -> None:
        """ID-02: caller-attached signature/proof verify."""
        priv = generate_keypair()
        did = create_did_key(priv.public_key())
        profile = AgentProfile(did=did, role=AgentRole.DISCOVERER, name="signed")
        chain = registry.register_agent(profile)
        genesis = chain.events[0]
        genesis.signature = _sign_bytes(priv, genesis.hash.encode("utf-8"))
        genesis.proof = create_event_proof(genesis, priv, verification_method=did)
        assert genesis.signature != ""
        assert verify_event_proof(genesis) is True

    def test_state_roundtrip_preserves_signature(
        self, registry: AgentRegistry, tmp_path: Path
    ) -> None:
        """ID-11: signature/proof survive _save_engine/_load_engine."""
        priv = generate_keypair()
        did = create_did_key(priv.public_key())
        profile = AgentProfile(did=did, role=AgentRole.DISCOVERER, name="roundtrip")
        chain = registry.register_agent(profile)
        genesis = chain.events[0]
        genesis.signature = _sign_bytes(priv, genesis.hash.encode("utf-8"))
        genesis.proof = create_event_proof(genesis, priv, verification_method=did)

        state_path = tmp_path / "state.json"
        _save_engine(registry.engine, state_path)
        engine2 = _load_engine(state_path)
        ev = engine2.chains[did].events[0]
        assert ev.signature == genesis.signature
        assert ev.proof == genesis.proof
        assert ev.previous_event_id == genesis.previous_event_id


class TestValidationNMin:
    def test_dev_single_validator_activates(self) -> None:
        """ID-03: dev N_min=1 — one ACTIVE validator activates the next agent."""
        reg, admin_priv, admin_did = _make_admin_registry()
        _, did_a, _ = _register(reg, "a", priv=generate_keypair())
        _admin_attest(reg, admin_priv, admin_did, did_a)  # external root of trust
        _, did_b, _ = _register(reg, "b", priv=generate_keypair())
        reg.validate_agent(did_b, did_a)
        assert reg.agent_status(did_b) == AgentStatus.ACTIVE

    def test_prod_requires_two_validators(self) -> None:
        """ID-04: in production a single validator can never activate an agent.

        Mirrors ConsensusEngine._effective_n_min semantics: rejected VALIDATE
        transitions never append events, so with N_min=2 the first validator
        always fails (existing stays empty). An agent reaches ACTIVE in
        production only via admin attestation (P0-1) or a validator history
        accumulated in dev mode before the switch.
        """
        reg, admin_priv, admin_did = _make_admin_registry()
        _, did_a1, _ = _register(reg, "a1", priv=generate_keypair())
        _admin_attest(reg, admin_priv, admin_did, did_a1)
        _, did_a2, _ = _register(reg, "a2", priv=generate_keypair())
        _admin_attest(reg, admin_priv, admin_did, did_a2)
        _, did_d, _ = _register(reg, "d", priv=generate_keypair())
        reg.engine.set_production_mode()
        with pytest.raises(ADLConsensusError, match="distinct validators"):
            reg.validate_agent(did_d, did_a1)
        with pytest.raises(ADLConsensusError, match="distinct validators"):
            reg.validate_agent(did_d, did_a2)  # existing still empty -> rejected
        assert reg.agent_status(did_d) == AgentStatus.PENDING

        # Validator history accumulated in dev mode survives the prod switch.
        reg2, admin2_priv, admin2_did = _make_admin_registry()
        _, b1, _ = _register(reg2, "b1", priv=generate_keypair())
        _admin_attest(reg2, admin2_priv, admin2_did, b1)
        _, b2, _ = _register(reg2, "b2", priv=generate_keypair())
        _admin_attest(reg2, admin2_priv, admin2_did, b2)
        _, e, _ = _register(reg2, "e", priv=generate_keypair())
        reg2.validate_agent(e, b1)  # dev: 1st validator OK
        reg2.validate_agent(e, b2)  # dev: 2nd validator OK
        reg2.engine.set_production_mode()
        assert reg2.agent_status(e) == AgentStatus.ACTIVE

    def test_self_validation_rejected(self, registry: AgentRegistry) -> None:
        """ID-05: validator == agent itself is forbidden (B3 analog)."""
        _, did_a, _ = _register(registry, "a", priv=generate_keypair())
        with pytest.raises(ADLConsensusError, match="self-validation"):
            registry.validate_agent(did_a, did_a)

    def test_unregistered_validator_rejected(self, registry: AgentRegistry) -> None:
        """ID-06: validator must be a registered ACTIVE agent."""
        _, did_a, _ = _register(registry, "a", priv=generate_keypair())
        with pytest.raises(ADLConsensusError, match="ACTIVE agent"):
            registry.validate_agent(did_a, "did:key:znonexistentvalidator")


class TestAdminBootstrap:
    def test_admin_attestation_skips_nmin(self) -> None:
        """ID-07: valid admin signature bypasses N_min and yields ACTIVE."""
        reg, admin_priv, admin_did = _make_admin_registry()
        reg.engine.set_production_mode()
        _, did_x, _ = _register(reg, "x", priv=generate_keypair())
        _admin_attest(reg, admin_priv, admin_did, did_x)
        assert reg.agent_status(did_x) == AgentStatus.ACTIVE

    def test_admin_forgery_rejected(self) -> None:
        """ID-08/P0-1: bad signature or unknown admin DID -> rejected."""
        reg, admin_priv, admin_did = _make_admin_registry()
        _, did_x, _ = _register(reg, "x", priv=generate_keypair())
        chain = reg.engine.chains[did_x]
        other_priv = generate_keypair()
        bad_sig = _sign_bytes(other_priv, chain.events[-1].hash.encode("utf-8"))
        with pytest.raises(ADLConsensusError, match="signature verification failed"):
            reg.validate_agent(did_x, admin_did, admin=True, signature=bad_sig)
        with pytest.raises(ADLConsensusError, match="signature verification failed"):
            reg.validate_agent(did_x, "did:key:z6MkunknownAdmin", admin=True, signature=bad_sig)

    def test_admin_requires_internal_guard(self) -> None:
        """P0-3: admin=True without _admin_calls_allowed is rejected."""
        admin_priv = generate_keypair()
        admin_did = create_did_key(admin_priv.public_key())
        reg = AgentRegistry(admin_public_keys={admin_did: _pubkey_b64(admin_priv)})
        _, did_x, _ = _register(reg, "x", priv=generate_keypair())
        sig = _sign_bytes(admin_priv, reg.engine.chains[did_x].events[-1].hash.encode("utf-8"))
        with pytest.raises(ADLConsensusError, match="admin-gated API"):
            reg.validate_agent(did_x, admin_did, admin=True, signature=sig)


class TestDerivedQueriesAndLifecycle:
    def test_profile_roundtrip(self, registry: AgentRegistry) -> None:
        """ID-10: profile derives from the chain."""
        profile, did, _ = _register(registry, "p1", priv=generate_keypair())
        got = registry.get_agent(did)
        assert got is not None
        assert got.name == profile.name
        assert got.capabilities == profile.capabilities
        assert got.role == profile.role

    def test_deprecate_status(self) -> None:
        """ID-12: DEPRECATED dominates ACTIVE."""
        reg, did_a, _ = _active_pair()
        _, did_b, _ = _register(reg, "b2", priv=generate_keypair())
        reg.validate_agent(did_b, did_a)
        assert reg.agent_status(did_b) == AgentStatus.ACTIVE
        reg.deprecate_agent(did_b, did_b, "retired")
        assert reg.agent_status(did_b) == AgentStatus.DEPRECATED

    def test_update_agent_owner_only(self, registry: AgentRegistry) -> None:
        """update_agent requires owner (or registered admin)."""
        _, did_a, _ = _register(registry, "a", priv=generate_keypair())
        _, did_b, _ = _register(registry, "b", priv=generate_keypair())
        with pytest.raises(ADLConsensusError, match="owning agent"):
            registry.update_agent(did_a, did_b, model="gpt-5")
        ev = registry.update_agent(did_a, did_a, model="gpt-5")
        assert ev.event_type == EventType.AGENT_UPDATE

    def test_list_agents_filters_scope(self, registry: AgentRegistry) -> None:
        _register(registry, "pub1", priv=generate_keypair())
        priv = generate_keypair()
        did = create_did_key(priv.public_key())
        registry.register_agent(
            AgentProfile(did=did, role=AgentRole.LIBRARIAN, name="priv1", scope="private/acme")
        )
        public_only = registry.list_agents(scope="public")
        assert all(a.scope == "public" for a in public_only)
        assert len(registry.list_agents()) == 2
