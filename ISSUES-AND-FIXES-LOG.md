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

**Note:** three real bugs were found and fixed during Phases 4-6
(evidence-tagging bug for test case #6, authorization-evidence overhead
bug, version-ledger cross-stack collision bug) before this log was
actually put into use — they were only documented narratively at the
time, in `docs/Threat-Model.md`'s "Phase N results" sections and
`STATUS.md`'s session log. Backfilled below as ISSUE-004/005/006 once
the log was actually in use (Phase 7). Numbering reflects the order
entries were logged, not the order the bugs actually occurred — 004-006
predate 001-003 chronologically; see each entry's "Found during" for the
real phase. Content here is reconstructed from the existing narrative
write-ups and the actual source fix, not from memory of the original
debugging session.

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

## [ISSUE-003] health_check.py's model doesn't fit real, long-running flight software (resolved)

- **Date found:** 2026-08-03
- **Date resolved:** 2026-08-03
- **Found during:** Phase 7 — attempting to run S3+ conditions against
  the newly-confirmed real `cfs-real`/`fprime-real` binaries
- **Category:** design flaw
- **Severity:** medium (blocked a real capability; no incorrect result was
  ever shipped, since the gap was caught and gated rather than worked
  around)
- **Description:** `src/health/health_check.py` ran the target binary to
  completion via `subprocess.run(..., timeout=5)` and diffed its stdout
  against a fixed expected pattern. Both real binaries are long-running
  processes — `core-cpu1` reaches `OPERATIONAL` state and loops forever;
  `Ref` is a network server that retries a GDS connection forever if none
  is present — so this model doesn't apply. Left unhandled, the
  5-second timeout would raise `subprocess.TimeoutExpired`, which the
  existing `except` clause would have silently treated as an execution
  failure — mislabeling a healthy, genuinely-running flight-software
  process as a broken build.
- **Root cause:** the health-check design was built around the Phase 1-6
  stand-in stubs, which are short-lived deterministic CLI programs by
  construction. That assumption was never revisited against what real
  flight software actually does (run indefinitely), because no real
  binary existed to test it against until this phase.
- **Fix:** designed and implemented a second, distinct health-check
  strategy — `_health_check_persistent_process` in
  `src/health/health_check.py` — selected per-stack via a new
  `Stack.health_check_mode` property in `src/target_stack.py`. It
  launches the binary via `subprocess.Popen`, watches stdout (through a
  background reader thread, so a stalled process still gets a correctly
  bounded check instead of hanging) for a real, per-stack
  `boot_success_markers` substring within `boot_timeout_seconds`, then
  terminates the process (SIGTERM, escalating to SIGKILL) regardless of
  outcome — "still running" is expected and not itself a failure signal;
  only whether the marker actually appeared decides pass/fail. Boot
  markers were derived empirically, not guessed: `core-cpu1` reliably
  prints `CFE_ES_Main: CFE_ES_Main entering OPERATIONAL state` within
  ~50ms of launch (confirmed via direct testing); `Ref` prints
  `Hit Ctrl-C to quit` as its very first line of output, before any
  network activity (also confirmed via direct testing, including a clean
  re-test without a shell-pipe artifact that had previously made `Ref`'s
  actual exit/kill status ambiguous). Test case #11 (`force_fail`) is
  unaffected — it still short-circuits before either strategy runs.
  This is a deliberate non-fabrication design: it never reports "healthy"
  based on absence of a crash or absence of a timeout; only a genuine,
  observed boot-success log line counts.
- **Disclosure status:** n/a
- **Verified fixed:** yes — `tests/test_phase7_real_builds.py` now has
  four real assertions instead of the old fail-loud-only checks:
  `test_cfs_real_s4_happy_path` / `test_fprime_real_s4_happy_path`
  (health check passes, rollback confirms) and
  `test_cfs_real_s4_forced_health_failure_triggers_rollback` /
  `test_fprime_real_s4_forced_health_failure_triggers_rollback` (test
  case #11 against real binaries — forced failure still triggers
  rollback correctly). Also spot-checked that a non-flight-software
  binary (`/bin/true`, which exits instantly with no output) is
  correctly reported unhealthy in ~25ms rather than waiting out the full
  timeout window. Full suite: 41/41 passing, no regressions.

