# Security Policy

## Scope

This repository contains a research prototype for evaluating software
supply-chain assurance mechanisms applied to spacecraft flight software
(cFS-based). It is **not** operational flight software and is not deployed
on any real spacecraft or ground system. That said, findings in this
project's own code (the pipeline components, evidence store, verification
logic) are welcome and taken seriously, since the whole point of the
project is to reason carefully about this class of vulnerability.

## Reporting a vulnerability

If you find a security issue in this project's own code:

1. Do **not** open a public GitHub issue for it.
2. Report it privately to: aman.singh2406@live.com (or via GitHub's
   private security advisory feature once the repo is created, which is
   preferred if available).
3. Include: affected component, reproduction steps, and potential impact.

As an independent researcher, response times may vary, but every report
will be acknowledged. Once a fix is available, the finding will be logged
in `ISSUES-AND-FIXES-LOG.md` and credited to the reporter (unless
anonymity is requested).

## Reporting a vulnerability in an upstream dependency

If you find an issue in an upstream project this repository depends on
(NASA cFS, Sigstore/cosign, in-toto, Syft, etc.), please report it directly
to that project through its own disclosure channel — this repo will link
to the public disclosure once available, but is not the right place to
report it first.

## Out of scope

- Findings that require assuming access to real operational spacecraft
  hardware, real signing keys, or real mission infrastructure — none of
  that exists in this project (see `docs/Legal-Data-Sourcing-Notes.md`).
- Issues in the simulated uplink's fidelity to real RF/physical-layer
  behavior — this is a documented, intentional simplification (see
  `docs/PRD.md` non-goals), not a security bug.
