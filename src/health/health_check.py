"""
Health validation harness — runs the currently-active installed binary
and checks its output against the expected deterministic pattern for the
active target stack (see `src/target_stack.py`).

Phase 6 scope: parameterized by `stack` rather than hardcoding
cfs-app/stub-telemetry-app's specific "channel=N value=M" output shape.
Each stack registers its own `expected_health_output` — the cFS-informed
stub's four "channel=N value=M" lines, or the F Prime-informed stub's
four "telemetry.chanN=M" lines — so this harness's actual check logic
(run binary, compare stdout line-for-line) needed no stack-specific
branches at all. Default remains `"cfs"`, so Phase 1-5 behavior and tests
are unaffected.

Covers attack matrix test case #11 (failed health check) via the
`force_fail` test hook — simulates a build that runs but misbehaves,
without needing a second broken artifact. Applies identically regardless
of which stack is active.

Phase 7 (ISSUE-003) scope: the two "real" stacks (`"cfs-real"`,
`"fprime-real"`) don't fit the exact-match model at all — both are
long-running processes: cFS's `core-cpu1` reaches an `OPERATIONAL` state
and then loops forever managing the flight software bus; F´'s `Ref`
binary blocks waiting for a network GDS connection and retries
indefinitely if none is present. Running either through
`subprocess.run(..., timeout=5)` would just time out and get misreported
as an unhealthy/failed build — factually wrong for a genuinely-running
flight-software core. Confirmed empirically on a Docker-capable machine
(see ISSUES-AND-FIXES-LOG.md ISSUE-003): `core-cpu1` prints
`CFE_ES_Main: CFE_ES_Main entering OPERATIONAL state` within ~50ms of
startup and shuts down cleanly on SIGTERM; `Ref` prints `Hit Ctrl-C to
quit` as its very first line of output, well before any network activity,
and never exits on its own.

So these two stacks use a second, distinct strategy —
`_health_check_persistent_process`: launch the binary, watch its stdout
(via a background reader thread, since a blocking read would defeat the
timeout) for one of `Stack.boot_success_markers` within
`Stack.boot_timeout_seconds`, then terminate it (SIGTERM, escalating to
SIGKILL if it doesn't exit within 3s) regardless of outcome. Finding the
marker means "the flight-software core booted correctly" — the same
thing the exact-match model verifies for the stub stacks, just via a
substring-within-a-window check instead of a full-output diff, because a
process that never exits can't be diffed against a full expected
transcript. `Stack.health_check_mode` picks the right strategy per
stack; nothing about test case #11 (`force_fail`) changes — that check
runs before either strategy and short-circuits identically for all
stacks.

Phase 7 (ISSUE-007) scope: both real binaries are Linux ELF executables
(built inside an Ubuntu 22.04 Docker container). Running the pipeline on
a non-Linux host hits `OSError: [Errno 8] Exec format error` the moment
this module tries to launch the binary directly — the host kernel can't
exec a foreign binary format outside Docker's virtualization layer.
Confirmed the hard way: gathering real-stack evaluation data on a Mac,
after every prior individual verification of this module had (without
realizing it) been run in a Linux environment where direct execution
happens to work. The original code caught *any* `OSError` from `Popen`
and recorded it as an unhealthy build — which silently mislabeled a pure
host/environment incompatibility as if it were evidence about the
artifact itself, exactly the kind of fabricated signal this module's
whole design is supposed to avoid. `_launch_process` below fixes this:
it attempts direct execution first, and only on `ENOEXEC` specifically
(never any other `OSError`) falls back to re-running the identical
binary *inside* its already-built Docker image
(`Stack.docker_image`/`Stack.container_binary_path`) via `docker run`.
If there's no Docker fallback configured, or Docker itself isn't
available, this raises a distinct, loud error rather than recording a
misleading per-run "fail" — see ISSUES-AND-FIXES-LOG.md ISSUE-007.
"""

from __future__ import annotations

import errno
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_store import EvidenceStore  # noqa: E402
import target_stack  # noqa: E402