## [ISSUE-004] Test case #6 tagged at the wrong evidence stage (backfilled)

- **Date found:** 2026-08-03
- **Found during:** Phase 4 — building the automated S0-S5 detection
  comparison table (`evaluation/metrics.py::build_comparison_table`),
  which reads pass/fail directly from the evidence store rather than
  from test assertions
- **Category:** bug
- **Severity:** low (no incorrect security decision was ever made — the
  pipeline correctly rejected the tampered update in every run; this was
  an evidence-trail/reporting gap, not a detection failure)
- **Description:** test case #6 (modified update in transit, implemented
  in Phase 1) was tagged at the *injection* point (`uplink`, logged
  `n/a`) instead of the *detection* point
  (`onboard_signature_verification`, logged `fail`). Every other test
  case added in Phases 2-4 tags the record that actually caught the
  attack; #6 was the one inconsistency, introduced in Phase 1 before that
  convention existed. Building the automated comparison table
  immediately surfaced it as `caught=0` in the S0-S5 matrix, despite the
  underlying pipeline test for this case having "passed" for three
  phases straight.
- **Root cause:** Phase 1's original test-case-#6 evidence record was
  written before a project-wide convention (tag the detection record,
  not the injection point) had been established; nothing caught the
  inconsistency because manual pass/fail test assertions don't inspect
  *which* evidence record got the test-case tag, only whether the
  pipeline's return value was correct.
- **Fix:** added an explicit `test_case_injected="6"` tag to the real
  detection-point record in `src/pipeline.py` (the
  `onboard_signature_verification` failure branch, alongside the
  existing `result="fail"` record) rather than only the injection-point
  one. This is a genuinely good example of why automated,
  evidence-store-driven evaluation matters over a manual test suite: the
  manual suite had never revealed that the evidence trail itself was
  incomplete, only the tooling that reads the evidence store directly
  did.
- **Known follow-on effect (not itself a bug):** tagging both the
  injection and detection records for one conceptual test instance
  produced a temporary double-count (`seen=2, caught=1`) in the
  comparison table — the pass/fail signal was correct, just the instance
  count wasn't. Resolved properly in Phase 5, where
  `evaluation/experiment.py` counts test *instances* directly from
  `PipelineResult` fields per trial rather than counting evidence-store
  records at all.
