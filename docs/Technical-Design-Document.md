# Technical Design Document (TDD)

**Last updated:** 2026-08-02
**Status:** Draft v1 — architecture proposal, not yet implemented

## 1. Design principles

1. **One codebase, six conditions.** S0–S5 must be config-driven, not
   forked implementations. Every pipeline stage checks "is this mechanism
   active for the current condition?" rather than having condition-specific
   code paths duplicated.
2. **Evidence-first.** Every stage that could plausibly produce forensic
   or audit value writes a structured record to the evidence store, even
   at low assurance conditions where that evidence isn't yet *used* by
   verification — this lets later analysis compare "evidence existed but
   wasn't checked" (S0-S1) vs. "evidence existed and was checked" (S2+).
3. **No real spacecraft, no real ground segment.** Everything is simulated
   locally or in containers. See Legal-Data-Sourcing-Notes.md.
4. **Reuse existing standard tooling wherever possible.** This project
   composes SLSA/in-toto/Sigstore/CycloneDX-class tools rather than
   inventing new cryptographic primitives — novelty comes from the
   spacecraft-constrained composition and evaluation, not from new crypto.

## 2. Target artifact

A cFS (NASA Core Flight System, Apache 2.0) application. Candidate:
start with a single simple app (e.g., a sample telemetry output app from
the cFS sample-apps set) to get the full pipeline working end-to-end
before adding a second app for the generalizability question flagged in
PRD.md.

## 3. Component architecture

| Component | Candidate tooling | Notes |
|---|---|---|
| Reproducible build | Docker/Nix-pinned build environment | Must produce bit-identical output on re-run |
| Provenance generation | in-toto / SLSA provenance generator | Standard attestation format |
| SBOM generation | Syft → CycloneDX or SPDX | Pick one format and stay consistent |
| Signing | Sigstore/cosign (or a local-CA equivalent if offline signing is needed to model "no live human") | Needs to support a "revoked key" test case — plan key rotation/revocation handling explicitly |
| Ground authorization | Custom policy service (small rules engine) | Encodes "permitted configuration" policy for test case #8 |
| Uplink simulator | Custom, CCSDS-informed | Configurable latency/loss/bandwidth; this is the component most likely to draw reviewer scrutiny — build it carefully and document its model explicitly |
| Onboard verification agent | Custom, runs inside the cFS runtime or a wrapper around it | Signature + policy check |
| Attestation | Software-based attestation (TPM simulation or a software equivalent — real TPM hardware likely unnecessary for a simulated node) | Document clearly that this is software-simulated, not hardware root-of-trust, unless hardware becomes available |
| Installation / A/B rollback | Custom partition-state manager | Two logical partitions (active/inactive), atomic switch |
| Health validation | Custom health-check harness | Simple liveness/behavior checks against the running app |
| Evidence store | Structured JSON log, OSCAL-informed schema | Append-only; source of truth for metrics |
| Attack/failure injector | Custom test harness | Injects the 15 test cases from Threat-Model.md at the correct pipeline stage |
| Metrics collector | Python analysis scripts over the evidence store | Produces the per-condition comparison tables for the paper |

*(All "candidate tooling" choices are proposals — confirm/revise during
Phase 1 of Implementation-Plan.md and update this table. Don't treat this
table as final.)*

## 4. Evidence record schema (draft)

Each evidence record, regardless of stage, should carry at minimum:

```json
{
  "record_id": "uuid",
  "timestamp": "ISO8601",
  "pipeline_stage": "string (e.g. 'build', 'provenance', 'signing', ...)",
  "condition": "S0 | S1 | S2 | S3 | S4 | S5",
  "artifact_ref": "hash or identifier of the artifact this record concerns",
  "actor": "which simulated actor produced this record",
  "result": "pass | fail | n/a",
  "detail": { "...stage-specific fields..." },
  "test_case_injected": "null, or test case # from Threat-Model.md if this run included an injected failure"
}
```

Refine this schema once the evidence store is actually implemented —
update this section rather than letting the schema drift undocumented.

## 5. Condition switching mechanism

Proposal: a single config file (e.g., `condition.yaml`) read by every
pipeline stage at run time, defining which mechanisms are active:

```yaml
condition: S3
mechanisms:
  signature: true
  sbom: true
  provenance: true
  onboard_attestation: true
  trusted_rollback: false
  machine_readable_authorization: false
```

Each stage checks the relevant flag before performing its check —
inactive mechanisms are skipped, not stubbed with fake-pass results, so
the pipeline behaves as an honest S0-S5 system rather than a system that
"has everything but pretends not to."

## 6. Deployment/runtime model for the prototype

Recommend: everything runs in Docker Compose (or similar) on a single
development machine — build service, ground authorization service, uplink
simulator, "spacecraft" container (running the cFS app + onboard
verification/attestation/rollback logic), evidence store, all as separate
containers/services communicating over local network. This is sufficient
realism for the supply-chain claims being made and avoids any real
network/hardware dependency.

## 7. Open technical decisions (track resolution in STATUS.md)

- Exact SBOM format (CycloneDX vs SPDX) — leaning CycloneDX for tooling
  maturity, confirm during Phase 2.
- Whether to model a real TPM (via software TPM / swtpm) or a fully custom
  attestation stub — swtpm gives more credibility for the S3 claims.
  Decide during Phase 3.
