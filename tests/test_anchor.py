"""
Tests for hardened TransparencyAnchor.
"""

from unittest.mock import MagicMock, patch

import pytest

from adl_lite.key_registry import TransparencyAnchor
from adl_lite.models import Event, EventChain, EventType


def test_anchor_idempotent():
    chain = EventChain(concept_id="b")
    chain.append(Event(concept_id="b", event_type=EventType.REGISTER))
    chain2 = EventChain(concept_id="a")
    chain2.append(Event(concept_id="a", event_type=EventType.REGISTER))
    a = TransparencyAnchor()
    h1 = a.anchor([chain, chain2])
    h2 = a.anchor([chain2, chain])
    assert h1 == h2


def test_verify_anchor():
    chain = EventChain(concept_id="c")
    chain.append(Event(concept_id="c", event_type=EventType.REGISTER))
    a = TransparencyAnchor()
    a.anchor([chain])
    assert a.verify_anchor() is True


def test_verify_anchor_at_commit():
    chain = EventChain(concept_id="c")
    chain.append(Event(concept_id="c", event_type=EventType.REGISTER))
    a = TransparencyAnchor()
    a.anchor([chain])
    with patch("subprocess.run") as m:
        m.return_value = MagicMock(
            stdout=f"`{a._compute_anchor([chain])}`\n", returncode=0
        )
        assert a.verify_anchor_at_commit("deadbeef") is True


def test_anchor_history():
    chain = EventChain(concept_id="c")
    chain.append(Event(concept_id="c", event_type=EventType.REGISTER))
    a = TransparencyAnchor()
    a.anchor([chain])

    call_count = 0

    def run(cmd, **kwargs):
        nonlocal call_count
        call_count += 1
        r = MagicMock()
        r.returncode = 0
        if call_count == 1:
            r.stdout = "deadbeef:1234567890\n"
        else:
            r.stdout = f"`{a._compute_anchor([chain])}`\n"
        return r

    with patch("subprocess.run", side_effect=run):
        hist = a.anchor_history()
    assert len(hist) == 1
    assert hist[0]["commit"] == "deadbeef"
    assert hist[0]["anchor"] == a._compute_anchor([chain])
