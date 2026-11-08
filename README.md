# Verifiable Spacecraft Software Lifecycle

Independent research project building and evaluating a controlled, end-to-end
verifiable software lifecycle pipeline for spacecraft flight software (NASA
Core Flight System / cFS), with the goal of producing a reproducible prototype
and a publishable comparative evaluation of software supply-chain assurance
levels (S0–S5).

## New here? Start with this

**First time cloning this repo to run or test it yourself?** Read
`docs/Getting-Started.md` — step-by-step instructions to install, run the
demo pipeline, run the test suite, and run the evaluation/ablation
harnesses. No prior context needed. Or, for the fastest possible path to
seeing it work, copy-paste the block below.

### Quick start (copy-paste, ~2 minutes, no Docker required)

```bash
git clone https://github.com/Zartharas/verifiable-spacecraft-lifecycle.git
cd verifiable-spacecraft-lifecycle
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# 1. Run the demo pipeline (five end-to-end calls, incl. a caught tamper attack)
python3 src/pipeline.py

# 2. Run the full test suite (197 tests: every attack case x every assurance level, plus regression and mutation tests)
python3 -m pytest -q

# 3. Run the statistical evaluation that produces the paper's numbers
python3 evaluation/experiment.py

# 4. Run the mechanism-isolation ablation study
python3 evaluation/ablation.py
```

Everything above runs against a fast, local stand-in binary — no Docker,
no NASA source download, nothing beyond Python 3.10+. Running against the
*real* NASA cFS/F´ frameworks via Docker is optional and covered in
`docs/Getting-Started.md` § 6. Full explanations, expected output, and
troubleshooting for every command above: `docs/Getting-Started.md`.

## How it works

```mermaid
flowchart TD
    A[Source] --> B["Reproducible Build"]
    B --> C["Provenance Generation<br/><sub>active from S2</sub>"]
    C --> D["SBOM Generation<br/><sub>active from S1</sub>"]
    D --> E["Signed Release<br/><sub>active from S0 baseline</sub>"]
    E --> F[Ground Authorization]
    F --> G[Simulated Uplink]
    G --> H["Onboard Signature and Policy Verification<br/><sub>policy check active from S5</sub>"]
    H --> I[Installation]
    I --> J["Boot/Runtime Attestation<br/><sub>active from S3</sub>"]
    J --> K[Health Validation]
    K -->|fail| L["A/B Partition Rollback<br/><sub>active from S4</sub>"]
    K -->|pass| M[Approval]
    L --> N["Updated Authorization Evidence<br/><sub>active from S5</sub>"]
    M --> N
    N -.feeds next cycle.-> A

    style E fill:#2d6a4f,color:#fff
    style D fill:#40916c,color:#fff
    style C fill:#52b788,color:#fff
    style J fill:#1b4965,color:#fff
    style L fill:#9d0208,color:#fff
    style N fill:#3a0ca3,color:#fff
```

Twelve stages, one artifact lifecycle, six increasingly strict assurance
levels layered on top of the same pipeline. See
`docs/Pipeline-Flow-Document.md` for the full per-stage actor/input/output/
evidence breakdown.

### The S0–S5 assurance ladder

Each level is strictly additive — every mechanism from the level below
stays active:

```mermaid
flowchart LR
    S0["S0<br/>Signature only<br/><sub>baseline</sub>"] --> S1["S1<br/>+ SBOM<br/><sub>component inventory</sub>"]
    S1 --> S2["S2<br/>+ Build Provenance<br/><sub>SLSA / in-toto style</sub>"]
    S2 --> S3["S3<br/>+ Onboard Attestation<br/><sub>runtime/boot proof</sub>"]
    S3 --> S4["S4<br/>+ Trusted Rollback<br/><sub>verified A/B partition</sub>"]
    S4 --> S5["S5<br/>+ Machine-Readable<br/>Authorization Evidence<br/><sub>OSCAL-style, ground/auditor-consumable</sub>"]

    style S0 fill:#590d22,color:#fff
    style S1 fill:#800f2f,color:#fff
    style S2 fill:#a4133c,color:#fff
    style S3 fill:#c9184a,color:#fff
    style S4 fill:#ff4d6d,color:#fff
    style S5 fill:#3a0ca3,color:#fff
```

Fifteen injected attack cases run against every level; the evaluation
harness measures which level first catches each one. See
`docs/Threat-Model.md` for the full attack matrix.

<p align="center">
  <img src="docs/assets/assurance-ladder.svg" alt="Animated diagram showing the S0-S5 assurance ladder building up one mechanism at a time" width="820">
</p>

### Evaluation architecture

