# Measuring Software Supply-Chain Assurance for Spacecraft Flight Software: A Controlled, Comparative Evaluation

**Status:** Draft v0.3 — full first draft, all nine sections plus both
required disclosure statements, written section by section with an
integrity/citation self-check after each one rather than in one pass (see
STATUS.md's 2026-08-07 entries for what each check caught and fixed), then
run through a five-lens self-critique pass (methodology & statistics,
novelty & contribution, reproducibility, research ethics, clarity &
argument) with all seven findings addressed: the AI-use disclosure
statement corrected to name the actual tools used per red-team pass; the
ablation and adaptive-attacker citations extended to all four target
stacks, not just two; a new explicit Limitations bullet on TUF being the
only empirically baselined comparison framework; the promised evidence-
count/traceability metrics from Section 5.2 actually reported in Section
6.1; a deterministic-vs-stochastic framing paragraph added to Section 5.3
so Wilson-CI detection rates aren't misread as characterizing outcome
randomness; an honest multi-environment execution-environment disclosure
added to Section 5.3 (results were not gathered on one controlled
benchmark machine); and every bracketed cross-reference placeholder
resolved to a real section number now that the structure is stable.
**Not yet done:** several citations (marked inline) still need full-text
verification rather than abstract-level confidence, the exact per-pass
AI-tool identity for the four red-team reviews is still an approximate
recollection pending the author's own records (flagged inline in the
AI-use disclosure statement), and precise hardware specifications for the
execution environments used are still unconfirmed. Treat this as a
complete, self-critiqued draft to do a final verification pass on before
submission, not yet a finished manuscript.

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
S5, Section 3) — and measured what each additional
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
   8).

The remainder of this paper is organized as follows: Section 2
situates this work against SLSA/in-toto/TUF/Sigstore and prior spacecraft
software security literature; Section 3 formalizes the
threat actors and the S0–S5 ladder; Section 4 describes the
pipeline implementation; Section 5 describes the
attack matrix, metrics, and experimental protocol; Sections 6 and 7 present and interpret the findings; Section 8
states plainly what this evaluation does not establish; Section
9 closes.

---

## 2. Background / Related Work

