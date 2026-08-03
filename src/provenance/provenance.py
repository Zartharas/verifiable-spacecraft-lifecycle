"""
Provenance generation and verification — S2 assurance mechanism.

SLSA/in-toto-shaped provenance attestation linking: binary hash -> source
commit -> build environment -> builder identity -> version. Hand-rolled
JSON rather than a full in-toto/SLSA library invocation, for the same
reason as sbom.py: the stand-in artifact's build is trivial, and the
schema shape here is what matters for testing the assurance-ladder
comparison, not conformance to the full in-toto spec. Swap in a real
SLSA provenance generator once pointed at the real cFS build.

Covers attack matrix test cases:
  #1 — binary does not match source (provenance binary-hash mismatch)
  #2 — missing or false provenance
  #5 — unauthorized build runner (builder_id not in allowlist)
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_store import EvidenceStore  # noqa: E402

PROVENANCE_DIR = REPO_ROOT / "work" / "provenance"

# Test-only allowlist for test case #5. In a real system this would be a
# ground-side registry of authorized build runner identities/certificates.
ALLOWED_BUILDER_IDS = {"trusted-ci-runner-01"}


def _current_source_commit() -> str:
    """
    The pinned "source" identity for provenance purposes: this repo's own
    current commit (the stub artifact lives inside this repo). Falls back
    to a placeholder if not in a git repo / no commits yet (e.g. very
    first run before any commit exists).
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown-no-git-history"


def generate_provenance(
    binary_path: Path,
    condition_name: str = "S2",
    version: int = 1,
    builder_id: str = "trusted-ci-runner-01",
) -> Path:
    store = EvidenceStore()
    with open(binary_path, "rb") as f:
        artifact_hash = hashlib.sha256(f.read()).hexdigest()

    provenance = {
        "_type": "https://in-toto.io/Statement/v1",
        "predicateType": "https://slsa.dev/provenance/v1",
        "subject": [{"name": binary_path.name, "digest": {"sha256": artifact_hash}}],
        "predicate": {
            "buildDefinition": {
                "buildType": "verifiable-spacecraft-lifecycle/phase1-gcc-build",
                "externalParameters": {"source_commit": _current_source_commit()},
            },
            "runDetails": {
                "builder": {"id": builder_id},
                "metadata": {"version": version},
            },
        },
    }

    PROVENANCE_DIR.mkdir(parents=True, exist_ok=True)
    prov_path = PROVENANCE_DIR / f"{binary_path.name}.provenance.json"
    with open(prov_path, "w") as f:
        json.dump(provenance, f, indent=2)

    store.record(
        pipeline_stage="provenance_generation",
        condition=condition_name,
        artifact_ref=artifact_hash,
        actor="build_system",
        result="pass",
        detail={
            "provenance_path": str(prov_path),
            "builder_id": builder_id,
            "version": version,
            "source_commit": provenance["predicate"]["buildDefinition"]["externalParameters"][
                "source_commit"
            ],
        },
    )
    return prov_path


def verify_provenance(
    binary_path: Path, prov_path: Path, condition_name: str = "S2"
) -> tuple[bool, Optional[str], Optional[dict]]:
    """
    Returns (valid, failure_reason, provenance_dict_or_None).
    Checks, in order: provenance file present and parseable (#2),
    binary hash matches subject digest (#1), builder_id is authorized (#5).
    """
    store = EvidenceStore()

    with open(binary_path, "rb") as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()

    if not prov_path.exists():
        store.record(
            pipeline_stage="provenance_verification",
            condition=condition_name,
            artifact_ref=actual_hash,
            actor="ground_authorization_service",
            result="fail",
            detail={"reason": "provenance file missing"},
            test_case_injected="2",
        )
        return False, "provenance file missing", None

    try:
        with open(prov_path) as f:
            provenance = json.load(f)
    except json.JSONDecodeError:
        store.record(
            pipeline_stage="provenance_verification",
            condition=condition_name,
            artifact_ref=actual_hash,
            actor="ground_authorization_service",
            result="fail",
            detail={"reason": "provenance file is not valid JSON (false provenance)"},
            test_case_injected="2",
        )
        return False, "provenance file is not valid JSON", None

    try:
        recorded_hash = provenance["subject"][0]["digest"]["sha256"]
        builder_id = provenance["predicate"]["runDetails"]["builder"]["id"]
    except (KeyError, IndexError):
        store.record(
            pipeline_stage="provenance_verification",
            condition=condition_name,
            artifact_ref=actual_hash,
            actor="ground_authorization_service",
            result="fail",
            detail={"reason": "provenance missing required fields (false provenance)"},
            test_case_injected="2",
        )
        return False, "provenance missing required fields", None

    if recorded_hash != actual_hash:
        store.record(
            pipeline_stage="provenance_verification",
            condition=condition_name,
            artifact_ref=actual_hash,
            actor="ground_authorization_service",
            result="fail",
            detail={
                "reason": "binary does not match source/provenance record",
                "recorded_hash": recorded_hash,
                "actual_hash": actual_hash,
            },
            test_case_injected="1",
        )
        return False, "binary does not match provenance record", provenance

    if builder_id not in ALLOWED_BUILDER_IDS:
        store.record(
            pipeline_stage="provenance_verification",
            condition=condition_name,
            artifact_ref=actual_hash,
            actor="ground_authorization_service",
            result="fail",
            detail={"reason": "unauthorized build runner", "builder_id": builder_id},
            test_case_injected="5",
        )
        return False, f"unauthorized build runner: {builder_id}", provenance

    store.record(
        pipeline_stage="provenance_verification",
        condition=condition_name,
        artifact_ref=actual_hash,
        actor="ground_authorization_service",
        result="pass",
        detail={"builder_id": builder_id},
    )
    return True, None, provenance
