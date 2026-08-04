"""
Boot/runtime attestation — S3 assurance mechanism.

Decision (Technical-Design-Document.md § 7/7c): **software-based
attestation stub**, not a real TPM/swtpm. The authoring sandbox has no
swtpm binary, no tpm2-tools, and no root to install them. A software stub
that signs a measurement (installed binary hash + timestamp + partition
id) with a dedicated attestation key models the *assurance property*
under test — "can we trust a claim about what's currently running, and
detect a stale claim?" — without a hardware root of trust. This is a
materially weaker guarantee than real TPM-backed attestation (a software
key can be exfiltrated in ways a TPM-sealed key can't), and that
limitation must be stated plainly in the paper, not glossed over. See
STATUS.md "Claims status" — attestation claims stay non-hardware-backed
until/unless a real TPM (or swtpm on a capable machine) is substituted in.

Covers attack matrix test case #12 (stale attestation).

Phase 8 red-team fix (2026-08-04), finding #6 (see Threat-Model.md "Phase
8 independent (blind, AI) red-team review"): no revocation mechanism
existed for the attestation key at all, unlike the signing key
(`signing.py`'s `is_revoked()`). If the attestation private key were ever
known or suspected compromised, there was no way to invalidate it short
of manually swapping key files. Added `is_attestation_key_revoked()` /
`revoke_current_attestation_key()`, mirroring `signing.py`'s (Phase 8
finding #2 fix) fail-closed pattern exactly: an integrity-protected
revocation list (via `state_integrity.py`) that fails closed (treats the
key as revoked) if it's ever tampered with or deleted after being
protected. `verify_attestation()` now checks this before trusting a
quote.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_store import EvidenceStore  # noqa: E402
from state_integrity import StateIntegrityError, protect, read_verified, discard  # noqa: E402

KEYS_DIR = REPO_ROOT / "keys"
ATTESTATION_PRIVATE_KEY_PATH = KEYS_DIR / "attestation_key.pem"
ATTESTATION_PUBLIC_KEY_PATH = KEYS_DIR / "attestation_key.pub.pem"
ATTESTATION_REVOKED_KEYS_PATH = KEYS_DIR / "attestation_revoked_keys.txt"
ATTESTATION_DIR = REPO_ROOT / "work" / "attestation"

DEFAULT_FRESHNESS_SECONDS = 300  # attestation older than this is "stale" (test case #12)


def _fingerprint(public_key_path: Path) -> str:
    with open(public_key_path, "rb") as f:
        raw = f.read()
    return hashlib.sha256(raw).hexdigest()[:16]


def _ensure_revocation_list_initialized() -> None:
    """See signing.py's identical helper — co-initializes an empty,
    integrity-protected revocation list so content and sidecar are
    always created together."""
    try:
        data = read_verified(ATTESTATION_REVOKED_KEYS_PATH)
    except StateIntegrityError:
        return
    if data is None:
        KEYS_DIR.mkdir(parents=True, exist_ok=True)
        ATTESTATION_REVOKED_KEYS_PATH.write_text("")
        protect(ATTESTATION_REVOKED_KEYS_PATH)


def is_attestation_key_revoked(public_key_path: Path = ATTESTATION_PUBLIC_KEY_PATH) -> bool:
    try:
        data = read_verified(ATTESTATION_REVOKED_KEYS_PATH)
    except StateIntegrityError as e:
        EvidenceStore().record(
            pipeline_stage="attestation_verification",
            condition="n/a",
            artifact_ref=_fingerprint(public_key_path),
            actor="health_monitor",
            result="fail",
            detail={
                "reason": "attestation revocation list integrity check failed — treating key as revoked",
                "error": str(e),
            },
        )
        return True
    if data is None:
        return False
    fingerprint = _fingerprint(public_key_path)
    return fingerprint in data.decode().split()


def revoke_current_attestation_key() -> None:
    """Operator/test action for revoking a known-or-suspected-compromised
    attestation key (Phase 8 finding #6)."""
    _ensure_revocation_list_initialized()
    fingerprint = _fingerprint(ATTESTATION_PUBLIC_KEY_PATH)
    with open(ATTESTATION_REVOKED_KEYS_PATH, "a") as f:
        f.write(fingerprint + "\n")
    protect(ATTESTATION_REVOKED_KEYS_PATH)


def reset_attestation_revocation_list() -> None:
    """Test helper — restore the legitimate 'nothing revoked' state."""
    discard(ATTESTATION_REVOKED_KEYS_PATH)
    _ensure_revocation_list_initialized()


def _generate_attestation_keypair(force: bool = False) -> None:
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    _ensure_revocation_list_initialized()
    if ATTESTATION_PRIVATE_KEY_PATH.exists() and not force:
        return
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    with open(ATTESTATION_PRIVATE_KEY_PATH, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    with open(ATTESTATION_PUBLIC_KEY_PATH, "wb") as f:
        f.write(
            public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
    ATTESTATION_PRIVATE_KEY_PATH.chmod(0o600)


def generate_attestation(
    installed_binary_path: Path,
    partition_id: str,
    condition_name: str = "S3",
    backdate_seconds: int = 0,
) -> Path:
    """
    Produce a signed attestation quote: measured hash of what's actually
    installed, which partition it's in, and a timestamp.

    backdate_seconds: subtract this many seconds from the recorded
    timestamp — test helper for simulating a stale attestation
    (test case #12), not something a real boot process would ever do to
    itself.
    """
    store = EvidenceStore()
    _generate_attestation_keypair()

    with open(installed_binary_path, "rb") as f:
        measured_hash = hashlib.sha256(f.read()).hexdigest()

    # Second red-team pass, finding #11 (2026-08-05) — same reasoning as
    # signing.py's identical fix: log visibility for "quoting with an
    # already-revoked attestation key," deliberately not refusing to
    # produce the quote at all, since test case #6's own regression test
    # (revoke, then run() through S4) models exactly that and expects
    # the *downstream* verify_attestation() check to catch it, not this
    # function to block it outright.
    if is_attestation_key_revoked():
        store.record(
            pipeline_stage="boot_attestation",
            condition=condition_name,
            artifact_ref=measured_hash,
            actor="onboard_attestation_agent",
            result="fail",
            detail={
                "reason": "quoting with an already-revoked attestation key — no "
                "automatic rotation occurred; an operator must call "
                "_generate_attestation_keypair(force=True)",
                "key_fingerprint": _fingerprint(ATTESTATION_PUBLIC_KEY_PATH),
            },
        )

    quote_time = time.time() - backdate_seconds
    quote = {
        "measured_binary": installed_binary_path.name,
        "measured_hash": measured_hash,
        "partition_id": partition_id,
        "timestamp": quote_time,
    }
    quote_bytes = json.dumps(quote, sort_keys=True).encode()

    with open(ATTESTATION_PRIVATE_KEY_PATH, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
    signature = private_key.sign(quote_bytes)

    ATTESTATION_DIR.mkdir(parents=True, exist_ok=True)
    attestation_path = ATTESTATION_DIR / f"{partition_id}.attestation.json"
    with open(attestation_path, "w") as f:
        json.dump({"quote": quote, "signature": signature.hex()}, f, indent=2)

    store.record(
        pipeline_stage="boot_attestation",
        condition=condition_name,
        artifact_ref=measured_hash,
        actor="onboard_attestation_agent",
        result="pass",
        detail={
            "partition_id": partition_id,
            "attestation_path": str(attestation_path),
            "backdated_seconds": backdate_seconds,
            "note": "software attestation stub, NOT hardware-backed (no TPM) — see module docstring",
        },
    )
    return attestation_path


def verify_attestation(
    attestation_path: Path,
    expected_binary_path: Path,
    condition_name: str = "S3",
    max_age_seconds: int = DEFAULT_FRESHNESS_SECONDS,
) -> tuple[bool, Optional[str]]:
    store = EvidenceStore()

    with open(expected_binary_path, "rb") as f:
        expected_hash = hashlib.sha256(f.read()).hexdigest()

    if not attestation_path.exists():
        store.record(
            pipeline_stage="attestation_verification",
            condition=condition_name,
            artifact_ref=expected_hash,
            actor="health_monitor",
            result="fail",
            detail={"reason": "attestation missing"},
        )
        return False, "attestation missing"

    if is_attestation_key_revoked():
        store.record(
            pipeline_stage="attestation_verification",
            condition=condition_name,
            artifact_ref=expected_hash,
            actor="health_monitor",
            result="fail",
            detail={"reason": "attestation key revoked"},
        )
        return False, "attestation key revoked"

    with open(attestation_path) as f:
        record = json.load(f)
    quote = record["quote"]
    signature = bytes.fromhex(record["signature"])
    quote_bytes = json.dumps(quote, sort_keys=True).encode()

    with open(ATTESTATION_PUBLIC_KEY_PATH, "rb") as f:
        public_key = serialization.load_pem_public_key(f.read())

    from cryptography.exceptions import InvalidSignature

    try:
        public_key.verify(signature, quote_bytes)
    except InvalidSignature:
        store.record(
            pipeline_stage="attestation_verification",
            condition=condition_name,
            artifact_ref=expected_hash,
            actor="health_monitor",
            result="fail",
            detail={"reason": "attestation signature invalid"},
        )
        return False, "attestation signature invalid"

    age_seconds = time.time() - quote["timestamp"]
    if age_seconds > max_age_seconds:
        store.record(
            pipeline_stage="attestation_verification",
            condition=condition_name,
            artifact_ref=expected_hash,
            actor="health_monitor",
            result="fail",
            detail={"reason": "attestation is stale", "age_seconds": age_seconds, "max_age_seconds": max_age_seconds},
            test_case_injected="12",
        )
        return False, "attestation is stale"

    # Second red-team pass, finding #4 (2026-08-05): the check above only
    # ever rejected a quote for being too OLD. A quote whose `timestamp`
    # is in the future gives a negative `age_seconds`, which is always
    # `< max_age_seconds` and therefore always "fresh" by the check
    # above — indefinitely, since real time only ever moves the negative
    # age closer to zero, never past the staleness threshold on its own.
    # A "pre-dated" attestation is not physically possible for a real
    # boot process to produce honestly, so treat one as invalid rather
    # than silently trusting it.
    if age_seconds < 0:
        store.record(
            pipeline_stage="attestation_verification",
            condition=condition_name,
            artifact_ref=expected_hash,
            actor="health_monitor",
            result="fail",
            detail={
                "reason": "attestation timestamp is in the future",
                "age_seconds": age_seconds,
            },
        )
        return False, "attestation timestamp is in the future"

    if quote["measured_hash"] != expected_hash:
        store.record(
            pipeline_stage="attestation_verification",
            condition=condition_name,
            artifact_ref=expected_hash,
            actor="health_monitor",
            result="fail",
            detail={
                "reason": "measured hash does not match currently installed binary",
                "measured_hash": quote["measured_hash"],
                "expected_hash": expected_hash,
            },
        )
        return False, "measured hash mismatch"

    store.record(
        pipeline_stage="attestation_verification",
        condition=condition_name,
        artifact_ref=expected_hash,
        actor="health_monitor",
        result="pass",
        detail={"age_seconds": age_seconds},
    )
    return True, None
