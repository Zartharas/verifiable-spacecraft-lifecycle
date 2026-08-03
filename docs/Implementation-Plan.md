# Implementation Plan

**Last updated:** 2026-08-02
**Status:** Draft v1 — no phases started yet

Each phase below should end with a STATUS.md update and, where relevant,
new entries in ISSUES-AND-FIXES-LOG.md for anything nontrivial that broke
and got fixed along the way.

## Phase 0 — Project setup (current phase)

- [x] Define PRD, Threat Model, Pipeline Flow, TDD (this document set)
- [ ] Finalize repo license (Apache 2.0 vs MIT)
- [ ] Create GitHub repo, push initial doc set
- [ ] Set up local dev environment (Docker/Docker Compose, cFS toolchain)
- [ ] Confirm SBOM format, attestation approach, policy language (open
      questions in Technical-Design-Document.md § 7)

## Phase 1 — Minimal S0 pipeline (baseline)

Goal: get a single cFS app moving through the full 12-stage lifecycle at
condition S0 (signature only), end to end, with all other mechanisms
present in the architecture but inactive (per condition-switching design).

- [ ] Select and build target cFS sample app
- [ ] Reproducible build environment (Docker/Nix-pinned)
- [ ] Basic signing (cosign or equivalent)
- [ ] Ground authorization stub (approve/deny, minimal policy)
- [ ] Uplink simulator v1 (can start with no latency/loss modeling, refine
      in Phase 2)
- [ ] Onboard verification agent (signature check only at S0)
- [ ] Installation (simple, no A/B yet at S0)
- [ ] Evidence store v1 (schema from TDD § 4)
- [ ] End-to-end smoke test: artifact moves source → installed with a
      valid evidence trail
- [ ] Metrics collector v1 (even if most metrics are trivial at S0)

**Exit criteria:** a clean run of test case #6 (modified update in
transit) is correctly rejected by signature verification, with an evidence
record showing the rejection.

## Phase 2 — SBOM + Provenance (S1, S2)

- [ ] SBOM generation, wired into signed release bundle
- [ ] Provenance generation (in-toto/SLSA), wired into signed release bundle
- [ ] Ground authorization policy checks expanded to consider SBOM/provenance
- [ ] Uplink simulator v2: add configurable latency/loss/bandwidth ceiling,
      CCSDS-informed
- [ ] Test cases #1–5 implemented and passing at expected conditions
- [ ] Test case #9 (downgrade attempt) — provenance version check

**Exit criteria:** S1 and S2 conditions each demonstrably catch a superset
of what S0 catches, with evidence records showing the mechanism that
caught each case.

## Phase 3 — Attestation + Rollback (S3, S4)

- [ ] Software-based attestation (swtpm or custom) at boot/runtime
- [ ] A/B partition manager
- [ ] Health validation harness
- [ ] Rollback controller wired to health/attestation failure
- [ ] Test cases #10–14 implemented and passing at expected conditions

**Exit criteria:** an interrupted installation (#10) and a failed health
check (#11) both correctly trigger rollback to last-known-good, with full
evidence trail, and recovery success/time-to-trusted-restoration metrics
are being collected.

## Phase 4 — Machine-readable authorization evidence (S5)

- [ ] OSCAL-informed (or similar) structured evidence output across the
      whole lifecycle
- [ ] Ground authorization policy checks for prohibited configurations
      (test case #8) using machine-readable policy
- [ ] Inventory reconciliation logic (test case #13)
- [ ] False-telemetry detection logic (test case #15)

**Exit criteria:** all 15 test cases from Threat-Model.md pass at their
expected detection condition; full S0–S5 comparison table can be generated
from the evidence store automatically.

## Phase 5 — Evaluation and metrics collection

- [ ] Run full test suite (all 15 cases × all 6 conditions) with repeated
      trials for statistical validity
- [ ] Compute all metrics from PRD.md § success criteria / Threat-Model.md § 4
- [ ] Produce comparison tables/plots
- [ ] Sanity-check every metric against a credible baseline (resolve the
      "metric legitimacy" open question from PRD.md before trusting results)

## Phase 6 — Generalizability (stretch, needed for TDSC/TSE/TOSEM)

- [ ] Add a second software stack or formalize a stack-agnostic model
- [ ] Re-run relevant subset of evaluation against the second stack
- [ ] Update Research-Paper-Outline.md venue assessment based on results

## Phase 7 — Paper drafting and repo polish

- [ ] Draft paper per Research-Paper-Outline.md
- [ ] Clean up repo: finalize README, ensure reproducibility instructions
      work from a clean checkout
- [ ] Finalize SECURITY.md, confirm ISSUES-AND-FIXES-LOG.md is
      publication-ready (redact anything that shouldn't be public before
      disclosure timelines are met, if applicable)
- [ ] Submit per venue sequence in Research-Paper-Outline.md

## How to use this plan in future sessions

At the start of any work session: read STATUS.md, find the current phase
here, and confirm STATUS.md and this plan agree on what's done. If they
disagree, STATUS.md is more likely to be current — resolve the conflict
and fix this document before proceeding.
