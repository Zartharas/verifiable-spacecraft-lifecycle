# Project Status

**Read this file first in every new session.** It is the single source of
truth for "where are we right now." Update it at the end of every work
session, however small.

---

## Current phase

**Phase 3 — Attestation + Rollback (S3/S4): COMPLETE.** (see `docs/Implementation-Plan.md`)
Next up: Phase 4 (S5 — machine-readable authorization evidence), or run
`cfs-app/Dockerfile` to bring the real cFS build online.

## Last session summary

**Date:** 2026-08-03 (session 3)

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
- [x] **Phase 3 (S3/S4: attestation + rollback) complete** — see
      Implementation-Plan.md for full breakdown; 20/20 tests passing

## What's next (immediate)

- [ ] **You:** run `cfs-app/Dockerfile` on your Mac (has Docker) to build
      the real cFS sample app; report back so the target artifact can be
      swapped from the stub to the real thing
- [ ] **You:** commit + push this session's changes
- [ ] Begin Phase 4 of Implementation-Plan.md: machine-readable
      authorization evidence (S5) — includes test case #13 (deferred from
      Phase 3), prohibited-configuration policy (test case #8), inventory
      reconciliation, false-telemetry detection (test case #15)
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

- Detection-accuracy claims at **S0-S4 only**, **against the stand-in
  stub artifact only**: `PRELIMINARY_INTERNAL_ONLY` — test cases #1, #2,
  #3, #4, #5, #6, #7, #9, #10, #11, #12, #14 all pass in automated tests
  (see Threat-Model.md "Phase 1/2/3 results"), but this is 5 of 6
  conditions, one non-cFS artifact, no statistical repetition. Not
  citable as a research result yet. Test case #13 remains unimplemented
  (Phase 4/S5), and test cases #8, #15 also await Phase 4.
- Detection-accuracy claims for S5 or against real cFS: `NOT_PERMITTED` —
  not implemented / not run yet
- Recovery-success claims **against the stub artifact**:
  `PRELIMINARY_INTERNAL_ONLY` — test cases #10/#11/#14 demonstrate
  rollback working correctly in automated tests (see Threat-Model.md
  "Phase 3 results"), but "time to trusted restoration" as a *measured
  metric* (not just pass/fail) still needs Phase 5 (evaluation) and a
  defined baseline (PRD.md § 8) before it's citable.
- Reproducible-build claims **against the stub artifact**:
  `PRELIMINARY_INTERNAL_ONLY` — verified bit-identical across 2 runs in
  this sandbox; not yet demonstrated for the real cFS build (needs Docker)
- Generalizability claims (beyond single cFS stack): `NOT_PERMITTED` —
  requires Phase 6
- CCSDS/protocol-conformance claims: `NOT_PERMITTED` — uplink simulator is
  CCSDS-*informed*, not a conformance-tested implementation (see PRD.md
  non-goals)
- Flight-software or operational-spacecraft applicability claims:
  `NOT_PERMITTED` — this is a simulated research prototype only, and this
  restriction is permanent, not phase-gated (see PRD.md non-goals)
- Publication-evidence status: `NOT_PERMITTED` until Phase 5 (evaluation)
  produces results with a credible baseline (see PRD.md § 8 metric
  legitimacy risk)

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
6. Ground authorization policy language for S5 (custom DSL vs OPA/Rego) —
   needed for Phase 4

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
