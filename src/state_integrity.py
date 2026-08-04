"""
Local ground-truth state integrity — HMAC-protects security-critical
side-state files (version ledger, partition state, key-revocation lists)
against direct filesystem tampering.

Motivation: the Phase 8 blind red-team review (see Threat-Model.md "Phase
8 independent (blind, AI) red-team review") found that every one of these
files was plain, unsigned JSON/text — anything with filesystem write
access could edit `last_approved_version` back to 0, or delete
`revoked_keys.txt` to silently un-revoke a key, bypassing the mechanism
built on top entirely. This module closes that gap for every caller that
adopts it.

Deliberately symmetric (HMAC), not asymmetric signing: these are all
LOCAL, single-trust-domain side-state files (the same process that writes
the state is the only process meant to read/trust it later) — this
differs from `signing.py`'s Ed25519 use, which protects an artifact
crossing an actual trust boundary (ground -> uplink -> spacecraft), or
`evidence_store/authorization_evidence.py`'s signing, which protects a
document meant for an external auditor. A symmetric HMAC key stored
alongside the state (gitignored, like every other key in `keys/`) is
proportionate to what's actually being defended here: "did this file
change since we last wrote it," not "can an untrusted third party verify
this independently."

Threat model, stated honestly (do not overclaim in the paper): this
defends against an attacker who can edit the *state* file but not also
read/use the *HMAC key* file to forge a consistent replacement — e.g., a
less-privileged process, a component compromised in a way that only
grants access to `work/` and not `keys/`, or plain accidental corruption.
It does NOT defend against an attacker with full filesystem access who
can also read the HMAC key and re-sign a forged file consistently — no
purely local symmetric scheme can close that gap; only an external,
independently-held root of trust (e.g., writing to a remote, append-only
log) would. That residual limitation is real and should be stated
plainly, not glossed over.

Lifecycle contract each caller must follow for the guarantee to hold:
call `protect(path)` immediately after *every* write to a protected file,
including its very first write (an empty/default value counts) — this
ensures content and sidecar are always created together, so "content
exists but sidecar doesn't" and "sidecar exists but content doesn't" are
both unambiguous tamper signals rather than confusable with a legitimate
first-ever-run. See `version_ledger.py`/`partitions.py`/`signing.py` for
the adopted call sites.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
KEYS_DIR = REPO_ROOT / "keys"
STATE_HMAC_KEY_PATH = KEYS_DIR / "state_integrity.key"


class StateIntegrityError(Exception):
    """Raised whenever protected state cannot be trusted: tampered
    content, or content/sidecar existing without its required pair.
    Callers MUST treat this as a fail-closed condition (deny, don't
    silently fall back to a default) — see each call site."""


def _get_hmac_key() -> bytes:
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    if not STATE_HMAC_KEY_PATH.exists():
        STATE_HMAC_KEY_PATH.write_bytes(secrets.token_bytes(32))
        STATE_HMAC_KEY_PATH.chmod(0o600)
    return STATE_HMAC_KEY_PATH.read_bytes()


def _hmac_path(path: Path) -> Path:
    return path.with_name(path.name + ".hmac")


def protect(path: Path) -> None:
    """Write/update the HMAC sidecar for `path`, over its current
    on-disk bytes. Call this immediately after every write to `path`,
    including the very first one."""
    key = _get_hmac_key()
    data = path.read_bytes()
    tag = hmac.new(key, data, hashlib.sha256).hexdigest()
    _hmac_path(path).write_text(tag)


def read_verified(path: Path) -> bytes | None:
    """Returns `path`'s bytes if content and its HMAC sidecar both exist
    and match, or `None` if neither the content nor the sidecar exists
    (the legitimate "nothing ever recorded" state).

    Raises `StateIntegrityError` for every other combination:
      - content exists, sidecar missing (deleted, or predates this
        protection mechanism being adopted for this file)
      - sidecar exists, content missing (deleted *after* being
        protected — exactly the "delete the file to reset it" tamper
        pattern the red-team review found)
      - both exist but don't match (content edited directly)
    """
    key = _get_hmac_key()
    hmac_path = _hmac_path(path)
    content_exists = path.exists()
    hmac_exists = hmac_path.exists()

    if not content_exists and not hmac_exists:
        return None

    if content_exists and not hmac_exists:
        raise StateIntegrityError(
            f"{path} exists but has no integrity sidecar ({hmac_path}) — "
            "either it predates this protection mechanism being enabled "
            "for this file, or the sidecar was removed. Treating as "
            "untrusted."
        )
    if hmac_exists and not content_exists:
        raise StateIntegrityError(
            f"{path} was deleted while its integrity sidecar ({hmac_path}) "
            "still exists — this is exactly the tamper pattern of "
            "deleting state to silently reset it. Treating as untrusted."
        )

    data = path.read_bytes()
    expected = hmac_path.read_text().strip()
    actual = hmac.new(key, data, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, actual):
        raise StateIntegrityError(
            f"{path} failed integrity verification — its content does "
            "not match the recorded HMAC. Treating as untrusted/tampered."
        )
    return data


def discard(path: Path) -> None:
    """Test/reset helper — restores the legitimate 'nothing recorded'
    state by overwriting `path` with empty content and re-protecting it,
    rather than deleting it outright. Some sandboxes (see this project's
    STATUS.md "Environment notes") reject `unlink()` on files created by
    a prior process even with matching ownership — overwriting in place
    avoids that entirely. Empty-but-protected is indistinguishable, for
    every caller in this codebase, from genuinely never-written: each
    caller's own parser already treats empty/missing content as its
    default value (0 for the ledger, an empty revocation list, the
    default partition state, etc.). Not for production use (a real
    deployment should never need to reset state this way)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    protect(path)
