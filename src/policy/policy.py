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


# Second red-team pass, finding #10 (2026-08-05): representations that
# should all count as "the pattern's True" for a security-relevant
# boolean flag, since a caller-supplied config can plausibly arrive as
# JSON-decoded (real bool), a raw string, or a loosely-typed int, and a
# deny-rule that only catches one of those representations is trivially
# bypassed by using a different one for the exact same intent.
_TRUTHY_STRINGS = {"true", "1", "yes", "on"}


def _values_match(config_value, pattern_value) -> bool:
    """Equality check for one field, deliberately more permissive than
    `==` when the pattern's value is a bool — `{"debug_mode": True}` must
    also match `{"debug_mode": "true"}` / `1` / `"1"`, not just the
    exact Python `True` singleton. Python's `"true" == True` is `False`,
    so a bare `==` on the pattern above lets a config that means the same
    thing but is spelled differently sail past the only rule in the
    deny-list. Non-bool pattern values keep exact-equality semantics —
    this coercion is specifically about the boolean-flag case, not a
    general fuzzy-match policy engine."""
    if isinstance(pattern_value, bool):
        if isinstance(config_value, bool):
            return config_value == pattern_value
        if isinstance(config_value, str):
            return (config_value.strip().lower() in _TRUTHY_STRINGS) == pattern_value
        if isinstance(config_value, (int, float)):
            return bool(config_value) == pattern_value
        return False
    return config_value == pattern_value


def _matches(config: dict, pattern: dict) -> bool:
    """A config matches a prohibited pattern if every key/value in the
    pattern is present and equal in the config (a simple deny-rule
    semantics — real Rego would express this more richly)."""
    return all(_values_match(config.get(k), v) for k, v in pattern.items())


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
