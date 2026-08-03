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

## Phase 1 — Minimal S0 pipeline (baseline) — COMPLETE (2026-08-03)

Goal: get a single cFS app moving through the full 12-stage lifecycle at
condition S0 (signature only), end to end, with all other mechanisms
present in the architecture but inactive (per condition-switching design).

- [x] Select and build target cFS sample app — **partially**: a stand-in
      stub artifact is built and tested end-to-end; the real cFS build is
      documented and pinned in `cfs-app/Dockerfile` but not yet run
      (authoring sandbox had no Docker). Run it on a Docker-capable
      machine before treating any result as being about real cFS/spacecraft
      software — see `cfs-app/README.md` and STATUS.md "Claims status."
- [x] Reproducible build environment — implemented via `src/build/build.py`
      (gcc, deterministic flags); verified bit-identical across two
      independent compiles. Docker/cmake version for real cFS documented,
      not yet run.
- [x] Basic signing — **Ed25519 via `cryptography`**, not cosign (see
      Technical-Design-Document.md § 7a for rationale).
- [x] Ground authorization stub (approve/deny, minimal policy) —
      `src/ground_authorization/ground_auth.py`
- [x] Uplink simulator v1 (no latency/loss modeling yet, per plan;
      Phase 2) — `src/uplink_sim/uplink.py`, includes tamper-injection hook
- [x] Onboard verification agent (signature check only at S0) —
      `src/onboard_verification/onboard.py`
- [x] Installation (simple, no A/B yet at S0) — `src/installation/install.py`
- [x] Evidence store v1 (schema from TDD § 4) — `src/evidence_store/`
- [x] End-to-end smoke test: artifact moves source → installed with a
      valid evidence trail — `src/pipeline.py`, `tests/test_phase1_pipeline.py`
- [x] Metrics collector v1 — `evaluation/metrics.py`

**Exit criteria: MET.** `tests/test_phase1_pipeline.py::test_case_06_modified_update_in_transit_is_rejected`
passes — modified update in transit is correctly rejected by onboard
signature verification, with an evidence record showing the rejection
(`test_case_injected: "6"`, `result: "fail"`). Bonus: test case #7
(revoked signing key) also implemented and passing, with an interesting
early-detection result — see Threat-Model.md "Phase 1 results."

**Run it yourself:**
```
pip install -r requirements-dev.txt
python3 src/pipeline.py                        # happy path + test case #6, printed
python3 -m pytest tests/test_phase1_pipeline.py -v
python3 evaluation/metrics.py                  # evidence store summary
```

## Phase 2 — SBOM + Provenance (S1, S2) — COMPLETE (2026-08-03)

- [x] SBOM generation, wired into signed release bundle —
      `src/sbom/sbom.py` (CycloneDX-shaped JSON, hand-rolled — see TDD § 7a)
- [x] Provenance generation (in-toto/SLSA-shaped), wired into signed
      release bundle — `src/provenance/provenance.py`
- [x] Ground authorization policy checks expanded to consider
      SBOM/provenance — `src/ground_authorization/ground_auth.py`, now
      condition-gated via `condition.py`
- [x] Uplink simulator v2: configurable latency/bandwidth/loss via
      `LinkProfile` (LEO_TYPICAL, DEEP_SPACE_TYPICAL, IDEAL presets),
      CCSDS-order-of-magnitude-informed, not RF-accurate (per PRD non-goals)
      — `src/uplink_sim/uplink.py`
- [x] Test cases #1–5 implemented and passing at expected conditions —
      `tests/test_phase2_pipeline.py`
- [x] Test case #9 (downgrade attempt) — version ledger at
      `src/ground_authorization/version_ledger.py`, wired into S2 ground
      authorization

