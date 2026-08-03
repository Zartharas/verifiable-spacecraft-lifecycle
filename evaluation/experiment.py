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

Run with: python3 evaluation/experiment.py
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
from signing.signing import generate_keypair, revoke_current_key, REVOKED_KEYS_PATH  # noqa: E402
from operational_monitoring import monitoring  # noqa: E402
from evidence_store import EvidenceStore  # noqa: E402
from attestation.attestation import DEFAULT_FRESHNESS_SECONDS  # noqa: E402

N_TRIALS = 5

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


def _reset_all_state():
    version_ledger.reset()
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

def happy_path_trials(condition_name: str, n_trials: int = N_TRIALS) -> list[dict]:
    _reset_all_state()
    trials = []
    for i in range(1, n_trials + 1):
        elapsed, result, records = _timed_run(condition_name=condition_name, version=i)
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

def scenario_01(version: int) -> dict:
    elapsed, result, _ = _timed_run(
        condition_name="S2", version=version, corrupt_binary_after_provenance=True
    )
    return {"caught": result.rejected_at == "ground_authorization", "elapsed_seconds": elapsed}


def scenario_02(version: int) -> dict:
    # Mirrors tests/test_phase2_pipeline.py::test_case_02 — S2 requires
    # a valid SBOM too, so one is supplied to isolate the provenance
    # failure specifically (see Threat-Model.md "Phase 2 results").
    from build.build import build as build_stage
    from sbom.sbom import generate_sbom
    from provenance.provenance import generate_provenance
    from ground_authorization.ground_auth import authorize
    from signing.signing import sign

    t0 = time.perf_counter()
    build_result = build_stage(condition_name="S2")
    binary_path = Path(build_result["binary_path"])
    sbom_path = generate_sbom(binary_path, condition_name="S2")
    prov_path = generate_provenance(binary_path, condition_name="S2", version=version)
    prov_path.write_text("")
    sig_path = sign(binary_path, condition_name="S2")
    approved = authorize(
        binary_path, sig_path, condition_name="S2", sbom_path=sbom_path, prov_path=prov_path, version=version
    )
    elapsed = time.perf_counter() - t0
    return {"caught": not approved, "elapsed_seconds": elapsed}


def scenario_03(version: int) -> dict:
    elapsed, result, _ = _timed_run(condition_name="S1", version=version, inject_incomplete_sbom=True)
    return {"caught": result.rejected_at == "ground_authorization", "elapsed_seconds": elapsed}


def scenario_04(version: int) -> dict:
    elapsed, result, _ = _timed_run(condition_name="S1", version=version, inject_vulnerable_dependency=True)
    return {"caught": result.rejected_at == "ground_authorization", "elapsed_seconds": elapsed}


def scenario_05(version: int) -> dict:
    elapsed, result, _ = _timed_run(condition_name="S2", version=version, builder_id="rogue-unregistered-runner")
    return {"caught": result.rejected_at == "ground_authorization", "elapsed_seconds": elapsed}


def scenario_06(version: int) -> dict:
    elapsed, result, _ = _timed_run(condition_name="S0", version=version, tamper_in_transit=True)
    return {"caught": result.rejected_at == "onboard_verification", "elapsed_seconds": elapsed}


def scenario_07(version: int) -> dict:
    generate_keypair()
    revoke_current_key()
    try:
        elapsed, result, _ = _timed_run(condition_name="S0", version=version)
        caught = result.rejected_at == "ground_authorization"
    finally:
        if REVOKED_KEYS_PATH.exists():
            REVOKED_KEYS_PATH.write_text("")
    return {"caught": caught, "elapsed_seconds": elapsed}


def scenario_08(version: int) -> dict:
    elapsed, result, _ = _timed_run(condition_name="S5", version=version, configuration={"debug_mode": True})
    return {"caught": result.rejected_at == "ground_authorization", "elapsed_seconds": elapsed}


def scenario_09(version_pair: tuple[int, int]) -> dict:
    baseline_version, downgrade_version = version_pair
    run(condition_name="S2", version=baseline_version)
    elapsed, result, _ = _timed_run(condition_name="S2", version=downgrade_version)
    return {"caught": result.rejected_at == "ground_authorization", "elapsed_seconds": elapsed}


def scenario_10(version_pair: tuple[int, int]) -> dict:
    baseline_version, attack_version = version_pair
    baseline = run(condition_name="S4", version=baseline_version)
    assert baseline.rollback_outcome == "confirmed"
    elapsed, result, _ = _timed_run(
        condition_name="S4", version=attack_version, simulate_interrupted_install=True
    )
    return {"caught": result.rejected_at == "installation", "elapsed_seconds": elapsed}


