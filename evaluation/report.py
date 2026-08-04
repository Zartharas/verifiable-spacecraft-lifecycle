"""
Phase 5 metric aggregation and reporting — reads
evaluation/results/phase5_raw_results.json (produced by experiment.py) and
computes the metrics defined in docs/PRD.md § 10, writing a JSON summary
and a human-readable Markdown report.

Read docs/PRD.md § 10 before interpreting any number this produces —
timing metrics are a sandbox-timing proxy, "manual evidence-processing
effort" is an evidence-record-count proxy, and none of this is against
the real cFS build (see STATUS.md "Claims status").

Phase 6 (generalizability): pass a stack name as the CLI argument to
summarize a non-"cfs" stack's raw results (produced by
`evaluation/experiment.py <stack>`) instead — e.g.
`python3 evaluation/report.py fprime` reads
`phase6_raw_results_fprime.json` and writes `phase6_summary_fprime.json`
/ `phase6_report_fprime.md`. All aggregation logic below is identical
regardless of stack; only the file paths differ.

Run with: python3 evaluation/report.py           # cfs (Phase 5, unchanged)
          python3 evaluation/report.py fprime     # fprime (Phase 6)

Phase 8 (2026-08-03): added 95% confidence intervals, per the
rejection-risk review in docs/Research-Paper-Outline.md flagging that
reporting a bare rate/mean from 5 trials with no interval was the
weakest single methodological gap. Two different CI methods are used
deliberately, not one applied blindly to everything:

- Rates (success/reproducible/detection rate) use the Wilson score
  interval, not a normal approximation. A normal-approximation CI on a
  proportion breaks down exactly at the boundary (a 100% or 0% observed
  rate — which is common here, since most conditions/cases show
  clean 100% or 0% across trials) and can report an invalid interval
  like [1.0, 1.0] with zero width or extend past [0, 1]. Wilson's
  interval handles boundary rates correctly and needs no library beyond
  stdlib math.
- Timing means use a normal-approximation CI (mean +/- 1.96 *
  stdev/sqrt(n)), which is the standard choice for a continuous
  measurement at n=30 — reasonable here given the Central Limit Theorem
  and that these are sandbox-timing measurements, not a bounded rate.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def _paths_for(stack: str) -> tuple[Path, Path, Path]:
    results_dir = REPO_ROOT / "evaluation" / "results"
    if stack == "cfs":
        return (
            results_dir / "phase5_raw_results.json",
            results_dir / "phase5_summary.json",
            results_dir / "phase5_report.md",
        )
    return (
        results_dir / f"phase6_raw_results_{stack}.json",
        results_dir / f"phase6_summary_{stack}.json",
        results_dir / f"phase6_report_{stack}.md",
    )


_STACK_ARG = sys.argv[1] if len(sys.argv) > 1 else "cfs"
RAW_RESULTS_PATH, SUMMARY_JSON_PATH, REPORT_MD_PATH = _paths_for(_STACK_ARG)

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


def _wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion. Chosen over a
    normal-approximation CI specifically because it stays valid at the
    boundary (p=0 or p=1), which is the common case here — see module
    docstring."""
    if n == 0:
        return 0.0, 0.0
    p = successes / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half_width = z * ((p * (1 - p) / n) + (z**2 / (4 * n**2))) ** 0.5 / denom
    lo = max(0.0, center - half_width)
    hi = min(1.0, center + half_width)
    return lo, hi


def _mean_ci(values: list[float], z: float = 1.96) -> tuple[float, float]:
    """95% normal-approximation CI for a mean — see module docstring for
    why this (rather than Wilson) is used for continuous timing values."""
    if len(values) < 2:
        return (values[0], values[0]) if values else (0.0, 0.0)
    mean_v, stdev_v = _mean_stdev(values)
    half_width = z * stdev_v / (len(values) ** 0.5)
    return mean_v - half_width, mean_v + half_width


def load_raw_results() -> dict:
    with open(RAW_RESULTS_PATH) as f:
        return json.load(f)


def summarize_happy_path(raw: dict) -> dict:
    summary = {}
    baseline_sizes = None
    for condition, trials in raw["happy_path"].items():
        times = [t["elapsed_seconds"] for t in trials]
        n = len(trials)
        mean_t, stdev_t = _mean_stdev(times)
        mean_t_ci = _mean_ci(times)
        reproducible_successes = sum(1 for t in trials if t["reproducible"])
        success_successes = sum(1 for t in trials if t["success"])
        reproducible_rate = reproducible_successes / n
        success_rate = success_successes / n
        reproducible_rate_ci = _wilson_ci(reproducible_successes, n)
        success_rate_ci = _wilson_ci(success_successes, n)
        # Second red-team pass, finding #8 (2026-08-05): traceability and
        # every artifact-size figure used to be taken solely from
        # trials[0] — timing and success/reproducibility were properly
        # aggregated across all n_trials, these weren't. If a later
        # trial ever regressed (e.g. a stage's evidence record went
        # missing only sometimes), this summary would never have shown
        # it. These fields SHOULD be deterministic across trials for the
        # same condition (same code path every time), so trial[0] remains
        # the reported value, but now every trial is checked against it
        # and any divergence is surfaced explicitly rather than silently
        # possible.
        trace_values = {t["traceability_completeness"] for t in trials}
        size_field_names = {
            "sbom_bytes": "sbom_size",
            "provenance_bytes": "provenance_size",
            "attestation_bytes": "attestation_size",
            "authorization_evidence_bytes": "authorization_evidence_size",
        }
        size_value_sets = {
            label: {t[raw_key] for t in trials} for label, raw_key in size_field_names.items()
        }
        inconsistencies = []
        if len(trace_values) > 1:
            inconsistencies.append(
                f"traceability_completeness varied across trials: {sorted(trace_values)}"
            )
        for label, values in size_value_sets.items():
            if len(values) > 1:
                inconsistencies.append(f"{label} varied across trials: {sorted(values)}")

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
            "success_rate_ci95": success_rate_ci,
            "reproducible_rate": reproducible_rate,
            "reproducible_rate_ci95": reproducible_rate_ci,
            "mean_elapsed_seconds": mean_t,
            "mean_elapsed_seconds_ci95": mean_t_ci,
            "stdev_elapsed_seconds": stdev_t,
            "n_trials": n,
            "traceability_completeness": trace,
            "record_count_mean": _mean_stdev([t["record_count"] for t in trials])[0],
            "storage_overhead_bytes": sizes,
            "total_overhead_bytes": total_overhead_bytes,
            "overhead_vs_s0_bytes": total_overhead_bytes - (baseline_sizes or 0),
            "mean_attestation_age_seconds": mean_age,
            "trial_metrics_consistent": len(inconsistencies) == 0,
            "trial_metrics_inconsistencies": inconsistencies,
        }
    return summary


