# Threat Model & Assurance Ladder

**Last updated:** 2026-08-02
**Status:** Draft v1 — defines the experimental design; treat changes here as
requiring a corresponding update to Technical-Design-Document.md and
Implementation-Plan.md.

This document is the core experimental design artifact. Everything else in
the project (pipeline components, test cases, metrics) exists to support
measuring across the conditions defined here.

## 1. Assurance ladder (S0–S5)

Each condition is strictly additive — S(n) includes everything in S(n-1)
plus one new mechanism. This lets us isolate the marginal effect of each
added assurance layer.

| Condition | Mechanisms present | New mechanism vs. prior |
|---|---|---|
| S0 | Signature only | — (baseline) |
| S1 | Signature + SBOM | Software Bill of Materials |
| S2 | Signature + SBOM + build provenance | SLSA/in-toto-style provenance attestation |
| S3 | S2 + onboard attestation | Runtime/boot attestation on the spacecraft side |
| S4 | S3 + trusted rollback | Verified A/B partition rollback on failure |
| S5 | S4 + machine-readable authorization evidence | OSCAL-style structured evidence for ground/auditor consumption |

Each of the 12 pipeline stages (see Pipeline-Flow-Document.md) is either
active or a no-op depending on which condition is under test. The pipeline
implementation must support running the *same* artifact through all six
conditions with only configuration changes — no code forks per condition.
This is a hard architectural requirement (see Technical-Design-Document.md
§ "Condition switching").

## 2. Threat actors considered

- **External attacker with network access** to the ground segment or the
  uplink channel (tampering in transit, replay, downgrade).
- **Compromised build infrastructure** (unauthorized/malicious build
  runner, poisoned dependency).
- **Insider with legitimate but excessive access** (approves a
  configuration that is technically signed but policy-prohibited).
- **Compromised or leaked signing key** (revoked key still presented as
  valid).
- **Onboard software fault** (failed health check, interrupted
  installation) — not adversarial, but must be handled by the same
  recovery machinery and is in scope because assurance mechanisms should
  degrade gracefully under non-adversarial failure too.
- **Ground/space state divergence** (inventory disagreement, false
  "successful installation" telemetry) — covers both deception and honest
  desync.

Explicitly out of scope: RF-layer jamming/spoofing, physical tampering with
ground hardware, insider threats with root access to the signing HSM
itself. These are real spacecraft security concerns but outside this
project's scope (supply-chain/lifecycle assurance, not RF security or
personnel security).

## 3. Attack / failure injection matrix

Each row is a standardized test case, run against every applicable
condition (S0–S5) where the relevant mechanism could plausibly detect it.
"Expected detection point" marks which condition should first catch it —
this is the actual hypothesis the experiment tests.

| # | Test case | Pipeline stage injected | Expected first detection at |
|---|---|---|---|
| 1 | Binary does not match source | Build → Provenance | S2 (provenance) |
| 2 | Missing or false provenance | Provenance | S2 |
| 3 | Incomplete SBOM | SBOM generation | S1 |
| 4 | Dependency with known test vulnerability | SBOM / dependency scan | S1 |
| 5 | Unauthorized build runner | Build environment | S2 |
| 6 | Modified update (in transit) | Uplink | S0 (signature should catch this) |
| 7 | Revoked signing key | Signature verification | S0/S2 (requires revocation-aware verification — flag as a design requirement, not automatic) |
| 8 | Correct signature but prohibited configuration | Ground authorization / policy | S5 (needs machine-readable policy evidence) |
| 9 | Downgrade attempt | Ground authorization / onboard verification | S2/S4 (provenance version check, or rollback policy) |
| 10 | Interrupted installation | Installation | S4 (rollback) |
| 11 | Failed health check | Post-install health validation | S3/S4 |
| 12 | Stale attestation | Onboard attestation | S3 |
| 13 | Ground/spacecraft inventory disagreement | Operational monitoring | S5 |
| 14 | Invalid recovery image | Rollback | S4 |
| 15 | False "successful installation" telemetry | Operational monitoring / attestation | S3/S5 |

