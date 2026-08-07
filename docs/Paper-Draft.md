# Measuring Software Supply-Chain Assurance for Spacecraft Flight Software: A Controlled, Comparative Evaluation

**Status:** Draft v0.1 — Introduction only. Remaining sections
(Background/Related Work, Threat Model, System Design, Evaluation
Methodology, Results, Discussion, Limitations, Conclusion) are stubbed
below per `docs/Research-Paper-Outline.md` §2's structure; each gets
drafted and reviewed section by section, not all at once, so citation and
factual claims can be checked incrementally rather than in one large pass.

Target venue (current decision, see `docs/Research-Paper-Outline.md` §3,
2026-08-07): Computers & Security, first attempt; Journal of Space Safety
Engineering as the next attempt if that submission does not succeed.

---

## 1. Introduction

Spacecraft flight software updates are typically deployed with minimal
verifiable assurance beyond a digital signature, if that. When a signature
is the only check performed, an update is trusted the moment it can be
shown to have come from the right key — nothing in that check says
whether the *build* that produced the signed artifact was itself
trustworthy, whether the configuration it carries is one an operator
actually authorized, or whether the spacecraft can prove, after
installation, that the update it is now running is the one that was
approved. Terrestrial software has spent the last several years building
a substantial body of tooling and practice to close exactly this gap —
SLSA, in-toto, Sigstore, and the Update Framework (TUF) each formalize a
piece of it: build provenance, artifact attestation, and resilience to
signing-key compromise, respectively [TODO: cite TUF/in-toto/SLSA — per
`docs/Research-Paper-Outline.md` §6's 2026-08-07 flag, these are cited via
their own specifications as the systems this paper measures against, not
as literature-review citations subject to the peer-reviewed-journal bar
used elsewhere in this section; final citation form to be confirmed].
Spacecraft software has not seen an equivalent, empirically grounded
treatment, despite operating under constraints that make supply-chain
failures more consequential and harder to recover from than in most
terrestrial systems: links are often high-latency or intermittent, there
is frequently no human in the loop at the moment an anomaly must be
handled, and a bad update to a single, physically unreachable asset
cannot be patched by simply pushing another commit.

This gap is not hypothetical. Real attacks against operational space
systems have already demonstrated what an under-defended software/update
layer costs in practice: the AcidRain wiper malware disabled satellite
modems in the Viasat KA-SAT network in 2022, and a later variant,
AcidPour, extended the same attack pattern to a broader set of embedded
Linux devices (Kang, Park, & Lee, 2024, cite for the fact that these
incidents are discussed in that survey). **Flag — not yet
citation-verified:** the specific figures often quoted for this incident
(affected-device counts, exact date) are widely reported in press
coverage of the Viasat hack but have **not** been checked against Kang et
al.'s actual paper text (only their abstract, which names AcidRain/
AcidPour, has been seen so far) — this draft deliberately omits specific
numbers until that check happens, rather than repeat a figure from
general knowledge and attach it to a citation that may not actually state
it. Before this section is finalized: (1) read Kang et al.'s full text to
confirm exactly what it claims about these incidents, and (2) if
specific figures are wanted, find and verify a primary source (e.g., the
original SentinelOne/Viasat incident disclosures) rather than cite them
through a survey paper that may only mention the incidents in passing.
These are ground/terminal-segment incidents rather than attacks on an
onboard flight computer directly, but they establish that the broader
satellite-system software supply chain is an active, exploited attack
surface, not a theoretical concern reserved for nation-state threat
modeling exercises.