def summarize_attack_cases(raw: dict) -> dict:
    summary = {}
    for test_case, info in raw["attack_cases"].items():
        trials = info["trials"]
        times = [t["elapsed_seconds"] for t in trials]
        n = len(trials)
        mean_t, stdev_t = _mean_stdev(times)
        mean_t_ci = _mean_ci(times)
        caught = sum(1 for t in trials if t["caught"])
        summary[test_case] = {
            "condition": info["condition"],
            "detection_rate": caught / n,
            "detection_rate_ci95": _wilson_ci(caught, n),
            "n_trials": n,
            "metric_label": "time_to_trusted_restoration" if test_case in RECOVERY_TEST_CASES else "time_to_identify",
            "mean_elapsed_seconds": mean_t,
            "mean_elapsed_seconds_ci95": mean_t_ci,
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


_STACK_ARTIFACT_DESC = {
    "cfs": "the stand-in stub artifact (`cfs-app/stub-telemetry-app`), not the real cFS build",
    "fprime": "the stand-in stub artifact (`fprime-app/stub-component-app`), not the real F Prime (F´) framework",
}


def _write_markdown_report(summary: dict) -> None:
    phase_label = "Phase 5" if _STACK_ARG == "cfs" else f"Phase 6 (stack: {_STACK_ARG})"
    artifact_desc = _STACK_ARTIFACT_DESC.get(
        _STACK_ARG, f"the stand-in stub artifact for stack '{_STACK_ARG}'"
    )
    lines = []
    lines.append(f"# {phase_label} Evaluation Report (auto-generated)")
    lines.append("")
    lines.append(
        "**Read `docs/PRD.md` § 10 before citing any number here.** Timing "
        "metrics are a sandbox-timing proxy, not hardware/real-mission "
        "timing. \"Manual evidence-processing effort\" is an evidence-"
        f"record-count proxy, not measured human time. All results are "
        f"against {artifact_desc}. See STATUS.md \"Claims status\" for the "
        "full caveat list."
    )
    lines.append("")
    lines.append(
        "**All rates below are 95% Wilson score intervals; all timing means "
        "are 95% normal-approximation intervals** (see this file's module "
        "docstring for why two different methods are used). n = number of "
        "trials, shown per row."
    )
    lines.append("")
    lines.append("## Happy path per condition")
    lines.append("")
    lines.append(
        "| Condition | n | Success rate (95% CI) | Reproducible rate (95% CI) | Mean time s (95% CI) | "
        "Traceability | Overhead vs S0 (bytes) | Mean attestation age (s) |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for condition, s in summary["happy_path"].items():
        age = f"{s['mean_attestation_age_seconds']:.4f}" if s["mean_attestation_age_seconds"] is not None else "n/a"
        succ_lo, succ_hi = s["success_rate_ci95"]
        repro_lo, repro_hi = s["reproducible_rate_ci95"]
        t_lo, t_hi = s["mean_elapsed_seconds_ci95"]
        lines.append(
            f"| {condition} | {s['n_trials']} | {s['success_rate']:.0%} ({succ_lo:.0%}-{succ_hi:.0%}) | "
            f"{s['reproducible_rate']:.0%} ({repro_lo:.0%}-{repro_hi:.0%}) | "
            f"{s['mean_elapsed_seconds']:.4f} ({t_lo:.4f}-{t_hi:.4f}) | "
            f"{s['traceability_completeness']:.0%} | "
            f"{s['overhead_vs_s0_bytes']} | {age} |"
        )
    lines.append("")
    lines.append("## Attack matrix detection results (all 15 test cases)")
    lines.append("")
    lines.append("| Test case | Condition | n | Detection rate (95% CI) | Metric | Mean time s (95% CI) |")
    lines.append("|---|---|---|---|---|---|")
    for tc in sorted(summary["attack_cases"], key=int):
        s = summary["attack_cases"][tc]
        det_lo, det_hi = s["detection_rate_ci95"]
        t_lo, t_hi = s["mean_elapsed_seconds_ci95"]
        lines.append(
            f"| #{tc} | {s['condition']} | {s['n_trials']} | "
            f"{s['detection_rate']:.0%} ({det_lo:.0%}-{det_hi:.0%}) | {s['metric_label']} | "
            f"{s['mean_elapsed_seconds']:.4f} ({t_lo:.4f}-{t_hi:.4f}) |"
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