**Note:** "Expected first detection" values are hypotheses to validate, not
guaranteed outcomes — a key result of the paper may be that some conditions
catch things earlier or later than the naive expectation (e.g., S0 alone
should already catch #6 via signature mismatch; if it doesn't in the
prototype, that's a bug, not a finding).

**Phase 1 results (2026-08-03), against the stand-in artifact — see
cfs-app/README.md for why it's not the real cFS target yet:**

- **Test case #6 (modified update in transit): confirmed detected at S0**,
  matching the hypothesis. Onboard signature verification correctly
  rejects a binary tampered after signing; evidence record logged with
  `test_case_injected: "6"`. See `tests/test_phase1_pipeline.py::test_case_06_modified_update_in_transit_is_rejected`.
- **Test case #7 (revoked signing key): detected at S0, but one stage
  earlier than the Threat-Model.md hypothesis of "S0/S2".** In this
  implementation, `ground_authorization` and `onboard_verification` both
  call the same revocation-aware signature check, so a revoked key is
  caught at the ground-authorization gate before uplink even happens,
  rather than only on the spacecraft side after transmission. This is an
  earlier catch than hypothesized, not a worse one — worth discussing
  explicitly in the paper's Results/Discussion section as an example of a
  condition catching something earlier than the naive expectation (see
  note above and Research-Paper-Outline.md § 4).

**Phase 2 results (2026-08-03), against the stand-in artifact:**

- **Test case #3 (incomplete SBOM): confirmed detected at S1**, matching
  the hypothesis. `sbom_verification` evidence record logged with
  `test_case_injected: "3"`.
- **Test case #4 (dependency with known test vulnerability): confirmed
  detected at S1**, matching the hypothesis. Uses a small synthetic
  vulnerability table (`KNOWN_VULNERABLE_COMPONENTS` in `src/sbom/sbom.py`)
  rather than a real CVE feed — sufficient to test the detection
  *mechanism*, not a claim about real vulnerability coverage.
- **Test case #1 (binary does not match source): confirmed detected at
  S2**, matching the hypothesis. Simulated by corrupting the binary
  *after* provenance generation but *before* signing (`corrupt_binary_
  after_provenance` in `src/pipeline.py`) — models an attacker or faulty
  process substituting the artifact between attestation and release.
- **Test case #2 (missing/false provenance): confirmed detected at S2**,
  matching the hypothesis.
- **Test case #5 (unauthorized build runner): confirmed detected at S2**,
  matching the hypothesis, via a builder-ID allowlist
  (`ALLOWED_BUILDER_IDS` in `src/provenance/provenance.py`).
- **Test case #9 (downgrade attempt): confirmed detected at S2**, at the
  earlier end of the hypothesized "S2/S4" range. Implemented via a simple
  version ledger (`src/ground_authorization/version_ledger.py`) tracking
  the last ground-approved version number.
- **Scoping note worth keeping for the paper's Methods/Discussion
  section:** S2's preset is *signature + SBOM + provenance* (additive per
  the ladder design), not provenance alone. A test for test case #2
  originally failed for the wrong reason — it omitted a valid SBOM, so
  ground authorization rejected on the *missing SBOM* check before ever
  reaching provenance verification, masking the intended failure mode.
  This is a useful illustration of a real methodological trap in this kind
  of layered-condition testing: injecting a single-mechanism failure at a
  multi-mechanism condition requires satisfying every *other* active
  mechanism first, or the test isn't isolating what it claims to isolate.
  Worth a sentence in the paper's evaluation methodology section.

**Phase 3 results (2026-08-03), against the stand-in artifact:**

- **Test case #10 (interrupted installation): confirmed detected at S4**,
  matching the hypothesis. The write-verification step
  (`partitions.verify_written`) catches the mismatch between the intended
  and actual on-disk hash before the new partition is ever tentatively
  activated — the system simply never leaves the confirmed baseline.
