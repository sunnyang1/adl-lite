"""
ADL Lite — Replay harness (EAL Phase 2).

Independently re-executes a capability from its ``adl:execution`` spec and
compares the resulting output commitment against an EXECUTE receipt or a
declared test vector, producing the evidence for an ATTEST verdict.

Security model (explicit, matching the project's no-``eval`` rule):
- Commands are executed with ``shell=False`` after ``shlex.split``; shell
  features (pipes, redirects, globs) are intentionally unsupported.
- The harness NEVER runs implicitly: it executes only when a validator
  explicitly invokes it (CLI ``adl-lite attest replay`` or direct API call).
  Validators run untrusted capability code in their own environment — that is
  the point of the replay role; sandboxing beyond timeouts is the operator's
  responsibility (containers, VMs).
- No dynamic evaluation of property strings in Phase 2: deterministic
  capabilities get exact-commitment comparison; ``stochastic`` and
  ``side-effecting`` capabilities receive ``inconclusive`` verdicts pending
  the statistical/property engines (Phase 3).
"""

from __future__ import annotations

import hashlib
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .logging_config import get_logger
from .models import ADLExecutionBlock, ADLExecutionTestVector, Event, EventChain, EventType

logger = get_logger(__name__)

COMMITMENT_PREFIX = "sha256:"


def sha256_commitment(data: bytes) -> str:
    """Commitment format used across EAL payloads: ``sha256:<hex>``."""
    return COMMITMENT_PREFIX + hashlib.sha256(data).hexdigest()


def file_commitment(path: str | Path) -> str:
    return sha256_commitment(Path(path).read_bytes())


@dataclass
class ReplayOutcome:
    """Result of one replay attempt, mapped to an ATTEST verdict."""

    verdict: str  # "confirm" | "refute" | "inconclusive"
    reason: str = ""
    replay: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0


class ReplayHarness:
    """Re-executes a capability per its ``adl:execution`` spec."""

    def __init__(self, spec: ADLExecutionBlock) -> None:
        self.spec = spec

    # ------------------------------------------------------------------
    # Command execution
    # ------------------------------------------------------------------

    def run(self, input_file: str | Path) -> tuple[bytes, int]:
        """Run the invocation command against ``input_file``.

        Returns ``(stdout_bytes, duration_ms)``. Raises on non-zero exit or
        unsupported invocation type; the caller maps exceptions to verdicts.
        """
        invocation = self.spec.invocation
        if invocation.type not in ("cli", "python"):
            raise NotImplementedError(
                f"invocation type {invocation.type!r} is not supported by the Phase 2 harness"
            )
        template = invocation.command
        if not template.strip():
            raise ValueError("execution spec has an empty invocation.command")
        command = template.replace("{input_file}", str(input_file))
        argv = shlex.split(command)

        start = time.monotonic()
        proc = subprocess.run(  # noqa: S603 — shell=False, argv from shlex
            argv,
            capture_output=True,
            timeout=invocation.timeout_ms / 1000,
            check=False,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="replace")[:400]
            raise RuntimeError(f"replay command exited {proc.returncode}: {stderr}")
        return proc.stdout, duration_ms

    # ------------------------------------------------------------------
    # Verdict logic
    # ------------------------------------------------------------------

    def _determinism_gate(self) -> str | None:
        """Return an inconclusive reason when the capability is not replayable exactly."""
        if self.spec.determinism == "stochastic":
            return "stochastic capability: exact replay inconclusive (statistical conformance is Phase 3)"
        if self.spec.determinism == "side-effecting":
            return "side-effecting capability: property-check required (Phase 3), replay skipped"
        return None

    def replay_against_commitments(
        self,
        *,
        input_commitment: str,
        expected_output_commitment: str,
        input_file: str | Path,
    ) -> ReplayOutcome:
        """Replay and compare against committed input/output (receipt or test vector)."""
        gate = self._determinism_gate()
        if gate is not None:
            return ReplayOutcome(verdict="inconclusive", reason=gate)

        input_file = Path(input_file)
        actual_input = file_commitment(input_file)
        if actual_input != input_commitment:
            return ReplayOutcome(
                verdict="inconclusive",
                reason=(
                    "input file does not match the receipt's input_commitment "
                    f"({actual_input[:20]}… != {input_commitment[:20]}…); cannot replay"
                ),
            )

        try:
            output, duration_ms = self.run(input_file)
        except subprocess.TimeoutExpired:
            return ReplayOutcome(
                verdict="inconclusive",
                reason=f"replay exceeded timeout ({self.spec.invocation.timeout_ms} ms)",
            )
        except (RuntimeError, ValueError, NotImplementedError, OSError) as exc:
            return ReplayOutcome(verdict="inconclusive", reason=f"replay failed: {exc}")

        actual_output = sha256_commitment(output)
        match = actual_output == expected_output_commitment
        return ReplayOutcome(
            verdict="confirm" if match else "refute",
            reason="output commitment matches" if match else "output commitment MISMATCH",
            replay={
                "input_commitment": input_commitment,
                "output_commitment": actual_output,
                "expected_output_commitment": expected_output_commitment,
                "match": match,
                "tolerance": "exact",
            },
            duration_ms=duration_ms,
        )

    def replay_receipt(self, receipt: Event, input_file: str | Path) -> ReplayOutcome:
        """Replay against an EXECUTE receipt's commitments."""
        return self.replay_against_commitments(
            input_commitment=receipt.payload.get("input_commitment", ""),
            expected_output_commitment=receipt.payload.get("output_commitment", ""),
            input_file=input_file,
        )

    def replay_test_vector(
        self, vector: ADLExecutionTestVector, input_file: str | Path
    ) -> ReplayOutcome:
        """Replay against a declared spec test vector."""
        return self.replay_against_commitments(
            input_commitment=vector.input_commitment,
            expected_output_commitment=vector.expected_output_commitment,
            input_file=input_file,
        )


