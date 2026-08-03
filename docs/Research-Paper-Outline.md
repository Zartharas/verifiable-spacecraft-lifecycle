# Research Paper Outline & Venue Strategy

**Last updated:** 2026-08-02
**Status:** Draft v1

## 1. Central claim

Not: "we added an SBOM and signature to spacecraft software."
Instead: a controlled, comparative evaluation of six additive software
supply-chain assurance levels (S0–S5) for spacecraft flight software
lifecycle management, measuring detection accuracy, recovery success, and
operational overhead under spacecraft-relevant constraints (link
latency/loss, autonomous recovery, no live human-in-the-loop during
anomalies) that existing terrestrial frameworks (SLSA/in-toto/TUF) do not
directly address.

## 2. Proposed structure (IMRaD-style, adjust per venue)

1. **Introduction** — motivate with real supply-chain incidents
   (terrestrial: SolarWinds-class; spacecraft: cite any public post-mortems
   or near-misses if available), state the gap (no measurable comparison of
   assurance levels under spacecraft constraints), state the contribution.
2. **Background / Related Work** — SLSA, in-toto, Sigstore, TUF, OSCAL;
   spacecraft software engineering and cFS; existing spacecraft security
   literature (CCSDS security working group outputs, any prior spacecraft
   supply-chain papers found via lit review — verify via search, don't
   cite from memory).
3. **Threat Model** — pulls from Threat-Model.md; formalize threat actors
   and the S0–S5 ladder.
4. **System Design** — pulls from Technical-Design-Document.md and
   Pipeline-Flow-Document.md.
5. **Evaluation Methodology** — the 15 test cases, the metrics, the
   experimental protocol (repeated trials, statistical treatment).
6. **Results** — per-condition comparison tables/plots; explicitly discuss
   any test cases where detection happened earlier/later than hypothesized.
7. **Discussion** — what the marginal cost/benefit of each assurance layer
   implies for real mission design tradeoffs; honest treatment of what
   doesn't generalize beyond the simulated environment.
8. **Limitations** — simulated uplink (not RF-accurate), single/limited
   software stack (unless Phase 6 completed), no real spacecraft hardware,
   no human-factors evaluation of the ground authorization workflow.
9. **Conclusion**

## 3. Venue strategy (from prior analysis)

**Best target sequence:**
1. Build the end-to-end pipeline (Phases 0–5 of Implementation-Plan.md)
2. Publish an initial system + controlled evaluation at a development
   venue: IEEE Aerospace Conference or NDSS SpaceSec
3. Incorporate feedback, add stronger baselines and independent
   reproduction, and — if pursuing top-tier venues — a second software
   stack (Phase 6)
4. Submit to a primary archival target: AIAA Journal of Aerospace
   Information Systems, or Computers & Security
5. Only attempt IEEE TDSC, IEEE TSE, or ACM TOSEM if the contribution
   demonstrably generalizes beyond a single spacecraft software stack —
   these require a formal assurance model, defined evidence/trust
   properties, and evaluation beyond one cFS pipeline.

**Primary targets:**
- AIAA Journal of Aerospace Information Systems (strongest natural fit —
  aerospace software engineering, V&V, embedded systems, mission
  assurance, case studies welcome)
- Computers & Security (frame around secure software lifecycle, audit
  evidence, integrity, operational security — explicitly do NOT frame as
  a new cryptographic-signature contribution, journal excludes cryptology
  as a primary subject)
- IEEE Transactions on Aerospace and Electronic Systems (if the paper
  demonstrates integration/operational value within a full
  spacecraft/ground system, not just CI/CD tooling)
- Journal of Space Safety Engineering (if emphasis is on preventing unsafe
  deployment and proving trusted recovery)

**Stretch targets (require generalization beyond one stack):**
- IEEE Transactions on Dependable and Secure Computing — needs formal
  assurance model, defined evidence/trust properties, tested
  compromise/rollback cases, demonstrated reproducibility, applicability
  beyond one satellite software stack
- IEEE Transactions on Software Engineering — needs a genuinely
  generalizable SE method (provenance, update assurance, traceability,
  reproducible builds, continuous authorization) with strong evaluation
  beyond a single cFS pipeline
- ACM Transactions on Software Engineering and Methodology — needs a
  reusable methodology + significant empirical evaluation, not an
  aerospace case study framing
- ACM Transactions on Cyber-Physical Systems — appropriate if the paper
  tightly links software provenance/update trust to physical spacecraft
  states and mission assurance

**Development venues / practitioner feedback (not archival, or
lower-stakes first outings):**
- IEEE Aerospace Conference
- AIAA SciTech or ASCEND
- NDSS SpaceSec
- IEEE International Symposium on Software Reliability Engineering (if
  emphasizing failure/recovery/reliability)
- ACM/IEEE ICSE workshops → followed by full journal submission
- NIST / OSCAL community events (practitioner feedback, not archival)
- CCSDS security and software-related working groups (standards-oriented
  feedback)

## 4. Reviewer objections to pre-empt (from prior devil's-advocate pass —
keep these in mind while writing every section, not just Discussion/Limitations)

1. **"This is just SLSA/in-toto/Sigstore/TUF applied to a new domain."**
   Answer must rest on spacecraft-specific constraints changing the
   engineering problem, not just the deployment target. Make this
   argument explicitly and early, not just in the discussion section.
2. **"Your simulated uplink isn't realistic."** Either model it faithfully
   against CCSDS/DTN assumptions, or scope the paper honestly as
   "terrestrial-analog pipeline with spacecraft-motivated constraints" and
   say so plainly in Limitations. Do not claim spacecraft realism that
   hasn't been earned.
3. **"Single stack, doesn't generalize."** Caps venue ceiling absent
   Phase 6. Be upfront about this rather than overclaiming.
4. **"Where do these baseline numbers come from?"** Every effort/overhead
   metric needs a defined, defensible baseline (what does S0 represent
   operationally?) before it's presented as a finding.

## 5. Literature review tracking

Use this section to log papers found during lit review (via arXiv/Semantic
Scholar/Google Scholar tools) that are directly relevant, so citations
aren't re-derived from memory. Update as research progresses.

| Paper | Relevance | Status |
|---|---|---|
| *(none logged yet)* | | |
