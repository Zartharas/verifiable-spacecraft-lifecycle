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
- [ ] **You:** commit + push this session's changes
- [ ] Move to Phase 8 (paper drafting and repo polish)
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