def run_health_check(
    installed_binary_path: Path,
    condition_name: str = "S3",
    force_fail: bool = False,
    stack: str = "cfs",
) -> tuple[bool, Optional[str]]:
    store = EvidenceStore()
    import hashlib

    stack_def = target_stack.get(stack)
    mode = stack_def.health_check_mode

    with open(installed_binary_path, "rb") as f:
        artifact_hash = hashlib.sha256(f.read()).hexdigest()

    if force_fail:
        store.record(
            pipeline_stage="health_validation",
            condition=condition_name,
            artifact_ref=artifact_hash,
            actor="health_monitor",
            result="fail",
            detail={"reason": "forced failure (test case #11 simulation)", "stack": stack},
            test_case_injected="11",
        )
        return False, "forced health check failure"

    if mode == "unimplemented":
        raise NotImplementedError(
            f"Stack '{stack}' has no working health-check strategy "
            "(neither expected_health_output nor boot_success_markers set "
            "in target_stack.py)."
        )

    if mode == "persistent_process":
        return _health_check_persistent_process(
            installed_binary_path, condition_name, stack, stack_def, store, artifact_hash
        )

    expected_lines = list(stack_def.expected_health_output)

    try:
        result = subprocess.run(
            [str(installed_binary_path)], capture_output=True, text=True, timeout=5
        )
    except (OSError, subprocess.SubprocessError) as e:
        store.record(
            pipeline_stage="health_validation",
            condition=condition_name,
            artifact_ref=artifact_hash,
            actor="health_monitor",
            result="fail",
            detail={"reason": f"execution failed: {e}", "stack": stack},
            test_case_injected="11",
        )
        return False, f"execution failed: {e}"

    output_lines = [line.strip() for line in result.stdout.strip().splitlines()]
    healthy = result.returncode == 0 and output_lines == expected_lines

    store.record(
        pipeline_stage="health_validation",
        condition=condition_name,
        artifact_ref=artifact_hash,
        actor="health_monitor",
        result="pass" if healthy else "fail",
        detail={
            "stack": stack,
            "returncode": result.returncode,
            "output_matches_expected": output_lines == expected_lines,
        },
        test_case_injected=None if healthy else "11",
    )
    return healthy, None if healthy else "unexpected output or nonzero exit"


def _launch_process(installed_binary_path: Path, stack_def: "target_stack.Stack") -> subprocess.Popen:
    """
    Launch a persistent-process stack's binary, transparently falling
    back to Docker execution if the host can't run this binary format
    directly (ISSUE-007 — see health_check.py module docstring).

    Three distinct outcomes, deliberately not conflated:
    1. Direct execution works (e.g., a Linux host) — used as-is, no
       Docker involved, no extra startup latency.
    2. Direct execution fails with ENOEXEC (a foreign binary format for
       this host, e.g. macOS trying to run a Linux ELF binary) and a
       Docker fallback is configured — transparently retried via
       `docker run --rm [--sysctl k=v ...] <image> <container_binary_path>
       <launch_args>`, which runs the identical binary inside the
       environment it was actually built for. `Stack.docker_sysctls`
       covers container-kernel limits that differ from what the binary
       needs (ISSUE-008 — cFS's Software Bus needs a higher POSIX
       message-queue limit than Docker Desktop's Linux VM ships by
       default; passed as a namespaced `--sysctl`, no host changes
       needed).
    3. Anything else (the binary is genuinely missing, not executable,
       ENOEXEC with no Docker fallback configured, or Docker itself is
       unavailable/fails) — raised, not silently recorded as "unhealthy."
       An artifact-genuinely-broken failure (case: missing/corrupt file)
       is still a legitimate health-check "fail" and is handled by the
       caller's `except OSError`; a pure environment/configuration
       problem (case: ENOEXEC with nothing to fall back to, or Docker
       missing) is raised as `RuntimeError` instead, specifically so it
       is NOT caught by that same `except OSError` — it isn't evidence
       about the artifact at all, and recording it as a per-run "fail"
       would fabricate a misleading signal.
    """
    direct_cmd = [str(installed_binary_path), *stack_def.launch_args]
    try:
        return subprocess.Popen(
            direct_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
        )
    except OSError as e:
        if e.errno != errno.ENOEXEC:
            raise  # genuine artifact problem (missing file, not executable, etc.) — let caller record it
        if not stack_def.docker_image:
            raise RuntimeError(
                f"Cannot execute '{installed_binary_path}' on this host: {e}. "
                f"This is a Linux binary with no Docker fallback configured for "
                f"stack '{stack_def.name}' in target_stack.py. See "
                f"ISSUES-AND-FIXES-LOG.md ISSUE-007."
            ) from e

        sysctl_flags = []
        for key, value in stack_def.docker_sysctls:
            sysctl_flags += ["--sysctl", f"{key}={value}"]
        docker_cmd = [
            "docker", "run", "--rm", *sysctl_flags, stack_def.docker_image,
            stack_def.container_binary_path, *stack_def.launch_args,
        ]
        try:
            return subprocess.Popen(
                docker_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )
        except OSError as docker_e:
            raise RuntimeError(
                f"Cannot execute '{installed_binary_path}' directly on this host "
                f"({e}), and the Docker fallback also failed to launch "
                f"({docker_e}). Is Docker installed, running, and is the image "
                f"'{stack_def.docker_image}' present (docker images)? See "
                f"ISSUES-AND-FIXES-LOG.md ISSUE-007."
            ) from docker_e


