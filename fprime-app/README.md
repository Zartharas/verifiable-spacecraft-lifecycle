# Target artifact under test — stack #2 (Phase 6, generalizability)

## Why a second stack, and why F Prime

`cfs-app/` (Phases 1-5) evaluated the S0-S5 assurance ladder against one
stand-in artifact informed by NASA's cFS: a message-bus C architecture.
PRD.md § 8 ("Generalizability risk") and Research-Paper-Outline.md flag
that a single-stack evaluation caps the venue ceiling and invites the
reviewer objection "single stack, doesn't generalize." Phase 6 exists to
address that directly.

**NASA JPL's F´ (F Prime)** was chosen as the second stack because it is:

- A **real, actively-used flight software framework** — component-driven
  architecture, used on real missions (e.g., the Mars Ingenuity
  helicopter), not a toy example invented for this project.
- **Architecturally distinct from cFS**: component/port-based rather than
  message-bus based, and its generated code is C++ rather than C — so a
  second stand-in built for it can't accidentally reuse cFS's exact
  toolchain assumptions.
- **Open-source and legally clean**: Apache License 2.0, copyright
  California Institute of Technology, "United States Government
  Sponsorship acknowledged" (verified directly from
  `github.com/nasa/fprime`'s `LICENSE.txt`) — same legal category as cFS,
  see `docs/Legal-Data-Sourcing-Notes.md` § 2/3a.
- **Publicly hosted with a stable, tagged release**: latest tag `v4.2.2`
  as of 2026-08-03 (verified via `github.com/nasa/fprime/releases`).

## Current state (Phase 6, sandbox-constrained — same limitation as cfs-app/)

The authoring sandbox still has no Docker, no cmake, and no root access,
so the real F´ framework (cloning the repo, running its code generator,
building a component) could not be built or tested there — the same
constraint documented in `cfs-app/README.md` for the real cFS build.

To keep Phase 6 honest and unblocked, the pipeline runs against a small
**stand-in artifact** (`stub-component-app/`) instead — a trivial C++
program that mimics an F´ component's telemetry-producing role (compiled
binary produced by source, moved through the same lifecycle as stack #1)
without being F´ itself.

**This file exists so nobody mistakes the stub for the real F´ framework
when reading results later.** Any metrics collected against
`stub-component-app` are pipeline/architecture-generalization validation
only, not spacecraft-software results, and not a claim that the assurance
ladder has been validated against two real flight-software frameworks —
see STATUS.md "Claims status" for the exact wording to use.

## What Phase 6 actually demonstrates

Re-running the S0-S5 pipeline, its 15-case attack matrix, and the Phase 5
evaluation harness against this second, architecturally distinct stand-in
— with **zero changes** to `condition.py`, `evidence_store/`, `signing/`,
`ground_authorization/`, `uplink_sim/`, `onboard_verification/`,
`installation/`, `attestation/`, `health/` (logic), `rollback/`,
`policy/`, or `operational_monitoring/` — demonstrates that those modules'
design is stack-agnostic. Only two small adapters needed a `stack`
parameter: `src/build/build.py` (source location + compiler) and
`src/health/health_check.py` (expected deterministic output), both driven
by `src/target_stack.py`'s registry. See Technical-Design-Document.md
§ 7f for the full writeup.

## Getting the real F´ build running (do this on your Mac, which has Docker)

1. Build the Docker image:
   ```
   cd fprime-app
   docker build -t verifiable-spacecraft-lifecycle-fprime .
   ```
2. Run a build inside it:
   ```
   docker run --rm -v "$(pwd)/build-output:/output" verifiable-spacecraft-lifecycle-fprime
   ```
   This clones NASA's F´ framework at a pinned tag (see `Dockerfile` for
   the exact tag — pinned per Legal-Data-Sourcing-Notes.md § 3a-equivalent
   policy, never vendored into this repo) and builds a reference
   component, writing the resulting binary and a build log to
   `build-output/`.
3. Once that works, `src/target_stack.py`'s `"fprime"` entry should be
   pointed at the real binary output instead of the stub — update
   `source_dir`/`binary_name` there. Update this README and
   `docs/Technical-Design-Document.md` § 7f with confirmation once
   verified working.

## Directory contents

- `stub-component-app/` — the Phase 6 stand-in artifact (trivial C++
  program, architecturally distinct from stack #1's C stub)
- `Dockerfile` — reproducible build environment for the real F´ framework
  (untested in the authoring sandbox; needs to be run and verified on a
  Docker-capable machine, same status as `cfs-app/Dockerfile`)