**Note on citation treatment in this section, per the 2026-08-07 flag in
`docs/Research-Paper-Outline.md` §6:** SLSA, in-toto, Sigstore, TUF, and
OSCAL are cited below via their own specifications/project sites, as the
systems this project's design is built from and measured against — the
same treatment already given to TUF in the real-baseline comparison
(Section 5; `docs/Threat-Model.md` "Phase 8
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
3 and the real-baseline comparison against an unmodified
python-tuf deployment (Section 6.4) make this gap
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
constraints Section 3 treats as first-class, and neither
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
a standardized attack matrix (Section 5), produces
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
  8 rather than presented as RF-accurate.
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
stated expectation is itself a result worth reporting (Section 6
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
Sections 6/7: state plainly, per objection 5 in
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
  Section 8 on the related Docker-launch-overhead confound
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
trials per case in the results reported in Section 6, following
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

**What varies across the 30 trials, stated precisely.** Each trial
injects the same fixed scenario input against a deterministic code path,
so the detect/no-detect outcome itself is not a random variable in the
way a Bernoulli-trial framing might suggest — it is a repeated execution
of the same logic against the same input, not 30 independent draws from
an uncertain process. What genuinely varies trial to trial is execution
timing (observed directly in the raw per-trial data, e.g., elapsed times
ranging roughly 0.80–1.07 seconds across ablation trials on identical
inputs), reflecting real OS-scheduling and environment variance rather
than a fixed, memorized value. The Wilson confidence intervals reported
in Section 6 for detection/success rates are therefore best read as a
formally correct treatment of a rate observed over repeated executions,
not as evidence that detection *could* have gone the other way on any
given trial absent a code change — whereas the timing confidence
intervals are a meaningful characterization of genuine run-to-run
variability. This distinction is stated here explicitly so the two kinds
of interval in Section 6 are not read as epistemically equivalent.

**Execution environment, stated honestly rather than omitted.** Results
in this paper were not gathered on a single, controlled benchmarking
machine with recorded hardware specifications. The stand-in stub-artifact
results (Section 6.1) were produced in a cloud-based Linux development
sandbox; the two real, unmodified NASA/JPL framework results (Section
6.2 onward) required Docker and were produced on the author's own macOS
machine, since the sandbox environment had no Docker available. Exact
CPU, memory, and OS-version specifications were not captured at
measurement time for either environment. [TODO before submission: capture
and report at least the author's macOS machine's specifications
retroactively if still accessible, and note the sandbox's general class
of environment, rather than leave this unspecified — full precision may
not be recoverable for the sandbox environment specifically.] The
practical consequence is that this paper's timing comparisons should be
read as meaningful *within* a given stack's own S0–S5 progression
(measured on one environment), not as precise absolute comparisons
*across* stub-artifact and real-framework results, which were measured on
different machines with different baseline performance characteristics
entirely independent of the assurance mechanisms under test.

## 6. Results

All results below are drawn directly from `evaluation/results/` (30
trials per condition/test-case combination unless noted) and are reported
per the caveats fixed in Section 5.2 — detection/success rates are 95%
Wilson score intervals, timing means are 95% normal-approximation
intervals, and every timing figure is a sandbox/local-hardware proxy, not
a flight-hardware claim.

### 6.1 Happy-path and attack-matrix detection, stand-in stub artifacts

Against both stand-in stub artifacts (the cFS-modeled C stub and the F
Prime-modeled C++ stub), happy-path success and reproducibility were 100%
(89%–100% Wilson CI, n=30) at every condition S0–S5, and all 15 attack
matrix cases were detected at a 100% (89%–100% CI) rate at their tested
condition, with zero false positives and zero false negatives in every
condition's confusion matrix (`evaluation/results/phase5_report.md`,
`phase6_report_fprime.md`). Traceability completeness — the fraction of
stages expected active at a condition that actually produced evidence —
was 100% at every condition, and mean evidence-record count per run
(the manual-evidence-processing-effort proxy defined in Section 5.2)
increases monotonically with condition: 7 records at S0, 9 at S1, 12 at
S2, 15 at S3, 17 at S4, and 21 at S5 (`evaluation/results/
phase5_summary.json`) — roughly triple the review burden at S5 relative
to S0, the expected direction stated in Section 5.2, now with the actual
measured figures rather than only the qualitative claim. Storage overhead
relative to S0 increases monotonically with condition — 0 bytes at S0,
613 bytes at S1 (SBOM),
1264 bytes at S2 (+provenance), 1631 bytes at S3 (+attestation), 1624
bytes at S4 (a 7-byte decrease from S3 — no formal significance test was
run on this specific delta, but the magnitude is consistent with S4
adding a rollback *mechanism* rather than new per-run evidence volume,
not with a meaningfully larger artifact), and 5747
bytes at S5 (+machine-readable authorization evidence, the single largest
jump in the ladder) — identical byte counts across both stub stacks,
since this metric depends on evidence-record shape, not the stub
artifact's own content.

### 6.2 Generalization to real, unmodified NASA/JPL frameworks

The same 100%/0% pattern holds against both real, unmodified flight
software frameworks (cFS `v7.0.1`, F´ `v4.2.2`): happy-path success,
reproducibility of the ablation/adaptive mechanisms under test, and
attack-matrix detection are structurally identical to the stub-artifact
results (`evaluation/results/phase6_report_cfs-real.md`,
`phase6_report_fprime-real.md`). One real, measured asymmetry emerged in
build reproducibility specifically, not in any assurance-mechanism
result: two independent from-scratch builds of the real F´ binary were
byte-for-byte identical, while two independent builds of the real cFS
binary differed in exactly 22 of approximately 915,000 bytes — isolated
precisely (via `cmp -l` and a `strings` diff, not assumed) to a build
timestamp string embedded by cFS's own build system at two byte offsets,
plus a downstream 20-byte ELF build-ID hash that changes as a consequence
of that timestamp. Every other byte of the cFS binary, including all
flight-software logic, was identical across both builds. This is reported
as a genuine finding about the two real frameworks' own build systems, not
a defect in this project's pipeline, and it means the "reproducibility"
metric's claim differs slightly by framework: fully bit-identical for F´,
identical-modulo-a-known-and-explained-non-functional-difference for cFS.

### 6.3 A hypothesis-vs-implementation divergence worth reporting explicitly

Test case #12 ("stale attestation") was hypothesized in the threat model
(Section 3.2; `docs/Threat-Model.md` §3) to be first detected at S3, the
condition where onboard attestation itself activates. The actual
evaluation harness tests this case at condition S4 instead, measuring
`time_to_trusted_restoration` rather than a pure S3-level detection time
(`evaluation/experiment.py::scenario_12`). This is a deliberate
implementation choice, not a bug or a failed hypothesis: `scenario_12`
establishes a confirmed S4 baseline, then injects a backdated attestation
timestamp and measures whether the system not merely *flags* the stale
attestation but actually completes a rollback in response
(`rollback_outcome == "rolled_back"`). In other words, the implemented
test is a strictly stronger claim than the original hypothesis — it
measures recovery, not just detection — but it means the "S3" entry in
the attack matrix table (Section 5.1) should be read as "the mechanism
that makes detection possible activates at S3," not as "this specific
trial was measured at S3." This distinction is stated here explicitly
rather than left as a quiet inconsistency between Sections 3, 5, and 6,
consistent with this paper's stated intent (Section 3.2) to report
hypothesis divergences rather than reconcile them silently.

### 6.4 Real-baseline comparison against unmodified TUF

Of the 15 attack matrix cases, an unmodified, real upstream `python-tuf`
deployment (Section 5; `evaluation/baselines/tuf_baseline.py`) has a
plausible native detection mechanism for exactly 3: case #6 (in-transit
tampering, via TUF's target hash/length verification), case #7 (revoked
signing key, via TUF's key-revocation/rotation mechanism), and case #9
(downgrade attempt, via TUF's version-monotonicity protection). All three
were caught at 30/30 (100%) trials
(`evaluation/results/phase8_tuf_baseline.json`) — a result that confirms
TUF works correctly for the guarantees it actually makes, and is reported
as exactly that, not as evidence that TUF is "weak." The remaining 12
cases, including 9 that are load-bearing parts of this project's own
S1–S5 ladder (SBOM, build provenance, dependency-vulnerability scanning,
authorized-builder identity, policy/configuration evaluation,
installation-state management, runtime health checking, onboard
attestation, ground/spacecraft state reconciliation, and rollback/recovery
management — case #12's metadata-expiration mechanism is noted as a
related but non-equivalent partial overlap, not scored as coverage), have
no corresponding concept anywhere in TUF's specification. This is the
paper's primary measured evidence for the claim that spacecraft-relevant
supply-chain assurance is not simply "TUF applied to a new domain": the
majority of what this project's ladder measures sits entirely outside an
already-mature terrestrial framework's stated scope, not inside it and
merely unimplemented.

### 6.5 Ablation study: per-mechanism isolation

To test whether each mechanism's contribution holds when it alone is
disabled from an otherwise fully-active condition — rather than only
observed cumulatively as conditions are added — six ablation cases each
disable exactly one mechanism (SBOM, provenance, onboard attestation,
trusted rollback, and machine-readable authorization, the last tested via
two independent cases, #8 and #15) while leaving every other mechanism at
its otherwise-active condition. In every case, the baseline (mechanism
active) detection rate was 100% and the ablated (mechanism disabled) rate
was 0%, with the effect explicitly attributed to the ablated mechanism
specifically, identically across all four target stacks
(`evaluation/results/phase8_ablation_cfs.json`,
`phase8_ablation_fprime.json`, `phase8_ablation_cfs-real.json`,
`phase8_ablation_fprime-real.json`) — including both real, unmodified
NASA/JPL frameworks, not only the stub artifact this result might
otherwise be assumed to be limited to. This clean isolation — full detection
on, zero detection off, for every mechanism tested independently — is
the direct evidence for this paper's central comparative claim (Section
1): each mechanism in the ladder is doing genuine, individually
attributable work, not contributing to a detection rate that would hold
regardless of its presence.

### 6.6 Adaptive-attacker scenarios

Two scenarios combine multiple attack vectors in sequence to test whether
an attacker adapting across attempts changes the outcome: (A) a rogue
build runner combined with in-transit tampering, and (B) an interrupted
installation combined with a stale attestation. Both were caught at a
100% rate, and in both, the pipeline halted before the second vector could
be exercised (`halted_before_second_vector_rate` = 1.0), identically
across all four target stacks (`phase8_adaptive_cfs.json`,
`phase8_adaptive_fprime.json`, `phase8_adaptive_cfs-real.json`,
`phase8_adaptive_fprime-real.json`) — again including both real,
unmodified frameworks. **This result must be read
against its actual scope, not an inflated one:** these scenarios test
whether the pipeline halts on the *first* of two vectors it already has a
mechanism to detect — they are not a test of a genuinely evasive or
time-adaptive attacker who might, for instance, attempt the second vector
independently of the first, or attempt to time an attack around a
detection window. Stating this boundary here, in Results, rather than
only in Limitations, is deliberate: a reader should not come away from
this section believing more was tested than was.

## 7. Discussion

### 7.1 What the marginal-cost results imply for mission design tradeoffs

The central practical question this paper set out to answer was not
whether stronger assurance mechanisms work — Section 6 shows each does,
cleanly and individually — but what each one costs relative to what it
buys. Read against Section 6.1's overhead figures, a mission designer
choosing among conditions has a genuinely graduated set of options rather
than a single "secure or not" decision: S1 and S2 (SBOM and provenance)
add a few hundred bytes each and, per the stub-artifact happy-path timing
in Section 6.1, roughly 10–25 milliseconds of cumulative timing overhead
over the S0 baseline in this sandbox environment — closing the entire
class of build-integrity
and dependency-visibility gaps that both this paper's own attack matrix
and Section 6.4's TUF comparison show a signature-only baseline has no
visibility into at all. S5's authorization evidence is, by a wide margin,
the most expensive single step in the ladder — more than triple any other
mechanism's storage footprint — and correspondingly the one whose
cost/benefit case rests most heavily on how much a mission actually values
machine-readable, auditor-consumable evidence over the cheaper mechanisms
already catching the same underlying attacks in this evaluation's specific
attack matrix (case #8, prohibited-but-signed configuration, is the one
case in this matrix S5's policy check is *uniquely* positioned to catch
here; cases #13 and #15 route through S5 as well, but represent a
different mechanism — inventory/telemetry reconciliation — bundled into
the same condition). This suggests a real, if narrow, design lever: a
mission with tight storage/link-budget constraints and low concern about
insider-approved-but-prohibited configurations could reasonably stop at
S4 without giving up detection coverage this specific attack matrix
tests for; a mission where auditability to a third party (a regulator, a
launch-services customer, a multi-stakeholder mission) is itself a
requirement would find S5 worth its cost regardless of the marginal
detection-rate argument, since machine-readable evidence is doing
compliance work, not just detection work.

### 7.2 What the TUF gap implies, and what it doesn't

Section 6.4's finding — that 12 of 15 attack matrix cases have no
corresponding concept in TUF's specification at all — is this paper's
strongest evidence against the "just SLSA/in-toto/TUF in a new domain"
framing (Section 1; `docs/Research-Paper-Outline.md` §4 objection 1), but
it is worth being precise about what the finding does and does not show.
It shows that TUF, specifically, does not natively address build
provenance, SBOM/dependency visibility, installation-state management,
runtime health/attestation, or ground/spacecraft state reconciliation —
because TUF was never designed to. It does not show that no combination
of existing terrestrial tools could cover the same ground: SLSA-format
provenance generators, CycloneDX/SPDX SBOM tooling, and various runtime
attestation frameworks each address a subset of what this paper's ladder
covers, and a terrestrial system composing several of them (rather than
using TUF alone) would close some of that 12-case gap. What no single
existing framework or straightforward composition addresses, as far as
this paper's evaluation goes, is the *spacecraft-specific* combination:
autonomous rollback decisions with no live operator (S4), and structured
evidence aggregation specifically shaped for a ground/auditor consumer
who cannot inspect the artifact directly (S5). That narrower, more
defensible claim — not "no terrestrial tool does any of this" — is the
one this paper's evidence actually supports, and Section 1's framing
should be read accordingly rather than as a claim of total novelty.

### 7.3 What does and does not generalize beyond this evaluation

Section 6.2's real-framework results are genuine evidence that this
project's assurance mechanisms are not artifacts of the stand-in stubs'
simplicity — the identical 100%/0% pattern against real cFS and F´
binaries is the strongest single piece of evidence in this paper for that
specific claim. It is not evidence that the same results would hold on
flight-representative hardware, over a real CCSDS-conformant link, or
under a genuinely adaptive adversary; each of those is a different claim
requiring different evidence, and Section 8 (Limitations) states plainly
which of them this evaluation does and does not license. The cFS-vs-F´
reproducibility asymmetry found in Section 6.2 is a useful illustration of
this boundary in miniature: it is a real result about two real build
systems, discovered by direct measurement rather than assumed, and it
would have been invisible to an evaluation that only ever used the
stand-in stubs — but it is also a result specific to *these two
frameworks' current build tooling*, not a general claim about
reproducibility of spacecraft flight software as a category.

### 7.4 The ablation study's implication: mechanisms are doing individual work, not incidental work

A standing risk in any additive-ladder evaluation is that a
higher-condition detection result is actually being carried by a
lower-condition mechanism that happens to still be active, rather than by
the specific mechanism nominally under test — for instance, S5's
100% detection on case #8 could, in principle, be substantially explained
by S2's provenance check catching something adjacent, with the S5 policy
check itself contributing little. Section 6.5's ablation results directly
rule this out for every mechanism tested: disabling one mechanism from an
otherwise fully-active condition drops that mechanism's specific case from
100% to 0%, not to some intermediate rate that would suggest a different
mechanism was doing most of the real work. This is the paper's most
direct evidence that the S0–S5 ladder's individual line items are
meaningful units of assurance, not just cumulative labels on an
increasingly capable but internally undifferentiated system.

## 8. Limitations

This section states plainly what this evaluation does not establish,
rather than leaving those boundaries to be inferred from careful reading
of Sections 4–7 alone.

**Simulated uplink, not RF-accurate.** The uplink model (Section 4.2) is
loosely, order-of-magnitude informed by CCSDS-class link budgets but has
not been validated against any specific reference mission's actual
telemetry, and this project does not attempt RF/physical-layer simulation
(`docs/PRD.md` non-goals). Every result in Section 6 that touches the
uplink stage should be read as evidence about a terrestrial-analog
pipeline with spacecraft-motivated constraints (latency, loss, bandwidth
ceilings modeled as configurable parameters), not as evidence about
behavior over a real spacecraft communications link. This paper does not
claim the latter, and results should not be cited as if it did.

**Software-only attestation, not hardware-rooted.** As stated in Section
4.2, onboard attestation in this implementation is a software-held
Ed25519 signature over a measurement, not a TPM-backed hardware root of
trust. Every S3+ result in Section 6 demonstrates that the *attestation
concept* — proving what is actually running, not just what was sent —
functions correctly in this pipeline; none of them demonstrate resistance
to the specific threat a hardware root of trust exists to prevent
(exfiltration of the attestation key itself). A production system making
an attestation claim for a real mission would need real hardware backing
this project's software stub only approximates.

**Docker-launch overhead as a timing confound for the real-framework
results specifically.** The real cFS and F´ binaries (Section 6.2) run
inside Docker on the machine executing the pipeline; the persistent-process
health-check strategy (Section 4.3) that makes S3+ evaluation possible
against these binaries incurs container-launch overhead on the order of
2.4–2.6 seconds per invocation, observed directly rather than assumed.
This means the real-framework timing figures in Section 6 mix genuine
pipeline-stage cost with this infrastructure overhead, and the two are not
separated in the current results. The claim these results support is that
detection and recovery *work correctly* against real, unmodified flight
software frameworks; the claim they do not support is that the observed
timings approximate native flight-computer execution — that would require
running outside Docker, on representative hardware, which this evaluation
does not do. More of this paper's evidence base rests on this same
infrastructure than a reader might assume from the stub-artifact results
alone, since the real-framework results in Sections 6.2, 6.5, and 6.6 all
share this confound.

**Reproducibility is a claim about the stand-in stub artifacts primarily,
with one real-framework data point in each direction.** Section 6.1's
reproducibility figures are measured against the stand-in stubs. Section
6.2 adds two real, measured data points — F´ fully bit-identical across
independent builds, cFS differing in exactly 22 explained, non-functional
bytes — but this is evidence about these two specific frameworks' current
build tooling as of the versions pinned in this evaluation (cFS `v7.0.1`,
F´ `v4.2.2`), not a general claim about flight-software build
reproducibility as a property of the category.

**Adaptive-attacker scenarios test whether the pipeline halts, not
whether an attacker is genuinely evasive.** Restated from Section 6.6
because it belongs here as well: the two adaptive scenarios (Section 5.1)
confirm the pipeline halts before a second attack vector can be
attempted; they do not model an attacker who varies timing, avoids the
specific detection signatures this pipeline's mechanisms check for, or
pursues the second vector independently rather than in the fixed sequence
tested. A reader should not extend this paper's adaptive-attacker results
to a claim of resistance against a genuinely adaptive or evasive
adversary.

**Only TUF was empirically baselined; SLSA, in-toto, and Sigstore were
not.** Section 6.4's measured comparison, and this paper's central claim
that spacecraft-specific constraints are not addressed by "terrestrial
frameworks applied to a new domain," rests on a real-baseline comparison
against TUF specifically, not against SLSA, in-toto, or Sigstore. Section
7.2 already scopes the paper's claim narrowly for this reason — the
evidence supports "TUF specifically doesn't cover this," not "no
terrestrial tool or composition of tools could" — but that scoping is
stated here explicitly as its own limitation as well, since a reader
scanning this section specifically for this gap should find it named
plainly rather than only inferable from Discussion. A real baseline
comparison against a SLSA-conformant provenance pipeline or an in-toto
attestation chain would be a natural, concrete extension of this work.

**No completed independent human security review.** Independent
verification of this project's threat model and mitigations to date
consists of four independent, blind, AI-driven red-team review passes
(Section 3; `docs/Threat-Model.md`) and a from-scratch comparison against
an unmodified upstream `python-tuf` deployment (Section 6.4). A human
domain-expert review was requested but had not been completed at the time
of submission. This is treated as a limitation rather than a resolved
concern: AI-driven review, however methodologically structured, is not a
substitute for the judgment a human security practitioner brings,
particularly regarding which findings matter operationally and which
attacker capabilities are realistic for a spacecraft mission context. If
a human review is completed prior to publication, its findings will be
incorporated; if not, this remains an open direction for follow-on work.

**The same process that designed the threat model also designed, and
red-teamed, its own mitigations.** Distinct from the human-review gap
above: the S0–S5 ladder, its implementation, and the four red-team review
passes that pressure-tested it were all produced by the same
author-plus-AI process. The red-team passes were designed specifically to
create genuine independence within that constraint — each pass ran with a
fresh context, without access to prior findings or the existing threat
model, until after its own testing was complete — and the second, third,
and fourth passes were each scoped in part at what earlier passes had
missed, including at the fix code the process itself had produced. This
is real, disclosable independence at the level of *execution*, and it
found and led to fixes for 21 genuine defects (Section 1) that a
purely self-reviewing process, by construction, cannot be assumed to find.
It does not resolve the deeper point this objection names: no review
pass, however wide or however many rounds, was conducted by a party
outside the author-plus-AI process that built the system under review.
The strongest accurate statement available from this paper's evidence is
that this process found and fixed real, non-trivial gaps across multiple
independent-context passes, including gaps in its own prior remedies —
not that the underlying methodological concern has been resolved.

## 9. Conclusion

This paper set out to answer a narrower question than "does spacecraft
software need better supply-chain security" — namely, how much
additional assurance each of six additive mechanisms actually buys, and
at what measured cost, under constraints that make spacecraft update
failures harder to recover from than most terrestrial software failures.
The six-level S0–S5 ladder and its reference implementation make that
question answerable rather than argued: every mechanism, tested
individually via ablation (Section 6.5) and cumulatively across a 15-case
attack matrix (Section 6.1), detects what it is designed to detect at a
100% rate across four independent target software stacks, including two
real, unmodified NASA/JPL flight software frameworks (Section 6.2) — and
a real, unmodified baseline comparison against TUF (Section 6.4) shows
that 12 of those 15 cases have no corresponding concept in an
already-mature terrestrial update-security framework's specification at
all, which is measured evidence, not assertion, for this paper's central
claim that spacecraft-specific constraints change the engineering problem
rather than merely relocating it.

That claim is deliberately narrower than "no existing tool addresses
spacecraft supply-chain security" (Section 7.2) — what this paper's
evidence actually supports is that the *specific combination* this ladder
tests, autonomous recovery with no live operator plus structured evidence
for a ground/auditor consumer who cannot inspect the artifact directly,
sits outside what TUF alone, and plausibly any straightforward
composition of existing terrestrial tools, was designed to cover. Section
8 states, without qualification, what this evaluation does not license:
claims about flight-representative hardware timing, RF-accurate uplink
behavior, resistance to a genuinely adaptive adversary, or a resolved
answer to the question of whether a process can adequately audit its own
security design. Two of those boundaries — flight-hardware timing and
independent human review — are the most direct next steps for this work,
not incidental gaps; the rest (RF realism, adversarial adaptivity) mark
where this paper's contribution ends and a different, complementary study
would need to begin.

The practical upshot for a mission designer, per Section 7.1, is that the
S0–S5 ladder is not an all-or-nothing decision: the cheapest mechanisms
close an entire class of build-integrity and dependency-visibility gaps
this project's evidence shows a signature-only baseline has no visibility
into at all, while the most expensive step is worth its cost specifically
when third-party auditability is itself a mission requirement, not merely
when marginal detection rate is the only consideration. Making that
tradeoff visible and measurable — rather than leaving "how much security
is enough" as a judgment call with no comparative basis — is this paper's
contribution to a domain that has, to date, applied far less empirical
scrutiny to its own software update assurance than the consequences of
getting it wrong would seem to warrant.

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
