"""
Machine-readable authorization evidence — S5 assurance mechanism.

Aggregates evidence-store records for a single pipeline run into one
structured document, loosely informed by OSCAL's assessment-results shape
(subject, assessed controls/checks, findings, overall result) rather than
a full OSCAL schema implementation — the point being tested is "can the
full lifecycle's evidence be assembled into one machine-readable
authorization record automatically," which is also what satisfies the
Phase 4 exit criterion about generating a full comparison table from the
evidence store automatically (see evaluation/metrics.py).

**Important:** this takes an explicit `records` list from the caller
rather than looking records up by `artifact_hash` internally. The
stand-in stub artifact's source never changes, so its build hash is
IDENTICAL across every run and every condition — an internal
`store.for_artifact(artifact_hash)` lookup would silently aggregate every
record ever logged for that hash across the *entire* evaluation session,
not just this one release's evidence trail. That's not a reporting
nuance, it's a correctness bug in the S5 mechanism itself (the document
is supposed to represent *this* release's evidence, not accumulated
cross-run noise) — caught while building the Phase 5 evaluation harness,
which showed S5's storage overhead ballooning to ~850KB before this fix.
Callers (see `src/pipeline.py`) must pass only the records generated
during the current run, obtained by index-slicing the evidence log
around the `run()` call, not a hash-based lookup.

Phase 8 red-team fix (2026-08-04), finding #5 (see Threat-Model.md "Phase
8 independent (blind, AI) red-team review"): this document was
previously unsigned, plain JSON, and keyed only by artifact hash — since
the stand-in artifact's hash is constant across every run (the reason
noted above for an unrelated bug), every re-run silently overwrote
whatever authorization-evidence document existed at that path, including
one that had recorded a detected failure. Fixed two ways:

  1. **Never overwritten again**: the filename now includes `run_id` (the
     caller's evidence-log start index for this run — already computed
     by `pipeline.py`, a natural, already-unique-per-run identifier, so
     no new ID scheme was needed), making every run's document a
     distinct file.
  2. **Signed**: a dedicated Ed25519 keypair (mirroring `attestation.py`'s
     per-mechanism-key convention) signs the document's canonical JSON
     bytes; the detached signature is written to a `.sig` sidecar, and
     `verify_authorization_evidence()` lets an external auditor/ground
     reviewer check it hasn't been altered since generation — closing
     the "unsigned deliverable at the top of the assurance ladder" gap
     the red-team review found.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.exceptions import InvalidSignature

from evidence_store import EvidenceStore  # noqa: E402

AUTHORIZATION_EVIDENCE_DIR = REPO_ROOT / "work" / "authorization_evidence"
KEYS_DIR = REPO_ROOT / "keys"
AUTH_EVIDENCE_PRIVATE_KEY_PATH = KEYS_DIR / "authorization_evidence_key.pem"
AUTH_EVIDENCE_PUBLIC_KEY_PATH = KEYS_DIR / "authorization_evidence_key.pub.pem"


def _generate_auth_evidence_keypair(force: bool = False) -> None:
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    if AUTH_EVIDENCE_PRIVATE_KEY_PATH.exists() and not force:
        return
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    with open(AUTH_EVIDENCE_PRIVATE_KEY_PATH, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    with open(AUTH_EVIDENCE_PUBLIC_KEY_PATH, "wb") as f:
        f.write(
            public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
    AUTH_EVIDENCE_PRIVATE_KEY_PATH.chmod(0o600)


def generate_authorization_evidence(
    artifact_hash: str, records: list[dict], condition_name: str = "S5", run_id: int = 0
) -> Path:
    store = EvidenceStore()
    _generate_auth_evidence_keypair()

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
        "subject": {"artifact_hash": artifact_hash, "condition": condition_name, "run_id": run_id},
        "findings": findings,
        "overall_result": overall_result,
        "finding_count": len(findings),
    }
    canonical_bytes = json.dumps(document, sort_keys=True).encode()

    with open(AUTH_EVIDENCE_PRIVATE_KEY_PATH, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
    signature = private_key.sign(canonical_bytes)

    AUTHORIZATION_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    # Phase 8 fix: run_id in the filename means two runs against the same
    # (possibly constant, for the stand-in stub) artifact hash never
    # collide and never overwrite one another's evidence.
    doc_path = (
        AUTHORIZATION_EVIDENCE_DIR / f"{artifact_hash}.{run_id}.authorization-evidence.json"
    )
    sig_path = Path(str(doc_path) + ".sig")
    with open(doc_path, "w") as f:
        json.dump(document, f, indent=2)
    sig_path.write_bytes(signature)

    store.record(
        pipeline_stage="authorization_evidence_generation",
        condition=condition_name,
        artifact_ref=artifact_hash,
        actor="ground_authorization_service",
        result="pass",
        detail={
            "document_path": str(doc_path),
            "signature_path": str(sig_path),
            "finding_count": len(findings),
            "overall_result": overall_result,
            "run_id": run_id,
        },
    )
    return doc_path


def verify_authorization_evidence(doc_path: Path) -> tuple[bool, str | None]:
    """External-auditor-facing check: does this authorization-evidence
    document's signature still match its content? Returns (valid,
    failure_reason_or_None). Added alongside the Phase 8 signing fix so
    the property being fixed ("this document can't be silently altered
    after generation") is directly testable, not just asserted."""
    sig_path = Path(str(doc_path) + ".sig")
    if not doc_path.exists():
        return False, "document missing"
    if not sig_path.exists():
        return False, "signature missing"
    if not AUTH_EVIDENCE_PUBLIC_KEY_PATH.exists():
        return False, "authorization-evidence public key missing"

    with open(doc_path) as f:
        document = json.load(f)
    canonical_bytes = json.dumps(document, sort_keys=True).encode()
    signature = sig_path.read_bytes()

    with open(AUTH_EVIDENCE_PUBLIC_KEY_PATH, "rb") as f:
        public_key = serialization.load_pem_public_key(f.read())

    try:
        public_key.verify(signature, canonical_bytes)
    except InvalidSignature:
        return False, "signature does not match document content"
    return True, None
