"""
Phase 5 metric aggregation and reporting — reads
evaluation/results/phase5_raw_results.json (produced by experiment.py) and
computes the metrics defined in docs/PRD.md § 10, writing a JSON summary
and a human-readable Markdown report.

Read docs/PRD.md § 10 before interpreting any number this produces —
timing metrics are a sandbox-timing proxy, "manual evidence-processing
effort" is an evidence-record-count proxy, and none of this is against
the real cFS build (see STATUS.md "Claims status").

Run with: python3 evaluation/report.py   (after running experiment.py)
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
RAW_RESULTS_PATH = REPO_ROOT / "evaluation" / "results" / "phase5_raw_results.json"
SUMMARY_JSON_PATH = REPO_ROOT / "evaluation" / "results" / "phase5_summary.json"
REPORT_MD_PATH = REPO_ROOT / "evaluation" / "results" / "phase5_report.md"

# Test cases whose successful outcome is a completed rollback — "time to
# trusted restoration" applies to these. All others get "time to
# identify" as the more accurate label (detection, not recovery).
RECOVERY_TEST_CASES = {"10", "11", "12", "14"}


def _mean_stdev(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return values[0], 0.0
    return statistics.mean(values), statistics.stdev(values)


def load_raw_results() -> dict:
    with open(RAW_RESULTS_PATH) as f:
        return json.load(f)


def summarize_happy_path(raw: dict) -> dict:
    summary = {}
    baseline_sizes = None
    for condition, trials in raw["happy_path"].items():
        times = [t["elapsed_seconds"] for t in trials]
        mean_t, stdev_t = _mean_stdev(times)
        reproducible_rate = sum(1 for t in trials if t["reproducible"]) / len(trials)
        success_rate = sum(1 for t in trials if t["success"]) / len(trials)
        trace = trials[0]["traceability_completeness"]
        sizes = {
            "sbom_bytes": trials[0]["sbom_size"],
            "provenance_bytes": trials[0]["provenance_size"],
            "attestation_bytes": trials[0]["attestation_size"],
            "authorization_evidence_bytes": trials[0]["authorization_evidence_size"],
        }
        total_overhead_bytes = sum(sizes.values())
        if condition == "S0":
            baseline_sizes = total_overhead_bytes  # should be 0
        ages = [t["attestation_age_seconds"] for t in trials if t["attestation_age_seconds"] is not None]
        mean_age, _ = _mean_stdev(ages) if ages else (None, None)

        summary[condition] = {
            "success_rate": success_rate,
            "reproducible_rate": reproducible_rate,
            "mean_elapsed_seconds": mean_t,
            "stdev_elapsed_seconds": stdev_t,
            "traceability_completeness": trace,
            "record_count_mean": _mean_stdev([t["record_count"] for t in trials])[0],
            "storage_overhead_bytes": sizes,
            "total_overhead_bytes": total_overhead_bytes,
            "overhead_vs_s0_bytes": total_overhead_bytes - (baseline_sizes or 0),
            "mean_attestation_age_seconds": mean_age,
        }
    return summary


def summarize_attack_cases(raw: dict) -> dict:
    summary = {}
    for test_case, info in raw["attack_cases"].items():
        trials = info["trials"]
        times = [t["elapsed_seconds"] for t in trials]
        mean_t, stdev_t = _mean_stdev(times)
        caught = sum(1 for t in trials if t["caught"])
        summary[test_case] = {
            "condition": info["condition"],
            "detection_rate": caught / len(trials),
            "n_trials": len(trials),
            "metric_label": "time_to_trusted_restoration" if test_case in RECOVERY_TEST_CASES else "time_to_identify",
            "mean_elapsed_seconds": mean_t,
            "stdev_elapsed_seconds": stdev_t,
        }
    return summary


def build_confusion_matrix(raw: dict, happy_summary: dict, attack_summary: dict) -> dict:
    """
    Update acceptance accuracy, per condition: TP = legitimate updates
    correctly approved (happy path successes), FN = legitimate updates
    wrongly rejected, TN = attacks correctly rejected, FP = attacks
    wrongly approved. Aggregated across whichever attack cases apply to
    that condition.
    """
    matrix = {}
    for condition in raw["happy_path"]:
        tp = round(happy_summary[condition]["success_rate"] * len(raw["happy_path"][condition]))
        fn = len(raw["happy_path"][condition]) - tp

        relevant_cases = [tc for tc, info in raw["attack_cases"].items() if info["condition"] == condition]
        tn = sum(round(attack_summary[tc]["detection_rate"] * attack_summary[tc]["n_trials"]) for tc in relevant_cases)
        total_attack_trials = sum(attack_summary[tc]["n_trials"] for tc in relevant_cases)
        fp = total_attack_trials - tn

        matrix[condition] = {"TP": tp, "FN": fn, "TN": tn, "FP": fp, "attack_cases_covered": relevant_cases}
    return matrix


def generate_report() -> dict:
    raw = load_raw_results()
    happy_summary = summarize_happy_path(raw)
    attack_summary = summarize_attack_cases(raw)
    confusion = build_confusion_matrix(raw, happy_summary, attack_summary)

    summary = {
        "note": "See docs/PRD.md § 10 for metric definitions and baseline caveats before interpreting.",
        "happy_path": happy_summary,
        "attack_cases": attack_summary,
        "confusion_matrix": confusion,
    }

    SUMMARY_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_JSON_PATH, "w") as f:
        json.dump(summary, f, indent=2)

    _write_markdown_report(summary)
    return summary


def _write_markdown_report(summary: dict) -> None:
    lines = []
    lines.append("# Phase 5 Evaluation Report (auto-generated)")
    lines.append("")
    lines.append(
        "**Read `docs/PRD.md` § 10 before citing any number here.** Timing "
        "metrics are a sandbox-timing proxy, not hardware/real-mission "
        "timing. \"Manual evidence-processing effort\" is an evidence-"
        "record-count proxy, not measured human time. All results are "
        "against the stand-in stub artifact (`cfs-app/stub-telemetry-app`), "
        "not the real cFS build. See STATUS.md \"Claims status\" for the "
        "full caveat list."
    )
    lines.append("")
    lines.append("## Happy path per condition")
    lines.append("")
    lines.append(
        "| Condition | Success rate | Reproducible rate | Mean time (s) | "
        "Traceability | Overhead vs S0 (bytes) | Mean attestation age (s) |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for condition, s in summary["happy_path"].items():
        age = f"{s['mean_attestation_age_seconds']:.4f}" if s["mean_attestation_age_seconds"] is not None else "n/a"
        lines.append(
            f"| {condition} | {s['success_rate']:.0%} | {s['reproducible_rate']:.0%} | "
            f"{s['mean_elapsed_seconds']:.4f} | {s['traceability_completeness']:.0%} | "
            f"{s['overhead_vs_s0_bytes']} | {age} |"
        )
    lines.append("")
    lines.append("## Attack matrix detection results (all 15 test cases)")
    lines.append("")
    lines.append("| Test case | Condition | Detection rate | Metric | Mean time (s) | Stdev (s) |")
    lines.append("|---|---|---|---|---|---|")
    for tc in sorted(summary["attack_cases"], key=int):
        s = summary["attack_cases"][tc]
        lines.append(
            f"| #{tc} | {s['condition']} | {s['detection_rate']:.0%} | {s['metric_label']} | "
            f"{s['mean_elapsed_seconds']:.4f} | {s['stdev_elapsed_seconds']:.4f} |"
        )
    lines.append("")
    lines.append("## Update acceptance accuracy (confusion matrix, per condition)")
    lines.append("")
    lines.append("| Condition | TP | FN | TN | FP | Attack cases covered |")
    lines.append("|---|---|---|---|---|---|")
    for condition, m in summary["confusion_matrix"].items():
        cases = ", ".join(f"#{c}" for c in m["attack_cases_covered"]) or "(none)"
        lines.append(f"| {condition} | {m['TP']} | {m['FN']} | {m['TN']} | {m['FP']} | {cases} |")
    lines.append("")

    with open(REPORT_MD_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    summary = generate_report()
    print(f"Summary JSON written to {SUMMARY_JSON_PATH}")
    print(f"Markdown report written to {REPORT_MD_PATH}")
