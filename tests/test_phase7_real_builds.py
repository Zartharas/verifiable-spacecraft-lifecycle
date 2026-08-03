"""
Phase 7 (real framework builds) tests — exercises the pipeline against the
genuine, Docker-built cFS and F´ binaries (`"cfs-real"`, `"fprime-real"`
in `src/target_stack.py`) rather than the stand-in stubs.

These tests are SKIPPED automatically if the prebuilt binaries aren't
present — they only exist after someone actually runs
`cfs-app/Dockerfile` / `fprime-app/Dockerfile` on a Docker-capable
machine (see each app's README). Neither the Claude authoring sandbox
nor a fresh CI checkout has them; only the user's local Docker Desktop
run produces them, and they are gitignored (never committed — see
`.gitignore` and `cfs-app/confirmed-build.json` /
`fprime-app/confirmed-build.json` for the provenance record instead).

Scope: confirms the S0-S2 lifecycle (build → provenance → SBOM → signing
→ ground authorization → uplink → onboard verification → installation)
works against real artifacts, AND (since ISSUE-003's fix) that S3+
conditions (attestation, persistent-process health check, rollback) work
against both real, long-running binaries via the
`_health_check_persistent_process` strategy in `health_check.py` — see
ISSUES-AND-FIXES-LOG.md ISSUE-003 and Threat-Model.md "Phase 7 findings"
for the full writeup of the persistent-process design.

Run with: pytest tests/test_phase7_real_builds.py -v
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from pipeline import run  # noqa: E402
from ground_authorization import version_ledger  # noqa: E402
from installation import partitions  # noqa: E402
import target_stack  # noqa: E402

CFS_REAL_AVAILABLE = target_stack.get("cfs-real").prebuilt_binary_path.exists()
FPRIME_REAL_AVAILABLE = target_stack.get("fprime-real").prebuilt_binary_path.exists()


def setup_function(_):
    version_ledger.reset("cfs-real")
    version_ledger.reset("fprime-real")
    partitions.reset()


@pytest.mark.skipif(not CFS_REAL_AVAILABLE, reason="real cfs binary not built — run cfs-app/Dockerfile first")
def test_cfs_real_s2_happy_path():
    result = run(condition_name="S2", version=1, stack="cfs-real")
    assert result.rejected_at is None
    assert result.installed_path is not None
    # Reproducibility here is a trivial copy-integrity check, not a real
    # two-build comparison — see build.py module docstring.
    assert result.build_result["reproducible"] is True


@pytest.mark.skipif(not FPRIME_REAL_AVAILABLE, reason="real fprime binary not built — run fprime-app/Dockerfile first")
def test_fprime_real_s2_happy_path():
    result = run(condition_name="S2", version=1, stack="fprime-real")
    assert result.rejected_at is None
    assert result.installed_path is not None
    assert result.build_result["reproducible"] is True


@pytest.mark.skipif(not CFS_REAL_AVAILABLE, reason="real cfs binary not built — run cfs-app/Dockerfile first")
def test_cfs_real_s4_happy_path():
    """
    core-cpu1 is a long-running flight-software process — health_check.py
    must use the persistent-process strategy (launch, watch for the real
    `CFE_ES_Main entering OPERATIONAL state` boot-success line, terminate)
    rather than the exact-match model. See ISSUES-AND-FIXES-LOG.md
    ISSUE-003.
    """
    result = run(condition_name="S4", version=2, stack="cfs-real")
    assert result.health_ok is True
    assert result.rollback_outcome == "confirmed"
    assert result.rejected_at is None


@pytest.mark.skipif(not FPRIME_REAL_AVAILABLE, reason="real fprime binary not built — run fprime-app/Dockerfile first")
def test_fprime_real_s4_happy_path():
    """
    Ref is a network server that never exits on its own while waiting for
    a GDS connection — same persistent-process strategy as
    test_cfs_real_s4_happy_path, keyed off Ref's real `Hit Ctrl-C to quit`
    boot-success line instead.
    """
    result = run(condition_name="S4", version=2, stack="fprime-real")
    assert result.health_ok is True
    assert result.rollback_outcome == "confirmed"
    assert result.rejected_at is None


@pytest.mark.skipif(not CFS_REAL_AVAILABLE, reason="real cfs binary not built — run cfs-app/Dockerfile first")
def test_cfs_real_s4_forced_health_failure_triggers_rollback():
    """Test case #11 (failed health check) against the real cFS binary:
    force_health_fail must still short-circuit before the
    persistent-process check even runs, and rollback must recover."""
    baseline = run(condition_name="S4", version=1, stack="cfs-real")
    assert baseline.rollback_outcome == "confirmed"

    result = run(condition_name="S4", version=2, stack="cfs-real", force_health_fail=True)
    assert result.health_ok is False
    assert result.rollback_outcome == "rolled_back"
    assert result.rejected_at is not None


@pytest.mark.skipif(not FPRIME_REAL_AVAILABLE, reason="real fprime binary not built — run fprime-app/Dockerfile first")
def test_fprime_real_s4_forced_health_failure_triggers_rollback():
    """Test case #11 against the real F´ binary — same reasoning as
    test_cfs_real_s4_forced_health_failure_triggers_rollback."""
    baseline = run(condition_name="S4", version=1, stack="fprime-real")
    assert baseline.rollback_outcome == "confirmed"

    result = run(condition_name="S4", version=2, stack="fprime-real", force_health_fail=True)
    assert result.health_ok is False
    assert result.rollback_outcome == "rolled_back"
    assert result.rejected_at is not None