- Second cFS app or second software stack entirely, and when to add it.
- Exact policy language for ground authorization (custom DSL vs. reusing
  something like OPA/Rego) — Phase 1 uses a trivial hardcoded policy
  (approve iff signature valid); real policy language decision deferred
  to Phase 4 (S5 machine-readable authorization).

## 7a. Phase 1 decisions actually made (resolved, not just planned)

- **Signing: Ed25519 via the `cryptography` Python package**, not
  Sigstore/cosign. Rationale: S0's assurance claim is "signature only" —
  a standard, composable Ed25519 signature satisfies that without needing
  Sigstore's transparency-log infrastructure, which is more relevant to
  S2+ provenance/transparency claims. Revisit if a later phase specifically
  needs keyless signing or a public transparency log.
- **Target artifact: a stand-in stub (`cfs-app/stub-telemetry-app`), not
  real cFS**, because the authoring sandbox had no Docker/cmake/root. The
  real cFS build is pinned and documented in `cfs-app/Dockerfile`
  (tag `v7.0.0`, commit `b4ec679b2fd9d825610515ceb186cbfa80c60cfc`) but
  untested — run it on a Docker-capable machine and confirm before citing
  any Phase 1+ result as being about "spacecraft software." See
  `cfs-app/README.md`.
- **Condition switching: implemented as designed** — `src/condition.py`
  loads a `condition.yaml` with one boolean per mechanism; every stage
  checks its own flag. No condition-specific code forks.
- **Evidence store: implemented as designed** — append-only JSON-Lines at
  `evaluation/evidence_log.jsonl`, matching the § 4 schema exactly.

## 7b. Phase 2 decisions actually made

- **SBOM format: CycloneDX**, confirming the § 7 lean. Hand-rolled
  minimal JSON generator (`src/sbom/sbom.py`) rather than invoking Syft —
  the stub artifact has no real dependency graph for Syft to discover.
  Swap in real Syft output once pointed at the real cFS build; the shape
  is deliberately CycloneDX-compatible so that swap should be low-friction.
- **Provenance format: hand-rolled, SLSA v1/in-toto-statement-shaped
  JSON** (`src/provenance/provenance.py`), not a full in-toto/SLSA library
  invocation, for the same reason as SBOM — schema shape matters for
  testing the assurance-ladder comparison, not spec conformance, at this
  stage. Source identity is this repo's own `git rev-parse HEAD` (the stub
  artifact lives inside this repo) — revisit once the real cFS build has
  its own separate source repo to attest against.
- **Known-vulnerability detection: a small synthetic table**
  (`KNOWN_VULNERABLE_COMPONENTS`), not a real CVE/OSV feed lookup. Tests
  the detection *mechanism*, not real-world vulnerability coverage — don't
  conflate the two when writing up results.
- **Version/downgrade tracking: a single-file JSON ledger**
  (`src/ground_authorization/version_ledger.py`), explicitly flagged in
  its own docstring as a Phase 2 simplification — a real system would tie
  this into the evidence/authorization chain (S5), not a side file.
- **Uplink link profiles: three fixed presets** (`IDEAL`,
  `LEO_TYPICAL`, `DEEP_SPACE_TYPICAL`) in `src/uplink_sim/uplink.py`,
  loosely order-of-magnitude informed by CCSDS-class link budgets, not
  tied to a specific real mission. Loss/latency values are illustrative,
  not validated against a specific reference system — flag this
  explicitly if cited in the paper's methodology.

## 7c. Phase 3 decisions actually made

- **Attestation: custom software stub, not swtpm/real TPM.** The
  authoring sandbox has no swtpm binary, no tpm2-tools, and no root to
  install either. `src/attestation/attestation.py` signs a measurement
  (installed binary hash + partition id + timestamp) with a dedicated
  Ed25519 key, which lets the *assurance property under test* —
  detecting a stale or mismatched claim about what's running — be tested
  without hardware. **This is a materially weaker guarantee than real
  TPM-backed attestation**: a software-held key can be exfiltrated in ways
  a TPM-sealed key cannot, and there's no hardware root of trust anchoring
  the measurement. State this limitation explicitly in the paper — do not
  let "attestation" imply hardware backing it doesn't have. Revisit if
  swtpm becomes available on a capable machine (same category of decision
  as the real cFS Docker build — flagged, not blocking).
- **A/B partitions: tentative-activate + confirm/revert, single JSON state
  file.** `src/installation/partitions.py`. Models the standard embedded
  update pattern (boot into candidate, validate, confirm or revert) rather
  than a naive immediate-switch. The recovery-image integrity check before
  reverting (test case #14) was a late but important addition — a plain
  A/B implementation without it would pass every test except that one.
- **Health check: execute the installed binary, compare stdout to an
  expected deterministic pattern.** `src/health/health_check.py`. Works
  because the stub artifact is deterministic by construction (see
  `cfs-app/stub-telemetry-app/main.c`) — a real cFS app's health check
  would look at telemetry/housekeeping data instead, not stdout.
- **Rollback controller: thin coordination layer, not new state.**
  `src/rollback/rollback.py` just decides confirm-vs-revert and delegates
  to `partitions.py`, which owns all actual state and the integrity check.
  Kept separate to match the named "Rollback controller" actor in
  Pipeline-Flow-Document.md, not because the logic is complex enough to
  need its own module on merits alone.
