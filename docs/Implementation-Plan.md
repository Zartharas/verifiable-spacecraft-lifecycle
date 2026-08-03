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

## Phase 5 — Evaluation and metrics collection — COMPLETE (2026-08-03)

- [x] Metric definitions and baselines resolved and written down *before*
      generating any numbers — PRD.md § 10 (baseline = S0 itself, sandbox-
      timing proxy caveat, evidence-record-count proxy for "manual effort,"
      condition-specific traceability denominator)
- [x] Evaluation harness (`evaluation/experiment.py`) — 5 repeated trials
      for the happy path at every condition (S0-S5) and for every one of
      the 15 attack matrix test cases at its expected condition
- [x] Metric aggregation and reporting (`evaluation/report.py`) — computes
      success/reproducibility rates, mean/stdev timing, traceability
      completeness, storage overhead vs. S0, detection rate per test case,
      and a per-condition TP/FN/TN/FP confusion matrix; writes
      `evaluation/results/phase5_summary.json` and `phase5_report.md`
- [x] Run full evaluation and sanity-check results
- [x] Run full pytest suite to confirm no regressions (26/26 passing)

**Exit criteria: MET.** All 6 conditions: 100% happy-path success and
reproducibility. All 15 attack matrix test cases: 100% detection rate
across 5 trials each, 0 false positives/negatives in every condition's
confusion matrix. S5's storage overhead over S0 is 5,748 bytes (mean,
across all four added artifact types combined) — a real, sane number.

This last figure replaced a materially wrong one: the evaluation harness's
first run showed S5 overhead ballooning to ~855,655 bytes, which turned
out to be a genuine correctness bug (not a reporting artifact) in
`src/evidence_store/authorization_evidence.py` — its `generate_authorization_evidence()`
looked records up by `artifact_hash` internally, and because the stand-in
stub artifact's build hash never changes, that lookup silently aggregated
*every* evidence record ever logged across the whole evaluation session
into each run's "authorization evidence" document, not just that run's
own trail. Fixed by changing the function to take an explicit `records`
list from the caller, with `src/pipeline.py` now tracking an evidence-log
index at the start of `run()` and slicing only the current run's records.
Confirmed via the full pytest suite (26/26 still passing) that the fix
caused no regressions. See the module docstring in
`authorization_evidence.py` and `evaluation/experiment.py`'s module
docstring for the full writeup — this is the same category of
"evidence-store lookups keyed by a constant hash silently aggregate
cross-run noise" trap that the Phase 4 comparison table caught for test
case #6, now caught a second time by the evaluation harness itself. Worth
a sentence in the paper's methodology section: two independent, real bugs
were found purely by the act of building automated, evidence-driven
evaluation tooling, not by manual review.

**Sandbox note:** the full evaluation run (happy path × 6 conditions +
attack trials × 15 test cases, 5 trials each ≈ 135 `pipeline.run()` calls)
takes roughly 45-60 seconds end to end, which exceeds this session's
per-command execution ceiling. Run in three chunks (happy path; attack
cases 1-11; attack cases 12-15, or similar), writing each chunk's results
to a temp file, then merge into `evaluation/results/phase5_raw_results.json`
before running `report.py`. Not a pipeline bug — each individual
`pipeline.run()` call is ~0.2-0.5s; the cumulative total across the whole
matrix is just larger than one command's execution budget.

**Run it yourself:**
```
python3 evaluation/experiment.py               # ~45-60s: writes phase5_raw_results.json
python3 evaluation/report.py                   # writes phase5_summary.json + phase5_report.md
cat evaluation/results/phase5_report.md
```

## Phase 6 — Generalizability (stretch, needed for TDSC/TSE/TOSEM) — COMPLETE (2026-08-03)

- [x] Added a second target stack: NASA JPL's F Prime (F´), Apache 2.0,
      pinned to tag `v4.2.2` (see `fprime-app/README.md`,
      `docs/Legal-Data-Sourcing-Notes.md`) — architecturally distinct from
      stack #1 (component-driven C++ vs. cFS's message-bus C)
