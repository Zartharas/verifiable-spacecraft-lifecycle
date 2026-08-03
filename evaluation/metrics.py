"""
Metrics collector v1 — reads the evidence store and computes basic
per-run statistics. Full per-condition comparison tables (S0-S5) come in
Phase 5 once all conditions are implemented; this is a Phase 1 stub that
proves the evidence store -> metrics pipeline works end-to-end.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_store import EvidenceStore  # noqa: E402


def summarize(store: EvidenceStore | None = None) -> dict:
    store = store or EvidenceStore()
    records = store.read_all()

    by_stage_result = Counter((r["pipeline_stage"], r["result"]) for r in records)
    by_condition = Counter(r["condition"] for r in records)
    test_cases_triggered = Counter(
        r["test_case_injected"] for r in records if r["test_case_injected"]
    )

    total_records = len(records)
    fail_count = sum(1 for r in records if r["result"] == "fail")
    pass_count = sum(1 for r in records if r["result"] == "pass")

    return {
        "total_evidence_records": total_records,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "by_stage_result": dict(by_stage_result),
        "by_condition": dict(by_condition),
        "test_cases_triggered": dict(test_cases_triggered),
    }


def print_summary() -> None:
    summary = summarize()
    print("=== Evidence Store Summary ===")
    print(f"Total records: {summary['total_evidence_records']}")
    print(f"Pass: {summary['pass_count']}  Fail: {summary['fail_count']}")
    print("\nBy (stage, result):")
    for (stage, result), count in sorted(summary["by_stage_result"].items()):
        print(f"  {stage:35s} {result:5s} x{count}")
    print("\nBy condition:")
    for condition, count in sorted(summary["by_condition"].items()):
        print(f"  {condition}: {count}")
    if summary["test_cases_triggered"]:
        print("\nTest cases triggered:")
        for tc, count in sorted(summary["test_cases_triggered"].items()):
            print(f"  test case #{tc}: {count}")


if __name__ == "__main__":
    print_summary()