- **Test case #11 (failed health check): confirmed detected at S4**,
  matching the hypothesis (S3/S4 range). At S3 alone, a health failure is
  *detected* (logged as `post_install_unrecoverable_at_s3`) but nothing
  can be done about it — no recovery mechanism exists yet at that
  condition. At S4, the same failure triggers a real rollback to the last
  confirmed partition. This S3-vs-S4 contrast (detect-only vs.
  detect-and-recover) is a clean, citable illustration of what the extra
  assurance layer actually buys you — worth a table row or figure in the
  paper specifically contrasting S3 and S4 outcomes for the same fault.
- **Test case #12 (stale attestation): confirmed detected at S3**
  (attestation verification itself, which is active from S3), and at S4
  additionally **triggers a rollback**, matching and slightly exceeding
  the hypothesis. Simulated via `attestation_backdate_seconds` rather than
  a real elapsed-time wait, for fast deterministic tests.
- **Test case #14 (invalid recovery image): confirmed detected at S4**,
  matching the hypothesis, and this is the most interesting Phase 3
  result: the rollback path checks the *recovery target's own* on-disk
  integrity (not just the failing partition's) before trusting it, and
  correctly reports `recovery_failed` rather than silently activating
  corrupted "known-good" content. This is a genuinely important point for
  the paper — a naive A/B rollback implementation that skips this check
  would look correct in every test except this one, and would silently
  make things worse in the exact scenario rollback exists to handle.
- **Test case #13 (ground/spacecraft inventory disagreement): NOT
  implemented in Phase 3**, deferred to Phase 4 (S5) as originally scoped
  — it requires machine-readable authorization evidence to reconcile
  ground and spacecraft state, which doesn't exist until S5.

**Phase 4 results (2026-08-03), against the stand-in artifact — all 15
attack matrix test cases now implemented:**

- **Test case #8 (correct signature but prohibited configuration):
  confirmed detected at S5**, matching the hypothesis, via a hand-rolled
  policy check (not OPA/Rego — see TDD § 7d for why).
- **Test case #13 (ground/spacecraft inventory disagreement): confirmed
  detected at S5**, matching the hypothesis. The natural trigger for this
  in a real system — a Phase 3 rollback the ground was never told
  about — is exactly what the reconciliation check compares against.
- **Test case #15 (false "successful installation" telemetry): confirmed
  detected at S5**, matching the hypothesis (S5/S3 range), by cross-
  checking claimed telemetry against the actual rollback outcome recorded
  in the evidence store.
- **All 15 test cases from the attack matrix are now implemented and
  passing at their expected condition.** `evaluation/metrics.py::build_
  comparison_table` generates the full S0-S5 detection matrix
  automatically from the evidence store — this satisfies the Phase 4
  exit criterion directly and is the tool that surfaced the finding below.
- **Methodological finding worth keeping for the paper:** building the
  automated comparison table immediately surfaced that test case #6
  (modified update in transit, from Phase 1) was tagged at the *injection*
  point (`uplink`, logged `n/a`) rather than the *detection* point
  (`onboard_signature_verification`, logged `fail`), so it silently showed
  `caught=0` in the table despite genuinely being caught (confirmed by the
  Phase 1 test passing all along). Every other test case in Phases 2-4
  tags the catching record directly — #6 was the one inconsistency,
  introduced in Phase 1 before this convention was established. Fixed by
  explicitly tagging the detection record in `src/pipeline.py`. This is a
  good concrete example for the paper's methodology section of *why*
  automated, evidence-store-driven evaluation matters: a manual pass/fail
  test suite had already "passed" this case for three phases without
  anyone noticing the evidence trail itself was incomplete.
- **Known limitation of the current comparison table, refined in
  Phase 5:** because test case #6 now has two tagged records (injection
  point + detection point) for one conceptual test instance, the table
  reports `seen=2, caught=1` rather than `seen=1, caught=1` — a
  double-count, not a correctness bug (the pass/fail signal is right).
  **Resolved in Phase 5** (see "Phase 5 results" below): the evaluation
  harness (`evaluation/experiment.py`) counts *test instances* directly —
  each scenario function returns one `caught: bool` per trial from
  `PipelineResult` fields, not from counting evidence-store records — so
  this double-count doesn't propagate into any Phase 5 metric.
  `evaluation/metrics.py::build_comparison_table` (the Phase 4 tool) still
  has the underlying record-counting behavior and should be treated as a
  quick-look debugging aid, not a source of cited numbers; cite Phase 5's
  `evaluation/results/phase5_report.md` instead.

