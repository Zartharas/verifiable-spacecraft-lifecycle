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

*[Not yet drafted. Pulls from: TUF/in-toto/SLSA/Sigstore/OSCAL (cited per
§6's flag above); spacecraft/CCSDS software security literature — see
`docs/Research-Paper-Outline.md` §6's verified peer-reviewed shortlist
(Manulis et al. 2020, Ahmad et al. 2022, Kang et al. 2024, Pan et al.
2023, Usman et al. 2026, Qureshi et al. 2021, Sahlmann et al. 2021,
Ganesan/McComas et al. 2012, Gonzalez et al. 2019); NASA cFS engineering
literature. Each citation's specific claim needs to be checked against the
actual paper text before use, not assumed from its abstract.]*

## 3. Threat Model

*[Not yet drafted. Pulls from `docs/Threat-Model.md` §§1–2: the S0–S5
ladder and the six threat actors, with the explicit out-of-scope list
(RF-layer attacks, physical tampering, insider root access to the signing
HSM) stated plainly rather than left implicit.]*

## 4. System Design

*[Not yet drafted. Pulls from `docs/Technical-Design-Document.md` and
`docs/Pipeline-Flow-Document.md`.]*

## 5. Evaluation Methodology

*[Not yet drafted. Pulls from the 15-case attack matrix
(`docs/Threat-Model.md` §3), the metric definitions and S0-as-baseline
decision (`docs/PRD.md` §10), and `evaluation/experiment.py`'s actual
implementation — every metric claim must trace to a specific measured
quantity, not a described intention.]*

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
