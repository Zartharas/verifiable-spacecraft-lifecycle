"""
Phase 8 real-baseline comparison — python-tuf (The Update Framework),
run unmodified against the same 15-case attack matrix used to evaluate the
S0-S5 assurance ladder (see Threat-Model.md § 3).

Motivation (Research-Paper-Outline.md § 4, item 6): the paper's central
claim — that terrestrial supply-chain frameworks don't address
spacecraft-specific constraints — was previously asserted, not measured.
This module builds a real, working TUF repository + `tuf.ngclient.Updater`
client (the actual upstream library, `pip install tuf`, not a
reimplementation) and exercises it against every one of the 15 test cases,
recording case-by-case whether TUF's *own* security guarantees catch it.

Scope decision, stated explicitly: this uses TUF's low-level Metadata API
directly (the same API python-tuf's own `examples/manual_repo/basic_repo.py`
demonstrates), with one Ed25519-equivalent (ECDSA, via
`securesystemslib.signer.CryptoSigner`) key per top-level role and no
delegation — the simplest correct TUF repository, not a
maximally-hardened one. This is a deliberate, honest choice: it tests
TUF's *core* guarantees (metadata integrity, key revocation via root
rotation, rollback protection), not a maximally-hardened deployment's
edge cases, which would not change which of the 15 cases are in-scope for
TUF at all (see `NOT_APPLICABLE` below) — those are architectural gaps in
TUF's specification, not implementation-depth gaps that a fancier
repository setup would close.

No live HTTP server is used. `_LocalFetcher` reads `file://` URLs directly
from disk — this keeps the baseline in-process and deterministic, exactly
like every other stage in this project's own pipeline (a direct function
call, not a live network service), and avoids introducing a second,
unrelated source of flakiness (port binding, thread lifecycle) into a
comparison whose entire point is measuring TUF's own cryptographic
guarantees, not this test harness's networking code.
"""

from __future__ import annotations

import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator, Optional

from securesystemslib.signer import CryptoSigner

from tuf.api.exceptions import DownloadError
from tuf.api.metadata import (
    Metadata,
    MetaFile,
    Root,
    Snapshot,
    TargetFile,
    Targets,
    Timestamp,
)
from tuf.api.serialization.json import JSONSerializer
from tuf.ngclient import Updater
from tuf.ngclient.config import UpdaterConfig
from tuf.ngclient.fetcher import FetcherInterface

PRETTY = JSONSerializer(compact=False)


def _in(days: float) -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=days)


class _LocalFetcher(FetcherInterface):
    """Reads `file://` URLs from local disk instead of a real network
    fetch — see module docstring for why this project deliberately avoids
    a live HTTP server for this baseline."""

    def _fetch(self, url: str) -> Iterator[bytes]:
        if not url.startswith("file://"):
            raise ValueError(f"_LocalFetcher only supports file:// URLs, got: {url}")
        path = Path(url[len("file://") :])
        if not path.exists():
            from tuf.api.exceptions import DownloadHTTPError

            raise DownloadHTTPError(f"{path} not found", 404)
        data = path.read_bytes()

        def _iter() -> Iterator[bytes]:
            yield data

        return _iter()


def build_repo(repo_dir: Path, target_name: str, target_bytes: bytes, version: int = 1):
    """Creates a minimal, single-key-per-top-level-role TUF repository at
    `repo_dir`, containing one target file at version `version`. Returns
    (roles, signers) so callers can publish further versions or rotate
    keys for subsequent test steps, mirroring python-tuf's own
    `examples/manual_repo/basic_repo.py` pattern."""
    metadata_dir = repo_dir / "metadata"
    targets_dir = repo_dir / "targets"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    targets_dir.mkdir(parents=True, exist_ok=True)

    target_path = targets_dir / target_name
    target_path.write_bytes(target_bytes)

    roles: dict = {}
    signers: dict = {}

    roles["targets"] = Metadata(Targets(version=version, expires=_in(7)))
    roles["targets"].signed.targets[target_name] = TargetFile.from_file(
        target_name, str(target_path)
    )

    roles["snapshot"] = Metadata(Snapshot(expires=_in(7)))
    roles["timestamp"] = Metadata(Timestamp(expires=_in(1)))
    roles["root"] = Metadata(Root(expires=_in(365)))

    for name in ["targets", "snapshot", "timestamp", "root"]:
        signers[name] = CryptoSigner.generate_ecdsa()
        roles["root"].signed.add_key(signers[name].public_key, name)

    roles["snapshot"].signed.meta["targets.json"] = MetaFile(version=version)
    roles["timestamp"].signed.snapshot_meta = MetaFile(version=roles["snapshot"].signed.version)

    for name in ["targets", "snapshot", "timestamp", "root"]:
        roles[name].sign(signers[name])

    for name in ["root", "targets", "snapshot"]:
        filename = f"{roles[name].signed.version}.{roles[name].signed.type}.json"
        roles[name].to_file(str(metadata_dir / filename), serializer=PRETTY)
    roles["timestamp"].to_file(str(metadata_dir / "timestamp.json"), serializer=PRETTY)

    return roles, signers


