"""
Signing stage — S0 baseline assurance mechanism.

Uses Ed25519 (via the `cryptography` package) rather than shelling out to
openssl or standing up Sigstore/cosign infrastructure. This is a deliberate
Phase 1 scope decision (see Technical-Design-Document.md § 7 open
questions): Ed25519 signing is itself standard, composable tooling — it
satisfies the "signature only" S0 condition. Keyless/transparency-log-backed
signing (Sigstore/cosign) remains a candidate upgrade for later phases,
relevant mainly to the S2+ provenance/transparency claims, not S0's basic
authenticity guarantee.

Test-only keys: never treat anything under keys/ as real signing material.
See SECURITY.md and .gitignore (*.pem, *.key are excluded from git).

Phase 8 red-team fix (2026-08-04), finding #2 (see Threat-Model.md "Phase
8 independent (blind, AI) red-team review"): `is_revoked()` previously
returned `False` (not revoked) whenever `revoked_keys.txt` didn't exist —
a classic fail-open default. Deleting the file with a single unprivileged
filesystem write un-revoked every key with no cryptographic trace.

Fixed via `state_integrity.py`: the revocation list is now co-initialized
(empty, but integrity-protected) the moment a keypair is generated, so
content and its HMAC sidecar always exist together from that point on.
`is_revoked()` now fails **closed** — if the list's integrity check
fails (tampered, or deleted while its sidecar remains, which is exactly
the "delete the file to un-revoke" pattern the red-team found), every
key is treated as revoked rather than risk trusting a forged "nothing is
revoked" file. The only way to legitimately reach "not revoked" is a
verified-empty or verified-containing-other-fingerprints list.
"""

from __future__ import annotations

import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.exceptions import InvalidSignature

REPO_ROOT = Path(__file__).parent.parent.parent
KEYS_DIR = REPO_ROOT / "keys"
PRIVATE_KEY_PATH = KEYS_DIR / "test_signing_key.pem"
PUBLIC_KEY_PATH = KEYS_DIR / "test_signing_key.pub.pem"
REVOKED_KEYS_PATH = KEYS_DIR / "revoked_keys.txt"

sys.path.insert(0, str(REPO_ROOT / "src"))
from evidence_store import EvidenceStore  # noqa: E402
from state_integrity import StateIntegrityError, protect, read_verified, discard  # noqa: E402


def _ensure_revocation_list_initialized() -> None:
    """Co-initializes an empty, integrity-protected revocation list if
    one doesn't exist yet, so content and its HMAC sidecar are always
    created together from this point forward — removes the ambiguity
    between "never protected" and "protected, then tampered" for every
    `is_revoked()` check that follows. A no-op if the list is already
    initialized (verified-empty or verified-non-empty) or already
    tampered (in which case there's nothing safe to initialize —
    `is_revoked()` will surface that on its own)."""
    try:
        data = read_verified(REVOKED_KEYS_PATH)
    except StateIntegrityError:
        return
    if data is None:
        KEYS_DIR.mkdir(parents=True, exist_ok=True)
        REVOKED_KEYS_PATH.write_text("")
        protect(REVOKED_KEYS_PATH)


