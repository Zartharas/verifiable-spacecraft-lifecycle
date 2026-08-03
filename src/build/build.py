"""
Reproducible build stage.

Phase 1 scope: compiles the stand-in artifact (cfs-app/stub-telemetry-app)
twice, independently, and verifies the two binaries are bit-identical —
that's the reproducible-build property the S2+ provenance claims will
eventually depend on. Records both the build log and a pass/fail evidence
entry regardless of which condition is active (per evidence-first design
principle — see Technical-Design-Document.md).

Swap TARGET_SOURCE_DIR to point at a real cFS build output once the
Dockerfile in cfs-app/ has been run on a Docker-capable machine — see
cfs-app/README.md.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
TARGET_SOURCE_DIR = REPO_ROOT / "cfs-app" / "stub-telemetry-app"
WORK_DIR = REPO_ROOT / "work" / "build"

sys.path.insert(0, str(REPO_ROOT / "src"))
from evidence_store import EvidenceStore  # noqa: E402


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def _compile(source: Path, output: Path) -> None:
    """
    Deterministic compile: strip build-path strings, fix debug info,
    disable timestamp-dependent macros. This is the minimum needed for
    gcc to produce a bit-identical binary across two independent runs
    from the same source.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "gcc",
        "-O0",
        f"-fdebug-prefix-map={source.parent}=.",
        "-frandom-seed=fixed-seed-for-reproducibility",
        "-o",
        str(output),
        str(source),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"compile failed: {result.stderr}")


def build(condition_name: str = "S0") -> dict:
    store = EvidenceStore()
    source = TARGET_SOURCE_DIR / "main.c"
    build_a = WORK_DIR / "run_a" / "stub-telemetry-app"
    build_b = WORK_DIR / "run_b" / "stub-telemetry-app"

    # Note: deliberately not deleting WORK_DIR between runs. The sandbox's
    # mounted-folder filesystem has been observed to reject unlink() on
    # files/dirs created by a prior process even with matching ownership
    # (see STATUS.md environment notes) — so files are overwritten in
    # place (O_TRUNC via compiler output / write_bytes) rather than
    # removed and recreated. This is safe here because build output paths
    # are fixed and always fully overwritten before use.
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    _compile(source, build_a)
    _compile(source, build_b)

    hash_a = _sha256(build_a)
    hash_b = _sha256(build_b)
    reproducible = hash_a == hash_b

    artifact_ref = hash_a  # binary content hash is the artifact's identity downstream

    store.record(
        pipeline_stage="build",
        condition=condition_name,
        artifact_ref=artifact_ref,
        actor="build_system",
        result="pass" if reproducible else "fail",
        detail={
            "source": str(source.relative_to(REPO_ROOT)),
            "hash_run_a": hash_a,
            "hash_run_b": hash_b,
            "reproducible": reproducible,
            "note": "stand-in artifact per cfs-app/README.md, not real cFS",
        },
    )

    if not reproducible:
        raise RuntimeError(
            f"Build is NOT reproducible: run_a={hash_a} run_b={hash_b}"
        )

    final_output = WORK_DIR / "stub-telemetry-app"
    shutil.copy(build_a, final_output)

    return {
        "binary_path": str(final_output),
        "artifact_hash": artifact_ref,
        "reproducible": reproducible,
    }


if __name__ == "__main__":
    result = build()
    print(f"Build OK — reproducible={result['reproducible']}")
    print(f"Artifact hash: {result['artifact_hash']}")
    print(f"Binary at: {result['binary_path']}")
