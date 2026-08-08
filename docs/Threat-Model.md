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

## Phase 7 findings (real framework builds, 2026-08-03)

Both `cfs-app/Dockerfile` and `fprime-app/Dockerfile` were run for the
first time on a Docker-capable machine (the authoring sandbox has never
had Docker). Both failed on the first attempt, for reasons worth
recording precisely because they're the kind of thing that's easy to get
subtly wrong when writing infrastructure code without being able to test
it:

- **cFS:** the Dockerfile assumed a bare `cmake .. && make
  mission-install` invocation would work from a `build/` subdirectory.
  It does not — the cFS bundle repo's actual build system is Make-based
  at the top level (`make native_std.prep` / `make native_std.install`,
  which invoke cmake internally with the correct paths). Confirmed
  against the repo's own README rather than guessed a second time.
- **F´:** the Dockerfile assumed `pip install -e .` on a bare framework
  clone would install the tool suite. It does not — the framework repo
  has no `setup.py`/`pyproject.toml` at its root; the tools
  (`fprime-tools`, `fprime-gds`, `fprime-fpp`) are separate PyPI packages
  pinned in the repo's own `requirements.txt`. Fixed by installing from
  that file, then building the framework's own bundled `Ref` reference
  deployment via `fprime-util`.

Both fixes were made by consulting each framework's own authoritative
build documentation (verified via web fetch, not from memory) rather
than iterating blindly a third time. The cFS tag was also corrected from
`v7.0.0` to `v7.0.1` (the actual current official release) while
re-verifying the build instructions — see
`docs/Legal-Data-Sourcing-Notes.md` § 5.

**Both builds succeeded on retry.** `core-cpu1` (cFS) logs a genuine CFE
startup sequence and reaches `CFE_ES_Main entering OPERATIONAL state`;
`Ref` (F´) built clean and correctly rejects an unrecognized CLI flag
with a real usage message. Both are wired into `src/target_stack.py` as
`"cfs-real"` / `"fprime-real"`, smoke-tested successfully through the
full S0-S2 lifecycle (build → provenance → SBOM → signing → ground
authorization → uplink → onboard verification → installation).

