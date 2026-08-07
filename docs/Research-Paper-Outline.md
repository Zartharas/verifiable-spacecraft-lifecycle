# Research Paper Outline & Venue Strategy

**Last updated:** 2026-08-04
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

**2026-08-07 note — decision made, informed by item 7 no longer having a
human-review component before submission.** With the colleague review no
longer gating submission (see item 7's update below and STATUS.md), the
open question above is resolved in favor of the development-venue outing
first, not skipping to a primary archival target. Reasoning: the paper's
strongest remaining answer to "who verified this besides the people who
built it" is currently two AI-driven red-team passes plus a from-scratch
python-tuf baseline — real, disclosable evidence, but weaker than a human
domain-expert review, and a security-adversarial primary venue (Computers
& Security, TDSC-tier stretch targets) is exactly where a reviewer is most
likely to press on that specific gap. A development venue's own peer
review then becomes the first real independent human check on this work,
which is a more organic fix than either waiting indefinitely on the
colleague or submitting to a top venue with a disclosed gap in the
weakest-defended part of the methodology. **Revised sequence for this
round:** submit to IEEE Aerospace Conference (AeroConf) or NDSS SpaceSec
first — SpaceSec is arguably the better scope match (supply-chain-security
topics named explicitly) but its 2027 CFP isn't published yet (expected
~Sept–Oct 2026, per § 5); AeroConf's Oct 2 deadline is the more concrete
near-term option if timing matters. AIAA JAIS remains a reasonable direct
primary-target alternative if a development-venue round is skipped for
timing reasons — its Q2/less-adversarial reviewer culture is a materially
softer landing for a disclosed no-human-review limitation than Computers &
Security or the stretch targets. Hold Computers & Security and the
TDSC/TSE/TOSEM stretch targets for a revision after this round, ideally
once either the colleague's review does land or the development venue's
own reviewers have served as the first real independent human check.

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

## 4. Reviewer objections to pre-empt (last revised 2026-08-04 — see the
2026-08-03 rejection-risk review and 2026-08-04 reassessment below for how
this list evolved; keep these in mind while writing every section, not
just Discussion/Limitations)

1. **"This is just SLSA/in-toto/Sigstore/TUF applied to a new domain."**
   Answer must rest on spacecraft-specific constraints changing the
   engineering problem, not just the deployment target. Make this
   argument explicitly and early, not just in the discussion section.
   **Sharpened, 2026-08-04:** this objection gets much stronger without a
   real baseline — see item 6 below, still open.
2. **"Your simulated uplink isn't realistic."** Either model it faithfully
   against CCSDS/DTN assumptions, or scope the paper honestly as
   "terrestrial-analog pipeline with spacecraft-motivated constraints" and
   say so plainly in Limitations. Do not claim spacecraft realism that
   hasn't been earned.
3. ~~"Single stack, doesn't generalize."~~ **Resolved, Phase 6/7/8
   (2026-08-03/04).** Now four stacks (two stand-in artifacts, two real
   NASA frameworks), with matching results not just on the original 15
   attack cases but on a 3-mechanism ablation study and 2 combined-vector
   adaptive-attacker scenarios, all at n=30. Superseded by item 7 below —
   generalization is now demonstrated across *stacks*, but not across
   *evaluators* or *independent tooling*.
4. **"Where do these baseline numbers come from?"** Every effort/overhead
   metric needs a defined, defensible baseline (what does S0 represent
   operationally?) before it's presented as a finding.
