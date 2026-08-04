"""
Phase 8 red-team remediation tests (2026-08-04).

Covers all 7 findings from the blind (AI) red-team review — see
Threat-Model.md "Phase 8 independent (blind, AI) red-team review" for
the original findings and "Phase 8 red-team fixes" for what changed.
Each test demonstrates the specific gap the red-team found, confirms it
is now closed, and (where relevant) confirms the fix fails *closed*
rather than merely fixing the one exact reported scenario.

Run with: pytest tests/test_phase8_redteam_fixes.py -v
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_store.authorization_evidence import verify_authorization_evidence  # noqa: E402
from ground_authorization import version_ledger  # noqa: E402
from installation import partitions  # noqa: E402
from attestation.attestation import (  # noqa: E402
    is_attestation_key_revoked,
    revoke_current_attestation_key,
    reset_attestation_revocation_list,
)
from signing.signing import is_revoked, revoke_current_key, reset_revocation_list  # noqa: E402
from state_integrity import StateIntegrityError, protect, discard  # noqa: E402
from pipeline import run  # noqa: E402


def setup_function(_):
    version_ledger.reset("cfs")
    partitions.reset()
    reset_revocation_list()
    reset_attestation_revocation_list()


def teardown_function(_):
    version_ledger.reset("cfs")
    partitions.reset()
    reset_revocation_list()
    reset_attestation_revocation_list()


# --- Finding #1: unprotected ground-truth state files -------------------


def test_finding1_tampered_version_ledger_fails_closed():
    """Directly editing the ledger's content (bypassing the
    integrity-protected write path) must be detected and cause every
    subsequent authorization to be denied — not silently treated as
    'no prior version', which would reopen the downgrade window."""
    run(condition_name="S2", version=5, stack="cfs")  # legitimate approval

    ledger_path = version_ledger._ledger_path("cfs")
    tampered = ledger_path.read_bytes().replace(b"5", b"0")
    ledger_path.write_bytes(tampered)  # direct edit, sidecar now stale

    with pytest.raises(StateIntegrityError):
        version_ledger._read_last_approved("cfs")

    result = run(condition_name="S2", version=1, stack="cfs")
    assert result.rejected_at == "ground_authorization"
    assert result.ground_approved is False


def test_finding1_deleted_content_with_sidecar_remaining_fails_closed(tmp_path):
    """Deleting a protected file but leaving its integrity sidecar behind
    (the literal 'delete the file to reset it' tamper pattern the
    red-team found) must fail closed, not be treated as fresh/never-
    written state. Exercised directly against state_integrity.py's
    contract on a fresh path — this sandbox rejects unlink() on files a
    prior write already created (see STATUS.md "Environment notes"), so
    this test creates the sidecar directly rather than deleting real
    ledger state to reach the same code path."""
    p = tmp_path / "protected_state.json"
    p.write_text('{"x": 1}')
    protect(p)
    p.unlink()  # fresh tmp_path file, never touched before — unlink works here

    with pytest.raises(StateIntegrityError):
        from state_integrity import read_verified

        read_verified(p)


def test_finding1_tampered_partition_state_fails_closed():
    """Same property for partition state: a direct edit must be caught,
    and the pipeline must reject rather than trust unverifiable state.

    Detection point update (second red-team pass, finding #3,
    2026-08-05): this used to always fail at
    `partition_state_integrity_failure` (inside pipeline.py's own
    trusted_rollback try/except). Since onboard.py's new independent
    downgrade check (`check_independent_downgrade`) now reads partition
    state during onboard verification -- which runs *before* that
    try/except block -- the same tamper is now caught even earlier, at
    `onboard_verification`. Both are genuine fail-closed outcomes for the
    same underlying tamper; accept either rather than pin to one exact
    stage name and risk this test looking broken every time detection
    coverage gets earlier/better."""
    run(condition_name="S4", version=1, stack="cfs")  # confirms partition A

    partitions.STATE_PATH.write_text(
        partitions.STATE_PATH.read_text().replace('"confirmed": true', '"confirmed": false')
    )

    with pytest.raises(StateIntegrityError):
        partitions._load_state()

    result = run(condition_name="S4", version=2, stack="cfs")
    assert result.rejected_at in ("partition_state_integrity_failure", "onboard_verification")


# --- Finding #2: fail-open key revocation --------------------------------


def test_finding2_legitimate_never_revoked_state_is_not_revoked():
    """Sanity check: the fix must not make every key look revoked by
    default — a genuinely never-touched revocation list means 'not
    revoked', same as before."""
    assert is_revoked() is False