## Phase 5 results (evaluation and metrics collection, 2026-08-03)

Ran 5 repeated trials of the happy path at every condition (S0-S5) and of
every one of the 15 attack matrix test cases at its expected condition
(`evaluation/experiment.py`), then aggregated per PRD.md § 10's resolved
metric definitions (`evaluation/report.py`). Full numbers in
`evaluation/results/phase5_report.md`; summary here:

- **Happy path:** 100% success rate and 100% build-reproducibility rate
  across all 6 conditions, all 5 trials each. Traceability completeness is
  100% at every condition — every expected pipeline stage for that
  condition produced at least one evidence record in every trial.
- **Attack matrix:** all 15 test cases show a 100% detection rate (5/5
  trials each) at their expected condition, confirming the Phase 1-4
  single-run results hold up under repetition, not just as one-off passes.
- **Update acceptance accuracy (confusion matrix):** 0 false positives and
  0 false negatives in every condition — no legitimate update was ever
  wrongly rejected, and no attack trial was ever wrongly approved.
- **Storage/link overhead vs. S0:** grows monotonically and sensibly with
  each added assurance mechanism (S1 adds an SBOM; S2 adds provenance on
  top; S3/S4 add attestation; S5 adds authorization evidence). S5's total
  overhead is 5,748 bytes — small in absolute terms, which is itself a
  useful data point: for this artifact size, machine-readable authorization
  evidence at S5 is not the dominant cost of the ladder.
- **Methodological finding worth keeping for the paper (second one of this
  kind):** the first full evaluation run showed S5's storage overhead
  ballooning to ~855,655 bytes — a genuine correctness bug, not noise. The
  cause: `authorization_evidence.py`'s internal `store.for_artifact(hash)`
  lookup aggregated every evidence record ever logged for the stand-in
  stub's (constant) build hash across the *entire* evaluation session, not
  just the current run. Fixed by having `src/pipeline.py` pass an explicit,
  index-sliced `records` list for just the current run. This is the same
  underlying trap as the test case #6 tagging bug above (a lookup keyed by
  something that doesn't uniquely identify "this run" silently pulls in
  cross-run noise) — worth stating in the paper as a recurring hazard of
  building evaluation tooling against a non-varying stand-in artifact, not
  a one-off mistake.
- **Caveats (see PRD.md § 10 and STATUS.md "Claims status"):** timing
  numbers are a sandbox-timing proxy, not hardware/real-mission timing;
  "manual evidence-processing effort" is an evidence-record-count proxy,
  not measured human time; all results are against the stand-in stub
  artifact, not the real cFS build. Not yet citable as an external research
  result — still `PRELIMINARY_INTERNAL_ONLY`.

## Phase 6 results (generalizability, 2026-08-03)

Added a second target stack — NASA JPL's F Prime (F´), Apache 2.0,
pinned to tag `v4.2.2` — architecturally distinct from stack #1 (cFS-
informed): component-driven C++ vs. message-bus C. See
`fprime-app/README.md` for the full rationale and legal basis.

- **What generalized with zero changes:** `condition.py`,
  `evidence_store/`, `signing/`, `sbom/`, `provenance/`,
  `ground_authorization/ground_auth.py`, `uplink_sim/`,
  `onboard_verification/`, `installation/partitions.py`, `attestation/`,
  `rollback/`, `policy/`, `operational_monitoring/`,
  `evidence_store/authorization_evidence.py`. None of these modules care
  what language or architecture produced the binary they're handed — they
  all already worked on `binary_path`/`installed_path` generically.
