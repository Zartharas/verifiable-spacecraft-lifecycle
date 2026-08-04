# Phase 6 (stack: fprime) Evaluation Report (auto-generated)

**Read `docs/PRD.md` § 10 before citing any number here.** Timing metrics are a sandbox-timing proxy, not hardware/real-mission timing. "Manual evidence-processing effort" is an evidence-record-count proxy, not measured human time. All results are against the stand-in stub artifact (`fprime-app/stub-component-app`), not the real F Prime (F´) framework. See STATUS.md "Claims status" for the full caveat list.

**All rates below are 95% Wilson score intervals; all timing means are 95% normal-approximation intervals** (see this file's module docstring for why two different methods are used). n = number of trials, shown per row.

## Happy path per condition

| Condition | n | Success rate (95% CI) | Reproducible rate (95% CI) | Mean time s (95% CI) | Traceability | Overhead vs S0 (bytes) | Mean attestation age (s) |
|---|---|---|---|---|---|---|---|
| S0 | 30 | 100% (89%-100%) | 100% (89%-100%) | 0.2880 (0.2702-0.3058) | 100% | 0 | n/a |
| S1 | 30 | 100% (89%-100%) | 100% (89%-100%) | 0.2983 (0.2842-0.3124) | 100% | 613 | n/a |
| S2 | 30 | 100% (89%-100%) | 100% (89%-100%) | 0.2908 (0.2849-0.2967) | 100% | 1264 | n/a |
| S3 | 30 | 100% (89%-100%) | 100% (89%-100%) | 0.3533 (0.3284-0.3781) | 100% | 1631 | 0.0014 |
| S4 | 30 | 100% (89%-100%) | 100% (89%-100%) | 0.3635 (0.3387-0.3883) | 100% | 1623 | 0.0013 |
| S5 | 30 | 100% (89%-100%) | 100% (89%-100%) | 0.5182 (0.4766-0.5598) | 100% | 5747 | 0.0015 |

## Attack matrix detection results (all 15 test cases)

| Test case | Condition | n | Detection rate (95% CI) | Metric | Mean time s (95% CI) |
|---|---|---|---|---|---|
| #1 | S2 | 30 | 100% (89%-100%) | time_to_identify | 0.3253 (0.3125-0.3381) |
| #2 | S2 | 30 | 100% (89%-100%) | time_to_identify | 0.2495 (0.2332-0.2659) |
| #3 | S1 | 30 | 100% (89%-100%) | time_to_identify | 0.3011 (0.2904-0.3117) |
| #4 | S1 | 30 | 100% (89%-100%) | time_to_identify | 0.3285 (0.3003-0.3568) |
| #5 | S2 | 30 | 100% (89%-100%) | time_to_identify | 0.3015 (0.2969-0.3061) |
| #6 | S0 | 30 | 100% (89%-100%) | time_to_identify | 0.3204 (0.2821-0.3587) |
| #7 | S0 | 30 | 100% (89%-100%) | time_to_identify | 0.3008 (0.2912-0.3103) |
| #8 | S5 | 30 | 100% (89%-100%) | time_to_identify | 0.3233 (0.3083-0.3383) |
| #9 | S2 | 30 | 100% (89%-100%) | time_to_identify | 0.3557 (0.3134-0.3981) |
| #10 | S4 | 30 | 100% (89%-100%) | time_to_trusted_restoration | 0.3588 (0.3311-0.3865) |
| #11 | S4 | 30 | 100% (89%-100%) | time_to_trusted_restoration | 0.3555 (0.3266-0.3844) |
| #12 | S4 | 30 | 100% (89%-100%) | time_to_trusted_restoration | 0.3816 (0.3706-0.3927) |
| #13 | S5 | 30 | 100% (89%-100%) | time_to_identify | 0.0002 (0.0002-0.0002) |
| #14 | S4 | 30 | 100% (89%-100%) | time_to_trusted_restoration | 0.3848 (0.3660-0.4036) |
| #15 | S5 | 30 | 100% (89%-100%) | time_to_identify | 0.5326 (0.5087-0.5564) |

## Update acceptance accuracy (confusion matrix, per condition)

| Condition | TP | FN | TN | FP | Attack cases covered |
|---|---|---|---|---|---|
| S0 | 30 | 0 | 60 | 0 | #6, #7 |
| S1 | 30 | 0 | 60 | 0 | #3, #4 |
| S2 | 30 | 0 | 120 | 0 | #1, #2, #5, #9 |
| S3 | 30 | 0 | 0 | 0 | (none) |
| S4 | 30 | 0 | 120 | 0 | #10, #11, #12, #14 |
| S5 | 30 | 0 | 90 | 0 | #8, #13, #15 |

