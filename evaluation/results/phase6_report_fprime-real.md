# Phase 6 (stack: fprime-real) Evaluation Report (auto-generated)

**Read `docs/PRD.md` § 10 before citing any number here.** Timing metrics are a sandbox-timing proxy, not hardware/real-mission timing. "Manual evidence-processing effort" is an evidence-record-count proxy, not measured human time. All results are against the stand-in stub artifact for stack 'fprime-real'. See STATUS.md "Claims status" for the full caveat list.

**All rates below are 95% Wilson score intervals; all timing means are 95% normal-approximation intervals** (see this file's module docstring for why two different methods are used). n = number of trials, shown per row.

## Happy path per condition

| Condition | n | Success rate (95% CI) | Reproducible rate (95% CI) | Mean time s (95% CI) | Traceability | Overhead vs S0 (bytes) | Mean attestation age (s) |
|---|---|---|---|---|---|---|---|
| S0 | 30 | 100% (89%-100%) | 100% (89%-100%) | 0.3754 (0.3681-0.3826) | 100% | 0 | n/a |
| S1 | 30 | 100% (89%-100%) | 100% (89%-100%) | 0.3853 (0.3718-0.3989) | 100% | 583 | n/a |
| S2 | 30 | 100% (89%-100%) | 100% (89%-100%) | 0.4449 (0.4280-0.4619) | 100% | 1219 | n/a |
| S3 | 30 | 100% (89%-100%) | 100% (89%-100%) | 2.0019 (1.9774-2.0263) | 100% | 1569 | 0.0088 |
| S4 | 30 | 100% (89%-100%) | 100% (89%-100%) | 1.9761 (1.9563-1.9958) | 100% | 1578 | 0.0077 |
| S5 | 30 | 100% (89%-100%) | 100% (89%-100%) | 2.3252 (2.2964-2.3539) | 100% | 5703 | 0.0075 |

## Attack matrix detection results (all 15 test cases)

| Test case | Condition | n | Detection rate (95% CI) | Metric | Mean time s (95% CI) |
|---|---|---|---|---|---|
| #1 | S2 | 30 | 100% (89%-100%) | time_to_identify | 0.3923 (0.3820-0.4026) |
| #2 | S2 | 30 | 100% (89%-100%) | time_to_identify | 0.0939 (0.0927-0.0951) |
| #3 | S1 | 30 | 100% (89%-100%) | time_to_identify | 0.3521 (0.3415-0.3628) |
| #4 | S1 | 30 | 100% (89%-100%) | time_to_identify | 0.3508 (0.3406-0.3610) |
| #5 | S2 | 30 | 100% (89%-100%) | time_to_identify | 0.3843 (0.3725-0.3962) |
| #6 | S0 | 30 | 100% (89%-100%) | time_to_identify | 0.3861 (0.3693-0.4029) |
| #7 | S0 | 30 | 100% (89%-100%) | time_to_identify | 0.3406 (0.3318-0.3494) |
| #8 | S5 | 30 | 100% (89%-100%) | time_to_identify | 0.4094 (0.3974-0.4215) |
| #9 | S2 | 30 | 100% (89%-100%) | time_to_identify | 0.4380 (0.4240-0.4520) |
| #10 | S4 | 30 | 100% (89%-100%) | time_to_trusted_restoration | 0.5049 (0.4780-0.5319) |
| #11 | S4 | 30 | 100% (89%-100%) | time_to_trusted_restoration | 0.5390 (0.5142-0.5637) |
| #12 | S4 | 30 | 100% (89%-100%) | time_to_trusted_restoration | 2.1303 (2.0802-2.1804) |
| #13 | S5 | 30 | 100% (89%-100%) | time_to_identify | 0.0003 (0.0002-0.0003) |
| #14 | S4 | 30 | 100% (89%-100%) | time_to_trusted_restoration | 0.6208 (0.5916-0.6500) |
| #15 | S5 | 30 | 100% (89%-100%) | time_to_identify | 1.0328 (0.9079-1.1577) |

## Update acceptance accuracy (confusion matrix, per condition)

| Condition | TP | FN | TN | FP | Attack cases covered |
|---|---|---|---|---|---|
| S0 | 30 | 0 | 60 | 0 | #6, #7 |
| S1 | 30 | 0 | 60 | 0 | #3, #4 |
| S2 | 30 | 0 | 120 | 0 | #1, #2, #5, #9 |
| S3 | 30 | 0 | 0 | 0 | (none) |
| S4 | 30 | 0 | 120 | 0 | #10, #11, #12, #14 |
| S5 | 30 | 0 | 90 | 0 | #8, #13, #15 |