def test_finding2_deleting_revocation_list_after_a_revocation_fails_closed(tmp_path, monkeypatch):
    """The exact red-team scenario: a key is revoked, then the
    revocation list file is deleted (its sidecar remains) to try to
    silently un-revoke it. Must now fail closed (treat as revoked),
    not fail open (treat as not revoked). Uses a fresh tmp_path copy of
    the revocation-list mechanism since this sandbox rejects unlink() on
    files a prior write already created (see STATUS.md "Environment
    notes") — monkeypatching REVOKED_KEYS_PATH to a fresh, deletable
    location exercises the identical code path."""
    import signing.signing as signing_mod

    fresh_path = tmp_path / "revoked_keys.txt"
    monkeypatch.setattr(signing_mod, "REVOKED_KEYS_PATH", fresh_path)

    revoke_current_key()
    assert is_revoked() is True

    fresh_path.unlink()  # sidecar remains — fresh tmp_path file, unlink works here
    assert is_revoked() is True  # fails closed, not open


def test_finding2_tampered_revocation_list_fails_closed():
    revoke_current_key()
    from signing.signing import REVOKED_KEYS_PATH

    REVOKED_KEYS_PATH.write_text("some-other-fingerprint\n")  # direct edit
    assert is_revoked() is True


# --- Finding #3: version/provenance binding ------------------------------


def test_finding3_inflated_version_argument_rejected():
    """Supplying a version to authorize()/run() that doesn't match what
    generate_provenance() actually embedded must be rejected — this is
    exactly the DoS vector the red-team found: an inflated version could
    otherwise poison the ledger and lock out real future releases."""
    from ground_authorization.ground_auth import authorize
    from provenance.provenance import generate_provenance
    from signing.signing import sign
    from sbom.sbom import generate_sbom
    from build.build import build

    build_result = build(condition_name="S2", stack="cfs")
    binary_path = Path(build_result["binary_path"])
    prov_path = generate_provenance(binary_path, condition_name="S2", version=1)
    sbom_path = generate_sbom(binary_path, condition_name="S2")
    sig_path = sign(binary_path, condition_name="S2")

    # Provenance says version 1, but we ask ground authorization to
    # approve version 999 — must be denied, not silently accepted.
    approved = authorize(
        binary_path,
        sig_path,
        condition_name="S2",
        sbom_path=sbom_path,
        prov_path=prov_path,
        version=999,
        stack="cfs",
    )
    assert approved is False


def test_finding3_matching_version_still_approved():
    """Sanity check: the fix must not break the legitimate case where
    the argument and the provenance record agree."""
    result = run(condition_name="S2", version=7, stack="cfs")
    assert result.ground_approved is True


# --- Finding #4: dead onboard policy stub + string-match gate -----------


def test_finding4_onboard_rejects_prohibited_configuration_at_s5():
    """The onboard side must independently reject a prohibited
    configuration at S5, not just ground authorization — the whole
    point of the fix is that onboard verification no longer rubber-
    stamps this via a dead `return True` stub."""
    from onboard_verification.onboard import verify_received_bundle
    from signing.signing import sign
    from build.build import build

    build_result = build(condition_name="S5", stack="cfs")
    binary_path = Path(build_result["binary_path"])
    sig_path = sign(binary_path, condition_name="S5")

    ok = verify_received_bundle(
        binary_path, sig_path, condition_name="S5", configuration={"debug_mode": True}
    )
    assert ok is False


def test_finding4_gate_uses_mechanism_flag_not_literal_string():
    """The gate must key off cond.active('machine_readable_authorization')
    (via condition.preset()), not a literal `condition_name == "S5"`
    string compare — confirmed by checking S4 (mechanism inactive) does
    NOT run the policy check even with a prohibited configuration."""
    from onboard_verification.onboard import verify_received_bundle
    from signing.signing import sign
    from build.build import build

    build_result = build(condition_name="S4", stack="cfs")
    binary_path = Path(build_result["binary_path"])
    sig_path = sign(binary_path, condition_name="S4")

    ok = verify_received_bundle(
        binary_path, sig_path, condition_name="S4", configuration={"debug_mode": True}
    )
    assert ok is True  # S4 has no policy mechanism at all — correctly not checked


# --- Finding #5: unsigned, overwritable authorization evidence ----------


