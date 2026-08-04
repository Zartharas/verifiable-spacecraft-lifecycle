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

## [ISSUE-009] macOS build-reproducibility fix (`-Wl,-no_uuid`) now makes stub binaries fail to load entirely

- **Date found:** 2026-08-04
- **Found during:** Phase 8, running the just-added ablation study and
  adaptive-attacker scenarios (plus the routine 30-trial evaluation) on
  the user's Mac for the first time since the trial-count bump. Every S4+
  happy-path run failed health validation with `returncode: -6` (SIGABRT)
  on both the `cfs` and `fprime` stub stacks — a plain, no-attack-injected
  run, not one of the 15 attack cases.
- **Category:** bug (regression, environment/toolchain-version-dependent)
- **Severity:** high — blocked the entire evaluation suite (happy path,
  all 15 attack cases, the new ablation/adaptive scenarios) against both
  stub stacks on macOS; did not affect the Linux sandbox at all, which is
  exactly why it went unnoticed until now.
- **Description:** Running the crashing binary directly
  (`work/partitions/A/installed_binary`) surfaced the real error, which
  `health_check.py`'s `subprocess.run(..., capture_output=True)` had been
  silently discarding (it only logs `stdout`/`returncode`, never
  `stderr`): `dyld[...]: missing LC_UUID load command`, then `abort`
  (exit 134). Confirmed precisely, not guessed: compiling the exact same
  source without the `-Wl,-no_uuid` flag ran cleanly (exit 0, correct
  output) on the same machine.
- **Root cause:** `src/build/build.py`'s `_compile()` has added
  `-Wl,-no_uuid` on Darwin since the very first Phase 1 session, to make
  ld64's per-link output bit-identical across two independent compiles
  (ld64 otherwise embeds a fresh random UUID load command on every
  link). That flag was verified working on the user's Mac at the time.
  Between then and now, macOS/Xcode updated (confirmed via `sw_vers`:
  macOS 26.5.2, build 25F84; `clang --version`: Apple clang 21.0.0) to a
  dyld that now hard-requires the LC_UUID load command at load time —
  what used to be a load-time non-issue is now a fatal `abort()`. The
  flag itself, not anything in this project's own pipeline logic, is the
  direct cause.
- **Fix:** Removed `-Wl,-no_uuid` from `_compile()` entirely. Added
  `_mask_macho_uuid()` (parses the Mach-O header/load-command list
  directly, zeroes the 16 UUID bytes inside any `LC_UUID` command it
  finds, no-ops on anything that isn't a little-endian 64-bit Mach-O
  binary — i.e., a complete no-op on Linux/ELF) and
  `_sha256_reproducibility()`, used **only** for the build-reproducibility
  comparison (`hash_a_masked == hash_b_masked`) inside `build()` — never
  for the artifact's identity hash (`artifact_ref`/downstream
  `artifact_hash`), which still uses the real, unmasked file content.
  This preserves the original "two independent compiles are the same
  code" guarantee without touching the shipped binary's loadability at
  all — the same "characterize the exact non-deterministic bytes rather
  than hide them" approach already used for the real cFS embedded
  build-timestamp finding (see `docs/Threat-Model.md` "Phase 7
  reproducibility verification"). Does not handle FAT/universal
  (multi-architecture) Mach-O binaries — stated limitation (falls back to
  no-op for those too), not a silent gap.
- **Disclosure status:** n/a — this project's own code/flag choice, not
  an upstream dependency issue.
- **Verified fixed:** Linux: full 41/41 regression suite passes unchanged
  (confirms the masking function is a true no-op there — `_mask_macho_uuid`
  tested directly against non-Mach-O bytes too). **macOS: confirmed,
  2026-08-04** — user re-ran the full 30-trial evaluation (happy path,
  all 15 attack cases, Phase 8 ablation study, Phase 8 adaptive-attacker
  scenarios) against both `cfs` and `fprime` stub stacks from a clean
  `work/` directory: all completed cleanly with the exact predicted
  100%/0% rates throughout — no SIGABRT, no load failures. Real
  `cfs-real`/`fprime-real` re-run still pending.

---

## [ISSUE-010] ISSUE-007 regression test silently depended on Docker being absent from the test environment

- **Date found:** 2026-08-04
- **Found during:** re-verifying ISSUE-009's fix on the user's Mac — the
  full test suite ran clean except one unrelated failure:
  `test_enoexec_with_docker_fallback_but_docker_unavailable_raises_runtime_error`
  reported "DID NOT RAISE RuntimeError".
- **Category:** bug (test design flaw — environment-dependent test)
- **Severity:** low — the test gave a false sense of coverage rather than
  masking a real production bug; `_launch_process` itself was never
  wrong.
- **Description:** The test configured a bogus, non-existent Docker
  image and asserted that `_launch_process` raises `RuntimeError` because
  "the `docker` command itself isn't available/working in this
  environment" (its own docstring, written for the original authoring
  sandbox, which has no Docker installed at all). On the user's Mac —
  where Docker Desktop is installed and running, required by Phase 7's
  real-stack work — `docker run --rm this-image-does-not-exist-anywhere
  ...` still launches the `docker` CLI process successfully; the "image
  not found" failure happens later, asynchronously, inside the container
  runtime, not as a Python-level `OSError` from `Popen`. So on any
  machine with Docker actually installed, this test silently stopped
  exercising the code path it claimed to, without ever failing loudly
  about it — until trial count 30 made every test run's environment
  differences matter more, surfacing it now.
