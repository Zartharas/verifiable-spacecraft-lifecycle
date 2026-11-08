"""
Hash-only baseline (added in response to peer review, 2026-10).

Question (reviewer comment): if the artifact deployed to the device has the
same SHA-256 as the release published on a source forge such as GitHub, what
problem remains?

This module answers that question by running a minimal "hash-only"
deployment against the same 15-case attack matrix used for the S0-S5 ladder
and the python-tuf baseline. The deployment model is deliberately generous
to the baseline:

* A release host publishes an artifact together with its SHA-256 digest
  (GitHub computes and exposes this digest for release assets at upload
  time; see the manuscript's reference list).
* The deployer downloads the artifact, recomputes SHA-256, and installs the
  artifact if and only if it equals the published digest.

Scope of what is exercised
--------------------------
Each applicable case builds a concrete scenario with real bytes and a real
SHA-256 comparison, and records whether the hash check rejects the
deployment. Cases that concern post-install state (10-15) are recorded as
out of scope for a pre-install integrity check, with a stated reason,
rather than scored.

This is a coverage comparison, not a probabilistic detection experiment:
every check is deterministic, so repeated trials confirm harness stability
(fresh random artifact bytes each trial), not a detection rate.

Assumption sensitivity
----------------------
Case 6 is the only case a digest comparison can catch, and only when the
digest reaches the deployer over a channel the attacker cannot rewrite.
`case_06b_digest_rewritten` shows the same attack succeeding when the
attacker controls the host or channel that serves both artifact and digest.
"""

from __future__ import annotations

import hashlib
import os
from typing import Callable


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ReleaseHost:
    """A source-forge-style release host: stores an artifact and the digest
    computed over whatever bytes were uploaded."""

    def __init__(self) -> None:
        self.artifacts: dict[str, bytes] = {}
        self.digests: dict[str, str] = {}

    def upload(self, name: str, data: bytes) -> None:
        self.artifacts[name] = data
        self.digests[name] = _sha256(data)  # computed at upload time

    def fetch(self, name: str) -> tuple[bytes, str]:
        return self.artifacts[name], self.digests[name]


def hash_only_deploy(received: bytes, published_digest: str) -> bool:
    """Returns True if the deployer would install the artifact."""
    return _sha256(received) == published_digest


def _fresh_firmware() -> bytes:
    return b"FLIGHT-SW-v1\x00" + os.urandom(4096)


# --- applicable cases -------------------------------------------------------


