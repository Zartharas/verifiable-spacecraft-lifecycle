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
from condition import preset, custom as condition_custom  # noqa: E402


def authorize(
    binary_path: Path,
    sig_path: Path,
    condition_name: str = "S0",
    sbom_path: Optional[Path] = None,
    prov_path: Optional[Path] = None,
    version: int = 1,
    configuration: Optional[dict] = None,
    stack: str = "cfs",
    disable_mechanisms: tuple = (),
) -> bool:
    # Phase 8 (2026-08-05), reviewer objection #5 fix: this function used
    # to build its own Condition via preset(condition_name) alone, ignoring
    # any disable_mechanisms override passed to pipeline.run(). That made
    # the SBOM/provenance/S5-policy checks below structurally immune to
    # the ablation study — disabling one of those mechanisms at the
    # pipeline level never reached this function's own gating. Mirror
    # pipeline.py's own pattern so ablation actually reaches every check
    # performed here.
    store = EvidenceStore()
    cond = preset(condition_name)
    if disable_mechanisms:
        cond = condition_custom(cond, disable=disable_mechanisms)

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
        elif not verify_sbom(sbom_path, binary_path=binary_path, condition_name=condition_name):
            checks_passed = False
            denial_reasons.append("SBOM verification failed")

    if checks_passed and cond.active("provenance"):
        provenance_doc = None
        if prov_path is None:
            checks_passed = False
            denial_reasons.append("provenance required by condition but not provided")
        else:
            valid_prov, reason, provenance_doc = verify_provenance(
                binary_path, prov_path, condition_name=condition_name
            )
            if not valid_prov:
                checks_passed = False
                denial_reasons.append(f"provenance verification failed: {reason}")

        # Phase 8 red-team fix (2026-08-04), finding #3: the `version`
        # argument used for downgrade protection was never bound to the
        # provenance record it travels alongside — a caller could supply
        # an inflated version number, independent of what the artifact's
        # actual provenance declares, and poison the shared ledger,
        # permanently locking out future *legitimate* lower/correct
        # version numbers. This is the mirror image of test case #9 (a
        # low version sneaking past the ledger): here the attack inflates
        # it. Require the two to match before ever consulting the ledger.
        if checks_passed and provenance_doc is not None:
            try:
                provenance_version = provenance_doc["predicate"]["runDetails"]["metadata"]["version"]
            except (KeyError, TypeError):
                provenance_version = None
            if provenance_version != version:
                checks_passed = False
                denial_reasons.append(
                    f"version/provenance mismatch: authorization requested version "
                    f"{version}, but provenance record declares version "
                    f"{provenance_version}"
                )
                store.record(
                    pipeline_stage="ground_authorization",
                    condition=condition_name,
                    artifact_ref=artifact_hash,
                    actor="ground_authorization_service",
                    result="fail",
                    detail={
                        "reason": "version/provenance binding check failed",
                        "requested_version": version,
                        "provenance_version": provenance_version,
                    },
                )

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
