# Project Status

**Read this file first in every new session.** It is the single source of
truth for "where are we right now." Update it at the end of every work
session, however small.

---

## Current phase

**Phase 7 — Real framework builds and real-stack statistical evaluation:
COMPLETE.**
(see `docs/Implementation-Plan.md`) Both `cfs-app/Dockerfile` and
`fprime-app/Dockerfile` run successfully on the user's Docker-capable Mac
(after fixing real bugs in both). Real `core-cpu1` (cFS) and `Ref` (F´)
binaries are built, confirmed working, and wired into the pipeline as
`"cfs-real"`/`"fprime-real"` stacks. Full S0-S5 lifecycle exercised
against both, including a persistent-process health-check strategy
(ISSUE-003). Independent reproducibility verification complete: F´'s
`Ref` is byte-for-byte reproducible across two from-scratch builds; cFS's
`core-cpu1` is not, with the cause precisely isolated (an embedded build
timestamp, 22 bytes of ~915KB). See `docs/Threat-Model.md` "Phase 7
reproducibility verification."

**Real-stack statistical evaluation (the paper's real-framework results
section) also complete.** Getting there surfaced two real bugs, both
found and fixed the same day: **ISSUE-007** (real health checks crashed
with `Exec format error` outside Docker on macOS, and the error handling
was silently mislabeling that as an unhealthy build — fixed with a
transparent Docker-run fallback) and **ISSUE-008** (`cfs-real` still
failed after that fix — Docker Desktop's default `fs.mqueue.msg_max`
too low for cFE's Software Bus — fixed via a per-stack `docker_sysctls`
override, confirmed manually before being coded). With both fixed, the
full repeated-trial harness (5 trials × 6 conditions × 15 attack cases)
ran successfully against **both** real binaries: 100% happy-path
success/reproducibility, 100% detection, 0 false positives/negatives for
both `cfs-real` and `fprime-real` — structurally identical to the
stub-artifact results. 47/47 unit tests passing. See `docs/Threat-Model.md`
"Phase 7 real-stack statistical evaluation results" and
ISSUES-AND-FIXES-LOG.md ISSUE-007/ISSUE-008. Next up: Phase 8 (paper
drafting and repo polish).

## Last session summary

**Date:** 2026-08-03 (session 7)

Ran both Docker builds for the first time ever (previously untested,
since the authoring sandbox has no Docker). Both failed on the first
attempt — real bugs in the Dockerfiles I'd written blind: cFS's assumed
a bare `cmake`/`make mission-install` flow that doesn't match the bundle
repo's actual Make-based build system, and F´'s assumed `pip install
-e .` on a repo with no setup.py/pyproject.toml. Fixed both by consulting
each framework's own authoritative build docs (verified via web fetch)
instead of guessing a third time — also caught and corrected a wrong cFS
tag pin (`v7.0.0` → `v7.0.1`, the actual current release) along the way.
Both builds succeeded on retry: `core-cpu1` boots and logs a genuine CFE
startup sequence through `OPERATIONAL` state; `Ref` built clean.

Given the choice of how to wire these into the pipeline (build.py's
compile-from-source-twice-per-run model doesn't fit a multi-minute NASA
build), the user chose treating them as fixed confirmed snapshots.
Implemented: `src/target_stack.py`'s `Stack` dataclass now supports
either stub-compile mode (`source_dir`+`compiler`) or prebuilt-binary
mode (`prebuilt_binary_path`), validated mutually exclusive at
registration time. Added `"cfs-real"`/`"fprime-real"` entries.
`build.py` copies the confirmed binary for real stacks instead of
recompiling, with evidence records explicitly flagging that the
resulting `reproducible=True` is a trivial copy-integrity check, not a
real two-independent-builds comparison — this distinction is documented
in the module docstring, the evidence record fields themselves, and new
`cfs-app/confirmed-build.json`/`fprime-app/confirmed-build.json`
provenance manifests (git-tracked; the binaries themselves stay
gitignored, consistent with every other build artifact in this repo).

