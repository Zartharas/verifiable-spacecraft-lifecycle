# Verifiable Spacecraft Software Lifecycle

Independent research project building and evaluating a controlled, end-to-end
verifiable software lifecycle pipeline for spacecraft flight software (NASA
Core Flight System / cFS), with the goal of producing a reproducible prototype
and a publishable comparative evaluation of software supply-chain assurance
levels (S0–S5).

## Who this is for

This repo is maintained by a single independent researcher. These documents
exist so that both the researcher and any AI assistant (Claude) picking the
project back up mid-stream can reconstruct full context without re-deriving
decisions already made. Read `STATUS.md` first in every new session.

## Document index

Read in this order when resuming work:

1. **STATUS.md** — current state, what's done, what's next, open blockers. Read this first, always.
2. **docs/PRD.md** — what we're building and why, scope, success criteria.
3. **docs/Threat-Model.md** — the S0–S5 assurance ladder and the attack/test matrix that drives everything else.
4. **docs/Pipeline-Flow-Document.md** — the end-to-end lifecycle flow (source → rollback), actors, data flow.
5. **docs/Technical-Design-Document.md** — architecture, components, tech stack, schemas.
6. **docs/Implementation-Plan.md** — phased build plan, milestones, task breakdown.
7. **docs/Research-Paper-Outline.md** — how the prototype's results map to a paper, venue targets.
8. **docs/Legal-Data-Sourcing-Notes.md** — what data/software sources are used and why they're legally clean for an independent researcher.
9. **ISSUES-AND-FIXES-LOG.md** — every bug and security finding, root cause, fix, and disclosure status.
10. **SECURITY.md** — responsible disclosure policy for this repo.

## Project structure (planned)

```
verifiable-spacecraft-lifecycle/       # repo root
├── README.md                          # this file
├── STATUS.md                          # living progress tracker — update every session
├── SECURITY.md                        # responsible disclosure policy
├── ISSUES-AND-FIXES-LOG.md            # bug/security fix ledger
├── docs/
│   ├── PRD.md
│   ├── Threat-Model.md
│   ├── Pipeline-Flow-Document.md
│   ├── Technical-Design-Document.md
│   ├── Implementation-Plan.md
│   ├── Research-Paper-Outline.md
│   └── Legal-Data-Sourcing-Notes.md
├── src/                                # pipeline code (to be created)
│   ├── build/
│   ├── provenance/
│   ├── sbom/
│   ├── signing/
│   ├── ground-authorization/
│   ├── uplink-sim/
│   ├── onboard-verification/
│   ├── attestation/
│   └── rollback/
├── cfs-app/                            # target cFS application under test
├── tests/                              # attack/tamper injection test suite
└── evaluation/                         # metrics collection, results, plots
```

`src/`, `cfs-app/`, `tests/`, and `evaluation/` don't exist yet — they get
created as implementation phases start (see `docs/Implementation-Plan.md`).

## Status

See `STATUS.md` for the current phase. As of project setup (documentation
phase), no code has been written yet.

## License

Apache License 2.0 (see `LICENSE`) — matches cFS's own license and includes
an explicit patent grant, appropriate for research code composing multiple
licensed components.