def publish_new_version(
    repo_dir: Path, roles: dict, signers: dict, target_name: str, target_bytes: bytes, new_version: int
) -> None:
    """Publishes a legitimate new release: new target content, targets
    metadata version bump, snapshot/timestamp updated to match, all signed
    with the repo's current keys."""
    metadata_dir = repo_dir / "metadata"
    (repo_dir / "targets" / target_name).write_bytes(target_bytes)

    roles["targets"].signed.version = new_version
    roles["targets"].signed.targets[target_name] = TargetFile.from_file(
        target_name, str(repo_dir / "targets" / target_name)
    )
    roles["targets"].signatures.clear()
    roles["targets"].sign(signers["targets"])
    roles["targets"].to_file(
        str(metadata_dir / f"{new_version}.targets.json"), serializer=PRETTY
    )

    roles["snapshot"].signed.meta["targets.json"].version = new_version
    roles["snapshot"].signed.version += 1
    roles["snapshot"].signatures.clear()
    roles["snapshot"].sign(signers["snapshot"])
    roles["snapshot"].to_file(
        str(metadata_dir / f"{roles['snapshot'].signed.version}.snapshot.json"), serializer=PRETTY
    )

    roles["timestamp"].signed.snapshot_meta.version = roles["snapshot"].signed.version
    roles["timestamp"].signed.version += 1
    roles["timestamp"].signatures.clear()
    roles["timestamp"].sign(signers["timestamp"])
    roles["timestamp"].to_file(str(metadata_dir / "timestamp.json"), serializer=PRETTY)


def run_client(
    repo_dir: Path, client_dir: Path, target_name: str, expected: Optional[bytes]
) -> tuple[bool, str]:
    """Runs a real `tuf.ngclient.Updater` refresh + target download against
    the repo at `repo_dir`, using `client_dir` as this client's persistent
    local trust store (reused across calls to exercise rollback/replay
    protection, which depends on the client's previously-trusted metadata
    being cached locally — the same reason the real client example uses a
    persistent `metadata_dir`). Raises whatever `tuf.api.exceptions` /
    `tuf.ngclient` itself raises on failure — this function does not
    catch or reinterpret those; callers decide what a raised exception
    means for a given test case."""
    client_dir.mkdir(parents=True, exist_ok=True)
    download_dir = client_dir / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)

    bootstrap = None
    if not (client_dir / "root.json").exists():
        bootstrap = (repo_dir / "metadata" / "1.root.json").read_bytes()

    updater = Updater(
        metadata_dir=str(client_dir),
        metadata_base_url=f"file://{repo_dir}/metadata/",
        target_dir=str(download_dir),
        target_base_url=f"file://{repo_dir}/targets/",
        fetcher=_LocalFetcher(),
        bootstrap=bootstrap,
        # This repo writes target files under their plain target name (no
        # hash-prefixed filename) even though root.consistent_snapshot is
        # True for metadata — simpler for this minimal repo, and irrelevant
        # to the actual security guarantees under test (hash/length
        # verification still happens on the downloaded bytes regardless of
        # what the file on the mirror happens to be named).
        config=UpdaterConfig(prefix_targets_with_hash=False),
    )
    updater.refresh()
    info = updater.get_targetinfo(target_name)
    if info is None:
        raise RuntimeError(f"target {target_name!r} not found in repo metadata")
    path = updater.download_target(info)
    data = Path(path).read_bytes()
    if expected is not None and data != expected:
        raise RuntimeError(
            "downloaded bytes did not match expected content — TUF accepted "
            "something it should not have; this would be a genuine TUF bug, "
            "not an expected test outcome"
        )
    return True, path


# ---------------------------------------------------------------------------
# The three test cases TUF's own core security guarantees can actually be
# exercised against. See NOT_APPLICABLE below for the other 12 and why.
# ---------------------------------------------------------------------------


