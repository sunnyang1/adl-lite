"""
Ed25519 Key Registry for ADL Lite — Phase 1.5 survival path.

Maps actor strings to Ed25519 public keys in a local YAML file.
Provides Git signature soft-checks and deterministic transparency anchors.

Constraints (survival path):
    - No sigstore.dev, no Ethereum, no external transparency logs.
    - Git + local YAML only.
"""

from __future__ import annotations

import base64
import hashlib
import os
import struct
import subprocess
import tempfile
import warnings
from datetime import datetime, timezone
from pathlib import Path

import yaml
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

from .did_resolver import is_did, resolve_did_key, verify_did_signature
from .models import Event, EventChain


class KeyRegistry:
    """YAML-based actor → Ed25519 public key registry."""

    def __init__(self, registry_path: str = ".adl/keys/registry.yaml") -> None:
        self.path = Path(registry_path)
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            self._data = yaml.safe_load(self.path.read_text()) or {}
        else:
            self._data = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(yaml.safe_dump(self._data, sort_keys=True), encoding="utf-8")

    def register(self, actor: str, public_key: ed25519.Ed25519PublicKey) -> None:
        pk_bytes = public_key.public_bytes_raw()
        self._data[actor] = {"public_key": base64.b64encode(pk_bytes).decode("ascii")}
        self._save()

    def get_public_key(self, actor: str) -> ed25519.Ed25519PublicKey | None:
        """Return public key for actor or DID. For DID, resolve locally."""
        if is_did(actor):
            return resolve_did_key(actor)
        entry = self._data.get(actor)
        if not entry or entry.get("revoked"):
            return None
        try:
            pk_bytes = base64.b64decode(entry["public_key"])
            return ed25519.Ed25519PublicKey.from_public_bytes(pk_bytes)
        except Exception:
            return None

    def verify_signature(self, actor: str, message: bytes, signature: bytes) -> bool:
        """Verify signature for actor or DID."""
        if is_did(actor):
            return verify_did_signature(actor, message, signature)
        pk = self.get_public_key(actor)
        if pk is None:
            return False
        try:
            pk.verify(signature, message)
            return True
        except InvalidSignature:
            return False

    def revoke(self, actor: str) -> None:
        if actor not in self._data:
            raise KeyError(f"actor '{actor}' not registered")
        self._data[actor]["revoked"] = True
        self._save()

    def is_revoked(self, actor: str) -> bool:
        return bool(self._data.get(actor, {}).get("revoked"))

    def list_actors(self) -> list[str]:
        return sorted(self._data.keys())


class GitSignatureVerifier:
    """Soft verification that Git commits are signed by a registered actor key."""

    def __init__(self, registry: KeyRegistry) -> None:
        self.registry = registry

    def verify_commit_signature(self, actor: str, commit_hash: str) -> bool:
        try:
            result = subprocess.run(
                ["git", "verify-commit", commit_hash],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return False
            pk = self.registry.get_public_key(actor)
            if pk is None:
                return False
            return True
        except Exception as exc:
            warnings.warn(f"Git signature soft-check failed: {exc}")
            return False

    def verify_all_events_in_chain(self, chain: EventChain) -> list[tuple[Event, bool]]:
        return [(e, self.verify_event(e)) for e in chain.events]

    def verify_event(self, event: Event, repo_path: str = ".") -> bool:
        commit = self._find_commit(event, repo_path)
        if not commit:
            warnings.warn(f"Event {event.event_id} not found in Git history")
            return False
        return self._verify_commit(commit, event.actor, repo_path)

    def _find_commit(self, event: Event, repo_path: str) -> str | None:
        for needle in (event.hash, event.event_id):
            try:
                r = subprocess.run(
                    ["git", "-C", repo_path, "log", "--all", "--reverse", "--format=%H", "-S", needle],
                    capture_output=True, text=True, check=True,
                )
                lines = [l for l in r.stdout.strip().split("\n") if l]
                if lines:
                    return lines[0]
            except Exception:
                pass
        return None

    def _verify_commit(self, commit: str, actor: str, repo_path: str) -> bool:
        pk = self.registry.get_public_key(actor)
        if pk is None:
            return False
        if subprocess.run(
            ["git", "-C", repo_path, "verify-commit", commit],
            capture_output=True, text=True,
        ).returncode != 0:
            return False
        pk_bytes = pk.public_bytes_raw()
        wire = struct.pack(">I", 11) + b"ssh-ed25519" + struct.pack(">I", len(pk_bytes)) + pk_bytes
        key = f"ssh-ed25519 {base64.b64encode(wire).decode()}"
        fd, path = tempfile.mkstemp(suffix=".signers")
        try:
            os.write(fd, f"{actor} * {key}\n".encode())
            os.close(fd)
            return subprocess.run(
                ["git", "-C", repo_path, "-c", f"gpg.ssh.allowedSignersFile={path}",
                 "verify-commit", commit],
                capture_output=True, text=True,
            ).returncode == 0
        except Exception:
            return False
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass


class TransparencyAnchor:
    """Deterministic anchor over EventChain hashes, written to ANCHOR.md."""

    def __init__(self, anchor_path: str = "ANCHOR.md") -> None:
        self.anchor_path = Path(anchor_path)
        self._last_chains: list[EventChain] = []

    def _compute_anchor(self, chains: list[EventChain]) -> str:
        hashes = [
            hashlib.sha256("".join(e.hash for e in c.events).encode("utf-8")).hexdigest()
            for c in sorted(chains, key=lambda x: x.concept_id)
        ]
        return hashlib.sha256("".join(hashes).encode("utf-8")).hexdigest()

    def anchor(self, chains: list[EventChain]) -> str:
        self._last_chains = chains
        value = self._compute_anchor(chains)
        self.anchor_path.write_text(
            f"# ADL Transparency Anchor\n\n`{value}`\n", encoding="utf-8"
        )
        return value

    def verify_anchor(self) -> bool:
        if not self.anchor_path.exists():
            return False
        content = self.anchor_path.read_text(encoding="utf-8")
        expected = self._compute_anchor(self._last_chains)
        return f"`{expected}`" in content

    def verify_anchor_at_commit(self, commit_hash: str) -> bool:
        try:
            r = subprocess.run(
                ["git", "show", f"{commit_hash}:{self.anchor_path}"],
                capture_output=True, text=True,
            )
            return r.returncode == 0 and f"`{self._compute_anchor(self._last_chains)}`" in r.stdout
        except Exception:
            return False

    def anchor_history(self) -> list[dict[str, str]]:
        try:
            r = subprocess.run(
                ["git", "log", "--follow", "--format=%H:%at", "--", str(self.anchor_path)],
                capture_output=True, text=True, check=True,
            )
            history: list[dict[str, str]] = []
            for line in r.stdout.strip().split("\n"):
                if not line:
                    continue
                h, ts = line.split(":", 1)
                try:
                    content = subprocess.run(
                        ["git", "show", f"{h}:{self.anchor_path}"],
                        capture_output=True, text=True, check=True,
                    ).stdout
                    start = content.find("`")
                    end = content.find("`", start + 1) if start != -1 else -1
                    if start != -1 and end != -1:
                        val = content[start + 1:end]
                        if len(val) == 64:
                            history.append({
                                "commit": h,
                                "timestamp": datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat(),
                                "anchor": val,
                            })
                except Exception:
                    pass
            return history
        except Exception:
            return []
