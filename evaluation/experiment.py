"""
Phase 5 evaluation harness — runs repeated trials of the happy path (per
condition) and every attack matrix test case (at its expected condition),
capturing timing, detection outcomes, and artifact sizes, then hands the
raw results to metrics.py for aggregation.

Baseline/metric definitions are documented in docs/PRD.md § 10 — read
that before interpreting any number this script produces. In particular:
timing metrics are a sandbox-timing proxy (not hardware/real-mission
timing), and "manual evidence-processing effort" is evidence-record count
(not measured human time).

Methodological note (worth remembering for future Claude sessions): the
stand-in stub artifact's source never changes, so its build hash is
IDENTICAL across every trial and every condition. That means
`EvidenceStore.for_artifact(hash)` cannot be used to isolate "this one
run's evidence" — it will return every record ever logged for that hash
across the whole evaluation. This script isolates per-run evidence by
recording the evidence log's record count before and after each
`pipeline.run()` call and slicing by index instead. This is the same
category of trap the Phase 4 comparison table surfaced (see
Threat-Model.md "Phase 4 results") — evidence-store-based analysis needs
to be designed around what's actually unique per run, not assumed.

Phase 6 (generalizability): every function here takes a `stack` parameter
(default `"cfs"`, Phases 1-5's stand-in) so the exact same harness can be
re-run against `stack="fprime"` (see `src/target_stack.py`,
`fprime-app/README.md`) with zero duplicated logic. `_reset_all_state()`
resets the given stack's version ledger specifically — a second real bug
was found here too: the version ledger used to be one global file shared
across stacks, so approving version 1 for `fprime` right after `cfs` had
already advanced past version 1 would have been wrongly flagged as a
downgrade attempt. Fixed in `src/ground_authorization/version_ledger.py`
by keying the ledger file by stack — see Threat-Model.md "Phase 6
results" for the full writeup.

Run with: python3 evaluation/experiment.py             # cfs (Phase 5, unchanged)
          python3 evaluation/experiment.py fprime       # fprime (Phase 6)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from pipeline import run  # noqa: E402
from ground_authorization import version_ledger  # noqa: E402
from installation import partitions  # noqa: E402
from signing.signing import generate_keypair, revoke_current_key, reset_revocation_list  # noqa: E402
from evidence_store import EvidenceStore  # noqa: E402
from attestation.attestation import DEFAULT_FRESHNESS_SECONDS  # noqa: E402

N_TRIALS = 30
# Phase 8 (2026-08-03): bumped from 5 to 30 per the rejection-risk review
# in docs/Research-Paper-Outline.md — 5 trials was too thin to support a
# reported confidence interval with any real precision. report.py now
# computes Wilson score intervals for rates and normal-approximation CIs
# for timing means; see its module docstring for why those specific
# methods were chosen. The pipeline itself is close to deterministic
# (little real stochastic variance beyond real-binary boot timing), which
# is the actual justification for 30 being sufficient rather than needing
# hundreds of trials — stated explicitly here rather than left implicit.

ALL_CONDITIONS = ["S0", "S1", "S2", "S3", "S4", "S5"]

# Which pipeline stages are expected to produce evidence at each
# condition, for the happy path (no attack) — used for traceability
# completeness. Derived from condition.py's mechanism flags, not guessed.
EXPECTED_STAGES = {
    "S0": ["build", "signing", "ground_authorization", "uplink", "onboard_signature_verification", "installation"],
    "S1": ["build", "sbom_generation", "signing", "sbom_verification", "ground_authorization", "uplink", "onboard_signature_verification", "installation"],
    "S2": ["build", "provenance_generation", "sbom_generation", "signing", "sbom_verification", "provenance_verification", "ground_authorization", "uplink", "onboard_signature_verification", "installation"],
    "S3": ["build", "provenance_generation", "sbom_generation", "signing", "sbom_verification", "provenance_verification", "ground_authorization", "uplink", "onboard_signature_verification", "installation", "boot_attestation", "attestation_verification", "health_validation"],
    "S4": ["build", "provenance_generation", "sbom_generation", "signing", "sbom_verification", "provenance_verification", "ground_authorization", "uplink", "onboard_signature_verification", "installation", "boot_attestation", "attestation_verification", "health_validation", "operational_monitoring"],
    "S5": ["build", "provenance_generation", "sbom_generation", "signing", "sbom_verification", "provenance_verification", "configuration_policy_check", "ground_authorization", "uplink", "onboard_signature_verification", "installation", "boot_attestation", "attestation_verification", "health_validation", "operational_monitoring", "inventory_reconciliation", "authorization_evidence_generation"],
}


def _reset_all_state(stack: str = "cfs"):
    version_ledger.reset(stack)
    partitions.reset()


def _records_since(store: EvidenceStore, start_count: int) -> list[dict]:
    return store.read_all()[start_count:]


def _timed_run(**kwargs) -> tuple[float, "PipelineResult", list[dict]]:
    store = EvidenceStore()
    start_count = len(store.read_all())
    t0 = time.perf_counter()
    result = run(**kwargs)
    elapsed = time.perf_counter() - t0
    records = _records_since(store, start_count)
    return elapsed, result, records


# --- Happy path per condition -------------------------------------------

def happy_path_trials(condition_name: str, n_trials: int = N_TRIALS, stack: str = "cfs") -> list[dict]:
    _reset_all_state(stack)
    trials = []
    for i in range(1, n_trials + 1):
        elapsed, result, records = _timed_run(condition_name=condition_name, version=i, stack=stack)
        stages_present = {r["pipeline_stage"] for r in records}
        expected = set(EXPECTED_STAGES[condition_name])
        attestation_ages = [
            r["detail"]["age_seconds"]
            for r in records
            if r["pipeline_stage"] == "attestation_verification" and "age_seconds" in r["detail"]
        ]
        trials.append(
            {
                "attestation_age_seconds": attestation_ages[0] if attestation_ages else None,
                "elapsed_seconds": elapsed,
                "success": result.rejected_at is None,
                "reproducible": result.build_result["reproducible"],
                "record_count": len(records),
                "traceability_completeness": len(stages_present & expected) / len(expected),
                "sbom_size": result.sbom_path.stat().st_size if result.sbom_path else 0,
                "provenance_size": result.provenance_path.stat().st_size if result.provenance_path else 0,
                "attestation_size": result.attestation_path.stat().st_size if result.attestation_path else 0,
                "authorization_evidence_size": (
                    result.authorization_evidence_path.stat().st_size
                    if result.authorization_evidence_path
                    else 0
                ),
            }
        )
    return trials


# --- Attack scenarios, one function per test case -----------------------
# Each returns a dict: {"caught": bool, "elapsed_seconds": float, **extra}

def scenario_01(version: int, stack: str = "cfs") -> dict:
    elapsed, result, _ = _timed_run(
        condition_name="S2", version=version, corrupt_binary_after_provenance=True, stack=stack
    )
    return {"caught": result.rejected_at == "ground_authorization", "elapsed_seconds": elapsed}


def scenario_02(version: int, stack: str = "cfs") -> dict:
    # Mirrors tests/test_phase2_pipeline.py::test_case_02 — S2 requires
    # a valid SBOM too, so one is supplied to isolate the provenance
    # failure specifically (see Threat-Model.md "Phase 2 results").
    from build.build import build as build_stage
    from sbom.sbom import generate_sbom
    from provenance.provenance import generate_provenance
    from ground_authorization.ground_auth import authorize
    from signing.signing import sign

    t0 = time.perf_counter()
    build_result = build_stage(condition_name="S2", stack=stack)
    binary_path = Path(build_result["binary_path"])
    sbom_path = generate_sbom(binary_path, condition_name="S2")
    prov_path = generate_provenance(binary_path, condition_name="S2", version=version)
    prov_path.write_text("")
    sig_path = sign(binary_path, condition_name="S2")
    approved = authorize(
        binary_path,
        sig_path,
        condition_name="S2",
        sbom_path=sbom_path,
        prov_path=prov_path,
        version=version,
        stack=stack,
    )
    elapsed = time.perf_counter() - t0
    return {"caught": not approved, "elapsed_seconds": elapsed}


def scenario_03(version: int, stack: str = "cfs") -> dict:
    elapsed, result, _ = _timed_run(
        condition_name="S1", version=version, inject_incomplete_sbom=True, stack=stack
    )
    return {"caught": result.rejected_at == "ground_authorization", "elapsed_seconds": elapsed}


def scenario_04(version: int, stack: str = "cfs") -> dict:
    elapsed, result, _ = _timed_run(
        condition_name="S1", version=version, inject_vulnerable_dependency=True, stack=stack
    )
    return {"caught": result.rejected_at == "ground_authorization", "elapsed_seconds": elapsed}


def scenario_05(version: int, stack: str = "cfs") -> dict:
    elapsed, result, _ = _timed_run(
        condition_name="S2", version=version, builder_id="rogue-unregistered-runner", stack=stack
    )
    return {"caught": result.rejected_at == "ground_authorization", "elapsed_seconds": elapsed}


def scenario_06(version: int, stack: str = "cfs") -> dict:
    elapsed, result, _ = _timed_run(
        condition_name="S0", version=version, tamper_in_transit=True, stack=stack
    )
    return {"caught": result.rejected_at == "onboard_verification", "elapsed_seconds": elapsed}


def scenario_07(version: int, stack: str = "cfs") -> dict:
    generate_keypair()
    revoke_current_key()
    try:
        elapsed, result, _ = _timed_run(condition_name="S0", version=version, stack=stack)
        caught = result.rejected_at == "ground_authorization"
    finally:
        # Phase 8 red-team fix #2 (2026-08-04): must go through
        # reset_revocation_list(), not a raw write_text() — the
        # revocation list is now integrity-protected
        # (src/state_integrity.py), and writing its content directly
        # without updating the HMAC sidecar would make every subsequent
        # is_revoked() call fail closed (treat every key as revoked) for
        # the rest of the evaluation run, exactly the fail-closed
        # behavior the fix is supposed to have, but not what this
        # cleanup step intends.
        reset_revocation_list()
    return {"caught": caught, "elapsed_seconds": elapsed}


def scenario_08(version: int, stack: str = "cfs") -> dict:
    elapsed, result, _ = _timed_run(
        condition_name="S5", version=version, configuration={"debug_mode": True}, stack=stack
    )
    return {"caught": result.rejected_at == "ground_authorization", "elapsed_seconds": elapsed}


def scenario_09(version_pair: tuple[int, int], stack: str = "cfs") -> dict:
    baseline_version, downgrade_version = version_pair
    run(condition_name="S2", version=baseline_version, stack=stack)
    elapsed, result, _ = _timed_run(condition_name="S2", version=downgrade_version, stack=stack)
    return {"caught": result.rejected_at == "ground_authorization", "elapsed_seconds": elapsed}


def scenario_10(version_pair: tuple[int, int], stack: str = "cfs") -> dict:
    baseline_version, attack_version = version_pair
    baseline = run(condition_name="S4", version=baseline_version, stack=stack)
    assert baseline.rollback_outcome == "confirmed", (
        f"baseline run did not confirm as expected (stack={stack!r}, "
        f"condition=S4, version={baseline_version}): "
        f"rollback_outcome={baseline.rollback_outcome!r}, "
        f"health_ok={baseline.health_ok!r}, rejected_at={baseline.rejected_at!r}"
    )
    elapsed, result, _ = _timed_run(
        condition_name="S4", version=attack_version, simulate_interrupted_install=True, stack=stack
    )
    return {"caught": result.rejected_at == "installation", "elapsed_seconds": elapsed}


def scenario_11(version_pair: tuple[int, int], stack: str = "cfs") -> dict:
    baseline_version, attack_version = version_pair
    baseline = run(condition_name="S4", version=baseline_version, stack=stack)
    assert baseline.rollback_outcome == "confirmed", (
        f"baseline run did not confirm as expected (stack={stack!r}, "
        f"condition=S4, version={baseline_version}): "
        f"rollback_outcome={baseline.rollback_outcome!r}, "
        f"health_ok={baseline.health_ok!r}, rejected_at={baseline.rejected_at!r}"
    )
    elapsed, result, _ = _timed_run(
        condition_name="S4", version=attack_version, force_health_fail=True, stack=stack
    )
    return {"caught": result.rollback_outcome == "rolled_back", "elapsed_seconds": elapsed}


def scenario_12(version_pair: tuple[int, int], stack: str = "cfs") -> dict:
    baseline_version, attack_version = version_pair
    baseline = run(condition_name="S4", version=baseline_version, stack=stack)
    assert baseline.rollback_outcome == "confirmed", (
        f"baseline run did not confirm as expected (stack={stack!r}, "
        f"condition=S4, version={baseline_version}): "
        f"rollback_outcome={baseline.rollback_outcome!r}, "
        f"health_ok={baseline.health_ok!r}, rejected_at={baseline.rejected_at!r}"
    )
    elapsed, result, _ = _timed_run(
        condition_name="S4",
        version=attack_version,
        attestation_backdate_seconds=DEFAULT_FRESHNESS_SECONDS + 3600,
        stack=stack,
    )
    return {"caught": result.rollback_outcome == "rolled_back", "elapsed_seconds": elapsed}


def scenario_13(version_pair: tuple[int, int], stack: str = "cfs") -> dict:
    """Test case #13 (inventory disagreement between ground and
    spacecraft).

    Second red-team pass, finding #7 (2026-08-05): this used to call
    `monitoring.reconcile_inventory()` directly with hardcoded,
    deliberately-mismatched constants (`ground_expected_version=2`,
    `spacecraft_confirmed_version=1`, a synthetic hash string) — never
    driving the check through a real `pipeline.run()`. That guaranteed
    "100% detection" for this test case by construction, regardless of
    whether the ladder's actual inventory-reconciliation code path works;
    it demonstrated that `reconcile_inventory()` itself can tell two
    different numbers apart, not that the pipeline produces a genuine
    disagreement when something really does go wrong.

    Rewritten to produce the mismatch for real: a confirmed baseline
    install, then a forced health-check failure causes a genuine
    rollback back to the baseline slot — so ground's own `version`
    argument for this call (`attack_version`) genuinely disagrees with
    what the spacecraft actually ends up confirming
    (`baseline_version`), through `pipeline.py`'s own
    `reconcile_inventory()` call, not a hand-fed pair of constants. This
    is the same underlying real attack `scenario_15` uses (a forced
    rollback at S5) — the two test cases now correctly share one real
    mechanism trigger while checking two independently-meaningful result
    fields (`inventory_reconciled` here, `telemetry_consistent` there)."""
    baseline_version, attack_version = version_pair
    baseline = run(condition_name="S5", version=baseline_version, stack=stack)
    assert baseline.rollback_outcome == "confirmed", (
        f"baseline run did not confirm as expected (stack={stack!r}, "
        f"condition=S5, version={baseline_version}): "
        f"rollback_outcome={baseline.rollback_outcome!r}, "
        f"health_ok={baseline.health_ok!r}, rejected_at={baseline.rejected_at!r}"
    )
    elapsed, result, _ = _timed_run(
        condition_name="S5", version=attack_version, force_health_fail=True, stack=stack
    )
    return {"caught": result.inventory_reconciled is False, "elapsed_seconds": elapsed}


def scenario_14(version_pair: tuple[int, int], stack: str = "cfs") -> dict:
    baseline_version, attack_version = version_pair
    baseline = run(condition_name="S4", version=baseline_version, stack=stack)
    assert baseline.rollback_outcome == "confirmed", (
        f"baseline run did not confirm as expected (stack={stack!r}, "
        f"condition=S4, version={baseline_version}): "
        f"rollback_outcome={baseline.rollback_outcome!r}, "
        f"health_ok={baseline.health_ok!r}, rejected_at={baseline.rejected_at!r}"
    )
    state = partitions._load_state()
    slot_path = partitions._slot_path(state["active"])
    data = bytearray(slot_path.read_bytes())
    data[0] ^= 0xFF
    slot_path.write_bytes(bytes(data))
    elapsed, result, _ = _timed_run(
        condition_name="S4", version=attack_version, force_health_fail=True, stack=stack
    )
    return {"caught": result.rollback_outcome == "recovery_failed", "elapsed_seconds": elapsed}


def scenario_15(version_pair: tuple[int, int], stack: str = "cfs") -> dict:
    baseline_version, attack_version = version_pair
    baseline = run(condition_name="S5", version=baseline_version, stack=stack)
    assert baseline.rollback_outcome == "confirmed", (
        f"baseline run did not confirm as expected (stack={stack!r}, "
        f"condition=S5, version={baseline_version}): "
        f"rollback_outcome={baseline.rollback_outcome!r}, "
        f"health_ok={baseline.health_ok!r}, rejected_at={baseline.rejected_at!r}"
    )
    elapsed, result, _ = _timed_run(
        condition_name="S5",
        version=attack_version,
        force_health_fail=True,
        claimed_telemetry_success=True,
        stack=stack,
    )
    return {"caught": result.telemetry_consistent is False, "elapsed_seconds": elapsed}


SINGLE_VERSION_SCENARIOS = {
    "1": scenario_01,
    "2": scenario_02,
    "3": scenario_03,
    "4": scenario_04,
    "5": scenario_05,
    "6": scenario_06,
    "7": scenario_07,
    "8": scenario_08,
}

PAIRED_VERSION_SCENARIOS = {
    "9": scenario_09,
    "10": scenario_10,
    "11": scenario_11,
    "12": scenario_12,
    "13": scenario_13,
    "14": scenario_14,
    "15": scenario_15,
}

TEST_CASE_CONDITION = {
    "1": "S2", "2": "S2", "3": "S1", "4": "S1", "5": "S2", "6": "S0", "7": "S0",
    "8": "S5", "9": "S2", "10": "S4", "11": "S4", "12": "S4", "13": "S5",
    "14": "S4", "15": "S5",
}


def run_attack_trials(test_case: str, n_trials: int = N_TRIALS, stack: str = "cfs") -> list[dict]:
    _reset_all_state(stack)
    trials = []
    for i in range(n_trials):
        # Phase 8 red-team fix #7 (2026-08-04) added real enforcement:
        # a detected operational-monitoring mismatch (test cases #13/#15)
        # now freezes the stack's ledger until an operator clears it —
        # see version_ledger.freeze()/unfreeze(). Deliberately triggering
        # that mismatch every trial (which is exactly what #13/#15's
        # scenarios do, on purpose) would otherwise freeze the stack on
        # trial 1 and silently corrupt every subsequent trial in this
        # loop (they'd get rejected at ground_authorization instead of
        # ever reaching the mechanism actually under test). Each trial
        # here models an independent release attempt, so clear any prior
        # trial's freeze before running the next one — this is a
        # test-harness modeling choice, not something a real deployment
        # would do automatically (a real freeze stays until a human
        # operator reviews it).
        version_ledger.unfreeze(stack)
        if test_case in SINGLE_VERSION_SCENARIOS:
            trials.append(SINGLE_VERSION_SCENARIOS[test_case](i + 1, stack=stack))
        elif test_case == "9":
            # Downgrade attempt: attack_v must be LOWER than baseline_v,
            # and baseline_v must strictly increase each trial so it's
            # accepted as a legitimate upgrade against the ledger's
            # running state (not reset between trials in this loop).
            baseline_v = 100 + i * 10
            attack_v = baseline_v - 5
            trials.append(PAIRED_VERSION_SCENARIOS[test_case]((baseline_v, attack_v), stack=stack))
        else:
            baseline_v = i * 2 + 1
            attack_v = i * 2 + 2
            trials.append(PAIRED_VERSION_SCENARIOS[test_case]((baseline_v, attack_v), stack=stack))
    return trials


def run_full_evaluation(n_trials: int = N_TRIALS, stack: str = "cfs") -> dict:
    results = {"happy_path": {}, "attack_cases": {}}

    for condition in ALL_CONDITIONS:
        results["happy_path"][condition] = happy_path_trials(condition, n_trials, stack=stack)

    for test_case in sorted(TEST_CASE_CONDITION, key=int):
        results["attack_cases"][test_case] = {
            "condition": TEST_CASE_CONDITION[test_case],
            "trials": run_attack_trials(test_case, n_trials, stack=stack),
        }

    return results


if __name__ == "__main__":
    import json

    stack_arg = sys.argv[1] if len(sys.argv) > 1 else "cfs"
    print(f"Running Phase {'5' if stack_arg == 'cfs' else '6'} evaluation "
          f"({N_TRIALS} trials per scenario, stack={stack_arg})...")
    results = run_full_evaluation(stack=stack_arg)

    out_dir = REPO_ROOT / "evaluation" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_name = "phase5_raw_results.json" if stack_arg == "cfs" else f"phase6_raw_results_{stack_arg}.json"
    with open(out_dir / out_name, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"Raw results written to {out_dir / out_name}")