**Searched, 2026-08-07, and reporting the negative result rather than
implying otherwise:** no publicly documented real-world incident of an
onboard flight-software supply chain compromise specifically (a
build-time or update-time compromise, as distinct from the ground/RF-
segment attacks above) was found. A related but importantly distinct
paper turned up during this search — Vanlyssel, Sobrados, Anwar, Roman, &
Anwar, "SpyChain: Multi-Vector Supply Chain Attacks on Small Satellite
Systems" (arXiv:2510.06535, 2025) — and an initial draft of this
paragraph mischaracterized it before its actual abstract was read
directly (fetched and checked 2026-08-07): SpyChain targets *auxiliary
COTS hardware components* (its abstract explicitly contrasts this with
flight software, which it describes as already benefiting from "strict
security practices and oversight"), not a flight-software build or
update-time compromise. It is evidence that the broader small-satellite
hardware/component supply chain is an active research target, not
evidence bearing on this paper's specific claim about flight-software
update pipelines — citing it as if it were would overstate the
motivation. It is an arXiv preprint, not a peer-reviewed publication, so
it would not qualify for the journal-only bar in any case; it is
mentioned here only as a search result worth being aware of, not as a
citation this paper should rely on.

The honest state of the evidence, then, is: no known documented incident,
academic or otherwise, of a flight-software build/update-time supply
chain compromise on an operational spacecraft. **This absence is itself
part of the motivation, not a weakness to paper over:** a supply-chain
compromise against a single, physically unreachable spacecraft is a
low-frequency, high-consequence event by construction — the appropriate
engineering response is not to wait for one to be publicly documented
before building measurable defenses, any more than aviation safety
engineering waits for a specific class of crash before addressing a
known-feasible failure mode. State this reasoning explicitly in the final
version rather than leave the absence of an incident unexplained or
imply one exists.

The central problem this paper addresses is not "spacecraft software
lacks security" in the abstract, but something narrower and, we argue,
more useful: there is no standard, measurable way to compare *how much*
security assurance a given update pipeline actually provides, or to
quantify the cost — in time, storage, or manual review effort — of adding
a stronger assurance mechanism. This makes it hard for mission designers
to make informed tradeoffs (is a given mechanism worth its overhead for
this mission's risk profile?), and hard for researchers proposing new
supply-chain security schemes to compare their approach against prior work
on common ground.

**This paper's contribution is comparative, not descriptive.** We do not
claim to have added a signature and a Software Bill of Materials (SBOM) to
a piece of spacecraft software. We built a controlled, end-to-end software
lifecycle pipeline for spacecraft flight software — instrumented with six
discrete, strictly additive levels of supply-chain assurance (S0 through
S5, Section [Threat Model reference]) — and measured what each additional
mechanism actually buys, and at what cost, under spacecraft-relevant
constraints: link latency and loss, autonomous recovery without a live
operator, and no ability to simply redeploy a fixed binary to a
unit already in orbit. We evaluate this pipeline against a standardized
battery of 15 attack and failure scenarios, across four independent
target software stacks — two purpose-built stand-in artifacts and two
real, unmodified NASA/JPL flight software frameworks (Core Flight System
and F Prime) — and against a real, unmodified baseline deployment of TUF,
to ground the paper's central claim (that spacecraft-specific constraints
change the engineering problem, not just the deployment target) in
measurement rather than assertion.

Concretely, this paper makes the following contributions:

1. A six-level, strictly additive supply-chain assurance ladder (S0–S5)
   for spacecraft flight software, with an open-source, reproducible
   reference implementation spanning build, ground authorization,
   simulated uplink, onboard verification, installation, attestation,
   operational monitoring, and rollback.
2. A standardized 15-case attack and failure injection matrix, run
   against every assurance condition across four independent target
   software stacks, including two real, unmodified NASA/JPL flight
   software frameworks.
3. A real, measured baseline comparison against an unmodified upstream
   TUF deployment, quantifying which parts of this project's assurance
   ladder have no equivalent in an existing, widely adopted terrestrial
   software-update framework.
4. A methodology for independently pressure-testing the resulting threat
   model and mitigations — four independent, blind, AI-driven red-team
   review passes that surfaced and led to fixes for 21 real security and
   correctness defects — reported with an explicit, honest accounting of
   what this methodology does and does not substitute for (Section
   [Limitations reference]).

The remainder of this paper is organized as follows: Section [Background]
situates this work against SLSA/in-toto/TUF/Sigstore and prior spacecraft
software security literature; Section [Threat Model] formalizes the
threat actors and the S0–S5 ladder; Section [System Design] describes the
pipeline implementation; Section [Evaluation Methodology] describes the
attack matrix, metrics, and experimental protocol; Sections [Results] and
[Discussion] present and interpret the findings; Section [Limitations]
states plainly what this evaluation does not establish; Section
[Conclusion] closes.

---

## 2. Background / Related Work

**Note on citation treatment in this section, per the 2026-08-07 flag in
`docs/Research-Paper-Outline.md` §6:** SLSA, in-toto, Sigstore, TUF, and
OSCAL are cited below via their own specifications/project sites, as the
systems this project's design is built from and measured against — the
same treatment already given to TUF in the real-baseline comparison
(Section [Evaluation Methodology]; `docs/Threat-Model.md` "Phase 8
real-baseline comparison: python-tuf"). This project does not reimplement
any of them, and pinning to a specification rather than a single academic
paper about that specification is arguably more precise for a systems
paper regardless of the venue's stance on conference proceedings. All
other citations in this section are drawn from the peer-reviewed-journal
shortlist verified in `docs/Research-Paper-Outline.md` §6
(2026-08-07) and are limited to claims that abstract-level information
can actually support — anything more specific is marked for full-text
verification before submission, not asserted from the abstract alone.

### 2.1 Terrestrial software supply-chain security

Following SolarWinds-class incidents, terrestrial software supply-chain
security has converged on a small number of complementary properties
rather than a single tool: **provenance** (can the deployed artifact be
traced to the source and build process that produced it — SLSA's graduated
levels, in-toto's attestation layer), **transparency/attestation** (can a
claim about an artifact's origin or state be independently verified —
Sigstore's signing and transparency-log infrastructure), and **update
resilience** (can the update mechanism itself survive compromise of one or
more of its own signing keys — TUF's core contribution, and the specific
property this project's S0 baseline deliberately does *not* provide,
since S0 is signature-only with no revocation-aware verification layered
on top). OSCAL, from NIST, addresses a related but distinct need:
representing compliance and authorization evidence in a machine-readable
form suitable for automated policy checking rather than only human audit
review. This project's S1–S5 ladder maps loosely onto this same property
space — SBOM (S1) and provenance (S2) to the first property, onboard
attestation (S3) to the second, and machine-readable authorization
evidence (S5) to a use of the third that mirrors OSCAL's design goal more
than any of SLSA/in-toto/TUF's own scope. None of these frameworks was
designed with spacecraft-specific operating constraints in view; Section
[Threat Model] and the real-baseline comparison against an unmodified
python-tuf deployment (Section [Evaluation Methodology]) make this gap
measurable rather than asserted, addressing the most direct form of
objection this framing invites — that this project is "just SLSA/in-toto/
TUF applied to a new domain."

### 2.2 Spacecraft and satellite software security

The existing literature on spacecraft and satellite cybersecurity is
weighted heavily toward the ground segment and the radio-frequency link,
not the onboard software supply chain. Manulis, Bridges, Harrison, Sekar,
& Davis (2020) analyze historical satellite security incidents and find
that ground and RF communications, not the space segment itself, have
been the most favored attack targets to date — a finding this paper's own
literature search (Section 1) independently corroborates for the specific
case of flight-software build/update compromise, where no documented
incident was found at all. Ahmad et al. (2022) and Kang, Park, & Lee
(2024) both survey satellite communication security more broadly,
covering confidentiality/integrity/availability threats and countermeasures
at the communications-protocol level; Kang et al. specifically discuss the
AcidRain and AcidPour incidents referenced in Section 1. [TODO: verify
before final drafting whether either survey discusses onboard
software-update assurance as a category, or confirms — as the current
draft asserts based on their abstracts and general scope — that this is
outside their focus.] Taken together, this body of work establishes that
satellite cybersecurity is an active and maturing research area, but one
whose center of gravity has been the link and ground segment; the software
lifecycle that produces and updates what runs onboard has received
comparatively little direct empirical treatment, which is the specific gap
this paper's contribution targets.

### 2.3 Adjacent domains: attestation and update assurance in other
constrained/autonomous systems

Three areas of adjacent work bear directly on this project's specific
combination of attestation and update assurance without a live human
overseeing either. Usman, Afzal, & Asplund (2026) integrate remote
attestation with secure software updates in embedded systems (RASUES,
extending the IETF RATS architecture to explicitly cover the pre- and
post-update device state) — the closest direct analog to this project's
S3-plus-update-pipeline combination found in this literature search, and
worth returning to for detailed comparison once this section is finalized
against its full text rather than its abstract alone. Qureshi, Marvi,
Shamsi, & Aijaz (2021) and Sahlmann, Clemens, Nowak, & Schnor (2021)
address secure over-the-air update assurance in, respectively, autonomous
vehicles and constrained IoT devices — domains that share this project's
concern with updating a device that cannot be physically retrieved on
demand, but neither operates under the link-latency/intermittency
constraints Section [Threat Model] treats as first-class, and neither
targets a domain where a failed update can mean total, permanent loss of
the asset the way an unrecoverable spacecraft update can. [TODO: confirm
this last claim — permanence/unrecoverability of failure — against each
paper's actual treatment of failure modes, not just inferred from domain
knowledge of vehicles/IoT generally.]

### 2.4 NASA Core Flight System and flight-software engineering practice

The target artifact used throughout this project's evaluation, NASA's
Core Flight System (cFS), has its own body of engineering-practice
literature independent of the security question this paper addresses.
Ganesan, Lindvall, McComas et al. (2012) analyze unit-testing practice
across a flight-software product line predating cFS's open-source release,
and Gonzalez, Rojas, Bergel, & Díaz (2019) evaluate flight-software
architecture verification methodology for CubeSat nanosatellites using a
different framework (SUCHAI) but a directly comparable engineering
concern — ensuring an evolving flight-software codebase continues to
satisfy its architectural and non-functional requirements over the
software's lifecycle. Neither addresses supply-chain assurance
specifically, but both establish that flight-software engineering rigor
and verification tooling is an active concern in this community
independent of the security framing this paper adds to it — this project's
contribution sits alongside this literature rather than in competition
with it.

## 3. Threat Model

### 3.1 Threat actors

This project's threat model considers six actors, chosen to span both
adversarial and non-adversarial causes of an untrustworthy update reaching
a spacecraft (`docs/Threat-Model.md` §2):

1. **An external attacker with network access** to the ground segment or
   the uplink channel — tampering with an update in transit, replaying a
   prior update, or attempting a downgrade to a previously superseded
   version.
2. **Compromised build infrastructure** — an unauthorized or malicious
   build runner, or a poisoned upstream dependency, producing an artifact
   that does not match its claimed source.
3. **An insider with legitimate but excessive access** — someone who can
   validly sign a release but approves a configuration that is
   technically authenticated yet policy-prohibited (for example, a debug
   flag that should never reach a flight build).
4. **A compromised or leaked signing key** — where the specific failure
   mode of interest is not the initial compromise but whether the system
   continues to accept updates signed with that key after it should have
   been revoked.
5. **Onboard software fault** — a failed health check or an installation
   interrupted partway through. This actor is not adversarial, but it is
   included deliberately: assurance mechanisms built to catch adversarial
   tampering (such as a rollback path) need to degrade gracefully under
   ordinary hardware/software failure too, and a design that only handles
   the adversarial case is incomplete for an operational spacecraft.
6. **Ground/space state divergence** — a disagreement between what the
   ground segment believes is installed and what is actually running
   onboard, covering both deliberate deception (falsified telemetry) and
   honest desynchronization (a missed or delayed status update).

**Explicitly out of scope**, and stated here rather than left for a
reviewer to infer: RF-layer jamming or spoofing, physical tampering with
ground-segment hardware, and an insider threat with root access to the
signing HSM itself. These are real and significant spacecraft security
concerns, but they sit outside this project's scope — which is
supply-chain and lifecycle assurance for the software itself, not RF
security or physical/personnel security. A design that claimed to address
these without evaluating them would be a stronger claim than this paper's
evidence supports.

### 3.2 The S0–S5 assurance ladder

Rather than treat "supply-chain security" as a single property a pipeline
either has or lacks, this project decomposes it into six strictly
additive conditions, S0 through S5, where each condition includes every
mechanism present at the prior level plus exactly one new one. This
additive structure is the paper's central methodological device: because
every condition above S0 is "S0 plus one more thing," any difference in
detection rate, timing, or overhead observed between two adjacent
conditions can be attributed to that one added mechanism specifically,
rather than to an uncontrolled bundle of simultaneous changes.

| Condition | Mechanisms present | New mechanism vs. prior | Primarily addresses (§3.1 actor) |
|---|---|---|---|
| S0 | Signature only | — (baseline) | External attacker (in-transit tampering only — a *revoked* key is still accepted at S0, since revocation-aware verification is not part of the baseline) |
| S1 | S0 + SBOM | Software Bill of Materials | Compromised build infrastructure (undisclosed/vulnerable dependencies) |
| S2 | S1 + build provenance | SLSA/in-toto-style provenance attestation | Compromised build infrastructure (source-to-binary correspondence); downgrade attempts |
| S3 | S2 + onboard attestation | Runtime/boot attestation on the spacecraft side | Ground/space state divergence (verifying what is actually running, not just what was sent) |
| S4 | S3 + trusted rollback | Verified A/B partition rollback on failure | Onboard software fault; interrupted installation |
| S5 | S4 + machine-readable authorization evidence | OSCAL-informed structured evidence for ground/auditor consumption | Insider with legitimate-but-excessive access (policy-prohibited but technically signed configurations) |

The pipeline implementation enforces a hard architectural requirement
behind this table: the same underlying artifact and pipeline code must be
able to run under any of the six conditions purely through configuration,
with no per-condition code fork (`docs/Technical-Design-Document.md`
"Condition switching"). This is what makes the comparison controlled
rather than incidental — every condition is the identical pipeline with a
strictly larger or smaller set of mechanisms switched on, not six
differently-implemented pipelines being compared after the fact.

It is worth being explicit about what this ladder does not claim. It is
not a claim that these six mechanisms are the only ones worth measuring,
nor that this specific ordering is the only defensible one (SBOM before
provenance, for instance, is a design choice, not a logical necessity).
It is a claim that *this* additive structure, evaluated end-to-end against
a standardized attack matrix (Section [Evaluation Methodology]), produces
measurable, attributable evidence about the marginal value of each
mechanism — which is the specific gap Section 1 identifies in existing
practice.

## 4. System Design

### 4.1 Pipeline architecture

The reference implementation moves an artifact through twelve stages —
source, reproducible build, provenance generation, SBOM generation, signed
release, ground authorization, simulated uplink, onboard signature and
policy verification, installation, boot/runtime attestation, health
validation, and A/B partition rollback-or-approval, closing with an
updated authorization-evidence record that feeds the next lifecycle
iteration (`docs/Pipeline-Flow-Document.md` §§1–3). Every stage that can
plausibly produce forensic or audit value writes a structured record to a
single append-only evidence store, even at assurance conditions where
that evidence is not yet acted upon — this is a deliberate design
principle (`docs/Technical-Design-Document.md` §1, principle 2), not an
incidental logging choice, because it is what lets the evaluation
distinguish "the evidence existed but nothing checked it" (below the
condition where a mechanism activates) from "the evidence existed and was
checked" (at or above it), rather than conflating absence-of-checking
with absence-of-evidence.

The architectural requirement stated in Section 3.2 — one codebase, six
conditions, no per-condition code fork — is implemented as a single
configuration file read by every stage at run time (`src/condition.py`),
with one boolean flag per mechanism. Each stage checks its own flag
before performing its check; an inactive mechanism is skipped outright,
not stubbed with a fake-pass result, so the pipeline behaves as an honest
S0–S5 system rather than one that implements every mechanism internally
and merely suppresses reporting of some of them
(`docs/Technical-Design-Document.md` §5). This distinction matters for
the paper's evidentiary claims: a detection result at condition S(n) is
evidence that mechanism *n* caught the case, not evidence that a
more-capable, always-on system happened to have its result correctly
filtered for display.

### 4.2 Component implementation and stated fidelity

Several components are implemented as deliberately reduced-fidelity
stand-ins for real infrastructure, each chosen to test the *assurance
property* a mechanism is meant to provide without requiring
infrastructure unavailable in the original build environment. Each
reduction is stated plainly here, not left for a reviewer to discover:

- **Provenance and SBOM formats** (`src/provenance/provenance.py`,
  `src/sbom/sbom.py`) are hand-rolled, SLSA v1/in-toto-statement-shaped
  and CycloneDX-shaped JSON respectively, rather than full library
  invocations of the corresponding standard tooling. This tests whether
  the pipeline's *use* of provenance/SBOM data (binding it to an
  artifact, checking it, rejecting on mismatch) works correctly; it is
  not a claim of byte-level conformance to either specification.
- **Onboard attestation** (`src/attestation/attestation.py`) is a
  software-only construction: a measurement (installed binary hash,
  partition identifier, timestamp) signed with a dedicated Ed25519 key,
  not a hardware root of trust such as a TPM. This is a materially
  weaker guarantee than real TPM-backed attestation — a software-held
  key can be exfiltrated in ways a hardware-sealed key cannot — and this
  paper does not claim otherwise; "attestation" throughout this paper
  refers to this software construction unless stated otherwise
  (`docs/Technical-Design-Document.md` §7c).
- **The simulated uplink** (`src/uplink_sim/uplink.py`) offers three
  fixed link profiles (ideal, LEO-typical, deep-space-typical) that are
  loosely, order-of-magnitude informed by CCSDS-class link budgets but
  not validated against any specific reference mission's actual
  telemetry. This is the component most likely to draw scrutiny over
  spacecraft-realism claims, and is treated accordingly in Section
  [Limitations] rather than presented as RF-accurate.
- **Ground-authorization policy** is a small, explicit Python deny-list
  rather than a general-purpose policy engine (e.g., OPA/Rego). This
  tests whether a correctly-signed release can still be correctly
  rejected on policy grounds — the property under test — without
  depending on unverified third-party policy infrastructure; the
  deny-list's check-shape maps cleanly onto a Rego `deny` rule set should
  a real ground-system migration ever be pursued
  (`docs/Technical-Design-Document.md` §7d).
- **Authorization evidence** (S5) is an OSCAL-*informed* JSON
  aggregation — subject, findings, and overall-result fields modeled on
  OSCAL's shape — rather than a conformant implementation of the OSCAL
  schema itself. This paper makes no claim of OSCAL compatibility
  specifically, only that machine-readable, structured evidence in this
  general shape is what the S5 condition provides.

Each of these choices trades specification conformance for testability of
the specific mechanism-level question this paper asks (does this
assurance layer detect what it is supposed to detect, and at what cost),
and each is a place where a production system aimed at operational
deployment, rather than controlled comparative measurement, would
reasonably choose differently.

### 4.3 Target software stacks

The pipeline was evaluated against four independent target artifacts,
added incrementally to address generalizability: two purpose-built
stand-in stub applications (a C telemetry-output stub and an
architecturally distinct C++ component-based stub, modeled respectively
on cFS's message-bus architecture and F Prime's component/port
architecture), and two real, unmodified NASA/JPL flight software
frameworks built and run for the first time against this pipeline in
Phase 7 — NASA's Core Flight System (cFS, tag `v7.0.1`) and NASA JPL's F
Prime (F´, tag `v4.2.2`). The two real frameworks required no changes to
the assurance-mechanism implementations themselves; generalizing from the
stand-in stubs to the real frameworks required changes to exactly two
adapter modules (`src/build/build.py`, `src/health/health_check.py`) that
had accidentally hardcoded assumptions specific to the first stub's shape
(`docs/Technical-Design-Document.md` §7f), plus one real correctness fix
the generalization exercise itself surfaced (a version ledger that was a
single global file rather than scoped per stack, which produced a false
downgrade-detection result the first time a second stack was evaluated).
Health checking against the two real frameworks required a further
design change, since both are long-running processes rather than the
stand-in stubs' run-to-completion model: `health_check.py` was extended
with a persistent-process check that waits for a genuine, empirically
determined boot-success log line from the binary's own stdout, rather
than treating the mere absence of a crash as a health signal
(`docs/Technical-Design-Document.md` §7g) — a design decision made
deliberately to avoid fabricating a health result from the absence of
evidence.

## 5. Evaluation Methodology

### 5.1 Attack and failure injection matrix

A standardized battery of 15 test cases is injected at the pipeline stage
each is designed to target, and each is run against every assurance
condition where the relevant mechanism could plausibly detect it
(`docs/Threat-Model.md` §3). Each test case carries a stated *expected*
first-detection condition — a hypothesis about which mechanism should
catch it first, not a guaranteed or engineered outcome. This distinction
matters methodologically: a case that is caught earlier or later than its
stated expectation is itself a result worth reporting (Section [Results]
states any such divergence explicitly, per `docs/Threat-Model.md` §3's
own note that these hypotheses are "to validate, not guaranteed
outcomes"), not evidence to be quietly reconciled after the fact.

| # | Test case | Injected at | Expected first detection |
|---|---|---|---|
| 1 | Binary does not match source | Build → Provenance | S2 |
| 2 | Missing or false provenance | Provenance | S2 |
| 3 | Incomplete SBOM | SBOM generation | S1 |
| 4 | Dependency with known test vulnerability | SBOM / dependency scan | S1 |
| 5 | Unauthorized build runner | Build environment | S2 |
| 6 | Modified update (in transit) | Uplink | S0 |
| 7 | Revoked signing key | Signature verification | S0/S2 (revocation-aware verification) |
| 8 | Correct signature but prohibited configuration | Ground authorization / policy | S5 |
| 9 | Downgrade attempt | Ground authorization / onboard verification | S2/S4 |
| 10 | Interrupted installation | Installation | S4 |
| 11 | Failed health check | Post-install health validation | S3/S4 |
| 12 | Stale attestation | Onboard attestation | S3 |
| 13 | Ground/spacecraft inventory disagreement | Operational monitoring | S5 |
| 14 | Invalid recovery image | Rollback | S4 |
| 15 | False "successful installation" telemetry | Operational monitoring / attestation | S3/S5 |

Beyond this matrix, two adaptive-attacker scenarios and a per-mechanism
ablation study extend the evaluation to two questions the fixed matrix
cannot answer on its own: whether an attacker adapting across attempts
changes the outcome, and whether each individual mechanism's contribution
holds when it alone is disabled from an otherwise-fully-active condition
(rather than only observed cumulatively as conditions are added). [TODO,
Section [Results]/[Discussion]: state plainly, per objection 5 in
`docs/Research-Paper-Outline.md` §4, that the adaptive-attacker scenarios
test whether detection halts the pipeline, not whether the attacker is
genuinely evasive or time-adaptive — this scope boundary must not be
implied away when the results are presented.]

### 5.2 Metrics and the baseline decision

Every metric is defined and its measurement method fixed *before* any
results were generated, specifically to prevent the metric definitions
themselves from being shaped retroactively by whatever the numbers
happened to show (`docs/PRD.md` §8, "metric legitimacy" risk; §10,
resolution). **The baseline for every overhead metric is S0 itself, not
an external real-world reference process.** This project's central claim
is comparative — S0 vs. S1 vs. ... vs. S5 — so S0's own cost is the
correct zero-point; inventing a "real mission's manual process" baseline
this project has no way to independently validate would substitute an
unverifiable number for a measured one.

- **Detection rate:** the fraction of attack trials at a given condition
  where the pipeline correctly rejects the injected case, read directly
  from `PipelineResult.rejected_at` / `rollback_outcome` fields, not
  inferred from log inspection.
- **Time to detection / time to trusted restoration:** wall-clock seconds
  for the relevant pipeline call, measured with `time.perf_counter()`.
  **This is a sandbox/local-hardware timing proxy, not a flight-hardware
  or real-mission timing claim** and is stated as such wherever cited —
  useful for relative comparison across conditions on the same hardware,
  not as an absolute number meaningful outside this environment (see
  Section [Limitations] on the related Docker-launch-overhead confound
  for the real-framework stacks specifically).
- **Manual evidence-processing effort:** the count of evidence-store
  records generated per run, per condition — an explicit proxy for review
  burden, not a measured human-hours figure. No human-factors study of
  actual operator effort exists or is claimed.
- **Traceability completeness:** for each condition, the fraction of
  pipeline stages *expected to be active* at that condition that actually
  produced at least one evidence record during a given run. The
  denominator is condition-specific, so S0 is not penalized for lacking
  evidence from stages it was never meant to exercise.
- **Storage and link overhead:** the byte size of the additional
  artifacts (SBOM, provenance, attestation, authorization evidence) a
  condition produces beyond S0, measured directly from on-disk file
  sizes.
- **Reproducibility:** the fraction of build trials in which two
  independent builds from the same source produced a bit-identical
  binary hash.
- **Update acceptance accuracy:** a confusion matrix per condition —
  true positive (legitimate update correctly approved), true negative
  (attack correctly rejected), false positive (attack wrongly approved),
  false negative (legitimate update wrongly rejected).

### 5.3 Experimental protocol

Each condition/test-case combination is run as a repeated trial (30
trials per case in the results reported in Section [Results], following
an initial reduced-trial verification pass used only to confirm harness
correctness before the full run) via `evaluation/experiment.py`, which
implements one scenario function per attack-matrix test case returning an
explicit outcome record for that trial, rather than inferring outcomes by
re-scanning the shared evidence store after the fact — a design chosen
specifically to avoid a double-counting failure mode an earlier internal
version of the comparison tooling exhibited when a single test case
produced evidence records at multiple pipeline stages
(`docs/Technical-Design-Document.md` §7d–§7e). Aggregate statistics,
including Wilson confidence intervals for proportions and closed-form
confidence intervals for means, are computed by `evaluation/report.py`;
both were independently cross-checked — the proportion-CI logic against
a third-party implementation (`statsmodels.stats.proportion.
proportion_confint`), the mean-CI logic against an independently derived
closed-form computation — with 33 dedicated tests, not assumed correct
because the formulas "look standard" (`docs/Research-Paper-Outline.md` §4
objection 9).

## 6. Results

*[Not yet drafted. Pulls from `evaluation/results/` — the four-stack
100%/0% detection results, the TUF baseline comparison, and the ablation
study. State any case where detection happened earlier/later than
hypothesized explicitly, per the outline's structure guidance, rather
than only reporting confirmations.]*

## 7. Discussion

*[Not yet drafted.]*

## 8. Limitations

*[Not yet drafted. Must include, at minimum, verbatim or near-verbatim:
the no-human-review disclosure drafted in
`docs/Research-Paper-Outline.md` §4 objection 7 (2026-08-07); the
simulated-uplink/CCSDS-realism scoping (objection 2); the Docker-timing
confound (objection 10); the "same author designed the lock and the
lockpick" recursion (objection 7's core point, distinct from the
human-review sub-point).]*

## 9. Conclusion

*[Not yet drafted.]*

---

## AI-use disclosure statement

*[Use the drafted text in `docs/Research-Paper-Outline.md` §7 verbatim,
adapted to Computers & Security's required placement: a section titled
"Declaration of generative AI and AI-assisted technologies in the writing
process," immediately above the references.]*

## Data / code availability statement

*[Use the drafted text in `docs/Research-Paper-Outline.md` §8, dropping
the "request from the corresponding author" sentence only if submitting
to a double-blind venue — not applicable for Computers & Security.]*