# ---------------------------------------------------------------------------
# ATTEST event construction
# ---------------------------------------------------------------------------


def build_attest_event(
    *,
    capability_id: str,
    subject_receipt: Event,
    outcome: ReplayOutcome,
    actor: str,
    scope: str | None = None,
    evidence_ref: str | None = None,
    reasoning: str = "",
) -> Event:
    """Build an unsigned ATTEST event from a replay outcome.

    The event is unsigned because the proof must cover the final chaining
    fields (``previous_event_id`` / ``prev_hash``); use
    :func:`append_attestation` to append + sign atomically.
    """
    payload: dict[str, Any] = {
        "subject_execution": subject_receipt.payload.get("execution_id"),
        "subject_log_root": None,
        "method": "replay",
        "verdict": outcome.verdict,
        "replay": outcome.replay or None,
        "evidence_ref": evidence_ref,
        "reason": outcome.reason,
    }
    if scope:
        payload["scope"] = scope
    return Event(
        concept_id=capability_id,
        event_type=EventType.ATTEST,
        actor=actor,
        reasoning=reasoning or outcome.reason,
        payload=payload,
    )


def append_attestation(
    chain: EventChain,
    event: Event,
    *,
    private_key: Any = None,
    verification_method: str | None = None,
) -> Event:
    """Append an ATTEST event to a governance chain, then sign it in place.

    Signing happens AFTER append because the LD-Proof canonicalization covers
    the chaining fields (``previous_event_id``, ``prev_hash``), which are only
    finalized by ``EventChain.append``. Axiom 14 requires the proof, so
    attesting without a key produces a chain that fails verification.
    """
    chain.append(event)
    if private_key is not None:
        from .ld_proof import create_event_proof

        event.proof = create_event_proof(
            event, private_key, verification_method=verification_method
        )
    else:
        logger.warning("ATTEST event appended unsigned; axiom 14 will fail verification")
    return event
