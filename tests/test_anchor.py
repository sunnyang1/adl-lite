"""
Tests for hardened TransparencyAnchor.
"""

import json
from unittest.mock import MagicMock, patch

from adl_lite.key_registry import TransparencyAnchor
from adl_lite.models import Event, EventChain, EventType


def test_anchor_idempotent(tmp_path):
    chain = EventChain(concept_id="b")
    chain.append(Event(concept_id="b", event_type=EventType.REGISTER))
    chain2 = EventChain(concept_id="a")
    chain2.append(Event(concept_id="a", event_type=EventType.REGISTER))
    # NOTE: anchor files are written to tmp_path — the default ANCHOR.md path
    # must never be used in tests (it is a tracked repo file).
    a = TransparencyAnchor(str(tmp_path / "ANCHOR.md"))
    h1 = a.anchor([chain, chain2])
    h2 = a.anchor([chain2, chain])
    assert h1 == h2


def test_verify_anchor(tmp_path):
    chain = EventChain(concept_id="c")
    chain.append(Event(concept_id="c", event_type=EventType.REGISTER))
    a = TransparencyAnchor(str(tmp_path / "ANCHOR.md"))
    a.anchor([chain])
    assert a.verify_anchor() is True


def test_verify_anchor_at_commit(tmp_path):
    chain = EventChain(concept_id="c")
    chain.append(Event(concept_id="c", event_type=EventType.REGISTER))
    a = TransparencyAnchor(str(tmp_path / "ANCHOR.md"))
    a.anchor([chain])
    with patch("subprocess.run") as m:
        m.return_value = MagicMock(stdout=f"`{a._compute_anchor([chain])}`\n", returncode=0)
        assert a.verify_anchor_at_commit("deadbeef") is True


def test_anchor_history(tmp_path):
    chain = EventChain(concept_id="c")
    chain.append(Event(concept_id="c", event_type=EventType.REGISTER))
    a = TransparencyAnchor(str(tmp_path / "ANCHOR.md"))
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


# ---------------------------------------------------------------------------
# F18: Enhanced Merkle anchor tests
# ---------------------------------------------------------------------------


def _make_chain(concept_id: str) -> EventChain:
    """Create a minimal EventChain with one REGISTER event."""
    chain = EventChain(concept_id=concept_id)
    chain.append(Event(concept_id=concept_id, event_type=EventType.REGISTER))
    return chain


def test_anchor_merkle_writes_proofs(tmp_path):
    """Anchor 3 chains with use_merkle=True + proofs_dir, verify proof files created."""
    chains = [_make_chain(cid) for cid in ("a", "b", "c")]
    proofs_dir = tmp_path / "proofs"
    anchor_path = tmp_path / "ANCHOR.md"

    a = TransparencyAnchor(anchor_path=str(anchor_path))
    a.anchor(chains, use_merkle=True, proofs_dir=proofs_dir)

    for cid in ("a", "b", "c"):
        proof_file = proofs_dir / f"{cid}.proof.json"
        assert proof_file.exists(), f"Proof file for {cid} should exist"

        # Verify proof file content is valid
        data = json.loads(proof_file.read_text())
        assert "leaf_index" in data
        assert "leaf_hash" in data
        assert "siblings" in data
        assert "root" in data


def test_anchor_merkle_anchormd_format(tmp_path):
    """Verify ANCHOR.md contains the correct Merkle format."""
    chains = [_make_chain(cid) for cid in ("x", "y")]
    proofs_dir = tmp_path / "proofs"
    anchor_path = tmp_path / "ANCHOR.md"

    a = TransparencyAnchor(anchor_path=str(anchor_path))
    a.anchor(chains, use_merkle=True, proofs_dir=proofs_dir)

    content = anchor_path.read_text()
    assert "ADL Transparency Anchor (Merkle)" in content
    assert "Root:" in content
    assert "## Chains" in content
    assert "`x`" in content
    assert "`y`" in content
    assert "proof=" in content


def test_verify_anchor_at_commit_merkle(tmp_path):
    """Mock git show returning Merkle-format ANCHOR.md, verify_anchor_at_commit works."""
    chains = [_make_chain(cid) for cid in ("a", "b")]
    a = TransparencyAnchor(str(tmp_path / "ANCHOR.md"))
    a.anchor(chains, use_merkle=True)

    merkle_root = a._last_tree.root_hex

    with patch("subprocess.run") as m:
        m.return_value = MagicMock(
            stdout=f"# ADL Transparency Anchor (Merkle)\n\nRoot: `{merkle_root}`\n",
            returncode=0,
        )
        assert a.verify_anchor_at_commit("deadbeef") is True


def test_verify_batch_end_to_end(tmp_path):
    """Anchor 3 chains → get proofs → verify_batch → all pass."""
    chains = [_make_chain(cid) for cid in ("p", "q", "r")]
    proofs_dir = tmp_path / "proofs"
    anchor_path = tmp_path / "ANCHOR.md"

    a = TransparencyAnchor(anchor_path=str(anchor_path))
    a.anchor(chains, use_merkle=True, proofs_dir=proofs_dir)

    # Load proofs from files and build proofs dict
    proofs = {}
    for cid in ("p", "q", "r"):
        proof_data = json.loads((proofs_dir / f"{cid}.proof.json").read_text())
        from adl_lite.merkle import MerkleProof

        proofs[cid] = MerkleProof(
            leaf_index=proof_data["leaf_index"],
            leaf_hash=proof_data["leaf_hash"],
            siblings=[(s[0], s[1]) for s in proof_data["siblings"]],
            root=proof_data["root"],
        )

    result = TransparencyAnchor.verify_batch(chains, a._last_tree.root_hex, proofs)
    assert result == {"p": True, "q": True, "r": True}
