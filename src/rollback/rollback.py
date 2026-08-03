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
    """
    if health_ok and attestation_ok:
        partitions.confirm_active(condition_name=condition_name)
        return "confirmed", None

    reverted, reason = partitions.revert_to_other(condition_name=condition_name)
    if reverted:
        return "rolled_back", reason
    return "recovery_failed", reason
