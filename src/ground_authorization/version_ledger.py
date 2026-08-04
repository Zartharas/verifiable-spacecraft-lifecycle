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

Phase 8 red-team fix (2026-08-04), findings #1 and #7 (see
Threat-Model.md "Phase 8 independent (blind, AI) red-team review"):

  - **Finding #1** — this file was previously plain, unsigned JSON,
    directly editable by anything with filesystem write access (e.g.
    resetting `last_approved_version` to 0 defeats downgrade protection
    with no signature/provenance forgery required). Now protected via
    `state_integrity.py` (HMAC sidecar); a tampered or deleted-after-
    protection ledger fails closed (denies the authorization) rather
    than silently falling back to "no prior version."
  - **Finding #7** — operational-monitoring mismatches (test cases
    #13/#15) were detected but never enforced; `pipeline.run()` logged
    them and moved on. This ledger is now the enforcement point: a
    detected mismatch **freezes** the stack's ledger, and every
    subsequent `check_and_advance()` call is denied until an operator
    explicitly `unfreeze()`s it. This is real behavioral enforcement, not
    just a stronger log message.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_store import EvidenceStore  # noqa: E402
from state_integrity import StateIntegrityError, protect, read_verified, discard  # noqa: E402

LEDGER_DIR = REPO_ROOT / "work"


def _ledger_path(stack: str) -> Path:
    return LEDGER_DIR / f"version_ledger.{stack}.json"


def _freeze_path(stack: str) -> Path:
    return LEDGER_DIR / f"version_ledger.{stack}.frozen.json"


def _read_last_approved(stack: str) -> int:
    """Raises StateIntegrityError if the ledger exists but fails
    verification — callers MUST treat that as a denial, never as
    'no prior version' (that would silently reopen the downgrade
    window the ledger exists to close)."""
    path = _ledger_path(stack)
    data = read_verified(path)
    if data is None:
        return 0
    content = data.decode().strip()
    if not content:
        return 0
    try:
        return json.loads(content).get("last_approved_version", 0)
    except json.JSONDecodeError:
        return 0


def _write_last_approved(version: int, stack: str) -> None:
    path = _ledger_path(stack)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"last_approved_version": version, "stack": stack}, f)
    protect(path)


def reset(stack: str = "cfs") -> None:
    """Test helper — reset the given stack's ledger (and its integrity
    sidecar, and any freeze) between test runs."""
    discard(_ledger_path(stack))
    _write_last_approved(0, stack)
    unfreeze(stack)


def is_frozen(stack: str) -> Optional[str]:
    """Returns the freeze reason if `stack`'s ledger is frozen, else
    None. Frozen state is itself integrity-protected for the same
    reason as the ledger: an attacker who could just delete the freeze
    file would defeat the whole enforcement fix (#7)."""
    path = _freeze_path(stack)
    try:
        data = read_verified(path)
    except StateIntegrityError:
        # A tampered/deleted-after-protection freeze marker is itself a
        # security-relevant event — fail closed by treating it as still
        # frozen with an explicit reason, rather than silently unfreezing.
        return "freeze marker failed integrity verification — treating as frozen"
    if data is None:
        return None
    content = data.decode().strip()
    if not content:
        # unfreeze() (via state_integrity.discard()) leaves an empty,
        # re-protected file in place rather than truly deleting it (some
        # sandboxes reject unlink() on files created by a prior process
        # — see STATUS.md "Environment notes"). Empty content here means
        # "not frozen," exactly like an empty ledger/partition-state file
        # means "no prior state" elsewhere in this module.
        return None
    try:
        return json.loads(content).get("reason")
    except json.JSONDecodeError:
        return "freeze marker unreadable — treating as frozen"


def freeze(stack: str, reason: str) -> None:
    """Enforcement action for Phase 8 red-team finding #7: called when
    an operational-monitoring mismatch (test case #13/#15) is detected.
    Every subsequent `check_and_advance()` for this stack is denied
    until `unfreeze()` is called explicitly (an operator action, not
    something the pipeline does automatically — a real detected
    ground/spacecraft mismatch should require human review before
    resuming automated approvals)."""
    path = _freeze_path(stack)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"frozen": True, "reason": reason, "stack": stack}, f)
    protect(path)
    EvidenceStore().record(
        pipeline_stage="ground_authorization",
        condition="S5",
        artifact_ref="n/a",
        actor="ground_authorization_service",
        result="fail",
        detail={"decision": "freeze", "stack": stack, "reason": reason},
    )


def unfreeze(stack: str) -> None:
    """Operator action clearing a freeze. Test helper doubles as the
    real 'operator has reviewed and cleared' action in this prototype —
    a real ground system would gate this behind an actual authenticated
    operator action, not a bare function call."""
    discard(_freeze_path(stack))


def check_and_advance(
    version: int, artifact_hash: str, condition_name: str = "S2", stack: str = "cfs"
) -> bool:
    """
    Returns True and advances the given stack's ledger if `version` is
    strictly greater than that stack's last approved version. Returns
    False (does NOT advance the ledger) if this looks like a downgrade
    attempt, if the stack is frozen (finding #7 enforcement), or if the
    ledger's own integrity check fails (finding #1 — fail closed, never
    silently trust unverifiable state).
    """
    store = EvidenceStore()

    freeze_reason = is_frozen(stack)
    if freeze_reason is not None:
        store.record(
            pipeline_stage="ground_authorization",
            condition=condition_name,
            artifact_ref=artifact_hash,
            actor="ground_authorization_service",
            result="fail",
            detail={"reason": "stack frozen (operational-monitoring mismatch)", "freeze_reason": freeze_reason, "stack": stack},
        )
        return False

    try:
        last_approved = _read_last_approved(stack)
    except StateIntegrityError as e:
        store.record(
            pipeline_stage="ground_authorization",
            condition=condition_name,
            artifact_ref=artifact_hash,
            actor="ground_authorization_service",
            result="fail",
            detail={"reason": "ground-truth ledger state integrity check failed", "error": str(e), "stack": stack},
        )
        return False

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