def scenario_11(version_pair: tuple[int, int]) -> dict:
    baseline_version, attack_version = version_pair
    baseline = run(condition_name="S4", version=baseline_version)
    assert baseline.rollback_outcome == "confirmed"
    elapsed, result, _ = _timed_run(condition_name="S4", version=attack_version, force_health_fail=True)
    return {"caught": result.rollback_outcome == "rolled_back", "elapsed_seconds": elapsed}


def scenario_12(version_pair: tuple[int, int]) -> dict:
    baseline_version, attack_version = version_pair
    baseline = run(condition_name="S4", version=baseline_version)
    assert baseline.rollback_outcome == "confirmed"
    elapsed, result, _ = _timed_run(
        condition_name="S4",
        version=attack_version,
        attestation_backdate_seconds=DEFAULT_FRESHNESS_SECONDS + 3600,
    )
    return {"caught": result.rollback_outcome == "rolled_back", "elapsed_seconds": elapsed}


def scenario_13(_: int) -> dict:
    t0 = time.perf_counter()
    ok, _reason = monitoring.reconcile_inventory(
        ground_expected_version=2,
        spacecraft_confirmed_version=1,
        artifact_hash="phase5-synthetic-hash-case-13",
        condition_name="S5",
    )
    elapsed = time.perf_counter() - t0
    return {"caught": not ok, "elapsed_seconds": elapsed}


def scenario_14(version_pair: tuple[int, int]) -> dict:
    baseline_version, attack_version = version_pair
    baseline = run(condition_name="S4", version=baseline_version)
    assert baseline.rollback_outcome == "confirmed"
    state = partitions._load_state()
    slot_path = partitions._slot_path(state["active"])
    data = bytearray(slot_path.read_bytes())
    data[0] ^= 0xFF
    slot_path.write_bytes(bytes(data))
    elapsed, result, _ = _timed_run(condition_name="S4", version=attack_version, force_health_fail=True)
    return {"caught": result.rollback_outcome == "recovery_failed", "elapsed_seconds": elapsed}


def scenario_15(version_pair: tuple[int, int]) -> dict:
    baseline_version, attack_version = version_pair
    baseline = run(condition_name="S5", version=baseline_version)
    assert baseline.rollback_outcome == "confirmed"
    elapsed, result, _ = _timed_run(
        condition_name="S5",
        version=attack_version,
        force_health_fail=True,
        claimed_telemetry_success=True,
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
    "13": scenario_13,
}

PAIRED_VERSION_SCENARIOS = {
    "9": scenario_09,
    "10": scenario_10,
    "11": scenario_11,
    "12": scenario_12,
    "14": scenario_14,
    "15": scenario_15,
}

TEST_CASE_CONDITION = {
    "1": "S2", "2": "S2", "3": "S1", "4": "S1", "5": "S2", "6": "S0", "7": "S0",
    "8": "S5", "9": "S2", "10": "S4", "11": "S4", "12": "S4", "13": "S5",
    "14": "S4", "15": "S5",
}


def run_attack_trials(test_case: str, n_trials: int = N_TRIALS) -> list[dict]:
    _reset_all_state()
    trials = []
    for i in range(n_trials):
        if test_case in SINGLE_VERSION_SCENARIOS:
            trials.append(SINGLE_VERSION_SCENARIOS[test_case](i + 1))
        elif test_case == "9":
            # Downgrade attempt: attack_v must be LOWER than baseline_v,
            # and baseline_v must strictly increase each trial so it's
            # accepted as a legitimate upgrade against the ledger's
            # running state (not reset between trials in this loop).
            baseline_v = 100 + i * 10
            attack_v = baseline_v - 5
            trials.append(PAIRED_VERSION_SCENARIOS[test_case]((baseline_v, attack_v)))
        else:
            baseline_v = i * 2 + 1
            attack_v = i * 2 + 2
            trials.append(PAIRED_VERSION_SCENARIOS[test_case]((baseline_v, attack_v)))
    return trials


def run_full_evaluation(n_trials: int = N_TRIALS) -> dict:
    results = {"happy_path": {}, "attack_cases": {}}

    for condition in ALL_CONDITIONS:
        results["happy_path"][condition] = happy_path_trials(condition, n_trials)

    for test_case in sorted(TEST_CASE_CONDITION, key=int):
        results["attack_cases"][test_case] = {
            "condition": TEST_CASE_CONDITION[test_case],
            "trials": run_attack_trials(test_case, n_trials),
        }

    return results


if __name__ == "__main__":
    import json

    print(f"Running Phase 5 evaluation ({N_TRIALS} trials per scenario)...")
    results = run_full_evaluation()

    out_dir = REPO_ROOT / "evaluation" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "phase5_raw_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"Raw results written to {out_dir / 'phase5_raw_results.json'}")
