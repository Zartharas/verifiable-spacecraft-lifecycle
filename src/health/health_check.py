"""
Health validation harness — runs the currently-active installed binary
and checks its output against the expected pattern for
cfs-app/stub-telemetry-app (see that file's docstring: four deterministic
"channel=N value=M" lines).

Covers attack matrix test case #11 (failed health check) via the
`force_fail` test hook — simulates a build that runs but misbehaves,
without needing a second broken artifact.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_store import EvidenceStore  # noqa: E402

EXPECTED_LINES = [f"channel={i} value={i * 2 + 1}" for i in range(4)]


def run_health_check(
    installed_binary_path: Path,
    condition_name: str = "S3",
    force_fail: bool = False,
) -> tuple[bool, Optional[str]]:
    store = EvidenceStore()
    import hashlib

    with open(installed_binary_path, "rb") as f:
        artifact_hash = hashlib.sha256(f.read()).hexdigest()

    if force_fail:
        store.record(
            pipeline_stage="health_validation",
            condition=condition_name,
            artifact_ref=artifact_hash,
            actor="health_monitor",
            result="fail",
            detail={"reason": "forced failure (test case #11 simulation)"},
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
            detail={"reason": f"execution failed: {e}"},
            test_case_injected="11",
        )
        return False, f"execution failed: {e}"

    output_lines = [line.strip() for line in result.stdout.strip().splitlines()]
    healthy = result.returncode == 0 and output_lines == EXPECTED_LINES

    store.record(
        pipeline_stage="health_validation",
        condition=condition_name,
        artifact_ref=artifact_hash,
        actor="health_monitor",
        result="pass" if healthy else "fail",
        detail={
            "returncode": result.returncode,
            "output_matches_expected": output_lines == EXPECTED_LINES,
        },
        test_case_injected=None if healthy else "11",
    )
    return healthy, None if healthy else "unexpected output or nonzero exit"