Smoke-tested both real stacks through S0-S2 (build → provenance → SBOM →
signing → ground authorization → uplink → onboard verification →
installation) — clean pass, since none of those stages execute the
binary. Found a genuine architectural mismatch testing S3+: both real
binaries are long-running processes (`core-cpu1` loops forever once
`OPERATIONAL`; `Ref` waits for a network GDS connection), incompatible
with `health_check.py`'s run-to-completion-and-diff-stdout model.
Deliberately rejected the tempting shortcut of catching the resulting
subprocess timeout and treating it as a pass — that would fabricate a
health signal, not measure one. `run_health_check` now raises
`NotImplementedError` for any stack with no working health-check
strategy, which is honest but means S3+ against real binaries is
explicitly blocked pending a real design decision (not implemented this
session). New `tests/test_phase7_real_builds.py` (4 tests, auto-skip if
the local Docker-built binaries aren't present) locks in both the S0-S2
happy path and the explicit-failure behavior. Full suite: 39/39 passing.

**Previous session (2026-08-03, session 6):**

Added Phase 6 (generalizability): a second target stack, NASA JPL's F
Prime (F´), pinned to tag `v4.2.2` (Apache 2.0, verified directly from
the repo's `LICENSE.txt` and releases page, not from memory). Built
`src/target_stack.py` as a small registry so `src/build/build.py` and
`src/health/health_check.py` — the only two modules that had hardcoded
the Phase 1 stub's specific shape — could take a `stack` parameter
instead. Added `fprime-app/stub-component-app/main.cpp` (C++, different
output shape) plus a matching README/Dockerfile mirroring `cfs-app`'s
honest stand-in-vs-real conventions. Every other pipeline module
(signing, SBOM, provenance, attestation, partitions, rollback, policy,
monitoring, authorization evidence) needed zero changes — confirming the
S0-S5 ladder's design was already stack-agnostic in practice, not just in
principle.

Found and fixed a real bug in the process: `src/ground_authorization/
version_ledger.py` was a single global JSON file tracking "last approved
version" across the whole evaluation session, so approving version 1 for
`fprime` immediately after `cfs`'s test suite had already advanced its
counter was wrongly flagged as a downgrade attempt. Fixed by scoping the
ledger file per stack — the more correct design, since a real ground
system tracks version history per deployed target. This is the third
real bug found purely by building this project's own evaluation tooling
(after the Phase 4 comparison-table tagging bug and the Phase 5
authorization-evidence overhead bug) — a good, recurring pattern for the
paper's methodology section.

Added `tests/test_phase6_generalizability.py` (9 tests: build
reproducibility, S0/S5 happy path, one attack case per assurance layer,
and a dedicated regression test for the version-ledger fix). Full suite
now 35/35 passing. Re-ran the Phase 5-style evaluation harness
(`evaluation/experiment.py fprime`, `evaluation/report.py fprime`,
chunked the same way as Phase 5) against `fprime`: 100% happy-path
success/reproducibility across all 6 conditions, 100% detection across
all 15 attack matrix test cases (5/5 trials each), 0 false positives/
negatives anywhere. Storage-overhead figures matched stack #1's almost
exactly (S5 overhead vs. S0: 5,748 bytes for both) — expected, since
those artifacts are JSON documents sized by schema, not by the underlying
binary.

**Previous session (2026-08-03, session 5):**

Built and ran the Phase 5 evaluation harness (`evaluation/experiment.py`,
`evaluation/report.py`). Along the way, found and fixed a real correctness
bug in `src/evidence_store/authorization_evidence.py`: its internal
`store.for_artifact(artifact_hash)` lookup aggregated every evidence
record ever logged for the (constant, since the stub artifact never
changes) hash across the whole evaluation session, not just the current
run — inflating S5's measured storage overhead to ~855,655 bytes. Fixed
by changing the function to accept an explicit `records` list from the
caller; `src/pipeline.py` now tracks an evidence-log index at the start
of `run()` and passes only that run's slice. Confirmed via the full
pytest suite (26/26, no regressions) and via a corrected evaluation run:
S5 overhead vs. S0 is now 5,748 bytes. This is the second time this
category of bug (a constant-hash lookup silently aggregating cross-run
noise) has been caught by the project's own evidence-driven evaluation
tooling — the first was the Phase 4 comparison table's discovery of the
test case #6 tagging bug. Good, citable pattern for the paper's
methodology section.

Full corrected results: 100% happy-path success and reproducibility
across all 6 conditions; 100% detection rate across all 15 attack matrix
test cases, 5/5 trials each; 0 false positives/negatives in every
condition's confusion matrix. Full numbers in
`evaluation/results/phase5_report.md`. Per PRD.md § 10, all timing figures
are a sandbox-timing proxy, not hardware/real-mission timing, and all
results are against the stand-in stub artifact, not real cFS.

Sandbox note worth remembering: the full evaluation (~135
`pipeline.run()` calls) takes ~45-60s cumulatively, which exceeded a
single command's execution ceiling in this environment even though each
individual run is fast (~0.2-0.5s). Ran it in three chunks (happy path;
attack cases 1-11; attack cases 12-15) and merged results before running
`report.py` — documented in Implementation-Plan.md's Phase 5 section so
future sessions don't waste time treating this as a pipeline slowdown.

**Previous session (2026-08-03, session 4):**

Built and verified all three remaining S5 mechanisms: prohibited-
configuration policy (`src/policy/policy.py`, custom deny-list — not
OPA/Rego, see TDD § 7d for why), inventory reconciliation and false-
telemetry detection (`src/operational_monitoring/monitoring.py`), and an
OSCAL-informed authorization evidence aggregator
(`src/evidence_store/authorization_evidence.py`). 6 new tests covering
attack matrix cases #8, #13, #15 — all passing, plus all 20 Phase 1-3
tests still passing (26/26 total). **All 15 attack matrix test cases are
now implemented and passing** — the full S0-S5 assurance ladder is built.

Best moment this session: `evaluation/metrics.py::build_comparison_table`
(the automated S0-S5 detection matrix required by the Phase 4 exit
criteria) immediately surfaced a real evidence-tagging bug from Phase 1 —
test case #6 was tagged at the injection point instead of the detection
point, so it silently showed `caught=0` in the table despite being
correctly caught all along (the Phase 1 test had passed for three phases
without anyone noticing the evidence trail was incomplete). Fixed in
`src/pipeline.py`. This is genuinely a good example for the paper's
methodology section of why automated, evidence-store-driven evaluation
catches things a manual pass/fail test suite alone won't. Full writeup in
Threat-Model.md "Phase 4 results," including a known remaining limitation
(double-counting when a test case is tagged at two stages) flagged for
Phase 5 to fix properly.

**Previous session (2026-08-03, session 3):

Built and verified software attestation (`src/attestation/attestation.py`
— a custom stub, NOT swtpm/real TPM; no swtpm/tpm2-tools available and no
root to install them, and this limitation is materially important, not
cosmetic — see TDD § 7c), an A/B partition manager with tentative-
activate/confirm/revert semantics (`src/installation/partitions.py`), a
health check harness (`src/health/health_check.py`), and a rollback
controller (`src/rollback/rollback.py`). 6 new tests covering attack
matrix cases #10, #11, #12, #14 — all passing, plus all 14 Phase 1/2
tests still passing (20/20 total, no regressions). Best result this
session: the rollback path's recovery-image integrity check (test case
#14) — a naive A/B implementation without it would pass every other test
and still silently activate a corrupted "recovery" image in exactly the
scenario rollback exists to handle. See Threat-Model.md "Phase 3 results"
for the full breakdown, including a clean S3-vs-S4 contrast (detect-only
vs. detect-and-recover) worth a table/figure in the paper.

**Previous session (2026-08-03, session 2):** Built and verified SBOM
generation (`src/sbom/sbom.py`, CycloneDX-shaped), provenance generation/
verification (`src/provenance/provenance.py`, SLSA-shaped), a version
ledger for downgrade detection, condition-gated ground authorization
covering S1/S2, and an upgraded uplink simulator with configurable link
profiles. 10 tests covering attack matrix cases #1, #2, #3, #4, #5, #9.
One methodological catch worth remembering: an early version of the test
case #2 test failed for the wrong reason (missing SBOM masked the
intended provenance failure) because S2's preset is
signature+SBOM+provenance together, not provenance alone — see
Threat-Model.md "Phase 2 results."

**Previous session (2026-08-03, session 1):** Built and verified the full
Phase 1 S0 pipeline end-to-end: reproducible build, Ed25519 signing,
ground authorization, simulated uplink (with tamper hook), onboard
verification, installation, evidence store, metrics collector. All
against a stand-in stub artifact — the authoring sandbox had no
Docker/cmake/root, so the real cFS build (pinned and documented in
`cfs-app/Dockerfile`) could not be run there; needs to be run on a
Docker-capable machine (user has Docker locally) before any result is
cited as being about real spacecraft software. Added Apache 2.0 LICENSE.
Fixed a macOS-specific build reproducibility bug (ld64 UUID load command)
— confirmed 4/4 tests passing on both Linux sandbox and user's macOS.

## What's done

- [x] Research idea analyzed and validated (feasibility, publishability,
      venue targets)
- [x] Legal/data-sourcing question resolved — project needs no real
      operational spacecraft data (see Legal-Data-Sourcing-Notes.md)
- [x] Full documentation set drafted (v1) for: PRD, Threat Model, Pipeline
      Flow, Technical Design, Implementation Plan, Research Paper Outline,
      Legal/Data Sourcing Notes, this Status doc, Issues Log, Security
      policy
- [x] Project folder structure created under
      `Satellite-Cybersecurity-Research/verifiable-spacecraft-lifecycle/`
- [x] Apache 2.0 LICENSE added
- [x] GitHub repo live and pushed
- [x] **Phase 1 (S0 pipeline) complete**, cross-platform verified
      (Linux + macOS)
- [x] **Phase 2 (S1/S2: SBOM + provenance) complete** — 14/14 tests passing
- [x] **Phase 3 (S3/S4: attestation + rollback) complete** — 20/20 tests passing
- [x] **Phase 4 (S5: machine-readable authorization evidence) complete** —
      see Implementation-Plan.md for full breakdown; **26/26 tests
      passing, all 15 attack matrix test cases implemented**
- [x] **Phase 5 (evaluation and metrics collection) complete** —
      `evaluation/experiment.py` + `evaluation/report.py`; 5 repeated
      trials per condition and per attack case; 100% detection/success/
      reproducibility, 0 false positives/negatives; S5 overhead vs. S0 a
      sane 5,748 bytes (see Implementation-Plan.md Phase 5 for the
      correctness bug found and fixed along the way)
- [x] **Phase 6 (generalizability) complete** — second target stack (NASA
      JPL's F Prime, `fprime-app/`) added via `src/target_stack.py`;
      35/35 tests passing (26 + 9 new Phase 6 tests); full evaluation
      re-run against `fprime` with results structurally identical to
      stack #1 (100% detection/success/reproducibility, 0 false
      positives/negatives); one real bug found and fixed (version ledger
      wasn't stack-scoped) — see Implementation-Plan.md Phase 6
- [x] **Phase 7 (real framework builds) complete, save one open item** —
      real cFS (`core-cpu1`, tag v7.0.1) and real F´ (`Ref`, tag v4.2.2)
      both built successfully via Docker on the user's Mac, after fixing
      two real Dockerfile bugs (see ISSUES-AND-FIXES-LOG.md
      ISSUE-001/002). Wired in as `"cfs-real"`/`"fprime-real"` stacks;
      full S0-S5 lifecycle now exercised against both, including a
      persistent-process health-check strategy designed and implemented
      for ISSUE-003 (both real binaries are long-running processes that
      don't fit the original run-to-completion model — see ISSUE-003 for
      the fix). 41/41 tests passing (35 + 6 new, auto-skip if binaries
      absent). Independent reproducibility verification also complete:
      F´'s `Ref` is byte-for-byte reproducible across two from-scratch
      Docker builds; cFS's `core-cpu1` is not, with the exact cause
      (an embedded build-timestamp string and its downstream effect on
      the ELF build-id) isolated precisely — see
      `docs/Threat-Model.md` "Phase 7 reproducibility verification"

## What's next (immediate)

- [x] Rejection-risk review against target venues (2026-08-03, see
      `docs/Research-Paper-Outline.md`) — identified the "ceiling effect /
      detection-by-construction" objection as the single biggest exposure,
      plus statistical-thinness (5 trials, no CIs) and no-ablation gaps.
      User chose to address 3 of 4 proposed mitigations before Phase 8, all
      now **complete**:
      1. Ablation study — `condition.custom()`/`pipeline.run()`'s new
         `disable_mechanisms` param, `evaluation/ablation.py`; 3 mechanisms
         ablated (onboard_attestation, trusted_rollback,
         machine_readable_authorization), all showing exactly the
         predicted effect on both stub stacks. See `docs/Threat-Model.md`
         "Phase 8 ablation study."
      2. Adaptive-attacker scenarios — `evaluation/adaptive_attacks.py`,
         2 combined-vector scenarios confirming the pipeline halts at the
         first violated layer rather than merely detecting-but-continuing.
         See `docs/Threat-Model.md` "Phase 8 adaptive-attacker scenarios."
      3. Trial count/CI — `N_TRIALS` bumped 5 -> 30 in
         `evaluation/experiment.py`; `evaluation/report.py` now computes
         95% Wilson score intervals for rates and normal-approximation
         CIs for timing means (verified via synthetic-data smoke test;
         Wilson CI confirmed well-behaved at 0%/100% boundaries).
      All verified via the 41/41 regression suite (no changes to default
      behavior) plus targeted smoke tests; **not yet re-run as the full
      30-trial paper-scale evaluation** (the harness takes several
      minutes at n=30, beyond a single sandboxed command — same chunking
      pattern as Phase 5) and **not yet run against real
      `cfs-real`/`fprime-real`** (requires the user's Docker-capable Mac).
- [x] **ISSUE-009 found and fixed (2026-08-04):** the user's first attempt
      to run the above on their Mac hit a wall immediately — every S4+
      happy-path run on both stub stacks crashed with SIGABRT, no attack
      injected. Root cause, confirmed not guessed: `-Wl,-no_uuid`
      (Phase 1's original macOS build-reproducibility fix) now makes the
      binary fail to *load* at all under the user's current dyld
      (macOS 26.5.2 / Apple clang 21) — `dyld: missing LC_UUID load
      command`. Fixed by removing that flag and instead masking the
      Mach-O LC_UUID's bytes before hashing, only for the
      reproducibility comparison (never the artifact's identity hash).
      See `ISSUES-AND-FIXES-LOG.md` ISSUE-009. **macOS fix confirmed
      2026-08-04:** user re-ran the full 30-trial evaluation, Phase 8
      ablation study, and Phase 8 adaptive-attacker scenarios against
      both `cfs` and `fprime` stub stacks from a clean `work/` directory
      — all passed cleanly with the exact predicted 100%/0% rates
      throughout (`phase5_report.md`, `phase6_report_fprime.md`,
      `phase8_ablation_{cfs,fprime}.json`, `phase8_adaptive_{cfs,fprime}.json`
      all now reflect real n=30 data on real macOS hardware, not just the
      Linux sandbox).
- [x] **ISSUE-010 found and fixed (2026-08-04):** the same re-run surfaced
      one unrelated pytest failure —
      `test_enoexec_with_docker_fallback_but_docker_unavailable_raises_runtime_error`
      — caused by the test relying on Docker genuinely being absent from
      the environment (true in the authoring sandbox, false on the
      user's Mac, which has Docker Desktop installed for Phase 7). Fixed
      by monkeypatching `subprocess.Popen` deterministically instead of
      depending on the real `docker` binary's behavior. See
      `ISSUES-AND-FIXES-LOG.md` ISSUE-010. 41/41 passing on both
      environments now.
- [x] **Real-stack (n=30) run complete, 2026-08-04.** User re-ran the full
      evaluation, Phase 8 ablation study, and Phase 8 adaptive-attacker
      scenarios against `cfs-real` and `fprime-real` — identical
      100%/0% results to the stub stacks throughout, no exceptions. This
      closes out the rejection-risk mitigation work entirely: all three
      chosen mitigations (ablation, adaptive-attacker scenarios, 30-trial
      CI reporting) are now verified against genuine NASA cFS/F´
      binaries, not just the stand-in artifacts. See
      `docs/Threat-Model.md`'s "Phase 8 ablation study"/"Phase 8
      adaptive-attacker scenarios" update notes.
- [x] **Blind(-ish) red-team review complete, 2026-08-04.** In response to
      reviewer objection 7 ("same team designed the threat model, the
      mitigations, and the fixes for the mitigations' own credibility
      gap"), spawned a fresh agent with no prior context on this project,
      gave it only 20 source files under `src/`, and tasked it with
      finding attack vectors the existing 15 test cases + ablation +
      adaptive scenarios don't cover. It reported 7 findings; all 7 were
      independently re-verified against the actual source in this session
      (not just trusted from its report) and all 7 hold up: (1) ground-
      truth state files (version ledger, partition state) have no
      integrity protection and are directly editable, bypassing every
      mechanism built on top; (2) signing-key revocation fails open if
      `revoked_keys.txt` is missing/deleted; (3) the `version` argument
      used for downgrade protection is never bound to the provenance
      record it travels with, enabling a version-inflation DoS distinct
      from anything in the current matrix; (4) the onboard-side
      prohibited-configuration check is a permanent dead stub (`return
      True`), additionally gated by a literal `condition_name == "S5"`
      string match rather than the mechanism flag; (5) the S5
      authorization-evidence document is unsigned and silently
      overwritten on every re-run against the same artifact hash; (6) no
      revocation mechanism exists for the attestation key; (7)
      operational-monitoring mismatches (test cases #13/#15) are logged
      but never enforced — `pipeline.run()` never branches on the
      result. See `docs/Threat-Model.md` "Phase 8 independent (blind,
      AI) red-team review" for the full write-up, including the honest
      caveat that source-code comments name test-case numbers throughout,
      so this wasn't blind to *which* attacks were already known — only
      independent in design origin. **Decision needed:** whether to fix
      some/all of these 7 gaps before the paper is finalized, or disclose
      them as known limitations/future work instead — not decided in this
      session. If fixing, items 1, 2, and 4 look like the highest-value,
      lowest-effort fixes (HMAC/sign the state files; fail closed on a
      missing revocation list; wire the existing `policy.check_configuration`
      into the onboard stub and fix the string-match gate).
- [x] **Real-baseline comparison (python-tuf) complete, 2026-08-04.** Built
      a real, unmodified upstream `python-tuf` (v7.0.0) repository +
      `ngclient.Updater` client (`evaluation/baselines/tuf_baseline.py`,
      no live HTTP server — a `file://` `FetcherInterface` keeps it
      in-process and deterministic) and ran it against the same 15-case
      attack matrix. Of the 15, only 3 have any TUF-native detection
      mechanism at all: #6 (modified update in transit), #7 (revoked
      signing key), #9 (downgrade attempt) — all three caught 30/30
      (100%). The other 12, including 9 that are load-bearing parts of
      this project's own S1-S5 ladder (SBOM, provenance, builder
      authorization, policy, attestation, rollback, inventory
      reconciliation, telemetry, installation itself), have no
      corresponding concept anywhere in TUF's specification — recorded
      as N/A with a stated architectural reason each rather than run as
      fake scenarios. This directly, empirically substantiates the
      paper's central claim (terrestrial frameworks address a narrower
      problem than spacecraft lifecycle assurance requires) instead of
      merely asserting it. See `docs/Threat-Model.md` "Phase 8
      real-baseline comparison: python-tuf" and
      `evaluation/results/phase8_tuf_baseline.json`. Closes out reviewer
      objection 6. Requirements.txt updated (`tuf>=7.0.0`, comparison-only
      dependency).
- [x] **All 7 red-team-found gaps fixed, 2026-08-04.** New
      `src/state_integrity.py` (HMAC-protected side-state, fail-closed
      on tamper/deletion) closes findings #1, #2, and #6 (version
      ledger, partition state, signing-key revocation list,
      attestation-key revocation list). `ground_auth.py` now binds the
      `version` argument to the provenance record (#3). `onboard.py`'s
      dead policy stub now delegates to real policy evaluation, gated
      by the mechanism flag instead of a string match (#4).
      `authorization_evidence.py` documents are now signed and
      per-run-unique, never overwritten (#5). Detected
      operational-monitoring mismatches now freeze the stack's ledger
      until an operator clears it — real enforcement (#7). Full
      writeup per finding: `ISSUES-AND-FIXES-LOG.md` ISSUE-011 through
      ISSUE-017. Verified via 19 new tests
      (`tests/test_phase8_redteam_fixes.py`) plus a full re-run of the
      existing 47-test suite, all 15 attack-matrix cases, the Phase 8
      ablation study, and the Phase 8 adaptive-attacker scenarios
      against both `cfs` and `fprime` (zero drift in any prior result)
      and against real `cfs-real`/`fprime-real` via
      `tests/test_phase7_real_builds.py` (6/6). Also fixed two real,
      latent instances of finding #2's exact anti-pattern found while
      verifying (`tests/test_phase1_pipeline.py`,
      `evaluation/experiment.py::scenario_07`).
- [x] **Committed and pushed, 2026-08-04: commit `53b8573`** ("Phase 8:
      fix all 7 red-team-found gaps + python-tuf baseline comparison"),
      22 files changed. Also untracked `keys/revoked_keys.txt` from git
      (now gitignored, per the state-integrity fix's new sidecar-file
      convention) — hit a stale `.git/index.lock` from an earlier `git
      status` call in the Claude sandbox along the way, consistent with
      this repo's known recurring lock-contention issue (see
      "Repository" section below); cleared manually from the user's own
      Terminal and the commit/push completed cleanly on retry.
- [x] **Ablation study extended to 5/6 mechanisms + evaluation-code
      correctness tests added, 2026-08-05.** Following the post-fix
      reviewer-objection reassessment, the user chose to act on two of
      four proposed follow-ups (objections 5 and 9), deferring the
      AI-disclosure statement and the objection-7 recursion write-up.
      1. **Objection 5 (ablation scope gap):** `disable_mechanisms` is
         now threaded through `ground_authorization.ground_auth.
         authorize()` and `onboard_verification.onboard.
         verify_received_bundle()`, not just `pipeline.py`'s own gating
         — closing the exact gap stated in Threat-Model.md's prior
         ablation write-up. `sbom`, `provenance`, and the S5 policy check
         (a second scenario for test case #8, distinct from the existing
         #15) are now ablatable; all show the same clean 100%/0%
         isolation as the original 3. `signature` remains deliberately
         excluded (stated design property, not an oversight — see
         `evaluation/ablation.py`'s module docstring). Fixing this also
         required threading the same parameter into `onboard.py`'s
         redundant S5 policy check (Phase 8 finding #4's fix), since that
         check would otherwise have silently caught the attack anyway
         when `machine_readable_authorization` was ablated at the
         ground-auth level, defeating the point of the ablation. Locked
         in with 4 fast, single-trial regression tests
         (`tests/test_phase8_ablation_extension.py`). The extended
         6-mechanism results themselves were run at reduced trial counts
         (n=10/n=5, not the standard n=30) due to this tool's per-command
         time limit and the fact that background processes don't persist
         across separate tool invocations in this sandbox — **the full
         30-trial re-run for the paper's actual numbers still needs to
         happen outside this sandbox**, same pattern as the earlier
         real-stack 30-trial re-runs the user did directly. See
         `docs/Threat-Model.md`'s "Phase 8 ablation study" update.
      2. **Objection 9 (evaluation-code correctness):** added 33 tests
         (`tests/test_evaluation_report_correctness.py`) for `evaluation/
         report.py`'s `_wilson_ci`/`_mean_ci`/`_mean_stdev` and its three
         aggregation functions. `_wilson_ci` cross-checked against an
         independent third-party implementation
         (`statsmodels.stats.proportion.proportion_confint`, statsmodels
         0.14.6, installed and used only to *generate* the hardcoded
         reference values — not a runtime test dependency) at the exact
         normal quantile, matching to 1e-9; the module's actual rounded
         `z=1.96` default separately confirmed close (5e-4). `_mean_ci`
         cross-checked against an independently-written closed-form
         computation. All pass. See `docs/Threat-Model.md`'s new "Phase 8
         evaluation-code correctness tests" section.
      Full regression check after both changes: 66 pre-existing tests
      (phases 1-4, 6, 7, and the 19 red-team-fix tests) plus the 37 new
      tests (4 ablation-extension + 33 correctness) all pass — 103/103,
      zero drift in any prior result.
- [x] **Full 30-trial ablation study confirmed, 2026-08-05.** User ran
      `python3 evaluation/ablation.py` against all four stacks (`cfs`,
      `fprime`, `cfs-real`, `fprime-real`) at the standard `N_TRIALS =
      30`. All four produced the identical result: all 6 cases
      (`#4` sbom, `#5` provenance, `#12` onboard_attestation, `#11`
      trusted_rollback, `#15`/`#8` machine_readable_authorization) at
      100% baseline / 0% ablated, `effect_specifically_attributable_to_
      mechanism: true` throughout — including against the real cFS/F´
      binaries, not just the stub artifacts. This supersedes the
      sandbox's earlier reduced-trial (n=10/n=5) verification run and
      is now the citable number for the paper. See Threat-Model.md's
      "Phase 8 ablation study" update and Research-Paper-Outline.md
      item 5. Raw results: `evaluation/results/phase8_ablation_
      {cfs,fprime,cfs-real,fprime-real}.json`.
- [x] **Remaining-objection decisions made, 2026-08-05 (user).** Item 11
      (AI-use disclosure statement): deferred, to be drafted alongside
      the paper/documentation work itself rather than as standalone prep
      — not forgotten, just sequenced later. Item 8 (repo visibility):
      decided — stays private through the research/writing phase, made
      public at the point of publication. No code or doc changes needed
      for either; recorded here so neither is mistaken for still-undecided
      in a future session.
- [x] **Second (wider) blind red-team review complete, all 12 findings
      triaged, 2026-08-05.** In direct response to the newly-surfaced
      recursion problem (this session's own objection-5/9 fix work was
      designed by the same process being scrutinized, and the first
      red-team pass never saw `build.py`/`health_check.py`/`uplink_sim/`/
      `evaluation/`), spawned a second fresh, context-free agent with
      full `src/` + `evaluation/` coverage (27 files) and an explicit
      mandate to review the fix code itself and audit the evaluation
      harness for vacuous tests. It reported 12 findings; all 12
      independently re-verified against the actual source before any fix
      was written. User chose "fix all 12." 11 fixed:
      1. SBOM bound to the actual artifact hash (was checked only
         internally, never against the co-supplied binary).
      2. Docker health-check fallback now bind-mounts the real installed
         binary instead of running the image's frozen baked-in copy —
         the one finding with real stakes for already-published results
         (checked: didn't corrupt any of the 15 attack-matrix numbers,
         but the implementation didn't match its own documented
         behavior on the exact hardware that produced the real-cFS/F´
         results).
      3. Onboard-side independent downgrade check added (sibling gap to
         the S5-policy fix from the first review).
      4. Attestation freshness floor added (future-dated quotes no
         longer pass indefinitely).
      6. Provenance now records + can optionally enforce a dirty-
         source-tree check (opt-in — not enabled by default, since this
         project's own repo is routinely dirty during active
         development).
      7. `evaluation/experiment.py::scenario_13` rewritten to drive a
         real pipeline execution instead of calling the mismatch
         detector directly with hardcoded constants — exactly the
         vacuous-test pattern objection 9 worries about, found in this
         project's own evaluation code.
      8. `report.py`'s trial-0-only aggregation for two field groups
         fixed to detect (not silently miss) cross-trial divergence.
      9. Ablation baseline-assertion guards made consistent across all
         six cases.
      10. Policy type-coercion bypass closed.
      11. Signing/attestation now log visibility when producing new
         material with an already-revoked key (the natural "refuse to
         sign" fix was tried and reverted — it broke the existing,
         correct test case #7 design; see ISSUE-026 for the full
         reasoning).
      12. Uplink tamper injection diversified across byte offsets.
      Finding #5 (persistent-process health check has no artifact-
      identity tie) documented as a known limitation instead of fixed —
      a real fix needs a bigger design change (correlating a boot marker
      with a per-invocation nonce or hash) than this pass's scope.
      Verified via 31 new tests (`tests/test_second_redteam_fixes.py`)
      plus a full re-run of the existing 66-test regression suite —
      caught and fixed one genuine regression along the way (the new
      onboard downgrade check's `StateIntegrityError` handling needed to
      fail closed internally rather than propagate and crash
      `pipeline.run()`, which broke an existing red-team-fix test;
      fixed, and that test's assertion updated to reflect the
      new-and-earlier, still fail-closed, detection point). Re-confirmed
      the extended ablation study (5/6 mechanisms) still shows clean
      100%/0% isolation after all 12 fixes. Full per-finding writeup:
      `ISSUES-AND-FIXES-LOG.md` ISSUE-018 through ISSUE-029.
      See `docs/Threat-Model.md` "Phase 8 second independent red-team
      review" and `docs/Research-Paper-Outline.md` § 4 item 7's updated
      recursion note.
- [x] **Committed and pushed, 2026-08-05: commit `4994094`** ("Phase 8:
      extend ablation to 6 mechanisms, add eval-code correctness tests,
      second red-team pass + 11 fixes"), 25 files changed (6354
      insertions, 796 deletions) — the objection-5/9 work, the full
      30-trial ablation confirmation, and all 12 second-red-team-pass
      fixes from this session. Hit the same stale `.git/index.lock`
      issue as the prior commit (see "Repository" section below);
      cleared manually from the user's own Terminal (confirmed no real
      git process running first) and the commit/push completed cleanly
      on retry.
- [ ] **Colleague (human) review requested, 2026-08-05 — no longer a
      submission requirement, 2026-08-07.** As the practical next step
      on objection 7's recursion — rather than a third AI-driven
      red-team pass, which would still be spawned and directed by the
      same author+AI process — the user asked a colleague (a security
      engineer) to independently review the codebase, and shared
      `Security-Review-Brief.md` with him. **Decision, 2026-08-07:** the
      colleague's timeline is uncertain enough that the user chose not
      to gate submission on it. This is not being treated as "review
      completed" or "review cancelled" — it stays open, informal, no
      deadline, and its result (if it ever arrives) still gets logged
      exactly like the AI passes (ISSUES-AND-FIXES-LOG.md) whether that's
      before or after submission. Instead, the gap is being disclosed
      honestly as a stated limitation in the paper itself (see
      `docs/Research-Paper-Outline.md` § 4 item 7's 2026-08-07 update for
      the exact disclosure language), and factored into venue choice for
      this submission round (§ 3's 2026-08-07 update) rather than worked
      around or hidden.
- [x] **Committed and pushed, 2026-08-06: commit `81b4a5c`** (ISSUE-030
      fix + tests + docs, plus new `docs/Getting-Started.md` and a
      README refresh — 7 files changed, 528 insertions, 36 deletions).
      Hit the same recurring stale `.git/index.lock` issue as prior
      commits; cleared from the user's own Terminal (confirmed no real
      git process running first) and the commit/push completed cleanly
      on retry.
- [x] **Third independent (blind, AI) red-team pass complete, 2026-08-06
      — different model/tool than the first two.** Run as a stopgap
      while the human colleague review is still pending. The reviewer's
      first attempt accidentally targeted an unrelated repo of the
      author's with a similarly-named path; it caught the mismatch
      itself and stopped, and was re-run cleanly once given the correct
      path (see ISSUE-030 in ISSUES-AND-FIXES-LOG.md and the new
      "Phase 8 third independent red-team review" section in
      Threat-Model.md for the full account). Found one genuinely novel,
      end-to-end-confirmed finding — the S5 policy deny-rule matched
      config keys case-sensitively, so `{"DEBUG_MODE": True}` was
      confirmed onboard and the signed authorization-evidence document
      recorded `overall_result: "pass"` for a release carrying a
      prohibited-intent configuration. Fixed in `src/policy/policy.py`
      (case-fold the config keys once before matching, values-axis
      semantics from ISSUE-027 untouched), regression tests added to
      `tests/test_second_redteam_fixes.py`, and independently
      re-confirmed via a direct `pipeline.run()` call that the bypass is
      closed. Two other candidates the reviewer raised (SBOM
      binding-skipped-when-`binary_path=None`, attestation quote has no
      verifier nonce) both correctly reduced to already-documented items
      on cross-check against the answer-key docs, not new issues. Full
      per-file regression run, no drift (excluding the environment-
      dependent real-Docker-binary tests in `test_phase7_real_builds.py`,
      unaffected). This is the strongest evidence yet that the
      independent-review process itself is doing real work: a genuinely
      different reviewer found a real bypass that two prior AI passes and
      the full test suite had all missed.
- [x] **Committed and pushed, 2026-08-06: commit `badb622`** (ISSUE-031
      fix + 18 tests + docs — 7 files changed, 604 insertions, 34
      deletions). Same recurring stale `.git/index.lock` issue as prior
      commits; cleared from the user's own Terminal and the commit/push
      completed cleanly on retry.
- [x] **Git identity misattribution found and fully corrected, 2026-08-06.**
      Every commit in this repo had author/committer email
      `12345678+Zartharas@users.noreply.github.com` — a placeholder-looking
      numeric ID, not the user's real one. GitHub resolves a commit's
      displayed name/avatar by looking up whichever account currently owns
      that numeric ID, ignoring the username text in the email string; the
      placeholder ID happened to belong to a real, unrelated GitHub account
      (username `shubh2294`), so every commit on GitHub's UI was showing his
      avatar as the author — a display/attribution quirk, not an actual
      access or data leak (`shubh2294` has no access to this private repo
      and nothing of the user's reached his account). Root cause: the git
      config's `user.email` was set to a copy of GitHub's own example
      placeholder format (`12345678+username@users.noreply.github.com`, an
      extremely common documentation example) without substituting the
      real numeric ID. Fixed in two parts: (1) `git config` (both
      `--local` for this repo and `--global` for the machine) updated to
      the user's real private email
      (`1402357+Zartharas@users.noreply.github.com`, confirmed directly
      from GitHub's own Settings → Emails page); (2) the entire existing
      history rewritten via `git filter-branch --env-filter` to correct
      the email on all 23 commits (author + committer), then force-pushed
      — the cheap time to do this was now, while the repo is still private
      with 0 forks/watchers, per the user's explicit priority: "don't want
      to give the impression I had help from some user and didn't give
      credit." First rewrite attempt aborted cleanly (`filter-branch`
      correctly refuses to run on a dirty working tree — a pending
      uncommitted `STATUS.md` edit was in the way); committed that first,
      then the rewrite succeeded on the second attempt, confirmed by every
      commit hash changing. All commit-hash references in this file
      updated to match the new hashes (`3d7370b`→`53b8573`,
      `11fd7df`→`4994094`, `6f8a8bf`→`81b4a5c`, `f04e124`→`badb622`) by
      matching old/new commit messages one-to-one (linear history, no
      merges, message text unchanged by the rewrite). A full backup of the
      pre-rewrite repo was taken first
      (`verifiable-spacecraft-lifecycle-backup-before-rewrite`, sibling
      directory) as a safety net before the destructive rewrite.
- [x] **Fourth independent (blind, AI) red-team pass complete, 2026-08-06
      — different model/tool than the first three.** Specifically tasked
      with adversarially re-testing whether ISSUE-030's fix actually
      held (it didn't) and looking for anything new. Found five more
      re-defeats of the same policy-matcher rule on axes the third
      pass's fix missed (whitespace-in-key, key-collision fail-open,
      non-string-key crash, Unicode fullwidth, container-wrapped
      values), all independently re-verified against the real code
      before any fix was written. Also found a real-but-not-reachable-
      under-this-project's-threat-model gap in
      `installation/partitions.py::confirm_active()` (no re-hash
      immediately before confirming) and correctly self-scoped two more
      observations as documentation-only. See ISSUE-031 in
      ISSUES-AND-FIXES-LOG.md and the new "Phase 8 fourth independent
      red-team review" section in Threat-Model.md for the full account,
      including an honest note on the reviewer hitting and working
      around a genuine tooling outage mid-session. Fixed `policy.py`'s
      matcher properly this time (NFKC-normalize-and-casefold keys,
      checked against every colliding key rather than one collapsed
      dict, Python-truthiness fallback for container values) instead of
      another narrow patch; hardened `confirm_active()`/
      `rollback.resolve()` as defense-in-depth even though not reachable
      by any of the six stated threat actors. 18 new regression tests in
      `tests/test_second_redteam_fixes.py`. Full per-file regression run,
      no drift; `_ablation_case_11`/`_ablation_case_12` (the two
      mechanisms touching the changed code) re-verified directly to
      still isolate correctly. Full 6-mechanism ablation study not
      re-run at full scale in-sandbox due to per-command time
      constraints, consistent with every prior full run needing chunking
      or the user's own machine.
- [ ] Move to Phase 8 (paper drafting and repo polish) — including the
      writing-only work already scoped: objection 1 (make the
      spacecraft-specific-constraints argument explicit and early, not
      left implicit), objections 2 and 10 (honest, explicit scoping of
      uplink-simulation realism and the Docker-timing confound in
      Limitations), and the AI-use disclosure statement (objection 11,
      deferred here from 2026-08-04/05 specifically to be drafted
      alongside the paper itself).
- [ ] Consider reviewing prior related projects already present in the
      Development Projects folder (`mission-aware-satellite-cyber-recovery`,
      `satcom-ttc-post-compromise-recovery`) for reusable components or
      lessons learned

## Blockers

- None currently. GitHub repo is live and up to date (see below).
- None of the code-level open questions (SBOM format, attestation
  approach) are true blockers — they just need a decision before Phase 1
  coding starts.

## Repository

- **Live at:** https://github.com/Zartharas/verifiable-spacecraft-lifecycle (private)
- Pushed from local `master` branch to remote `main` on 2026-08-02.
- Commit author uses GitHub noreply email
  (`12345678+Zartharas@users.noreply.github.com`) per GH007 privacy
  requirement — set via `git config user.email` in this repo; not a global
  git config change.
- The Claude sandbox's mounted-folder git client repeatedly hit stale
  `.git/*.lock` files during commit/push (both `HEAD.lock` and
  `index.lock`), which real Terminal access on the host machine did not
  reproduce identically but did also encounter once. Going forward,
  **commits/pushes for this repo should be run from a local Terminal**,
  not through the Claude sandbox, to avoid repeated lock contention. Claude
  can still edit files directly; the user commits/pushes.

## Claims status (not-yet-permitted list)

Convention adopted from the adjacent `satcom-ttc-post-compromise-recovery`
project in this workspace, which uses explicit machine-readable status
labels for every claim category to prevent overclaiming before evaluation
data exists. Update these labels only when the corresponding phase in
`docs/Implementation-Plan.md` actually completes with passing results —
not based on intent or partial progress.

- Detection-accuracy claims across **all S0-S5 conditions**, **against
  the stand-in stub artifact only**: `PRELIMINARY_INTERNAL_ONLY` — all 15
  attack matrix test cases now pass with 100% detection across 5 repeated
  trials each (Phase 5, see `evaluation/results/phase5_report.md`), with a
  documented, resolved metric-definition baseline (PRD.md § 10). Still
  `PRELIMINARY_INTERNAL_ONLY` rather than fully citable: this is one
  non-cFS artifact in one sandbox environment, not yet the real cFS build
  and not yet cross-validated on a second machine/stack.
- Detection-accuracy claims across **all S0-S5 conditions**, **against
  real cFS and real F´**: `PRELIMINARY_INTERNAL_ONLY` — **upgraded from
  "individual test runs only," Phase 7 real-stack statistical evaluation
  (2026-08-03).** The full repeated-trial evaluation harness (same one
  used for Phase 5/6's stub-artifact results — 5 trials × 6 conditions ×
  15 attack cases) ran successfully against both `core-cpu1` and `Ref`
  after fixing ISSUE-007 (Docker execution fallback) and ISSUE-008 (cFS's
  `fs.mqueue.msg_max` limit under Docker Desktop). Results: 100%
  happy-path success/reproducibility across all 6 conditions for both
  real stacks, 100% detection across all 15 attack cases for both, 0
  false positives/negatives in every condition's confusion matrix for
  both — structurally identical to the stub-artifact results. See
  `evaluation/results/phase6_report_cfs-real.md` /
  `phase6_report_fprime-real.md` and `docs/Threat-Model.md` "Phase 7
  real-stack statistical evaluation results." Still
  `PRELIMINARY_INTERNAL_ONLY` rather than fully citable: this is one
  evaluation run each, on one machine, not independently replicated
  elsewhere.
- Recovery-success claims **against the stub artifacts**:
  `PRELIMINARY_INTERNAL_ONLY` — test cases #10/#11/#12/#14 demonstrate
  rollback working correctly across 5 repeated trials each (100% detection)
  against **both** stand-in stacks (Phase 5 `cfs`, Phase 6 `fprime`), with
  "time to trusted restoration" now a measured metric against the resolved
  S0 baseline (PRD.md § 10), not just pass/fail. **Against real cFS/F´:**
  `PRELIMINARY_INTERNAL_ONLY` — upgraded alongside the detection-accuracy
  claim above; the same statistical run covers rollback (test cases
  #10/#11/#12/#14) with identical 100%/0-false-positive results.
- Reproducible-build claims **against the stub artifacts**:
  `PRELIMINARY_INTERNAL_ONLY` — 100% reproducible across all Phase 5/6
  trials (5 per condition, 6 conditions, both stacks) in this sandbox.
  Reproducible-build claims **against real F´ (`Ref`, v4.2.2)**:
  `PRELIMINARY_INTERNAL_ONLY` — **upgraded from `NOT_PERMITTED`, Phase 7
  reproducibility verification (2026-08-03).** A genuine, independent
  two-from-scratch-builds comparison (`docker build --no-cache`, ~1 hour
  apart) produced a byte-for-byte identical binary (0 bytes differing via
  `cmp -l`). Still `PRELIMINARY_INTERNAL_ONLY` rather than fully citable:
  this is a single comparison (one rebuild), not a repeated-trial result,
  and only covers this project's specific pinned tag + Ubuntu 22.04
  Docker environment.
  Reproducible-build claims **against real cFS (`core-cpu1`, v7.0.1)**:
  `NOT_PERMITTED`, and now for a specific, verified reason rather than
  "not yet tested" — the same independent rebuild comparison found
  `core-cpu1` is **not** bit-identical: 22 bytes differ (of ~915KB),
  precisely isolated to an embedded build-timestamp string and its
  downstream effect on the ELF build-id hash (see
  `docs/Threat-Model.md` "Phase 7 reproducibility verification" for the
  full byte-offset-level methodology). The compiled flight-software logic
  itself is otherwise identical across both builds — this is a real,
  narrow, well-understood non-determinism, not "the build is broken" —
  but bit-identical reproducibility cannot be claimed for cFS as currently
  built. `build.py` still does not recompile either real framework from
  scratch per pipeline call regardless of this result (see its module
  docstring) — the pipeline's own per-run `reproducible=True` for
  `"cfs-real"`/`"fprime-real"` remains a trivial copy-integrity check,
  distinct from the manual verification described here.
- Generalizability claims (beyond a single stack): `PRELIMINARY_INTERNAL_ONLY`
  — **strengthened, Phase 7 real-stack statistical evaluation
  (2026-08-03), and again by Phase 8's ablation/adaptive-attacker work
  (2026-08-04).** The S0-S5 ladder's mechanisms and evidence schema, with
  zero changes beyond the two stack-specific adapters, now show
  structurally identical repeated-trial results across four stacks: two
  stand-in artifacts (`cfs`, `fprime`, Phase 6) and two genuine NASA
  flight-software frameworks (`cfs-real`, `fprime-real`, Phase 7) — and,
  as of Phase 8, this now covers not just the original 15 attack-matrix
  cases but also the 3-mechanism ablation study and the 2 combined-vector
  adaptive-attacker scenarios, all at n=30, all four stacks, all matching.
  Still `PRELIMINARY_INTERNAL_ONLY`, not fully citable: one evaluation run
  per stack, on one or two machines, not independently replicated
  elsewhere. This is nonetheless the strongest generalizability evidence
  gathered so far — "the full S0-S5 ladder's mechanisms and evidence
  schema generalize, with matching detection/recovery/reproducibility
  behavior — including under mechanism ablation and combined-vector
  attacks — across two architecturally distinct stand-in artifacts and
  two real NASA flight-software frameworks" is a defensible
  characterization; "the ladder is validated for operational use on real
  cFS/F´" is not (see the permanent restriction below).
- CCSDS/protocol-conformance claims: `NOT_PERMITTED` — uplink simulator is
  CCSDS-*informed*, not a conformance-tested implementation (see PRD.md
  non-goals)
- Flight-software or operational-spacecraft applicability claims:
  `NOT_PERMITTED` — this is a simulated research prototype only, and this
  restriction is permanent, not phase-gated (see PRD.md non-goals)
- Publication-evidence status: `PRELIMINARY_INTERNAL_ONLY` — Phases 5-7
  now provide a full stub-artifact evaluation with a credible, documented
  baseline (PRD.md § 10) across two architecturally distinct stacks, plus
  a working S0-S2 smoke test against both real frameworks. Still not
  `PERMITTED` for external citation: no repeated-trial evaluation exists
  against either real binary, S3-S5 cannot be tested against them at all
  yet, and reproducibility of either real build is unverified.

Mandatory stop point: do not submit any manuscript, external write-up, or
public claim of a result until the specific phase above has completed and
this section has been updated to reflect it.

## Open questions awaiting a decision

See PRD.md § 9 and Technical-Design-Document.md § 7 for the full list.
Key ones:
1. ~~Repo license~~ — resolved: Apache 2.0
2. ~~Second software stack — pursue now or defer to Phase 6?~~ — resolved:
   pursued now, Phase 6 (2026-08-03), NASA JPL's F Prime (F´)
3. ~~Baseline definition for S0 in effort/overhead metrics~~ — resolved,
   PRD.md § 10
4. ~~SBOM format (CycloneDX vs SPDX)~~ — resolved: CycloneDX (see TDD § 7b)
5. ~~Attestation approach (swtpm vs custom stub)~~ — resolved: custom
   stub, no swtpm available (see TDD § 7c) — revisit if swtpm becomes
   available on a capable machine
6. ~~Ground authorization policy language for S5~~ — resolved: custom
   deny-list, not OPA/Rego (see TDD § 7d)

## Environment notes (for future Claude sessions)

The Claude sandbox's mounted-folder filesystem has repeatedly rejected
`unlink()`/`rmtree()` on files or directories created by a prior process,
even with matching ownership — seen with git lock files (see Repository
section) and with `shutil.rmtree()` in `src/build/build.py` (fixed by
removing the rmtree call and overwriting build outputs in place instead).
**Pattern to follow in new code:** always overwrite files in place
(`open(..., 'w')`, `write_bytes()`, compiler `-o` output) rather than
delete-then-recreate. If you hit `PermissionError`/`Operation not
permitted` on a delete, this is almost certainly why — don't spend time
debugging it as a logic bug.

No Docker, no cmake, no root (`apt-get` fails) in the sandbox. Python 3.10,
git, gcc/make, gpg, openssl, and internet access (via allowlisted proxy)
are available. Install Python packages with `pip3 install
--break-system-packages <pkg>`.

## Session log

| Date | Summary | Docs touched |
|---|---|---|
| 2026-08-02 | Initial documentation scaffold created | All docs (v1) |
| 2026-08-02 | Adopted cFS source-handling policy and claims-status governance from adjacent workspace projects | STATUS.md, Legal-Data-Sourcing-Notes.md |
| 2026-08-02 | Initial commit pushed to GitHub (private repo live), README structure diagram fixed | README.md, STATUS.md, repo now on GitHub |
| 2026-08-03 | Phase 1 (S0 pipeline) built and verified end-to-end: build, signing, ground auth, uplink sim, onboard verification, installation, evidence store, metrics collector. LICENSE added. Real cFS build pinned/documented but not run (no Docker in sandbox). 4/4 tests passing. | LICENSE, README.md, requirements.txt, requirements-dev.txt, .gitignore, src/ (new), cfs-app/ (new), tests/ (new), evaluation/metrics.py (new), docs/Threat-Model.md, docs/Technical-Design-Document.md, docs/Implementation-Plan.md, docs/Legal-Data-Sourcing-Notes.md, STATUS.md |
| 2026-08-03 | Fixed macOS-specific build reproducibility failure: ld64 embeds a non-deterministic UUID load command in Mach-O binaries; disabled via `-Wl,-no_uuid` on Darwin only (Linux GNU ld unaffected). Confirmed 4/4 tests passing on both Linux sandbox and user's macOS. Phase 1 now cross-platform verified. | src/build/build.py |
| 2026-08-03 | Phase 2 (S1/S2: SBOM + provenance) built and verified: SBOM generation/checks, provenance generation/verification, version ledger (downgrade detection), condition-gated ground authorization, uplink v2 with link profiles. 10 new tests covering attack cases #1,#2,#3,#4,#5,#9; 14/14 total passing, no regressions. | src/sbom/ (new), src/provenance/ (new), src/ground_authorization/version_ledger.py (new), src/ground_authorization/ground_auth.py, src/uplink_sim/uplink.py, src/pipeline.py, tests/test_phase2_pipeline.py (new), docs/Threat-Model.md, docs/Technical-Design-Document.md, docs/Implementation-Plan.md, STATUS.md |
| 2026-08-03 | Phase 3 (S3/S4: attestation + rollback) built and verified: software attestation stub (no swtpm available), A/B partition manager (tentative-activate/confirm/revert), health check harness, rollback controller with recovery-image integrity check. 6 new tests covering attack cases #10,#11,#12,#14; 20/20 total passing, no regressions. | src/attestation/ (new), src/installation/partitions.py (new), src/health/ (new), src/rollback/ (new), src/pipeline.py, tests/test_phase3_pipeline.py (new), docs/Threat-Model.md, docs/Technical-Design-Document.md, docs/Implementation-Plan.md, STATUS.md |
| 2026-08-03 | Phase 4 (S5: machine-readable authorization evidence) built and verified: prohibited-configuration policy (custom deny-list, not OPA/Rego), inventory reconciliation, false-telemetry detection, OSCAL-informed authorization evidence aggregator, automated S0-S5 comparison table. 6 new tests covering attack cases #8,#13,#15; 26/26 total passing (all 15 attack matrix cases now implemented). Comparison table generator caught a real Phase 1 evidence-tagging bug (test case #6 tagged at wrong stage) — fixed. | src/policy/ (new), src/operational_monitoring/ (new), src/evidence_store/authorization_evidence.py (new), src/ground_authorization/ground_auth.py, src/pipeline.py, evaluation/metrics.py, tests/test_phase4_pipeline.py (new), docs/Threat-Model.md, docs/Technical-Design-Document.md, docs/Implementation-Plan.md, STATUS.md |
| 2026-08-03 | Phase 5 (evaluation and metrics collection) built and run: 5 repeated trials for the happy path at every condition and every one of the 15 attack matrix test cases at its expected condition. Found and fixed a real correctness bug in `authorization_evidence.py` (constant-hash lookup aggregating cross-run evidence, inflating S5 overhead to ~855,655 bytes); corrected figure is 5,748 bytes. Final results: 100% happy-path success/reproducibility across all 6 conditions, 100% detection across all 15 attack cases, 0 false positives/negatives in every condition's confusion matrix. 26/26 tests still passing, no regressions. | src/evidence_store/authorization_evidence.py, src/pipeline.py, evaluation/experiment.py (new), evaluation/report.py (new), evaluation/results/ (new), docs/PRD.md, docs/Implementation-Plan.md, STATUS.md |
| 2026-08-03 | Phase 6 (generalizability) built and run: added a second target stack (NASA JPL's F Prime, pinned to tag v4.2.2, Apache 2.0) via a new `src/target_stack.py` registry, parameterizing `build.py`/`health_check.py` by `stack`. Every other pipeline module generalized unmodified. Found and fixed a real bug: the version ledger was a single global file, not scoped per stack, wrongly flagging fprime's first release as a downgrade. 9 new tests (35/35 total passing, no regressions). Re-ran the Phase 5 evaluation harness against `fprime`: results structurally identical to stack #1 (100% detection/success/reproducibility, 0 false positives/negatives, matching storage overhead). | src/target_stack.py (new), src/build/build.py, src/health/health_check.py, src/pipeline.py, src/ground_authorization/version_ledger.py, src/ground_authorization/ground_auth.py, fprime-app/ (new), evaluation/experiment.py, evaluation/report.py, evaluation/results/ (phase6 files), tests/test_phase6_generalizability.py (new), docs/PRD.md, docs/Threat-Model.md, docs/Technical-Design-Document.md, docs/Implementation-Plan.md, docs/Legal-Data-Sourcing-Notes.md, STATUS.md |
| 2026-08-03 | Phase 7 (real framework builds, partial): ran both Dockerfiles for the first time on the user's Docker-capable Mac; both failed on the first attempt (ISSUE-001 cFS wrong build invocation, ISSUE-002 F´ wrong install method), fixed by consulting each framework's own authoritative build docs. Both builds succeeded on retry — real `core-cpu1` (v7.0.1) and `Ref` (v4.2.2) confirmed working. Wired in as `"cfs-real"`/`"fprime-real"` stacks (prebuilt-binary mode in `target_stack.py`, since a real framework build is too slow to redo per pipeline call); smoke-tested through S0-S2. Found a genuine architectural mismatch testing S3+ (ISSUE-003): both real binaries are long-running processes, incompatible with `health_check.py`'s run-to-completion model — fixed to fail loudly (`NotImplementedError`) rather than silently mislabel a healthy process as broken. 4 new tests, auto-skip if binaries absent (39/39 total passing). Renumbered Implementation-Plan.md's old Phase 7 (paper drafting) to Phase 8 to make room. | src/target_stack.py, src/build/build.py, src/health/health_check.py, cfs-app/Dockerfile, cfs-app/README.md, cfs-app/confirmed-build.json (new), fprime-app/Dockerfile, fprime-app/README.md, fprime-app/confirmed-build.json (new), .gitignore, tests/test_phase7_real_builds.py (new), docs/PRD.md, docs/Threat-Model.md, docs/Technical-Design-Document.md, docs/Implementation-Plan.md, docs/Legal-Data-Sourcing-Notes.md, ISSUES-AND-FIXES-LOG.md, STATUS.md |
| 2026-08-03 | ISSUE-003 resolved: designed and implemented a persistent-process health-check strategy (`_health_check_persistent_process` in `health_check.py`, selected via new `Stack.health_check_mode` in `target_stack.py`) so S3+ conditions (attestation, health check, rollback) can now be exercised against both real binaries — previously hard-blocked. Launch via `Popen`, watch stdout through a background reader thread for an empirically-confirmed boot-success marker (`core-cpu1`'s `CFE_ES_Main entering OPERATIONAL state`; `Ref`'s `Hit Ctrl-C to quit`, confirmed via direct testing incl. catching a shell-pipe artifact that had made `Ref`'s exit status look ambiguous) within a bounded window, then terminate. Never fabricates a pass — only a genuinely-observed marker counts. Replaced the two `NotImplementedError`-only tests with 4 real assertions (S4 happy path + test case #11 against both real binaries); 41/41 total passing, no regressions. Real-binary S3-S5 claims upgraded from `NOT_PERMITTED` to `PRELIMINARY_INTERNAL_ONLY` in STATUS.md "Claims status." | src/target_stack.py, src/health/health_check.py, tests/test_phase7_real_builds.py, cfs-app/confirmed-build.json, fprime-app/confirmed-build.json, ISSUES-AND-FIXES-LOG.md, docs/Threat-Model.md, docs/Technical-Design-Document.md, docs/Implementation-Plan.md, STATUS.md |
| 2026-08-03 | Phase 7 reproducibility verification complete: rebuilt both real frameworks from scratch a second time (`docker build --no-cache`, ~1 hour after the first) into a separate gitignored `build-output-verify/`, then hash-compared against the first build. F´'s `Ref` (v4.2.2) came back byte-for-byte identical (0 bytes differing via `cmp -l`) — genuinely reproducible. cFS's `core-cpu1` (v7.0.1) did not — 22 of ~915KB bytes differ; root cause isolated precisely (not guessed): a literal embedded build-timestamp string (`202608031808` vs `202608031907`, the two builds' actual wall-clock times) at two byte offsets, plus a 20-byte block that is the ELF `.note.gnu.build-id` SHA-1 note changing as a downstream consequence of that timestamp. Every other byte of `core-cpu1` — the actual flight-software logic — is identical across both builds. Updated both `confirmed-build.json` manifests, STATUS.md "Claims status" (F´ reproducibility upgraded to `PRELIMINARY_INTERNAL_ONLY`; cFS's `NOT_PERMITTED` now backed by a specific verified reason instead of "not yet tested"), Implementation-Plan.md Phase 7 checklist (now fully MET), and Threat-Model.md with the full byte-offset-level methodology. This was a real, upstream-framework finding, not a bug in this project's own code — no ISSUES-AND-FIXES-LOG entry, per that log's scope. | cfs-app/confirmed-build.json, fprime-app/confirmed-build.json, .gitignore, docs/Threat-Model.md, docs/Implementation-Plan.md, STATUS.md |
| 2026-08-03 | Backfilled ISSUES-AND-FIXES-LOG.md with the three real bugs found during Phases 4-6 that had only ever been documented narratively (in Threat-Model.md/STATUS.md), not as proper log entries: ISSUE-004 (test case #6 tagged at the injection point instead of the detection point, surfaced by the Phase 4 automated comparison table), ISSUE-005 (authorization-evidence overhead inflated ~150x by a cross-run-aggregating lookup, found in the first Phase 5 evaluation run), ISSUE-006 (version ledger was a single global file rather than scoped per stack, surfaced immediately on testing the Phase 6 `fprime` stack). All three share a common root-cause pattern worth noting: state or a lookup keyed by something that doesn't uniquely identify "this run/target" silently aggregates cross-run/cross-stack noise instead of failing loudly — the same category of hazard ISSUE-003's non-fabrication principle addresses from a different angle. Numbered 004-006 (logged after 001-003) despite predating them chronologically, since log-entry numbers reflect logging order, not occurrence order. No code changes — documentation only. | ISSUES-AND-FIXES-LOG.md, STATUS.md |
| 2026-08-03 | ISSUE-007 found and fixed: attempting the real repeated-trial evaluation (`evaluation/experiment.py cfs-real`) on the user's actual Mac — for the first time, since every prior individual verification had run in Claude's own Linux sandbox — crashed with `OSError: [Errno 8] Exec format error`. Root cause: `core-cpu1`/`Ref` are Linux ELF binaries (Docker-built) that can't execute directly on macOS outside Docker's virtualization layer; S0-S2 never surfaced this since those stages never execute the binary. A second, more serious bug was found alongside it: `_health_check_persistent_process`'s `except OSError` caught this and silently recorded it as an unhealthy build, fabricating a signal about the artifact that wasn't true. Fixed: `target_stack.py` now records each real stack's `docker_image`/`container_binary_path`; new `_launch_process()` in `health_check.py` tries direct execution first and transparently falls back to `docker run --rm <image> <container_binary_path>` only on `ENOEXEC` specifically — environments that can execute directly (Linux) never invoke Docker. No Docker fallback configured, or Docker itself failing, now raises a loud `RuntimeError` instead of a misleading fail record. New `tests/test_issue007_docker_fallback.py` (4 tests, no real Docker or binaries needed — uses a synthetic file that reliably reproduces ENOEXEC) confirms all three branches plus the Stack validation. 45/45 total passing, no regressions. **Still pending:** the user re-running the evaluation harness to confirm the Docker fallback actually works end-to-end and to gather the real S3-S5 statistical data this was all in service of. | src/target_stack.py, src/health/health_check.py, tests/test_issue007_docker_fallback.py (new), evaluation/experiment.py (diagnostic assert messages), ISSUES-AND-FIXES-LOG.md, docs/Threat-Model.md, STATUS.md |
| 2026-08-03 | User re-ran the evaluation harness with ISSUE-007's fix: `fprime-real` completed successfully end-to-end via the Docker fallback (confirming that fix genuinely works), but `cfs-real` failed again at the identical point. Since `docker run --rm` gives every invocation a fresh container filesystem, the pre-ISSUE-007 "accumulated CDS/EEPROM state" theory couldn't apply anymore, so the actual evidence-store record and a live re-run with a longer window were inspected directly instead of guessed at — found ISSUE-008: `core-cpu1` was genuinely failing to initialize inside the container (`CFE_SB_CreatePipe Failed` → commanded `PROCESSOR RESET` → exit), caused by Docker Desktop's default Linux VM shipping a `fs.mqueue.msg_max` too low for cFE's Software Bus queue depth. Confirmed the fix manually (`docker run --sysctl fs.mqueue.msg_max=1024 ...` reached `OPERATIONAL` and ran indefinitely) before writing any code. Added `Stack.docker_sysctls` (set for `cfs-real` only) and wired it into `health_check.py`'s Docker-fallback command as `--sysctl key=value` flags. 2 new tests (monkeypatched `subprocess.Popen`, no real Docker needed) confirm the flags are constructed and positioned correctly, and that a stack with no `docker_sysctls` never gets a stray flag. 47/47 total passing. **Still pending:** the user re-running `evaluation/experiment.py cfs-real` to confirm this fix works end-to-end and to actually gather the real S3-S5 statistical data. | src/target_stack.py, src/health/health_check.py, tests/test_issue007_docker_fallback.py, ISSUES-AND-FIXES-LOG.md, docs/Threat-Model.md, cfs-app/confirmed-build.json, STATUS.md |
| 2026-08-03 | Phase 7 real-stack statistical evaluation complete: user re-ran `evaluation/experiment.py cfs-real` with ISSUE-008's fix in place and it completed successfully — full repeated-trial harness (5 trials × 6 conditions × 15 attack cases) against both real binaries now done. Results for both `cfs-real` and `fprime-real`: 100% happy-path success/reproducibility, 100% detection across all 15 attack cases, 0 false positives/negatives — structurally identical to the Phase 5/6 stub-artifact results. Upgraded STATUS.md "Claims status": detection/recovery claims against real cFS/F´ across all S0-S5 conditions now `PRELIMINARY_INTERNAL_ONLY` (from "individual test runs only"), generalizability claim strengthened to cover four stacks (two stand-ins, two real frameworks) with matching results. Updated Implementation-Plan.md Phase 7 checklist and Threat-Model.md with the final results table summary. This closes out Phase 7 entirely, including the real-stack data gathering that motivated ISSUE-007/ISSUE-008. Next: Phase 8 (paper drafting and repo polish). | evaluation/results/phase6_raw_results_cfs-real.json (new), evaluation/results/phase6_summary_cfs-real.json (new), evaluation/results/phase6_report_cfs-real.md (new), evaluation/results/phase6_raw_results_fprime-real.json (new), evaluation/results/phase6_summary_fprime-real.json (new), evaluation/results/phase6_report_fprime-real.md (new), ISSUES-AND-FIXES-LOG.md, docs/Threat-Model.md, docs/Implementation-Plan.md, STATUS.md |
| 2026-08-04 | Rejection-risk reassessment against everything built since the original 2026-08-03 review, plus new topics surfaced by this session's own work (Docker-timing confound, the bug list itself, ISSUE-009/010's implications, AI-disclosure depth, the "same author" problem for Phase 8's own mitigations). Fixed two real, environment-dependent bugs found running Phase 8's work on the user's Mac for the first time: ISSUE-009 (`-Wl,-no_uuid`, the original macOS build-reproducibility fix, now breaks binary loadability under current dyld — fixed via post-link Mach-O UUID-byte masking instead of a link flag) and ISSUE-010 (a Docker-fallback regression test silently depended on Docker being absent from the test environment — fixed via deterministic `Popen` monkeypatching). Both confirmed via the user's full clean-`work/`-directory re-run of the 30-trial evaluation + ablation + adaptive scenarios against all four stacks (`cfs`, `fprime`, `cfs-real`, `fprime-real`) — identical 100%/0% results throughout. Updated Research-Paper-Outline.md § 4 to an 11-item reviewer-objections list with a working plan for the three items still fully open (real baseline comparison, independent evaluator, repo visibility). Ran both remaining mitigations this session: (1) independent-evaluator — a fresh, context-free agent given only 20 `src/` files found 7 attack-vector/design gaps beyond the existing test matrix; all 7 independently re-verified against the actual source (not just trusted from the report) and all 7 hold up (unprotected ground-truth state files, fail-open key revocation, unbound version/provenance pairing, dead onboard policy-check stub with a brittle string-match gate, unsigned/overwritable authorization-evidence document, no attestation-key revocation, unenforced monitoring mismatches) — see Threat-Model.md "Phase 8 independent (blind, AI) red-team review"; (2) real baseline comparison — built and ran a real, unmodified `python-tuf` repository + client (`evaluation/baselines/tuf_baseline.py`) against the same 15-case matrix: only 3 cases have any TUF-native mechanism (#6, #7, #9, all 30/30 caught), the other 12 (9 of them load-bearing parts of this project's own ladder) have no TUF equivalent at all — see Threat-Model.md "Phase 8 real-baseline comparison: python-tuf". This closes out reviewer objections 6 and 7 with real, measured evidence rather than argument. Decision on whether to fix the 7 red-team-found gaps before the paper, or disclose as limitations, still deferred. | ISSUES-AND-FIXES-LOG.md, src/build/build.py, tests/test_issue007_docker_fallback.py, evaluation/baselines/tuf_baseline.py (new), evaluation/baselines/__init__.py (new), evaluation/results/phase8_tuf_baseline.json (new), requirements.txt, docs/Threat-Model.md, docs/Research-Paper-Outline.md, STATUS.md |
| 2026-08-04 | Fixed all 7 red-team-found gaps (user chose to fix rather than disclose-as-limitation). New `src/state_integrity.py` (HMAC-protected side-state files, fails closed on tamper/deletion) closes findings #1/#2/#6. `ground_auth.py` now binds the `version` argument to the provenance record (#3). `onboard.py`'s dead policy stub now delegates to real policy evaluation, gated by the mechanism flag instead of a literal string match (#4). `authorization_evidence.py` documents are now signed (dedicated Ed25519 keypair) and filenamed per-run, never overwritten (#5). Detected operational-monitoring mismatches now freeze the affected stack's ledger until an operator clears it — real enforcement, not just a log entry (#7). While verifying, found and fixed two real, latent instances of finding #2's exact anti-pattern (a raw file write bypassing the new integrity sidecar) in `tests/test_phase1_pipeline.py` and `evaluation/experiment.py::scenario_07`; also had to teach `evaluation/experiment.py::run_attack_trials()` and `evaluation/ablation.py::run_ablation_study()` to clear the new freeze between trials, since test cases #13/#15 deliberately trigger the exact mismatch the freeze reacts to on every trial by design. Verified via 19 new tests (`tests/test_phase8_redteam_fixes.py`, one or more per finding, each confirming the fix fails *closed* rather than only patching the reported scenario) plus a full re-run of the existing 47-test suite, all 15 attack-matrix cases, the Phase 8 ablation study, and the Phase 8 adaptive-attacker scenarios against both `cfs` and `fprime` — zero drift in any prior result (100%/0% throughout, 100%/100% for the adaptive scenarios) — and against real `cfs-real`/`fprime-real` via `tests/test_phase7_real_builds.py` (6/6 passing). Full per-finding writeup: `ISSUES-AND-FIXES-LOG.md` ISSUE-011 through ISSUE-017. | src/state_integrity.py (new), src/ground_authorization/version_ledger.py, src/ground_authorization/ground_auth.py, src/installation/partitions.py, src/signing/signing.py, src/attestation/attestation.py, src/onboard_verification/onboard.py, src/evidence_store/authorization_evidence.py, src/pipeline.py, evaluation/experiment.py, evaluation/ablation.py, tests/test_phase1_pipeline.py, tests/test_phase8_redteam_fixes.py (new), ISSUES-AND-FIXES-LOG.md, docs/Threat-Model.md, docs/Research-Paper-Outline.md, STATUS.md |
| 2026-08-04 | Committed and pushed all of the above to `origin/main` (commit `53b8573`) after troubleshooting two Terminal-side git issues on the user's machine (a stuck shell from a multi-line commit message, then a stale `.git/index.lock` left behind by an earlier sandbox `git status` call) — both resolved from the user's own Terminal per this project's git-operations convention. Then, per the user's request, re-discussed the remaining reviewer-objection exposure with the new red-team/TUF-baseline evidence in hand: surfaced a previously-undocumented meta-objection (the fix/verification work for objection 7 was itself designed by the same process being scrutinized, and the red-team pass never saw several modules including its own resulting fix code), then asked the user which of four follow-ups to prioritize before paper drafting. User chose two: extend the ablation study to all 6 mechanisms (objection 5) and add evaluation-code correctness tests (objection 9); deferred the AI-disclosure statement and documenting the objection-7 recursion. | (discussion only; no code/doc changes this entry — see next row for the resulting work) |
| 2026-08-05 | Executed the two objection-5/9 follow-ups approved the prior session. **Objection 5:** threaded `disable_mechanisms` through `ground_authorization.ground_auth.authorize()` and `onboard_verification.onboard.verify_received_bundle()` (previously each built its own `Condition` via `preset()` alone, immune to `pipeline.py`'s ablation override) — this also required fixing onboard's redundant S5 policy check so ablating `machine_readable_authorization` couldn't be silently caught by the un-ablated duplicate. Added 3 new ablation scenarios (`_ablation_case_04` SBOM, `_ablation_case_05` provenance, `_ablation_case_08` S5 policy) to `evaluation/ablation.py`, taking coverage from 3/6 to 5/6 mechanisms (`signature` deliberately excluded — it's the one mechanism active at every condition including the S0 floor, never itself gated by `cond.active()`). All 6 mechanisms confirmed showing clean 100%-active/0%-ablated isolation (run at n=10/n=5 due to this tool's per-command time limit — full 30-trial re-run still needed outside the sandbox before citing in the paper). Locked in with 4 fast regression tests (`tests/test_phase8_ablation_extension.py`). **Objection 9:** added 33 tests (`tests/test_evaluation_report_correctness.py`) for `evaluation/report.py`'s `_wilson_ci`/`_mean_ci`/`_mean_stdev` and its aggregation functions — `_wilson_ci` cross-checked against an independent third-party implementation (`statsmodels.stats.proportion.proportion_confint`, matching to 1e-9 at the exact normal quantile), `_mean_ci` cross-checked against an independently-written closed-form computation, plus boundary/structural properties and a hand-computed synthetic-fixture check of the aggregation logic. Full regression check: 66 pre-existing tests + 37 new tests, 103/103 passing, zero drift. | src/ground_authorization/ground_auth.py, src/onboard_verification/onboard.py, src/pipeline.py, evaluation/ablation.py, tests/test_phase8_ablation_extension.py (new), tests/test_evaluation_report_correctness.py (new), docs/Threat-Model.md, docs/Research-Paper-Outline.md, STATUS.md |
| 2026-08-05 | User ran the full 30-trial ablation study on their Mac against all four stacks (`cfs`, `fprime`, `cfs-real`, `fprime-real`) — identical 100%/0% isolation on all 6 cases across every stack, confirming the sandbox's reduced-trial (n=10/n=5) verification run at full scale, including against the real cFS/F´ binaries. Recorded the two remaining reviewer-objection decisions: AI-disclosure statement deferred to the paper-drafting phase; repo stays private until publication. Then, per the user's request, discussed remaining challenges again — surfaced that this exact session's own fix work (objection 5/9) deepens objection 7's recursion, and that the first red-team pass never saw `build.py`/`health_check.py`/`uplink_sim/`/`evaluation/`. User chose to run a second, wider blind red-team pass rather than just document the gap or defer again. | docs/Threat-Model.md, docs/Research-Paper-Outline.md, STATUS.md |
| 2026-08-05 | Ran a second fresh, context-free red-team agent with full `src/`+`evaluation/` coverage (27 files, closing the first pass's file-coverage gap) and an explicit mandate to review the fix code itself and audit the evaluation harness for vacuous tests. It reported 12 findings, all independently re-verified against source; user chose "fix all 12." Fixed 11 (SBOM-artifact binding, Docker health-check binary-mount mismatch, onboard-side independent downgrade check, attestation future-timestamp floor, provenance dirty-tree opt-in check, `scenario_13` rewritten off a hardcoded/vacuous call onto a real pipeline execution, `report.py`'s trial-0-only aggregation, ablation assertion-guard consistency, policy type-coercion bypass, signing/attestation revoked-key visibility logging, uplink tamper-offset diversification); documented finding #5 (health-check has no artifact-identity tie) as a known limitation instead. One fix (refuse to sign/attest with a revoked key) was tried, found to break the existing correct test case #7 design, and reverted for a visibility-only fix instead. Verified via 31 new tests (`tests/test_second_redteam_fixes.py`) plus a full re-run of the existing 66-test suite — caught and fixed one genuine regression along the way (the new onboard downgrade check needed to fail closed on a `StateIntegrityError` internally rather than let it propagate and crash `pipeline.run()`, which broke an existing red-team-fix test; updated that test to accept the new, earlier, still-fail-closed detection point). Re-confirmed the 5/6-mechanism ablation study still isolates cleanly after all 12 fixes. | src/sbom/sbom.py, src/health/health_check.py, src/onboard_verification/onboard.py, src/attestation/attestation.py, src/provenance/provenance.py, src/policy/policy.py, src/signing/signing.py, src/uplink_sim/uplink.py, src/pipeline.py, evaluation/ablation.py, evaluation/experiment.py, evaluation/report.py, tests/test_second_redteam_fixes.py (new), tests/test_phase8_redteam_fixes.py, ISSUES-AND-FIXES-LOG.md, docs/Threat-Model.md, docs/Research-Paper-Outline.md, STATUS.md |
| 2026-08-06 | Ran a third independent (blind, AI) red-team pass, this time with a genuinely different model/tool than the first two, as a stopgap while the human colleague review remains pending. (The reviewer's first attempt accidentally ran against an unrelated, similarly-named local repo; it caught the structural mismatch itself, stopped, and was re-run cleanly against the correct path.) Found one novel, end-to-end-confirmed finding: the S5 policy deny-rule (`policy.py::_matches()`) matched config keys case-sensitively, so `{"DEBUG_MODE": True}` — meaning the exact same thing as the only prohibited-configuration rule — was never caught, and a real `pipeline.run()` call confirmed the release onboard with the signed authorization-evidence document itself recording `overall_result: "pass"`. This sits on a different axis than ISSUE-027 (second pass, finding #10), which fixed value representations, not key names. Fixed by case-folding the config once before matching; added 2 parametrized regression tests; independently re-confirmed end-to-end that the same config is now rejected at `ground_authorization` with no authorization-evidence document written at all. Two other candidates the reviewer raised (SBOM binding skipped when `binary_path=None`; attestation quote has no verifier nonce) both correctly cross-checked to already-documented items (ISSUE-018, ISSUE-021) rather than new issues, and it independently re-confirmed ISSUE-022's forgeable-boot-marker gap is still live. Full per-file regression run, no drift (excluding the unaffected, unchanged `test_phase7_real_builds.py`). Logged as ISSUE-030. | src/policy/policy.py, tests/test_second_redteam_fixes.py, ISSUES-AND-FIXES-LOG.md, docs/Threat-Model.md, STATUS.md |
| 2026-08-06 | Ran a fourth independent (blind, AI) red-team pass, a different model/tool than the first three, specifically tasked with adversarially re-testing whether ISSUE-030's fix actually held rather than trusting its own regression tests. It didn't: found 5 more re-defeats of the same `policy.py` matcher on axes the third pass's narrow fix missed (whitespace-in-key, key-collision-after-fold fail-open, non-string-key crash, Unicode fullwidth via NFKC, container-wrapped boolean values), plus a real-but-not-reachable-under-this-project's-stated-threat-model gap in `partitions.py::confirm_active()` (no re-hash immediately before permanently confirming a slot), plus two correctly-self-scoped documentation-only observations. All independently re-verified against the real code before any fix was written — every one of the five matcher bypasses reproduced directly, and the Unicode claim was interactively confirmed (`casefold()` alone does not fold fullwidth Latin; NFKC normalization first is required) rather than trusted from the report. Rewrote `policy.py`'s matcher properly this time (checks every colliding key rather than one collapsed dict, Python-truthiness fallback for containers) instead of another narrow patch; hardened `confirm_active()`/`rollback.resolve()` as defense-in-depth even though not reachable by any of the six stated threat actors. 18 new regression tests. Full per-file regression run, no drift; the two mechanisms touching the changed code (`_ablation_case_11` trusted_rollback, `_ablation_case_12` onboard_attestation) re-verified directly to still isolate correctly. Full 6-mechanism ablation study not re-run at full scale in-sandbox (per-command time constraints, consistent with every prior full run). Logged as ISSUE-031. | src/policy/policy.py, src/installation/partitions.py, src/rollback/rollback.py, tests/test_second_redteam_fixes.py, ISSUES-AND-FIXES-LOG.md, docs/Threat-Model.md, STATUS.md |
| 2026-08-07 | Refreshed venue research (venue list, impact factors, and AI-disclosure policies from the 2026-08-03 pass all confirmed still current via live re-check); identified two real, un-addressed submission gaps — no ORCID registered yet (a hard blocker for IEEE TAES specifically), and Computers & Security's CRediT/Highlights/graphical-abstract/data-availability requirements not yet drafted since the manuscript itself doesn't exist yet. Then, per the user's request, decided the colleague (human) review is no longer a submission requirement — its timeline is outside the author's control, so the gap is disclosed as a stated Limitations-section item instead of worked around, and that decision is factored into venue choice for this submission round: lead with a development venue (AeroConf or NDSS SpaceSec, once its 2027 CFP is published) or AIAA JAIS directly, holding Computers & Security and the TDSC/TSE/TOSEM stretch targets for a later revision once either the colleague's review lands or a development venue's own peer review has served as the first real independent human check. Exact Limitations-section disclosure language drafted and recorded. | docs/Research-Paper-Outline.md, STATUS.md |