def case_06_modified_in_transit() -> dict:
    """Attacker alters the artifact in transit; the published digest reaches
    the deployer unmodified (independent channel)."""
    host = ReleaseHost()
    genuine = _fresh_firmware()
    host.upload("fw.bin", genuine)
    _, digest = host.fetch("fw.bin")
    tampered = bytearray(genuine)
    tampered[len(tampered) // 2] ^= 0xFF
    installed = hash_only_deploy(bytes(tampered), digest)
    return {"case": "6", "caught": not installed,
            "reason": "SHA-256 mismatch between received bytes and published digest"}


def case_06b_digest_rewritten() -> dict:
    """Same attack, but the attacker controls the host/channel serving both
    artifact and digest (a compromised release page or mirror)."""
    host = ReleaseHost()
    genuine = _fresh_firmware()
    host.upload("fw.bin", genuine)
    tampered = bytearray(genuine)
    tampered[len(tampered) // 2] ^= 0xFF
    host.upload("fw.bin", bytes(tampered))  # attacker replaces asset; digest recomputed
    received, digest = host.fetch("fw.bin")
    installed = hash_only_deploy(received, digest)
    return {"case": "6b", "caught": not installed,
            "reason": "digest and artifact are replaced together, so the check passes"}


def _malicious_but_consistent(case: str, reason: str) -> dict:
    """The malicious artifact is published with its own correct digest. The
    deployer's check passes, because a digest binds bytes to a digest and
    nothing else."""
    host = ReleaseHost()
    host.upload("fw.bin", _fresh_firmware() + b"\x90\x90 attacker-controlled build output")
    received, digest = host.fetch("fw.bin")
    installed = hash_only_deploy(received, digest)
    return {"case": case, "caught": not installed, "reason": reason}


def case_01_binary_not_from_source():
    return _malicious_but_consistent(
        "1", "digest is computed over the malicious binary after the fact; "
             "it records no link to source")


def case_02_missing_or_false_provenance():
    return _malicious_but_consistent(
        "2", "a hash check carries no provenance claim, true or false")


def case_03_incomplete_sbom():
    return _malicious_but_consistent(
        "3", "a hash check carries no component inventory")


def case_04_vulnerable_dependency():
    return _malicious_but_consistent(
        "4", "a hash check says nothing about vulnerable dependencies inside the artifact")


def case_05_unauthorized_build_runner():
    return _malicious_but_consistent(
        "5", "a hash check does not identify who built the artifact")


def case_07_revoked_signing_key():
    return _malicious_but_consistent(
        "7", "no signing keys exist in a hash-only deployment; a holder of any "
             "formerly trusted upload credential publishes artifact and digest together")


def case_08_prohibited_configuration():
    return _malicious_but_consistent(
        "8", "a hash check does not evaluate configuration content against policy")


def case_09_downgrade():
    host = ReleaseHost()
    old = b"FLIGHT-SW-v0\x00" + os.urandom(4096)
    host.upload("fw-v0.bin", old)  # genuine, but superseded, release
    received, digest = host.fetch("fw-v0.bin")
    installed = hash_only_deploy(received, digest)
    return {"case": "9", "caught": not installed,
            "reason": "an old release has a valid digest; version order is not checked"}


APPLICABLE_CASES: dict[str, Callable[[], dict]] = {
    "1": case_01_binary_not_from_source,
    "2": case_02_missing_or_false_provenance,
    "3": case_03_incomplete_sbom,
    "4": case_04_vulnerable_dependency,
    "5": case_05_unauthorized_build_runner,
    "6": case_06_modified_in_transit,
    "7": case_07_revoked_signing_key,
    "8": case_08_prohibited_configuration,
    "9": case_09_downgrade,
}

SENSITIVITY_CASES: dict[str, Callable[[], dict]] = {
    "6b": case_06b_digest_rewritten,
}

OUT_OF_SCOPE = {
    "10": "Installation state is outside a pre-install integrity check.",
    "11": "A hash check has no runtime health concept.",
    "12": "A hash check has no attestation of running software.",
    "13": "A hash check has no ground/spacecraft state reconciliation.",
    "14": "A hash check has no recovery-image or rollback concept.",
    "15": "A hash check has no operational-telemetry consistency concept.",
}


def run_baseline(n_trials: int = 30) -> dict:
    results: dict = {}
    for case, fn in {**APPLICABLE_CASES, **SENSITIVITY_CASES}.items():
        trials = [fn() for _ in range(n_trials)]
        caught = sum(1 for t in trials if t["caught"])
        results[case] = {
            "applicable": True,
            "sensitivity_variant": case in SENSITIVITY_CASES,
            "n_trials": n_trials,
            "caught_count": caught,
            "detection_rate": caught / n_trials,
            "sample_reason": trials[0]["reason"],
        }
    for case, reason in OUT_OF_SCOPE.items():
        results[case] = {"applicable": False, "reason": reason}
    return results


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path

    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    res = run_baseline(n)
    for c in [str(i) for i in range(1, 16)] + ["6b"]:
        r = res[c]
        if r["applicable"]:
            print(f"#{c:>2}: {r['caught_count']}/{r['n_trials']} rejected - {r['sample_reason']}")
        else:
            print(f"#{c:>2}: out of scope - {r['reason']}")
    out = Path(__file__).parent.parent / "results" / "phase9_hash_baseline.json"
    out.write_text(json.dumps(res, indent=2))
    print(f"Wrote {out}")
