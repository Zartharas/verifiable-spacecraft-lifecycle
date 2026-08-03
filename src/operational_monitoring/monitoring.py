"""
Operational monitoring — S5 assurance mechanism: reconciling ground's
beliefs against the spacecraft's actual state, and cross-checking
self-reported telemetry against what the evidence store actually shows
happened.

Covers attack matrix test cases:
  #13 — ground/spacecraft inventory disagreement
  #15 — false "successful installation" telemetry

Both checks are deliberately simple state comparisons for Phase 4 — a
real S5 implementation would tie this into signed, structured evidence
(see evidence_store/authorization_evidence.py) rather than comparing two
plain values, but the comparison *logic* being tested is the same either
way.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_store import EvidenceStore  # noqa: E402


def reconcile_inventory(
    ground_expected_version: int,
    spacecraft_confirmed_version: Optional[int],
    artifact_hash: str,
    condition_name: str = "S5",
) -> tuple[bool, Optional[str]]:
    """
    Test case #13: does ground's belief about the currently-approved
    version match what the spacecraft has actually confirmed as active?
    A natural way this diverges: a Phase 3 rollback reverts the
    spacecraft to an older version while ground's ledger has already
    advanced to the newer one it approved, and ground was never told the
    rollback happened.
    """
    store = EvidenceStore()
    agree = spacecraft_confirmed_version == ground_expected_version

    store.record(
        pipeline_stage="inventory_reconciliation",
        condition=condition_name,
        artifact_ref=artifact_hash,
        actor="ground_authorization_service",
        result="pass" if agree else "fail",
        detail={
            "ground_expected_version": ground_expected_version,
            "spacecraft_confirmed_version": spacecraft_confirmed_version,
        },
        test_case_injected=None if agree else "13",
    )
    if not agree:
        return False, (
            f"inventory disagreement: ground expects version "
            f"{ground_expected_version}, spacecraft confirms "
            f"{spacecraft_confirmed_version}"
        )
    return True, None


def check_telemetry(
    claimed_success: bool,
    actual_confirmed: bool,
    artifact_hash: str,
    condition_name: str = "S5",
) -> tuple[bool, Optional[str]]:
    """
    Test case #15: does self-reported "installation successful" telemetry
    match what the evidence store actually recorded for this run? Catches
    both deception (an attacker forging success telemetry) and honest bugs
    (a health-check false positive that never gets corrected).
    """
    store = EvidenceStore()
    consistent = claimed_success == actual_confirmed

    store.record(
        pipeline_stage="operational_monitoring",
        condition=condition_name,
        artifact_ref=artifact_hash,
        actor="ground_authorization_service",
        result="pass" if consistent else "fail",
        detail={"claimed_success": claimed_success, "actual_confirmed": actual_confirmed},
        test_case_injected=None if consistent else "15",
    )
    if not consistent:
        return False, (
            f"telemetry mismatch: claimed success={claimed_success}, "
            f"actual confirmed state={actual_confirmed}"
        )
    return True, None
