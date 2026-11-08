"""
Uptane coverage of the 15-case matrix, derived from the Uptane Standard
2.1.0 text (https://uptane.org/docs/2.1.0/standard/uptane-standard, read
28 October 2026). SPECIFICATION-BASED, NOT EXECUTED: no Uptane
implementation was run. Each case is classified from what the standard
requires, with the section it rests on.

Status values
  native               the standard requires a mechanism for this failure
  partial_analogue     the standard has a related mechanism that does not
                       specify the behavior the case tests
  stated_out_of_scope  the standard names this class as out of scope
  not_addressed        no concept in the standard (searched for it)
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
OUT = REPO_ROOT / "evaluation" / "results" / "phase11_uptane_spec_analysis.json"

CASES = {
    "1": ("stated_out_of_scope", "S3.4 excludes compromise of the supply chain, including the build system; a binary built from other source and then signed is consistent with signed Targets metadata."),
    "2": ("stated_out_of_scope", "S3.4 excludes the supply chain and points to in-toto and Scudo as complements; the standard has no provenance structure."),
    "3": ("not_addressed", "No SBOM or component inventory appears in the standard."),
    "4": ("not_addressed", "No dependency or vulnerability data appears; S3.4 excludes malware embedded in a trusted package."),
    "5": ("stated_out_of_scope", "Delegations (S5.1.2.1) authorize which key signs which images, not which build system produced them; build systems are excluded by S3.4."),
    "6": ("native", "S5.4.3.4 step 7: all hashes and the length in the Targets metadata must match the image; arbitrary-software attack listed in S4.3.4."),
    "7": ("native", "Root role distributes and revokes keys (S2.2, S5.2.2)."),
    "8": ("not_addressed", "No policy language. S5.4.3.4 step 3 checks a hardware identifier, which does not evaluate configuration content."),
    "9": ("native", "Rollback attack (S4.3.3); release counter check (S5.4.3.4 step 5); version checks on Timestamp, Snapshot and Targets (S5.4.4.4 to S5.4.4.6)."),
    "10": ("partial_analogue", "S5.4.3.5 says installation SHOULD occur with a backup of the current image and metadata in case it fails; no detection or recovery procedure is specified."),
    "11": ("not_addressed", "No post-install health check or health concept appears."),
    "12": ("partial_analogue", "ECU version report carries the latest verifiable time and a nonce (S5.4.2.1.2); the Director checks time and nonce reuse (S5.3.2.1 steps 3 and 4). Staleness of an installed-state quote is not specified."),
    "13": ("partial_analogue", "Director compares the manifest with its inventory database (S5.3.2.1 step 3), but the required checks cover ECU presence, signatures and time; the database records identity and keys, not installed images or policy (S5.3.2.2)."),
    "14": ("not_addressed", "The backup image mentioned in S5.4.3.5 is a precondition; no verification of a recovery image is specified."),
    "15": ("partial_analogue", "The ECU-signed version report includes the hash of the installed image (S5.4.2.1.2). It is self-reported, and the threat model (S4.2) assumes at most one compromised ECU per vehicle."),
}


def build() -> dict:
    counts: dict[str, int] = {}
    for status, _ in CASES.values():
        counts[status] = counts.get(status, 0) + 1
    return {
        "source": "Uptane Standard 2.1.0",
        "executed": False,
        "basis": "specification text only",
        "counts": counts,
        "cases": {k: {"status": s, "basis": b} for k, (s, b) in CASES.items()},
    }


if __name__ == "__main__":
    out = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(out["counts"])