def case_06_modified_in_transit() -> dict:
    """Test case #6 analogue: a target file is swapped on the mirror/in
    transit after the repository published metadata declaring its correct
    hash/length. TUF's core target-integrity guarantee should catch this
    — this is the single guarantee TUF is most fundamentally designed
    around."""
    tmp = Path(tempfile.mkdtemp(prefix="tuf_baseline_case06_"))
    try:
        repo_dir, client_dir = tmp / "repo", tmp / "client"
        build_repo(repo_dir, "firmware.bin", b"GOOD-FIRMWARE-V1", version=1)
        (repo_dir / "targets" / "firmware.bin").write_bytes(b"TAMPERED-PAYLOAD-XYZ")

        caught, reason = False, None
        try:
            run_client(repo_dir, client_dir, "firmware.bin", expected=b"GOOD-FIRMWARE-V1")
        except Exception as e:  # noqa: BLE001 — we want to classify *any* rejection
            caught, reason = True, f"{type(e).__name__}: {e}"
        return {"case": "6", "caught": caught, "reason": reason}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def case_07_revoked_key() -> dict:
    """Test case #7 analogue: a previously-trusted signing key is revoked
    (removed from root's authorized keys for the targets role, root
    re-signed and re-published), then an attacker (holding the old,
    now-revoked key — e.g. because it leaked) tries to publish a new
    malicious release signed only with that old key. TUF's root-rotation
    /key-revocation mechanism should reject it."""
    tmp = Path(tempfile.mkdtemp(prefix="tuf_baseline_case07_"))
    try:
        repo_dir, client_dir = tmp / "repo", tmp / "client"
        roles, signers = build_repo(repo_dir, "firmware.bin", b"GOOD-FIRMWARE-V1", version=1)
        old_targets_signer = signers["targets"]

        # Legitimate initial trust establishment (client "installs" v1).
        run_client(repo_dir, client_dir, "firmware.bin", expected=b"GOOD-FIRMWARE-V1")

        # Revoke the old targets key, rotate in a new one. Root key itself
        # stays the same across this rotation, so the new root version is
        # trivially still validly signed against both the previously-
        # trusted root and its own new content — no dual-threshold
        # complexity needed for this specific, narrow test.
        new_targets_signer = CryptoSigner.generate_ecdsa()
        roles["root"].signed.revoke_key(old_targets_signer.public_key.keyid, "targets")
        roles["root"].signed.add_key(new_targets_signer.public_key, "targets")
        roles["root"].signed.version += 1
        roles["root"].signatures.clear()
        roles["root"].sign(signers["root"])
        roles["root"].to_file(
            str(repo_dir / "metadata" / f"{roles['root'].signed.version}.root.json"),
            serializer=PRETTY,
        )
        signers["targets"] = new_targets_signer

        # Attacker, still holding the OLD (now-revoked) targets key,
        # forges a new malicious release signed only with it.
        (repo_dir / "targets" / "firmware.bin").write_bytes(b"MALICIOUS-PAYLOAD-FROM-REVOKED-KEY")
        forged = Metadata(Targets(version=2, expires=_in(7)))
        forged.signed.targets["firmware.bin"] = TargetFile.from_file(
            "firmware.bin", str(repo_dir / "targets" / "firmware.bin")
        )
        forged.sign(old_targets_signer)
        forged.to_file(str(repo_dir / "metadata" / "2.targets.json"), serializer=PRETTY)

        roles["snapshot"].signed.meta["targets.json"].version = 2
        roles["snapshot"].signed.version += 1
        roles["snapshot"].signatures.clear()
        roles["snapshot"].sign(signers["snapshot"])
        roles["snapshot"].to_file(
            str(repo_dir / "metadata" / f"{roles['snapshot'].signed.version}.snapshot.json"),
            serializer=PRETTY,
        )
        roles["timestamp"].signed.snapshot_meta.version = roles["snapshot"].signed.version
        roles["timestamp"].signed.version += 1
        roles["timestamp"].signatures.clear()
        roles["timestamp"].sign(signers["timestamp"])
        roles["timestamp"].to_file(str(repo_dir / "metadata" / "timestamp.json"), serializer=PRETTY)

        caught, reason = False, None
        try:
            run_client(repo_dir, client_dir, "firmware.bin", expected=None)
        except Exception as e:  # noqa: BLE001
            caught, reason = True, f"{type(e).__name__}: {e}"
        return {"case": "7", "caught": caught, "reason": reason}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def case_09_downgrade() -> dict:
    """Test case #9 analogue: after a client has already trusted version 2
    of a release, the repository/mirror is rolled back to serve version 1's
    (validly signed, but older) metadata and target again — a classic TUF
    rollback attack. TUF's version-monotonicity check (enforced via the
    client's persisted local trusted metadata) should reject it."""
    tmp = Path(tempfile.mkdtemp(prefix="tuf_baseline_case09_"))
    try:
        repo_dir, client_dir = tmp / "repo", tmp / "client"
        roles, signers = build_repo(repo_dir, "firmware.bin", b"GOOD-FIRMWARE-V1", version=1)

        v1_timestamp_bytes = (repo_dir / "metadata" / "timestamp.json").read_bytes()

        # Legitimate initial trust establishment at v1.
        run_client(repo_dir, client_dir, "firmware.bin", expected=b"GOOD-FIRMWARE-V1")

        # Legitimate new release, v2 — client trusts this too.
        publish_new_version(repo_dir, roles, signers, "firmware.bin", b"GOOD-FIRMWARE-V2", new_version=2)
        run_client(repo_dir, client_dir, "firmware.bin", expected=b"GOOD-FIRMWARE-V2")

        # Attacker/misconfigured mirror rolls the served timestamp back to
        # the old, validly-signed-but-lower-version v1 timestamp (the v1
        # snapshot/targets/root files are still on disk too, consistent-
        # snapshot style, so this alone is enough to attempt the replay).
        (repo_dir / "metadata" / "timestamp.json").write_bytes(v1_timestamp_bytes)

        caught, reason = False, None
        try:
            run_client(repo_dir, client_dir, "firmware.bin", expected=None)
        except Exception as e:  # noqa: BLE001
            caught, reason = True, f"{type(e).__name__}: {e}"
        return {"case": "9", "caught": caught, "reason": reason}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


