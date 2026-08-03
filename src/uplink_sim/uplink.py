"""
Simulated uplink — Phase 1 scope: pass-through transport with a tamper
injection hook for attack matrix test case #6 (modified update in transit).

Latency/loss/bandwidth-ceiling modeling (CCSDS-informed) is Phase 2 work
per Implementation-Plan.md. This is deliberately a simple, honest
placeholder — see PRD.md non-goals and Pipeline-Flow-Document.md § 3.7:
this is NOT an RF-accurate simulation.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_store import EvidenceStore  # noqa: E402

RECEIVED_DIR = REPO_ROOT / "work" / "spacecraft_received"


def transmit(
    binary_path: Path,
    sig_path: Path,
    condition_name: str = "S0",
    tamper: bool = False,
) -> tuple[Path, Path]:
    """
    Simulate transmission of a signed release bundle over the uplink.

    If tamper=True, flips a byte in the transmitted binary to simulate
    test case #6 (modified update in transit) — the signature file is
    transmitted unmodified, so onboard verification should reject the
    mismatch.
    """
    store = EvidenceStore()
    import hashlib

    RECEIVED_DIR.mkdir(parents=True, exist_ok=True)
    data = bytearray(binary_path.read_bytes())
    original_hash = hashlib.sha256(bytes(data)).hexdigest()

    if tamper:
        # Flip a bit in the middle of the binary — enough to invalidate
        # any signature computed over the original content.
        mid = len(data) // 2
        data[mid] ^= 0xFF

    received_binary = RECEIVED_DIR / binary_path.name
    received_sig = RECEIVED_DIR / sig_path.name
    received_binary.write_bytes(bytes(data))
    received_sig.write_bytes(sig_path.read_bytes())

    received_hash = hashlib.sha256(bytes(data)).hexdigest()

    store.record(
        pipeline_stage="uplink",
        condition=condition_name,
        artifact_ref=original_hash,
        actor="uplink_simulator",
        result="n/a",  # transit itself has no pass/fail — verification does
        detail={
            "tampered_in_transit": tamper,
            "hash_before_transmission": original_hash,
            "hash_after_transmission": received_hash,
        },
        test_case_injected="6" if tamper else None,
    )

    return received_binary, received_sig
