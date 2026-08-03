# Product/Research Requirements Document (PRD)

**Project:** Verifiable Spacecraft Software Lifecycle
**Owner:** Independent researcher (Zartharas)
**Status:** Draft v1 — documentation phase
**Last updated:** 2026-08-02

## 1. Problem statement

Spacecraft flight software updates are typically deployed with minimal
verifiable assurance beyond a digital signature, if that. There is no
standard, measurable way to compare *how much* security assurance a given
update pipeline actually provides, or to quantify the cost (time, storage,
manual effort) of adding stronger assurance mechanisms. This makes it hard
for mission designers to make informed tradeoffs, and hard for researchers
to compare proposed supply-chain security schemes against each other.

Terrestrial software supply-chain security (SLSA, in-toto, Sigstore, TUF)
has matured rapidly since 2020, largely in response to incidents like
SolarWinds. Spacecraft software has not seen an equivalent, empirically
grounded treatment — despite operating under constraints (intermittent/
high-latency links, no human-in-the-loop during anomalies, physical
unrecoverability of a bad update) that make supply-chain failures more
consequential and harder to recover from than in terrestrial systems.

## 2. Goal

Build a controlled, end-to-end software lifecycle pipeline for a spacecraft
flight software application (cFS-based), instrument it with six discrete
levels of supply-chain assurance (S0–S5), inject a standardized set of
tampering/failure scenarios at each level, and measure detection accuracy,
recovery success, and operational overhead as assurance increases.

The **central research claim is comparative, not descriptive**: this project
does not claim "we added a signature and an SBOM to spacecraft software." It
claims to measure what each additional assurance mechanism buys you, and at
what cost, under spacecraft-relevant constraints (link latency/loss,
autonomous recovery, no live human intervention).

## 3. Non-goals

- This is **not** a production flight software security product. It is a
  research prototype for a controlled empirical study.
- This project does **not** use real operational spacecraft telemetry,
  real mission signing infrastructure, or any export-controlled technical
  data. See `Legal-Data-Sourcing-Notes.md`.
- This project does **not** aim to build a new cryptographic signature
  scheme — it composes existing, standard cryptographic tooling
  (Sigstore/cosign or equivalent) rather than inventing new crypto.
- Not attempting real RF/physical-layer simulation — the "uplink" is a
  protocol-realistic (CCSDS-informed) simulation, not an RF simulation.

## 4. Success criteria

The project is successful if it produces:

1. A working, reproducible pipeline that moves a cFS application through
   the full lifecycle: source → reproducible build → provenance → SBOM →
   signed release → ground authorization → simulated uplink → onboard
   verification → installation → attestation → operational monitoring →
   rollback/approval → updated authorization evidence.
2. Six configurable assurance conditions (S0–S5, see `Threat-Model.md`)
   that can be toggled independently for controlled comparison.
3. A standardized battery of injected failure/attack scenarios (tampered
   binary, incomplete SBOM, revoked key, downgrade attempt, stale
   attestation, false telemetry, etc.) run against every condition.
4. Quantitative results across all defined metrics (detection accuracy,
   time-to-identification, recovery success, manual evidence-processing
   effort, storage/link overhead, reproducibility rate) per condition.
5. A public GitHub repository with full documentation, reproducible setup
   instructions, and a clean issue/fix history suitable for citing as a
   contribution artifact.
6. A paper draft targeting the venue sequence defined in
   `Research-Paper-Outline.md`.

## 5. Assurance conditions (summary — full detail in Threat-Model.md)

| Condition | Assurance available |
|---|---|
| S0 | Signature only |
| S1 | Signature + SBOM |
| S2 | Signature + SBOM + build provenance |
| S3 | S2 + onboard attestation |
| S4 | S3 + trusted rollback |
| S5 | S4 + machine-readable authorization evidence |

## 6. Target artifact under test

A cFS (NASA Core Flight System) application, or a small set of them,
representing realistic flight software components (e.g., a telemetry
handler, a command ingest app). cFS is Apache 2.0 licensed and purpose-built
for this kind of research use — see `Legal-Data-Sourcing-Notes.md`.

## 7. Stakeholders / audience

- Primary: the researcher (sole contributor).
- Secondary: peer reviewers at target venues (IEEE Aerospace, SpaceSec,
  AIAA JAIS, Computers & Security, stretch: TDSC/TSE/TOSEM).
- Tertiary: open-source community / GitHub visitors who may cite, fork, or
  build on the pipeline, and any security researchers who discover and
  responsibly disclose issues via `SECURITY.md`.

## 8. Key risks (see also Threat-Model.md and prior analysis in project history)

- **Novelty risk:** SLSA/in-toto/Sigstore/TUF already formalize much of
  S0–S3. The paper's contribution must rest on spacecraft-specific
  constraints (latency, autonomy, unrecoverability) changing the
  engineering problem, not just relabeling existing frameworks.
- **Simulation realism risk:** an unrealistic "simulated uplink" (no
  latency, no loss, no bandwidth ceiling) undermines the paper's spacecraft
  claims. Must be CCSDS/DTN-informed or the paper must be scoped honestly
  as "terrestrial-analog pipeline with spacecraft-motivated constraints."