APPLICABLE_CASES = {
    "6": case_06_modified_in_transit,
    "7": case_07_revoked_key,
    "9": case_09_downgrade,
}


# ---------------------------------------------------------------------------
# The other 12 test cases: not run, because TUF's specification has no
# mechanism that could plausibly catch them. Recorded explicitly (with a
# stated reason each) rather than silently omitted, so the comparison
# table is honest about what was actually tested vs. what's an
# architectural non-goal of TUF itself.
# ---------------------------------------------------------------------------

NOT_APPLICABLE = {
    "1": "Same underlying mechanism as case #6 (target hash/length "
    "verification) — not run as a separate scenario to avoid double- "
    "counting one TUF guarantee as two 'wins.'",
    "2": "Build provenance (binary->source->build-environment->builder "
    "chain, SLSA/in-toto-style) is entirely outside TUF's specification. "
    "TUF verifies that a target's hash/length matches what a trusted "
    "signer declared, never how or where it was built.",
    "3": "SBOM / component-inventory tracking is out of scope for TUF's "
    "specification.",
    "4": "Known-vulnerability scanning of dependencies is out of scope for "
    "TUF's specification.",
    "5": "TUF's delegation model authorizes which key may sign which "
    "role's metadata, not which build system produced a given artifact — "
    "there is no 'authorized builder identity' concept in the core spec.",
    "8": "No policy/configuration-evaluation language exists in TUF's "
    "core specification (custom target metadata fields exist, but there "
    "is no built-in policy engine to evaluate them against).",
    "10": "Installation itself (writing to a partition, A/B slots, etc.) "
    "is entirely outside TUF's scope — TUF's responsibility ends at "
    "'deliver a verified target file to the client.'",
    "11": "No runtime health-check concept exists in TUF's specification.",
    "12": "TUF has metadata *expiration* (a related but distinct freshness "
    "guarantee protecting the repository's own metadata, not a runtime "
    "attestation quote about currently-running software) — a partial "
    "conceptual overlap, not an equivalent mechanism, so not scored as "
    "covering this case.",
    "13": "No ground/spacecraft state-reconciliation concept exists in "
    "TUF's specification.",
    "14": "No rollback/recovery-image concept exists — TUF does not "
    "manage installed system state at all, only metadata/target delivery.",
    "15": "No operational-telemetry-consistency concept exists in TUF's "
    "specification.",
}


def run_baseline(n_trials: int = 30) -> dict:
    """Runs each of the 3 applicable cases `n_trials` times (deterministic
    cryptographic checks — repetition here confirms no flakiness in this
    test harness itself, not a probabilistic detection rate) and returns a
    full 15-case comparison structure, explicit about which cases were
    actually exercised vs. architecturally out of scope."""
    results: dict = {}
    for case, fn in APPLICABLE_CASES.items():
        trials = [fn() for _ in range(n_trials)]
        caught_count = sum(1 for t in trials if t["caught"])
        results[case] = {
            "applicable": True,
            "n_trials": n_trials,
            "caught_count": caught_count,
            "detection_rate": caught_count / n_trials,
            "sample_reason": trials[0]["reason"],
        }
    for case, reason in NOT_APPLICABLE.items():
        results[case] = {"applicable": False, "reason": reason}
    return results


def print_summary(results: dict) -> None:
    print("=== python-tuf baseline vs. 15-case attack matrix ===\n")
    for case in [str(i) for i in range(1, 16)]:
        r = results[case]
        if r["applicable"]:
            print(
                f"  #{case:>2}: APPLICABLE — {r['caught_count']}/{r['n_trials']} caught "
                f"({r['detection_rate']:.0%}) — e.g. {r['sample_reason']}"
            )
        else:
            print(f"  #{case:>2}: N/A — {r['reason']}")


if __name__ == "__main__":
    import json
    import sys

    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    results = run_baseline(n_trials=n)
    print_summary(results)

    out_path = Path(__file__).parent.parent / "results" / "phase8_tuf_baseline.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote {out_path}")
