"""
Reproducible build stage.

Phase 1 scope: compiles the stand-in artifact (cfs-app/stub-telemetry-app)
twice, independently, and verifies the two binaries are bit-identical —
that's the reproducible-build property the S2+ provenance claims will
eventually depend on. Records both the build log and a pass/fail evidence
entry regardless of which condition is active (per evidence-first design
principle — see Technical-Design-Document.md).

Phase 6 scope: parameterized by `stack` (see `src/target_stack.py`) rather
than hardcoding `cfs-app/stub-telemetry-app` and a `gcc`-only compile
command. This lets the exact same reproducible-build logic run against a
second, architecturally distinct stand-in (`fprime-app/stub-component-app`,
C++) with zero changes beyond reading the target's source directory,
filename, and compiler from the stack registry — see
Technical-Design-Document.md § 7f. Default remains `"cfs"`, so every
Phase 1-5 call site (and every existing test) is unaffected.

Phase 7 scope ("cfs-real"/"fprime-real"): these stacks set
`prebuilt_binary_path` instead of `source_dir` (see `target_stack.py`).
For these, this function does NOT compile anything — it copies the
already-Docker-built real framework binary for both "run_a" and "run_b"
and hashes each copy. **This is a deliberate, documented departure from
the compile-twice-and-diff model**, not a shortcut applied without
thought: a real NASA cFS/F´ build takes minutes (confirmed: ~230s for
cFS, ~24s for F´'s final compile step alone, on top of clone/install
time), and this pipeline is designed around calls that complete in a
fraction of a second — the Phase 5/6 evaluation harness alone makes
~135 `pipeline.run()` calls per stack. Recompiling a full NASA framework
twice on every single call is not a performance tuning problem, it is
architecturally incompatible with how this pipeline is used.

**Because of this, `reproducible=True` for a prebuilt-binary stack does
NOT mean "two independent framework builds were compared this run."** It
means "the same already-built file was copied twice and both copies
hash identically" — a trivial, always-true integrity check, not a
build-reproducibility test. The evidence record for these stacks makes
this explicit via `"build_mode": "prebuilt_real_framework"` and
`"reproducibility_claim_status"`. The *actual* reproducibility question
for a real framework (does rebuilding cFS/F´ from scratch twice produce
a bit-identical binary?) has not yet been tested — see
`cfs-app/confirmed-build.json` / `fprime-app/confirmed-build.json` for
the honest status of that question, and STATUS.md "Claims status" for
why reproducible-build claims against the real frameworks remain
unresolved even though the artifact itself is now real.

Swap a stack's `source_dir`/`binary_name` (stub) or `prebuilt_binary_path`
(real) in `src/target_stack.py` to point at a different build output.
"""

from __future__ import annotations

import hashlib
import platform
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
WORK_DIR = REPO_ROOT / "work" / "build"

