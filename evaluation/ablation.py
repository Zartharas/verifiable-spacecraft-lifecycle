"""
Phase 8 ablation study.

Why this exists: every one of the 15 attack matrix test cases in
evaluation/experiment.py is evaluated ONLY at the condition where its
responsible mechanism is active (e.g. test case #12 only at S4, where
onboard_attestation is on). That shows each mechanism catches its target
attack, but never shows what happens if the mechanism is ABSENT — so a
reviewer could reasonably ask whether "100% detection across all 15
cases" reflects the S0-S5 ladder's structure doing real, isolable work,
or a test suite where everything is engineered to always trip (see the
2026-08 rejection-risk review in docs/Research-Paper-Outline.md).

This script closes that gap: for a small, curated set of (condition,
mechanism, attack scenario) triples, it holds the target condition's
configuration fixed and forces exactly ONE mechanism off (via
condition.custom(), wired through pipeline.run()'s new disable_mechanisms
parameter — see src/condition.py and src/pipeline.py), then re-runs the
same attack. The result changes exactly as the threat model predicts:
either the attack goes fully undetected, or detection holds but recovery
capability is specifically lost (the documented S3-vs-S4 distinction,
now demonstrated with re-run data instead of just prose).

Scope, stated explicitly rather than left implicit: only mechanisms
gated directly inside src/pipeline.py's own `cond` object can be cleanly
ablated this way — onboard_attestation, trusted_rollback,
machine_readable_authorization. The prohibited-configuration policy
check (test case #8) lives inside src/ground_authorization/ground_auth.py,
which derives its own Condition independently via condition.preset() and
ignores pipeline.py's ablated one — so "signature"/"sbom"/"provenance"
mechanisms, and the S5 policy check specifically, are NOT ablatable via
this script without also threading disable_mechanisms into
ground_auth.authorize(). That's a natural follow-up, not a silent gap;
noted here and in docs/Threat-Model.md so nobody mistakes "3 mechanisms
ablated" for "all mechanisms ablated."

Run with: python3 evaluation/ablation.py             # cfs
          python3 evaluation/ablation.py fprime       # fprime
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "evaluation"))

from pipeline import run  # noqa: E402
from attestation.attestation import DEFAULT_FRESHNESS_SECONDS  # noqa: E402
from experiment import _reset_all_state, _timed_run, N_TRIALS  # noqa: E402
from ground_authorization import version_ledger  # noqa: E402

N_ABLATION_TRIALS = N_TRIALS


def _ablation_case_12(stack: str, disable: tuple[str, ...], version_pair: tuple[int, int]) -> dict:
    """Test case #12 (stale attestation) at S4. Normally caught via
    attestation staleness -> rolled_back. Ablating onboard_attestation
    means attestation is never generated/checked at all (attestation_ok
    defaults to True in pipeline.py), so a stale-attestation attack has
    nothing left to trip it."""
    baseline_version, attack_version = version_pair
    baseline = run(condition_name="S4", version=baseline_version, stack=stack, disable_mechanisms=disable)
    assert baseline.rollback_outcome == "confirmed", (
        f"baseline run did not confirm as expected (stack={stack!r}, disable={disable!r}): "
        f"rollback_outcome={baseline.rollback_outcome!r}, health_ok={baseline.health_ok!r}, "
        f"rejected_at={baseline.rejected_at!r}"
    )
    t0 = time.perf_counter()
    result = run(
        condition_name="S4",
        version=attack_version,
        attestation_backdate_seconds=DEFAULT_FRESHNESS_SECONDS + 3600,
        stack=stack,
        disable_mechanisms=disable,
    )
    elapsed = time.perf_counter() - t0
    return {"caught": result.rollback_outcome == "rolled_back", "elapsed_seconds": elapsed}


def _ablation_case_11(stack: str, disable: tuple[str, ...], version_pair: tuple[int, int]) -> dict:
    """Test case #11 (failed post-install health check) at S4. Normally
    caught AND recovered via rollback (rollback_outcome == "rolled_back").
    Ablating trusted_rollback drops the pipeline into the S3-equivalent
    branch: attestation + health check still run (onboard_attestation
    stays active), so the failure is still DETECTED
    (rejected_at == "post_install_unrecoverable_at_s3"), but rollback_outcome
    stays None — recovery capability specifically lost, not detection."""
    baseline_version, attack_version = version_pair
    baseline = run(condition_name="S4", version=baseline_version, stack=stack, disable_mechanisms=disable)
    if not disable:
        assert baseline.rollback_outcome == "confirmed", (
            f"baseline run did not confirm as expected (stack={stack!r}): "
            f"rollback_outcome={baseline.rollback_outcome!r}, rejected_at={baseline.rejected_at!r}"
        )
    t0 = time.perf_counter()
    result = run(
        condition_name="S4",
        version=attack_version,
        force_health_fail=True,
        stack=stack,
        disable_mechanisms=disable,
    )
    elapsed = time.perf_counter() - t0
    detected = (result.rollback_outcome == "rolled_back") or (
        result.rejected_at == "post_install_unrecoverable_at_s3"
    )
    recovered = result.rollback_outcome == "rolled_back"
    return {
        "caught": detected,
        "recovered": recovered,
        "rollback_outcome": result.rollback_outcome,
        "rejected_at": result.rejected_at,
        "elapsed_seconds": elapsed,
    }


def _ablation_case_15(stack: str, disable: tuple[str, ...], version_pair: tuple[int, int]) -> dict:
    """Test case #15 (false telemetry claim) at S5. Normally caught via
    the machine_readable_authorization block's check_telemetry call
    (telemetry_consistent == False). Ablating that mechanism skips the
    entire inventory-reconciliation/telemetry-check/authorization-evidence
    block, so telemetry_consistent stays at its default None — no check
    ever ran, rather than a check that ran and passed.

    Mirrors evaluation/experiment.py's scenario_15 exactly (force_health_fail
    so the actual outcome genuinely fails, claimed_telemetry_success=True so
    the ground-reported claim contradicts it) — the actual mismatch
    check_telemetry is built to catch."""
    baseline_version, attack_version = version_pair
    baseline = run(condition_name="S5", version=baseline_version, stack=stack, disable_mechanisms=disable)
    if not disable:
        assert baseline.rollback_outcome == "confirmed", (
            f"baseline run did not confirm as expected (stack={stack!r}): "
            f"rollback_outcome={baseline.rollback_outcome!r}, rejected_at={baseline.rejected_at!r}"
        )
    t0 = time.perf_counter()
    result = run(
        condition_name="S5",
        version=attack_version,
        force_health_fail=True,
        claimed_telemetry_success=True,
        stack=stack,
        disable_mechanisms=disable,
    )
    elapsed = time.perf_counter() - t0
    return {
        "caught": result.telemetry_consistent is False,
        "telemetry_consistent": result.telemetry_consistent,
        "elapsed_seconds": elapsed,
    }


# Each entry: (test_case, mechanism, condition, runner, metric). "metric"
# is the dict key the ablation is actually judged on — for #12 and #15
# that's "caught" (detection itself is lost when ablated); for #11 it's
# "recovered" (detection holds via the S3-equivalent path, but recovery
# specifically is lost) since "caught" for #11 is deliberately designed
# to stay true either way (see _ablation_case_11's docstring).
ABLATIONS = [
    ("12", "onboard_attestation", "S4", _ablation_case_12, "caught"),
    ("11", "trusted_rollback", "S4", _ablation_case_11, "recovered"),
    ("15", "machine_readable_authorization", "S5", _ablation_case_15, "caught"),
]


def run_ablation_study(n_trials: int = N_ABLATION_TRIALS, stack: str = "cfs") -> dict:
    results = {}
    for test_case, mechanism, condition_name, runner, metric in ABLATIONS:
        # Phase 8 red-team fix #7 (2026-08-04): _ablation_case_15
        # deliberately triggers a telemetry mismatch every trial (the
        # attack it's testing), which now freezes the stack's ledger
        # (real enforcement, see version_ledger.freeze()). Clear it
        # before each trial — same reasoning as experiment.py's
        # run_attack_trials — so trial N+1's baseline call doesn't get
        # wrongly rejected by trial N's deliberate mismatch.
        _reset_all_state(stack)
        baseline_trials = []
        for i in range(n_trials):
            version_ledger.unfreeze(stack)
            baseline_trials.append(runner(stack, (), (i * 2 + 1, i * 2 + 2)))
        _reset_all_state(stack)
        ablated_trials = []
        for i in range(n_trials):
            version_ledger.unfreeze(stack)
            ablated_trials.append(runner(stack, (mechanism,), (i * 2 + 1, i * 2 + 2)))

        baseline_rate = sum(1 for t in baseline_trials if t[metric]) / n_trials
        ablated_rate = sum(1 for t in ablated_trials if t[metric]) / n_trials

        results[test_case] = {
            "mechanism_ablated": mechanism,
            "condition": condition_name,
            "metric_judged": metric,
            "baseline_rate": baseline_rate,
            "ablated_rate": ablated_rate,
            "effect_specifically_attributable_to_mechanism": (
                baseline_rate == 1.0 and ablated_rate == 0.0
            ),
            "baseline_trials": baseline_trials,
            "ablated_trials": ablated_trials,
        }
    return results


def print_summary(results: dict) -> None:
    print(f"{'Case':<6}{'Mechanism':<32}{'Cond':<6}{'Metric':<12}{'Baseline':<12}{'Ablated':<12}{'Isolated?'}")
    for test_case, r in results.items():
        print(
            f"#{test_case:<5}{r['mechanism_ablated']:<32}{r['condition']:<6}{r['metric_judged']:<12}"
            f"{r['baseline_rate']*100:>7.0f}%    {r['ablated_rate']*100:>7.0f}%    "
            f"{'yes' if r['effect_specifically_attributable_to_mechanism'] else 'NO'}"
        )


if __name__ == "__main__":
    import json

    stack_arg = sys.argv[1] if len(sys.argv) > 1 else "cfs"
    print(f"Running Phase 8 ablation study ({N_ABLATION_TRIALS} trials per baseline/ablated pair, "
          f"stack={stack_arg})...")
    results = run_ablation_study(stack=stack_arg)
    print_summary(results)

    out_dir = REPO_ROOT / "evaluation" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_name = f"phase8_ablation_{stack_arg}.json"
    with open(out_dir / out_name, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nFull results written to {out_dir / out_name}")
