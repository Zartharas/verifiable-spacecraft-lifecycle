"""
ISSUE-007/ISSUE-008 regression tests — `_launch_process`'s ENOEXEC/
Docker-fallback logic in `src/health/health_check.py`, including the
per-stack `docker_sysctls` override (ISSUE-008 — cFS needs a higher
POSIX message-queue limit than Docker Desktop's Linux VM ships by
default).

Unlike tests/test_phase7_real_builds.py, these do NOT require the real
cFS/F´ binaries to be present, and do NOT require Docker to actually be
installed. They exercise `_launch_process` directly against a synthetic
"garbage" executable file (no shebang, no valid binary magic bytes) that
reliably triggers a real `OSError: [Errno 8] Exec format error` from the
OS itself on any Linux/macOS host — the same error class that surfaced
ISSUE-007 in the first place — without needing a genuine cross-
architecture binary to reproduce it. The `docker_sysctls` tests use a
monkeypatched `subprocess.Popen` instead, since verifying the exact
`docker run` command built doesn't require actually invoking Docker.

Run with: pytest tests/test_issue007_docker_fallback.py -v
"""

import errno
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import health.health_check as health_check  # noqa: E402
from health.health_check import _launch_process  # noqa: E402
import target_stack  # noqa: E402


@pytest.fixture
def garbage_binary(tmp_path) -> Path:
    """A file that is executable but not a valid binary format for any
    host — reliably triggers ENOEXEC, the same error class ISSUE-007
    found being mishandled for real cross-architecture binaries."""
    p = tmp_path / "not_a_real_binary"
    p.write_text("this is not a shebang line and not ELF/Mach-O magic bytes\n")
    p.chmod(p.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return p


def _stack(prebuilt_binary_path: Path, **kwargs) -> target_stack.Stack:
    return target_stack.Stack(
        name="test-stack",
        binary_name="not_a_real_binary",
        description="synthetic stack for ISSUE-007 tests",
        prebuilt_binary_path=prebuilt_binary_path,
        boot_success_markers=("irrelevant",),
        **kwargs,
    )


def test_enoexec_with_no_docker_fallback_raises_runtime_error(garbage_binary):
    """No docker_image configured at all — this must be a loud,
    unambiguous RuntimeError, never a silently-recorded health-check
    failure (that would fabricate a signal about the artifact that isn't
    true — see health_check.py module docstring)."""
    stack_def = _stack(garbage_binary)  # docker_image/container_binary_path default to None
    with pytest.raises(RuntimeError, match="Cannot execute"):
        _launch_process(garbage_binary, stack_def)


def test_enoexec_with_docker_fallback_but_docker_unavailable_raises_runtime_error(garbage_binary):
    """docker_image IS configured, but the `docker` command itself isn't
    available/working in this environment (true in this authoring
    sandbox, which has no Docker) — must still raise loudly, not record
    a misleading health-check failure."""
    stack_def = _stack(
        garbage_binary,
        docker_image="this-image-does-not-exist-anywhere",
        container_binary_path="/bin/true",
    )
    with pytest.raises(RuntimeError, match="Docker fallback also failed"):
        _launch_process(garbage_binary, stack_def)


def test_missing_binary_raises_plain_oserror_not_runtime_error(tmp_path):
    """A genuinely missing/broken artifact (not an ENOEXEC/environment
    problem) must still surface as a plain OSError, exactly as before —
    this is legitimate health-check-failure evidence about the artifact
    itself, and the caller (`_health_check_persistent_process`) relies on
    catching OSError specifically to record it as such."""
    missing = tmp_path / "does_not_exist"
    stack_def = _stack(missing)
    with pytest.raises(OSError) as excinfo:
        _launch_process(missing, stack_def)
    assert not isinstance(excinfo.value, RuntimeError)


def _make_fake_popen(captured_cmds):
    """First call simulates the direct-exec attempt hitting ENOEXEC (the
    real failure mode this bug is about); every subsequent call (the
    Docker fallback) succeeds, just recording the command it was given."""
    calls = {"n": 0}

    class _FakePopen:
        def __init__(self, cmd, **kwargs):
            captured_cmds.append(cmd)
            calls["n"] += 1
            if calls["n"] == 1:
                raise OSError(errno.ENOEXEC, "Exec format error")

    return _FakePopen


def test_docker_sysctls_are_passed_to_docker_run(garbage_binary, monkeypatch):
    """ISSUE-008 — per-stack `docker_sysctls` (e.g. cFS's
    fs.mqueue.msg_max fix) must actually reach the `docker run` command
    as `--sysctl key=value` flags, positioned before the image name."""
    captured_cmds = []
    monkeypatch.setattr(health_check.subprocess, "Popen", _make_fake_popen(captured_cmds))

    stack_def = _stack(
        garbage_binary,
        docker_image="some-image",
        container_binary_path="/some/path",
        docker_sysctls=(("fs.mqueue.msg_max", "1024"), ("fs.mqueue.msgsize_max", "8192")),
    )
    _launch_process(garbage_binary, stack_def)

    assert len(captured_cmds) == 2  # direct attempt (fails fast), then the docker fallback
    docker_cmd = captured_cmds[1]
    assert docker_cmd[:3] == ["docker", "run", "--rm"]
    assert "--sysctl" in docker_cmd
    sysctl_idx = docker_cmd.index("--sysctl")
    assert docker_cmd[sysctl_idx + 1] == "fs.mqueue.msg_max=1024"
    assert docker_cmd[sysctl_idx + 3] == "fs.mqueue.msgsize_max=8192"
    assert docker_cmd.index("some-image") > sysctl_idx  # sysctl flags precede the image name


def test_no_sysctls_means_no_sysctl_flags(garbage_binary, monkeypatch):
    """A stack with no docker_sysctls configured (e.g. fprime-real) must
    not get a stray `--sysctl` flag."""
    captured_cmds = []
    monkeypatch.setattr(health_check.subprocess, "Popen", _make_fake_popen(captured_cmds))

    stack_def = _stack(garbage_binary, docker_image="some-image", container_binary_path="/some/path")
    _launch_process(garbage_binary, stack_def)

    docker_cmd = captured_cmds[1]
    assert "--sysctl" not in docker_cmd


def test_stack_requires_docker_fields_together():
    """Stack.__post_init__ must reject a stack that sets only one of
    docker_image/container_binary_path — half-configured Docker fallback
    is a real config error, not a valid state."""
    with pytest.raises(ValueError, match="docker_image and"):
        target_stack.Stack(
            name="bad-stack",
            binary_name="x",
            description="d",
            prebuilt_binary_path=Path("/nonexistent"),
            boot_success_markers=("x",),
            docker_image="some-image",
            # container_binary_path deliberately omitted
        )
