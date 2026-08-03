# Target artifact under test

## Current state (Phase 1, sandbox-constrained)

The Claude sandbox that authored the initial Phase 1 pipeline has no
Docker, no cmake, and no root access — so the real NASA cFS build
(the intended target artifact per PRD.md and Technical-Design-Document.md)
could not be built or tested there. Building the actual pipeline machinery
(signing, ground authorization, uplink simulation, onboard verification,
evidence store) against a real cFS binary was not possible in that
environment.

To keep Phase 1 honest and unblocked, the pipeline runs end-to-end against
a small **stand-in artifact** (`stub-telemetry-app/`) instead — a trivial
C program that mimics a cFS sample app's role (compiled binary produced
by source, meant to move through the lifecycle) without being cFS itself.
This lets every S0 mechanism (signing, verification, evidence logging) get
built and tested for real now, with the real cFS swapped in as a drop-in
replacement once Docker is available.

**This file exists so nobody mistakes the stub for the real target
artifact when reading results later.** Any metrics collected against
`stub-telemetry-app` are pipeline-mechanism validation only, not
spacecraft-software results — do not cite them as such (see STATUS.md
"Claims status" section).

## Getting the real cFS build running (do this on your Mac, which has Docker)

1. Build the Docker image:
   ```
   cd cfs-app
   docker build -t verifiable-spacecraft-lifecycle-cfs .
   ```
2. Run a build inside it:
   ```
   docker run --rm -v "$(pwd)/build-output:/output" verifiable-spacecraft-lifecycle-cfs
   ```
   This clones NASA cFS at a pinned commit (see `Dockerfile` for the exact
   SHA — pinned per Legal-Data-Sourcing-Notes.md § 3a, never vendored into
   this repo) and builds a sample app, writing the resulting binary and a
   build log to `build-output/`.
3. Once that works, `src/build/build.py` should be pointed at the real
   binary output instead of the stub — that's a one-line change to
   `TARGET_BINARY_PATH` at the top of that file. Update this README and
   `docs/Technical-Design-Document.md` § 7 with the pinned commit SHA once
   confirmed working.

## Directory contents

- `stub-telemetry-app/` — the Phase 1 stand-in artifact (trivial C program)
- `Dockerfile` — reproducible build environment for the real cFS sample app
  (untested in the authoring sandbox; needs to be run and verified on a
  Docker-capable machine)
