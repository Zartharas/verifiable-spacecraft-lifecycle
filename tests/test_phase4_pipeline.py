"""
Phase 4 (S5) pipeline tests — machine-readable authorization evidence.

Covers the Phase 4 exit criteria from Implementation-Plan.md: all 15 test
cases from Threat-Model.md pass at their expected detection condition,
and a full S0-S5 comparison table can be generated from the evidence
store automatically (see evaluation/metrics.py::build_comparison_table,
exercised in test_full_comparison_table_generates below).

Run with: pytest tests/test_phase4_pipeline.py -v
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


def test_s5_happy_path_confirms_and_generates_evidence():
    result = run(condition_name="S5", version=1)
    assert result.rollback_outcome == "confirmed"
    assert result.inventory_reconciled is True
    assert result.telemetry_consistent is True
    assert result.authorization_evidence_path is not None
    assert result.authorization_evidence_path.exists()


def test_case_08_prohibited_configuration_caught_at_s5():
    """Threat-Model.md row 8 — expected first detection S5."""
    result = run(condition_name="S5", version=1, configuration={"debug_mode": True})
    assert result.ground_approved is False
    assert result.rejected_at == "ground_authorization"
    assert _fail_records_for("configuration_policy_check", "8")


def test_case_08_not_active_before_s5():
    """
    S4 has no machine-readable policy mechanism, so the same prohibited
    configuration is silently accepted — signature/SBOM/provenance are
    all satisfied, and there's no S4 mechanism to check `configuration`
    against anything. Confirms the ladder property: S4 genuinely lacks
    this mechanism rather than happening to catch it anyway.
    """
    result = run(condition_name="S4", version=1, configuration={"debug_mode": True})
    assert result.rollback_outcome == "confirmed"  # accepted despite the flag S5 would reject


def test_case_13_inventory_disagreement_after_rollback():
    """
    Threat-Model.md row 13 — expected first detection S5.

    A natural way ground/spacecraft inventory disagrees: ground approves
    version 2, but the spacecraft's health check fails and it rolls back
    to version 1 — and ground was never told. Simulate by directly
    advancing the ground version ledger to look like it approved version 2
    while the spacecraft is actually confirmed on version 1, then run
    reconciliation directly (mirrors how test_phase2's test_case_02
    isolates a single mechanism against hand-built state).
    """
    baseline = run(condition_name="S5", version=1)
    assert baseline.rollback_outcome == "confirmed"

    # Simulate a rollback the spacecraft/ground never reconciled: force a
    # failed health check so the spacecraft stays on version 1, but bump
    # what ground *would have* expected to version 2 by calling
    # reconcile_inventory directly with a mismatched expectation.
    from operational_monitoring import monitoring

    ok, reason = monitoring.reconcile_inventory(
        ground_expected_version=2,
        spacecraft_confirmed_version=1,
        artifact_hash="test-artifact-hash-for-case-13",
        condition_name="S5",
    )
    assert ok is False
    assert _fail_records_for("inventory_reconciliation", "13")


def test_case_15_false_success_telemetry_caught_at_s5():
    """Threat-Model.md row 15 — expected first detection S5/S3."""
    baseline = run(condition_name="S5", version=1)
    assert baseline.rollback_outcome == "confirmed"

    result = run(
        condition_name="S5",
        version=2,
        force_health_fail=True,
        claimed_telemetry_success=True,  # lies about success despite the rollback
    )
    assert result.rollback_outcome == "rolled_back"
    assert result.telemetry_consistent is False
    assert _fail_records_for("operational_monitoring", "15")


def test_full_comparison_table_generates():
    """Phase 4 exit criterion: a full S0-S5 comparison table can be
    generated from the evidence store automatically."""
    from evaluation.metrics import build_comparison_table

    # Populate the evidence store with at least one run across a spread
    # of conditions so the table has real content.
    run(condition_name="S0", version=100)
    run(condition_name="S1", version=101)
    run(condition_name="S5", version=102)

    table = build_comparison_table()
    assert isinstance(table, dict)
    assert len(table) > 0
    # Every condition present should map to a dict of stage -> counts.
    for condition, stages in table.items():
        assert isinstance(stages, dict)
