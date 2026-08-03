"""
Phase 1 (S0) pipeline tests.

Covers the Phase 1 exit criteria from Implementation-Plan.md: a clean run
of test case #6 (modified update in transit) is correctly rejected by
signature verification, with an evidence record showing the rejection.
Also covers the reproducible-build property and a happy-path smoke test.

Run with: pytest tests/test_phase1_pipeline.py -v
(run from the repo root so the sys.path insertions in src/ modules resolve)
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from build.build import build  # noqa: E402
from evidence_store import EvidenceStore  # noqa: E402
from pipeline import run  # noqa: E402
from signing.signing import revoke_current_key, generate_keypair  # noqa: E402


def test_build_is_reproducible():
    result = build()
    assert result["reproducible"] is True


def test_happy_path_installs_successfully():
    result = run(tamper_in_transit=False)
    assert result.ground_approved is True
    assert result.onboard_verified is True
    assert result.installed_path is not None
    assert result.rejected_at is None


def test_case_06_modified_update_in_transit_is_rejected():
    """Attack matrix test case #6 — Threat-Model.md row 6."""
    result = run(tamper_in_transit=True)
    assert result.ground_approved is True  # ground never sees the tampering
    assert result.onboard_verified is False  # onboard signature check catches it
    assert result.installed_path is None
    assert result.rejected_at == "onboard_verification"

    # Evidence trail must show the rejection explicitly.
    store = EvidenceStore()
    records = store.read_all()
    rejections = [
        r
        for r in records
        if r["pipeline_stage"] == "onboard_signature_verification"
        and r["result"] == "fail"
    ]
    assert len(rejections) >= 1, "expected a logged rejection evidence record"


def test_case_07_revoked_key_is_rejected():
    """
    Attack matrix test case #7 — Threat-Model.md row 7 (revoked signing key).

    Both ground_authorization and onboard_verification call the same
    revocation-aware signature check in this implementation, so a revoked
    key is caught at the first gate (ground_authorization) rather than
    reaching onboard verification. That's an earlier catch than the
    Threat-Model.md hypothesis of "S0/S2" — worth noting as a result, not
    a bug: rejecting earlier is strictly better, not worse.
    """
    generate_keypair()
    revoke_current_key()
    try:
        result = run(tamper_in_transit=False)
        assert result.ground_approved is False
        assert result.rejected_at == "ground_authorization"
    finally:
        # Clean up so this test doesn't poison later runs / other tests.
        revoked_file = REPO_ROOT / "keys" / "revoked_keys.txt"
        if revoked_file.exists():
            revoked_file.write_text("")
