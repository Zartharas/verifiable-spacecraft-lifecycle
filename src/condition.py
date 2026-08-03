"""
Condition loader — the single source of truth for which assurance
mechanisms (S0-S5) are active for a given pipeline run.

Design principle (Technical-Design-Document.md, "Design principles" #1):
one codebase, six conditions. Every pipeline stage imports this module and
checks the relevant flag rather than having condition-specific code paths
duplicated. Inactive mechanisms are skipped honestly, not stubbed with a
fake pass, so S0 behaves like a real S0 system rather than "S5 pretending
to be S0."
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import yaml

DEFAULT_CONDITION_FILE = Path(__file__).parent / "condition.yaml"

# Canonical mechanism set and the condition each one first activates at.
# Used both to validate config files and to auto-generate a condition.yaml
# for any of the six standard S0-S5 presets.
MECHANISM_ACTIVATION_ORDER = [
    "signature",
    "sbom",
    "provenance",
    "onboard_attestation",
    "trusted_rollback",
    "machine_readable_authorization",
]

CONDITION_PRESETS = {
    "S0": ["signature"],
    "S1": ["signature", "sbom"],
    "S2": ["signature", "sbom", "provenance"],
    "S3": ["signature", "sbom", "provenance", "onboard_attestation"],
    "S4": ["signature", "sbom", "provenance", "onboard_attestation", "trusted_rollback"],
    "S5": MECHANISM_ACTIVATION_ORDER,
}


@dataclasses.dataclass(frozen=True)
class Condition:
    name: str
    mechanisms: dict

    def active(self, mechanism: str) -> bool:
        if mechanism not in MECHANISM_ACTIVATION_ORDER:
            raise ValueError(
                f"Unknown mechanism '{mechanism}'. Known: {MECHANISM_ACTIVATION_ORDER}"
            )
        return bool(self.mechanisms.get(mechanism, False))

    def as_dict(self) -> dict:
        return {"condition": self.name, "mechanisms": dict(self.mechanisms)}


def preset(condition_name: str) -> Condition:
    """Build a Condition from one of the six standard S0-S5 presets."""
    if condition_name not in CONDITION_PRESETS:
        raise ValueError(
            f"Unknown condition '{condition_name}'. Must be one of {list(CONDITION_PRESETS)}"
        )
    active = set(CONDITION_PRESETS[condition_name])
    mechanisms = {m: (m in active) for m in MECHANISM_ACTIVATION_ORDER}
    return Condition(name=condition_name, mechanisms=mechanisms)


def load(path: Path | str = DEFAULT_CONDITION_FILE) -> Condition:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"condition file not found at {path} — run write_default() or "
            f"select a preset via condition.preset('S0')"
        )
    with open(path) as f:
        data = yaml.safe_load(f)
    return Condition(name=data["condition"], mechanisms=data.get("mechanisms", {}))


def write_default(path: Path | str = DEFAULT_CONDITION_FILE, condition_name: str = "S0") -> None:
    cond = preset(condition_name)
    path = Path(path)
    with open(path, "w") as f:
        yaml.safe_dump(cond.as_dict(), f, sort_keys=False)


if __name__ == "__main__":
    import sys

    name = sys.argv[1] if len(sys.argv) > 1 else "S0"
    write_default(condition_name=name)
    print(f"Wrote {DEFAULT_CONDITION_FILE} for condition {name}")
