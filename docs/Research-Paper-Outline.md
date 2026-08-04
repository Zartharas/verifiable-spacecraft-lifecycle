# Research Paper Outline & Venue Strategy

**Last updated:** 2026-08-03
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

**2026-08-03 note — step 3's precondition is now largely met.** Phase 6
(second software stack, F´) and Phase 7 (real-framework statistical
validation against both real cFS and real F´ builds, not stand-in stubs)
are both complete as of this date, with matching 100%/0-FP-FN results
across both real stacks (see STATUS.md, ISSUES-AND-FIXES-LOG.md
ISSUE-007/008, and `evaluation/results/phase6_report_{cfs-real,fprime-real}.md`).
This is worth weighing against the original 5-step sequence: the paper may
now have enough generalization evidence to skip straight to a primary
archival target (step 4) rather than a development-venue outing first
(step 2), *if* the writing and self-critique pass (multi-expert-analysis,
methodology/novelty/reproducibility/ethics/clarity lenses per the
academic-publishing skill) hold up. This is flagged as an observation for
your judgment, not a decision made here — a development-venue outing still
has real value (cheap, fast feedback before an archival submission) even
when not strictly required to clear the generalizability objection.

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

## 5. Venue submission requirements (researched 2026-08-03, via live web search — verify again close to actual submission, these details change)

General caveat: everything below was pulled from each venue's current author-guidance
pages this session. Journal impact factors/quartiles are cited because the
academic-publishing skill flags them as time-sensitive and not something to trust from
memory — confirm again shortly before submission since they update annually. Items
marked **[UNVERIFIED — could not confirm]** need a direct check of the primary source
(often a PDF template gated behind a submission portal) before being treated as fact.

### Primary targets

**AIAA Journal of Aerospace Information Systems (JAIS)**
- Scope confirmed to fit well: aerospace systems/software engineering, V&V of embedded
  systems, systems health management, mission assurance, case studies explicitly
  welcomed. Signal processing/electromagnetics/networking-hardware topics are explicitly
  *out* of scope (not a concern for this paper).
- Submission via ScholarOne Manuscripts (`mc.manuscriptcentral.com/aiaa`); all co-authors
  must complete an Author Verification Form before the submission counts as complete —
  build this step into the submission timeline, it's not instantaneous.
