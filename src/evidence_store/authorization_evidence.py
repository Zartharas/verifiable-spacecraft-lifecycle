"""
Machine-readable authorization evidence — S5 assurance mechanism.

Aggregates all evidence-store records for a given artifact into a single
structured document, loosely informed by OSCAL's assessment-results shape
(subject, assessed controls/checks, findings, overall result) rather than
a full OSCAL schema implementation — the point being tested is "can the
full lifecycle's evidence be assembled into one machine-readable
authorization record automatically," which is also what satisfies the
Phase 4 exit criterion about generating a full comparison table from the
evidence store automatically (see evaluation/metrics.py).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_store import EvidenceStore  # noqa: E402

AUTHORIZATION_EVIDENCE_DIR = REPO_ROOT / "work" / "authorization_evidence"


def generate_authorization_evidence(artifact_hash: str, condition_name: str = "S5") -> Path:
    store = EvidenceStore()
    records = store.for_artifact(artifact_hash)

    findings = [
        {
            "stage": r["pipeline_stage"],
            "actor": r["actor"],
            "result": r["result"],
            "test_case": r["test_case_injected"],
            "timestamp": r["timestamp"],
        }
        for r in records
    ]
    overall_result = "pass" if all(r["result"] != "fail" for r in records) else "fail"

    document = {
        "_type": "authorization-evidence/v1",
        "oscal_informed": True,
        "subject": {"artifact_hash": artifact_hash, "condition": condition_name},
        "findings": findings,
        "overall_result": overall_result,
        "finding_count": len(findings),
    }

    AUTHORIZATION_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    doc_path = AUTHORIZATION_EVIDENCE_DIR / f"{artifact_hash}.authorization-evidence.json"
    with open(doc_path, "w") as f:
        json.dump(document, f, indent=2)

    store.record(
        pipeline_stage="authorization_evidence_generation",
        condition=condition_name,
        artifact_ref=artifact_hash,
        actor="ground_authorization_service",
        result="pass",
        detail={"document_path": str(doc_path), "finding_count": len(findings), "overall_result": overall_result},
    )
    return doc_path
