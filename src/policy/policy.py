"""
Prohibited-configuration policy — S5 assurance mechanism.

Decision (Technical-Design-Document.md § 7/7d): a **custom, hand-rolled
policy check**, not OPA/Rego. Real OPA would mean fetching an external
binary release with no clean verification path from this sandbox (no
package manager entry, would require a raw binary download and trust
decision this project isn't positioned to make lightly). A small,
explicit Python policy table is sufficient to test the assurance
mechanism itself — "can a correctly-signed, otherwise-valid release still
be rejected for policy reasons?" — without pulling in unverified
infrastructure. Swap in OPA/Rego later if the project moves to a real
ground system; the check-shape here (deny-list of prohibited config
patterns) maps cleanly onto a Rego `deny` rule set if that migration
happens.

Covers attack matrix test case #8 (correct signature but prohibited
configuration).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_store import EvidenceStore  # noqa: E402

# Test-only prohibited-configuration table. A real ground system would
# load this from a versioned, ground-approved policy document, not a
# hardcoded Python list.
PROHIBITED_CONFIGURATIONS = [
    {"debug_mode": True},  # debug builds must never be authorized for flight
]


def _matches(config: dict, pattern: dict) -> bool:
    """A config matches a prohibited pattern if every key/value in the
    pattern is present and equal in the config (a simple deny-rule
    semantics — real Rego would express this more richly)."""
    return all(config.get(k) == v for k, v in pattern.items())


def check_configuration(
    config: dict, artifact_hash: str, condition_name: str = "S5"
) -> tuple[bool, Optional[str]]:
    store = EvidenceStore()

    for pattern in PROHIBITED_CONFIGURATIONS:
        if _matches(config, pattern):
            store.record(
                pipeline_stage="configuration_policy_check",
                condition=condition_name,
                artifact_ref=artifact_hash,
                actor="ground_authorization_service",
                result="fail",
                detail={"reason": "prohibited configuration", "matched_pattern": pattern, "config": config},
                test_case_injected="8",
            )
            return False, f"prohibited configuration: {pattern}"

    store.record(
        pipeline_stage="configuration_policy_check",
        condition=condition_name,
        artifact_ref=artifact_hash,
        actor="ground_authorization_service",
        result="pass",
        detail={"config": config},
    )
    return True, None