- **Page/length limit — now confirmed (2026-08-03, via AIAA's "Journal Page Limits and
  Word Count Guidelines" PDF, read directly in-browser):** Regular Full Article 7–10
  published pages (≈10,000–12,000 words); Technical Note 1–3 pages (≈1,700–4,000
  words); Survey Paper 10–13 pages (≈10,000–20,000 words). This paper should target the
  Regular Full Article band. Manuscript formatting confirmed separately: 10-point type,
  double-spaced, single-column, abstract 100–200 words (one paragraph, no acronyms/
  numerical references), title ≤12 words.
- Each author is expected to review three other submitted manuscripts as a reciprocal
  obligation — a real (if soft) commitment worth knowing about ahead of submission.
- **Preprint/self-archiving policy — now confirmed:** authors may post draft
  manuscripts anywhere, anytime, including preprint servers (arXiv), before submission;
  after acceptance, the accepted (peer-reviewed) manuscript version may go to arXiv and
  institutional repositories, but the final AIAA-formatted/copyedited version may not.
  This directly answers the "preprint posting not checked" gap noted below for AIAA
  specifically.
- Current metrics (2026): Impact Factor 1.5, SJR 0.6, quartile Q2. Editor-in-Chief Ella
  M. Atkins (Virginia Tech).
- **AI-use policy — checked AIAA's Publication Policies page directly (2026-08-03):
  still no AIAA-specific generative-AI disclosure policy found there** (that page
  covers self-archiving, copyright, ethics, name changes, numerical-accuracy standards
  — no AI-use section). Genuinely **[UNVERIFIED]**, not just unsearched — the safe
  default is to follow IEEE-style disclosure practice (below) even though AIAA is the
  publisher here, and confirm directly with AIAA (arcsupport@aiaa.org) before
  submission.

**Computers & Security (Elsevier)**
- Guide for Authors (ScienceDirect) requires: abstract ≈250 words, a Highlights list, a
  graphical abstract, a CRediT author-contribution statement, and a data availability
  statement. Editors reportedly screen new submissions against this checklist before
  peer review — get all four right in the first draft.
- Elsevier's generative-AI policy (applies here): authors may use AI tools to support
  drafting, but never as a substitute for human critical thinking/expertise, and always
  with human oversight. A disclosure statement is **mandatory** if generative AI/AI-
  assisted tools were used: a section titled "Declaration of generative AI and
  AI-assisted technologies in the writing process," placed immediately above the
  references, naming the tool, its purpose, and the extent of human oversight. AI tools
  may **not** be used by reviewers/editors in the evaluation process (not our concern as
  authors, but relevant if any of us also review for this venue later). Authors remain
  fully accountable for content regardless of AI assistance used.
  This paper *will* need this declaration — Claude has been used throughout the build
  and (per this task) the paper-prep research; document that honestly rather than omit
  it.
- Explicit reminder from the original venue-strategy analysis still holds: frame this
  as secure software lifecycle / audit evidence / operational integrity, not as a new
  cryptographic-signature contribution — the journal excludes cryptology as a primary
  subject area.
- Current metrics (2026): Impact Factor 6.8, SJR 1.445, quartile Q1 — meaningfully
  more competitive than JAIS; this is the higher-ceiling / higher-bar primary target.

**IEEE Transactions on Aerospace and Electronic Systems (IEEE TAES)**
- All authors need an ORCID — set this up in advance if not already done, it's now a
  submission blocker for IEEE journals generally, not just TAES.
- Two contribution types: full "regular papers" (thorough treatment) vs. shorter
  "correspondence" items (same quality bar, narrower scope) — decide which framing
  fits before drafting rather than after.
- Hybrid OA model: traditional (no author charge, subscription-gated) or open access
  (IEEE's OA article processing charge is $2,800 USD, independent of paper
  type) — a real cost to budget for if OA is wanted/required by a funder, but the
  no-cost traditional route is available if the paper isn't tied to a funder OA
  mandate.
- Typical review cycle cited at ~60 days.
- IEEE's general generative-AI disclosure policy applies (see below, shared across
  IEEE venues) — content generated by AI (text, figures, images, code) must be
  disclosed in the Acknowledgments section, naming the AI system and which sections
  used it, with a brief explanation of how it was used. AI cannot be a co-author.
  Editing/grammar-only AI use is "generally outside the intent" of the policy but
  disclosure is still recommended.
- Current metrics (2026): Impact Factor 5.7, quartile Q1.

**Journal of Space Safety Engineering (JSSE, Elsevier, published for IAASS)**
- Fully open access (no reader paywall) and **no author charge** — authors retain
  copyright. This changes the cost calculus versus TAES's OA option — worth
  highlighting to the user as JSSE being the only primary target that's OA at zero
  direct cost.
- Same Elsevier generative-AI disclosure policy as Computers & Security applies (see
  above) — same "Declaration of generative AI..." section required if used.
- Quarterly publication cadence; scope centers on space safety engineering broadly —
  good fit if the paper's framing leans toward "preventing unsafe deployment /
  proving trusted recovery" per the existing venue-strategy note above.
- Current metrics (2026): Impact Factor 1.8, quartile Q3 — the least competitive of
  the four primary targets, consistent with it being the safety-net option in this
  set rather than the reach option.

### Development venues (checked as requested; two most concretely relevant)

**IEEE Aerospace Conference (AeroConf)**
- AeroConf 2027: 48th edition, Big Sky, Montana, March 6–13 2027; technically
  co-sponsored by AIAA and the PHM Society. Scope fits well: aerospace systems/
  science/technology, systems engineering and management science in the aerospace
  industry.
