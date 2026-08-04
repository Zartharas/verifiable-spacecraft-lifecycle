# Phase 5 Evaluation Report (auto-generated)

**Read `docs/PRD.md` § 10 before citing any number here.** Timing metrics are a sandbox-timing proxy, not hardware/real-mission timing. "Manual evidence-processing effort" is an evidence-record-count proxy, not measured human time. All results are against the stand-in stub artifact (`cfs-app/stub-telemetry-app`), not the real cFS build. See STATUS.md "Claims status" for the full caveat list.

**All rates below are 95% Wilson score intervals; all timing means are 95% normal-approximation intervals** (see this file's module docstring for why two different methods are used). n = number of trials, shown per row.

## Happy path per condition

| Condition | n | Success rate (95% CI) | Reproducible rate (95% CI) | Mean time s (95% CI) | Traceability | Overhead vs S0 (bytes) | Mean attestation age (s) |
|---|---|---|---|---|---|---|---|
| S0 | 30 | 100% (89%-100%) | 100% (89%-100%) | 0.2277 (0.2144-0.2410) | 100% | 0 | n/a |
| S1 | 30 | 100% (89%-100%) | 100% (89%-100%) | 0.2373 (0.2159-0.2587) | 100% | 613 | n/a |
| S2 | 30 | 100% (89%-100%) | 100% (89%-100%) | 0.2529 (0.2398-0.2661) | 100% | 1264 | n/a |
| S3 | 30 | 100% (89%-100%) | 100% (89%-100%) | 0.2715 (0.2577-0.2853) | 100% | 1631 | 0.0013 |
| S4 | 30 | 100% (89%-100%) | 100% (89%-100%) | 0.2948 (0.2782-0.3115) | 100% | 1624 | 0.0014 |
| S5 | 30 | 100% (89%-100%) | 100% (89%-100%) | 0.3281 (0.3105-0.3458) | 100% | 5747 | 0.0051 |

## Attack matrix detection results (all 15 test cases)

| Test case | Condition | n | Detection rate (95% CI) | Metric | Mean time s (95% CI) |
|---|---|---|---|---|---|
| #1 | S2 | 30 | 100% (89%-100%) | time_to_identify | 0.2627 (0.2511-0.2743) |
| #2 | S2 | 30 | 100% (89%-100%) | time_to_identify | 0.2520 (0.2366-0.2673) |
| #3 | S1 | 30 | 100% (89%-100%) | time_to_identify | 0.2600 (0.2425-0.2776) |
| #4 | S1 | 30 | 100% (89%-100%) | time_to_identify | 0.2715 (0.2548-0.2883) |
| #5 | S2 | 30 | 100% (89%-100%) | time_to_identify | 0.2543 (0.2463-0.2623) |
| #6 | S0 | 30 | 100% (89%-100%) | time_to_identify | 0.2631 (0.2480-0.2782) |
| #7 | S0 | 30 | 100% (89%-100%) | time_to_identify | 0.2509 (0.2406-0.2611) |
| #8 | S5 | 30 | 100% (89%-100%) | time_to_identify | 0.2847 (0.2738-0.2956) |
| #9 | S2 | 30 | 100% (89%-100%) | time_to_identify | 0.2684 (0.2594-0.2773) |
| #10 | S4 | 30 | 100% (89%-100%) | time_to_trusted_restoration | 0.3034 (0.2883-0.3185) |
| #11 | S4 | 30 | 100% (89%-100%) | time_to_trusted_restoration | 0.2965 (0.2794-0.3137) |
| #12 | S4 | 30 | 100% (89%-100%) | time_to_trusted_restoration | 0.3202 (0.3100-0.3304) |
| #13 | S5 | 30 | 100% (89%-100%) | time_to_identify | 0.0002 (0.0002-0.0002) |
| #14 | S4 | 30 | 100% (89%-100%) | time_to_trusted_restoration | 0.3011 (0.2873-0.3149) |
| #15 | S5 | 30 | 100% (89%-100%) | time_to_identify | 0.4020 (0.3779-0.4260) |

## Update acceptance accuracy (confusion matrix, per condition)

| Condition | TP | FN | TN | FP | Attack cases covered |
|---|---|---|---|---|---|
| S0 | 30 | 0 | 60 | 0 | #6, #7 |
| S1 | 30 | 0 | 60 | 0 | #3, #4 |
| S2 | 30 | 0 | 120 | 0 | #1, #2, #5, #9 |
| S3 | 30 | 0 | 0 | 0 | (none) |
| S4 | 30 | 0 | 120 | 0 | #10, #11, #12, #14 |
| S5 | 30 | 0 | 90 | 0 | #8, #13, #15 |

