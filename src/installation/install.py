"""
Installation stage — Phase 1 scope: simple install, no A/B partitioning
yet (that's Phase 3/S4). Only runs if onboard verification already passed
— the orchestrator is responsible for that ordering.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_store import EvidenceStore  # noqa: E402

INSTALL_DIR = REPO_ROOT / "work" / "spacecraft_installed"


def install(binary_path: Path, condition_name: str = "S0") -> Path:
    store = EvidenceStore()
    import hashlib

    with open(binary_path, "rb") as f:
        artifact_hash = hashlib.sha256(f.read()).hexdigest()

    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    installed_path = INSTALL_DIR / binary_path.name
    shutil.copy(binary_path, installed_path)
    installed_path.chmod(0o755)

    store.record(
        pipeline_stage="installation",
        condition=condition_name,
        artifact_ref=artifact_hash,
        actor="installer",
        result="pass",
        detail={"installed_path": str(installed_path)},
    )
    return installed_path
