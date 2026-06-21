"""
Tests for hardened GitSignatureVerifier.
"""

import os
import struct
import subprocess
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from adl_lite.key_registry import GitSignatureVerifier, KeyRegistry
from adl_lite.models import Event, EventChain, EventType


def _mock_run(stdout="", returncode=0):
    def run(cmd, **kwargs):
        m = MagicMock()
        m.stdout = stdout
        m.returncode = returncode
        m.stderr = ""
        return m
    return run


@pytest.fixture
def registry(tmp_path):
    r = KeyRegistry(str(tmp_path / "registry.yaml"))
    pk = ed25519.Ed25519PrivateKey.generate().public_key()
    r.register("alice", pk)
    return r


def test_verify_event_not_found(registry, tmp_path):
    v = GitSignatureVerifier(registry)
    event = Event(concept_id="c", event_type=EventType.REGISTER, actor="alice")
    with patch("subprocess.run", side_effect=_mock_run(returncode=128)):
        assert v.verify_event(event, str(tmp_path)) is False


def test_verify_event_no_key(registry, tmp_path):
    v = GitSignatureVerifier(registry)
    event = Event(concept_id="c", event_type=EventType.REGISTER, actor="bob")
    assert v.verify_event(event, str(tmp_path)) is False


def test_verify_event_revoked(registry, tmp_path):
    v = GitSignatureVerifier(registry)
    registry.revoke("alice")
    event = Event(concept_id="c", event_type=EventType.REGISTER, actor="alice")
    with patch("subprocess.run", side_effect=_mock_run(stdout="abc123", returncode=0)):
        assert v.verify_event(event, str(tmp_path)) is False


def test_verify_event_success(registry, tmp_path):
    v = GitSignatureVerifier(registry)
    event = Event(concept_id="c", event_type=EventType.REGISTER, actor="alice")

    def run(cmd, **kwargs):
        m = MagicMock()
        m.stdout = ""
        m.returncode = 0
        if "log" in cmd and "--reverse" in cmd:
            m.stdout = "abc123\n"
        return m

    with patch("subprocess.run", side_effect=run):
        assert v.verify_event(event, str(tmp_path)) is True


def test_verify_all_events_in_chain(registry, tmp_path):
    v = GitSignatureVerifier(registry)
    chain = EventChain(concept_id="c")
    chain.append(Event(concept_id="c", event_type=EventType.REGISTER, actor="alice"))
    chain.append(Event(concept_id="c", event_type=EventType.VALIDATE, actor="alice"))

    def run(cmd, **kwargs):
        m = MagicMock()
        m.stdout = "abc123\n"
        m.returncode = 0
        return m

    with patch("subprocess.run", side_effect=run):
        results = v.verify_all_events_in_chain(chain)
    assert len(results) == 2
    assert all(r[1] for r in results)
    assert results[0][0].event_type == EventType.REGISTER
