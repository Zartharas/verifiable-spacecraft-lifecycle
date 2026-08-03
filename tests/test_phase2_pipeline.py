"""
Phase 2 (S1/S2) pipeline tests — SBOM + provenance.

Covers the Phase 2 exit criteria from Implementation-Plan.md: S1 and S2
conditions each demonstrably catch a superset of what S0 catches, with
evidence records showing the mechanism that caught each case. Also covers
attack matrix test cases #1, #2, #3, #4, #5, #9 (Threat-Model.md).

Run with: pytest tests/test_phase2_pipeline.py -v
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from pipeline import run  # noqa: E402
from ground_authorization import version_ledger  # noqa: E402
from evidence_store import EvidenceStore  # noqa: E402


def setup_function(_):
    """Each test starts with a clean version ledger — downgrade detection
    (test case #9) is inherently stateful across calls, so tests must not
    interfere with each other via shared ledger state."""
    version_ledger.reset()


def _fail_records_for(stage: str, test_case: str) -> list[dict]:
    store = EvidenceStore()
    return [
        r
        for r in store.read_all()
        if r["pipeline_stage"] == stage
        and r["result"] == "fail"
        and r["test_case_injected"] == test_case
    ]


def test_s1_happy_path_installs_successfully():
    result = run(condition_name="S1", version=1)
    assert result.ground_approved is True
    assert result.installed_path is not None
    assert result.sbom_path is not None
    assert result.provenance_path is None  # not active at S1


def test_s2_happy_path_installs_successfully():
    result = run(condition_name="S2", version=1)
    assert result.ground_approved is True
    assert result.installed_path is not None
    assert result.sbom_path is not None
    assert result.provenance_path is not None


def test_case_01_binary_does_not_match_source_caught_at_s2():
    """Threat-Model.md row 1 — expected first detection S2."""
    result = run(condition_name="S2", version=1, corrupt_binary_after_provenance=True)
    assert result.ground_approved is False
    assert result.rejected_at == "ground_authorization"
    assert _fail_records_for("provenance_verification", "1")


def test_case_01_not_caught_at_s1_since_provenance_inactive():
    """
    S1 has no provenance mechanism, so the same corruption is NOT caught
    at the ground-authorization stage at S1 — it would only be caught
    later (e.g. by signature verification, since signing happens after
    the corruption in this test). This confirms S1 does not accidentally
    inherit S2's detection, which is the whole point of the ladder.
    """
    result = run(condition_name="S1", version=1, corrupt_binary_after_provenance=True)
    # S1 has no provenance step, so corrupt_binary_after_provenance is a
    # no-op here (nothing to corrupt "after provenance" since none was
    # generated) — this just documents that S1 genuinely lacks the S2
    # mechanism, not that the attack silently passes review.
    assert result.provenance_path is None


def test_case_02_missing_provenance_caught_at_s2():
    """Threat-Model.md row 2 — expected first detection S2."""
    result = run(condition_name="S2", version=1)
    # Delete the provenance file after generation but before ground auth
    # would be the realistic injection point; simplest robust simulation
    # here is to corrupt/blank an existing one via direct file write.
    # Re-run against a fresh version with provenance forcibly emptied:
    from provenance.provenance import generate_provenance
    from sbom.sbom import generate_sbom
    from build.build import build as build_stage

    build_result = build_stage(condition_name="S2")
    binary_path = Path(build_result["binary_path"])
    # S2's preset requires SBOM *and* provenance (see CONDITION_PRESETS in
    # condition.py) — supply a valid SBOM so the failure we're isolating
    # is specifically the provenance one, not a missing-SBOM short-circuit.
    sbom_path = generate_sbom(binary_path, condition_name="S2")
    prov_path = generate_provenance(binary_path, condition_name="S2", version=2)
    prov_path.write_text("")  # simulate missing/corrupted provenance

    from ground_authorization.ground_auth import authorize
    from signing.signing import sign

    sig_path = sign(binary_path, condition_name="S2")
    approved = authorize(
        binary_path, sig_path, condition_name="S2", sbom_path=sbom_path, prov_path=prov_path, version=2
    )
    assert approved is False
    assert _fail_records_for("provenance_verification", "2")


def test_case_03_incomplete_sbom_caught_at_s1():
    """Threat-Model.md row 3 — expected first detection S1."""
    result = run(condition_name="S1", version=1, inject_incomplete_sbom=True)
    assert result.ground_approved is False
    assert result.rejected_at == "ground_authorization"
    assert _fail_records_for("sbom_verification", "3")


def test_case_04_known_vulnerable_dependency_caught_at_s1():
    """Threat-Model.md row 4 — expected first detection S1."""
    result = run(condition_name="S1", version=1, inject_vulnerable_dependency=True)
    assert result.ground_approved is False
    assert result.rejected_at == "ground_authorization"
    assert _fail_records_for("sbom_verification", "4")


def test_case_05_unauthorized_build_runner_caught_at_s2():
    """Threat-Model.md row 5 — expected first detection S2."""
    result = run(condition_name="S2", version=1, builder_id="rogue-unregistered-runner")
    assert result.ground_approved is False
    assert result.rejected_at == "ground_authorization"
    assert _fail_records_for("provenance_verification", "5")


def test_case_09_downgrade_attempt_caught_at_s2():
    """Threat-Model.md row 9 — expected first detection S2/S4."""
    first = run(condition_name="S2", version=5)
    assert first.ground_approved is True

    downgrade = run(condition_name="S2", version=3)  # lower than 5
    assert downgrade.ground_approved is False
    assert downgrade.rejected_at == "ground_authorization"
    assert _fail_records_for("ground_authorization", "9")


def test_case_09_not_active_at_s1():
    """S1 has no provenance/version-ledger mechanism, so repeated/lower
    version numbers are not checked at all — confirms the ladder property
    that S1 genuinely lacks this mechanism rather than silently having it."""
    version_ledger.reset()
    first = run(condition_name="S1", version=5)
    assert first.ground_approved is True
    second = run(condition_name="S1", version=1)  # would be a downgrade at S2
    assert second.ground_approved is True  # S1 doesn't check version at all
