"""
Phase 8 ablation-study extension tests (2026-08-05).

Covers the reviewer-objection-#5 fix: `disable_mechanisms` is now threaded
through `ground_authorization.ground_auth.authorize()` and
`onboard_verification.onboard.verify_received_bundle()`, not just
`pipeline.py`'s own gating — see those modules' docstrings and
`evaluation/ablation.py`'s updated scope note.

These are fast, single-trial regression checks (n=1) that lock in the
*mechanism* of the fix — that ablating sbom/provenance/
machine_readable_authorization actually reaches the checks that used to
be immune to it. The statistically-meaningful, 30-trial version of this
same claim lives in `evaluation/ablation.py`'s own results
(evaluation/results/phase8_ablation_cfs.json) and is not re-run here;
pytest is for correctness, not for regenerating the paper's numbers.

Run with: pytest tests/test_phase8_ablation_extension.py -v
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "evaluation"))

from ground_authorization import version_ledger  # noqa: E402
from installation import partitions  # noqa: E402
from signing.signing import reset_revocation_list  # noqa: E402
from attestation.attestation import reset_attestation_revocation_list  # noqa: E402
from pipeline import run  # noqa: E402
from ablation import ABLATIONS  # noqa: E402


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


def test_ablations_list_covers_five_of_six_mechanisms():
    """Before the fix, only onboard_attestation/trusted_rollback/
    machine_readable_authorization were ablatable (3/6). The fix adds
    sbom and provenance, and a second scenario (test case #8) for
    machine_readable_authorization -- 5 distinct mechanisms covered
    across 6 curated (test_case, mechanism) entries. signature is the
    one deliberately excluded mechanism (see ablation.py docstring)."""
    mechanisms_covered = {mechanism for _, mechanism, _, _, _ in ABLATIONS}
    assert mechanisms_covered == {
        "sbom",
        "provenance",
        "onboard_attestation",
        "trusted_rollback",
        "machine_readable_authorization",
    }
    assert "signature" not in mechanisms_covered


def test_sbom_ablation_reaches_ground_auth():
    """Ablating 'sbom' must now be visible to ground_auth.authorize()'s
    own Condition, not just pipeline.py's gating of generate_sbom(). A
    vulnerable-dependency SBOM must go undetected once the mechanism is
    off, having been caught with it on."""
    baseline = run(condition_name="S1", version=901, stack="cfs", disable_mechanisms=())
    assert baseline.rejected_at is None

    caught_active = run(
        condition_name="S1", version=902, inject_vulnerable_dependency=True, stack="cfs"
    )
    assert caught_active.rejected_at == "ground_authorization"

    version_ledger.reset("cfs")
    partitions.reset()
    caught_ablated = run(
        condition_name="S1",
        version=903,
        inject_vulnerable_dependency=True,
        stack="cfs",
        disable_mechanisms=("sbom",),
    )
    assert caught_ablated.rejected_at is None, (
        "vulnerable-dependency SBOM was still caught with 'sbom' ablated -- "
        "ground_auth.authorize() is not respecting disable_mechanisms"
    )


def test_provenance_ablation_reaches_ground_auth():
    """Same claim for 'provenance': a rogue/unregistered builder_id must
    go undetected once provenance is ablated at the ground_auth level."""
    caught_active = run(
        condition_name="S2", version=904, builder_id="rogue-unregistered-runner", stack="cfs"
    )
    assert caught_active.rejected_at == "ground_authorization"

    version_ledger.reset("cfs")
    partitions.reset()
    caught_ablated = run(
        condition_name="S2",
        version=905,
        builder_id="rogue-unregistered-runner",
        stack="cfs",
        disable_mechanisms=("provenance",),
    )
    assert caught_ablated.rejected_at is None, (
        "rogue builder_id was still caught with 'provenance' ablated -- "
        "ground_auth.authorize() is not respecting disable_mechanisms"
    )


def test_s5_policy_ablation_reaches_both_ground_and_onboard():
    """Test case #8 (prohibited configuration) is checked twice: once in
    ground_auth.authorize(), once redundantly in onboard.
    verify_received_bundle() (Phase 8 finding #4). Ablating
    machine_readable_authorization must silence BOTH -- if onboard's
    independent copy still catches it, the ablation isn't a clean test
    of the mechanism's necessity, it's just moving the detection point."""
    caught_active = run(
        condition_name="S5", version=906, configuration={"debug_mode": True}, stack="cfs"
    )
    assert caught_active.rejected_at in ("ground_authorization", "onboard_verification")

    version_ledger.reset("cfs")
    partitions.reset()
    caught_ablated = run(
        condition_name="S5",
        version=907,
        configuration={"debug_mode": True},
        stack="cfs",
        disable_mechanisms=("machine_readable_authorization",),
    )
    assert caught_ablated.rejected_at not in ("ground_authorization", "onboard_verification"), (
        f"prohibited configuration was still caught (rejected_at="
        f"{caught_ablated.rejected_at!r}) with machine_readable_authorization "
        f"ablated -- either ground_auth.py or onboard.py is not respecting "
        f"disable_mechanisms"
    )
