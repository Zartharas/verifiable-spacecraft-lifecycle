# Project Status

**Read this file first in every new session.** It is the single source of
truth for "where are we right now." Update it at the end of every work
session, however small.

---

## Current phase

**Phase 5 — Evaluation and metrics collection: COMPLETE.**
(see `docs/Implementation-Plan.md`) All 6 assurance conditions × 5 repeated
trials each for the happy path, and all 15 attack matrix test cases × 5
trials each at their expected condition. 100% detection across every
attack case, 100% happy-path success/reproducibility, 0 false positives/
negatives in every condition's confusion matrix, S5 storage overhead a
sane 5,748 bytes over S0. Next up: Phase 6 (generalizability), or run
`cfs-app/Dockerfile` to bring the real cFS build online — the latter was
explicitly deferred until Phase 5 completed.

## Last session summary

**Date:** 2026-08-03 (session 5)

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

## What's next (immediate)

- [ ] **You:** run `cfs-app/Dockerfile` on your Mac (has Docker) to build
      the real cFS sample app; report back so the target artifact can be
      swapped from the stub to the real thing — this was explicitly
      deferred until Phase 5 completed, and Phase 5 is now done
- [ ] **You:** commit + push this session's changes
- [ ] Begin Phase 6 (second software stack, for generalizability) or
      Phase 7 (paper drafting) — or pursue the real-cFS Docker build first
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
- Detection-accuracy claims against real cFS: `NOT_PERMITTED` — not run yet
- Recovery-success claims **against the stub artifact**:
  `PRELIMINARY_INTERNAL_ONLY` — test cases #10/#11/#12/#14 demonstrate
  rollback working correctly across 5 repeated trials each (100% detection,
  Phase 5), with "time to trusted restoration" now a measured metric
  against the resolved S0 baseline (PRD.md § 10), not just pass/fail. Still
  not against real cFS.
- Reproducible-build claims **against the stub artifact**:
  `PRELIMINARY_INTERNAL_ONLY` — 100% reproducible across all Phase 5
  trials (5 per condition, 6 conditions) in this sandbox; not yet
  demonstrated for the real cFS build (needs Docker)
- Generalizability claims (beyond single cFS stack): `NOT_PERMITTED` —
  requires Phase 6
- CCSDS/protocol-conformance claims: `NOT_PERMITTED` — uplink simulator is
  CCSDS-*informed*, not a conformance-tested implementation (see PRD.md
  non-goals)
- Flight-software or operational-spacecraft applicability claims:
  `NOT_PERMITTED` — this is a simulated research prototype only, and this
  restriction is permanent, not phase-gated (see PRD.md non-goals)
- Publication-evidence status: `PRELIMINARY_INTERNAL_ONLY` — Phase 5 now
  has a full evaluation with a credible, documented baseline (PRD.md § 10),
  resolving the "metric legitimacy" risk from PRD.md § 8. Still not
  `PERMITTED` for external citation until run against the real cFS build
  and, ideally, a second software stack (Phase 6).

Mandatory stop point: do not submit any manuscript, external write-up, or
public claim of a result until the specific phase above has completed and
this section has been updated to reflect it.

## Open questions awaiting a decision

See PRD.md § 9 and Technical-Design-Document.md § 7 for the full list.
Key ones:
1. ~~Repo license~~ — resolved: Apache 2.0
2. Second software stack — pursue now or defer to Phase 6?
3. Baseline definition for S0 in effort/overhead metrics
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
