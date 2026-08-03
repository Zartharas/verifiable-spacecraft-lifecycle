"""
Phase 3 (S3/S4) pipeline tests — attestation + rollback.

Covers the Phase 3 exit criteria from Implementation-Plan.md: an
interrupted installation (#10) and a failed health check (#11) both
correctly trigger rollback to last-known-good, with full evidence trail.
Also covers #12 (stale attestation) and #14 (invalid recovery image).
Test case #13 (ground/spacecraft inventory disagreement) is deferred to
Phase 4 (S5) per Threat-Model.md — not in scope here.

Run with: pytest tests/test_phase3_pipeline.py -v
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from pipeline import run  # noqa: E402
from ground_authorization import version_ledger  # noqa: E402
from installation import partitions  # noqa: E402
from evidence_store import EvidenceStore  # noqa: E402


def setup_function(_):
    version_ledger.reset()
    partitions.reset()


def _fail_records_for(stage: str, test_case: str) -> list[dict]:
    store = EvidenceStore()
    return [
        r
        for r in store.read_all()
        if r["pipeline_stage"] == stage and r["result"] == "fail" and r["test_case_injected"] == test_case
    ]


def test_s3_happy_path_no_recovery_mechanism_but_healthy():
    result = run(condition_name="S3", version=1)
    assert result.ground_approved is True
    assert result.installed_path is not None
    assert result.health_ok is True
    assert result.rejected_at is None


def test_s4_happy_path_confirms_partition():
    result = run(condition_name="S4", version=1)
    assert result.rollback_outcome == "confirmed"
    assert result.installed_path is not None
    assert result.rejected_at is None


def test_case_10_interrupted_installation_caught_at_s4():
    """Threat-Model.md row 10 — expected first detection S4."""
    # First, a good S4 install to establish a confirmed baseline partition.
    baseline = run(condition_name="S4", version=1)
    assert baseline.rollback_outcome == "confirmed"

    # Now attempt an update that gets interrupted mid-write.
    result = run(condition_name="S4", version=2, simulate_interrupted_install=True)
    assert result.rejected_at == "installation"
    assert result.installed_path is None  # never even tentatively activated
    assert _fail_records_for("installation", "10")

    # The system stayed on the baseline partition — confirm it's still there.
    assert partitions.active_slot() is not None
    active_state = partitions._load_state()  # test-only introspection
    assert active_state[active_state["active"]]["version"] == 1


def test_case_11_failed_health_check_triggers_rollback_at_s4():
    """Threat-Model.md row 11 — expected first detection S3/S4."""
    baseline = run(condition_name="S4", version=1)
    assert baseline.rollback_outcome == "confirmed"

    result = run(condition_name="S4", version=2, force_health_fail=True)
    assert result.health_ok is False
    assert result.rollback_outcome == "rolled_back"
    assert result.rejected_at == "post_install_rolled_back"
    assert _fail_records_for("health_validation", "11")

    # Confirm we're back on the baseline version, not the broken one.
    active_state = partitions._load_state()
    assert active_state[active_state["active"]]["version"] == 1


def test_case_12_stale_attestation_triggers_rollback_at_s4():
    """Threat-Model.md row 12 — expected first detection S3."""
    baseline = run(condition_name="S4", version=1)
    assert baseline.rollback_outcome == "confirmed"

    # Backdate the attestation well past the freshness window.
    from attestation.attestation import DEFAULT_FRESHNESS_SECONDS

    result = run(
        condition_name="S4",
        version=2,
        attestation_backdate_seconds=DEFAULT_FRESHNESS_SECONDS + 3600,
    )
    assert result.rollback_outcome == "rolled_back"
    assert _fail_records_for("attestation_verification", "12")


def test_case_14_invalid_recovery_image_reported_honestly():
    """
    Threat-Model.md row 14 — expected first detection S4.

    Corrupts the confirmed baseline partition's on-disk content directly
    (simulating bit rot or a prior undetected corruption of the recovery
    image itself), then forces a health failure on the new install so a
    rollback is attempted. The rollback must refuse to activate the
    corrupted "recovery" image rather than silently trusting it.
    """
    baseline = run(condition_name="S4", version=1)
    assert baseline.rollback_outcome == "confirmed"

    # Corrupt slot A's on-disk file after the fact (bit rot simulation).
    state = partitions._load_state()
    baseline_slot = state["active"]
    slot_path = partitions._slot_path(baseline_slot)
    data = bytearray(slot_path.read_bytes())
    data[0] ^= 0xFF
    slot_path.write_bytes(bytes(data))

    result = run(condition_name="S4", version=2, force_health_fail=True)
    assert result.rollback_outcome == "recovery_failed"
    assert _fail_records_for("rollback", "14")
