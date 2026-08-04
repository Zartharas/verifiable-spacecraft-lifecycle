"""
Phase 8 adaptive-attacker scenarios.

Why this exists: all 15 original attack matrix test cases
(evaluation/experiment.py) inject exactly ONE attack vector per run. A
2026-08-03 rejection-risk review (docs/Research-Paper-Outline.md)
flagged that this leaves an untested, reviewer-relevant question: an
attacker with knowledge of the ladder's own design wouldn't necessarily
try one thing at a time — they might combine vectors, hoping a violation
caught by an earlier stage doesn't actually stop a second vector from
mattering downstream (i.e., hoping the pipeline "detects but doesn't
halt"). Nothing in the original 15 cases tests this, because each one
runs in isolation.

These two scenarios combine two existing attack vectors in the SAME run
and check not just "was it caught" but "did the pipeline actually halt
at the first violated gate, or did it continue processing (and
potentially expose) the second vector anyway." Both are answered from
the existing pipeline.py control flow (no new artifact behavior needed):
ground_authorization's rejection returns before transmit() is ever
called; installation's write-verification failure returns before
attestation is ever generated. Combining vectors demonstrates the
pipeline is fail-closed at the *first* violated layer, not just
"eventually catches everything somehow."

Run with: python3 evaluation/adaptive_attacks.py             # cfs
          python3 evaluation/adaptive_attacks.py fprime       # fprime
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "evaluation"))

from pipeline import run  # noqa: E402
from attestation.attestation import DEFAULT_FRESHNESS_SECONDS  # noqa: E402
from experiment import _reset_all_state, N_TRIALS  # noqa: E402

N_ADAPTIVE_TRIALS = N_TRIALS


def adaptive_case_a(stack: str, version: int) -> dict:
    """Combined attack: rogue/unregistered builder_id (on its own, test
    case #5, caught at ground_authorization) submitted TOGETHER WITH an
    in-transit tamper (on its own, test case #6, caught at
    onboard_verification) in the same run, at S2.

    The adaptive question: does the ground_authorization rejection
    actually halt the pipeline before the tampered bundle is ever
    transmitted/checked onboard, or does some path let the second vector
    get exercised regardless? `onboard_verified` staying at its
    PipelineResult default (None) — not True or False — is the signal
    that transmit()/onboard verification was never reached at all,
    proving the first violation halted everything rather than merely
    being one of two independent detections.
    """
    t0 = time.perf_counter()
    result = run(
        condition_name="S2",
        version=version,
        builder_id="rogue-unregistered-runner",
        tamper_in_transit=True,
        stack=stack,
    )
    elapsed = time.perf_counter() - t0
    return {
        "caught": result.rejected_at == "ground_authorization",
        "halted_before_second_vector": result.onboard_verified is None,
        "onboard_verified": result.onboard_verified,
        "rejected_at": result.rejected_at,
        "elapsed_seconds": elapsed,
    }


def adaptive_case_b(stack: str, version_pair: tuple[int, int]) -> dict:
    """Combined attack at S4: an interrupted installation (on its own,
    test case #10, caught at the partition write-verify step) submitted
    TOGETHER WITH a stale attestation (on its own, test case #12, caught
    later via attestation-freshness -> rollback).

    The adaptive question: does the installation-layer failure halt the
    pipeline before attestation is ever generated, or does the pipeline
    continue on to generate/check a (backdated) attestation regardless?
    `attestation_path`/`health_ok` staying at their PipelineResult
    defaults (None) is the signal the attestation/health-check layer was
    never reached at all — the earliest violated layer (installation
    integrity) stopped everything, so the second vector never got a
    chance to matter either way.
    """
    baseline_version, attack_version = version_pair
    baseline = run(condition_name="S4", version=baseline_version, stack=stack)
    assert baseline.rollback_outcome == "confirmed", (
        f"baseline run did not confirm as expected (stack={stack!r}): "
        f"rollback_outcome={baseline.rollback_outcome!r}, rejected_at={baseline.rejected_at!r}"
    )
    t0 = time.perf_counter()
    result = run(
        condition_name="S4",
        version=attack_version,
        simulate_interrupted_install=True,
        attestation_backdate_seconds=DEFAULT_FRESHNESS_SECONDS + 3600,
        stack=stack,
    )
    elapsed = time.perf_counter() - t0
    return {
        "caught": result.rejected_at == "installation",
        "halted_before_second_vector": result.attestation_path is None and result.health_ok is None,
        "attestation_path": str(result.attestation_path) if result.attestation_path else None,
        "health_ok": result.health_ok,
        "rejected_at": result.rejected_at,
        "elapsed_seconds": elapsed,
    }


def run_adaptive_trials(n_trials: int = N_ADAPTIVE_TRIALS, stack: str = "cfs") -> dict:
    _reset_all_state(stack)
    case_a_trials = [adaptive_case_a(stack, version=i + 1) for i in range(n_trials)]

    _reset_all_state(stack)
    case_b_trials = [
        adaptive_case_b(stack, version_pair=(i * 2 + 1, i * 2 + 2)) for i in range(n_trials)
    ]

    return {
        "A_rogue_builder_plus_transit_tamper": {
            "condition": "S2",
            "caught_rate": sum(1 for t in case_a_trials if t["caught"]) / n_trials,
            "halted_before_second_vector_rate": (
                sum(1 for t in case_a_trials if t["halted_before_second_vector"]) / n_trials
            ),
            "trials": case_a_trials,
        },
        "B_interrupted_install_plus_stale_attestation": {
            "condition": "S4",
            "caught_rate": sum(1 for t in case_b_trials if t["caught"]) / n_trials,
            "halted_before_second_vector_rate": (
                sum(1 for t in case_b_trials if t["halted_before_second_vector"]) / n_trials
            ),
            "trials": case_b_trials,
        },
    }


def print_summary(results: dict) -> None:
    print(f"{'Scenario':<45}{'Cond':<6}{'Caught':<10}{'Halted-early?'}")
    for name, r in results.items():
        print(
            f"{name:<45}{r['condition']:<6}{r['caught_rate']*100:>6.0f}%    "
            f"{r['halted_before_second_vector_rate']*100:>6.0f}%"
        )


if __name__ == "__main__":
    import json

    stack_arg = sys.argv[1] if len(sys.argv) > 1 else "cfs"
    print(f"Running Phase 8 adaptive-attacker scenarios ({N_ADAPTIVE_TRIALS} trials each, "
          f"stack={stack_arg})...")
    results = run_adaptive_trials(stack=stack_arg)
    print_summary(results)

    out_dir = REPO_ROOT / "evaluation" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_name = f"phase8_adaptive_{stack_arg}.json"
    with open(out_dir / out_name, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nFull results written to {out_dir / out_name}")