def test_finding5_authorization_evidence_is_signed_and_verifiable():
    result = run(condition_name="S5", version=1, stack="cfs")
    assert result.authorization_evidence_path is not None
    valid, reason = verify_authorization_evidence(result.authorization_evidence_path)
    assert valid is True, reason


def test_finding5_tampered_authorization_evidence_fails_verification():
    result = run(condition_name="S5", version=2, stack="cfs")
    doc_path = result.authorization_evidence_path
    content = doc_path.read_text().replace('"overall_result": "pass"', '"overall_result": "fail"')
    doc_path.write_text(content)

    valid, reason = verify_authorization_evidence(doc_path)
    assert valid is False


def test_finding5_repeated_runs_never_overwrite_prior_evidence():
    """Two runs against the same (in this stub, constant) artifact hash
    must produce two distinct, independently-readable evidence files —
    not one silently clobbering the other."""
    r1 = run(condition_name="S5", version=10, stack="cfs")
    r2 = run(condition_name="S5", version=11, stack="cfs")
    assert r1.authorization_evidence_path != r2.authorization_evidence_path
    assert r1.authorization_evidence_path.exists()
    assert r2.authorization_evidence_path.exists()


# --- Finding #6: no attestation-key revocation ---------------------------


def test_finding6_attestation_key_not_revoked_by_default():
    assert is_attestation_key_revoked() is False


def test_finding6_revoked_attestation_key_rejected_at_s4():
    revoke_current_attestation_key()
    assert is_attestation_key_revoked() is True

    result = run(condition_name="S4", version=1, stack="cfs")
    # Attestation is checked, fails due to revocation, and since
    # attestation_ok becomes False, rollback.resolve() must not confirm.
    assert result.rollback_outcome != "confirmed"


def test_finding6_deleted_attestation_revocation_list_fails_closed(tmp_path, monkeypatch):
    """Same pattern as finding #2's equivalent test — monkeypatched to a
    fresh, deletable tmp_path location for the same sandbox-unlink
    reason (see STATUS.md "Environment notes")."""
    import attestation.attestation as attestation_mod

    fresh_path = tmp_path / "attestation_revoked_keys.txt"
    monkeypatch.setattr(attestation_mod, "ATTESTATION_REVOKED_KEYS_PATH", fresh_path)

    revoke_current_attestation_key()
    assert is_attestation_key_revoked() is True

    fresh_path.unlink()  # sidecar remains
    assert is_attestation_key_revoked() is True


# --- Finding #7: unenforced operational-monitoring mismatches -----------


def test_finding7_telemetry_mismatch_freezes_stack_and_rejects_run():
    """A detected telemetry mismatch (test case #15's own scenario) must
    now (a) mark that run's own result as rejected and (b) freeze the
    stack so the *next* authorization attempt is denied too — real
    enforcement, not just a log entry."""
    result = run(
        condition_name="S5",
        version=1,
        force_health_fail=True,
        claimed_telemetry_success=True,  # contradicts the actual (failed) outcome
        stack="cfs",
    )
    assert result.telemetry_consistent is False
    assert result.rejected_at is not None

    assert version_ledger.is_frozen("cfs") is not None

    # The freeze must actually block the next attempt too.
    next_result = run(condition_name="S2", version=2, stack="cfs")
    assert next_result.ground_approved is False
    assert next_result.rejected_at == "ground_authorization"


def test_finding7_unfreeze_restores_normal_operation():
    run(
        condition_name="S5",
        version=1,
        force_health_fail=True,
        claimed_telemetry_success=True,
        stack="cfs",
    )
    assert version_ledger.is_frozen("cfs") is not None

    version_ledger.unfreeze("cfs")
    assert version_ledger.is_frozen("cfs") is None

    result = run(condition_name="S2", version=2, stack="cfs")
    assert result.ground_approved is True


def test_finding7_tampered_freeze_marker_fails_closed():
    """A freeze marker that fails its own integrity check must be
    treated as still frozen — an attacker shouldn't be able to clear an
    enforcement freeze by corrupting the marker any more than they
    could by deleting it."""
    version_ledger.freeze("cfs", reason="test")
    freeze_path = version_ledger._freeze_path("cfs")
    tampered = freeze_path.read_bytes().replace(b"test", b"tampered-bytes-of-different-length")
    freeze_path.write_bytes(tampered)  # direct edit, sidecar now stale

    assert version_ledger.is_frozen("cfs") is not None
    result = run(condition_name="S2", version=1, stack="cfs")
    assert result.ground_approved is False
    assert result.rejected_at == "ground_authorization"
