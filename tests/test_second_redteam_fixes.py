"""
Second (wider) blind red-team review fixes (2026-08-05).

Covers all 12 findings from the second independent (blind, AI) red-team
pass — see Threat-Model.md "Phase 8 second independent red-team review"
for the original findings and their fixes. This pass was scoped
specifically to cover what the FIRST pass never saw (build.py,
health_check.py, uplink_sim/, evaluation/*) plus every file changed for
reviewer objections 5 and 9 the same session — see that section for the
full methodology.

Run with: pytest tests/test_second_redteam_fixes.py -v
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "evaluation"))

from ground_authorization import version_ledger  # noqa: E402
from installation import partitions  # noqa: E402
from signing.signing import (  # noqa: E402
    is_revoked,
    revoke_current_key,
    reset_revocation_list,
    sign,
)
from attestation.attestation import (  # noqa: E402
    DEFAULT_FRESHNESS_SECONDS,
    generate_attestation,
    is_attestation_key_revoked,
    reset_attestation_revocation_list,
    revoke_current_attestation_key,
    verify_attestation,
)
from sbom.sbom import generate_sbom, verify_sbom  # noqa: E402
from provenance import provenance as provenance_mod  # noqa: E402
from provenance.provenance import generate_provenance, verify_provenance  # noqa: E402
from policy.policy import check_configuration  # noqa: E402
from onboard_verification.onboard import check_independent_downgrade  # noqa: E402
from uplink_sim.uplink import transmit, IDEAL  # noqa: E402
from build.build import build  # noqa: E402
from pipeline import run  # noqa: E402
import health.health_check as health_check  # noqa: E402
from health.health_check import _launch_process  # noqa: E402
import target_stack  # noqa: E402
from evidence_store import EvidenceStore  # noqa: E402

from ablation import _ablation_case_04, _ablation_case_05, _ablation_case_12  # noqa: E402
from experiment import scenario_13, _reset_all_state  # noqa: E402
from report import summarize_happy_path  # noqa: E402


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


# --- Finding #1: SBOM not bound to the artifact it describes ------------


def test_finding1_sbom_bound_to_wrong_binary_is_rejected(tmp_path):
    binary_a = tmp_path / "binary_a"
    binary_a.write_bytes(b"binary A content")
    binary_b = tmp_path / "binary_b"
    binary_b.write_bytes(b"a completely different binary B")

    sbom_path = generate_sbom(binary_a, condition_name="S1")
    assert verify_sbom(sbom_path, binary_path=binary_a, condition_name="S1") is True
    assert verify_sbom(sbom_path, binary_path=binary_b, condition_name="S1") is False


def test_finding1_verify_sbom_without_binary_path_keeps_old_behavior(tmp_path):
    """Backward compatibility: existing call sites that never pass
    binary_path (structure-only checks) must be unaffected."""
    binary = tmp_path / "binary"
    binary.write_bytes(b"content")
    sbom_path = generate_sbom(binary, condition_name="S1")
    assert verify_sbom(sbom_path, condition_name="S1") is True


# --- Finding #2: Docker fallback now bind-mounts the real binary --------


def test_finding2_docker_fallback_mounts_the_real_installed_binary(tmp_path, monkeypatch):
    import errno

    installed = tmp_path / "installed_binary"
    installed.write_bytes(b"the actual attested binary")

    captured_cmds = []

    class _FakePopen:
        def __init__(self, cmd, **kwargs):
            captured_cmds.append(cmd)
            if len(captured_cmds) == 1:
                raise OSError(errno.ENOEXEC, "Exec format error")

    monkeypatch.setattr(health_check.subprocess, "Popen", _FakePopen)

    stack_def = target_stack.Stack(
        name="test-stack",
        binary_name="installed_binary",
        description="d",
        prebuilt_binary_path=installed,
        boot_success_markers=("x",),
        docker_image="some-image",
        container_binary_path="/some/path/binary",
    )
    _launch_process(installed, stack_def)

    assert len(captured_cmds) == 2
    docker_cmd = captured_cmds[1]
    assert "-v" in docker_cmd
    mount_idx = docker_cmd.index("-v")
    mount_arg = docker_cmd[mount_idx + 1]
    assert mount_arg == f"{installed.resolve()}:/some/path/binary:ro"
    # mount flag must precede the image name, and the executed path must
    # still be the in-container path (now overlaid by the mount)
    assert docker_cmd.index("some-image") > mount_idx
    assert docker_cmd[docker_cmd.index("some-image") + 1] == "/some/path/binary"


# --- Finding #3: onboard-side independent downgrade check ----------------


def test_finding3_onboard_rejects_downgrade_against_own_confirmed_state():
    partitions.write_to_inactive(REPO_ROOT / "README.md", version=10)
    partitions.tentative_activate("A")
    partitions.confirm_active()

    ok, reason = check_independent_downgrade(5)
    assert ok is False
    assert "lower" in reason

    ok, reason = check_independent_downgrade(15)
    assert ok is True


def test_finding3_tampered_partition_state_fails_closed_not_a_crash():
    """This check runs during onboard verification, which happens before
    pipeline.py's own trusted_rollback try/except block -- a
    StateIntegrityError here must be caught and turned into a denial by
    check_independent_downgrade itself, not left to propagate and crash
    pipeline.run() outright (regression: this was missed on the first
    pass and broke test_phase8_redteam_fixes.py's tampered-partition-
    state test, which now runs at S4 and reaches this code path first)."""
    from state_integrity import StateIntegrityError

    partitions.write_to_inactive(REPO_ROOT / "README.md", version=1)
    partitions.tentative_activate("A")
    partitions.confirm_active()

    state_path = partitions.STATE_PATH
    tampered = state_path.read_bytes().replace(b"1", b"9")
    state_path.write_bytes(tampered)

    with pytest.raises(StateIntegrityError):
        partitions._load_state()  # confirm the tamper is real, not a no-op

    ok, reason = check_independent_downgrade(5)
    assert ok is False
    assert "integrity" in reason


def test_finding3_no_confirmed_state_means_no_baseline_to_compare():
    """Nothing confirmed onboard yet (state["active"] is None) -- the
    check must not fabricate a rejection with no baseline to compare
    against."""
    ok, reason = check_independent_downgrade(1)
    assert ok is True


def test_finding3_end_to_end_downgrade_caught_onboard_at_s4_when_ground_desynced():
    """Full pipeline: the whole point of finding #3 is a defense that
    works when ground_auth's OWN downgrade check (the version ledger)
    can't help -- e.g. ground's ledger has no memory of what the
    spacecraft actually has confirmed (reset, never told about a prior
    out-of-band confirmation, etc). Simulate exactly that: the spacecraft
    has version 50 confirmed onboard, but ground's ledger is reset to
    "no prior version" -- so ground_auth.py's own check sees nothing
    wrong with an incoming version 10 and approves it. The new
    onboard-side check must still catch it independently."""
    partitions.write_to_inactive(REPO_ROOT / "README.md", version=50)
    partitions.tentative_activate("A")
    partitions.confirm_active()
    version_ledger.reset("cfs")  # ground has no memory of version 50

    result = run(condition_name="S4", version=10, stack="cfs")
    assert result.ground_approved is True, (
        "test setup assumption violated: ground_auth's own ledger check "
        "should NOT catch this (that's what makes it demonstrate the "
        "independent onboard defense, not a duplicate of the existing one)"
    )
    assert result.onboard_verified is False
    assert result.rejected_at == "onboard_verification"


# --- Finding #4: attestation freshness has no floor ----------------------


def test_finding4_future_dated_attestation_is_rejected(tmp_path):
    binary = tmp_path / "binary"
    binary.write_bytes(b"content")
    # backdate_seconds negative -> timestamp in the future
    attestation_path = generate_attestation(binary, "single", backdate_seconds=-3600)
    ok, reason = verify_attestation(attestation_path, binary)
    assert ok is False
    assert "future" in reason


def test_finding4_normal_fresh_attestation_still_passes(tmp_path):
    binary = tmp_path / "binary"
    binary.write_bytes(b"content")
    attestation_path = generate_attestation(binary, "single", backdate_seconds=0)
    ok, _ = verify_attestation(attestation_path, binary)
    assert ok is True


def test_finding4_stale_attestation_still_correctly_rejected(tmp_path):
    """Regression guard: the new future-timestamp floor must not have
    disturbed the pre-existing staleness check (test case #12)."""
    binary = tmp_path / "binary"
    binary.write_bytes(b"content")
    attestation_path = generate_attestation(
        binary, "single", backdate_seconds=DEFAULT_FRESHNESS_SECONDS + 3600
    )
    ok, reason = verify_attestation(attestation_path, binary)
    assert ok is False
    assert "stale" in reason


# --- Finding #5: persistent-process health check has no artifact-identity
# check -- documented as a known limitation, not fixed (see docstring); no
# test needed here since no code changed for it.


# --- Finding #6: provenance has no dirty-source-tree check ---------------


def test_finding6_dirty_tree_rejected_when_required(tmp_path, monkeypatch):
    binary = tmp_path / "binary"
    binary.write_bytes(b"content")
    monkeypatch.setattr(provenance_mod, "_source_tree_dirty", lambda: True)
    prov_path = generate_provenance(binary, condition_name="S2", version=1)

    ok, reason, _ = verify_provenance(binary, prov_path, require_clean_tree=True)
    assert ok is False
    assert "dirty" in reason


def test_finding6_dirty_tree_not_enforced_by_default(tmp_path, monkeypatch):
    """require_clean_tree defaults to False -- ground_auth.py's real call
    site must be unaffected by this project's own repo being dirty during
    active development."""
    binary = tmp_path / "binary"
    binary.write_bytes(b"content")
    monkeypatch.setattr(provenance_mod, "_source_tree_dirty", lambda: True)
    prov_path = generate_provenance(binary, condition_name="S2", version=1)

    ok, _reason, _ = verify_provenance(binary, prov_path)
    assert ok is True


def test_finding6_clean_tree_passes_even_when_required(tmp_path, monkeypatch):
    binary = tmp_path / "binary"
    binary.write_bytes(b"content")
    monkeypatch.setattr(provenance_mod, "_source_tree_dirty", lambda: False)
    prov_path = generate_provenance(binary, condition_name="S2", version=1)

    ok, _reason, _ = verify_provenance(binary, prov_path, require_clean_tree=True)
    assert ok is True


# --- Finding #7: scenario_13 now drives a real pipeline execution --------


def test_finding7_scenario_13_detects_a_real_inventory_mismatch():
    _reset_all_state("cfs")
    result = scenario_13((201, 202), stack="cfs")
    assert result["caught"] is True
    assert "elapsed_seconds" in result


# --- Finding #8: report.py now checks trial-to-trial consistency --------


def _trial(overrides=None):
    base = {
        "elapsed_seconds": 1.0,
        "reproducible": True,
        "success": True,
        "traceability_completeness": 1.0,
        "sbom_size": 100,
        "provenance_size": 50,
        "attestation_size": 0,
        "authorization_evidence_size": 0,
        "attestation_age_seconds": None,
        "record_count": 5,
    }
    base.update(overrides or {})
    return base


def test_finding8_consistent_trials_flagged_consistent():
    raw = {"happy_path": {"S1": [_trial(), _trial(), _trial()]}}
    summary = summarize_happy_path(raw)
    assert summary["S1"]["trial_metrics_consistent"] is True
    assert summary["S1"]["trial_metrics_inconsistencies"] == []


def test_finding8_divergent_trial_flagged_inconsistent():
    raw = {
        "happy_path": {
            "S1": [_trial(), _trial(overrides={"sbom_size": 999}), _trial()],
        }
    }
    summary = summarize_happy_path(raw)
    assert summary["S1"]["trial_metrics_consistent"] is False
    assert any("sbom_bytes" in msg for msg in summary["S1"]["trial_metrics_inconsistencies"])
    # reported value is still trial[0]'s, unchanged behavior for the
    # primary number
    assert summary["S1"]["storage_overhead_bytes"]["sbom_bytes"] == 100


# --- Finding #9: no automatic key rotation after revocation --------------


def test_finding9_sign_with_revoked_key_logs_evidence_but_does_not_crash(tmp_path):
    binary = tmp_path / "binary"
    binary.write_bytes(b"content")
    revoke_current_key()
    store = EvidenceStore()
    start = len(store.read_all())

    sig_path = sign(binary, condition_name="S0")  # must not raise

    assert sig_path.exists()
    records = store.read_all()[start:]
    assert any(
        r["pipeline_stage"] == "signing" and "revoked" in r["detail"].get("reason", "")
        for r in records
    )
    # downstream verification is still the actual defense
    assert is_revoked() is True


def test_finding9_attest_with_revoked_key_logs_evidence_but_does_not_crash(tmp_path):
    binary = tmp_path / "binary"
    binary.write_bytes(b"content")
    revoke_current_attestation_key()
    store = EvidenceStore()
    start = len(store.read_all())

    attestation_path = generate_attestation(binary, "single")  # must not raise

    assert attestation_path.exists()
    records = store.read_all()[start:]
    assert any(
        r["pipeline_stage"] == "boot_attestation" and "revoked" in r["detail"].get("reason", "")
        for r in records
    )
    assert is_attestation_key_revoked() is True


# --- Finding #10: policy type-coercion bypass -----------------------------


@pytest.mark.parametrize("config", [{"debug_mode": True}, {"debug_mode": "true"}, {"debug_mode": 1}, {"debug_mode": "1"}])
def test_finding10_all_truthy_representations_are_caught(config):
    ok, reason = check_configuration(config, "hash123", condition_name="S5")
    assert ok is False
    assert "prohibited" in reason


@pytest.mark.parametrize("config", [{"debug_mode": False}, {"debug_mode": "false"}, {"debug_mode": 0}, {}])
def test_finding10_falsy_representations_still_pass(config):
    ok, _reason = check_configuration(config, "hash123", condition_name="S5")
    assert ok is True


def test_finding10_non_boolean_fields_keep_exact_equality():
    """The coercion is specifically scoped to boolean pattern values --
    must not turn into a general fuzzy matcher for anything else."""
    ok, _ = check_configuration({"some_other_field": "1"}, "hash123", condition_name="S5")
    assert ok is True  # no rule for "some_other_field" at all


# --- Third independent (blind, AI) red-team pass, finding #1: policy
# key-name case-sensitivity bypass (2026-08-06) --------------------------
#
# Finding #10 above fixed the *value* axis ({"debug_mode": "true"} vs
# True). It never touched the *key* axis: {"DEBUG_MODE": True} means the
# exact same thing as the only prohibited pattern but never matched it,
# because the old lookup was `config.get(k)` with the pattern's exact-case
# key. Proven end-to-end through `pipeline.run(condition_name="S5",
# configuration={"DEBUG_MODE": True})`: the release was confirmed onboard
# and the signed S5 authorization-evidence document recorded
# `overall_result: "pass"` with no failed records anywhere in it -- a
# real "report says PASS without a genuine check" failure.


@pytest.mark.parametrize(
    "config",
    [{"DEBUG_MODE": True}, {"Debug_Mode": True}, {"debug_mode": True}],
)
def test_finding_case_variant_keys_are_caught(config):
    ok, reason = check_configuration(config, "hash123", condition_name="S5")
    assert ok is False
    assert "prohibited" in reason


@pytest.mark.parametrize(
    "config",
    [{"DEBUG_MODE": False}, {"Debug_Mode": "false"}, {}],
)
def test_finding_case_variant_falsy_keys_still_pass(config):
    ok, _reason = check_configuration(config, "hash123", condition_name="S5")
    assert ok is True


# --- Finding #11: ablation baseline-assertion guard consistency ---------


def test_finding11_ablation_case_04_does_not_crash_under_ablation():
    result = _ablation_case_04("cfs", ("sbom",), (301, 302))
    assert "caught" in result


def test_finding11_ablation_case_05_does_not_crash_under_ablation():
    result = _ablation_case_05("cfs", ("provenance",), (303, 304))
    assert "caught" in result


def test_finding11_ablation_case_12_does_not_crash_under_ablation():
    result = _ablation_case_12("cfs", ("onboard_attestation",), (305, 306))
    assert "caught" in result


# --- Finding #12: uplink tamper byte offset is no longer fixed ----------


def test_finding12_tamper_offset_varies_with_seed(tmp_path):
    binary_path = Path(build(condition_name="S0", stack="cfs")["binary_path"])
    sig_path = binary_path.with_suffix(binary_path.suffix + ".sig")
    sig_path.write_bytes(b"irrelevant-signature-bytes")

    offsets = set()
    for seed in range(8):
        received_binary, _ = transmit(
            binary_path, sig_path, tamper=True, link_profile=IDEAL, rng_seed=seed
        )
        original = binary_path.read_bytes()
        received = received_binary.read_bytes()
        diffs = [i for i in range(len(original)) if original[i] != received[i]]
        assert len(diffs) == 1
        offsets.add(diffs[0])

    assert len(offsets) > 1, (
        f"tamper injection produced the same byte offset across 8 different "
        f"seeds ({offsets}) -- expected diversity, not a fixed midpoint"
    )
