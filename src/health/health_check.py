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

    expected_lines = list(target_stack.get(stack).expected_health_output)

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
