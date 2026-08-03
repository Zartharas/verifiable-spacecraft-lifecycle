"""
SBOM generation and checks — S1 assurance mechanism.

Format decision (Technical-Design-Document.md § 7/7a): CycloneDX, chosen
for tooling maturity over SPDX. This is a hand-rolled minimal CycloneDX-
shaped JSON generator rather than invoking Syft, since the stand-in
artifact (cfs-app/stub-telemetry-app) has no real dependency graph for
Syft to discover — a single C source file compiled with gcc. Swap in real
Syft output once the pipeline points at the real cFS build (see
cfs-app/README.md); the CycloneDX shape here is deliberately compatible.

Covers attack matrix test cases:
  #3 — incomplete SBOM (missing required fields)
  #4 — dependency with a known test vulnerability
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_store import EvidenceStore  # noqa: E402

SBOM_DIR = REPO_ROOT / "work" / "sbom"

# Synthetic vulnerability database for test case #4. Not a real feed —
# a fixed, small, test-only table so the detection logic itself is
# exercised deterministically without a network call to a real CVE feed.
KNOWN_VULNERABLE_COMPONENTS = {
    ("libfake-crypto", "1.0.0"): "TESTCVE-2026-0001 (synthetic, test case #4 only)",
}

REQUIRED_COMPONENT_FIELDS = {"name", "version", "type"}


def generate_sbom(
    binary_path: Path,
    condition_name: str = "S1",
    inject_incomplete: bool = False,
    inject_vulnerable_dependency: bool = False,
) -> Path:
    """
    Generate a CycloneDX-shaped SBOM for the given binary.

    inject_incomplete=True drops a required field from a component
    (test case #3). inject_vulnerable_dependency=True adds a synthetic
    known-vulnerable component (test case #4).
    """
    store = EvidenceStore()
    with open(binary_path, "rb") as f:
        artifact_hash = hashlib.sha256(f.read()).hexdigest()

    components = [
        {
            "type": "application",
            "name": binary_path.name,
            "version": "0.1.0-phase2",
        },
        {
            "type": "library",
            "name": "libc",
            "version": "system",  # honestly vague — see completeness note below
        },
    ]

    if inject_vulnerable_dependency:
        components.append(
            {
                "type": "library",
                "name": "libfake-crypto",
                "version": "1.0.0",
            }
        )

    if inject_incomplete:
        # Drop a required field from one component to simulate an
        # incomplete SBOM (test case #3).
        del components[0]["version"]

    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:sbom-{artifact_hash[:16]}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": binary_path.name,
                "hashes": [{"alg": "SHA-256", "content": artifact_hash}],
            }
        },
        "components": components,
    }

    SBOM_DIR.mkdir(parents=True, exist_ok=True)
    sbom_path = SBOM_DIR / f"{binary_path.name}.cdx.json"
    with open(sbom_path, "w") as f:
        json.dump(sbom, f, indent=2)

    store.record(
        pipeline_stage="sbom_generation",
        condition=condition_name,
        artifact_ref=artifact_hash,
        actor="sbom_generator",
        result="pass",
        detail={
            "sbom_path": str(sbom_path),
            "component_count": len(components),
            "inject_incomplete": inject_incomplete,
            "inject_vulnerable_dependency": inject_vulnerable_dependency,
        },
        test_case_injected="3" if inject_incomplete else ("4" if inject_vulnerable_dependency else None),
    )
    return sbom_path


def check_completeness(sbom_path: Path) -> tuple[bool, Optional[str]]:
    """Test case #3: every component must have all required fields."""
    with open(sbom_path) as f:
        sbom = json.load(f)
    for component in sbom.get("components", []):
        missing = REQUIRED_COMPONENT_FIELDS - set(component.keys())
        if missing:
            return False, f"component {component.get('name', '?')} missing fields: {missing}"
    return True, None


def check_known_vulnerabilities(sbom_path: Path) -> tuple[bool, Optional[str]]:
    """Test case #4: flag any component matching the synthetic vuln table."""
    with open(sbom_path) as f:
        sbom = json.load(f)
    for component in sbom.get("components", []):
        key = (component.get("name"), component.get("version"))
        if key in KNOWN_VULNERABLE_COMPONENTS:
            return False, KNOWN_VULNERABLE_COMPONENTS[key]
    return True, None


def verify_sbom(sbom_path: Path, condition_name: str = "S1") -> bool:
    """Run all S1 SBOM checks, logging one evidence record for the stage."""
    store = EvidenceStore()

    if not sbom_path.exists():
        store.record(
            pipeline_stage="sbom_verification",
            condition=condition_name,
            artifact_ref="unknown",
            actor="ground_authorization_service",
            result="fail",
            detail={"reason": "SBOM file missing"},
        )
        return False

    with open(sbom_path) as f:
        sbom = json.load(f)
    artifact_hash = sbom.get("metadata", {}).get("component", {}).get("hashes", [{}])[0].get(
        "content", "unknown"
    )

    complete, reason1 = check_completeness(sbom_path)
    if not complete:
        store.record(
            pipeline_stage="sbom_verification",
            condition=condition_name,
            artifact_ref=artifact_hash,
            actor="ground_authorization_service",
            result="fail",
            detail={"reason": reason1},
            test_case_injected="3",
        )
        return False

    no_known_vulns, reason2 = check_known_vulnerabilities(sbom_path)
    if not no_known_vulns:
        store.record(
            pipeline_stage="sbom_verification",
            condition=condition_name,
            artifact_ref=artifact_hash,
            actor="ground_authorization_service",
            result="fail",
            detail={"reason": reason2},
            test_case_injected="4",
        )
        return False

    store.record(
        pipeline_stage="sbom_verification",
        condition=condition_name,
        artifact_ref=artifact_hash,
        actor="ground_authorization_service",
        result="pass",
        detail={},
    )
    return True