- **What needed a small, explicit adapter:** `src/build/build.py`
  (source directory + compiler) and `src/health/health_check.py`
  (expected deterministic stdout pattern), both driven by the new
  `src/target_stack.py` registry via a `stack` parameter (default `"cfs"`
  everywhere, so Phase 1-5 behavior is unchanged).
- **Methodological finding worth keeping for the paper (third one of this
  kind):** re-running the pipeline against `fprime` immediately surfaced
  a real bug in `src/ground_authorization/version_ledger.py` — it was a
  single global JSON file tracking "last approved version," so approving
  version 1 for `fprime` right after `cfs`'s test suite had already
  advanced its counter well past version 1 was wrongly flagged as a
  downgrade attempt (test case #9's mechanism), for a stack that had
  never been deployed before. This is the same category of hazard as the
  two Phase 4/5 findings (a piece of state that doesn't distinguish "this
  run/target" from "everything else" silently produces wrong results) —
  fixed by scoping the ledger file per stack. Arguably the more
  interesting result of Phase 6: a second target stack didn't just
  confirm generalization, it found a real correctness gap that a
  single-stack evaluation had no way to expose (nothing about testing
  `cfs` repeatedly could ever reveal that the ledger conflates "target
  identity" with "the whole evaluation session").
- **Results:** running the full evaluation harness
  (`evaluation/experiment.py fprime`, `evaluation/report.py fprime`)
  against `fprime` produced results structurally identical to `cfs`'s
  Phase 5 results: 100% happy-path success/reproducibility across all 6
  conditions, 100% detection across all 15 attack matrix test cases (5/5
  trials each), 0 false positives/negatives in every condition's
  confusion matrix. Storage-overhead figures match almost exactly between
  the two stacks (S5 overhead vs. S0: 5,748 bytes for both) — expected,
  since SBOM/provenance/attestation/authorization-evidence documents are
  JSON structures sized by their own schema, not by the underlying
  binary's language or size. Full numbers in
  `evaluation/results/phase6_report_fprime.md`.
- **Honest scope of this claim (see STATUS.md "Claims status"):** this is
  architectural/tooling generalizability between two stand-in artifacts —
  neither cFS nor F´ has actually been built and run in this project yet
  (both are gated on a Docker-capable machine). It is not yet a claim
  that the assurance ladder has been validated against two real
  flight-software frameworks; it is a claim that the ladder's design
  doesn't depend on which one is underneath.

## 4. Metrics (see PRD.md § success criteria for how these roll up)

- Tampered-artifact detection (rate, per condition, per test case)
- Incomplete-component detection (rate)
- Time to identify affected systems (wall-clock, simulated)
- Update acceptance accuracy (true positive / false positive / false negative)
- Attestation freshness (age of last valid attestation at time of check)
- Recovery success rate
- Time to trusted restoration (baseline definition resolved — PRD.md § 10)
- Manual evidence-processing effort (baseline definition resolved — PRD.md § 10)
- Traceability completeness (fraction of lifecycle stages with linked evidence)
- Storage and link overhead (bytes added per condition vs. S0)
- Reproducibility of the deployed binary (bit-for-bit reproducible build rate)

## 5. Per-stage STRIDE-style notes

To be expanded as each pipeline stage is implemented (Implementation-Plan.md
phases). Placeholder structure per stage:

- **Spoofing:** can an actor impersonate a legitimate source (build runner,
  ground authority, signing identity)?
- **Tampering:** can artifact content be altered without detection at this
  stage?
- **Repudiation:** can an actor deny having authorized/produced something?
- **Information disclosure:** does this stage leak anything that weakens
  later stages (e.g., exposing verification logic, key material)?
- **Denial of service:** can this stage be blocked/delayed to force a
  fallback to a weaker path?
- **Elevation of privilege:** can passing this stage grant more trust than
  it should?

Fill in per-stage detail here as `Technical-Design-Document.md` components
are built — keep this document as the single source of truth for "what are
we testing and why," separate from "how is it built."
