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

## Current state (Phase 7, 2026-08-03): real F´ build CONFIRMED WORKING

The real F´ build now works — confirmed on the user's Docker-capable Mac
after fixing the Dockerfile's install step (the original assumed `pip
install -e .` on a bare framework clone, which has no setup.py/
pyproject.toml; see `Legal-Data-Sourcing-Notes.md` § 5 change log). See
`confirmed-build.json` for the exact pinned tag, binary hash, and build
date.

The resulting binary (the framework's own bundled `Ref` reference
deployment, at `build-artifacts/Linux/Ref/bin/Ref` inside the Docker
run's `build-output/`, gitignored) is wired into the pipeline as the
**`"fprime-real"` stack** in `src/target_stack.py`, alongside the
original stand-in (`"fprime"`). Smoke-tested through the full S0-S2
lifecycle successfully.

**Two things this does NOT mean**, stated plainly:

1. **Reproducibility has not been verified** — `build.py` copies this
   one confirmed binary rather than recompiling F´ from scratch on every
   pipeline call (a full build takes ~24s just for the final compile
   step, incompatible with this pipeline's sub-second-call design). The
   pipeline's `reproducible=True` for this stack is a trivial copy-
   integrity check, not a real two-independent-builds comparison. See
   `confirmed-build.json`'s `reproducibility_note`.
2. **S3+ conditions don't work yet against this real binary** — the
   `Ref` binary is a network server that waits for a GDS connection
   (`-a`/`-p` flags), not a short-lived deterministic CLI program.
   `health_check.py` raises `NotImplementedError` for this stack rather
   than silently mislabeling it. See Threat-Model.md "Phase 7 findings."

## Background (Phase 6, sandbox-constrained — same limitation as cfs-app/ originally had)

The authoring sandbox had no Docker, no cmake, and no root access, so the
real F´ framework could not be built or tested there originally. To keep
Phase 6 honest and unblocked, the pipeline ran against a small
**stand-in artifact** (`stub-component-app/`) instead — a trivial C++
program that mimics an F´ component's telemetry-producing role without
being F´ itself. That stand-in (`"fprime"` in `target_stack.py`) still
exists and is still the fast, fully-reproducible stack the Phase 6
automated evaluation ran against — it is not being retired.

**Any metrics collected against `stub-component-app` remain
pipeline/architecture-generalization validation only, not
spacecraft-software results** — see STATUS.md "Claims status" for the
exact wording to use. Metrics against `"fprime-real"` are a step closer
but still capped at `PRELIMINARY_INTERNAL_ONLY` per the two caveats above.

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
3. `src/target_stack.py`'s `"fprime-real"` entry already points at
   `build-output/build-artifacts/Linux/Ref/bin/Ref` — no code change
   needed, just run the Docker build to (re)populate that path locally.

## Directory contents

- `stub-component-app/` — the Phase 6 stand-in artifact (trivial C++
  program, architecturally distinct from stack #1's C stub)
- `Dockerfile` — reproducible build environment for the real F´ framework
  (confirmed working 2026-08-03 — see `confirmed-build.json`)
- `confirmed-build.json` — provenance record for the real build (pinned
  tag, binary hash, build date, known limitations)
- `build-output/` — gitignored; created locally by running the Docker
  build above