def _health_check_persistent_process(
    installed_binary_path: Path,
    condition_name: str,
    stack: str,
    stack_def: "target_stack.Stack",
    store: EvidenceStore,
    artifact_hash: str,
) -> tuple[bool, Optional[str]]:
    """
    Launch a long-running flight-software binary, watch its stdout for a
    real boot-success log line within a bounded window, then terminate it.

    Why a background reader thread instead of a plain readline() loop: a
    blocking readline() would defeat the point of a timeout if the process
    ever stalls without producing output (it would hang the whole check,
    and by extension the pipeline, indefinitely). The reader thread does
    the blocking I/O; the main loop just polls the shared `lines` list
    against a wall-clock deadline, so a stalled/hung process still gets
    correctly reported as unhealthy rather than hanging this function.

    This never fabricates a signal: "healthy" means the specific,
    real, per-stack boot-success substring genuinely appeared in the
    binary's own output — not "it didn't crash" and not "it didn't time
    out." A binary that hangs before printing its boot marker, or prints
    nothing, or exits early, is correctly reported unhealthy. See
    ISSUES-AND-FIXES-LOG.md ISSUE-003 for why this replaced an earlier,
    rejected approach of treating a subprocess timeout as an implicit pass.

    Execution itself may need a Docker fallback (ISSUE-007) — see
    `_launch_process`.
    """
    try:
        proc = _launch_process(installed_binary_path, stack_def)
    except OSError as e:
        store.record(
            pipeline_stage="health_validation",
            condition=condition_name,
            artifact_ref=artifact_hash,
            actor="health_monitor",
            result="fail",
            detail={"reason": f"execution failed: {e}", "stack": stack},
            test_case_injected="11",
        )
        return False, f"execution failed: {e}"

    lines: list[str] = []

    def _reader():
        try:
            for line in proc.stdout:
                lines.append(line.rstrip("\n"))
        except (OSError, ValueError):
            pass

    reader_thread = threading.Thread(target=_reader, daemon=True)
    reader_thread.start()

    markers = stack_def.boot_success_markers
    deadline = time.monotonic() + stack_def.boot_timeout_seconds
    found_marker: Optional[str] = None
    checked = 0
    while time.monotonic() < deadline:
        if len(lines) > checked:
            snapshot = lines[checked:]
            checked = len(lines)
            for line in snapshot:
                for marker in markers:
                    if marker in line:
                        found_marker = marker
                        break
                if found_marker:
                    break
        if found_marker:
            break
        if proc.poll() is not None:
            break  # process exited on its own before we saw a marker or timed out
        time.sleep(0.02)

    # Always terminate — a healthy real flight-software core is *expected*
    # to still be running at this point (that's the whole reason it needed
    # this check instead of the exact-match one), so "still running" is not
    # itself a failure signal; only the marker check above decides pass/fail.
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
    reader_thread.join(timeout=1)

    healthy = found_marker is not None
    store.record(
        pipeline_stage="health_validation",
        condition=condition_name,
        artifact_ref=artifact_hash,
        actor="health_monitor",
        result="pass" if healthy else "fail",
        detail={
            "stack": stack,
            "health_check_mode": "persistent_process",
            "boot_success_markers": list(markers),
            "marker_found": found_marker,
            "boot_timeout_seconds": stack_def.boot_timeout_seconds,
            "captured_output_lines": len(lines),
            "note": (
                "process launched, watched for a real boot-success log "
                "marker within a bounded window, then terminated — this "
                "measures 'did the flight-software core boot correctly', "
                "not 'did it run to completion and match fixed output' "
                "(see health_check.py module docstring)"
            ),
        },
        test_case_injected=None if healthy else "11",
    )
    return healthy, None if healthy else (
        f"no boot-success marker found within {stack_def.boot_timeout_seconds}s"
    )
