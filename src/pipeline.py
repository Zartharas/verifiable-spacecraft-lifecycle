"""
End-to-end pipeline orchestrator.

Phase 1 (S0): build -> sign -> ground authorization -> simulated uplink ->
onboard verification -> installation.

Phase 2 (S1/S2) inserts, condition-gated via condition.py:
  build -> [provenance generation, S2+] -> [SBOM generation, S1+] ->
  sign -> ground authorization (now also checks SBOM/provenance/version) ->
  simulated uplink -> onboard verification -> installation

Later phases add attestation/health/rollback (after installation) as those
mechanisms come online — see Pipeline-Flow-Document.md.
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
from sbom.sbom import generate_sbom  # noqa: E402
from provenance.provenance import generate_provenance  # noqa: E402
from condition import preset  # noqa: E402


class PipelineResult:
    def __init__(self):
        self.build_result = None
        self.sbom_path = None
        self.provenance_path = None
        self.ground_approved = None
        self.onboard_verified = None
        self.installed_path = None
        self.rejected_at = None

    def __repr__(self):
        return (
            f"PipelineResult(rejected_at={self.rejected_at!r}, "
            f"ground_approved={self.ground_approved}, "
            f"onboard_verified={self.onboard_verified}, "
            f"installed={self.installed_path is not None})"
        )


def _corrupt_binary(binary_path: Path) -> None:
    """Test helper for test case #1 — simulate a binary swapped in after
    provenance/attestation but before release, so the two stop matching."""
    data = bytearray(binary_path.read_bytes())
    data.append(0xFF)  # append rather than flip, so it also changes length/hash robustly
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
) -> PipelineResult:
    result = PipelineResult()
    cond = preset(condition_name)

    build_result = build(condition_name=condition_name)
    result.build_result = build_result
    binary_path = Path(build_result["binary_path"])

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
        return result

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