5. **"Your 100% detection rate just means the test suite always
   trips."** (Identified 2026-08-03, the single biggest exposure at the
   time.) **Materially strengthened, 2026-08-05:** `disable_mechanisms`
   is now threaded through `ground_authorization.ground_auth.authorize()`
   and `onboard_verification.onboard.verify_received_bundle()`, not just
   `pipeline.py`'s own gating — closing the scope gap this objection
   originally flagged. The ablation study now covers 5 of 6 mechanisms
   (`sbom`, `provenance`, `onboard_attestation`, `trusted_rollback`,
   `machine_readable_authorization` — including a second scenario for
   the S5 policy check specifically, test case #8), all showing the same
   clean 100%-active / 0%-ablated isolation as the original 3. `signature`
   remains excluded, with a stated principled reason (it's the one
   mechanism active at every condition including the S0 floor, never
   itself gated by `cond.active()` in the implementation) rather than an
   unaddressed gap. See Threat-Model.md "Phase 8 ablation study" update,
   2026-08-05. **Confirmed at full scale, 2026-08-05:** user re-ran the
   study at the standard `N_TRIALS = 30` against all four stacks (`cfs`,
   `fprime`, `cfs-real`, `fprime-real`) — identical 100%/0% isolation on
   all 6 cases across every stack, including the real cFS/F´ binaries.
   These are the citable numbers for the paper; the sandbox's earlier
   reduced-trial verification run (n=10/n=5) is superseded. The
   adaptive-attacker
   scenarios are unchanged by this work: they still test "does detection
   halt the pipeline," not a genuinely evasive or time-adaptive attacker
   — state that scope boundary explicitly rather than imply full
   coverage.
6. **"Where's the comparison against an actual SLSA/in-toto/TUF
   pipeline?"** (New, 2026-08-04.) The paper's central claim — that
   terrestrial frameworks don't address spacecraft-specific constraints —
   is currently asserted, not measured. No real off-the-shelf tool has
   been run against the same 15 test cases as a control group. **Addressed,
   2026-08-04:** a real, unmodified upstream `python-tuf` deployment (see
   Threat-Model.md "Phase 8 real-baseline comparison: python-tuf") was
   run against the same 15-case matrix. Of the 15, only 3 have any
   TUF-native detection mechanism at all (#6 integrity, #7 key
   revocation, #9 downgrade protection) — all three caught 30/30 (100%),
   confirming TUF works correctly, not that it's weak. The other 12,
   including 9 that are load-bearing parts of this project's own S1-S5
   ladder, have no corresponding concept anywhere in TUF's specification
   — recorded as N/A with a stated architectural reason each, not run as
   fake scenarios. This is real, citable, measured evidence for the
   central claim rather than an assertion. Scope caveat: this speaks to
   TUF specifically, not SLSA or in-toto, which would need their own
   separate baseline runs to make the equivalent claim.
7. **"Same team designed the threat model, the mitigations, and the
   fixes for the mitigations' own credibility gap."** (New, 2026-08-04.)
   The ablation/adaptive-attacker work exists specifically to answer "you
   built both the lock and the lockpick" — but it was itself designed by
   the same process (this author + Claude) that built the original
   ladder. Not invalidating, but not resolved: name this explicitly in
   Methodology/Limitations rather than let a reviewer discover it
   unstated. **Partially addressed, 2026-08-04:** a blind(-ish) red-team
   pass by a fresh, context-free agent (see Threat-Model.md "Phase 8
   independent red-team review") found seven concrete gaps, all
   independently re-verified against the source afterward (unprotected
   ground-truth state files, fail-open key revocation, an unbound
   version/provenance pairing, a dead onboard policy-check stub with a
   brittle string-match gate, an unsigned/overwritable authorization-
   evidence document, no attestation-key revocation path, and unenforced
   operational-monitoring mismatches). Real, disclosable independence —
   but honestly caveated: the review wasn't blind to *which* attacks
   were already known (source comments name test-case numbers
   throughout), and it's an AI reviewer, not a human domain expert. State
   the findings and the caveat in the paper; do not oversell this as a
   fully independent human audit. **All seven fixed, 2026-08-04** (see
   Threat-Model.md's update note and ISSUES-AND-FIXES-LOG.md
   ISSUE-011-017) — verified via 19 new dedicated tests plus a full
   re-run of the existing regression suite, attack matrix, ablation
   study, and adaptive scenarios showing zero drift in any prior result.
   The paper's framing is now "an independent review found N real gaps
   in the original design, and all were fixed and re-verified the same
   day" — a materially stronger answer to this objection than "gaps were
   found," and itself a citable methodology point (independent review →
   fix → re-verify, not independent review as a one-time checkbox).
   **Recursion identified and addressed, 2026-08-05:** the fix/
   verification work above, plus the ablation-study extension and
   evaluation-code correctness tests (item 5/9 below), were themselves
   designed by the same process being scrutinized — the exact "you built
   the lock and the lockpick" pattern this objection names, recursing
   into its own remedy. Separately, the first red-team pass's file
   coverage was narrower than the codebase even at the time it ran (only
   20 files under `src/`, excluding `build.py`, `health_check.py`,
   `uplink_sim/`, and all of `evaluation/`). A second, wider blind
   red-team pass closed both gaps at once: full `src/` + `evaluation/`
   coverage (27 files) plus an explicit mandate to review the fix code
   itself and to audit the evaluation harness's own construction for
   vacuous tests. It found 12 more real gaps (see Threat-Model.md "Phase
   8 second independent red-team review" and ISSUES-AND-FIXES-LOG.md
   ISSUE-018 through ISSUE-029) — including one, a hardcoded/vacuous
   evaluation scenario, that is precisely the failure mode objection 9
   worries about, found by design in this project's own evaluation code.
   11 of 12 were fixed (one documented as a known limitation instead,
   ISSUE-022); one fix (automatic key-rotation refusal) was tried,
   found to break an existing correct test design, and reverted in favor
   of a different fix (visibility via evidence logging) — a genuine
   instance of a red-team-suggested remedy needing to be re-thought
   rather than applied literally, worth citing as evidence the
   fix-verify loop is doing real work, not rubber-stamping. This does
   not make the recursion disappear — every review pass, however wide,
   was still run by the same author-plus-AI process — but "two
   independent passes, the second one scoped specifically at what the
   first one missed and at the remedies for what it found, together
   surfacing 19 real gaps" is the strongest version of this answer
   achievable without a human domain-expert audit, and should be stated
   as exactly that: a strong mitigation, not a resolution of the
   underlying methodological point.
   **A third and fourth independent (blind, AI) red-team pass followed,
   2026-08-06** (different models/tools than the first two — see
   Threat-Model.md's third/fourth-pass sections and ISSUE-030/031),
   finding one further genuinely novel bypass plus five ways the third
   pass's own fix was incomplete — further evidence the multi-pass
   process finds real, non-trivial gaps, including gaps in its own prior
   remedies. **Human-review status decided, 2026-08-07:** a colleague
   (security engineer) review was requested 2026-08-05 and remains
   informally open, but the paper does not wait on it — its timeline is
   outside the author's control, so the gap is disclosed rather than
   worked around. Exact Limitations-section language:

   > Independent verification of this project's threat model and
   > mitigations to date consists of four independent, blind, AI-driven
   > red-team review passes (Section [Threat-Model reference]) and a
   > from-scratch comparison against an unmodified upstream `python-tuf`
   > deployment (Section [baseline-comparison reference]). A human
   > domain-expert review was requested but had not been completed at
   > the time of submission. We treat this as a limitation rather than a
   > resolved concern: AI-driven review, however methodologically
   > structured, is not a substitute for the judgment a human security
   > practitioner brings, particularly regarding which findings matter
   > operationally and which attacker capabilities are realistic for a
   > spacecraft mission context. If a human review is completed prior to
   > publication, its findings will be incorporated; if not, this remains
   > an open direction for follow-on work.

   This names the gap plainly rather than implying human verification
   happened, and leaves room to strengthen the claim later without
   having overclaimed now. See § 3's 2026-08-07 venue-strategy update for
   how this factors into venue choice for this submission round.
8. **"Is this code actually available, or just described?"** (New,
   2026-08-04.) The GitHub repo is currently private. Computers &
   Security and JSSE (per § 5 below) both expect data/code availability
   statements; "available on request" reads weaker than a public link at
   Q1 security venues especially. **Still open** — your decision, not a
   technical fix; see the working plan below.
9. **"How do we know the evaluation code itself is correct, not just
   the pipeline it measures?"** (New, 2026-08-04, prompted by ISSUE-010 —
   a latent, environment-dependent bug in the project's own test suite
   that only surfaced when run outside the original authoring sandbox for
   the first time.) **Addressed, 2026-08-05:** added 33 dedicated tests
   (`tests/test_evaluation_report_correctness.py`) for `evaluation/
   report.py`'s statistical functions — `_wilson_ci` cross-checked
   against an independent, third-party implementation
   (`statsmodels.stats.proportion.proportion_confint`, not a second copy
   of the same formula), `_mean_ci`/`_mean_stdev` cross-checked against
   an independently-written closed-form computation, boundary/structural
   properties (CI contains the point estimate, narrows with n, doesn't
   collapse at 0%/100%), and the aggregation logic
   (`summarize_happy_path`/`summarize_attack_cases`/
   `build_confusion_matrix`) checked against a small hand-computed
   synthetic fixture. All 33 pass. See Threat-Model.md "Phase 8
   evaluation-code correctness tests" for the full method. This doesn't
   prove there is no further hidden bug anywhere in the evaluation
   harness — no test suite proves that — but it closes the specific,
   previously-true claim that these functions had never been
   independently checked at all.
10. **Docker-container timing as a confound.** (Sharpened, 2026-08-04.)
    Real-stack timing numbers (Phase 7 and now Phase 8's ablation/adaptive
    work) include Docker container-launch overhead (~2.4-2.6s observed),
    not native flight-computer timing. More of the paper's evidence base
    now rests on this same infrastructure than when this was first noted.
    "Generalizes to real cFS/F´ binaries" is earned; "generalizes to
    flight-representative hardware" is not — keep these distinct in
    Discussion/Limitations.
11. **AI-use disclosure depth.** (Sharpened, 2026-08-04.) Originally
    scoped as "AI helped with drafting/research." By this point, AI
    (Claude) independently diagnosed several root causes (ISSUE-007
    through ISSUE-010) and designed the ablation/adaptive-attacker
    methodology itself, under human direction — a materially bigger claim
    than editing assistance. IEEE's disclosure policy specifically asks
    which sections used AI and how; the eventual statement needs to say
    this plainly, not undersell it.

### Working plan for the three still-open items (6, 7, 8) — added 2026-08-04

- **Item 6 (real baseline comparison): done, 2026-08-04.** Built a real,
  unmodified `python-tuf` repository + `ngclient.Updater` client
  (`evaluation/baselines/tuf_baseline.py`) and ran it against the same 15
  test cases. Results and scope caveats in Threat-Model.md "Phase 8
  real-baseline comparison: python-tuf" and item 6 above.
- **Item 7 (independent evaluator):** a second human reviewer or a
  genuinely blind red-team pass (an agent given only the source code, not
  the existing threat model or attack matrix, tasked with finding
  uncovered attack vectors) would add real, disclosable independence.
  Weaker than a human domain expert, but honestly stronger than nothing,
  and it's something that can actually be run this session if wanted.
- **Item 8 (repo visibility):** a decision, not a build — see STATUS.md
  for the tradeoffs and the exact command to flip it once decided.

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

## 7. AI-use disclosure statement (drafted 2026-08-07)

Objection 11 (§4) requires this to say plainly what AI actually did, not
undersell it as "editing assistance." Every claim below is traceable to a
specific STATUS.md/ISSUES-AND-FIXES-LOG.md entry — nothing here is
summarized from memory of the project, it's pulled from the log itself.
Adapt the wrapper/heading per venue (IEEE wants this in Acknowledgments,
naming the system and which sections used it; Elsevier wants a dedicated
"Declaration of generative AI and AI-assisted technologies in the writing
process" section immediately above the references) — the substance below
is the venue-agnostic master version.

> This project made substantive use of Claude (Anthropic), an AI system,
> across system design, implementation, testing, security review, and the
> preparation of this manuscript, under continuous human direction and
> review. Specifically: Claude wrote the majority of the pipeline's source
> code, test suite, and documentation to the author's specifications;
> independently diagnosed the root cause of several environment-dependent
> defects during real-hardware validation (e.g., a Docker-exec-format
> failure and a container `mqueue` sysctl limit, logged as ISSUE-007 and
> ISSUE-008); designed the mechanism-ablation study and adaptive-attacker
> test scenarios used in the evaluation methodology; and performed four
> independent, blind red-team review passes against the codebase, each
> using a fresh context without access to prior findings, that surfaced
> and led to fixes for 21 real security and correctness defects (logged
> as ISSUE-011 through ISSUE-031 in ISSUES-AND-FIXES-LOG.md; a further 10
> defects, ISSUE-001 through ISSUE-010, were found during real-hardware
> build/validation work rather than red-team review, also with Claude's
> involvement in root-cause diagnosis and fixes). Claude also assisted in
> researching target venues and drafting this manuscript.
>
> All AI-generated code, diagnoses, and findings were independently
> verified before being accepted: root-cause claims were confirmed via
> direct interactive testing rather than trusted from Claude's own report
> (for example, a Unicode-normalization claim in ISSUE-031 was verified by
> directly testing `casefold()` behavior against fullwidth Latin
> characters before the fix was written); every fix was checked against
> the full regression suite and, where applicable, against real target
> hardware; and all git operations, test executions on physical hardware,
> and final acceptance decisions were performed by the human author. AI
> is not listed as an author, consistent with the principle that
> authorship requires responsibilities only a human can hold. The
> author takes full responsibility for the accuracy and integrity of the
> content of this manuscript and the underlying codebase.
>
> We note, as a limitation rather than a strength, that the mitigations
> described above were designed by substantially the same human-plus-AI
> process being described — see the Limitations section (§4 objection 7)
> for the honest treatment of this recursion.

## 8. Data / code availability statement (drafted 2026-08-07)

Reflects the decided repo-visibility plan (STATUS.md, 2026-08-06/07: stays
private through the research/writing phase, made public at the point of
publication). Computers & Security and JSSE both expect this at
submission; phrase it as a firm commitment, not a vague "on request":

> The source code, test suite, evaluation harness, and full issue/fix
> history for this project are maintained in a version-controlled
> repository. The repository is currently private during the research and
> writing phase and will be made public no later than the date of
> publication, at which point it will be citable at
> https://github.com/Zartharas/verifiable-spacecraft-lifecycle. Reviewers
> requiring earlier access may request it from the corresponding author.

That last sentence matters — it gives reviewers a path to actually check
the code during review rather than only at publication, which is closer
to what these journals' screening actually wants than a pure "available
upon acceptance" line.

**Caveat — drop that last sentence for double-blind venues.** NDSS
SpaceSec requires anonymized submissions; naming "the corresponding
author" as a contact point would deanonymize the paper on sight. For any
double-blind submission, cut that sentence entirely and rely on the
public-at-publication commitment alone, or route requests through the
venue's own anonymous communication channel if one exists — check the
specific CFP once SpaceSec 2027's is published (§5).