- **Root cause:** the test relied on a real, uncontrolled external
  process's failure mode instead of a deterministic mock — a form of the
  same category of hazard this whole log has repeatedly caught elsewhere
  (state or a signal that depends on something outside the test's actual
  control silently producing a misleading result).
- **Fix:** `monkeypatch.setattr(health_check.subprocess, "Popen", ...)`
  to deterministically fail the *second* `Popen` call (the Docker
  fallback attempt) regardless of whether real Docker is present —
  reusing the exact pattern the file's other two Docker-related tests
  already used, for a different reason, two tests below this one.
- **Disclosure status:** n/a — this project's own test code.
- **Verified fixed:** yes — full 41/41 suite passes on both the Linux
  sandbox and the user's Mac (Docker installed) after the fix.

---

## [ISSUE-011] Ground-truth state files (version ledger, partition state) had no integrity protection — Phase 8 red-team finding #1

- **Date found:** 2026-08-04
- **Found during:** the Phase 8 blind (AI) red-team review (see
  Threat-Model.md "Phase 8 independent (blind, AI) red-team review",
  finding #1), independently re-verified against the actual source before
  being logged here.
- **Category:** design flaw / security finding
- **Severity:** high — a single unprivileged filesystem write (resetting
  `last_approved_version` to 0, or hand-editing partition state) could
  bypass downgrade protection or the rollback recovery-image integrity
  check entirely, with no signature or provenance forgery required.
- **Description:** `version_ledger.py` and `partitions.py` both persisted
  their state as bare, unsigned JSON files with plain `json.load`/
  `json.dump` — no HMAC, no signature, no append-only chain. Every
  mechanism built on top (downgrade protection, rollback recovery-image
  integrity) implicitly assumed this side-state was trustworthy, but
  nothing made it tamper-evident.
- **Root cause:** state persisted to a plain file with no integrity
  layer at all — a gap in the original Phase 2/3 design, not a
  regression.
- **Fix:** new `src/state_integrity.py` (HMAC-SHA256 sidecar files,
  symmetric key stored under `keys/`, gitignored) wired into both
  modules' read/write paths. Reads that fail verification, or find a
  deleted-after-protection file, raise `StateIntegrityError`; callers
  (`version_ledger.check_and_advance()`, `pipeline.py`'s
  `trusted_rollback` branch) treat this as a fail-closed denial, never
  as "fresh/empty state." Stated residual limitation: this defends
  against an attacker who can write the state file but not also read the
  HMAC key — it does not defend against an attacker with full filesystem
  access to both. See `state_integrity.py`'s module docstring for the
  full threat-model statement.
- **Disclosure status:** n/a — this project's own design gap.
- **Verified fixed:** yes — `tests/test_phase8_redteam_fixes.py`
  (`test_finding1_*`, 3 tests: tampered ledger, deleted-with-sidecar,
  tampered partition state, all confirmed fail-closed). Full regression
  suite (47 existing tests across all phases) re-run clean; evaluation
  harness, ablation study, and adaptive-attacker scenarios re-run at
  reduced trial counts against `cfs`/`fprime` with identical results to
  before the fix (100%/0% throughout, no drift).

---

## [ISSUE-012] Signing-key revocation failed open on a missing/deleted revocation list — Phase 8 red-team finding #2

- **Date found:** 2026-08-04
- **Found during:** Phase 8 blind red-team review, finding #2.
- **Category:** security finding
- **Severity:** high — deleting `keys/revoked_keys.txt` with a single
  unprivileged filesystem write un-revoked every previously revoked key,
  with no cryptographic trace.
- **Description:** `signing.py`'s `is_revoked()` returned `False` (not
  revoked) whenever the revocation list file didn't exist — a classic
  fail-open default on a security-critical control file.
- **Root cause:** "file missing" was conflated with "nothing has ever
  been revoked," with no way to distinguish a legitimately fresh list
  from one that had been deleted after use.