def generate_keypair(force: bool = False) -> None:
    """Generate a test Ed25519 keypair if one doesn't already exist."""
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    _ensure_revocation_list_initialized()

    if PRIVATE_KEY_PATH.exists() and not force:
        return

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    with open(PRIVATE_KEY_PATH, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    with open(PUBLIC_KEY_PATH, "wb") as f:
        f.write(
            public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
    PRIVATE_KEY_PATH.chmod(0o600)


def _fingerprint(public_key_path: Path) -> str:
    """Short fingerprint of a public key, used for revocation checks."""
    import hashlib

    with open(public_key_path, "rb") as f:
        raw = f.read()
    return hashlib.sha256(raw).hexdigest()[:16]


def is_revoked(public_key_path: Path = PUBLIC_KEY_PATH) -> bool:
    try:
        data = read_verified(REVOKED_KEYS_PATH)
    except StateIntegrityError as e:
        # Fail closed (Phase 8 red-team finding #2): cannot verify the
        # revocation list's integrity, so treat every key as revoked
        # rather than risk trusting a forged/deleted "nothing is
        # revoked" file.
        EvidenceStore().record(
            pipeline_stage="onboard_signature_verification",
            condition="n/a",
            artifact_ref=_fingerprint(public_key_path),
            actor="signing_authority",
            result="fail",
            detail={
                "reason": "revocation list integrity check failed — treating key as revoked",
                "error": str(e),
            },
        )
        return True
    if data is None:
        return False  # legitimate "nothing has ever been revoked" state
    fingerprint = _fingerprint(public_key_path)
    revoked = data.decode().split()
    return fingerprint in revoked


def revoke_current_key() -> None:
    """Test helper for attack matrix case #7 (revoked signing key)."""
    _ensure_revocation_list_initialized()
    fingerprint = _fingerprint(PUBLIC_KEY_PATH)
    with open(REVOKED_KEYS_PATH, "a") as f:
        f.write(fingerprint + "\n")
    protect(REVOKED_KEYS_PATH)


def reset_revocation_list() -> None:
    """Test helper — restore the legitimate 'nothing revoked' state
    between test runs."""
    discard(REVOKED_KEYS_PATH)
    _ensure_revocation_list_initialized()


def sign(binary_path: Path, condition_name: str = "S0") -> Path:
    """Sign a binary, write a detached .sig file, log evidence."""
    store = EvidenceStore()
    generate_keypair()

    with open(PRIVATE_KEY_PATH, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)

    with open(binary_path, "rb") as f:
        data = f.read()

    signature = private_key.sign(data)
    sig_path = Path(str(binary_path) + ".sig")
    sig_path.write_bytes(signature)

    import hashlib

    artifact_hash = hashlib.sha256(data).hexdigest()

    store.record(
        pipeline_stage="signing",
        condition=condition_name,
        artifact_ref=artifact_hash,
        actor="signing_authority",
        result="pass",
        detail={
            "binary": str(binary_path),
            "signature_path": str(sig_path),
            "key_fingerprint": _fingerprint(PUBLIC_KEY_PATH),
            "algorithm": "Ed25519",
        },
    )
    return sig_path


def verify(
    binary_path: Path,
    sig_path: Path,
    condition_name: str = "S0",
    actor: str = "onboard_verification_agent",
    check_revocation: bool = True,
) -> bool:
    """
    Verify a binary's signature. Returns True/False and always logs
    evidence regardless of outcome (evidence-first design principle).
    """
    store = EvidenceStore()
    import hashlib

    with open(binary_path, "rb") as f:
        data = f.read()
    artifact_hash = hashlib.sha256(data).hexdigest()

    if not PUBLIC_KEY_PATH.exists():
        store.record(
            pipeline_stage="onboard_signature_verification",
            condition=condition_name,
            artifact_ref=artifact_hash,
            actor=actor,
            result="fail",
            detail={"reason": "no public key available"},
        )
        return False

    if check_revocation and is_revoked(PUBLIC_KEY_PATH):
        store.record(
            pipeline_stage="onboard_signature_verification",
            condition=condition_name,
            artifact_ref=artifact_hash,
            actor=actor,
            result="fail",
            detail={"reason": "signing key revoked", "test_case": "7"},
            test_case_injected="7",
        )
        return False

    with open(PUBLIC_KEY_PATH, "rb") as f:
        public_key: Ed25519PublicKey = serialization.load_pem_public_key(f.read())

    signature = sig_path.read_bytes()

    try:
        public_key.verify(signature, data)
        valid = True
        reason = None
    except InvalidSignature:
        valid = False
        reason = "signature does not match artifact content"

    store.record(
        pipeline_stage="onboard_signature_verification",
        condition=condition_name,
        artifact_ref=artifact_hash,
        actor=actor,
        result="pass" if valid else "fail",
        detail={"reason": reason} if reason else {},
    )
    return valid


if __name__ == "__main__":
    generate_keypair()
    print(f"Keypair ready at {KEYS_DIR}")
