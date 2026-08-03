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

**Neither real binary has a working `expected_health_output` entry yet**
(set to `None`) — both are long-running processes (cFS's `core-cpu1`
loops forever once it reaches `OPERATIONAL` state; F´'s `Ref` binary
waits for a network GDS connection), not short-lived deterministic CLI
programs that print a fixed pattern and exit. `health_check.py` raises
`NotImplementedError` if asked to health-check a stack with no
`expected_health_output` — see Threat-Model.md "Phase 7 findings" for the
full writeup of why this needed a real design decision rather than a
quick patch, and STATUS.md for what's blocked on it (S3+ conditions
against the real binaries).
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
    # None means "no working health-check strategy yet" — see docstring.
    expected_health_output: Optional[tuple[str, ...]] = None

    def __post_init__(self):
        is_stub = self.source_dir is not None
        is_prebuilt = self.prebuilt_binary_path is not None
        if is_stub == is_prebuilt:
            raise ValueError(
                f"Stack '{self.name}' must set exactly one of "
                f"(source_dir+source_filename+compiler) or prebuilt_binary_path."
            )


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
        expected_health_output=None,  # see module docstring — long-running process
        description="Real NASA cFS build (tag v7.0.1), Docker-built on a Docker-capable machine — see cfs-app/confirmed-build.json",
    ),
    "fprime-real": Stack(
        name="fprime-real",
        prebuilt_binary_path=REPO_ROOT / "fprime-app" / "build-output" / "build-artifacts" / "Linux" / "Ref" / "bin" / "Ref",
        binary_name="Ref",
        expected_health_output=None,  # see module docstring — waits for a network GDS connection
        description="Real NASA JPL F Prime Ref deployment (tag v4.2.2), Docker-built on a Docker-capable machine — see fprime-app/confirmed-build.json",
    ),
}


def get(stack_name: str) -> Stack:
    if stack_name not in STACKS:
        raise ValueError(f"Unknown stack '{stack_name}'. Known: {list(STACKS)}")
    return STACKS[stack_name]