- **Full submission process now confirmed (2026-08-03, walked the live process page
  in-browser, `aeroconf.org/paper-submission`):** (1) create an aeroconf.org account,
  co-authors need their own accounts too; (2) submit an abstract before ~Jul 1 for
  timely review; (3) on abstract approval, write the paper from the official
  Word/LaTeX template; (4) obtain required publication-release approvals (relevant if
  any institutional/export-control sign-off is needed — worth flagging early given the
  spacecraft-security subject matter); (5) submit the complete PDF by the **Paper
  Submission Deadline, Oct 2** — draft/incomplete/improperly formatted papers are
  **not reviewed, with no appeal or secondary review**; (6) review comments returned
  by mid-November; (7) respond to review comments, submit the verified final paper by
  the **Final Submission Deadline, Jan 8**; (8) complete IEEE's electronic copyright
  transfer (eCF) before Xplore publication. The exact page limit itself is set inside
  the downloadable Word/LaTeX template (a binary file gated behind the submission
  site) — attempted to pull and parse it directly this session but the fetch failed
  both via the standard fetch tool and a direct sandbox download (network egress to
  aiaa.org/aeroconf.org's CDN was inconsistent from the sandbox); still
  **[UNVERIFIED — could not confirm exact page limit]**, download
  `aeroconf.org/cms/content_attachments/76/download` (the "2027 docx template" link)
  directly on your own machine to check.
- No-show policy (general IEEE conference policy, applies here): IEEE reserves the
  right to pull an accepted paper from IEEE Xplore distribution if it isn't actually
  presented at the conference (in person or via their Electronic Presentation Hall) —
  budget for someone to actually attend/present if this route is taken.
- Not archival in the same sense as a journal — matches its role in the existing
  venue-strategy doc as a development/feedback venue rather than the primary target.

**NDSS Workshop on the Security of Space and Satellite Systems (SpaceSec)**
- Full current CFP found (SpaceSec 2026, co-located with NDSS 2026): Short papers
  (max 4 pages) or Long papers (max 8 pages), NDSS double-column template, page
  limits exclude bibliography/appendices (up to 2 extra pages for long, 1 for short).
  Double-blind review — submissions must be anonymized.
  2026 dates already passed (submission deadline was 16 Nov 2025; workshop ran 23
  Feb 2026) — **the 2027 SpaceSec CFP is not yet published**; confirmed live
  (2026-08-03, `ndss-symposium.org/ndss2027/submissions/`) that NDSS 2027's own
  general Call for Papers is marked "OPENS SOON," specifically **15 August 2026**,
  and the co-located-workshop proposal call (which SpaceSec's own CFP would follow)
  is open now, due 1 Sept 2026. NDSS 2027 itself is in Seoul, workshops 22 and 26
  March 2027. Practical takeaway: expect the actual SpaceSec 2027 CFP to appear
  sometime after workshop proposals are accepted, plausibly September–October
  2026 — worth checking back then rather than waiting on this doc.
- Scope is a strong direct fit: "Secure Satellite Software/Hardware Development,"
  "Supply Chain Security for Space Mission Components," and "Legacy Space System
  Security Analysis" are named topics of interest — arguably a better scope match
  than AeroConf for this paper's specific supply-chain-assurance angle.
- Accepts multiple submission categories beyond "Research Paper" that could suit an
  earlier-stage submission if desired: Position Paper, Experience Paper, Preliminary
  Work Paper, Extended Work Paper.
- No separate generative-AI policy found for SpaceSec specifically — falls under
  NDSS/Internet Society's general conference conduct and originality rules (no
  simultaneous multi-venue submission, no previously published work, no plagiarism);
  **[UNVERIFIED]** whether a specific AI-disclosure clause exists — check the
  eventual 2027 CFP page directly.

### Cross-cutting notes

- **Generative-AI disclosure will very likely be required regardless of venue** —
  every venue checked here (Elsevier's two journals, IEEE's journal, and IEEE's
  general conference policy) has an explicit, mandatory AI-use disclosure
  requirement as of 2026. Given how this project was built (Claude used throughout
  design, debugging, and now paper-prep research), plan for a substantive, honest
  disclosure statement as a required paper section, not an afterthought — draft it
  alongside the paper rather than bolting it on at submission time.
- **Preprint posting** — not checked venue-by-venue this pass; general Elsevier and
  IEEE norms usually permit arXiv-style preprints, but confirm per-venue before
  posting one, since it varies and this wasn't directly verified here.
- **ORCID** — get one now (all authors) if not already held; IEEE journals require
  it, and it's good practice for every venue on this list regardless.

## 6. Literature review tracking

Use this section to log papers found during lit review (via arXiv/Semantic
Scholar/Google Scholar tools) that are directly relevant, so citations
aren't re-derived from memory. Update as research progresses.

| Paper | Relevance | Status |
|---|---|---|
| *(none logged yet)* | | |
