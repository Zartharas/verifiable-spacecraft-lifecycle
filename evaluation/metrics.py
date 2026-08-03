"""
Metrics collector — reads the evidence store and computes per-run
statistics, plus (from Phase 4) an automated S0-S5 comparison table.

The full statistical evaluation (repeated trials, all 15 test cases,
credible baselines) is Phase 5 scope per Implementation-Plan.md. What's
here satisfies the Phase 4 exit criterion specifically: "a full S0-S5
comparison table can be generated from the evidence store automatically"
— not yet the final paper-ready evaluation.
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


def build_comparison_table(store: EvidenceStore | None = None) -> dict:
    """
    Automated S0-S5 comparison table (Phase 4 exit criterion): for each
    condition present in the evidence store, which test cases were
    injected and what fraction were caught (result == "fail" at the
    detecting stage means the injected condition was correctly rejected).

    Returns: {condition: {"test_cases": {test_case_id: {"seen": N, "caught": N}},
                           "stage_results": {stage: {"pass": N, "fail": N, "n/a": N}}}}
    """
    store = store or EvidenceStore()
    records = store.read_all()

    table: dict = {}
    for r in records:
        condition = r["condition"]
        table.setdefault(condition, {"test_cases": {}, "stage_results": {}})

        stage_results = table[condition]["stage_results"]
        stage_results.setdefault(r["pipeline_stage"], {"pass": 0, "fail": 0, "n/a": 0})
        stage_results[r["pipeline_stage"]][r["result"]] += 1

        tc = r["test_case_injected"]
        if tc:
            test_cases = table[condition]["test_cases"]
            test_cases.setdefault(tc, {"seen": 0, "caught": 0})
            test_cases[tc]["seen"] += 1
            if r["result"] == "fail":
                test_cases[tc]["caught"] += 1

    return table


def print_comparison_table() -> None:
    table = build_comparison_table()
    print("=== S0-S5 Comparison Table (auto-generated from evidence store) ===")
    for condition in sorted(table):
        print(f"\n{condition}:")
        test_cases = table[condition]["test_cases"]
        if not test_cases:
            print("  (no test cases injected under this condition)")
        for tc, counts in sorted(test_cases.items(), key=lambda kv: int(kv[0])):
            print(f"  test case #{tc}: seen={counts['seen']} caught={counts['caught']}")


if __name__ == "__main__":
    print_summary()
    print()
    print_comparison_table()