**Exit criteria: MET.** 14/14 tests pass (4 Phase 1 + 10 Phase 2), no
regressions. S1 catches test cases #3 (incomplete SBOM) and #4 (known
test vulnerability), which S0 has no mechanism to catch at all. S2 catches
test cases #1 (binary/source mismatch), #2 (missing provenance), #5
(unauthorized builder), and #9 (downgrade attempt), none of which S0 or S1
can catch. This is the superset property the assurance ladder is supposed
to demonstrate. See Threat-Model.md "Phase 2 results" for the full
breakdown and one interesting scoping note (S2's preset requires SBOM
*and* provenance together, not provenance alone — this tripped up a test
before it tripped up the pipeline itself, see Threat-Model.md).

**Run it yourself:**
```
python3 src/pipeline.py                        # S0 scenarios + S2 happy path
python3 -m pytest tests/ -v                    # all 14 tests
python3 evaluation/metrics.py                  # evidence store summary
```

## Phase 3 — Attestation + Rollback (S3, S4) — COMPLETE (2026-08-03)

- [x] Software-based attestation (**custom stub, not swtpm** — no swtpm/
      tpm2-tools available and no root to install them; see TDD § 7c for
      why this is a materially weaker guarantee than hardware-backed
      attestation and must be stated as such in the paper) —
      `src/attestation/attestation.py`
- [x] A/B partition manager — `src/installation/partitions.py`, with
      tentative-activate/confirm/revert semantics and a recovery-image
      integrity check
- [x] Health validation harness — `src/health/health_check.py`
- [x] Rollback controller wired to health/attestation failure —
      `src/rollback/rollback.py`
- [x] Test cases #10, #11, #12, #14 implemented and passing at expected
      conditions — `tests/test_phase3_pipeline.py`. Test case #13
      (ground/spacecraft inventory disagreement) deferred to Phase 4 (S5)
      per Threat-Model.md — it's an S5 mechanism, not S3/S4.

**Exit criteria: MET.** An interrupted installation (#10) is caught before
ever tentatively activating (system stays on the confirmed baseline,
untouched). A failed health check (#11) is caught after tentative
activation and correctly triggers rollback to the last confirmed
partition. Both have full evidence trails (`installation`,
`health_validation`, `rollback` stages). Bonus: stale attestation (#12)
and invalid recovery image (#14) also implemented and passing — the
latter is a genuinely interesting result (see Threat-Model.md "Phase 3
results"): the rollback mechanism itself needs an integrity check, or a
"recovery" can silently activate a corrupted image.

20/20 tests pass across all three phases, no regressions.

**Run it yourself:**
```
python3 src/pipeline.py                        # includes S4 happy path
python3 -m pytest tests/ -v                    # all 20 tests
python3 evaluation/metrics.py                  # evidence store summary
```

## Phase 4 — Machine-readable authorization evidence (S5) — COMPLETE (2026-08-03)

- [x] OSCAL-*informed* structured evidence output across the whole
      lifecycle — `src/evidence_store/authorization_evidence.py`
      (aggregation shape, not full OSCAL schema conformance — see TDD § 7d)
- [x] Ground authorization policy checks for prohibited configurations
      (test case #8) using machine-readable policy — `src/policy/policy.py`
      (custom deny-list, not OPA/Rego — see TDD § 7d for why)
- [x] Inventory reconciliation logic (test case #13) —
      `src/operational_monitoring/monitoring.py`
- [x] False-telemetry detection logic (test case #15) — same module

**Exit criteria: MET.** All 15 test cases from Threat-Model.md now
implemented and passing at their expected condition (26/26 tests total,
no regressions). `evaluation/metrics.py::build_comparison_table` generates
a full S0-S5 detection matrix automatically from the evidence store —
and immediately caught a real evidence-tagging inconsistency from Phase 1
(test case #6 tagged at the injection point, not the detection point),
fixed in `src/pipeline.py`. See Threat-Model.md "Phase 4 results" for the
full writeup — this is a good concrete example for the paper of why
automated, evidence-driven evaluation catches things manual pass/fail
testing alone had missed for three phases.

**Run it yourself:**
```
python3 src/pipeline.py                        # includes S4/S5 happy paths
python3 -m pytest tests/ -v                    # all 26 tests
python3 evaluation/metrics.py                  # summary + S0-S5 comparison table
```

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
