"""
Evaluation-code correctness tests for evaluation/report.py (2026-08-05).

Directly answers reviewer objection #9 in docs/Research-Paper-Outline.md:
"how do we know the evaluation/metrics code itself is correct, independent
of the pipeline it measures?" Every number in the paper's tables (detection
rates, success rates, timing means, all with 95% CIs) flows through
`_wilson_ci`, `_mean_ci`, `_mean_stdev`, and the two `summarize_*`
aggregators in this module. None of that had a dedicated test before this
file — it was only ever exercised indirectly by running the full
evaluation harness and eyeballing the output.

Verification strategy, in order of strength:

1. `_wilson_ci` is cross-checked against `statsmodels.stats.proportion.
   proportion_confint(method="wilson")` — an independent, third-party
   implementation, not a second copy of the same formula. Reference
   values below were generated with statsmodels 0.14.6 (2026-08-05) via
   the exact 97.5th-percentile normal quantile
   z = 1.959963984540054 (scipy.stats.norm.ppf(0.975)), passed to
   `_wilson_ci` explicitly, so this test has zero dependency on
   statsmodels/scipy being installed. Reproduce with:
     from statsmodels.stats.proportion import proportion_confint
     proportion_confint(successes, n, alpha=0.05, method="wilson")
   `_wilson_ci`'s own default (z=1.96, a common rounded convention) is
   verified separately, to a looser tolerance, against the same
   reference — the two differ only in the 4th-5th decimal place, which
   is exactly the expected effect of 1.96 vs the exact quantile.

2. `_mean_ci` / `_mean_stdev` are cross-checked against a manual,
   independently-written closed-form computation using `statistics.
   mean`/`statistics.stdev` and the same exact z — not by re-deriving
   `_mean_ci`'s own formula, but by recomputing the textbook definition
   from scratch in the test.

3. Boundary and structural properties that must hold regardless of which
   CI method is "correct" in some absolute sense: the interval must
   contain the point estimate, must widen as n shrinks, must stay within
   [0, 1] for rates, and must collapse to a point at n<=1.

4. `summarize_happy_path` / `summarize_attack_cases` /
   `build_confusion_matrix` are exercised against a small, hand-computed
   synthetic `raw` fixture (not the real evaluation output) so the
   *aggregation* logic (which trials get grouped into which condition,
   how the confusion matrix rounds fractional counts) is checked
   independently of any real trial data.

Run with: pytest tests/test_evaluation_report_correctness.py -v
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "evaluation"))

from report import (  # noqa: E402
    _mean_ci,
    _mean_stdev,
    _wilson_ci,
    build_confusion_matrix,
    summarize_attack_cases,
    summarize_happy_path,
)

# scipy.stats.norm.ppf(0.975), i.e. the exact 97.5th percentile of the
# standard normal distribution -- what statsmodels uses internally for a
# 95% CI (alpha=0.05). _wilson_ci defaults to the rounded z=1.96.
EXACT_Z = 1.959963984540054

# Reference (successes, n) -> (lo, hi) pairs from
# statsmodels.stats.proportion.proportion_confint(s, n, alpha=0.05,
# method="wilson"), statsmodels 0.14.6, generated 2026-08-05. An
# independent, third-party Wilson-interval implementation -- not a second
# copy of report.py's own formula.
STATSMODELS_WILSON_REFERENCE = {
    (30, 30): (0.8864866068260311, 1.0),
    (0, 30): (0.0, 0.1135133931739688),
    (15, 30): (0.3315412564053376, 0.6684587435946624),
    (29, 30): (0.8332960900859081, 0.9940914096183875),
    (1, 30): (0.005908590381612455, 0.16670390991409176),
    (3, 5): (0.2307242812760129, 0.8823792257673522),
    (5, 5): (0.5655175352168252, 1.0),
    (0, 5): (0.0, 0.43448246478317487),
}


# --- _wilson_ci: cross-checked against an independent library -----------


@pytest.mark.parametrize("successes,n", list(STATSMODELS_WILSON_REFERENCE.keys()))
def test_wilson_ci_matches_statsmodels_at_exact_z(successes, n):
    """With the same z (exact normal quantile, not the rounded 1.96
    convention), _wilson_ci must match an independent third-party
    implementation to numerical precision."""
    lo, hi = _wilson_ci(successes, n, z=EXACT_Z)
    ref_lo, ref_hi = STATSMODELS_WILSON_REFERENCE[(successes, n)]
    assert lo == pytest.approx(ref_lo, abs=1e-9)
    assert hi == pytest.approx(ref_hi, abs=1e-9)


@pytest.mark.parametrize("successes,n", list(STATSMODELS_WILSON_REFERENCE.keys()))
def test_wilson_ci_default_z_close_to_exact_z(successes, n):
    """The module's actual default (z=1.96) should be close to, but not
    identical to, the exact-quantile reference -- confirming the rounding
    convention is a deliberate, small, well-understood approximation and
    not a sign the formula itself is wrong."""
    lo, hi = _wilson_ci(successes, n)  # default z=1.96
    ref_lo, ref_hi = STATSMODELS_WILSON_REFERENCE[(successes, n)]
    assert lo == pytest.approx(ref_lo, abs=5e-4)
    assert hi == pytest.approx(ref_hi, abs=5e-4)


# --- _wilson_ci: boundary and structural properties ----------------------


def test_wilson_ci_n_zero_returns_zero_width_at_origin():
    assert _wilson_ci(0, 0) == (0.0, 0.0)


def test_wilson_ci_bounds_stay_within_unit_interval():
    for successes in range(0, 31):
        lo, hi = _wilson_ci(successes, 30)
        assert 0.0 <= lo <= hi <= 1.0


def test_wilson_ci_contains_point_estimate():
    for successes, n in [(1, 3), (10, 30), (29, 30), (0, 10), (10, 10)]:
        lo, hi = _wilson_ci(successes, n)
        p = successes / n
        assert lo <= p <= hi


def test_wilson_ci_narrows_as_n_grows_at_fixed_rate():
    """Same observed proportion (50%), more trials -> tighter interval."""
    widths = []
    for n in (10, 100, 1000):
        lo, hi = _wilson_ci(n // 2, n)
        widths.append(hi - lo)
    assert widths[0] > widths[1] > widths[2]


def test_wilson_ci_boundary_rates_do_not_collapse_to_a_point():
    """This is the exact failure mode a normal-approximation CI has at
    p=0 or p=1 (module docstring) -- Wilson's interval must not report a
    zero-width interval for a 100%-or-0%-observed rate at finite n."""
    lo, hi = _wilson_ci(30, 30)
    assert hi - lo > 0.0
    lo, hi = _wilson_ci(0, 30)
    assert hi - lo > 0.0


# --- _mean_stdev / _mean_ci: cross-checked against an independent, -------
# --- from-scratch closed-form computation --------------------------------


@pytest.mark.parametrize(
    "values",
    [
        [1.0, 2.0, 3.0, 4.0, 5.0],
        [0.5, 0.5, 0.5],
        [0.1, 0.9, 0.4, 0.4, 0.7, 0.2],
    ],
)
def test_mean_ci_matches_independent_closed_form(values):
    import statistics as _stats

    mean_ref = _stats.mean(values)
    stdev_ref = _stats.stdev(values)
    half_width_ref = EXACT_Z * stdev_ref / (len(values) ** 0.5)
    lo_ref, hi_ref = mean_ref - half_width_ref, mean_ref + half_width_ref

    lo, hi = _mean_ci(values, z=EXACT_Z)
    assert lo == pytest.approx(lo_ref, abs=1e-9)
    assert hi == pytest.approx(hi_ref, abs=1e-9)


def test_mean_stdev_matches_stdlib_statistics():
    import statistics as _stats

    values = [2.5, 7.1, 3.3, 9.9, 1.0]
    mean, stdev = _mean_stdev(values)
    assert mean == pytest.approx(_stats.mean(values))
    assert stdev == pytest.approx(_stats.stdev(values))


def test_mean_stdev_empty_list_returns_zero_not_error():
    assert _mean_stdev([]) == (0.0, 0.0)


def test_mean_stdev_single_value_has_zero_stdev():
    assert _mean_stdev([4.2]) == (4.2, 0.0)


def test_mean_ci_single_value_collapses_to_point():
    """statistics.stdev requires n>=2 -- _mean_ci must guard this itself
    rather than propagating a StatisticsError, since n=1 happy-path/attack
    cells are a real (if rare) possibility in the raw results."""
    assert _mean_ci([7.3]) == (7.3, 7.3)


def test_mean_ci_empty_list_returns_zero_not_error():
    assert _mean_ci([]) == (0.0, 0.0)


def test_mean_ci_contains_the_mean():
    values = [1.0, 1.5, 2.0, 2.5, 10.0]
    lo, hi = _mean_ci(values)
    import statistics as _stats

    assert lo <= _stats.mean(values) <= hi


# --- Aggregation logic: summarize_* / build_confusion_matrix, against a --
# --- small, hand-computed synthetic fixture (not real evaluation data) ---


def _synthetic_raw() -> dict:
    """3 happy-path trials at S1 (2 successes, 1 failure -- deliberately
    NOT 100%, so success_rate isn't accidentally always 1.0 in the test)
    and 4 trials of one attack case at S1 (3 caught, 1 missed)."""
    return {
        "happy_path": {
            "S1": [
                {
                    "elapsed_seconds": 1.0,
                    "reproducible": True,
                    "success": True,
                    "traceability_completeness": 1.0,
                    "sbom_size": 100,
                    "provenance_size": 0,
                    "attestation_size": 0,
                    "authorization_evidence_size": 0,
                    "attestation_age_seconds": None,
                    "record_count": 5,
                },
                {
                    "elapsed_seconds": 2.0,
                    "reproducible": True,
                    "success": True,
                    "traceability_completeness": 1.0,
                    "sbom_size": 100,
                    "provenance_size": 0,
                    "attestation_size": 0,
                    "authorization_evidence_size": 0,
                    "attestation_age_seconds": None,
                    "record_count": 5,
                },
                {
                    "elapsed_seconds": 3.0,
                    "reproducible": False,
                    "success": False,
                    "traceability_completeness": 1.0,
                    "sbom_size": 100,
                    "provenance_size": 0,
                    "attestation_size": 0,
                    "authorization_evidence_size": 0,
                    "attestation_age_seconds": None,
                    "record_count": 5,
                },
            ]
        },
        "attack_cases": {
            "4": {
                "condition": "S1",
                "trials": [
                    {"elapsed_seconds": 0.5, "caught": True},
                    {"elapsed_seconds": 0.6, "caught": True},
                    {"elapsed_seconds": 0.7, "caught": True},
                    {"elapsed_seconds": 0.8, "caught": False},
                ],
            }
        },
    }


def test_summarize_happy_path_rates_and_counts():
    raw = _synthetic_raw()
    summary = summarize_happy_path(raw)
    s1 = summary["S1"]
    assert s1["n_trials"] == 3
    assert s1["success_rate"] == pytest.approx(2 / 3)
    assert s1["reproducible_rate"] == pytest.approx(2 / 3)
    assert s1["mean_elapsed_seconds"] == pytest.approx(2.0)
    assert s1["record_count_mean"] == pytest.approx(5.0)
    # success/reproducible rate CIs must actually contain the point rate
    lo, hi = s1["success_rate_ci95"]
    assert lo <= s1["success_rate"] <= hi


def test_summarize_attack_cases_detection_rate():
    raw = _synthetic_raw()
    summary = summarize_attack_cases(raw)
    c4 = summary["4"]
    assert c4["n_trials"] == 4
    assert c4["detection_rate"] == pytest.approx(3 / 4)
    assert c4["condition"] == "S1"
    # test case "4" is not in RECOVERY_TEST_CASES -> "time_to_identify"
    assert c4["metric_label"] == "time_to_identify"


def test_build_confusion_matrix_counts_match_hand_computation():
    raw = _synthetic_raw()
    happy_summary = summarize_happy_path(raw)
    attack_summary = summarize_attack_cases(raw)
    matrix = build_confusion_matrix(raw, happy_summary, attack_summary)
    s1 = matrix["S1"]
    # 3 happy-path trials, success_rate 2/3 -> TP = round(2/3 * 3) = 2, FN = 1
    assert s1["TP"] == 2
    assert s1["FN"] == 1
    # 4 attack trials, detection_rate 3/4 -> TN = round(3/4 * 4) = 3, FP = 1
    assert s1["TN"] == 3
    assert s1["FP"] == 1
    assert s1["attack_cases_covered"] == ["4"]
