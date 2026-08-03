"""
A/B partition manager — S4 assurance mechanism.

Models the standard embedded/spacecraft update pattern: write the new
artifact to the *inactive* slot, tentatively activate it, then only
*confirm* it (making the switch permanent) once health + attestation
checks pass. A failure before confirmation reverts the active pointer
back to the other slot — but only after checking that the recovery
target's own stored integrity hash still matches what was recorded when
it was last confirmed (test case #14: invalid recovery image). If that
check fails too, this honestly reports "cannot safely recover" rather
than silently activating a possibly-corrupted image.

State is a single JSON file (`work/partition_state.json`) — a Phase 3
simplification, same spirit as the Phase 2 version ledger. A real system
would tie this into signed, evidence-chained state (S5), not a bare file.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_store import EvidenceStore  # noqa: E402

PARTITIONS_DIR = REPO_ROOT / "work" / "partitions"
STATE_PATH = REPO_ROOT / "work" / "partition_state.json"

SLOTS = ("A", "B")


def _default_state() -> dict:
    return {
        "active": None,
        "A": {"version": None, "hash": None, "confirmed": False},
        "B": {"version": None, "hash": None, "confirmed": False},
    }


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return _default_state()
    try:
        content = STATE_PATH.read_text().strip()
        if not content:
            return _default_state()
        return json.loads(content)
    except json.JSONDecodeError:
        return _default_state()


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def reset() -> None:
    """Test helper — wipe partition state and files between test runs."""
    _save_state(_default_state())
    PARTITIONS_DIR.mkdir(parents=True, exist_ok=True)
    for slot in SLOTS:
        slot_path = PARTITIONS_DIR / slot / "installed_binary"
        if slot_path.exists():
            slot_path.write_bytes(b"")


def _slot_path(slot: str) -> Path:
    p = PARTITIONS_DIR / slot / "installed_binary"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _sha256_file(path: Path) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def inactive_slot() -> str:
    state = _load_state()
    active = state["active"]
    if active is None:
        return "A"  # bootstrap: nothing active yet, target A first
    return "B" if active == "A" else "A"


def active_slot() -> Optional[str]:
    return _load_state()["active"]


def get_active_path() -> Optional[Path]:
    slot = active_slot()
    if slot is None:
        return None
    return _slot_path(slot)


def write_to_inactive(source_binary_path: Path, version: int) -> tuple[str, Path]:
    """Copy the new artifact into the inactive slot, recording its
    intended hash/version (not yet confirmed)."""
    slot = inactive_slot()
    dest = _slot_path(slot)
    shutil.copy(source_binary_path, dest)
    dest.chmod(0o755)

    state = _load_state()
    state[slot] = {
        "version": version,
        "hash": _sha256_file(source_binary_path),  # intended hash
        "confirmed": False,
    }
    _save_state(state)
    return slot, dest


def verify_written(slot: str, condition_name: str = "S4") -> bool:
    """
    Test case #10 (interrupted installation): recompute the hash of what
    actually landed on disk in `slot` and compare against the intended
    hash recorded by write_to_inactive. A mismatch means the write was
    interrupted/corrupted.
    """
    store = EvidenceStore()
    state = _load_state()
    intended_hash = state[slot]["hash"]
    actual_path = _slot_path(slot)
    actual_hash = _sha256_file(actual_path) if actual_path.exists() else None

    ok = actual_hash == intended_hash
    store.record(
        pipeline_stage="installation",
        condition=condition_name,
        artifact_ref=intended_hash or "unknown",
        actor="installer",
        result="pass" if ok else "fail",
        detail={
            "slot": slot,
            "intended_hash": intended_hash,
            "actual_hash": actual_hash,
            "reason": None if ok else "installation was interrupted or corrupted in transit",
        },
        test_case_injected=None if ok else "10",
    )
    return ok


def tentative_activate(slot: str, condition_name: str = "S4") -> None:
    store = EvidenceStore()
    state = _load_state()
    state["active"] = slot
    _save_state(state)
    store.record(
        pipeline_stage="installation",
        condition=condition_name,
        artifact_ref=state[slot]["hash"] or "unknown",
        actor="installer",
        result="pass",
        detail={"decision": "tentative_activate", "slot": slot},
    )


def confirm_active(condition_name: str = "S4") -> None:
    store = EvidenceStore()
    state = _load_state()
    slot = state["active"]
    state[slot]["confirmed"] = True
    _save_state(state)
    store.record(
        pipeline_stage="operational_monitoring",
        condition=condition_name,
        artifact_ref=state[slot]["hash"] or "unknown",
        actor="health_monitor",
        result="pass",
        detail={"decision": "confirmed", "slot": slot},
    )


def revert_to_other(condition_name: str = "S4") -> tuple[bool, Optional[str]]:
    """
    Test case #14 (invalid recovery image) lives here: before reverting,
    verify the *other* slot's on-disk content still matches its last
    confirmed hash. If it doesn't, this is not a safe recovery target —
    report failure rather than activating a possibly-corrupted image.
    """
    store = EvidenceStore()
    state = _load_state()
    current = state["active"]
    other = "B" if current == "A" else "A"

    other_record = state[other]
    if not other_record.get("confirmed"):
        store.record(
            pipeline_stage="rollback",
            condition=condition_name,
            artifact_ref=other_record.get("hash") or "unknown",
            actor="rollback_controller",
            result="fail",
            detail={"reason": "no confirmed prior partition to roll back to", "slot": other},
        )
        return False, "no confirmed prior partition available"

    other_path = _slot_path(other)
    actual_hash = _sha256_file(other_path) if other_path.exists() else None
    if actual_hash != other_record["hash"]:
        store.record(
            pipeline_stage="rollback",
            condition=condition_name,
            artifact_ref=other_record["hash"],
            actor="rollback_controller",
            result="fail",
            detail={
                "reason": "recovery image integrity check failed — cannot safely roll back",
                "expected_hash": other_record["hash"],
                "actual_hash": actual_hash,
                "slot": other,
            },
            test_case_injected="14",
        )
        return False, "recovery image integrity check failed"

    state["active"] = other
    _save_state(state)
    store.record(
        pipeline_stage="rollback",
        condition=condition_name,
        artifact_ref=other_record["hash"],
        actor="rollback_controller",
        result="pass",
        detail={"reverted_to_slot": other},
    )
    return True, None
