# Issues & Fixes Log

Every bug, security finding, or design flaw discovered during this project
gets an entry here — both because it makes for a clean, citable
contribution history on GitHub, and because some findings (e.g., a real
vulnerability in a dependency or in cFS itself) may warrant a responsible
disclosure per `SECURITY.md` rather than just a code fix.

**Template for each entry — copy this block for every new issue:**

```
## [ISSUE-###] Short title

- **Date found:** YYYY-MM-DD
- **Found during:** (phase / test case / activity)
- **Category:** bug | security finding | design flaw | dependency vulnerability
- **Severity:** low | medium | high | critical
- **Description:** what happened / what was found
- **Root cause:** why it happened
- **Fix:** what was changed, with commit hash/link once pushed
- **Disclosure status:** n/a | reported upstream (link) | pending disclosure timeline | disclosed publicly (date)
- **Verified fixed:** yes/no, how verified (e.g., regression test added)
```

---

## Log

**Note:** several real bugs were found and fixed during Phases 4-6
(evidence-tagging bug for test case #6, authorization-evidence overhead
bug, version-ledger cross-stack collision bug) before this log was
actually put into use — those are documented narratively in
`docs/Threat-Model.md`'s "Phase N results" sections and `STATUS.md`'s
session log instead. Retroactively backfilling proper entries here for
those is still outstanding — see STATUS.md "What's next." Starting with
Phase 7, new findings get a real entry here.

## [ISSUE-001] cFS Dockerfile used the wrong build invocation

- **Date found:** 2026-08-03
- **Found during:** Phase 7 — first real attempt to run `cfs-app/Dockerfile`
  on a Docker-capable machine
- **Category:** bug
- **Severity:** low (build-tooling only; no security or data-integrity impact)
- **Description:** The Dockerfile's final build step ran `cp -r
  cfe/cmake/sample_defs sample_defs && mkdir build && cd build && cmake
  -DSIMULATION=native -DCMAKE_BUILD_TYPE=debug .. && make
  mission-install`, which failed with `CMake Error: The source directory
  "/build/cfs-src" does not appear to contain CMakeLists.txt.`
- **Root cause:** the cFS bundle repository's actual build system is a
  top-level Makefile that wraps cmake internally with correct paths
  (`make native_std.prep` / `make native_std.install`); it is not a bare
  cmake project invokable the way the Dockerfile assumed. This assumption
  was never tested before being written, since the authoring sandbox has
  no Docker.
- **Fix:** replaced the build step with `make native_std.prep && make
  native_std.install`, confirmed against the repo's own README ("Build
  and Run Quick Start" section) rather than guessed a second time. Also
  corrected the pinned tag from `v7.0.0` to `v7.0.1` (the actual current
  official release) while re-verifying.
- **Disclosure status:** n/a (this project's own Dockerfile, not an
  upstream cFS bug)
- **Verified fixed:** yes — Docker build succeeded on retry; resulting
  `core-cpu1` binary boots and logs a genuine CFE startup sequence
  through `OPERATIONAL` state. Recorded in `cfs-app/confirmed-build.json`.

## [ISSUE-002] F Prime Dockerfile used the wrong tool-installation method

- **Date found:** 2026-08-03
- **Found during:** Phase 7 — first real attempt to run
  `fprime-app/Dockerfile` on a Docker-capable machine
- **Category:** bug
- **Severity:** low (build-tooling only)
- **Description:** The Dockerfile ran `pip install -e .` against a bare
  clone of `nasa/fprime`, which failed with `ERROR: file:///build/fprime-src
  does not appear to be a Python project: neither 'setup.py' nor
  'pyproject.toml' found.`
- **Root cause:** the F´ framework repository has no `setup.py`/
  `pyproject.toml` at its root — its tool suite (`fprime-tools`,
  `fprime-gds`, `fprime-fpp`, etc.) ships as separate PyPI packages,
  pinned in the repo's own `requirements.txt`. `pip install -e .` was
  never a valid way to install them; this was never tested before being
  written, for the same reason as ISSUE-001.
- **Fix:** replaced with `pip install -r requirements.txt` (installing
  the pinned tool versions, including a pip-installed `cmake` since the
  bundled `Ref` deployment requires CMake ≥3.26, newer than Ubuntu 22.04's
  apt package), then built the framework's own bundled `Ref` reference
  deployment via `fprime-util generate && fprime-util build`. Confirmed
  against the framework's own installation guide
  (`docs/getting-started/installing-fprime.md`, "Working With An
  Existing Project" section).
- **Disclosure status:** n/a (this project's own Dockerfile)
- **Verified fixed:** yes — Docker build succeeded on retry; resulting
  `Ref` binary runs and correctly rejects an unrecognized CLI flag with a
  real usage message. Recorded in `fprime-app/confirmed-build.json`.

## [ISSUE-003] health_check.py's model doesn't fit real, long-running flight software (open)

- **Date found:** 2026-08-03
- **Found during:** Phase 7 — attempting to run S3+ conditions against
  the newly-confirmed real `cfs-real`/`fprime-real` binaries
- **Category:** design flaw
- **Severity:** medium (blocks a real capability; no incorrect result was
  shipped because the gap was caught and gated rather than worked around)
- **Description:** `src/health/health_check.py` runs the target binary to
  completion via `subprocess.run(..., timeout=5)` and diffs its stdout
  against a fixed expected pattern. Both real binaries are long-running
  processes — `core-cpu1` reaches `OPERATIONAL` state and loops forever;
  `Ref` is a network server waiting for a GDS connection — so this model
  doesn't apply. Left unhandled, the 5-second timeout would raise
  `subprocess.TimeoutExpired`, which the existing `except` clause would
  have silently treated as an execution failure — mislabeling a healthy,
  genuinely-running flight-software process as a broken build.
- **Root cause:** the health-check design was built around the Phase 1-6
  stand-in stubs, which are short-lived deterministic CLI programs by
  construction. That assumption was never revisited against what real
  flight software actually does (run indefinitely), because no real
  binary existed to test it against until this phase.
- **Fix (partial):** `run_health_check` now raises `NotImplementedError`
  explicitly for any stack with `expected_health_output=None`
  (`"cfs-real"`/`"fprime-real"` both set this) rather than letting the
  timeout produce a misleading pass/fail result. This is a deliberate
  fail-loud choice, not a full fix — S3+ conditions (attestation, health
  check, rollback) still cannot be exercised against either real binary.
  A real fix requires designing a persistent-process health-check
  strategy (e.g., launch + wait N seconds + check for an expected
  boot-log substring + terminate) and is intentionally left open pending
  a decision on how to proceed — see `docs/Implementation-Plan.md` Phase 7.
- **Disclosure status:** n/a
- **Verified fixed:** partially — `tests/test_phase7_real_builds.py`'s
  `test_cfs_real_health_check_not_yet_implemented` and
  `test_fprime_real_health_check_not_yet_implemented` confirm the
  fail-loud behavior; no test yet exists for the (not-yet-implemented)
  real fix.

---

## Notes on responsible disclosure

If a real vulnerability is found in an upstream dependency (cFS itself,
SLSA/in-toto/Sigstore tooling, etc.) rather than in this project's own
code, follow the upstream project's own disclosure process rather than
disclosing it here first — link to the upstream report from this log once
it's public, and note the disclosure timeline in the "Disclosure status"
field above. See `SECURITY.md` for this repo's own policy on findings
reported against this project's code.
