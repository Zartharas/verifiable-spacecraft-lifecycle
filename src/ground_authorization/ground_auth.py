"""
Ground authorization stage — simulated mission-ops approval function.

Phase 1 scope: minimal policy — approve any release that carries a valid
signature (S0). Richer policy (SBOM/provenance-aware checks, prohibited
configuration detection for test case #8) is added in later phases as
mechanisms activate (see Threat-Model.md attack matrix and
Implementation-Plan.md Phase 4).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_store import EvidenceStore  # noqa: E402
from signing.signing import verify as signature_verify  # noqa: E402


def authorize(
    binary_path: Path, sig_path: Path, condition_name: str = "S0"
) -> bool:
    """
    Ground-side authorization decision. At S0, this simply re-checks the
    signature is valid before releasing for uplink — later conditions add
    SBOM/provenance/policy checks on top of this same decision point.
    """
    store = EvidenceStore()
    import hashlib

    with open(binary_path, "rb") as f:
        artifact_hash = hashlib.sha256(f.read()).hexdigest()

    valid_signature = signature_verify(
        binary_path,
        sig_path,
        condition_name=condition_name,
        actor="ground_authorization_service",
    )

    approved = valid_signature  # Phase 1: signature validity is the only gate

    store.record(
        pipeline_stage="ground_authorization",
        condition=condition_name,
        artifact_ref=artifact_hash,
        actor="ground_authorization_service",
        result="pass" if approved else "fail",
        detail={"decision": "approve" if approved else "deny"},
    )
    return approved