- **Generalizability risk:** a single cFS-stack evaluation caps the venue
  ceiling at JAIS/Computers & Security. Reaching TDSC/TSE/TOSEM requires a
  second stack or a formal, stack-agnostic model. **Resolved 2026-08-03,
  Phase 6** — see § 11: a second stack (F Prime) was added and the
  evaluation re-run against it. Still not sufficient on its own for
  TDSC/TSE/TOSEM without also running against the real frameworks (see
  § 11's precise claims-status scoping).
- **Metric legitimacy risk:** metrics like "time to trusted restoration" or
  "manual evidence-processing effort" need a credible baseline (what does
  S0 represent operationally?) or they read as invented numbers.
- **Scope creep into "tool collection":** explicitly flagged as the easiest
  failure mode for this topic. The comparative S0–S5 framing exists
  specifically to prevent this — every implementation decision should be
  traceable back to "which condition(s) does this support, and what does
  it let us measure?"

## 9. Open questions (update as resolved — track in STATUS.md)

- ~~Second software stack for generalizability: pursue now, or defer to a
  revision cycle after initial cFS results are in?~~ — resolved: pursued
  now (Phase 6, 2026-08-03). NASA JPL's F Prime (F´) added as stack #2;
  see § 11 and `docs/Threat-Model.md` "Phase 6 results."
- ~~Baseline definition for S0 in operational-effort metrics~~ — resolved,
  see § 10.
- ~~License for the repo~~ — resolved: Apache 2.0.

## 10. Metric definitions and baselines (resolved 2026-08-03, Phase 5)

This section closes the "metric legitimacy" risk from § 8 by stating,
explicitly, what each metric means and what it's measured against —
before any numbers get generated, not after. **Baseline = S0 itself**,
not an external real-world process. The project's actual research claim
is comparative (S0 vs. S1 vs. ... vs. S5), so S0's own cost/effort is the
correct zero-point for every overhead metric — there's no need to invent
a "real mission's manual process" baseline that this project has no way
to validate anyway.

- **Tampered-artifact / incomplete-component detection rate:** fraction
  of attack trials at a given condition where the pipeline correctly
  rejects, per Threat-Model.md's attack matrix. Measured directly from
  `PipelineResult.rejected_at` / `rollback_outcome`, not inferred.
- **Time to identify / time to trusted restoration:** wall-clock seconds
  for the relevant `pipeline.run()` call in this sandbox, using
  `time.perf_counter()`. **This is a sandbox-timing proxy, not a hardware
  or real-mission timing claim** — flag explicitly wherever cited. It's
  useful for *relative* comparison across conditions (does S5 take
  measurably longer than S0 to reach a verdict?), not as an absolute
  number meaningful outside this environment.
- **Manual evidence-processing effort:** number of evidence-store records
  generated per run, per condition. **This is a proxy for review burden,
  not a measured human-hours metric** — no human-factors study exists or
  is planned for this phase. More evidence records at S5 than S0 is the
  expected, measurable direction; how that maps to real operator effort
  is explicitly out of scope and should never be stated as if it were
  measured.
- **Traceability completeness:** for each condition, the pipeline stages
  *expected to be active* at that condition (per `condition.py`'s
  mechanism flags) that actually produced at least one evidence record
  during a given run. Denominator is condition-specific — S0 is not
  penalized for lacking SBOM-stage evidence it was never supposed to
  produce.
- **Storage and link overhead:** byte size of the additional artifacts
  (SBOM, provenance, attestation, authorization evidence) a condition
  produces, relative to S0 (which produces none of them). Measured
  directly from file sizes on disk, not estimated.
- **Reproducibility of the deployed binary:** fraction of build trials
  where two independent compiles produced a bit-identical hash. Currently
  measured against the stand-in stub artifact only — see STATUS.md
  "Claims status" for why this isn't yet a claim about the real cFS build.
- **Update acceptance accuracy:** a confusion-matrix-style measure per
  condition — true positive (legitimate update correctly approved), true
  negative (attack correctly rejected), false positive (attack wrongly
  approved), false negative (legitimate update wrongly rejected).

See `evaluation/experiment.py` for the implementation and
`evaluation/results/` for generated output.

## 11. Generalizability (resolved 2026-08-03, Phase 6)

Closes the "generalizability risk" from § 8. A second target stack was
added rather than deferred: NASA JPL's F Prime (F´), Apache 2.0, pinned to
tag `v4.2.2`, architecturally distinct from stack #1 (component-driven C++
vs. cFS's message-bus C) — see `fprime-app/README.md` for the full
rationale and `docs/Legal-Data-Sourcing-Notes.md` for the legal basis.

Re-running the full pipeline, 15-case attack matrix, and Phase 5
evaluation harness against this second stack required changing exactly
two adapter modules (`src/build/build.py`, `src/health/health_check.py`)
plus one correctness fix the test surfaced
(`src/ground_authorization/version_ledger.py`, previously a single global
file rather than scoped per stack) — every other assurance mechanism
generalized unmodified. Results are structurally identical to stack #1's
Phase 5 results (100% detection/success/reproducibility, 0 false
positives/negatives). See `docs/Threat-Model.md` "Phase 6 results" and
`evaluation/results/phase6_report_fprime.md` for full numbers.

**Scope of this claim, stated precisely (see STATUS.md "Claims
status"):** this is architectural/tooling generalizability between two
stand-in artifacts, not validation against two real flight-software
frameworks — neither cFS nor F´ has actually been built and run in this
project yet (both gated on a Docker-capable machine). The claim is that
the assurance ladder's design does not depend on which framework is
underneath, not that it has been proven against real flight software
twice.
