"""
Evidence store — append-only structured log implementing the schema from
Technical-Design-Document.md § 4.

This is the single source of truth every metric in evaluation/ is computed
against. Every pipeline stage that produces a result (pass/fail/n/a) writes
one record here, regardless of whether the mechanism is "active" for the
current condition — this lets later analysis distinguish "evidence existed
but wasn't checked" (lower S-conditions) from "evidence existed and was
checked" (higher S-conditions). See Design principle #2 in the TDD.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

DEFAULT_STORE_PATH = Path(__file__).parent.parent.parent / "evaluation" / "evidence_log.jsonl"


class EvidenceStore:
    """Append-only JSON-Lines evidence log. One JSON object per line."""

    def __init__(self, path: Path | str = DEFAULT_STORE_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        pipeline_stage: str,
        condition: str,
        artifact_ref: str,
        actor: str,
        result: str,
        detail: Optional[dict[str, Any]] = None,
        test_case_injected: Optional[str] = None,
    ) -> dict:
        if result not in ("pass", "fail", "n/a"):
            raise ValueError(f"result must be pass|fail|n/a, got {result!r}")
        entry = {
            "record_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pipeline_stage": pipeline_stage,
            "condition": condition,
            "artifact_ref": artifact_ref,
            "actor": actor,
            "result": result,
            "detail": detail or {},
            "test_case_injected": test_case_injected,
        }
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

    def read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        with open(self.path) as f:
            return [json.loads(line) for line in f if line.strip()]

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()

    def for_artifact(self, artifact_ref: str) -> list[dict]:
        return [r for r in self.read_all() if r["artifact_ref"] == artifact_ref]