```mermaid
flowchart TB
    subgraph Stacks["Target stacks (stand-in + real, via Docker)"]
        direction LR
        CFS["NASA cFS<br/>(cfs / cfs-real)"]
        FPRIME["F Prime<br/>(fprime / fprime-real)"]
    end

    subgraph Harnesses["Evaluation harnesses"]
        direction TB
        EXP["evaluation/experiment.py<br/><sub>15 attack cases x S0-S5,<br/>detection/FP/FN rate, overhead, CIs</sub>"]
        ABL["evaluation/ablation.py<br/><sub>disable one mechanism at a time,<br/>confirm isolated detection loss</sub>"]
        TUF["evaluation/baselines/tuf_baseline.py<br/><sub>python-tuf comparison baseline</sub>"]
    end

    Stacks --> Harnesses
    Harnesses --> RESULTS["evaluation/results/*.json<br/><sub>raw + summarized, feeds the paper's numbers</sub>"]

    style CFS fill:#0b525b,color:#fff
    style FPRIME fill:#0b525b,color:#fff
    style EXP fill:#1b4965,color:#fff
    style ABL fill:#1b4965,color:#fff
    style TUF fill:#1b4965,color:#fff
    style RESULTS fill:#3a0ca3,color:#fff
```

## Who the rest of this document is for

This repo is maintained by a single independent researcher. The documents
below exist so that both the researcher and any AI assistant (Claude) picking
the project back up mid-stream can reconstruct full context without
re-deriving decisions already made. Read `STATUS.md` first in every new
session.

## Document index

Read in this order when resuming work:

1. **STATUS.md** — current state, what's done, what's next, open blockers. Read this first, always.
2. **docs/Getting-Started.md** — for a human running/testing this for the first time (see above).
3. **docs/PRD.md** — what we're building and why, scope, success criteria.
4. **docs/Threat-Model.md** — the S0–S5 assurance ladder and the attack/test matrix that drives everything else, including all independent red-team review findings.
5. **docs/Pipeline-Flow-Document.md** — the end-to-end lifecycle flow (source → rollback), actors, data flow.
6. **docs/Technical-Design-Document.md** — architecture, components, tech stack, schemas.
7. **docs/Implementation-Plan.md** — phased build plan, milestones, task breakdown.
8. **docs/Research-Paper-Outline.md** — how the prototype's results map to a paper, venue targets.
9. **docs/Legal-Data-Sourcing-Notes.md** — what data/software sources are used and why they're legally clean for an independent researcher.
10. **docs/Paper-Draft.md** — the manuscript itself: full text, citation-verification history, and target-venue status.
11. **ISSUES-AND-FIXES-LOG.md** — every bug and security finding, root cause, fix, and disclosure status.
12. **SECURITY.md** — responsible disclosure policy for this repo.

## Project structure

```
verifiable-spacecraft-lifecycle/       # repo root
├── README.md                          # this file
├── STATUS.md                          # living progress tracker — update every session
├── SECURITY.md                        # responsible disclosure policy
├── ISSUES-AND-FIXES-LOG.md            # bug/security fix ledger
├── docs/
│   ├── Getting-Started.md             # start here if you're new
│   ├── PRD.md
│   ├── Threat-Model.md
│   ├── Pipeline-Flow-Document.md
│   ├── Technical-Design-Document.md
│   ├── Implementation-Plan.md
│   ├── Research-Paper-Outline.md
│   ├── Legal-Data-Sourcing-Notes.md
│   ├── Paper-Draft.md                 # the manuscript itself
│   └── assets/                        # diagrams/animations used in this README
├── src/                                # pipeline code: build, signing, ground
│   │                                     authorization, uplink sim, onboard
│   │                                     verification, installation,
│   │                                     attestation, rollback, policy, SBOM,
│   │                                     provenance, evidence store
├── cfs-app/, fprime-app/               # target applications under test
│                                         (stand-in stubs by default; real
│                                         NASA cFS/F´ via Docker, optional)
├── tests/                              # attack/tamper injection + regression suite
└── evaluation/                        # experiment runner, metrics, ablation study
```

## Status

See `STATUS.md` for the current phase and detailed session log. In short:
the full S0–S5 pipeline is built and tested (197 tests passing), evaluated
against two target stacks (NASA cFS and F´, both stand-in and real Docker
builds) with a full statistical evaluation and mechanism-isolation ablation
study, and has been through four rounds of independent, blind, AI-driven
red-team review (Claude, OpenAI, Zhipu AI's GLM, and DeepSeek) — see
`docs/Threat-Model.md` and `ISSUES-AND-FIXES-LOG.md` for every finding and
fix. The companion paper (`docs/Paper-Draft.md`) has been submitted for
peer review; a human-colleague code review remains separately pending.
The repo is expected to go public no later than the paper's publication
date.

## License

Apache License 2.0 (see `LICENSE`) — matches cFS's own license and includes
an explicit patent grant, appropriate for research code composing multiple
licensed components.