- **Disclosure status:** n/a (this project's own evidence-tagging logic)
- **Verified fixed:** yes — the Phase 4 comparison table correctly shows
  test case #6 as caught at its expected condition; 26/26 tests passing
  at the time, no regressions. See `docs/Threat-Model.md` "Phase 4
  results" for the original write-up this entry is backfilled from.

## [ISSUE-005] Authorization-evidence overhead inflated ~150x by cross-run aggregation (backfilled)

- **Date found:** 2026-08-03
- **Found during:** Phase 5 — the first full evaluation harness run
  (`evaluation/experiment.py`), computing S0-S5 storage overhead
- **Category:** bug
- **Severity:** medium (a real correctness bug in a reported research
  metric — would have produced a materially wrong published number if
  not caught before write-up)
- **Description:** the first full evaluation run reported S5's
  authorization-evidence storage overhead as ~855,655 bytes — two orders
  of magnitude larger than plausible for machine-readable authorization
  evidence on this artifact size. The corrected figure, after the fix
  below, is 5,748 bytes.
- **Root cause:** `src/evidence_store/authorization_evidence.py`'s
  internal `store.for_artifact(hash)` lookup aggregated *every* evidence
  record ever logged for the stand-in stub's build hash across the
  entire evaluation session (the stub's build hash is constant across
  trials, since it's the same source recompiled deterministically), not
  just the records from the current run. Each successive trial's
  authorization-evidence generation pulled in every prior trial's
  records too, compounding across the ~135 calls the Phase 5 harness
  makes per stack. This is the same underlying trap as ISSUE-004: a
  lookup keyed by something that doesn't uniquely identify "this run"
  silently aggregates cross-run noise instead of failing loudly.
- **Fix:** `src/pipeline.py` now passes an explicit, index-sliced
  `records` list containing only the current run's evidence (sliced from
  `_run_evidence_start`, an index captured at the start of that specific
  `run()` call) into `generate_authorization_evidence`, rather than
  letting it query the store by build hash internally.
- **Disclosure status:** n/a (this project's own evaluation-metrics code)
- **Verified fixed:** yes — re-run evaluation harness reported the
  corrected 5,748-byte figure consistently across all 5 repeated trials;
  100% happy-path success/reproducibility across all 6 conditions, 0
  false positives/negatives across all 15 attack cases, 26/26 tests
  passing at the time. See `docs/Threat-Model.md` "Phase 5 results" and
  `docs/PRD.md` § 10 for the corrected baseline this fix established.

## [ISSUE-006] Version ledger was a single global file, not scoped per stack (backfilled)

- **Date found:** 2026-08-03
- **Found during:** Phase 6 — re-running the pipeline against the newly
  added `fprime` stack for the first time
- **Category:** bug
- **Severity:** medium (would have produced a false-positive downgrade
  rejection for any second target stack's legitimate first release — a
  real availability/correctness bug, not a security gap, since it fails
  toward over-rejection rather than under-detection)
- **Description:** approving version 1 for `fprime` — its first-ever
  release — was wrongly flagged as a downgrade attempt (the mechanism
  behind test case #9) immediately after `cfs`'s own test suite had
  already advanced its version counter well past 1, for a stack that had
  never been deployed at all.
- **Root cause:** `src/ground_authorization/version_ledger.py` stored
  "last approved version" in a single global JSON file shared by every
  target stack, rather than one scoped per stack. It conflated "target
  identity" with "the whole evaluation session" — the same category of
  hazard as ISSUE-004 and ISSUE-005 (state that doesn't uniquely
  identify "this run/target" silently produces wrong results instead of
  failing loudly). Nothing about testing `cfs` repeatedly could ever have
  exposed this: a single-stack evaluation has no way to surface a
  cross-stack collision.
- **Fix:** scoped the ledger file per stack (keyed by `stack` name)
  instead of using one shared file across all stacks.
- **Disclosure status:** n/a (this project's own ground-authorization
  code)
- **Verified fixed:** yes — 9 new Phase 6 tests added (35/35 total
  passing, no regressions), including one specifically asserting version
  ledgers are isolated per stack
  (`test_version_ledgers_are_isolated_per_stack` in
  `tests/test_phase6_generalizability.py`). Re-ran the Phase 5 evaluation
  harness against `fprime`: results structurally identical to stack #1
  (100% detection/success/reproducibility, 0 false positives/negatives).
  See `docs/Threat-Model.md` "Phase 6 results" for the original write-up.

## [ISSUE-007] Real-binary health checks crashed with "Exec format error" outside Docker, and the error handling silently mislabeled it as an unhealthy build

- **Date found:** 2026-08-03
- **Found during:** Phase 7 data-gathering — running the full repeated-trial
  evaluation harness (`evaluation/experiment.py cfs-real`) on the user's
  actual Mac (the machine that built the real binaries), for the first
  time. Every prior individual verification of ISSUE-003's fix
  (`tests/test_phase7_real_builds.py`, run via Claude's own Linux-based
  sandbox) had passed — but that sandbox happens to be Linux, where
  direct execution of the real binaries works, so it never exercised
  this path.
- **Category:** bug (two distinct ones, found together)
- **Severity:** high for the error-handling bug (it silently mislabeled
  an environment/config problem as evidence about the artifact's health —
  exactly the kind of fabricated signal this project's health-check
  design principle exists to prevent), medium for the missing
  capability (real S3-S5 evaluation was simply impossible on macOS until
  fixed, a real blocker for gathering paper data, not a security gap)
- **Description:** running `evaluation/experiment.py cfs-real` on macOS
  crashed with `AssertionError: baseline run did not confirm as
  expected: rollback_outcome='recovery_failed', health_ok=False,
  rejected_at='post_install_recovery_failed'`. Tracing it back: launching
  `core-cpu1` (a Linux ELF binary, built inside an Ubuntu 22.04 Docker
  container) directly via `subprocess.Popen` on macOS raises `OSError:
  [Errno 8] Exec format error` — the host kernel refusing to execute a
  foreign binary format, since Docker's virtualization layer (not the
  bare host) is what actually runs Linux binaries on macOS.
  `_health_check_persistent_process`'s original code caught *any*
  `OSError` from `Popen` and recorded it as a "fail" health-check
  evidence record — meaning every single real-stack health check on
  macOS silently reported "unhealthy build" instead of surfacing that
  the real problem was "this host cannot execute this binary format at
  all," a fact true of every build of this stack on this host, not a
  property of this one artifact.
- **Root cause:** two compounding gaps. (1) `target_stack.py`/
  `health_check.py` assumed the Docker-built binary would be executed on
  the same OS it was compiled for, since Docker was only ever used as the
  *build* environment in this project's design — nothing was ever
  actually run outside Docker before this. (2) The `except OSError`
  clause added for ISSUE-003 conflated two very different failure
  classes: a genuinely broken/missing artifact (legitimate health-check
  evidence) vs. a pure host/environment incompatibility (not evidence
  about the artifact at all). Neither gap was caught earlier because
  every previous individual verification happened to run in a Linux
  environment (Claude's own sandbox) where direct execution silently
  works — S0-S2 stages never execute the binary at all (they only hash/
  sign/copy it), so this was the first time any pipeline stage actually
  tried to run the real binary on the user's own Mac.
- **Fix:** added `Stack.docker_image` / `Stack.container_binary_path` to
  `target_stack.py` (both set for `"cfs-real"`/`"fprime-real"`, pointing
  at the already-built Docker images and each binary's path inside its
  container). New `_launch_process()` helper in `health_check.py`
  attempts direct execution first; on `OSError` with `errno == ENOEXEC`
  specifically (never any other `OSError`) it transparently retries via
  `docker run --rm <image> <container_binary_path> <launch_args>`
  instead. If there's no Docker fallback configured, or Docker itself
  fails to launch, it raises `RuntimeError` — deliberately NOT caught by
  the same `except OSError` the caller uses for genuine artifact
  failures, so an environment/config problem can never be silently
  recorded as a misleading per-run health-check "fail." Environments that
  can execute the binary directly (Linux) never invoke Docker at all —
  no added latency, no new dependency there.
- **Disclosure status:** n/a (this project's own execution/error-handling
  logic; not a cFS/F´ upstream issue — Docker being required to run a
  Linux binary on macOS is expected OS behavior, not a bug in either
  framework)
- **Verified fixed:** yes — new `tests/test_issue007_docker_fallback.py`
  (4 tests, run unconditionally, no real binaries or actual Docker
  required) exercises `_launch_process` directly against a synthetic
  "garbage" file that reliably triggers a real `ENOEXEC` on any host,
  confirming: (1) `ENOEXEC` with no Docker fallback configured raises
  `RuntimeError`, not a silent fail; (2) `ENOEXEC` with a Docker fallback
  configured but Docker itself unavailable (true in this authoring
  sandbox) also raises `RuntimeError`; (3) a genuinely missing binary
  still raises a plain `OSError`, preserving the existing, correct
  "artifact is unhealthy" behavior; (4) `Stack.__post_init__` rejects a
  half-configured Docker fallback. Full suite: 45/45 passing (41 + 4 new,
  no regressions). **End-to-end confirmation, same day:** the user
  re-ran `evaluation/experiment.py fprime-real` and the Docker fallback
  worked correctly end-to-end — the full repeated-trial evaluation
  completed successfully against the real F´ binary via `docker run`,
  with no direct-execution errors. (`cfs-real`'s run surfaced a second,
  distinct bug in the same investigation — see ISSUE-008.)

## [ISSUE-008] cFS's Software Bus fails to initialize inside Docker Desktop's default container due to a POSIX message-queue limit

- **Date found:** 2026-08-03
- **Found during:** Phase 7 data-gathering — immediately after ISSUE-007's
  Docker fallback was confirmed working for `fprime-real`, `cfs-real`'s
  evaluation run still failed at the identical point as before
  (`evaluation/experiment.py cfs-real`, scenario_10's baseline call:
  `health_ok=False, rollback_outcome='recovery_failed'`). Since `docker
  run --rm` gives every invocation a fresh, ephemeral container
  filesystem, the earlier "accumulated CDS/EEPROM state" theory (the
  original hypothesis before ISSUE-007 was found) could no longer apply —
  this had to be something else, so it was investigated directly rather
  than re-guessed.
- **Category:** bug (environment/configuration, not a code defect)
- **Severity:** medium (blocked real S3-S5 statistical evaluation for
  `cfs-real` specifically; `fprime-real` was unaffected)
- **Description:** inspecting the actual evidence-store record for the
  failing health check showed 59 lines of genuine `core-cpu1` output,
  ending in: `CFE_EVS_TaskInit: Call to CFE_SB_CreatePipe Failed`,
  `CFE_ES_ExitApp: CORE Application CFE_EVS Had an Init Error`,
  `CFE_ES_ResetCFE: PROCESSOR RESET called from CFE_ES_ResetCFE
  (Commanded)`, `CFE_PSP: Exiting cFE with PROCESSOR Reset status`. This
  is not a timeout or a slow boot — `core-cpu1` was genuinely failing to
  initialize and self-triggering a commanded reset, exiting entirely,
  before ever reaching `OPERATIONAL`.
- **Root cause:** cFE's Software Bus creates pipes backed by POSIX
  message queues. `OS_QueueCreate_Impl`'s own log output pointed directly
  at the cause: "Your queue depth may be too large for the OS to handle.
  Please check the msg_max parameter located in
  /proc/sys/fs/mqueue/msg_max." Docker Desktop's internal Linux VM ships
  a default `msg_max` too low for the queue depth cFE requests — a
  container-kernel configuration limit, unrelated to ISSUE-007's
  exec-format problem, unrelated to the binary or this project's code,
  and not something Claude's own Linux-based test sandbox (different
  kernel defaults, and never actually invoking `docker run` at all) could
  ever have surfaced.
- **Fix:** confirmed via a manual, isolated test first — `docker run --rm
  --sysctl fs.mqueue.msg_max=1024 verifiable-spacecraft-lifecycle-cfs
  /build/cfs-src/build-native_std/exe/cpu1/core-cpu1` — before writing
  any code, to avoid another guess-and-fail cycle. Confirmed: `core-cpu1`
  reached `CFE_ES_Main: CFE_ES_Main entering OPERATIONAL state` and ran
  indefinitely (FLYWHEEL heartbeat messages) until manually interrupted.
  Wired in as a new `Stack.docker_sysctls` field in `target_stack.py`
  (set to `(("fs.mqueue.msg_max", "1024"),)` for `cfs-real` only —
  `fprime-real` doesn't hit this limit and is unaffected), passed through
  as `--sysctl key=value` flags in `health_check.py`'s `_launch_process`
  Docker-fallback command construction. Docker's per-container `--sysctl`
  is namespaced — no changes to the host's Docker Desktop VM or its
  global settings were needed.
- **Disclosure status:** n/a (a Docker Desktop default vs. cFE's resource
  needs — not a cFS code defect, and not this project's own code defect
  either; purely an environment-configuration mismatch between two
  independently-reasonable defaults)
- **Verified fixed:** yes — 2 new tests in
  `tests/test_issue007_docker_fallback.py`
  (`test_docker_sysctls_are_passed_to_docker_run`,
  `test_no_sysctls_means_no_sysctl_flags`) confirm the `--sysctl` flags
  are built correctly and positioned before the image name, and that a
  stack with no `docker_sysctls` configured never gets a stray flag,
  using a monkeypatched `subprocess.Popen` (no real Docker needed to
  verify the command construction itself). Full suite: 47/47 passing.
  **End-to-end confirmation, same day:** the user re-ran
  `evaluation/experiment.py cfs-real` and it completed successfully —
  the full repeated-trial evaluation (5 trials × 6 conditions × 15 attack
  cases) ran against the real `core-cpu1` binary via the Docker fallback
  with the `fs.mqueue.msg_max` sysctl applied. Results: 100%
  happy-path success/reproducibility across all 6 conditions, 100%
  detection across all 15 attack cases, 0 false positives/negatives —
  structurally identical to the stub-artifact and `fprime-real` results.
  See `evaluation/results/phase6_report_cfs-real.md` and
  `docs/Threat-Model.md` "Phase 7 real-stack statistical evaluation
  results."

---

## Notes on responsible disclosure

If a real vulnerability is found in an upstream dependency (cFS itself,
SLSA/in-toto/Sigstore tooling, etc.) rather than in this project's own
code, follow the upstream project's own disclosure process rather than
disclosing it here first — link to the upstream report from this log once
it's public, and note the disclosure timeline in the "Disclosure status"
field above. See `SECURITY.md` for this repo's own policy on findings
reported against this project's code.
