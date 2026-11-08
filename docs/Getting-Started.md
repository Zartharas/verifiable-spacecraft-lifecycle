# Getting Started

A step-by-step guide for someone running and testing this project for the
first time — no prior context needed beyond what's here. If you're an AI
assistant picking up ongoing work on this project, read `STATUS.md`
instead; this document is for a human trying the code out.

## What you're testing

This is a research prototype: a simulated spacecraft software update
pipeline (build → sign → ground authorization → uplink → onboard
verification → installation → attestation → rollback) with six
increasingly strict software supply-chain assurance levels, S0 (signature
only) through S5 (+ machine-readable authorization evidence). The project
injects specific attacks at each level and measures whether that level's
mechanisms catch them. See `docs/Threat-Model.md` for the full attack
matrix and `docs/PRD.md` for the research question.

By default, everything below runs against a small stand-in binary, not
real spacecraft flight software — no Docker, no NASA cFS/F´ source
download, nothing beyond Python. That's intentional: it's fast (each
pipeline run completes in well under a second) and requires no special
setup. A separate, optional section near the end covers running the
pipeline against the *real* NASA cFS and F´ frameworks via Docker.

## Prerequisites

- Python 3.10 or newer (tested on 3.11 and 3.13; anything in that range
  should work — there's nothing version-specific beyond typing syntax
  introduced by 3.10).
- `pip`.
- `git`, to clone the repo.
- No Docker, no compiler, no other system dependencies for the steps in
  this section. (Docker is only needed for the optional real-framework
  section near the end.)

## 1. Clone and install

```bash
git clone https://github.com/Zartharas/verifiable-spacecraft-lifecycle.git
cd verifiable-spacecraft-lifecycle
pip install -r requirements-dev.txt
```

`requirements-dev.txt` pulls in `requirements.txt` plus `pytest`. The
runtime dependencies are deliberately minimal: `cryptography` (for real
Ed25519 signing/verification — this project uses genuine cryptographic
primitives throughout, not simulated ones), `pyyaml`, and `tuf` (only
used by one optional baseline-comparison script, `evaluation/baselines/
tuf_baseline.py` — you don't need it for anything else).

If you'd rather use a virtual environment (recommended, but not
required):

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

## 2. Run the demo pipeline

This runs five pipeline calls end-to-end — the S0 happy path, a deliberate
tamper-in-transit attack at S0, and happy paths at S2/S4/S5 — printing a
result object for each:

```bash
python3 src/pipeline.py
```

You should see five blocks of output. The two interesting ones to check:

- The **second** block (S0, tampered in transit) should show
  `rejected_at='onboard_verification'` and `installed=False` — the
  pipeline caught the tamper before installation.
- The **last** block (S5) prints a path to a signed, machine-readable
  authorization evidence document — open that JSON file and you'll see a
  per-stage audit trail of every check that ran and passed.

If this prints five results with no traceback, the basic install is
working correctly.

### Keys and local state

The first pipeline run auto-generates a few local Ed25519 test keypairs
under `keys/` (signing, attestation, authorization-evidence) — this is
normal and expected; the code does this lazily on first use rather than
requiring a setup script. `keys/*.pem` and everything under `work/` (the
version ledger, partition state, evidence logs) are git-ignored — they're
local runtime state, not project source, and are safe to delete if you
ever want to reset to a clean slate:

```bash
rm -rf work/ keys/*.pem keys/*.hmac keys/revoked_keys.txt keys/attestation_revoked_keys.txt
```

(The next pipeline run will regenerate everything it needs.)

## 3. Run the automated test suite

```bash
python3 -m pytest -q
```

This runs the full attack-matrix and regression suite — 197 tests as of
this writing, covering every one of the 15 injected-attack test cases at
every assurance level, plus every bug/security fix logged in
`ISSUES-AND-FIXES-LOG.md`. Expect a couple of minutes, not seconds — some
tests exercise real subprocess/Docker-fallback paths — and all tests
passing (aside from the auto-skipped file noted below).