**A genuine architectural finding surfaced testing S3+:** both real
binaries are long-running processes. `core-cpu1` reaches `OPERATIONAL`
and then loops forever managing the flight software bus — it has no
built-in "run once and exit" mode. `Ref` is a network server that blocks
waiting for a GDS connection. `health_check.py`'s entire model (run the
binary, expect it to exit quickly, diff its stdout against a fixed
pattern) assumes a short-lived deterministic CLI program — which is true
of the Phase 1-6 stubs by design, but is not true of either real
framework, and arguably *shouldn't* be true of real flight software
(a spacecraft's flight computer is not supposed to run once and exit).
This is not a bug to patch quietly: it's evidence that the stub
artifacts' "run to completion, check stdout" health-check design, while
adequate for testing the assurance-ladder mechanisms in isolation, does
not directly generalize to real flight software's actual execution
model. Rather than let a 5-second timeout silently mislabel a healthy,
genuinely-running process as a failed build (which would have been a
real correctness bug, not just an inconvenience), `run_health_check`
initially raised `NotImplementedError` for both real stacks — a
deliberate fail-loud gate, not a fix — pending a real design decision
(see ISSUES-AND-FIXES-LOG.md ISSUE-003).

**Resolved, same day.** A second, distinct health-check strategy —
`_health_check_persistent_process`, selected per-stack via
`Stack.health_check_mode` in `target_stack.py` — was designed and
implemented: launch the binary, watch its stdout (via a background
reader thread, so a stalled process can't hang the check past the
timeout) for a real, per-stack boot-success marker within
`boot_timeout_seconds`, then terminate it regardless of outcome. The
markers were derived empirically, not guessed: direct testing on the
Docker-capable machine confirmed `core-cpu1` reliably prints
`CFE_ES_Main: CFE_ES_Main entering OPERATIONAL state` within ~50ms of
launch and shuts down cleanly on SIGTERM; `Ref` prints `Hit Ctrl-C to
quit` as its very first line of output — before any network activity —
and, when no GDS is present, retries the connection forever rather than
exiting on its own (confirmed via a clean re-test after an earlier,
ambiguous result turned out to be a shell-piping artifact masking
`timeout`'s real exit status). "Still running" after the check window is
therefore expected, not a failure signal — only whether the marker
genuinely appeared decides pass/fail, preserving the project's
non-fabrication principle for health signals. S3+ conditions
(attestation, health check, rollback) can now be exercised against both
real binaries; `tests/test_phase7_real_builds.py` confirms both the S4
happy path and test case #11 (forced health-check failure → rollback)
against each. This is still individual test runs, not a repeated-trial
statistical evaluation — see STATUS.md "Claims status" for exactly what
that upgrades and what it doesn't.

**Reproducibility claims were NOT extended to the real frameworks by the
work above.** `build.py` does not compile `"cfs-real"`/`"fprime-real"`
from source on every pipeline call — a real framework build takes minutes
(confirmed: ~230s for cFS's install step, ~24s for F´'s final compile
alone), incompatible with a pipeline built around sub-second calls (the
Phase 5/6 evaluation harness makes ~135 calls per stack). Instead, the
one confirmed Docker-built binary is copied for both "independent" hash
comparisons the stub stacks perform for real — meaning `reproducible=True`
for these two stacks, as recorded by the pipeline itself, is a trivial
file-copy-integrity check, not evidence about rebuilding from scratch.
That real question is answered separately, below.

## Phase 7 reproducibility verification (real second builds, 2026-08-03)

To test whether cFS/F´ rebuild bit-identically — independent of the
pipeline's own trivial copy-check — both Dockerfiles were rebuilt a
second time from scratch (`docker build --no-cache`, ~1 hour after the
first build, output kept separate in `build-output-verify/`, gitignored)
and the resulting binaries hash-compared against the first build's
recorded sha256 in each `confirmed-build.json`.

**F´'s `Ref` (v4.2.2): bit-for-bit reproducible.** The second build's
sha256 (`e271e22c37d11d3b27f03b0d033291af727e4d11f8bdffa1c6a8aa83b47f4b9b`)
matched the first build's exactly; `cmp -l` confirmed 0 differing bytes
across the entire binary.

**cFS's `core-cpu1` (v7.0.1): NOT bit-for-bit reproducible — root cause
isolated precisely, not guessed at.** The second build's hash differed.
`cmp -l` showed exactly 22 differing bytes total (out of ~915KB), in two
locations:

1. Two isolated byte offsets (393508, 393510) carry a literal
   build-timestamp string baked into the binary by cFS's own build
   system. A raw `strings` diff (no filtering) showed the actual embedded
   values: `202608031808` (first build) vs `202608031907` (second
   build) — i.e., the two Docker builds' real wall-clock start times,
   ~59 minutes apart, in `YYYYMMDDHHMM` format.
2. A contiguous 20-byte block (offsets 889-908 — exactly the length of a
   SHA-1 digest) is the ELF `.note.gnu.build-id` section. GNU ld computes
   this as a SHA-1 hash over the final linked binary's contents by
   default; since (1) changes those contents, the derived build-id
   necessarily changes too. This is a downstream consequence of the
   embedded timestamp, not a second, independent source of
   non-determinism.

Every other byte in `core-cpu1` — the actual compiled flight-software
logic — was identical across two independent from-scratch builds. The
non-determinism is fully attributable to a build-timestamp string the
cFS build system embeds (likely into a generated version/build-info
source file compiled into the binary), not to compiler flag differences,
link order, or genuine nondeterministic compilation.

**What this licenses claiming, precisely (see STATUS.md "Claims
status" for the full label):** F´'s build process, as pinned and
Dockerized by this project, is independently verified reproducible.
cFS's is not — bit-identical reproducibility for `core-cpu1` would
require either patching out or normalizing the embedded build timestamp
(e.g., via `SOURCE_DATE_EPOCH`-style techniques, if cFS's build system
supports them — not investigated here) before a bit-identical claim
could be made. Neither result generalizes beyond these two specific,
pinned tags and this specific Ubuntu 22.04 Docker build environment; a
different toolchain or OS could introduce other non-determinism this
test wouldn't catch. This is a single comparison (one rebuild each), not
a repeated-trial statistical result.

## Phase 7 data-gathering finding: real health checks require Docker execution on non-Linux hosts (ISSUE-007, 2026-08-03)

Attempting the actual repeated-trial statistical evaluation against the
real binaries (`evaluation/experiment.py cfs-real`), for the paper's
real-stack results section, surfaced a genuine capability gap that no
prior testing had caught: running the harness on the user's own Mac (the
machine that built the real binaries) crashed immediately, tracing back
to `OSError: [Errno 8] Exec format error` when `health_check.py` tried to
launch `core-cpu1` directly via `subprocess.Popen`.

The reason: `core-cpu1` and `Ref` are Linux ELF binaries, compiled inside
an Ubuntu 22.04 Docker container. Docker was only ever this project's
*build* environment — nothing had ever actually executed either binary
outside a container before this run. S0-S2 never surfaced this because
those stages only hash/sign/copy the binary, never run it. Every prior
individual S3+ verification of ISSUE-003's fix had been run in Claude's
own Linux-based sandbox (which shares the same mounted files as the
user's Mac but is a different, Linux machine), where direct execution
happens to work — so the gap was invisible until the harness actually
ran on the real target machine.

A second, more serious bug was found in the same investigation:
`_health_check_persistent_process`'s `except OSError` clause caught
*any* launch failure and recorded it as an unhealthy build — meaning
every real-stack health check on macOS was silently mislabeling a pure
host/environment incompatibility as evidence about the artifact's
health. This is precisely the kind of fabricated signal the
persistent-process design was built to avoid (see ISSUE-003) — an
oversight in that fix's own error handling, not a new category of
problem.

**Fix:** `target_stack.py` now records each real stack's Docker image
name and the binary's path inside that image
(`Stack.docker_image`/`Stack.container_binary_path`).
`health_check.py`'s new `_launch_process()` tries direct execution
first, and only on `ENOEXEC` specifically falls back to `docker run --rm
<image> <container_binary_path>` — re-running the identical, already-
built binary inside the environment it was actually compiled for.
Environments that can execute the binary directly (Linux) never invoke
Docker at all. If there's no Docker fallback configured, or Docker
itself isn't available, this now raises a distinct, loud `RuntimeError`
instead of a misleading per-run "fail" record. See
ISSUES-AND-FIXES-LOG.md ISSUE-007 for the full write-up, including how
this was verified without needing actual Docker or a real cross-
architecture binary (a synthetic file reliably reproduces `ENOEXEC` on
any host).

**End-to-end confirmation, same day:** the user re-ran
`evaluation/experiment.py fprime-real` and it completed successfully —
the Docker fallback genuinely works, and F´'s full repeated-trial
evaluation ran end-to-end against the real `Ref` binary via `docker run`.

## Phase 7 data-gathering finding: cFS's Software Bus fails inside Docker Desktop's default container (ISSUE-008, 2026-08-03)

`cfs-real`'s equivalent run, however, failed at the identical point as
before ISSUE-007's fix — the same `scenario_10` baseline call,
`health_ok=False`. Since `docker run --rm` gives every invocation a
fresh, ephemeral container filesystem, the original "accumulated CDS/
EEPROM runtime-artifact state" hypothesis (from before ISSUE-007 was
even found) could no longer be the explanation. Rather than guess again,
the actual evidence-store record for the failing health check was
inspected directly: 59 lines of genuine `core-cpu1` output, ending in

```
CFE_EVS_TaskInit: Call to CFE_SB_CreatePipe Failed:RC=0xCA000005
CFE_ES_ExitApp: CORE Application CFE_EVS Had an Init Error.
CFE_ES_ResetCFE: PROCESSOR RESET called from CFE_ES_ResetCFE (Commanded).
CFE_PSP: Exiting cFE with PROCESSOR Reset status.
```

Not a timeout, not a slow boot — a genuine initialization failure.
`OS_QueueCreate_Impl`'s own log output named the exact cause: "Your
queue depth may be too large for the OS to handle. Please check the
msg_max parameter located in /proc/sys/fs/mqueue/msg_max." cFE's
Software Bus creates pipes backed by POSIX message queues, and Docker
Desktop's default Linux VM ships a `msg_max` too low for the queue depth
cFE requests — a container-kernel configuration limit, unrelated to
ISSUE-007's exec-format problem, and something Claude's own Linux
sandbox (different kernel defaults, and prior to ISSUE-007 never
actually invoked `docker run` at all) could never have surfaced.

**Fix confirmed before writing any code**, to avoid a second
guess-and-fail cycle: a manual, isolated test —
`docker run --rm --sysctl fs.mqueue.msg_max=1024
verifiable-spacecraft-lifecycle-cfs
/build/cfs-src/build-native_std/exe/cpu1/core-cpu1` — showed `core-cpu1`
reaching `CFE_ES_Main: CFE_ES_Main entering OPERATIONAL state` and
running indefinitely (FLYWHEEL heartbeat messages) until manually
interrupted. Only then was `Stack.docker_sysctls` added to
`target_stack.py` (set for `cfs-real` only; `fprime-real` doesn't hit
this limit) and wired into `health_check.py`'s Docker-fallback command
as `--sysctl key=value` flags — namespaced per-container, no host Docker
Desktop settings changed. See ISSUES-AND-FIXES-LOG.md ISSUE-008 for the
full write-up.

**End-to-end confirmation, same day:** the user re-ran
`evaluation/experiment.py cfs-real` and it completed successfully — see
"Phase 7 real-stack statistical evaluation results" below.

## Phase 7 real-stack statistical evaluation results (2026-08-03)

With ISSUE-007 (Docker fallback) and ISSUE-008 (`fs.mqueue.msg_max`
sysctl) both fixed, the full repeated-trial evaluation harness
(`evaluation/experiment.py`, the same one used for Phase 5/6's
stub-artifact results) ran successfully against **both** real binaries:
5 trials × 6 conditions (happy path) × 15 attack matrix test cases each.

**Results are structurally identical to the stub-artifact results**
(Phase 5 `cfs`, Phase 6 `fprime`): 100% happy-path success and
reproducibility across all 6 conditions for both `cfs-real` and
`fprime-real`; 100% detection across all 15 attack cases for both; 0
false positives/negatives in every condition's confusion matrix for
both. See `evaluation/results/phase6_report_cfs-real.md` and
`evaluation/results/phase6_report_fprime-real.md` for the full tables.

As expected, S3+ timings are meaningfully higher than the stub-artifact
or S0-S2 real-stack numbers — real health checks now launch an actual
container per call (mean happy-path time at S3-S5: ~2.4-2.6s for
`cfs-real`, ~1.8-2.1s for `fprime-real`, versus sub-second for the stub
stacks and for S0-S2 against these same real binaries). This is Docker
container-launch overhead plus the real boot-success-marker wait, not a
detection-latency problem — none of it affects any pass/fail or
detection-rate result, only the timing metric, and is exactly the kind
of real-artifact cost the stub-only results couldn't have shown.

**What this licenses claiming, precisely:** the S0-S5 assurance ladder's
mechanisms and evidence schema, unmodified except for the two
stack-specific adapters (`build.py`, `health_check.py`), now show
structurally identical detection/recovery/reproducibility results across
four stacks: two stand-in artifacts (`cfs`, `fprime`) and two genuine
NASA flight-software frameworks (`cfs-real`, `fprime-real`). This is
still `PRELIMINARY_INTERNAL_ONLY` per STATUS.md "Claims status" — one
evaluation run each, on one machine (the user's Mac for the real stacks),
not independently replicated elsewhere, and the timing metrics remain a
sandbox/container-timing proxy per PRD.md § 10, not real flight-hardware
timing.

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

## Phase 8 ablation study (2026-08-03)

**Motivation.** A 2026-08-03 rejection-risk review (recorded in
`docs/Research-Paper-Outline.md`) identified the single biggest exposure
across all target venues: every one of the 15 attack matrix test cases is
evaluated only at the condition where its responsible mechanism is
active, so "100% detection" could be read as "the test suite always
trips," not as evidence the ladder's structure does isolable work. This
section closes that gap directly.

**Method.** `src/condition.py` gained `custom(base, disable=())`, and
`src/pipeline.py`'s `run()` gained an optional `disable_mechanisms` tuple
(empty by default — every prior call site/test is unaffected, confirmed
via the full 41/41 suite passing unchanged). `evaluation/ablation.py`
uses this to hold a target condition's configuration fixed except for
one mechanism forced off, then re-runs the identical attack scenario used
in `evaluation/experiment.py`.

**Scope, stated explicitly (as of 2026-08-03, superseded 2026-08-05 —
see the update below):** only mechanisms gated directly inside
`pipeline.py`'s own `Condition` object are cleanly ablatable this way —
`onboard_attestation`, `trusted_rollback`, `machine_readable_authorization`.
The S5 prohibited-configuration policy check (test case #8) lives inside
`src/ground_authorization/ground_auth.py`, which derives its own
`Condition` independently via `condition.preset()` and does not see
`pipeline.py`'s ablation — so `signature`/`sbom`/`provenance` and the
policy check specifically are not covered by this pass. That is a
deliberate scope boundary, not an oversight, and a natural follow-up if a
reviewer asks for it.

**Results (5 trials each, both `cfs` and `fprime` stub stacks — identical
on both):**

| Case | Mechanism ablated | Condition | Metric judged | Baseline | Ablated | Effect isolated to mechanism? |
|---|---|---|---|---|---|---|
| #12 (stale attestation) | `onboard_attestation` | S4 | caught | 100% | 0% | Yes |
| #11 (failed health check) | `trusted_rollback` | S4 | **recovered** | 100% | 0% | Yes (caught stays 100% — see below) |
| #15 (false telemetry) | `machine_readable_authorization` | S5 | caught | 100% | 0% | Yes |

Case #11 is the most interesting result and worth stating precisely: with
`trusted_rollback` ablated, the pipeline falls into the S3-equivalent
branch (attestation + health check still run since `onboard_attestation`
stays active), so the failure is still *detected*
(`rejected_at == "post_install_unrecoverable_at_s3"`, `caught` stays 100%
even ablated) — but `recovered` (rollback actually succeeding) drops from
100% to 0%. This is the project's existing S3-vs-S4 narrative
("S3 tells you something is wrong but can't yet do anything about it")
demonstrated with actual re-run data instead of only prose, and it's a
stronger result for the paper than a simple caught/not-caught table would
have been: it shows the ladder degrades gracefully (detection survives
losing one layer down) rather than failing all-or-nothing.

Raw results: `evaluation/results/phase8_ablation_cfs.json` /
`phase8_ablation_fprime.json`.

**Update (2026-08-04): re-run at n=30 against all four stacks, including
both real frameworks.** After fixing ISSUE-009 (a macOS dyld/loadability
regression in the build-reproducibility fix, unrelated to the ablation
logic itself — see ISSUES-AND-FIXES-LOG.md), the user re-ran this study
at the full 30-trial count against `cfs`, `fprime`, and — for the first
time — the real `cfs-real`/`fprime-real` binaries. All four stacks
produced the identical table above (100%/0% at n=30, same
`effect_specifically_attributable_to_mechanism: true` for all three
cases). This means the ablation result — the ladder's mechanisms doing
real, isolable, individually-necessary work, and case #11's specific
"detection survives, recovery doesn't" graceful-degradation finding — now
holds against genuine NASA cFS and F´ flight-software binaries, not just
the stand-in artifacts. Raw results:
`evaluation/results/phase8_ablation_{cfs,fprime,cfs-real,fprime-real}.json`.
Still `PRELIMINARY_INTERNAL_ONLY` — one evaluation run per stack, not
independently replicated elsewhere — see STATUS.md "Claims status."

**Update (2026-08-05): extended to 5 of 6 mechanisms, closing the scope
gap noted above.** `disable_mechanisms` is now threaded through
`ground_authorization.ground_auth.authorize()` and
`onboard_verification.onboard.verify_received_bundle()`, not just
`pipeline.py`'s own gating (both modules' docstrings document the
change). That makes `sbom`, `provenance`, and the S5 policy check
ablatable, and specifically required fixing a subtler issue along the
way: the S5 policy check (test case #8) is checked *twice* — once in
`ground_auth.py`, redundantly again in `onboard.py` (Phase 8 finding #4,
see above) — so ablating `machine_readable_authorization` had to silence
*both* copies, or the untouched redundant check would have caught the
attack anyway and made the ablation look like it changed nothing, for a
reason having nothing to do with the mechanism's actual necessity.

`signature` remains deliberately excluded — not a residual gap, but a
stated design property: it is the one mechanism active at every
condition from S0 through S5 (S0 *is* "signature only," the floor of the
ladder), and neither `ground_auth.py` nor `signing.verify()` gate the
actual check behind `cond.active("signature")` in the first place — it
runs unconditionally, by design. There is no defined condition below S0
to fall back to, so forcing it off would exercise an implementation
quirk, not a claim about the ladder. See `evaluation/ablation.py`'s
module docstring for the full reasoning.

**Results (sandbox verification run, reduced trial counts — 10 trials
for S1/S2 cases, 5 for the two S5 cases, due to a per-command time
limit):**

| Case | Mechanism ablated | Condition | Metric judged | Baseline | Ablated | Effect isolated to mechanism? |
|---|---|---|---|---|---|---|
| #4 (vulnerable dependency in SBOM) | `sbom` | S1 | caught | 100% | 0% | Yes |
| #5 (rogue/unregistered builder) | `provenance` | S2 | caught | 100% | 0% | Yes |
| #12 (stale attestation) | `onboard_attestation` | S4 | caught | 100% | 0% | Yes |
| #11 (failed health check) | `trusted_rollback` | S4 | recovered | 100% | 0% | Yes |
| #15 (false telemetry) | `machine_readable_authorization` | S5 | caught | 100% | 0% | Yes |
| #8 (prohibited configuration) | `machine_readable_authorization` | S5 | caught | 100% | 0% | Yes |

**Confirmed at full scale, 2026-08-05: user re-ran `python3
evaluation/ablation.py` at the full `N_TRIALS = 30` against all four
stacks — `cfs`, `fprime`, and, for the first time for this specific
extension, the real `cfs-real`/`fprime-real` binaries.** All four stacks
produced the identical table below, with every one of the 6 cases
showing `effect_specifically_attributable_to_mechanism: true`:

| Case | Mechanism ablated | Condition | Metric judged | Baseline | Ablated | Effect isolated to mechanism? |
|---|---|---|---|---|---|---|
| #4 (vulnerable dependency in SBOM) | `sbom` | S1 | caught | 100% | 0% | Yes |
| #5 (rogue/unregistered builder) | `provenance` | S2 | caught | 100% | 0% | Yes |
| #12 (stale attestation) | `onboard_attestation` | S4 | caught | 100% | 0% | Yes |
| #11 (failed health check) | `trusted_rollback` | S4 | recovered | 100% | 0% | Yes |
| #15 (false telemetry) | `machine_readable_authorization` | S5 | caught | 100% | 0% | Yes |
| #8 (prohibited configuration) | `machine_readable_authorization` | S5 | caught | 100% | 0% | Yes |

This means the extended ablation result — now 5 of 6 mechanisms, up from
3 — holds at the standard 30-trial count and against genuine NASA cFS
and F´ flight-software binaries, not just the stub artifacts or the
sandbox's reduced-trial verification run above. Still
`PRELIMINARY_INTERNAL_ONLY` — one evaluation run per stack, not
independently replicated elsewhere — see STATUS.md "Claims status." Raw
results: `evaluation/results/phase8_ablation_{cfs,fprime,cfs-real,
fprime-real}.json`.

## Phase 8 evaluation-code correctness tests (2026-08-05)

**Motivation.** Every rate and timing figure in the paper's tables flows
through four small functions in `evaluation/report.py`: `_wilson_ci`,
`_mean_ci`, `_mean_stdev`, and the `summarize_happy_path`/
`summarize_attack_cases`/`build_confusion_matrix` aggregators. None of
that had a dedicated test before this — it was only ever exercised
indirectly by running the full evaluation harness and eyeballing the
output. A careful reviewer could reasonably ask "how do you know the
measurement code itself is correct, independent of the pipeline it
measures?" — this had no better answer than "we looked at it," which
isn't evidence.

**Method.** `tests/test_evaluation_report_correctness.py` (33 tests)
verifies these functions three ways, in increasing order of rigor:

1. `_wilson_ci` is cross-checked against `statsmodels.stats.proportion.
   proportion_confint(method="wilson")` — an independent, third-party
   implementation, not a second copy of the same formula written by the
   same process that wrote the original. Reference values were generated
   with statsmodels 0.14.6 and the exact 97.5th-percentile normal
   quantile (`z = 1.959963984540054`, i.e. `scipy.stats.norm.ppf(0.975)`,
   not the rounded `z = 1.96` `_wilson_ci` defaults to); passing that
   exact `z` into `_wilson_ci` reproduces the statsmodels values to
   1e-9. The rounded default is separately checked to be close (5e-4) —
   confirming the 1.96 convention is a small, well-understood, and
   correctly-applied approximation, not a sign the formula is wrong.
   This test has no runtime dependency on statsmodels/scipy — the
   reference values are hardcoded with the reproduction command in a
   comment.
2. `_mean_ci`/`_mean_stdev` are cross-checked against an independently
   written closed-form computation using `statistics.mean`/`statistics.
   stdev`, not by re-deriving `_mean_ci`'s own internal formula.
3. Boundary/structural properties that must hold regardless of
   implementation detail: the CI must contain the point estimate, must
   narrow as `n` grows, must stay within `[0, 1]` for rates, must not
   collapse to a zero-width interval at a 100%-or-0%-observed rate (the
   exact failure mode a normal-approximation CI has at that boundary —
   see this module's own docstring for why Wilson was chosen), and the
   `n<2` guards for `_mean_ci`/`_mean_stdev` must return a sane point
   value rather than propagating `statistics.StatisticsError`.
4. `summarize_happy_path`/`summarize_attack_cases`/
   `build_confusion_matrix` are exercised against a small, hand-computed
   synthetic `raw` results fixture (not real evaluation output, and
   deliberately not 100%/0% so a bug that always reports the trivial
   rate wouldn't slip through) — checking the aggregation and
   confusion-matrix rounding logic independently of any real trial data.

**Result:** all 33 pass; see `tests/test_evaluation_report_correctness.py`
for the full test list. This directly closes reviewer objection #9 in
`docs/Research-Paper-Outline.md`.

## Phase 8 adaptive-attacker scenarios (2026-08-03)

**Motivation.** The same rejection-risk review flagged a second, related
gap: every original test case injects exactly one attack vector, never
two combined — leaving untested whether an attacker who tries several
techniques at once could slip past a check that stops any one of them in
isolation (e.g., hoping a caught violation is logged but doesn't actually
halt the pipeline before a second vector matters downstream).

**Method.** `evaluation/adaptive_attacks.py` combines two existing attack
vectors in the same `pipeline.run()` call and checks not just whether the
combined attack was caught, but whether the pipeline demonstrably halted
before the second vector was ever exercised (via `PipelineResult` fields
that stay at their `None` default only if that stage was never reached
— e.g. `onboard_verified is None` means `transmit()`/onboard verification
never ran at all, not that it ran and happened to pass).

**Scenarios and results (5 trials each, both `cfs` and `fprime` — identical):**

| Scenario | Condition | Combined vectors | Caught | Halted before 2nd vector exercised? |
|---|---|---|---|---|
| A | S2 | rogue/unregistered builder_id (#5) + in-transit tamper (#6) | 100% | 100% — `onboard_verified` stayed `None`; `transmit()` was never called |
| B | S4 | interrupted installation (#10) + stale attestation (#12) | 100% | 100% — `attestation_path`/`health_ok` stayed `None`; attestation was never generated |

Both confirm the pipeline is fail-closed at the *first* violated layer
rather than merely "eventually catches everything somehow" — a
meaningfully stronger property than the original 15 isolated-vector
cases demonstrate on their own, and a direct answer to the
"detection-by-construction" reviewer objection.

**Scope, stated explicitly:** these two scenarios test whether earlier
detection *halts* the pipeline before a second, independent vector is
exercised — they do not yet test a genuinely time-adaptive attacker
(e.g. one that behaves correctly through a bounded health-check window
and only misbehaves afterward, exploiting the fact that health checks
here are one-shot at install time, not continuous). That "sleeper"
adaptive-attacker class would require new runtime behavior in the
artifacts themselves (not just new pipeline.run() kwargs) and is
explicitly out of scope for this pass — a real limitation worth stating
in the paper rather than silently overclaiming "adaptive attacker" to
mean more than what was actually tested.

Raw results: `evaluation/results/phase8_adaptive_cfs.json` /
`phase8_adaptive_fprime.json`.

**Update (2026-08-04): re-run at n=30 against all four stacks, including
both real frameworks.** Same re-run as the ablation study above, same
result: both combined-vector scenarios (A: rogue builder + transit
tamper; B: interrupted install + stale attestation) scored 100%
caught/100% halted-before-second-vector at n=30 against `cfs`, `fprime`,
`cfs-real`, and `fprime-real` alike. The fail-closed-at-first-violation
property holds against the real binaries, not just the stand-ins. Raw
results:
`evaluation/results/phase8_adaptive_{cfs,fprime,cfs-real,fprime-real}.json`.
Still `PRELIMINARY_INTERNAL_ONLY` — same caveat as above — and the
stated "sleeper attacker" scope limitation still applies regardless of
which stack is used.

## Phase 8 independent (blind, AI) red-team review (2026-08-04)

**Motivation.** Reviewer objection 7 in Research-Paper-Outline.md § 4
("same team designed the threat model, the mitigations, and the fixes for
the mitigations' own credibility gap") cannot be resolved by more
self-designed work. As a partial, honestly-caveated mitigation, a fresh
agent instance with no prior context on this project was given only 20
source files under `src/` (the mechanism implementations) and tasked with
independently finding attack vectors the existing 15 test cases + ablation
+ adaptive scenarios do not cover.

**Real limitation of the "blind" framing, stated plainly rather than
glossed over:** this project's source files themselves contain inline
comments referencing specific `test case #N` numbers throughout (a
consequence of this project's own in-code documentation habit), so a
reviewer reading `src/` is not blind to which attacks are already known —
only to the specifics of how they're tested and what's been checked
beyond them. The agent was instructed to exclude anything already flagged
as covered by a comment and focus on gaps beyond that. This makes the
review genuinely independent in *design origin* (a fresh context, not the
same reasoning chain that built the ladder) but not blind in the strict
"never saw the answer key" sense. State this precisely if citing this
review in the paper — don't oversell it as a naive/uninformed attacker
simulation.

**Tool used, confirmed with the author 2026-08-07 (not identified at the
time this section was first written):** this pass used Claude — the same
underlying AI system that performed the majority of this project's
design and implementation work, run in a separate session with no access
to prior project context. This makes it independent at the level of
context but not of AI system, unlike the second, third, and fourth passes
below, which each used a genuinely different AI system. State this
distinction precisely in the paper's AI-use disclosure and Limitations
sections rather than grouping all four passes under a single "distinct
systems" framing.

**Findings, ranked by the reviewer as most severe/concrete first. All
seven were independently spot-verified against the actual source in this
session (not just trusted from the sub-agent's report) — every one holds
up:**

1. **Ground-truth state files (version ledger, partition state) have no
   integrity protection and can be edited directly, bypassing every
   mechanism built on top of them.** *Verified.* `version_ledger.py`
   reads/writes a bare, unsigned JSON file
   (`work/version_ledger.<stack>.json`) with plain `json.load`/`json.dump`
   — no HMAC, no signature, no append-only chain. Directly editing
   `last_approved_version` back to 0 defeats downgrade protection (test
   case #9's mechanism) with no signature or provenance forgery required.
   `partitions.py`'s state file has the same property for rollback
   integrity (test case #14's mechanism). This is a real, previously
   unstated scope gap: every mechanism assumes its own persisted
   side-state is trustworthy, and nothing in the codebase makes that
   state tamper-evident. Worth a sentence in Limitations regardless of
   whether it's fixed — the threat model in § 2 above implicitly assumes
   ground-segment infrastructure integrity that isn't itself defended.
2. **Signing-key revocation fails open on a missing/deleted
   `revoked_keys.txt`.** *Verified.* `signing.py`'s `is_revoked()` returns
   `False` (not revoked) whenever the file doesn't exist —
   `if not REVOKED_KEYS_PATH.exists(): return False`. The file itself is
   unsigned plain text. Test case #7 exercises "fingerprint is in the
   list"; it does not exercise "the list itself was deleted or emptied,"
   which un-revokes every key with a single unprivileged filesystem
   write and leaves no cryptographic trace. Classic fail-open default on
   a security-critical control file.
3. **The `version` argument used for downgrade protection is never bound
   to the provenance record it travels alongside.** *Verified.*
   `ground_auth.py::authorize()` calls `verify_provenance(...)` and
   discards its third return value (`_`), then separately calls
   `version_ledger.check_and_advance(version, ...)` using the bare
   `version` function argument — never cross-checked against whatever
   version `generate_provenance()` embedded in the provenance document
   itself. This is the mirror image of test case #9 (a low version
   sneaking past the ledger): an inflated version number supplied to
   `authorize()`/`pipeline.run()` independently of the artifact's actual
   provenance could poison the shared ledger and permanently lock out
   future *legitimate* lower/correct version numbers — a DoS vector
   distinct from anything in the current matrix, and requiring no
   signature or provenance forgery at all.
4. **The onboard-side prohibited-configuration check is a permanent dead
   stub, gated by a literal string comparison rather than the mechanism
   flag.** *Verified.* `onboard.py::check_prohibited_configuration()`
   unconditionally `return True`s, with a comment saying it's a Phase 1
   placeholder "until Phase 4 implements real policy evaluation" — Phase
   4 built real policy evaluation (`policy.check_configuration`) but only
   wired it into ground-side `authorize()`, never back into this stub.
   The onboard side has no independent ability to reject a prohibited
   configuration if ground authorization is bypassed or fed different
   data. Additionally, the gate that even calls this useless stub is
   `if condition_name == "S5"` — a literal string match against the
   condition's *name*, not `cond.active("machine_readable_authorization")`
   — so a custom condition built via `condition.custom()` with that
   mechanism active under a different name silently skips the check
   entirely, independent of the stub itself being a no-op. This is a
   real, double-layered gap: even fixing the stub wouldn't matter for any
   condition object whose `.name` isn't literally the string `"S5"`.
5. **The S5 authorization-evidence document is unsigned and keyed only by
   artifact hash, so re-runs against the same (constant, stand-in)
   artifact silently overwrite prior evidence at that path.** *Verified.*
   `authorization_evidence.py::generate_authorization_evidence()` writes
   plain `json.dump` output to
   `work/authorization_evidence/{artifact_hash}.authorization-evidence.json`
   with no signature over the document and no run ID or timestamp in the
   filename. Since the stand-in artifact's hash is identical across every
   run (documented in the module's own docstring, for an unrelated
   reason — the Phase 5 cross-run-aggregation bug), every re-run silently
   clobbers whatever authorization-evidence document existed at that
   path, including one that recorded a detected failure. The evidence
   log itself (`evidence_log.jsonl`) is genuinely append-only and
   preserves history, but the actual deliverable meant to be handed to
   an external verifier is neither immutable nor signed.
6. **No revocation mechanism exists for the attestation key, unlike the
   signing key.** *Verified.* `attestation.py` has no
   `is_revoked()`/`REVOKED_KEYS_PATH` equivalent for
   `ATTESTATION_PRIVATE_KEY_PATH` — `signing.py`'s revocation check has
   no counterpart here. If the attestation key were ever known or
   suspected compromised, there is no operational mechanism in this
   codebase to invalidate it short of manually swapping key files.
7. **Operational-monitoring mismatches (test cases #13/#15) are logged
   but never enforced.** *Verified.* In `pipeline.py`'s S5 branch (lines
   ~257-277), `monitoring.reconcile_inventory()` and
   `monitoring.check_telemetry()` compute pass/fail and store it on
   `PipelineResult.inventory_reconciled`/`telemetry_consistent`, but
   `run()` never branches on either result — no rejection, no
   re-authorization freeze, no alert. A detected inventory disagreement
   or forged-telemetry mismatch produces an evidence-log entry and
   nothing else; detection here is purely retrospective/auditable, not
   preventive, and nothing stops the same mismatch recurring indefinitely
   on every subsequent run.

**What this licenses claiming, precisely:** an independently-instantiated
review (not the same reasoning chain that designed the ladder, though not
blind to which attacks were already known, per the caveat above) found
seven concrete gaps, all independently confirmed against the source in
this session — unprotected ground-truth state files, fail-open key
revocation, an unbound version/provenance pairing, a dead onboard
policy-check stub with a brittle string-match gate, an unsigned/
overwritable authorization-evidence document, no attestation-key
revocation path, and unenforced operational-monitoring mismatches — none
of which the original 15 test cases, ablation study, or adaptive
scenarios cover. This is genuine evidence the "same team" objection isn't
fully answered by more self-designed rigor alone: every one of these
gaps sits in the pipeline's own out-of-band state or in an
already-known-but-never-closed placeholder, exactly the kind of thing a
differently-motivated reader finds and an author's own mental model
routinely skips past. It is still not equivalent to a human security
domain expert's review — no claim is made here about completeness, only
that these seven are real and confirmed.

**Update (2026-08-04): all seven findings fixed the same day.** See
ISSUES-AND-FIXES-LOG.md ISSUE-011 through ISSUE-017 for the full
per-finding writeup. Summary:

1. Ground-truth state files (version ledger, partition state) are now
   HMAC-protected via new `src/state_integrity.py`; tampered or
   deleted-after-protection state now fails closed (denies the
   authorization/installation) rather than being silently trusted.
2. Signing-key revocation now fails **closed**: the revocation list is
   integrity-protected from the moment a keypair exists, and a
   tampered/deleted list is treated as "every key revoked," not "nothing
   revoked."
3. Ground authorization now cross-checks the `version` argument against
   the version embedded in the provenance record, rejecting a mismatch
   before ever consulting the ledger.
4. The onboard prohibited-configuration check now delegates to the same
   real policy evaluation ground authorization uses, gated by
   `cond.active("machine_readable_authorization")` instead of a literal
   string comparison.
5. The S5 authorization-evidence document is now signed (dedicated
   Ed25519 keypair) and filenamed per-run, so it can never be silently
   overwritten again; a new `verify_authorization_evidence()` lets an
   external verifier confirm it.
6. The attestation key now has the same revocation mechanism the signing
   key has, via the same integrity-protected, fail-closed pattern.
7. A detected operational-monitoring mismatch now freezes the affected
   stack's ledger (denying every subsequent authorization) until an
   operator explicitly clears it — real enforcement, not just a log
   entry.

All seven fixes were verified via a new dedicated test file
(`tests/test_phase8_redteam_fixes.py`, 19 tests, one or more per finding,
each demonstrating the original gap is closed and that the fix fails
*closed* rather than merely patching the one reported scenario) plus a
full re-run of the existing 47-test regression suite, the 15-case attack
matrix, the Phase 8 ablation study, and the Phase 8 adaptive-attacker
scenarios against both `cfs` and `fprime` — every existing result is
unchanged (100%/0% throughout, 100%/100% for the adaptive scenarios),
confirming the fixes close real gaps without altering any of the
project's existing, already-cited behavior. Also confirmed against real
`cfs-real`/`fprime-real` via the existing `tests/test_phase7_real_builds.py`
(6/6 passing). Two real, latent instances of finding #2's exact
anti-pattern (a raw file write bypassing the new integrity sidecar) were
also found and fixed while verifying, in `tests/test_phase1_pipeline.py`
and `evaluation/experiment.py`'s `scenario_07` — see ISSUE-012.

This closes Research-Paper-Outline.md § 4 item 7's remaining open
question of *whether* to fix these before the paper: they are fixed, and
the honest framing for the paper is now "an independent review found N
real gaps, and they were fixed and re-verified the same day," not merely
"an independent review found gaps."

## Phase 8 second independent (blind, AI) red-team review (2026-08-05)

**Tool used, confirmed with the author 2026-08-07:** OpenAI's models —
the first pass to use an AI system genuinely distinct from the one that
performed the majority of this project's design and implementation work.

**Motivation.** After the first red-team review (above) and its fixes,
a follow-up discussion surfaced a previously-undocumented meta-objection:
the fix/verification work for the first review's own findings, plus the
reviewer-objection-5/9 work done the same session (extending the
ablation study, adding evaluation-code correctness tests), was itself
designed by the same process (this author + Claude) being scrutinized —
the exact recursion objection 7 exists to name. Separately, the first
review's file coverage was narrower than the codebase even at the time
it ran: it saw only 20 files under `src/`, explicitly excluding
`build.py`, `health_check.py`, `uplink_sim/uplink.py`, and all of
`evaluation/`.

**Method.** A second fresh agent instance with no prior context was
given all 27 `.py` files under `src/` and `evaluation/` this time —
closing the file-coverage gap — and tasked with three things in order:
(1) attack vectors/design gaps not covered by existing mechanisms/tests,
with explicit emphasis on the files the first pass never saw; (2)
construction problems in the evaluation harness itself (could a metric
be guaranteed to show detection succeeding regardless of whether the
underlying mechanism works — the exact "vacuous test" pattern reviewer
objection 9 exists to guard against); (3) correctness/security issues in
every file changed for the objection-5/9 fixes and the first red-team
fixes, none of which had ever had independent review. Same caveat as the
first pass, stated again rather than assumed still true: source comments
name specific test-case numbers throughout, so this was not blind to
*which* attacks were already known, only to what's uncovered beyond
them.

**Findings.** 12 findings, all independently re-verified against the
actual source (not trusted from the sub-agent's report alone) before any
fix was written:

1. **SBOM was never bound to the artifact it describes.**
   `ground_auth.authorize()` never checked the SBOM's declared hash
   against the binary being authorized — only provenance had this
   binding check. Masked in the normal flow (SBOM is always generated
   from the same binary it ships with) but a real gap in `authorize()`
   as a general function.
2. **The Docker health-check fallback ran the wrong binary.** On any
   non-Linux host (including the machine that produced this project's
   own published real-cFS/F´ results), the fallback executed the
   image's baked-in binary, never the actual installed artifact — the
   module's own docstring claim ("re-runs the identical binary") was
   false as implemented. Checked whether this corrupted any of the 15
   published attack-matrix results: it did not (none rely on this
   specific check to catch a tampered binary), but the underlying
   implementation didn't match its own documented behavior on hardware
   this project already cited results from.
3. **Onboard verification had no independent downgrade defense**,
   the sibling gap to finding #4 from the first review (S5 policy) —
   fixed there, never generalized to downgrade protection.
4. **Attestation freshness had no floor** — a future-dated quote never
   expires (`age_seconds` goes negative and stays below the staleness
   threshold indefinitely).
5. **Persistent-process health check has no tie to artifact identity**
   — a trivial replacement binary that prints the boot-success marker
   string would pass. Documented as a known limitation, not fixed this
   pass (see ISSUE-022 for the full reasoning).
6. **Provenance bound to git HEAD only**, never checked for an
   uncommitted working tree.
7. **`evaluation/experiment.py::scenario_13` never exercised the real
   pipeline** — called the mismatch-detector directly with hardcoded
   constants, guaranteeing "100% detection" by construction. Exactly the
   vacuous-test pattern the review was asked to hunt for, found in this
   project's own evaluation code.
8. **`report.py::summarize_happy_path` aggregated two field groups from
   trial 0 only**, not across all trials, unlike every other metric in
   the same function.
9. **Ablation baseline-invariant asserts were inconsistently guarded**
   across three of the six ablation cases — latent fragility, no
   observed incorrect result.
10. **The prohibited-configuration policy matcher was bypassable by type
    coercion** — `{"debug_mode": "true"}` (string) evaded the same rule
    `{"debug_mode": True}` (bool) catches.
11. **No automatic key-rotation path after signing-key or
    attestation-key revocation** — the system kept silently producing
    new material with an already-revoked key indefinitely.
12. **Uplink tamper injection always corrupted the same byte offset** —
    a coverage-narrowness finding, not a detection gap (whole-artifact
    signature verification is location-agnostic).

**Fixes.** 11 of 12 were fixed (finding #5 documented as a known
limitation instead — see ISSUE-022 for why a real fix is a bigger design
change than this pass's scope). Notably, finding #11's most natural fix
(refuse to sign/attest with a revoked key) was tried and reverted: it
broke the existing, correct test case #7 design, which deliberately
models an operator/system that hasn't rotated yet, with the defense
correctly living in downstream verification. The actual fix adds
visibility (a distinct evidence record) without changing that control
flow — a real example of a red-team-suggested fix needing to be
re-thought rather than applied literally. Full per-finding writeup:
`ISSUES-AND-FIXES-LOG.md` ISSUE-018 through ISSUE-029.

Verified via a new dedicated test file (`tests/test_second_redteam_fixes.py`,
31 tests) plus a full re-run of the existing regression suite (66
pre-existing tests across phases 1-4, 6, 7, the first red-team fixes, the
ablation extension, and the evaluation-code correctness tests) — zero
drift in any prior result. One genuine regression was caught and fixed
during this re-run: the new onboard-side downgrade check (finding #3)
reads partition state during onboard verification, which runs before
`pipeline.py`'s own trusted_rollback try/except block — an uncaught
`StateIntegrityError` there would have crashed `pipeline.run()` outright
instead of returning a `PipelineResult`, breaking
`test_phase8_redteam_fixes.py`'s existing tampered-partition-state test.
Fixed by catching the error inside the new check itself and fail-closed
denying, consistent with the fail-closed pattern used everywhere else
this project checks integrity-protected state; the pre-existing test was
updated to accept either of the two (now both genuinely fail-closed)
detection points, since the fix makes detection happen earlier, not
weaker. The re-extended ablation study (5/6 mechanisms) was re-confirmed
clean at n=1 after all 12 fixes landed.

This is the strongest available answer to objection 7's recursion short
of a genuinely independent human audit: not just "a fresh reviewer found
gaps" but "a fresh reviewer scoped specifically at what the previous
review missed, including the fixes and extensions built the same
session, found 12 more real gaps, and 11 were fixed and re-verified the
same day." State this precisely in the paper, including the one
documented-not-fixed exception and the one fix that had to be reverted
and redesigned — both are more informative than a clean "all fixed" would
be, and demonstrate the fix-verification loop catching its own mistake
(the StateIntegrityError regression) working as intended.

## Phase 8 third independent (blind, AI) red-team review (2026-08-06)

**Tool used, confirmed with the author 2026-08-07:** Zhipu AI's GLM.

**Motivation.** With the human-colleague review still pending on the
colleague's own schedule, a third independent pass was run in the
interim using a different model/tool than the first two passes — a
genuinely different reviewer, not a third run of the same one. Given the
same blind-review brief (don't read `docs/Threat-Model.md` or
`ISSUES-AND-FIXES-LOG.md` until after independent testing; focus on the
least-reviewed newest files; build a reproducible harness for anything
found rather than asserting from a read-through) as the second pass.

**A process note worth recording honestly.** The reviewer's first
attempt ran against the wrong local repository — a similarly-named,
unrelated project of the author's — and, to its credit, caught the
structural mismatch itself (missing expected paths, wrong file names)
and stopped rather than forcing its findings to fit. The author supplied
the correct path and the review was re-run cleanly from scratch. Recorded
here rather than omitted, consistent with this project's practice of
logging process failures alongside code findings — this one happened to
be human/operator error (a mistaken path), not a flaw in the review
methodology itself, and the reviewer's own self-check is exactly the kind
of caution the fail-closed design philosophy elsewhere in this project
tries to instill in code.

**Method.** Standard baseline first (full `pytest` run, `ablation.py`),
then a full read of the same ten target files as the second pass, then
targeted exploit hypotheses built as reproducible harnesses, then —
only after its own testing was complete — the answer-key docs, to
classify each candidate as novel, already-known/fixed, or predicted-by-
the-threat-model-but-never-implemented.

**Findings.** One novel, end-to-end-confirmed finding; two candidates
that reduced to already-documented items on cross-check; one
already-documented-but-deliberately-unfixed limitation independently
re-confirmed still live:

1. **Novel — S5 policy deny-rule key matched case-sensitively.**
   `{"DEBUG_MODE": True}` meant the exact same thing as the only
   prohibited-configuration rule but never matched it, because the
   lookup was exact-case. Proven end-to-end through a real
   `pipeline.run()` call: the release was confirmed onboard and the
   signed authorization-evidence document itself recorded
   `overall_result: "pass"` — the report-says-PASS-without-a-genuine-
   check failure mode this project's entire methodology exists to catch.
   Correctly identified as sitting on a different axis than ISSUE-027
   (second pass, finding #10), which fixed how *values* are compared,
   never how *keys* are looked up. See ISSUES-AND-FIXES-LOG.md ISSUE-030
   for the full writeup and fix. This is the strongest single piece of
   evidence yet that the independent-review process is doing real work
   rather than rubber-stamping: a third reviewer, on the actual
   repository, found a real end-to-end bypass that two prior review
   passes and this project's own 130+ test suite had all missed.

2. **Reduces to known — SBOM binding skipped when `binary_path=None`.**
   Independently rediscovered the same optional-parameter shape already
   documented as ISSUE-018 (first red-team pass): the binding check only
   runs "when provided," and `ground_auth.authorize()` always provides
   it, so this stays a latent, not pipeline-reachable, gap. Not logged
   as a new issue.

3. **Reduces to known/different-axis — attestation quote has no
   verifier-supplied nonce.** A captured valid quote is theoretically
   replayable within the 300-second freshness window without a fresh
   boot; `measured_hash` binding limits this to the same binary, and the
   pipeline always regenerates the quote each run, so it isn't a clean
   end-to-end pipeline bypass the way finding 1 is. Correctly identified
   as a different axis than ISSUE-021 (second pass, finding #4), which
   only fixed the future-dated-timestamp floor. Recorded here as an
   acknowledged design limitation rather than a logged issue, since no
   concrete pipeline-reachable exploit was demonstrated for it (unlike
   finding 1).

4. **Independently re-confirmed still live — ISSUE-022's forgeable
   boot-success marker.** Rather than trusting the issues log's own
   "documented, not fixed" claim, the reviewer built a fresh harness: a
   binary that does nothing but print the expected marker string passes
   the persistent-process health check. Confirms ISSUE-022's status is
   accurate and the gap has not silently regressed into something worse
   (or been fixed without the log being updated).

**Fix and verification.** ISSUE-030's fix, regression tests, and an
independent end-to-end re-confirmation (the same `{"DEBUG_MODE": True}`
config is now rejected at `ground_authorization` and no authorization-
evidence document is written at all) are recorded in
ISSUES-AND-FIXES-LOG.md. Full per-file regression run across every test
file except the environment-dependent real-Docker-binary tests in
`test_phase7_real_builds.py` (unaffected, unchanged) — no drift.

**What this adds to the paper's answer to objection 7.** The second
pass's writeup already states that a fresh reviewer scoped at a prior
review's gaps is the strongest available answer short of a genuinely
independent human audit. This third pass adds a materially different
kind of evidence: a different model/tool, not just a fresh context
window of the same one, finding a real bypass that survived two AI
reviews and the full test suite. That is closer to genuine review
diversity than repeating the same reviewer, though it is still AI, not
the human colleague review that remains the honest gold-standard
comparison and is still pending separately.

## Phase 8 fourth independent (blind, AI) red-team review (2026-08-06)

**Tool used, confirmed with the author 2026-08-07:** DeepSeek.

**Motivation.** With ISSUE-030 (third pass) fixed, committed, and pushed,
a fourth pass — a different model/tool than all three prior ones — was
run specifically to check whether that fix actually holds under further
adversarial testing, not just against its own regression tests, and to
look for anything new. This directly tests the fix-verify loop's own
honesty: a fix whose only evidence of correctness is its own
author-written tests is exactly the "self-review reviewing itself"
concern objection 7 names.

**Process notes worth recording honestly, same practice as prior
passes.** (1) The reviewer correctly re-verified the exact repo path and
required structure before starting — the safeguard added after the third
pass's accidental wrong-repo run worked. (2) It hit a genuine
infrastructure outage in its own tool-approval backend for the entire
session (a 404 on every escalated/networked command) and handled it
honestly: rather than fabricating a baseline or silently skipping it, it
found a pre-installed Python interpreter with the needed dependencies
already available and used that instead, then explicitly flagged the
outage and asked before assuming it was resolved. This is the kind of
failure-handling this project wants to see modeled, and is recorded here
for the same reason the RevokedKeyError reversion and the
StateIntegrityError regression were recorded in earlier sections: it's
evidence the process is not glossing over its own friction.

**Findings — five re-defeats of ISSUE-030's fix, plus two more
findings, all independently re-verified against the real source before
any fix was written:**

1. **P4-K/P4-C/P4-N/P4-U/P4-V — ISSUE-030's fix was too narrow.** The
   third pass fixed the literal reported case-variant (`.lower()` on a
   single collapsed dict); this pass showed that missed whitespace,
   Unicode width variants, key collisions (fail-open, not fail-closed),
   non-string keys (crashed rather than denied), and container-wrapped
   values. Each was proven end-to-end: `check_configuration` returned
   `(True, None)` with an evidence record claiming `result: "pass"` for
   a config meaning exactly the same thing as the one prohibited
   pattern. See ISSUES-AND-FIXES-LOG.md ISSUE-031 for the full writeup
   and fix (a proper rewrite this time — NFKC-normalize-and-casefold key
   comparison checked against *every* colliding key rather than a single
   collapsed dict, and a Python-truthiness fallback for container
   values, rather than another narrow patch).

2. **P4-T — `confirm_active()` had no re-hash immediately before
   confirming.** Real code pattern (verify-then-trust with no re-check at
   the trust boundary), but reachability is precise and limited: it
   needs an adversary capability none of this project's six threat
   actors (§ 2 above) grant — independent write access to the onboard
   partition slot's bytes, timed to the exact window between health-
   check and confirm. Same category as ISSUE-018 (SBOM binding "masked
   in the normal flow"). Fixed anyway as cheap defense-in-depth,
   mirroring the re-hash `revert_to_other()` already does for the
   recovery slot — see ISSUE-031.

3. **P4-I — onboard's config check is not independent of ground's on
   the config axis.** Both delegate to the same `policy.check_configuration`,
   so any matcher bypass defeats both simultaneously. Correctly
   distinguished from what the onboard check *was* added to defend
   against (ground/spacecraft desync on which config was actually
   deployed) — that defense is real and unaffected; the "two independent
   checks" framing just needs the caveat that they share one
   implementation. Documented, no separate fix (fixing the shared
   matcher closes both).

4. **P4-L — `condition.yaml` is unprotected.** Correctly self-downgraded
   by the reviewer: no production path (`pipeline.run()`, `authorize()`,
   `verify_received_bundle()`) ever reads it — all build `Condition` via
   `preset()`/`custom()` from a hardcoded string. A latent documentation
   anomaly, not an exploitable gap.

**What this adds to the paper's answer to objection 7.** This is the
sharpest evidence yet that the iterative fix-verify process is doing real
work rather than converging on a false sense of completeness: a fix
written and verified by one AI pass, with its own passing regression
tests, was defeated on five separate axes by a different AI pass
specifically tasked with not trusting it. The honest framing for the
paper: this also means the *third* pass's fix should not be cited as
"resolved" without this fourth pass's correction — the real, citable
claim is the fix as it stands *after* ISSUE-031, verified by both the
narrower ISSUE-030 regression tests and the five new adversarial ones,
plus the reachability discipline that correctly separated the two
policy-axis findings (reachable, fixed) from the confirm-time finding
(not reachable under the stated threat model, fixed anyway) from the
two documentation-only observations (correctly not "fixed" at all,
because there was nothing exploitable to fix).

## Phase 8 real-baseline comparison: python-tuf (2026-08-04)

**Motivation.** Reviewer objection 6 in Research-Paper-Outline.md § 4
("where's the comparison against an actual SLSA/in-toto/TUF pipeline?")
cannot be answered by argument alone — the paper's central claim (that
terrestrial supply-chain frameworks don't address spacecraft-specific
constraints) needed to be measured, not asserted.

**Method.** Installed the real, unmodified upstream `python-tuf` library
(`pip install tuf`, v7.0.0 — not a reimplementation) and built a minimal,
correct TUF repository (one key per top-level role, no delegation, via
TUF's own low-level Metadata API, following the same pattern as
python-tuf's own `examples/manual_repo/basic_repo.py`) plus a real
`tuf.ngclient.Updater` client, in `evaluation/baselines/tuf_baseline.py`.
No live HTTP server is used — a `FetcherInterface` implementation reads
`file://` URLs directly from disk, keeping this baseline in-process and
deterministic like every other stage in this project's own pipeline; this
tests TUF's own cryptographic/protocol guarantees, not this harness's
networking code.

**Scope, decided honestly before running anything:** of the 15 attack
matrix test cases, only 3 have a plausible TUF-native detection
mechanism at all — #6 (modified update in transit → TUF's core
target-hash/length integrity check), #7 (revoked signing key → TUF's
root-key-rotation/revocation mechanism), and #9 (downgrade attempt → TUF's
version-monotonicity/rollback protection, enforced via the client's
persisted local trust store). These three are not incidental — they are
TUF's actual, textbook security guarantees. The other 12 test cases were
**not run** as scenarios, and are recorded as N/A with a stated
architectural reason each (see `NOT_APPLICABLE` in the module) rather
than silently omitted: build provenance (#2), SBOM (#3),
known-vulnerability scanning (#4), authorized-builder identity (#5),
policy/configuration evaluation (#8), installation/A-B partition
management (#10), runtime health checks (#11), onboard attestation (#12
— TUF's *metadata* expiration is a related-but-distinct freshness
guarantee, explicitly not scored as equivalent), ground/spacecraft
inventory reconciliation (#13), rollback/recovery-image integrity (#14),
and operational-telemetry consistency (#15) all have no corresponding
concept anywhere in TUF's specification. Test case #1 shares its
detection mechanism with #6 and was not double-counted as a separate win.

**Results (n=30, deterministic — repetition here confirms no flakiness in
the test harness itself, not a probabilistic detection rate):**

| Case | Mechanism | TUF detection rate |
|---|---|---|
| #6 (modified update in transit) | target hash/length verification | 30/30 (100%) — `DownloadLengthMismatchError` |
| #7 (revoked signing key) | root key rotation/revocation | 30/30 (100%) — `UnsignedMetadataError` ("targets was signed by 0/1 keys") |
| #9 (downgrade attempt) | version-monotonicity check | 30/30 (100%) — `BadVersionNumberError` |
| #1, #2, #3, #4, #5, #8, #10, #11, #12, #13, #14, #15 | — | N/A, no TUF mechanism exists |

Raw results: `evaluation/results/phase8_tuf_baseline.json`.

**What this licenses claiming, precisely:** a real, working, unmodified
TUF deployment correctly and reliably catches exactly the 3 attack types
its specification is designed around, and has no mechanism at all for
the other 12 — 9 of which are load-bearing parts of this project's own
S1-S5 ladder (SBOM, provenance, builder authorization, policy,
attestation, rollback, inventory reconciliation, telemetry consistency,
plus installation itself). This directly substantiates, with a real
control-group measurement rather than an assertion, the paper's central
claim that terrestrial software supply-chain frameworks address a
narrower problem than spacecraft lifecycle assurance requires — TUF is
not a weak or poorly-implemented tool here; it does exactly what it's
supposed to do, and what it's supposed to do is a proper subset of what
this project's S0-S5 ladder covers. Still worth stating precisely: this
is one baseline tool (chosen as the closest conceptual match to
`ground_authorization`/`onboard_verification`), one minimal (if correct)
repository configuration, and does not speak to SLSA or in-toto
specifically, which target adjacent but distinct parts of the problem
(build provenance, primarily) and would need their own, separate
baseline runs to make the equivalent claim about them.
