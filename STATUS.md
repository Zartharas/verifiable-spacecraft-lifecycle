# Project Status

**Read this file first in every new session.** It is the single source of
truth for "where are we right now." Update it at the end of every work
session, however small.

---

## Current phase

**Phase 0 — Project setup / documentation** (see `docs/Implementation-Plan.md`)

## Last session summary

**Date:** 2026-08-02

Set up full documentation scaffold: README, PRD, Threat-Model,
Pipeline-Flow-Document, Technical-Design-Document, Implementation-Plan,
Research-Paper-Outline, Legal-Data-Sourcing-Notes, this STATUS file,
ISSUES-AND-FIXES-LOG, and SECURITY.md. No code written yet. No GitHub repo
created yet (pending user authorization of the GitHub connector or manual
push).

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

## What's next (immediate)

- [ ] Decide repo license (Apache 2.0 vs MIT) — see PRD.md § 9
- [ ] Begin Phase 1 of Implementation-Plan.md: minimal S0 pipeline
- [ ] Resolve open technical decisions in Technical-Design-Document.md § 7
      (SBOM format, attestation approach, policy language)
- [ ] Consider reviewing prior related projects already present in the
      Development Projects folder (`mission-aware-satellite-cyber-recovery`,
      `satcom-ttc-post-compromise-recovery`) for reusable components or
      lessons learned before starting Phase 1 from scratch

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

- Detection-accuracy claims (any S-condition): `NOT_PERMITTED` — no test
  cases implemented yet (Phase 1+)
- Recovery-success / time-to-trusted-restoration claims: `NOT_PERMITTED` —
  requires Phase 3 (rollback) complete
- Reproducible-build claims: `NOT_PERMITTED` — requires Phase 1 build
  environment implemented and verified bit-identical across runs
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
1. Repo license
2. Second software stack — pursue now or defer to Phase 6?
3. Baseline definition for S0 in effort/overhead metrics
4. SBOM format (CycloneDX vs SPDX)
5. Attestation approach (swtpm vs custom stub)

## Session log

| Date | Summary | Docs touched |
|---|---|---|
| 2026-08-02 | Initial documentation scaffold created | All docs (v1) |
| 2026-08-02 | Adopted cFS source-handling policy and claims-status governance from adjacent workspace projects | STATUS.md, Legal-Data-Sourcing-Notes.md |
| 2026-08-02 | Initial commit pushed to GitHub (private repo live), README structure diagram fixed | README.md, STATUS.md, repo now on GitHub |
