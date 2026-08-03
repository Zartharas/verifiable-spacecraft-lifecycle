"""
End-to-end pipeline orchestrator.

Phase 1 (S0): build -> sign -> ground authorization -> simulated uplink ->
onboard verification -> installation.

Phase 2 (S1/S2) inserts, condition-gated: provenance generation (S2+),
SBOM generation (S1+), before signing; ground authorization now also
checks SBOM/provenance/version.

Phase 3 (S3/S4) inserts, condition-gated, after onboard verification:
  - S3 (onboard_attestation active, trusted_rollback not yet): simple
    install (as in Phase 1/2), then attestation + health check — but with
    NO recovery mechanism yet. A failure here is logged as unrecoverable
    at this condition, which is itself a meaningful result: S3 tells you
    something is wrong but can't yet do anything about it. That's the
    whole motivation for S4.
  - S4 (trusted_rollback active): full A/B partition flow — write to the
    inactive slot, verify the write landed intact (catches test case #10:
    interrupted installation), tentatively activate, attestation + health
    check, then confirm (permanent) or roll back to the other slot
    (catches test cases #11 failed health, #12 stale attestation, and via
    the rollback path itself, #14 invalid recovery image).

See Pipeline-Flow-Document.md for the full stage-by-stage description.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from build.build import build  # noqa: E402
from signing.signing import sign  # noqa: E402
from ground_authorization.ground_auth import authorize  # noqa: E402
from uplink_sim.uplink import transmit, LinkProfile, IDEAL  # noqa: E402
from onboard_verification.onboard import verify_received_bundle  # noqa: E402
from installation.install import install  # noqa: E402
from installation import partitions  # noqa: E402
from sbom.sbom import generate_sbom  # noqa: E402
from provenance.provenance import generate_provenance  # noqa: E402
from attestation.attestation import generate_attestation, verify_attestation  # noqa: E402
from health.health_check import run_health_check  # noqa: E402
from rollback import rollback  # noqa: E402
from policy.policy import PROHIBITED_CONFIGURATIONS  # noqa: E402,F401 (re-export for tests)
from operational_monitoring import monitoring  # noqa: E402
from evidence_store.authorization_evidence import generate_authorization_evidence  # noqa: E402
from condition import preset  # noqa: E402


class PipelineResult:
    def __init__(self):
        self.build_result = None
        self.sbom_path = None
        self.provenance_path = None
        self.ground_approved = None
        self.onboard_verified = None
        self.installed_path = None
        self.attestation_path = None
        self.health_ok = None
        self.rollback_outcome = None  # "confirmed" | "rolled_back" | "recovery_failed" | None
        self.rejected_at = None
        self.inventory_reconciled = None
        self.telemetry_consistent = None
        self.authorization_evidence_path = None

    def __repr__(self):
        return (
            f"PipelineResult(rejected_at={self.rejected_at!r}, "
            f"ground_approved={self.ground_approved}, "
            f"onboard_verified={self.onboard_verified}, "
            f"installed={self.installed_path is not None}, "
            f"rollback_outcome={self.rollback_outcome!r})"
        )


def _corrupt_binary(binary_path: Path) -> None:
    """Test helper for test case #1 — simulate a binary swapped in after
    provenance/attestation but before release, so the two stop matching."""
    data = bytearray(binary_path.read_bytes())
    data.append(0xFF)
    binary_path.write_bytes(bytes(data))


def run(
    condition_name: str = "S0",
    tamper_in_transit: bool = False,
    version: int = 1,
    builder_id: str = "trusted-ci-runner-01",
    inject_incomplete_sbom: bool = False,
    inject_vulnerable_dependency: bool = False,
    corrupt_binary_after_provenance: bool = False,
    link_profile: LinkProfile = IDEAL,
    rng_seed: Optional[int] = None,
    simulate_interrupted_install: bool = False,
    force_health_fail: bool = False,
    attestation_backdate_seconds: int = 0,
    configuration: Optional[dict] = None,
    claimed_telemetry_success: Optional[bool] = None,
) -> PipelineResult:
    result = PipelineResult()
    cond = preset(condition_name)
    configuration = configuration or {}

    from evidence_store import EvidenceStore as _EvidenceStore

    _run_evidence_start = len(_EvidenceStore().read_all())

    build_result = build(condition_name=condition_name)
    result.build_result = build_result
    binary_path = Path(build_result["binary_path"])

    import hashlib

    artifact_hash = hashlib.sha256(binary_path.read_bytes()).hexdigest()

    prov_path = None
    if cond.active("provenance"):
        prov_path = generate_provenance(
            binary_path, condition_name=condition_name, version=version, builder_id=builder_id
        )
        result.provenance_path = prov_path
        if corrupt_binary_after_provenance:
            _corrupt_binary(binary_path)

    sbom_path = None
    if cond.active("sbom"):
        sbom_path = generate_sbom(
            binary_path,
            condition_name=condition_name,
            inject_incomplete=inject_incomplete_sbom,
            inject_vulnerable_dependency=inject_vulnerable_dependency,
        )
        result.sbom_path = sbom_path

    sig_path = sign(binary_path, condition_name=condition_name)

    approved = authorize(
        binary_path,
        sig_path,
        condition_name=condition_name,
        sbom_path=sbom_path,
        prov_path=prov_path,
        version=version,
        configuration=configuration,
    )
    result.ground_approved = approved
    if not approved:
        result.rejected_at = "ground_authorization"
        return result

    received_binary, received_sig = transmit(
        binary_path,
        sig_path,
        condition_name=condition_name,
        tamper=tamper_in_transit,
        link_profile=link_profile,
        rng_seed=rng_seed,
    )

    verified = verify_received_bundle(received_binary, received_sig, condition_name=condition_name)
    result.onboard_verified = verified
    if not verified:
        result.rejected_at = "onboard_verification"
        if tamper_in_transit:
            # signing.verify() already logged a "fail" record for this
            # rejection, but without a test_case_injected tag (it's a
            # generic signature-mismatch check, not case-#6-specific).
            # Tag the detection explicitly so evaluation/metrics.py's
            # automated comparison table can find it — see Threat-Model.md
            # "Phase 4 results" for why this was missing and worth noting.
            from evidence_store import EvidenceStore

            EvidenceStore().record(
                pipeline_stage="onboard_signature_verification",
                condition=condition_name,
                artifact_ref=artifact_hash,
                actor="onboard_verification_agent",
                result="fail",
                detail={"reason": "test case #6 (modified update in transit) confirmed detected"},
                test_case_injected="6",
            )
        return result

    if cond.active("trusted_rollback"):
        slot, dest = partitions.write_to_inactive(received_binary, version)

        if simulate_interrupted_install:
            with open(dest, "rb") as f:
                data = f.read()
            with open(dest, "wb") as f:
                f.write(data[: len(data) // 2])

        written_ok = partitions.verify_written(slot, condition_name=condition_name)
        if not written_ok:
            result.rejected_at = "installation"
            return result

        partitions.tentative_activate(slot, condition_name=condition_name)
        tentative_path = partitions.get_active_path()

        attestation_ok = True
        if cond.active("onboard_attestation"):
            attestation_path = generate_attestation(
                tentative_path,
                slot,
                condition_name=condition_name,
                backdate_seconds=attestation_backdate_seconds,
            )
            result.attestation_path = attestation_path
            attestation_ok, _ = verify_attestation(
                attestation_path, tentative_path, condition_name=condition_name
            )

        health_ok, _ = run_health_check(
            tentative_path, condition_name=condition_name, force_fail=force_health_fail
        )
        result.health_ok = health_ok

        outcome, reason = rollback.resolve(
            health_ok=health_ok, attestation_ok=attestation_ok, condition_name=condition_name
        )
        result.rollback_outcome = outcome
        result.installed_path = partitions.get_active_path()
        if outcome != "confirmed":
            result.rejected_at = f"post_install_{outcome}"

        if cond.active("machine_readable_authorization"):
            state = partitions._load_state()
            active_slot = state["active"]
            spacecraft_confirmed_version = (
                state[active_slot]["version"] if state[active_slot]["confirmed"] else None
            )

            _, _ = monitoring.reconcile_inventory(
                ground_expected_version=version,
                spacecraft_confirmed_version=spacecraft_confirmed_version,
                artifact_hash=artifact_hash,
                condition_name=condition_name,
            )
            result.inventory_reconciled = spacecraft_confirmed_version == version

            actual_confirmed = outcome == "confirmed"
            claimed = (
                claimed_telemetry_success
                if claimed_telemetry_success is not None
                else actual_confirmed
            )
            telemetry_ok, _ = monitoring.check_telemetry(
                claimed_success=claimed,
                actual_confirmed=actual_confirmed,
                artifact_hash=artifact_hash,
                condition_name=condition_name,
            )
            result.telemetry_consistent = telemetry_ok

            this_run_records = _EvidenceStore().read_all()[_run_evidence_start:]
            result.authorization_evidence_path = generate_authorization_evidence(
                artifact_hash, this_run_records, condition_name=condition_name
            )

        return result

    elif cond.active("onboard_attestation"):
        # S3 only: attestation + health checked, but no recovery
        # mechanism exists yet at this condition — see module docstring.
        installed_path = install(received_binary, condition_name=condition_name)
        result.installed_path = installed_path

        attestation_path = generate_attestation(
            installed_path,
            "single",
            condition_name=condition_name,
            backdate_seconds=attestation_backdate_seconds,
        )
        result.attestation_path = attestation_path
        attestation_ok, _ = verify_attestation(
            attestation_path, installed_path, condition_name=condition_name
        )
        health_ok, _ = run_health_check(
            installed_path, condition_name=condition_name, force_fail=force_health_fail
        )
        result.health_ok = health_ok
        if not (attestation_ok and health_ok):
            result.rejected_at = "post_install_unrecoverable_at_s3"
        return result

    else:
        installed_path = install(received_binary, condition_name=condition_name)
        result.installed_path = installed_path
        return result


if __name__ == "__main__":
    print("=== S0 happy path (no tampering) ===")
    r1 = run(condition_name="S0", tamper_in_transit=False, version=1)
    print(r1)

    print("\n=== S0 test case #6: modified update in transit ===")
    r2 = run(condition_name="S0", tamper_in_transit=True, version=2)
    print(r2)

    print("\n=== S2 happy path (SBOM + provenance active) ===")
    r3 = run(condition_name="S2", version=3)
    print(r3)

    print("\n=== S4 happy path (A/B rollback active) ===")
    r4 = run(condition_name="S4", version=4)
    print(r4)

    print("\n=== S5 happy path (full machine-readable authorization evidence) ===")
    r5 = run(condition_name="S5", version=5)
    print(r5)
    print(f"authorization evidence written to: {r5.authorization_evidence_path}")