- **Fix:** the revocation list is now co-initialized (empty, but
  integrity-protected via `state_integrity.py`) the moment a keypair is
  generated, so content and its HMAC sidecar always exist together from
  that point on. `is_revoked()` now fails **closed**: if the list's
  integrity check fails (tampered, or deleted while its sidecar remains
  — exactly the red-team's "delete to un-revoke" pattern), every key is
  treated as revoked. The only way to reach "not revoked" is a
  verified-empty or verified-non-matching list.
- **Disclosure status:** n/a.
- **Verified fixed:** yes — `tests/test_phase8_redteam_fixes.py`
  (`test_finding2_*`, 3 tests). Also surfaced two real, latent instances
  of the same underlying anti-pattern (a raw `write_text("")` cleanup
  that bypasses the new integrity sidecar) in
  `tests/test_phase1_pipeline.py` and `evaluation/experiment.py`'s
  `scenario_07` — both fixed to go through the new
  `reset_revocation_list()` helper instead. Full regression suite and
  evaluation harness re-run clean (see ISSUE-011's verification note for
  the shared re-run).

---

## [ISSUE-013] `version` argument for downgrade protection was never bound to the provenance record it traveled with — Phase 8 red-team finding #3

- **Date found:** 2026-08-04
- **Found during:** Phase 8 blind red-team review, finding #3.
- **Category:** security finding
- **Severity:** medium — enables a denial-of-service distinct from
  anything in the existing 15-case attack matrix: an inflated version
  number, supplied independently of the artifact's actual provenance,
  could poison the shared ledger and permanently lock out future
  *legitimate* lower/correct version numbers, requiring no signature or
  provenance forgery.
- **Description:** `ground_auth.py::authorize()` called
  `verify_provenance()` and discarded its parsed-provenance return value,
  then separately called `version_ledger.check_and_advance(version, ...)`
  using the bare `version` function argument — never cross-checked
  against whatever version `generate_provenance()` had actually embedded
  in the provenance document.
- **Root cause:** the two "version" values (the caller-supplied argument
  and the provenance document's own field) were structurally independent
  from the start; nothing enforced they had to agree.
- **Fix:** `authorize()` now extracts
  `provenance_doc["predicate"]["runDetails"]["metadata"]["version"]` and
  denies the authorization if it doesn't match the `version` argument,
  before ever consulting the ledger.
- **Disclosure status:** n/a.
- **Verified fixed:** yes — `tests/test_phase8_redteam_fixes.py`
  (`test_finding3_*`, 2 tests: mismatched version rejected, matching
  version still approved). Full regression suite and evaluation harness
  re-run clean (all existing calls already pass matching version
  arguments throughout the codebase, confirmed via the full suite).

---

## [ISSUE-014] Onboard prohibited-configuration check was a permanent dead stub with a brittle string-match gate — Phase 8 red-team finding #4

- **Date found:** 2026-08-04
- **Found during:** Phase 8 blind red-team review, finding #4.
- **Category:** bug (incomplete implementation left over from Phase 1) /
  security finding
- **Severity:** medium — the spacecraft had no independent ability to
  reject a prohibited configuration if ground authorization was bypassed,
  compromised, or fed different data than what was actually deployed.
- **Description:** `onboard.py::check_prohibited_configuration()`
  unconditionally `return True`d, with a comment calling it a Phase 1
  placeholder "until Phase 4" — but Phase 4 *did* build real policy
  evaluation (`policy.check_configuration`), it was only ever wired into
  ground-side `authorize()`, never back into this stub. Compounding bug:
  the gate that even called the stub was `if condition_name == "S5"` — a
  literal string match against the condition's *name*, not
  `cond.active("machine_readable_authorization")` — so any condition
  object whose `.name` wasn't literally `"S5"` would silently skip the
  check regardless of whether the mechanism was actually active.
- **Root cause:** the Phase 1 placeholder was never revisited once Phase
  4 built the real mechanism elsewhere; the string-match gate was a
  Phase 1-era shortcut that predated `condition.py`'s `Condition.active()`
  API.
- **Fix:** `check_prohibited_configuration()` now delegates to the same
  `policy.check_configuration()` ground authorization uses. The gate now
  builds a real `Condition` via `condition.preset(condition_name)`
  (mirroring `ground_auth.py`'s own pattern) and checks
  `cond.active("machine_readable_authorization")` directly. Stated scope
  boundary, consistent with the one already documented for
  `ground_auth.py`'s own policy check: this builds its own `Condition`
  independent of any `disable_mechanisms` ablation override passed to
  `pipeline.py`'s `run()` — not a new gap, the same deliberate boundary
  the Phase 8 ablation study already documents.
- **Disclosure status:** n/a.
- **Verified fixed:** yes — `tests/test_phase8_redteam_fixes.py`
  (`test_finding4_*`, 2 tests: onboard independently rejects a prohibited
  configuration at S5; the mechanism-flag gate correctly does NOT run at
  S4, confirming it's keyed off the mechanism, not a literal string).
  Full regression suite and evaluation harness re-run clean.

---

## [ISSUE-015] S5 authorization-evidence document was unsigned and silently overwritten on every re-run — Phase 8 red-team finding #5

- **Date found:** 2026-08-04
- **Found during:** Phase 8 blind red-team review, finding #5.
- **Category:** security finding
- **Severity:** medium — the one deliverable meant to be handed to an
  external auditor/ground reviewer at the top of the assurance ladder was
  neither immutable nor signed, undermining the trust claim it's supposed
  to carry.
- **Description:** `authorization_evidence.py` wrote plain JSON to
  `work/authorization_evidence/{artifact_hash}.authorization-evidence.json`
  — keyed only by artifact hash, with no signature, run ID, or timestamp
  in the filename. Since the stand-in stub artifact's hash is identical
  across every run (a documented property, for an unrelated Phase 5
  reason), every re-run silently clobbered whatever document existed at
  that path, including one that had recorded a detected failure.
- **Root cause:** the filename's uniqueness key (artifact hash alone) was
  never actually unique per run for this project's stub artifacts; no
  signing was ever added because the module's original scope was "can
  the evidence be assembled automatically," not "is the assembled
  document itself protected."
- **Fix:** the document is now signed with a dedicated Ed25519 keypair
  (mirroring `attestation.py`'s per-mechanism-key convention; detached
  `.sig` sidecar), and the filename now includes `run_id` (the caller's
  evidence-log start index for this run, already computed by
  `pipeline.py` — no new ID scheme needed), so two runs never collide.
  New `verify_authorization_evidence()` lets an external verifier confirm
  the document hasn't been altered since generation.
- **Disclosure status:** n/a.
- **Verified fixed:** yes — `tests/test_phase8_redteam_fixes.py`
  (`test_finding5_*`, 3 tests: valid signature verifies, tampered content
  fails verification, two runs produce two distinct never-overwritten
  files). Full regression suite and evaluation harness re-run clean.

---

## [ISSUE-016] No revocation mechanism existed for the attestation key — Phase 8 red-team finding #6

- **Date found:** 2026-08-04
- **Found during:** Phase 8 blind red-team review, finding #6.
- **Category:** security finding
- **Severity:** medium — if the attestation private key were ever known
  or suspected compromised, there was no operational way to invalidate it
  short of manually swapping key files.
- **Description:** `attestation.py` had no `is_revoked()`/
  `REVOKED_KEYS_PATH` equivalent for `ATTESTATION_PRIVATE_KEY_PATH` —
  `signing.py`'s revocation check had no counterpart for the attestation
  mechanism.
- **Root cause:** the attestation module was built (Phase 3) before
  `signing.py`'s revocation mechanism existed conceptually as a pattern
  to replicate, and was never revisited once it did.
- **Fix:** added `is_attestation_key_revoked()`/
  `revoke_current_attestation_key()`, mirroring `signing.py`'s
  (ISSUE-012-fixed) fail-closed pattern exactly, via the same
  `state_integrity.py` mechanism. `verify_attestation()` now checks this
  before trusting a quote.
- **Disclosure status:** n/a.
- **Verified fixed:** yes — `tests/test_phase8_redteam_fixes.py`
  (`test_finding6_*`, 3 tests: not revoked by default, revoked key
  rejected at S4, deleted-after-protection revocation list fails closed).
  Full regression suite and evaluation harness re-run clean.

---

## [ISSUE-017] Operational-monitoring mismatches were detected but never enforced — Phase 8 red-team finding #7

- **Date found:** 2026-08-04
- **Found during:** Phase 8 blind red-team review, finding #7.
- **Category:** design flaw / security finding
- **Severity:** medium — detection here was purely retrospective/
  auditable, not preventive; nothing stopped the same mismatch from
  recurring indefinitely on every subsequent run.
- **Description:** `pipeline.py`'s S5 branch computed
  `inventory_reconciled`/`telemetry_consistent` via
  `monitoring.reconcile_inventory()`/`monitoring.check_telemetry()`
  (test cases #13/#15) but never branched on the result — no rejection,
  no re-authorization freeze, no alert; just an evidence-log entry.
- **Root cause:** the monitoring checks were built (Phase 4) to satisfy
  the detection requirement for test cases #13/#15, and the exit
  criterion at the time was "is the mismatch detected and logged," not
  "does detecting it change anything" — a real, if narrow, scope gap.
- **Fix:** a detected mismatch now (a) marks that run's own
  `PipelineResult.rejected_at`, and (b) calls
  `version_ledger.freeze(stack, reason)`, which denies every subsequent
  `check_and_advance()` call for that stack until an operator explicitly
  calls `unfreeze()` — real behavioral enforcement, not a stronger log
  message. The freeze marker is itself integrity-protected via
  `state_integrity.py` (fails closed if tampered/deleted).
  **Side effect requiring a coordinated fix:** `evaluation/experiment.py`'s
  `run_attack_trials()` and `evaluation/ablation.py`'s
  `run_ablation_study()` deliberately trigger this exact mismatch every
  trial for test cases #13/#15 (that's the attack being tested) — without
  clearing the freeze between trials, trial 1's freeze would silently
  corrupt every subsequent trial in the same loop (rejected at
  `ground_authorization` instead of ever reaching the mechanism under
  test). Both now call `version_ledger.unfreeze(stack)` before each
  trial, with a comment explaining this is a test-harness modeling
  choice (each trial = an independent release attempt), not something a
  real deployment would do automatically.
- **Disclosure status:** n/a.
- **Verified fixed:** yes — `tests/test_phase8_redteam_fixes.py`
  (`test_finding7_*`, 3 tests: mismatch freezes the stack and rejects the
  run, unfreeze restores normal operation, tampered freeze marker fails
  closed). Full regression suite, evaluation harness (all 15 cases
  individually re-checked at reduced trial counts), Phase 8 ablation
  study, and Phase 8 adaptive-attacker scenarios all re-run against
  `cfs`/`fprime` with results identical to before this whole fix set
  (100%/0% throughout, 100%/100% for adaptive scenarios, 0 drift). Also
  confirmed against real `cfs-real`/`fprime-real` via
  `tests/test_phase7_real_builds.py` (6/6 passing).

---

## [ISSUE-018] SBOM was never bound to the artifact it describes — second red-team finding #1

- **Date found:** 2026-08-05
- **Found during:** Second (wider) blind red-team review — see
  Threat-Model.md "Phase 8 second independent red-team review."
- **Category:** design flaw / security finding
- **Severity:** medium — masked in the normal pipeline flow (SBOM is
  always generated from the same binary it ships with), but
  `ground_auth.authorize()` is a general function accepting a
  caller-supplied `sbom_path` independently of `binary_path`, with no
  check that they actually describe the same artifact.
- **Description:** `sbom.py::verify_sbom()` checked only the SBOM's own
  internal fields (completeness, known vulnerabilities) — never that its
  declared `metadata.component.hashes[0].content` matches the binary
  being authorized alongside it. `provenance.py::verify_provenance()`
  has always performed the equivalent binding check; SBOM had no
  equivalent.
- **Root cause:** SBOM verification was designed and tested only against
  its own internal shape, never against the co-supplied artifact — an
  omission parallel to, but independently found from, the existing
  provenance-binding logic already in the codebase.
- **Fix:** new `sbom.py::check_binding()` compares the SBOM's declared
  hash against the actual binary's SHA-256; `verify_sbom()` gained an
  optional `binary_path` parameter that runs this check when provided.
  `ground_auth.py`'s real call site now always passes it.
- **Disclosure status:** n/a.
- **Verified fixed:** yes — `tests/test_second_redteam_fixes.py`
  (`test_finding1_*`, 2 tests: a valid SBOM paired with the wrong binary
  is rejected; omitting `binary_path` preserves old structure-only
  behavior for backward compatibility).

---

## [ISSUE-019] Docker health-check fallback ran the image's baked-in binary, never the actual installed one — second red-team finding #2

- **Date found:** 2026-08-05
- **Found during:** Second (wider) blind red-team review.
- **Category:** design flaw / measurement-validity bug
- **Severity:** high — this affects the exact machine/path (macOS via
  the Docker fallback) that produced this project's own published
  real-cFS/F´ health-check results. Checked whether it corrupted any of
  the 15 published attack-matrix results: it did not, because none of
  them rely on running a tampered binary through this specific check
  (they're caught earlier via hash comparisons in attestation/partition
  verification) — but the underlying claim ("re-runs the identical
  binary") was false as implemented, on real hardware this project
  already reported results from.
- **Description:** `health_check.py::_launch_process`'s Docker fallback
  ran `docker run --rm <image> <container_binary_path>` — the binary
  baked into the image at build time — and never mounted or otherwise
  passed in the real `installed_binary_path` argument the function
  actually received. The module's own docstring claimed this "re-runs
  the identical binary"; that was not what the code did.
- **Root cause:** ISSUE-007's original fallback fix (2026-08-03) focused
  on making Docker execution *work at all* (fixing the `ENOEXEC`
  crash-to-fabricated-failure bug) and never revisited whether the
  binary being executed inside the container was the one that mattered
  for *this specific pipeline run*, as opposed to whatever was baked
  into the image once.
- **Fix:** `_launch_process` now bind-mounts the real
  `installed_binary_path` over `container_binary_path` inside the
  container (`-v <host_path>:<container_binary_path>:ro`), so the
  Docker-fallback path genuinely re-executes the artifact that was
  actually attested/installed for this run, not a frozen image-build-time
  copy.
- **Disclosure status:** n/a.
- **Verified fixed:** yes — `tests/test_second_redteam_fixes.py`
  (`test_finding2_*`) monkeypatches `subprocess.Popen` and confirms the
  `-v` mount flag is present, points at the real installed binary
  resolved to an absolute path, and precedes the image name; existing
  `tests/test_issue007_docker_fallback.py` sysctl-ordering tests still
  pass unchanged (mount flags don't disturb sysctl-flag positioning).

---

## [ISSUE-020] Onboard verification had no independent downgrade defense — second red-team finding #3

- **Date found:** 2026-08-05
- **Found during:** Second (wider) blind red-team review.
- **Category:** design flaw / security finding
- **Severity:** medium — the same class of gap already closed for the
  S5 policy check (ISSUE-015/finding #4): downgrade protection (test
  case #9) was enforced only via `version_ledger.check_and_advance()`,
  called only from `ground_auth.authorize()`. If ground authorization is
  bypassed, compromised, or fed data inconsistent with what's actually
  transmitted, the spacecraft had zero independent fallback defense
  against a downgrade.
- **Description:** `onboard.py::verify_received_bundle()` had a
  policy-check fallback (added for finding #4) but nothing analogous for
  version/downgrade, even though the spacecraft already maintains its
  own independent record of the currently-confirmed version via
  partition state.
- **Root cause:** finding #4's fix addressed the one specific mechanism
  the red-team review flagged at the time (S5 policy) without
  generalizing to the sibling mechanism (downgrade protection) that has
  the identical "ground-side-only enforcement" shape.
- **Fix:** new `onboard.py::check_independent_downgrade()` compares an
  incoming release's `version` against the spacecraft's own
  currently-confirmed partition-state version (data ground never
  controls directly), gated on `trusted_rollback` being active (S4+,
  since partition state doesn't exist before then — consistent with the
  existing S3-vs-S4 capability-growth pattern documented elsewhere in
  this project). Fails closed on a partition-state integrity failure
  (`state_integrity.StateIntegrityError`) rather than letting it
  propagate and crash `pipeline.run()` — this check runs during onboard
  verification, before `pipeline.py`'s own trusted_rollback try/except
  block, so an uncaught exception here would have skipped returning a
  `PipelineResult` entirely.
- **Disclosure status:** n/a.
- **Verified fixed:** yes — `tests/test_second_redteam_fixes.py`
  (`test_finding3_*`, 4 tests: direct unit check of the downgrade logic;
  no-baseline case doesn't fabricate a rejection; a tampered partition
  state fails closed rather than crashing; a full pipeline run
  demonstrates the onboard check catching a downgrade specifically in
  the scenario where ground's own ledger has no memory of the
  spacecraft's true confirmed version and therefore can't catch it
  itself). Discovering the fail-closed-not-crash requirement required
  fixing a real regression this same fix introduced in
  `tests/test_phase8_redteam_fixes.py::test_finding1_tampered_partition_state_fails_closed`
  (see that test's updated comment) — the tamper is now caught even
  earlier (`onboard_verification` instead of
  `partition_state_integrity_failure`), a strictly earlier fail-closed
  detection point, not a weaker one.

---

## [ISSUE-021] Attestation freshness check had no floor — a future-dated quote never expired — second red-team finding #4

- **Date found:** 2026-08-05
- **Found during:** Second (wider) blind red-team review.
- **Category:** logic bug / security finding
- **Severity:** medium — never exercised by any of the 15 existing test
  cases (only positive `backdate_seconds`, i.e. staleness, was ever
  tested), so it was a genuinely uncovered gap, not a masked one.
- **Description:** `attestation.py::verify_attestation()` computed
  `age_seconds = time.time() - quote["timestamp"]` and rejected only when
  `age_seconds > max_age_seconds`. A quote whose `timestamp` is in the
  future yields a negative `age_seconds`, which is always less than
  `max_age_seconds` and therefore always "fresh" — indefinitely, since
  real time only ever moves the negative age closer to zero, never past
  the staleness threshold on its own.
- **Root cause:** the staleness check was designed around the one
  attack it needed to catch (test case #12, an old/stale quote) and
  never considered the symmetric case.
- **Fix:** added a floor check (`age_seconds < 0`) that rejects a
  future-dated attestation outright — a real boot process cannot
  honestly produce a quote timestamped after the moment it was created.
- **Disclosure status:** n/a.
- **Verified fixed:** yes — `tests/test_second_redteam_fixes.py`
  (`test_finding4_*`, 3 tests: a future-dated quote is rejected; a
  normal fresh quote still passes; the pre-existing staleness check for
  test case #12 is unaffected).

---

## [ISSUE-022] Persistent-process health check has no tie to artifact identity — second red-team finding #5 (documented, not fixed)

- **Date found:** 2026-08-05
- **Found during:** Second (wider) blind red-team review.
- **Category:** documented limitation (not fixed this pass)
- **Severity:** low-medium — for `cfs-real`/`fprime-real`, "healthy"
  means only that one of `Stack.boot_success_markers` appeared in
  stdout within the boot window; there is no hash tie-back to the
  attested/installed binary in that specific check. A trivial
  replacement binary that prints the magic marker string and does
  nothing else would pass. `force_fail` (test case #11) short-circuits
  before ever reaching this code path, so this specific forgeable-marker
  vector is genuinely untested.
- **Description / root cause:** the persistent-process health-check
  strategy (ISSUE-003) was designed to solve a different problem —
  long-running processes that never produce a fixed, diffable stdout
  transcript — and correctness of *that* substitution was never
  extended to also bind the observed marker to the specific binary's
  hash.
- **Fix:** none applied this pass. A real fix would need to correlate
  the boot-success marker with a per-invocation nonce or the binary's own
  hash (neither `core-cpu1` nor `Ref` currently print anything
  hash-specific at boot), which is a bigger design change than this
  pass's scope. Documented here and in Threat-Model.md as a stated,
  known limitation of the persistent-process health-check strategy
  rather than silently left unstated.
- **Disclosure status:** n/a.
- **Verified fixed:** n/a — intentionally not fixed; see above.

---

## [ISSUE-023] Provenance bound to git HEAD only, never checked for an uncommitted working tree — second red-team finding #6

- **Date found:** 2026-08-05
- **Found during:** Second (wider) blind red-team review.
- **Category:** design flaw / security finding
- **Severity:** low-medium — real but narrow: a binary built from a
  locally-modified (uncommitted) source tree gets provenance claiming
  the same `source_commit` as a clean checkout at that same HEAD, so the
  provenance record's source binding can silently diverge from what was
  actually compiled. Never exercised by test cases #1/#2.
- **Description:** `provenance.py::_current_source_commit()` records
  `git rev-parse HEAD` unconditionally, with no check for uncommitted
  changes (`git status --porcelain`).
- **Root cause:** the binding check was designed around "does the
  binary's hash match what provenance claims" (test case #1), never
  "does the recorded source identity itself reflect what was actually on
  disk at build time."
- **Fix:** new `provenance.py::_source_tree_dirty()` records the true
  ambient `git status --porcelain` result in every generated provenance
  document (`source_tree_dirty`, transparency, always computed).
  `verify_provenance()` gained an opt-in `require_clean_tree` parameter
  (default `False`) that treats a dirty-tree provenance record as a
  validity failure. Deliberately NOT enabled by `ground_auth.py`'s
  default call: this project's own repository is routinely dirty during
  active development (this exact session included), so enforcing it
  unconditionally would fail every evaluation run made while iterating
  on the code — an environment/workflow fact about this project, not a
  security property worth conflating with a real attack. The check is
  real, tested, and the correct default for an actual CI release
  pipeline gating what reaches a spacecraft; stated explicitly as
  opt-in rather than silently wired in or silently omitted.
- **Disclosure status:** n/a.
- **Verified fixed:** yes — `tests/test_second_redteam_fixes.py`
  (`test_finding6_*`, 3 tests: dirty tree rejected when
  `require_clean_tree=True`; not enforced by default; clean tree passes
  even when required).

---

## [ISSUE-024] Evaluation scenario_13 never exercised the real pipeline — second red-team finding #7

- **Date found:** 2026-08-05
- **Found during:** Second (wider) blind red-team review, specifically
  the ask to audit the evaluation harness's own construction for
  vacuous tests.
- **Category:** measurement-validity bug (evaluation code, not the
  pipeline it measures)
- **Severity:** medium — this is exactly the "metric that can't fail
  regardless of whether the mechanism works" pattern reviewer objection
  9 exists to guard against, found in this project's own evaluation
  code rather than the pipeline.
- **Description:** `evaluation/experiment.py::scenario_13()` called
  `monitoring.reconcile_inventory()` directly with hardcoded,
  deliberately-mismatched constants
  (`ground_expected_version=2, spacecraft_confirmed_version=1`, a
  synthetic hash string) instead of driving the check through a real
  `pipeline.run()`. This guaranteed "100% detection" for test case #13
  by construction — it demonstrated that `reconcile_inventory()` can
  tell two different numbers apart, not that the pipeline produces a
  genuine disagreement when something really does go wrong.
- **Root cause:** written as a direct unit-style exercise of the
  mechanism (mirroring `test_phase4_pipeline.py`'s own hand-built-state
  approach for test case #13) and never revisited once `scenario_15`
  established the pattern for driving the same underlying attack (a
  forced S5 rollback) through a real pipeline call.
- **Fix:** rewrote `scenario_13` to run a confirmed baseline at S5, then
  a forced health-check failure that causes a genuine rollback back to
  the baseline slot — so ground's `version` argument for the second call
  genuinely disagrees with what the spacecraft actually confirms,
  through `pipeline.py`'s own `reconcile_inventory()` call. Moved `"13"`
  from `SINGLE_VERSION_SCENARIOS` to `PAIRED_VERSION_SCENARIOS`
  accordingly. Test cases #13 and #15 now correctly share one real
  attack trigger while checking two independently-meaningful result
  fields (`inventory_reconciled`, `telemetry_consistent`).
- **Disclosure status:** n/a.
- **Verified fixed:** yes — `tests/test_second_redteam_fixes.py`
  (`test_finding7_scenario_13_detects_a_real_inventory_mismatch`)
  confirms the rewritten scenario still reports `caught: True` when
  driven through the real pipeline.

---

## [ISSUE-025] report.py aggregated traceability/artifact-size fields from trial 0 only — second red-team finding #8

- **Date found:** 2026-08-05
- **Found during:** Second (wider) blind red-team review.
- **Category:** measurement-validity bug (evaluation code)
- **Severity:** low-medium — timing and success/reproducibility were
  properly aggregated across all `n_trials`; `traceability_completeness`
  and every artifact-size figure were not. These fields are expected to
  be deterministic across trials for the same condition (same code path
  every time), so this was unlikely to have silently hidden a real
  regression in the numbers already published — but nothing was actually
  checking that assumption.
- **Description:** `evaluation/report.py::summarize_happy_path()` took
  `trace = trials[0]["traceability_completeness"]` and every
  `sizes[...] = trials[0][...]` unconditionally, never comparing against
  any other trial.
- **Root cause:** these fields were added expecting them to be constant
  per condition, and the aggregation code never revisited that
  assumption once means/CIs were added elsewhere in the same function
  for genuinely variable fields (Phase 8, 2026-08-03).
- **Fix:** now computes the full set of distinct values across all
  trials for `traceability_completeness` and each size field; the
  reported number is still trial[0]'s (unchanged behavior for anything
  already citing these numbers), but a new `trial_metrics_consistent`
  boolean and `trial_metrics_inconsistencies` list surface any
  divergence explicitly rather than leaving it silently possible.
- **Disclosure status:** n/a.
- **Verified fixed:** yes — `tests/test_second_redteam_fixes.py`
  (`test_finding8_*`, 2 tests: consistent trials flagged consistent with
  an empty inconsistency list; a deliberately divergent trial is flagged,
  naming the specific field, while the reported headline number stays
  unchanged).

---

## [ISSUE-026] No automatic key-rotation path after signing-key or attestation-key revocation — second red-team finding #11

- **Date found:** 2026-08-05
- **Found during:** Second (wider) blind red-team review.
- **Category:** design flaw / operational-hygiene finding
- **Severity:** low — once a key is revoked (test case #7 or the
  attestation-key equivalent), the system kept silently producing new
  signatures/quotes with that same revoked key indefinitely; every one
  of them guaranteed to fail verification downstream (the real defense,
  which already worked correctly), but with no evidence trail pointing
  at the actual moment an operator's mistake happened.
- **Description:** `signing.py::sign()` and
  `attestation.py::generate_attestation()` never checked
  `is_revoked()`/`is_attestation_key_revoked()` before producing new
  material with the current key.
- **Root cause:** revocation was designed and tested purely from the
  verification side (Phase 8 findings #2/#6); the signing/attestation
  side was never asked "should this even happen if the key is already
  known-bad."
- **Fix, and an explicit design tension worth stating:** the natural fix
  (refuse to sign/attest with a revoked key) was tried first and
  reverted — it broke the existing, correct test case #7 design (revoke
  the key, then attempt a release still signed with it, and rely on
  *downstream verification* to catch it) and the equivalent attestation
  regression test, both of which deliberately model an
  operator/system that hasn't rotated yet, with the defense correctly
  living in `verify()`/`verify_attestation()`, not in the signer itself.
  The actual fix: `sign()` and `generate_attestation()` now log a
  distinct evidence record ("signing/quoting with an already-revoked
  key") when this happens, giving visibility without changing control
  flow or breaking the existing attack simulation.
- **Disclosure status:** n/a.
- **Verified fixed:** yes — `tests/test_second_redteam_fixes.py`
  (`test_finding9_*`, 2 tests: signing/attesting with a revoked key still
  succeeds without raising, and produces a distinct, queryable evidence
  record naming the reason).

---

## [ISSUE-027] Prohibited-configuration policy check bypassable by type coercion — second red-team finding #10

- **Date found:** 2026-08-05
- **Found during:** Second (wider) blind red-team review.
- **Category:** logic bug / security finding
- **Severity:** low — the policy table itself is an explicitly-stated
  test-only toy (`policy.py`'s own module docstring), but this is a
  real, concrete evasion of the one rule it enforces.
- **Description:** `policy.py::_matches()` used bare `config.get(k) ==
  v` against the pattern `{"debug_mode": True}`. Python's `"true" ==
  True` and `1 == True` behave inconsistently for the intended semantics
  (`1 == True` is `True`, but a caller-supplied config of
  `{"debug_mode": "true"}` — a plausible shape if the config arrived as
  loosely-typed JSON or a string field — never matches the exact `True`
  singleton), so a config meaning the same thing but spelled differently
  silently bypassed the only rule in the deny-list.
- **Root cause:** the deny-rule matcher was written assuming config
  values always arrive as genuine Python booleans, never validated
  against how a real caller-supplied config might actually be typed.
- **Fix:** new `policy.py::_values_match()` normalizes boolean pattern
  values against `True`/`False`, `"true"`/`"false"`/`"1"`/`"0"`/etc., and
  numeric truthiness — while keeping exact-equality semantics for any
  non-boolean pattern value, so this stays scoped to the boolean-flag
  case rather than becoming a general fuzzy-match policy engine.
- **Disclosure status:** n/a.
- **Verified fixed:** yes — `tests/test_second_redteam_fixes.py`
  (`test_finding10_*`, 3 parameterized tests: every truthy representation
  is caught, every falsy representation still passes, non-boolean fields
  keep exact-equality semantics).

---

## [ISSUE-028] Ablation baseline-invariant asserts were inconsistently guarded — second red-team finding #9

- **Date found:** 2026-08-05
- **Found during:** Second (wider) blind red-team review.
- **Category:** latent fragility (no observed incorrect result)
- **Severity:** low — currently harmless (the asserted invariant happens
  to still hold under ablation for all three cases), but a latent
  fragility: if mechanism behavior ever changed, these three would crash
  the whole ablation run instead of degrading gracefully like their
  siblings.
- **Description:** `evaluation/ablation.py`'s `_ablation_case_04`,
  `_ablation_case_05`, and `_ablation_case_12` called their internal
  "baseline" sub-run with whatever `disable` tuple the caller passed
  (correctly), but then unconditionally asserted an invariant
  (`rejected_at is None` / `rollback_outcome == "confirmed"`) regardless
  of whether the mechanism was ablated for that call.
  `_ablation_case_08`, `_ablation_case_11`, and `_ablation_case_15`
  already guarded the equivalent assertion with `if not disable:`.
- **Root cause:** `_ablation_case_04`/`_05` were written this same
  session (objection-5 fix) by copying `_ablation_case_12`'s existing
  pattern, which itself predates the `if not disable:` guard convention
  established later for `_08`/`_11`/`_15` — an inconsistency introduced
  by not retrofitting the earlier-written functions once the safer
  pattern was established.
- **Fix:** added the same `if not disable:` guard to all three, for
  consistency across every ablation case.
- **Disclosure status:** n/a.
- **Verified fixed:** yes — `tests/test_second_redteam_fixes.py`
  (`test_finding11_*`, 3 tests confirming each of the three cases runs
  without raising when its own mechanism is ablated).

---

## [ISSUE-029] Uplink tamper injection always corrupted the same byte offset — second red-team finding #12

- **Date found:** 2026-08-05
- **Found during:** Second (wider) blind red-team review.
- **Category:** test-coverage narrowness (not a detection gap)
- **Severity:** very low — not a security hole (whole-artifact
  signature verification is location-agnostic, so detection was never
  at risk), just needlessly narrow coverage: "modified in transit" (test
  case #6) was only ever exercised as one specific single-byte-flip
  location across the entire test suite.
- **Description:** `uplink_sim/uplink.py::transmit()` always computed
  `mid = len(data) // 2; data[mid] ^= 0xFF` for both the deterministic
  `tamper` flag and random link-noise corruption.
- **Root cause:** the midpoint was a simple, arbitrary implementation
  choice made once in Phase 1 and never revisited.
- **Fix:** picks a pseudo-random offset from the same seeded `rng`
  instance instead of a fixed midpoint — `rng_seed` still makes a given
  test call fully reproducible, it just no longer always lands on the
  same byte.
- **Disclosure status:** n/a.
- **Verified fixed:** yes — `tests/test_second_redteam_fixes.py`
  (`test_finding12_tamper_offset_varies_with_seed`) confirms 8 different
  seeds produce more than one distinct corrupted-byte offset.

---

## Notes on responsible disclosure

If a real vulnerability is found in an upstream dependency (cFS itself,
SLSA/in-toto/Sigstore tooling, etc.) rather than in this project's own
code, follow the upstream project's own disclosure process rather than
disclosing it here first — link to the upstream report from this log once
it's public, and note the disclosure timeline in the "Disclosure status"
field above. See `SECURITY.md` for this repo's own policy on findings
reported against this project's code.
