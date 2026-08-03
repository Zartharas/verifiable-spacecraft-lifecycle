"""
Ground authorization stage — simulated mission-ops approval function.

Phase 1 (S0): approve any release that carries a valid signature.
Phase 2 (S1/S2) adds, condition-gated via condition.py:
  - S1: SBOM must be present, complete (test case #3), and free of known
    test vulnerabilities (test case #4).
  - S2: provenance must be present and valid — binary matches source
    record (test case #1), provenance itself is present/well-formed
    (test case #2), builder is authorized (test case #5) — plus a
    downgrade check against the version ledger (test case #9).

Phase 4 (S5) adds: prohibited-configuration policy check (test case #8),
condition-gated the same way.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_store import EvidenceStore  # noqa: E402
from signing.signing import verify as signature_verify  # noqa: E402
from sbom.sbom import verify_sbom  # noqa: E402
from provenance.provenance import verify_provenance  # noqa: E402
from ground_authorization import version_ledger  # noqa: E402
from policy.policy import check_configuration  # noqa: E402
from condition import preset  # noqa: E402


def authorize(
    binary_path: Path,
    sig_path: Path,
    condition_name: str = "S0",
    sbom_path: Optional[Path] = None,
    prov_path: Optional[Path] = None,
    version: int = 1,
    configuration: Optional[dict] = None,
    stack: str = "cfs",
) -> bool:
    store = EvidenceStore()
    cond = preset(condition_name)

    with open(binary_path, "rb") as f:
        artifact_hash = hashlib.sha256(f.read()).hexdigest()

    checks_passed = True
    denial_reasons = []

    valid_signature = signature_verify(
        binary_path,
        sig_path,
        condition_name=condition_name,
        actor="ground_authorization_service",
    )
    if not valid_signature:
        checks_passed = False
        denial_reasons.append("invalid or revoked signature")

    if checks_passed and cond.active("sbom"):
        if sbom_path is None:
            checks_passed = False
            denial_reasons.append("SBOM required by condition but not provided")
        elif not verify_sbom(sbom_path, condition_name=condition_name):
            checks_passed = False
            denial_reasons.append("SBOM verification failed")

    if checks_passed and cond.active("provenance"):
        if prov_path is None:
            checks_passed = False
            denial_reasons.append("provenance required by condition but not provided")
        else:
            valid_prov, reason, _ = verify_provenance(
                binary_path, prov_path, condition_name=condition_name
            )
            if not valid_prov:
                checks_passed = False
                denial_reasons.append(f"provenance verification failed: {reason}")

        if checks_passed and not version_ledger.check_and_advance(
            version, artifact_hash, condition_name=condition_name, stack=stack
        ):
            checks_passed = False
            denial_reasons.append("downgrade attempt")

    if checks_passed and cond.active("machine_readable_authorization"):
        config_ok, reason = check_configuration(
            configuration or {}, artifact_hash, condition_name=condition_name
        )
        if not config_ok:
            checks_passed = False
            denial_reasons.append(reason)

    store.record(
        pipeline_stage="ground_authorization",
        condition=condition_name,
        artifact_ref=artifact_hash,
        actor="ground_authorization_service",
        result="pass" if checks_passed else "fail",
        detail={
            "decision": "approve" if checks_passed else "deny",
            "reasons": denial_reasons,
        },
    )
    return checks_passed
