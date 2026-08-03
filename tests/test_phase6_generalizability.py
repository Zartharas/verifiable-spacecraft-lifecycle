"""
Phase 6 (generalizability) tests — re-runs a representative slice of the
pipeline and attack matrix against a second, architecturally distinct
stand-in target stack (`stack="fprime"`, see `src/target_stack.py` and
`fprime-app/README.md`) to demonstrate that the S0-S5 assurance ladder's
mechanisms and evidence schema are stack-agnostic, not accidentally
coupled to the Phase 1-5 `cfs` stub's specific shape (a single C file, a
"channel=N value=M" stdout format).

This file does NOT re-run the full 15-case matrix with repeated trials —
that's `evaluation/experiment.py` (parameterized by `stack`, see
`evaluation/results/phase6_report.md`). This file covers one
representative case per assurance layer (signature, provenance,
rollback) plus a dedicated regression test for the version-ledger
stack-scoping bug found while writing these tests — see
Threat-Model.md "Phase 6 results" for the full writeup.

Run with: pytest tests/test_phase6_generalizability.py -v
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from pipeline import run  # noqa: E402
from ground_authorization import version_ledger  # noqa: E402
from installation import partitions  # noqa: E402
from evidence_store import EvidenceStore  # noqa: E402
import target_stack  # noqa: E402


def setup_function(_):
    version_ledger.reset("cfs")
    version_ledger.reset("fprime")
    partitions.reset()


def _fail_records_for(stage: str, test_case: str) -> list[dict]:
    store = EvidenceStore()
    return [
        r
        for r in store.read_all()
        if r["pipeline_stage"] == stage and r["result"] == "fail" and r["test_case_injected"] == test_case
    ]


def test_both_stacks_registered_and_distinct():
    cfs = target_stack.get("cfs")
    fprime = target_stack.get("fprime")
    assert cfs.compiler == "gcc" and fprime.compiler == "g++"
    assert cfs.source_filename.endswith(".c")
    assert fprime.source_filename.endswith(".cpp")
    assert cfs.expected_health_output != fprime.expected_health_output


def test_build_reproducible_for_fprime_stack():
    from build.build import build

    result = build(condition_name="S0", stack="fprime")
    assert result["reproducible"] is True
    assert result["stack"] == "fprime"


def test_s0_happy_path_fprime():
    result = run(condition_name="S0", version=1, stack="fprime")
    assert result.rejected_at is None
    assert result.installed_path is not None
    assert result.build_result["reproducible"] is True


def test_s5_happy_path_fprime_generates_evidence():
    result = run(condition_name="S5", version=1, stack="fprime")
    assert result.rollback_outcome == "confirmed"
    assert result.inventory_reconciled is True
    assert result.telemetry_consistent is True
    assert result.authorization_evidence_path is not None
    assert result.authorization_evidence_path.exists()


def test_case_06_modified_update_in_transit_fprime():
    """Threat-Model.md row 6, re-run against the fprime stack — expected
    first detection S0, same as stack #1."""
    result = run(condition_name="S0", version=1, tamper_in_transit=True, stack="fprime")
    assert result.rejected_at == "onboard_verification"
    assert _fail_records_for("onboard_signature_verification", "6")


def test_case_01_binary_provenance_mismatch_fprime():
    """Threat-Model.md row 1, re-run against the fprime stack — expected
    first detection S2."""
    result = run(
        condition_name="S2", version=1, corrupt_binary_after_provenance=True, stack="fprime"
    )
    assert result.rejected_at == "ground_authorization"
    assert _fail_records_for("provenance_verification", "1")


def test_case_11_failed_health_triggers_rollback_fprime():
    """Threat-Model.md row 11, re-run against the fprime stack — expected
    first detection S4."""
    baseline = run(condition_name="S4", version=1, stack="fprime")
    assert baseline.rollback_outcome == "confirmed"

    result = run(condition_name="S4", version=2, force_health_fail=True, stack="fprime")
    assert result.rollback_outcome == "rolled_back"
    assert _fail_records_for("health_validation", "11")


def test_case_14_invalid_recovery_image_fprime():
    """Threat-Model.md row 14, re-run against the fprime stack — expected
    first detection S4."""
    baseline = run(condition_name="S4", version=1, stack="fprime")
    assert baseline.rollback_outcome == "confirmed"

    state = partitions._load_state()
    slot_path = partitions._slot_path(state["active"])
    data = bytearray(slot_path.read_bytes())
    data[0] ^= 0xFF
    slot_path.write_bytes(bytes(data))

    result = run(condition_name="S4", version=2, force_health_fail=True, stack="fprime")
    assert result.rollback_outcome == "recovery_failed"
    assert _fail_records_for("rollback", "14")


def test_version_ledgers_are_isolated_per_stack():
    """
    Regression test for a real bug found while building this file: the
    version ledger (src/ground_authorization/version_ledger.py) used to
    be one global JSON file shared across every stack. Approving version
    1 for `cfs` and then version 1 for `fprime` in the same session would
    have made the second call look like a downgrade attempt (test case
    #9) purely because of cross-stack state bleed, not an actual
    downgrade. Fixed by keying the ledger file by stack — this test
    guards against that regression coming back.
    """
    cfs_result = run(condition_name="S2", version=50, stack="cfs")
    assert cfs_result.rejected_at is None

    fprime_result = run(condition_name="S2", version=1, stack="fprime")
    assert fprime_result.rejected_at is None, (
        "fprime version 1 was wrongly rejected as a downgrade — "
        "version ledgers are not properly isolated per stack"
    )