- [x] Formalized a stack-agnostic model: `src/target_stack.py` registers
      each stack's source location, compiler, and expected deterministic
      output; only `src/build/build.py` and `src/health/health_check.py`
      needed a `stack` parameter (default `"cfs"`, zero behavior change
      for Phases 1-5). Every other module (`condition.py`,
      `evidence_store/`, `signing/`, `ground_authorization/` besides the
      version ledger, `uplink_sim/`, `onboard_verification/`,
      `installation/`, `attestation/`, `rollback/`, `policy/`,
      `operational_monitoring/`) required no changes at all
- [x] Fixed a real bug surfaced by testing the second stack: the version
      ledger (`src/ground_authorization/version_ledger.py`) was a single
      global file, so approving version 1 for `fprime` right after `cfs`
      had already advanced past version 1 would have been wrongly flagged
      as a downgrade attempt. Fixed by scoping the ledger file per stack
      — the more correct design (a real ground system tracks version
      history per deployed target, not one shared counter)
- [x] Re-ran the full evaluation (happy path × 6 conditions + all 15
      attack matrix test cases, 5 trials each) against the `fprime` stack
      — `evaluation/experiment.py fprime` /
      `evaluation/report.py fprime`, chunked across multiple invocations
      the same way as Phase 5 to stay under the sandbox's per-command
      execution ceiling
