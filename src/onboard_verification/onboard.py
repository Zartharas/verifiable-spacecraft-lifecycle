"""
Onboard signature & policy verification agent — the spacecraft-side check
that runs on a received bundle before installation is permitted.

Phase 1 scope: signature verification only (delegates to signing.verify,
which already logs evidence under actor="onboard_verification_agent").
From S5, this stage also checks machine-readable policy for prohibited
configurations (test case #8) — that hook is a placeholder here until
Phase 4.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from signing.signing import verify as signature_verify  # noqa: E402


def check_prohibited_configuration(condition_name: str) -> bool:
    """
    Placeholder for the S5 machine-readable-policy check (test case #8:
    correct signature but prohibited configuration). Always passes until
    Phase 4 implements real policy evaluation.
    """
    return True  # no prohibited-configuration logic yet — Phase 4


def verify_received_bundle(binary_path: Path, sig_path: Path, condition_name: str = "S0") -> bool:
    signature_ok = signature_verify(
        binary_path,
        sig_path,
        condition_name=condition_name,
        actor="onboard_verification_agent",
    )
    if not signature_ok:
        return False

    if condition_name == "S5" and not check_prohibited_configuration(condition_name):
        return False

    return True
