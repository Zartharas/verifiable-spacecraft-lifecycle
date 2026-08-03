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

## 4. Metrics (see PRD.md § success criteria for how these roll up)

- Tampered-artifact detection (rate, per condition, per test case)
- Incomplete-component detection (rate)
- Time to identify affected systems (wall-clock, simulated)
- Update acceptance accuracy (true positive / false positive / false negative)
- Attestation freshness (age of last valid attestation at time of check)
- Recovery success rate
- Time to trusted restoration (needs baseline definition — open question, see PRD.md § 9)
- Manual evidence-processing effort (needs baseline definition — open question)
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
