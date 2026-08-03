# Project Status

**Read this file first in every new session.** It is the single source of
truth for "where are we right now." Update it at the end of every work
session, however small.

---

## Current phase

**Phase 7 — Real framework builds: PARTIALLY COMPLETE.**
(see `docs/Implementation-Plan.md`) Both `cfs-app/Dockerfile` and
`fprime-app/Dockerfile` now run successfully on the user's Docker-capable
Mac (after fixing real bugs in both — see below). Real `core-cpu1` (cFS)
and `Ref` (F´) binaries are built, confirmed working, and wired into the
pipeline as `"cfs-real"`/`"fprime-real"` stacks, smoke-tested through the
full S0-S2 lifecycle. **Not yet done:** S3+ conditions against the real
binaries (blocked on a persistent-process health-check design — both
real binaries are long-running, not short-lived CLI programs) and
independent reproducibility verification (today's builds are one sample
each, not a two-build comparison). Next up: decide how to health-check a
persistent process, or move to Phase 8 (paper drafting) treating the
current real-build integration as sufficient for now.

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
- [x] **Phase 7 (real framework builds) partially complete** — real cFS
      (`core-cpu1`, tag v7.0.1) and real F´ (`Ref`, tag v4.2.2) both built
      successfully via Docker on the user's Mac, after fixing two real
      Dockerfile bugs (see ISSUES-AND-FIXES-LOG.md ISSUE-001/002). Wired
      in as `"cfs-real"`/`"fprime-real"` stacks; smoke-tested through the
      full S0-S2 lifecycle; 39/39 tests passing (35 + 4 new, auto-skip if
      binaries absent). **Not complete:** S3+ against real binaries
      (blocked on a persistent-process health-check design — see
      ISSUE-003) and independent reproducibility verification

## What's next (immediate)

- [ ] **You:** commit + push this session's changes
- [ ] Decide how to health-check a persistent process (cFS/F´ real
      binaries don't exit on their own) so S3+ conditions can be
      exercised against them — see ISSUES-AND-FIXES-LOG.md ISSUE-003 and
      Implementation-Plan.md Phase 7 for candidate designs, none chosen yet
- [ ] Optionally: independently verify reproducibility of either real
      build (rebuild from scratch a second time, e.g.
      `docker build --no-cache`, compare hashes) — not done yet, current
      "reproducible=True" for real stacks is a trivial copy-check, not a
      real test
- [ ] Retroactively backfill ISSUES-AND-FIXES-LOG.md entries for the
      Phase 4/5/6 bugs that were found but only documented narratively in
      Threat-Model.md/STATUS.md before the log was actually put into use
- [ ] Otherwise, move to Phase 8 (paper drafting and repo polish)
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
- Detection-accuracy claims against real cFS or real F´ (S0-S2
  mechanisms — signature, SBOM, provenance, ground authorization):
  `PRELIMINARY_INTERNAL_ONLY` — **upgraded from `NOT_PERMITTED`, Phase 7
  (2026-08-03).** Both real binaries (`core-cpu1` v7.0.1, `Ref` v4.2.2)
  are now built and smoke-tested through the S0-S2 lifecycle
  successfully. Still `PRELIMINARY_INTERNAL_ONLY`, not fully citable:
  this is a single smoke-test run each, not a repeated-trial evaluation
  (no Phase-5/6-style statistical run has been done against the real
  binaries yet).
- Detection-accuracy claims against real cFS or real F´ for S3-S5
  mechanisms (attestation, health check, rollback, machine-readable
  authorization evidence): `NOT_PERMITTED` — cannot currently be tested
  at all against either real binary; both are long-running processes
  incompatible with `health_check.py`'s current design (see
  ISSUES-AND-FIXES-LOG.md ISSUE-003). This is a hard blocker, not just
  "not yet run."
- Recovery-success claims **against the stub artifacts**:
  `PRELIMINARY_INTERNAL_ONLY` — test cases #10/#11/#12/#14 demonstrate
  rollback working correctly across 5 repeated trials each (100% detection)
  against **both** stand-in stacks (Phase 5 `cfs`, Phase 6 `fprime`), with
  "time to trusted restoration" now a measured metric against the resolved
  S0 baseline (PRD.md § 10), not just pass/fail. Against either real
  framework: `NOT_PERMITTED` (see ISSUE-003 above — rollback is an
  S3+ mechanism).
- Reproducible-build claims **against the stub artifacts**:
  `PRELIMINARY_INTERNAL_ONLY` — 100% reproducible across all Phase 5/6
  trials (5 per condition, 6 conditions, both stacks) in this sandbox.
  Reproducible-build claims **against either real framework**:
  `NOT_PERMITTED` — a real binary now exists for each, but `build.py`
  deliberately does not recompile a real framework from scratch per
  pipeline call (see `build.py` module docstring), so the pipeline's own
  `reproducible=True` for `"cfs-real"`/`"fprime-real"` is a trivial
  copy-integrity check, not a genuine two-independent-builds comparison.
  That comparison has not been performed. Do not cite either real
  framework as "reproducibly built" until it has.
- Generalizability claims (beyond a single stack): `PRELIMINARY_INTERNAL_ONLY`
  — **resolved from `NOT_PERMITTED`, Phase 6 (2026-08-03), stub-artifact
  scope only.** The S0-S5 ladder's mechanisms and evidence schema were
  re-run, unmodified except for two adapter modules, against a second,
  architecturally distinct stand-in stack (F Prime-informed) with
  structurally identical results. Still `PRELIMINARY_INTERNAL_ONLY`, not
  fully citable: this demonstrates architectural/tooling generalizability
  between two *stand-in artifacts*. Phase 7 (real builds) extends S0-S2
  of this claim to real artifacts, but S3-S5 generalizability against
  real frameworks is `NOT_PERMITTED` per the health-check blocker above —
  do not state or imply "the full S0-S5 ladder validated on real cFS and
  F´" yet.
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
