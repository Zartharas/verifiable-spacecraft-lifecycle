# Project Status

**Read this file first in every new session.** It is the single source of
truth for "where are we right now." Update it at the end of every work
session, however small.

---

## Current phase

**Phase 4 — Machine-Readable Authorization Evidence (S5): COMPLETE.**
(see `docs/Implementation-Plan.md`) All 6 assurance conditions (S0-S5) now
implemented, all 15 attack matrix test cases passing. Next up: Phase 5
(full statistical evaluation) or Phase 6 (generalizability), or run
`cfs-app/Dockerfile` to bring the real cFS build online.

## Last session summary

**Date:** 2026-08-03 (session 4)

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

## What's next (immediate)

- [ ] **You:** run `cfs-app/Dockerfile` on your Mac (has Docker) to build
      the real cFS sample app; report back so the target artifact can be
      swapped from the stub to the real thing
- [ ] **You:** commit + push this session's changes
- [ ] Begin Phase 5 of Implementation-Plan.md: full statistical
      evaluation (repeated trials, all metrics from PRD.md § success
      criteria, credible baselines) — or Phase 6 (second software stack,
      for generalizability) if pursuing that before evaluation
- [ ] Fix the comparison-table double-counting limitation noted in
      Threat-Model.md "Phase 4 results" as part of Phase 5's more
      rigorous evaluation (count test instances, not tagged records)
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
  attack matrix test cases now pass in automated tests (see
  Threat-Model.md "Phase 1/2/3/4 results"), and an automated comparison
  table can be generated, but this is still one non-cFS artifact with no
  statistical repetition (single run per test case, not repeated trials).
  Not citable as a research result yet — that's exactly what Phase 5 is for.
- Detection-accuracy claims against real cFS: `NOT_PERMITTED` — not run yet
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
