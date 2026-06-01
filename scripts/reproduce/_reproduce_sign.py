"""Reproduce LD-Proof signing: generate keypair, sign event, verify."""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from adl_lite.ld_proof import generate_keypair, sign_event, verify_event_signature  # noqa: E402
from adl_lite.models import Event, EventType  # noqa: E402


def main():
    sk = generate_keypair()
    pk = sk.public_key()

    event = Event(
        concept_id="artifact-demo",
        event_type=EventType.REGISTER,
        actor="demo_agent",
        timestamp="2024-06-01T00:00:00+00:00",
        payload={"domain": "test"},
    )

    signed = sign_event(event, sk)
    valid = verify_event_signature(signed, pk)

    pk_bytes = base64.b64encode(pk.public_bytes_raw()).decode("ascii")
    artifact = {
        "public_key": pk_bytes,
        "signed_event": signed,
        "verification": "PASS" if valid else "FAIL",
    }

    artifacts_dir = PROJECT_ROOT / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    with open(artifacts_dir / "signature_artifact.json", "w") as f:
        json.dump(artifact, f, indent=2)

    print(f"  Public key: {pk_bytes[:32]}...")
    print(f"  Signature type: {signed['proof']['type']}")
    print(f"  Verification: {'PASS' if valid else 'FAIL'}")
    print("\nLD-Proof Signing: 1/1 verified")
    print("OVERALL: PASS" if valid else "OVERALL: FAIL")
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
