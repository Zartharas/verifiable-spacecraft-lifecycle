"""
Target-stack registry — Phase 6 generalizability mechanism.

Phases 1-5 built and evaluated the S0-S5 assurance ladder against a
single stand-in artifact (`cfs-app/stub-telemetry-app`, informed by
NASA's cFS: a message-bus C architecture). Every pipeline stage except
`build.py` and `health_check.py` already took a `binary_path` and worked
on it generically (sign, SBOM, provenance, attestation, partitions,
rollback, policy, monitoring, authorization evidence — none of them care
what language or architecture produced the binary). Only `build.py`
(hardcoded source directory + `gcc`-specific compile command) and
`health_check.py` (hardcoded expected stdout pattern) were coupled to the
Phase 1 stub's specific shape.

This module is the fix: a small registry describing each target stack's
source location, compiler, and expected deterministic output, so
`build.py` and `health_check.py` can be parameterized by `stack` instead
of hardcoding one. This is what makes the claim "the assurance ladder
generalizes across target stacks" testable at all — see
Technical-Design-Document.md § 7f for the full rationale and
Threat-Model.md "Phase 6 results" for what running the full evaluation
against a second stack actually showed.

Two stacks are registered:

- **"cfs"** — the original Phase 1-5 stand-in, informed by NASA's cFS
  (Core Flight System): a message-bus C architecture. See
  `cfs-app/README.md`. Default for every existing call site, so nothing
  in Phases 1-5 changes behavior.
- **"fprime"** — the Phase 6 stand-in, informed by NASA JPL's F´ (F
  Prime): a component-driven C++ framework used on real flight missions
  (e.g., the Mars Ingenuity helicopter). See `fprime-app/README.md`.
  Deliberately a different language (C++ vs. C) and a different
  deterministic output shape, specifically so that "the pipeline works
  against stack #2" can't be explained away as "it just happened to also
  be a trivial C program with the same stdout format."

**"cfs" and "fprime" are stand-in artifacts, not the real frameworks.**
Neither cFS nor F´ is actually built by these two entries — see each
stack's README for why (no Docker/cmake/root in the authoring sandbox)
and STATUS.md "Claims status" for how to cite results against them
honestly. Phase 6's claim from those two entries alone is narrower and
more defensible than "validated against two real flight software
frameworks": it is "the S0-S5 ladder's mechanisms and evidence schema
required zero changes to generalize across two architecturally distinct
stand-in artifacts; only the two stack-specific adapters (build +
health-check) differ."

**"cfs-real" and "fprime-real"** (added once the user actually ran both
Dockerfiles successfully on a Docker-capable machine) point at the
*genuine* compiled binaries instead of a stub. These use
`prebuilt_binary_path` rather than `source_dir`/`source_filename`/
`compiler` — `build.py` copies the already-built binary instead of
compiling from source. This is a deliberate, documented departure from
the stub stacks' "compile twice, diff the hashes" reproducibility model:
a full NASA framework build takes minutes, not milliseconds, and doing
it twice on every single `pipeline.run()` call (as the stub stacks do) is
incompatible with how this pipeline is used (single calls run in a
fraction of a second; the Phase 5/6 evaluation harness alone makes ~135
calls per stack). See `build.py`'s docstring and
`cfs-app/confirmed-build.json` / `fprime-app/confirmed-build.json` for
the full reproducibility-claim caveat this implies, and
Technical-Design-Document.md § 7g for the decision writeup.

**Neither real binary fits the exact-match `expected_health_output` model**
— both are long-running processes (cFS's `core-cpu1` loops forever once
it reaches `OPERATIONAL` state; F´'s `Ref` binary waits for a network GDS
connection and retries indefinitely), not short-lived deterministic CLI
programs that print a fixed pattern and exit. Confirmed empirically on a
Docker-capable machine (see ISSUES-AND-FIXES-LOG.md ISSUE-003):
`core-cpu1` reaches `OPERATIONAL` state within ~50ms and shuts down
cleanly on SIGTERM; `Ref` prints `Hit Ctrl-C to quit` as its very first
line of output (before any network activity), then keeps retrying a GDS
connection forever, and does not exit on its own — it must be terminated.

`"cfs-real"`/`"fprime-real"` therefore use a second, distinct health-check
mode: `boot_success_markers` (a persistent-process model — launch, watch
stdout for a specific real boot-success log line within
`boot_timeout_seconds`, then terminate) instead of
`expected_health_output` (an exact-match model — run to completion, diff
full stdout). `Stack.health_check_mode` picks the right mode; `"cfs"`/
`"fprime"` keep `expected_health_output` and are unaffected. See
`health_check.py` for the persistent-process implementation and
`docs/Technical-Design-Document.md` § 7g for the decision writeup.

**Docker-execution fallback (ISSUE-007).** Both real binaries are Linux
ELF executables, built inside an Ubuntu 22.04 Docker container — they
are only guaranteed to be directly executable on a Linux host. Running
the pipeline on a non-Linux host (confirmed: macOS) hits `OSError: [Errno
8] Exec format error` the moment `health_check.py` tries to launch the
binary directly, since the host kernel can't exec a foreign binary
format outside Docker's virtualization layer. `docker_image` +
`container_binary_path` record how to re-run the exact same binary
*inside* the already-built Docker image instead (`docker run --rm
<image> <container_binary_path> <launch_args>`) — `health_check.py`
tries direct execution first and only falls back to this when it hits
`ENOEXEC` specifically, so environments that genuinely can run the
binary directly (Linux CI, this project's own Linux-based test sandbox)
never invoke Docker at all, while environments that can't (macOS)
transparently do. See ISSUES-AND-FIXES-LOG.md ISSUE-007 for the full
writeup of how this was found and why silently treating `ENOEXEC` as "the
build is unhealthy" (the original, wrong behavior) would have been a
fabricated signal, not a measured one.

**Docker mqueue sysctl (ISSUE-008).** Once the Docker fallback above was
actually exercised end-to-end, `cfs-real`'s health check still failed —
not from a timeout, but because `core-cpu1` genuinely failed to
initialize inside the container: cFE's Software Bus creates pipes backed
by POSIX message queues, and Docker Desktop's internal Linux VM ships a
default `/proc/sys/fs/mqueue/msg_max` too low for the queue depth cFE
requests, so `CFE_SB_CreatePipe` fails, `CFE_EVS` reports an init error,
and cFE self-triggers a commanded `PROCESSOR RESET` and exits — all
before ever reaching `OPERATIONAL`. `Stack.docker_sysctls` records
per-stack `--sysctl` overrides to pass to `docker run` (namespaced to the
container, no host changes needed); confirmed fixed via manual `docker
run --sysctl fs.mqueue.msg_max=1024 ...` before wiring it into
`_launch_process`. `fprime-real` doesn't need this — its IPC model
doesn't hit the same limit. See ISSUES-AND-FIXES-LOG.md ISSUE-008.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent


@dataclasses.dataclass(frozen=True)
class Stack:
    name: str
    binary_name: str
    description: str
    # Stub-compile stacks (source-based):
    source_dir: Optional[Path] = None
    source_filename: Optional[str] = None
    compiler: Optional[str] = None  # "gcc" or "g++" — see build.py::_compile
    # Real prebuilt-binary stacks (see module docstring):
    prebuilt_binary_path: Optional[Path] = None
    # Health-check mode 1: exact-match ("did stdout equal exactly this?").
    # Fits short-lived deterministic CLI programs (the "cfs"/"fprime" stubs).
    expected_health_output: Optional[tuple[str, ...]] = None
    # Health-check mode 2: persistent-process ("did a real boot-success log
    # line appear within the timeout window before we killed it?"). Fits
    # long-running flight-software processes ("cfs-real"/"fprime-real") —
    # see ISSUES-AND-FIXES-LOG.md ISSUE-003 and health_check.py.
    launch_args: tuple[str, ...] = ()
    boot_success_markers: Optional[tuple[str, ...]] = None
    boot_timeout_seconds: float = 5.0
    # Docker-execution fallback for persistent-process stacks whose binary
    # isn't directly executable on the current host (ISSUE-007) — see
    # module docstring. Both must be set together, or neither.
    docker_image: Optional[str] = None
    container_binary_path: Optional[str] = None
    # Per-stack `docker run --sysctl` overrides (ISSUE-008) — e.g. cFS's
    # Software Bus needs a higher POSIX-message-queue limit than Docker
    # Desktop's Linux VM ships by default. Only used when launching via
    # the Docker fallback above; ignored for direct execution.
    docker_sysctls: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        is_stub = self.source_dir is not None
        is_prebuilt = self.prebuilt_binary_path is not None
        if is_stub == is_prebuilt:
            raise ValueError(
                f"Stack '{self.name}' must set exactly one of "
                f"(source_dir+source_filename+compiler) or prebuilt_binary_path."
            )
        if self.expected_health_output is not None and self.boot_success_markers is not None:
            raise ValueError(
                f"Stack '{self.name}' must not set both expected_health_output "
                f"(exact-match mode) and boot_success_markers (persistent-process "
                f"mode) — pick exactly one health-check strategy."
            )
        if (self.docker_image is None) != (self.container_binary_path is None):
            raise ValueError(
                f"Stack '{self.name}' must set docker_image and "
                f"container_binary_path together, or neither."
            )

    @property
    def health_check_mode(self) -> str:
        """Which strategy health_check.py should use for this stack."""
        if self.boot_success_markers is not None:
            return "persistent_process"
        if self.expected_health_output is not None:
            return "deterministic_output"
        return "unimplemented"


STACKS: dict[str, Stack] = {
    "cfs": Stack(
        name="cfs",
        source_dir=REPO_ROOT / "cfs-app" / "stub-telemetry-app",
        source_filename="main.c",
        binary_name="stub-telemetry-app",
        compiler="gcc",
        expected_health_output=tuple(f"channel={i} value={i * 2 + 1}" for i in range(4)),
        description="cFS-informed stand-in (message-bus C architecture)",
    ),
    "fprime": Stack(
        name="fprime",
        source_dir=REPO_ROOT / "fprime-app" / "stub-component-app",
        source_filename="main.cpp",
        binary_name="stub-component-app",
        compiler="g++",
        expected_health_output=tuple(f"telemetry.chan{i}={i * 3 + 2}" for i in range(4)),
        description="F Prime-informed stand-in (component-driven C++ architecture)",
    ),
    "cfs-real": Stack(
        name="cfs-real",
        prebuilt_binary_path=REPO_ROOT / "cfs-app" / "build-output" / "exe" / "cpu1" / "core-cpu1",
        binary_name="core-cpu1",
        # No CLI args needed — core-cpu1 reaches OPERATIONAL state even
        # without its configured working directory / startup script (it
        # logs an error about the missing app-load file but the state
        # machine advances anyway; confirmed empirically, see ISSUE-003).
        boot_success_markers=("CFE_ES_Main: CFE_ES_Main entering OPERATIONAL state",),
        boot_timeout_seconds=5.0,
        # Docker fallback (ISSUE-007) — container path per cfs-app/Dockerfile's
        # own build layout (WORKDIR /build/cfs-src, native_std build output).
        docker_image="verifiable-spacecraft-lifecycle-cfs",
        container_binary_path="/build/cfs-src/build-native_std/exe/cpu1/core-cpu1",
        # ISSUE-008 — cFE's Software Bus creates POSIX-message-queue-backed
        # pipes; Docker Desktop's Linux VM ships a default msg_max too low
        # for the queue depth cFE requests, causing CFE_SB_CreatePipe to
        # fail and cFE to self-trigger a commanded PROCESSOR RESET before
        # ever reaching OPERATIONAL. Confirmed fixed via manual
        # `docker run --sysctl fs.mqueue.msg_max=1024 ...` before wiring
        # this in.
        docker_sysctls=(("fs.mqueue.msg_max", "1024"),),
        description="Real NASA cFS build (tag v7.0.1), Docker-built on a Docker-capable machine — see cfs-app/confirmed-build.json",
    ),
    "fprime-real": Stack(
        name="fprime-real",
        prebuilt_binary_path=REPO_ROOT / "fprime-app" / "build-output" / "build-artifacts" / "Linux" / "Ref" / "bin" / "Ref",
        binary_name="Ref",
        # A GDS host/port pair is required by Ref's CLI. No real GDS is
        # running during a health check (this only verifies the process
        # boots correctly, not that a ground station is attached), so
        # Ref will retry the connection forever until terminated — that's
        # fine, the boot-success marker prints long before any network
        # activity. Deliberately a non-standard port to avoid colliding
        # with a real GDS the operator might have running locally.
        launch_args=("-a", "127.0.0.1", "-p", "50999"),
        boot_success_markers=("Hit Ctrl-C to quit",),
        boot_timeout_seconds=5.0,
        # Docker fallback (ISSUE-007) — container path per fprime-app/Dockerfile's
        # own build layout (WORKDIR /build/fprime-src/Ref, its build-artifacts output).
        docker_image="verifiable-spacecraft-lifecycle-fprime",
        container_binary_path="/build/fprime-src/Ref/build-artifacts/Linux/Ref/bin/Ref",
        description="Real NASA JPL F Prime Ref deployment (tag v4.2.2), Docker-built on a Docker-capable machine — see fprime-app/confirmed-build.json",
    ),
}


def get(stack_name: str) -> Stack:
    if stack_name not in STACKS:
        raise ValueError(f"Unknown stack '{stack_name}'. Known: {list(STACKS)}")
    return STACKS[stack_name]
