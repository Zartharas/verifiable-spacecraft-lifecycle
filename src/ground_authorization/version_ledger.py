"""
Version ledger — tracks the last ground-approved version number so a
downgrade attempt (attack matrix test case #9) can be detected at ground
authorization. Deliberately simple (a single JSON file with one integer)
— this is Phase 2 scope; a real system would tie this to the evidence
store / authorization-evidence chain (S5), not a side file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_store import EvidenceStore  # noqa: E402

LEDGER_PATH = REPO_ROOT / "work" / "version_ledger.json"


def _read_last_approved() -> int:
    if not LEDGER_PATH.exists():
        return 0
    try:
        with open(LEDGER_PATH) as f:
            content = f.read().strip()
            if not content:
                return 0
            return json.loads(content).get("last_approved_version", 0)
    except json.JSONDecodeError:
        return 0


def _write_last_approved(version: int) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER_PATH, "w") as f:
        json.dump({"last_approved_version": version}, f)


def reset() -> None:
    """Test helper — reset the ledger between test runs."""
    _write_last_approved(0)


def check_and_advance(
    version: int, artifact_hash: str, condition_name: str = "S2"
) -> bool:
    """
    Returns True and advances the ledger if `version` is strictly greater
    than the last approved version. Returns False (does NOT advance the
    ledger) if this looks like a downgrade attempt.
    """
    store = EvidenceStore()
    last_approved = _read_last_approved()

    if version <= last_approved:
        store.record(
            pipeline_stage="ground_authorization",
            condition=condition_name,
            artifact_ref=artifact_hash,
            actor="ground_authorization_service",
            result="fail",
            detail={
                "reason": "downgrade attempt",
                "attempted_version": version,
                "last_approved_version": last_approved,
            },
            test_case_injected="9",
        )
        return False

    _write_last_approved(version)
    store.record(
        pipeline_stage="ground_authorization",
        condition=condition_name,
        artifact_ref=artifact_hash,
        actor="ground_authorization_service",
        result="pass",
        detail={"approved_version": version, "previous_version": last_approved},
    )
    return True
