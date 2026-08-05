"""
Rollback controller — the actor named in Pipeline-Flow-Document.md that
decides whether to confirm a tentatively-activated partition or revert.
Thin coordination layer over installation/partitions.py (which owns the
actual state and the recovery-image integrity check, test case #14) —
kept as its own module to match the architecture's named actor and to
keep the "when do we roll back" policy separate from "how partition state
is stored."
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from installation import partitions  # noqa: E402


def resolve(
    health_ok: bool,
    attestation_ok: bool,
    condition_name: str = "S4",
) -> tuple[str, Optional[str]]:
    """
    Given the results of health validation and attestation verification
    for the tentatively-active partition, either confirm it or roll back.

    Returns (outcome, reason) where outcome is one of:
      "confirmed"       — health + attestation both passed, now permanent
      "rolled_back"      — reverted to the other (confirmed) partition
      "recovery_failed"  — reversion itself failed (test case #14)

    Fourth independent (blind, AI) red-team pass, finding P4-T
    (2026-08-06): `partitions.confirm_active()` now re-verifies the
    slot's on-disk bytes against the hash recorded at write time
    immediately before confirming (see its docstring), and can itself
    fail closed. Previously this function called it and unconditionally
    returned "confirmed" without checking for a failure at all — treat a
    confirm-time integrity failure exactly like a failed health check:
    fall through to the same recovery path, not a silent "confirmed"
    that never actually happened.
    """
    if health_ok and attestation_ok:
        confirmed, confirm_reason = partitions.confirm_active(condition_name=condition_name)
        if confirmed:
            return "confirmed", None
        # Confirm-time integrity check failed even though health +
        # attestation passed earlier — treat it the same as any other
        # reason to attempt recovery, not a silent pass-through.
        reason = confirm_reason
    else:
        reason = None

    reverted, revert_reason = partitions.revert_to_other(condition_name=condition_name)
    if reverted:
        return "rolled_back", revert_reason or reason
    return "recovery_failed", revert_reason or reason
