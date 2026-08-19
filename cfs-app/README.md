# Target artifact under test

## Current state (Phase 7, 2026-08-03): real cFS build CONFIRMED WORKING

The real NASA cFS build now works — confirmed on the user's Docker-capable
Mac after two rounds of Dockerfile fixes (the original file's build
invocation didn't match the cFS bundle repo's actual Make-based build
system; see `Legal-Data-Sourcing-Notes.md` § 5 change log for the full
story). See `confirmed-build.json` for the exact pinned tag, binary hash,
and build date.

The resulting binary (`exe/cpu1/core-cpu1` inside the Docker run's
`build-output/`, gitignored — see "Getting the real build running" below
to regenerate it) is wired into the pipeline as the **`"cfs-real"` stack**
in `src/target_stack.py`, alongside the original stand-in (`"cfs"`).
Smoke-tested through the full S0-S2 lifecycle (build → provenance → SBOM
→ signing → ground authorization → uplink → onboard verification →
installation) successfully — see STATUS.md "Claims status" for exactly
what is and isn't citable from this yet.

**One thing this does NOT mean**, stated plainly so results aren't
overclaimed:

1. **Reproducibility has not been verified.** `src/build/build.py` no
   longer compiles this stack from source on every pipeline run (a real
   cFS build takes minutes; this pipeline is designed around
   sub-second calls) — it copies the one binary that was actually built.
   The pipeline's own `reproducible=True` flag for this stack is a
   trivial copy-integrity check, not a real two-independent-builds
   comparison. See `confirmed-build.json`'s `reproducibility_note`.

**Update (ISSUE-003, resolved):** an earlier version of this document
stated that S3+ conditions (attestation, health check, rollback) did not
work against this real binary, because `core-cpu1` is a long-running
process with no fixed, checkable stdout exit pattern the way the stub
has. That limitation was resolved by extending `src/health/health_check.py`
with a persistent-process check mode that waits for a genuine,
empirically determined boot-success log line from the binary's own
stdout rather than treating the absence of a crash as a health signal.
S3-S5 now run against `cfs-real` and are exercised in the full 30-trial
evaluation (`evaluation/results/phase6_report_cfs-real.md`). See
`ISSUES-AND-FIXES-LOG.md` ISSUE-003 and Threat-Model.md "Phase 7
findings" for the full history.

## Background (Phase 1, sandbox-constrained)

The Claude sandbox that authored the initial Phase 1 pipeline had no
Docker, no cmake, and no root access, so the real NASA cFS build could
not be built or tested there. To keep Phase 1 honest and unblocked, the
pipeline ran end-to-end against a small **stand-in artifact**
(`stub-telemetry-app/`) instead — a trivial C program that mimics a cFS
sample app's role without being cFS itself. That stand-in (`"cfs"` in
`target_stack.py`) still exists and is still the fast, fully-reproducible
stack every automated evaluation (Phases 1-6) ran against — it is not
being retired, just no longer the *only* option.

**Any metrics collected against `stub-telemetry-app` remain
pipeline-mechanism validation only, not spacecraft-software results** —
do not cite them as such (see STATUS.md "Claims status" section). Metrics
against `"cfs-real"` are a step closer but still capped at
`PRELIMINARY_INTERNAL_ONLY` per the two caveats above.

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
   This clones NASA cFS at the pinned tag (see `Dockerfile` — pinned per
   Legal-Data-Sourcing-Notes.md § 3a, never vendored into this repo) and
   builds it via `make native_std.prep && make native_std.install`,
   writing the resulting binaries to `build-output/exe/` (gitignored —
   this must be regenerated locally; it is not committed).
3. `src/target_stack.py`'s `"cfs-real"` entry already points at
   `build-output/exe/cpu1/core-cpu1` — no code change needed, just run
   the Docker build to (re)populate that path locally.

## Directory contents

- `stub-telemetry-app/` — the Phase 1 stand-in artifact (trivial C program)
- `Dockerfile` — reproducible build environment for the real cFS sample
  app (confirmed working 2026-08-03 — see `confirmed-build.json`)
- `confirmed-build.json` — provenance record for the real build (pinned
  tag, binary hash, build date, known limitations)
- `build-output/` — gitignored; created locally by running the Docker
  build above
- `build-output-verify/` — gitignored; a second, independent rebuild used
  only for the Phase 7 reproducibility-verification pass (see
  Implementation-Plan.md Phase 7), never the artifact the pipeline itself
  points at