- [x] New `tests/test_phase6_generalizability.py` (9 tests): build
      reproducibility, S0/S5 happy path, one representative attack case
      per assurance layer (signature #6, provenance #1, rollback
      #11/#14), and a dedicated regression test for the version-ledger
      stack-scoping fix

**Exit criteria: MET.** Re-running the pipeline against `fprime` required
touching exactly two adapter modules (`build.py`, `health_check.py`) plus
one correctness fix surfaced by the test (`version_ledger.py`) — every
other assurance mechanism generalized with zero changes. Results against
`fprime` are structurally identical to `cfs`: 100% happy-path success/
reproducibility across all 6 conditions, 100% detection across all 15
attack matrix test cases (5/5 trials each), 0 false positives/negatives
in every condition's confusion matrix. Even the storage-overhead figures
match almost exactly (S5 overhead vs. S0 is 5,748 bytes for both stacks)
— expected, since SBOM/provenance/attestation/authorization-evidence
documents are JSON structures sized by their own schema, not by the
underlying binary's size or language. Full numbers in
`evaluation/results/phase6_report_fprime.md`.

**Claims-status note (see STATUS.md):** this demonstrates architectural/
tooling generalizability — the S0-S5 ladder's mechanisms and evidence
schema work unmodified against a second, real, architecturally distinct
flight-software framework's *stand-in* — not validation against two real
flight-software frameworks. Neither cFS nor F´ has actually been built and
run yet; that remains gated on a Docker-capable machine (see
`cfs-app/README.md` and `fprime-app/README.md`).

**Run it yourself:**
```
python3 -m pytest tests/test_phase6_generalizability.py -v
python3 evaluation/experiment.py fprime        # writes phase6_raw_results_fprime.json
python3 evaluation/report.py fprime            # writes phase6_summary_fprime.json + phase6_report_fprime.md
cat evaluation/results/phase6_report_fprime.md
```

## Phase 7 — Real framework builds (cFS, F´) — PARTIALLY COMPLETE (2026-08-03)

- [x] Ran `cfs-app/Dockerfile` and `fprime-app/Dockerfile` on the user's
      Docker-capable Mac. Both failed on the first attempt — the cFS
      Dockerfile assumed a bare `cmake`/`make mission-install` invocation
      that doesn't match the bundle repo's actual Make-based build
      system, and the F´ Dockerfile assumed `pip install -e .` on a repo
      with no setup.py/pyproject.toml. Both fixed by consulting each
      framework's own authoritative build docs instead of guessing again;
      see `docs/Legal-Data-Sourcing-Notes.md` § 5 for the full story,
      including re-pinning cFS from the wrong tag (`v7.0.0`) to the
      actually-current one (`v7.0.1`)
- [x] Both builds succeeded on retry: real `core-cpu1` (cFS) boots and
      logs a genuine CFE startup sequence through `OPERATIONAL` state;
      real `Ref` (F´) built clean and rejects bad CLI args with a real
      usage message. Provenance recorded in `cfs-app/confirmed-build.json`
      / `fprime-app/confirmed-build.json`
- [x] Wired both as new stacks (`"cfs-real"`, `"fprime-real"`) in
      `src/target_stack.py`. Deliberately did NOT make `build.py`
      recompile these from source on every `pipeline.run()` call the way
      the stub stacks do — a real framework build takes minutes, and this
      pipeline is designed around sub-second calls (the Phase 5/6
      evaluation harness alone makes ~135 calls per stack). Instead,
      `build.py` copies the one already-Docker-built binary and documents
      explicitly that the resulting `reproducible=True` is a trivial
      copy-integrity check, not a real two-independent-builds comparison
      — see `src/build/build.py`'s module docstring
- [x] Smoke-tested both real stacks through the full S0-S2 lifecycle
      (build → provenance → SBOM → signing → ground authorization →
      uplink → onboard verification → installation) — works cleanly,
      since none of those stages execute the binary
- [x] Found a real architectural mismatch testing S3+: both real
      binaries are long-running processes (`core-cpu1` loops forever once
      `OPERATIONAL`; `Ref` waits for a network GDS connection), not
      short-lived deterministic CLI programs. `health_check.py`'s
      run-to-completion-and-diff-stdout model doesn't fit either one.
      Rather than let it silently time out and mislabel a healthy process
      as broken, `run_health_check` now raises `NotImplementedError` for
      any stack with `expected_health_output=None` (both real stacks set
      this). New `tests/test_phase7_real_builds.py` (4 tests, auto-skip
      if the local Docker-built binaries aren't present) locks in both
      the S0-S2 happy path and this explicit failure behavior
- [x] Designed and implemented a persistent-process health-check strategy
      (ISSUE-003) so S3+ (attestation, health check, rollback) can be
      exercised against the real binaries. `Stack.health_check_mode` in
      `src/target_stack.py` selects between the existing exact-match
      strategy (stub stacks) and a new `_health_check_persistent_process`
      strategy (real stacks): launch via `Popen`, watch stdout for a real,
      empirically-confirmed boot-success marker (`core-cpu1`'s
      `CFE_ES_Main entering OPERATIONAL state`; `Ref`'s `Hit Ctrl-C to
      quit`) within a bounded window via a background reader thread, then
      terminate regardless of outcome. `tests/test_phase7_real_builds.py`
      now asserts real S4 pass/fail behavior (happy path + test case #11)
      against both real binaries instead of just the prior fail-loud
      `NotImplementedError` gate. See ISSUES-AND-FIXES-LOG.md ISSUE-003
      for the full writeup and Threat-Model.md "Phase 7 findings" for the
      design rationale.
- [ ] **Not yet done:** independently verify reproducibility of either
      real framework build (rebuild from scratch a second time, e.g. via
      `docker build --no-cache`, and compare hashes) — today's builds are
      each a single sample, not yet a reproducibility test

**Exit criteria: MET**, aside from the separately-tracked reproducibility
item above (not part of ISSUE-003 — a distinct, still-open verification
task). The real artifacts exist, are integrated into the stack registry,
and now flow cleanly through S0-S5 including attestation, the
persistent-process health check, and rollback. See
Threat-Model.md "Phase 7 findings" for the full writeup and STATUS.md
"Claims status" for exactly what is and isn't citable from this work.

**Run it yourself** (requires having run the Docker builds first — see
`cfs-app/README.md` / `fprime-app/README.md`):
```
python3 -m pytest tests/test_phase7_real_builds.py -v
```

## Phase 8 — Paper drafting and repo polish

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
