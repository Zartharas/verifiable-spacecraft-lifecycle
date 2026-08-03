"""
Version ledger — tracks the last ground-approved version number so a
downgrade attempt (attack matrix test case #9) can be detected at ground
authorization. Deliberately simple (a single JSON file with one integer
per stack) — this is Phase 2 scope; a real system would tie this to the
evidence store / authorization-evidence chain (S5), not a side file.

Phase 6 note: the ledger is scoped **per target stack** (one file per
`stack`, see `src/target_stack.py`), not a single global counter. This
isn't a Phase-6-specific workaround so much as the more correct design
surfaced by testing against a second stack: a real ground system tracks
approved-version history per deployed target, not one counter shared
across every vehicle/stack it has ever approved a release for. Running
the evaluation harness against `stack="fprime"` with `version=1`
immediately (and correctly) exposed the bug in the single-global-counter
version of this file — it would have been flagged as a downgrade attempt
against whatever version the `cfs` stack's test suite had already
advanced the counter to. Fixed by keying the ledger file by stack.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_store import EvidenceStore  # noqa: E402

LEDGER_DIR = REPO_ROOT / "work"


def _ledger_path(stack: str) -> Path:
    return LEDGER_DIR / f"version_ledger.{stack}.json"


def _read_last_approved(stack: str) -> int:
    path = _ledger_path(stack)
    if not path.exists():
        return 0
    try:
        with open(path) as f:
            content = f.read().strip()
            if not content:
                return 0
            return json.loads(content).get("last_approved_version", 0)
    except json.JSONDecodeError:
        return 0


def _write_last_approved(version: int, stack: str) -> None:
    path = _ledger_path(stack)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"last_approved_version": version, "stack": stack}, f)


def reset(stack: str = "cfs") -> None:
    """Test helper — reset the given stack's ledger between test runs."""
    _write_last_approved(0, stack)


def check_and_advance(
    version: int, artifact_hash: str, condition_name: str = "S2", stack: str = "cfs"
) -> bool:
    """
    Returns True and advances the given stack's ledger if `version` is
    strictly greater than that stack's last approved version. Returns
    False (does NOT advance the ledger) if this looks like a downgrade
    attempt.
    """
    store = EvidenceStore()
    last_approved = _read_last_approved(stack)

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
                "stack": stack,
            },
            test_case_injected="9",
        )
        return False

    _write_last_approved(version, stack)
    store.record(
        pipeline_stage="ground_authorization",
        condition=condition_name,
        artifact_ref=artifact_hash,
        actor="ground_authorization_service",
        result="pass",
        detail={"approved_version": version, "previous_version": last_approved, "stack": stack},
    )
    return True
