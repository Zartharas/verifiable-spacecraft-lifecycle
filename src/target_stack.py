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

**Both are stand-in artifacts, not the real frameworks.** Neither cFS nor
F´ is actually built or run here — see each stack's README for why (no
Docker/cmake/root in the authoring sandbox) and STATUS.md "Claims status"
for how to cite results against them honestly. Phase 6's claim is
narrower and more defensible than "validated against two real flight
software frameworks": it is "the S0-S5 ladder's mechanisms and evidence
schema required zero changes to generalize across two architecturally
distinct stand-in artifacts; only the two stack-specific adapters
(build + health-check) differ."
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


@dataclasses.dataclass(frozen=True)
class Stack:
    name: str
    source_dir: Path
    source_filename: str
    binary_name: str
    compiler: str  # "gcc" or "g++" — see build.py::_compile
    expected_health_output: tuple[str, ...]
    description: str


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
}


def get(stack_name: str) -> Stack:
    if stack_name not in STACKS:
        raise ValueError(f"Unknown stack '{stack_name}'. Known: {list(STACKS)}")
    return STACKS[stack_name]
