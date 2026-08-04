"""
Onboard signature & policy verification agent — the spacecraft-side check
that runs on a received bundle before installation is permitted.

Phase 1 scope: signature verification only (delegates to signing.verify,
which already logs evidence under actor="onboard_verification_agent").

Phase 8 red-team fix (2026-08-04), finding #4 (see Threat-Model.md "Phase
8 independent (blind, AI) red-team review"): `check_prohibited_
configuration()` was a permanent dead stub (`return True` unconditionally)
with a comment saying it was a placeholder "until Phase 4" — but Phase 4
*did* implement real policy evaluation (`policy.check_configuration`), it
was only ever wired into ground-side `authorize()`, never back into this
onboard stub. That meant the spacecraft had no independent ability to
reject a prohibited configuration if ground authorization was bypassed,
compromised, or fed different data than what was actually deployed.

A second, compounding bug in the same finding: the gate that even called
the (useless) stub was `if condition_name == "S5"` — a literal string
match against the condition's *name*, not
`cond.active("machine_readable_authorization")` — so any condition
object whose `.name` wasn't literally the string `"S5"` would silently
skip the check regardless of whether the mechanism itself was active.
Fixed by building a real `Condition` via `condition.preset()` (mirroring
`ground_authorization/ground_auth.py`'s own pattern) and gating on the
mechanism flag directly.

Scope boundary, stated honestly, mirroring the one already documented for
`ground_auth.py`'s own policy check in Threat-Model.md's Phase 8 ablation
section: this builds its own `Condition` via `preset(condition_name)`,
independent of any `disable_mechanisms` override passed to
`pipeline.py`'s `run()`. This is consistent with the existing, deliberate
scope decision (the S5 policy check is not covered by the mechanism-
ablation study), not a new gap introduced by this fix.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from signing.signing import verify as signature_verify  # noqa: E402
from policy.policy import check_configuration  # noqa: E402
from condition import preset  # noqa: E402


def check_prohibited_configuration(
    configuration: dict, artifact_hash: str, condition_name: str
) -> tuple[bool, Optional[str]]:
    """S5 machine-readable-policy check (test case #8: correct signature
    but prohibited configuration) — onboard side. Delegates to the same
    `policy.check_configuration` ground authorization uses, so the
    spacecraft has an independent ability to reject a prohibited
    configuration even if ground authorization is bypassed or fed
    different data than what's actually deployed (Phase 8 finding #4)."""
    return check_configuration(configuration, artifact_hash, condition_name=condition_name)


def verify_received_bundle(
    binary_path: Path,
    sig_path: Path,
    condition_name: str = "S0",
    configuration: Optional[dict] = None,
) -> bool:
    signature_ok = signature_verify(
        binary_path,
        sig_path,
        condition_name=condition_name,
        actor="onboard_verification_agent",
    )
    if not signature_ok:
        return False

    cond = preset(condition_name)
    if cond.active("machine_readable_authorization"):
        with open(binary_path, "rb") as f:
            artifact_hash = hashlib.sha256(f.read()).hexdigest()
        config_ok, _ = check_prohibited_configuration(
            configuration or {}, artifact_hash, condition_name
        )
        if not config_ok:
            return False

    return True
