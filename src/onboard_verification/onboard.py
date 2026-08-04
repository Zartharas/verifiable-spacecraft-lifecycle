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

Phase 8 (2026-08-05), reviewer objection #5 fix: this module now accepts
and applies the same `disable_mechanisms` override as `ground_auth.py`
and `pipeline.py`. Previously it built its own `Condition` via
`preset(condition_name)` alone, so ablating `machine_readable_
authorization` at the pipeline/ground level would leave this redundant
onboard-side check still active — silently catching the attack anyway
and making the ablation study's "mechanism disabled -> attack
undetected" result look wrong for reasons that had nothing to do with
the mechanism actually mattering. Threading the same override through
here keeps both checks consistent with a single ablation decision.
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
from condition import preset, custom as condition_custom  # noqa: E402
from installation import partitions  # noqa: E402
from evidence_store import EvidenceStore  # noqa: E402
from state_integrity import StateIntegrityError  # noqa: E402


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


def check_independent_downgrade(version: Optional[int]) -> tuple[bool, Optional[str]]:
    """Second red-team pass, finding #3 (2026-08-05): downgrade
    protection (test case #9) was enforced only via
    `version_ledger.check_and_advance()`, called only from
    `ground_auth.authorize()` — the same class of gap already closed for
    the S5 policy check (Phase 8 finding #4): if ground authorization is
    bypassed, compromised, or fed different data than what's actually
    transmitted, the spacecraft had zero independent fallback defense
    against a downgrade.

    This checks the new bundle's `version` against the spacecraft's own
    currently-confirmed partition state — data ground never controls
    directly and that already exists onboard independently of anything
    ground_auth.py decided for this release. Only meaningful once
    `trusted_rollback` is active (S4+): before that, `install()` doesn't
    use partition state at all, so there's no independent onboard-side
    version record to compare against — consistent with the S3-vs-S4
    distinction already documented elsewhere in this project (detection
    capability grows with the mechanisms actually active at that
    condition, not claimed uniformly across all of them).

    Fails closed on a partition-state integrity failure: this call
    happens during onboard verification, which runs before pipeline.py's
    own trusted_rollback try/except block — letting
    `state_integrity.StateIntegrityError` propagate here would crash
    `pipeline.run()` outright (no `PipelineResult` returned at all)
    instead of the established "tampered state -> denied, never crash"
    pattern used everywhere else this project checks integrity-protected
    state (version_ledger, signing/attestation revocation lists)."""
    if version is None:
        return True, None
    try:
        state = partitions._load_state()
    except StateIntegrityError:
        return False, "partition state integrity check failed — cannot verify against a trusted baseline"
    active = state.get("active")
    if active is None:
        return True, None  # nothing confirmed onboard yet -- no baseline to compare against
    active_record = state.get(active, {})
    if not active_record.get("confirmed"):
        return True, None
    confirmed_version = active_record.get("version")
    if confirmed_version is not None and version < confirmed_version:
        return False, (
            f"new version {version} is lower than the spacecraft's own "
            f"currently-confirmed version {confirmed_version}"
        )
    return True, None


def verify_received_bundle(
    binary_path: Path,
    sig_path: Path,
    condition_name: str = "S0",
    configuration: Optional[dict] = None,
    version: Optional[int] = None,
    disable_mechanisms: tuple = (),
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
    if disable_mechanisms:
        cond = condition_custom(cond, disable=disable_mechanisms)

    if cond.active("trusted_rollback"):
        downgrade_ok, _ = check_independent_downgrade(version)
        if not downgrade_ok:
            with open(binary_path, "rb") as f:
                artifact_hash = hashlib.sha256(f.read()).hexdigest()
            EvidenceStore().record(
                pipeline_stage="onboard_verification",
                condition=condition_name,
                artifact_ref=artifact_hash,
                actor="onboard_verification_agent",
                result="fail",
                detail={"reason": "independent onboard downgrade check failed", "version": version},
                test_case_injected="9",
            )
            return False

    if cond.active("machine_readable_authorization"):
        with open(binary_path, "rb") as f:
            artifact_hash = hashlib.sha256(f.read()).hexdigest()
        config_ok, _ = check_prohibited_configuration(
            configuration or {}, artifact_hash, condition_name
        )
        if not config_ok:
            return False

    return True