One test file, `tests/test_phase7_real_builds.py`, is skipped
automatically unless the real cFS/F´ binaries described in the optional
Docker section below are present — that's expected, not a failure.

If you want to run just one phase's tests (useful for faster iteration or
narrowing down an issue):

```bash
python3 -m pytest tests/test_phase1_pipeline.py -v
```

## 4. Run the full evaluation harness

This is what actually produces the paper's numbers: it runs many repeated
trials of the happy path and every attack scenario at every assurance
level, and reports detection rate, false-positive/negative rate, and
overhead, with confidence intervals.

```bash
python3 evaluation/experiment.py
```

Results are written to `evaluation/results/phase5_raw_results.json`.
Expect this to take a couple of minutes — it's running real trials, not
reading cached numbers.

To see a human-readable summary instead of raw JSON, see
`evaluation/report.py` (import it and call `summarize_happy_path()` /
`summarize_attack_cases()` on the results, or see how `tests/
test_evaluation_report_correctness.py` exercises it for examples).

## 5. Run the ablation study

This isolates each individual assurance mechanism (SBOM check, provenance
check, attestation, rollback, machine-readable authorization) one at a
time — disabling exactly one mechanism per run and confirming detection
drops specifically for the attack that mechanism exists to catch, and
only that one:

```bash
python3 evaluation/ablation.py
```

Takes a few minutes at the default trial count. Results are written to
`evaluation/results/phase8_ablation_cfs.json`.

## 6. (Optional, advanced) Run against the real NASA cFS / F´ frameworks

Everything above uses a small stand-in binary that behaves like flight
software for the purposes of this pipeline (it can be signed, tampered
with, and health-checked), but is not the real thing. If you want to
confirm the pipeline also works against the actual, unmodified NASA cFS
and F´ (F Prime) frameworks — this is a heavier, optional step:

- Requires Docker.
- Full instructions live in `cfs-app/README.md` and `fprime-app/
  README.md`, including the exact pinned upstream tags this project
  builds against (see `docs/Legal-Data-Sourcing-Notes.md` for why those
  specific tags and licenses were chosen).
- Building takes several minutes per framework (compiling real flight
  software, not the sub-second stand-in build).
- Once built, `tests/test_phase7_real_builds.py`'s skipped tests will run
  automatically, and `cfs-real` / `fprime-real` become available as
  `--stack` arguments to the evaluation/ablation scripts above.
- **Update (ISSUE-003, resolved):** attestation/rollback (S3+) now works
  against both `cfs-real` and `fprime-real`. The real cFS/F´ binaries are
  long-running processes, not run-to-completion stand-ins, so the original
  health-check model didn't apply to them directly; this was fixed with a
  persistent-process health-check mode that waits for an
  empirically-confirmed boot-success marker on stdout. See
  `evaluation/results/phase6_report_cfs-real.md` and
  `evaluation/results/phase6_report_fprime-real.md` for verification, and
  `docs/Threat-Model.md` for the exact scope of what is currently verified
  against the real frameworks.

## If something doesn't work

- **Import errors on `src.` modules:** run commands from the repo root,
  not from inside `src/` or `tests/` — the modules manage their own
  `sys.path` insertion assuming that working directory.
- **A test fails that isn't `test_phase7_real_builds.py`:** please open
  an issue with the full `pytest -v` output for that test. This would be
  a real regression, not expected behavior, and is exactly the kind of
  outside verification this project is trying to get more of — see
  `docs/Threat-Model.md`'s red-team review sections for how seriously
  independent findings are taken here.
- **Leftover state from an interrupted run causing weird failures on a
  later run:** see the "reset to a clean slate" command in step 2 above.

## Where to go next

- `docs/Threat-Model.md` — the full S0–S5 ladder and attack matrix.
- `docs/Pipeline-Flow-Document.md` — the end-to-end lifecycle flow.
- `docs/Technical-Design-Document.md` — architecture and component
  details.
- `ISSUES-AND-FIXES-LOG.md` — every bug and security finding found during
  development, including four rounds of independent (blind, AI)
  red-team review, with root cause, fix, and verification for each.
- `SECURITY.md` — how to responsibly report a security issue.