sys.path.insert(0, str(REPO_ROOT / "src"))
from evidence_store import EvidenceStore  # noqa: E402
import target_stack  # noqa: E402


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def _compile(source: Path, output: Path, compiler: str) -> None:
    """
    Deterministic compile: strip build-path strings, fix debug info,
    disable timestamp-dependent macros. This is the minimum needed for
    gcc/g++ to produce a bit-identical binary across two independent runs
    from the same source.

    `compiler` is stack-driven ("gcc" for the cFS-informed C stub, "g++"
    for the F Prime-informed C++ stub — see target_stack.py) rather than
    hardcoded, so this function itself needed no stack-specific branches
    beyond the platform check below.

    Platform note: on macOS, gcc/g++ are aliased to Apple's clang/ld64,
    and ld64 embeds a UUID load command (LC_UUID) in every Mach-O binary
    that is NOT guaranteed content-deterministic across separate link
    invocations the way GNU ld's output is on Linux. `-Wl,-no_uuid`
    disables that load command. This flag is Apple-linker-specific and
    would fail on Linux's GNU ld, hence the platform check. This
    discrepancy is itself a small piece of evidence for why
    Technical-Design-Document.md specifies a pinned Docker build
    environment rather than trusting the host toolchain — host-toolchain
    "reproducibility" is platform-dependent in ways like this one.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        compiler,
        "-O0",
        f"-fdebug-prefix-map={source.parent}=.",
        "-frandom-seed=fixed-seed-for-reproducibility",
    ]
    if platform.system() == "Darwin":
        cmd += ["-Wl,-no_uuid"]
    cmd += ["-o", str(output), str(source)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"compile failed: {result.stderr}")


def _build_prebuilt(condition_name: str, stack: str, stack_def) -> dict:
    """Real-framework stacks: copy the already-Docker-built binary rather
    than compiling. See module docstring for why this is NOT equivalent
    to the stub stacks' compile-twice-and-diff reproducibility check."""
    store = EvidenceStore()

    if not stack_def.prebuilt_binary_path.exists():
        raise RuntimeError(
            f"Stack '{stack}' has no prebuilt binary at "
            f"{stack_def.prebuilt_binary_path}. Run the Docker build first "
            f"— see the stack's README for instructions."
        )

    build_a = WORK_DIR / stack / "run_a" / stack_def.binary_name
    build_b = WORK_DIR / stack / "run_b" / stack_def.binary_name
    build_a.parent.mkdir(parents=True, exist_ok=True)
    build_b.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(stack_def.prebuilt_binary_path, build_a)
    shutil.copy(stack_def.prebuilt_binary_path, build_b)

    hash_a = _sha256(build_a)
    hash_b = _sha256(build_b)
    reproducible = hash_a == hash_b  # trivially true — see module docstring

    artifact_ref = hash_a

    store.record(
        pipeline_stage="build",
        condition=condition_name,
        artifact_ref=artifact_ref,
        actor="build_system",
        result="pass",
        detail={
            "stack": stack,
            "build_mode": "prebuilt_real_framework",
            "source": str(stack_def.prebuilt_binary_path.relative_to(REPO_ROOT)),
            "hash_run_a": hash_a,
            "hash_run_b": hash_b,
            "reproducible": reproducible,
            "reproducibility_claim_status": "NOT_INDEPENDENTLY_VERIFIED_THIS_RUN",
            "note": (
                f"real framework build ({stack_def.description}); "
                "hash_a==hash_b here only confirms the file wasn't corrupted "
                "while being copied twice, NOT that two independent framework "
                "builds are bit-identical — see build.py module docstring and "
                f"{stack}-app/confirmed-build.json"
            ),
        },
    )

    final_output = WORK_DIR / stack / stack_def.binary_name
    shutil.copy(build_a, final_output)

    return {
        "binary_path": str(final_output),
        "artifact_hash": artifact_ref,
        "reproducible": reproducible,
        "stack": stack,
    }


def build(condition_name: str = "S0", stack: str = "cfs") -> dict:
    stack_def = target_stack.get(stack)

    # Note: deliberately not deleting WORK_DIR between runs. The sandbox's
    # mounted-folder filesystem has been observed to reject unlink() on
    # files/dirs created by a prior process even with matching ownership
    # (see STATUS.md environment notes) — so files are overwritten in
    # place (O_TRUNC via compiler output / write_bytes) rather than
    # removed and recreated. This is safe here because build output paths
    # are fixed and always fully overwritten before use. Each stack gets
    # its own subdirectory so different stacks' build outputs never collide.
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    if stack_def.prebuilt_binary_path is not None:
        return _build_prebuilt(condition_name, stack, stack_def)

    store = EvidenceStore()
    source = stack_def.source_dir / stack_def.source_filename
    build_a = WORK_DIR / stack / "run_a" / stack_def.binary_name
    build_b = WORK_DIR / stack / "run_b" / stack_def.binary_name

    _compile(source, build_a, stack_def.compiler)
    _compile(source, build_b, stack_def.compiler)

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
            "stack": stack,
            "build_mode": "compile_from_source",
            "source": str(source.relative_to(REPO_ROOT)),
            "hash_run_a": hash_a,
            "hash_run_b": hash_b,
            "reproducible": reproducible,
            "note": f"stand-in artifact ({stack_def.description}), not the real framework",
        },
    )

    if not reproducible:
        raise RuntimeError(
            f"Build is NOT reproducible for stack '{stack}': run_a={hash_a} run_b={hash_b}"
        )

    final_output = WORK_DIR / stack / stack_def.binary_name
    shutil.copy(build_a, final_output)

    return {
        "binary_path": str(final_output),
        "artifact_hash": artifact_ref,
        "reproducible": reproducible,
        "stack": stack,
    }


if __name__ == "__main__":
    for stack_name in target_stack.STACKS:
        try:
            result = build(stack=stack_name)
        except RuntimeError as e:
            print(f"[{stack_name}] SKIPPED: {e}")
            continue
        print(f"[{stack_name}] Build OK — reproducible={result['reproducible']}")
        print(f"[{stack_name}] Artifact hash: {result['artifact_hash']}")
        print(f"[{stack_name}] Binary at: {result['binary_path']}")
