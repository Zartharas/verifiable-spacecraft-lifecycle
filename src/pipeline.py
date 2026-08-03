"""
End-to-end pipeline orchestrator — Phase 1 (S0) scope.

Runs: build -> sign -> ground authorization -> simulated uplink ->
onboard verification -> installation, in that order, per
Pipeline-Flow-Document.md. Later phases add provenance/SBOM generation
(after build, before signing) and attestation/health/rollback (after
installation) as those mechanisms come online.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from build.build import build  # noqa: E402
from signing.signing import sign  # noqa: E402
from ground_authorization.ground_auth import authorize  # noqa: E402
from uplink_sim.uplink import transmit  # noqa: E402
from onboard_verification.onboard import verify_received_bundle  # noqa: E402
from installation.install import install  # noqa: E402


class PipelineResult:
    def __init__(self):
        self.build_result = None
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


def run(condition_name: str = "S0", tamper_in_transit: bool = False) -> PipelineResult:
    result = PipelineResult()

    build_result = build(condition_name=condition_name)
    result.build_result = build_result
    binary_path = Path(build_result["binary_path"])

    sig_path = sign(binary_path, condition_name=condition_name)

    approved = authorize(binary_path, sig_path, condition_name=condition_name)
    result.ground_approved = approved
    if not approved:
        result.rejected_at = "ground_authorization"
        return result

    received_binary, received_sig = transmit(
        binary_path, sig_path, condition_name=condition_name, tamper=tamper_in_transit
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
    print("=== Happy path (no tampering) ===")
    r1 = run(tamper_in_transit=False)
    print(r1)

    print("\n=== Test case #6: modified update in transit ===")
    r2 = run(tamper_in_transit=True)
    print(r2)
