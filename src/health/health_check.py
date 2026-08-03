"""
Health validation harness — runs the currently-active installed binary
and checks its output against the expected deterministic pattern for the
active target stack (see `src/target_stack.py`).

Phase 6 scope: parameterized by `stack` rather than hardcoding
cfs-app/stub-telemetry-app's specific "channel=N value=M" output shape.
Each stack registers its own `expected_health_output` — the cFS-informed
stub's four "channel=N value=M" lines, or the F Prime-informed stub's
four "telemetry.chanN=M" lines — so this harness's actual check logic
(run binary, compare stdout line-for-line) needed no stack-specific
branches at all. Default remains `"cfs"`, so Phase 1-5 behavior and tests
are unaffected.

Covers attack matrix test case #11 (failed health check) via the
`force_fail` test hook — simulates a build that runs but misbehaves,
without needing a second broken artifact. Applies identically regardless
of which stack is active.

Phase 7 scope: the two "real" stacks (`"cfs-real"`, `"fprime-real"`) have
`expected_health_output=None` in `target_stack.py`, because this
harness's whole model — run the binary, expect it to exit quickly with a
fixed stdout pattern — does not fit either real framework. Both are
long-running processes: cFS's `core-cpu1` reaches an `OPERATIONAL` state
and then loops forever managing the flight software bus; F´'s `Ref`
binary blocks waiting for a network GDS connection. Running either
through the existing `subprocess.run(..., timeout=5)` call would just
time out and get misreported as an unhealthy/failed build — factually
wrong for a genuinely-running flight-software core. Rather than let that
happen silently, `run_health_check` raises `NotImplementedError` for any
stack with `expected_health_output is None`. See Threat-Model.md "Phase 7
findings" for the full writeup and STATUS.md for what's blocked on this
(S3+ conditions against the real binaries) until a persistent-process
health-check strategy is designed.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_store import EvidenceStore  # noqa: E402
import target_stack  # noqa: E402


def run_health_check(
    installed_binary_path: Path,
    condition_name: str = "S3",
    force_fail: bool = False,
    stack: str = "cfs",
) -> tuple[bool, Optional[str]]:
    store = EvidenceStore()
    import hashlib

    stack_expected = target_stack.get(stack).expected_health_output
    if stack_expected is None:
        raise NotImplementedError(
            f"Stack '{stack}' has no working health-check strategy yet "
            "(expected_health_output=None in target_stack.py) — it is a "
            "long-running process, not a short-lived deterministic CLI "
            "program. See health_check.py module docstring and "
            "Threat-Model.md 'Phase 7 findings.'"
        )
    expected_lines = list(stack_expected)

    with open(installed_binary_path, "rb") as f:
        artifact_hash = hashlib.sha256(f.read()).hexdigest()

    if force_fail:
        store.record(
            pipeline_stage="health_validation",
            condition=condition_name,
            artifact_ref=artifact_hash,
            actor="health_monitor",
            result="fail",
            detail={"reason": "forced failure (test case #11 simulation)", "stack": stack},
            test_case_injected="11",
        )
        return False, "forced health check failure"

    try:
        result = subprocess.run(
            [str(installed_binary_path)], capture_output=True, text=True, timeout=5
        )
    except (OSError, subprocess.SubprocessError) as e:
        store.record(
            pipeline_stage="health_validation",
            condition=condition_name,
            artifact_ref=artifact_hash,
            actor="health_monitor",
            result="fail",
            detail={"reason": f"execution failed: {e}", "stack": stack},
            test_case_injected="11",
        )
        return False, f"execution failed: {e}"

    output_lines = [line.strip() for line in result.stdout.strip().splitlines()]
    healthy = result.returncode == 0 and output_lines == expected_lines

    store.record(
        pipeline_stage="health_validation",
        condition=condition_name,
        artifact_ref=artifact_hash,
        actor="health_monitor",
        result="pass" if healthy else "fail",
        detail={
            "stack": stack,
            "returncode": result.returncode,
            "output_matches_expected": output_lines == expected_lines,
        },
        test_case_injected=None if healthy else "11",
    )
    return healthy, None if healthy else "unexpected output or nonzero exit"
