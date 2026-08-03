# Phase 6 (stack: fprime) Evaluation Report (auto-generated)

**Read `docs/PRD.md` § 10 before citing any number here.** Timing metrics are a sandbox-timing proxy, not hardware/real-mission timing. "Manual evidence-processing effort" is an evidence-record-count proxy, not measured human time. All results are against the stand-in stub artifact (`fprime-app/stub-component-app`), not the real F Prime (F´) framework. See STATUS.md "Claims status" for the full caveat list.

## Happy path per condition

| Condition | Success rate | Reproducible rate | Mean time (s) | Traceability | Overhead vs S0 (bytes) | Mean attestation age (s) |
|---|---|---|---|---|---|---|
| S0 | 100% | 100% | 0.2842 | 100% | 0 | n/a |
| S1 | 100% | 100% | 0.3147 | 100% | 613 | n/a |
| S2 | 100% | 100% | 0.3490 | 100% | 1264 | n/a |
| S3 | 100% | 100% | 0.3364 | 100% | 1631 | 0.0066 |
| S4 | 100% | 100% | 0.4091 | 100% | 1623 | 0.0078 |
| S5 | 100% | 100% | 0.4602 | 100% | 5748 | 0.0066 |

## Attack matrix detection results (all 15 test cases)

| Test case | Condition | Detection rate | Metric | Mean time (s) | Stdev (s) |
|---|---|---|---|---|---|
| #1 | S2 | 100% | time_to_identify | 0.3591 | 0.0755 |
| #2 | S2 | 100% | time_to_identify | 0.2648 | 0.0428 |
| #3 | S1 | 100% | time_to_identify | 0.2989 | 0.0186 |
| #4 | S1 | 100% | time_to_identify | 0.2731 | 0.0273 |
| #5 | S2 | 100% | time_to_identify | 0.2925 | 0.0377 |
| #6 | S0 | 100% | time_to_identify | 0.2993 | 0.0644 |
| #7 | S0 | 100% | time_to_identify | 0.3315 | 0.0085 |
| #8 | S5 | 100% | time_to_identify | 0.3363 | 0.0088 |
| #9 | S2 | 100% | time_to_identify | 0.3497 | 0.0376 |
| #10 | S4 | 100% | time_to_trusted_restoration | 0.4336 | 0.0620 |
| #11 | S4 | 100% | time_to_trusted_restoration | 0.3893 | 0.0336 |
| #12 | S4 | 100% | time_to_trusted_restoration | 0.3849 | 0.0842 |
| #13 | S5 | 100% | time_to_identify | 0.0019 | 0.0005 |
| #14 | S4 | 100% | time_to_trusted_restoration | 0.3761 | 0.0185 |
| #15 | S5 | 100% | time_to_identify | 0.4452 | 0.0397 |

## Update acceptance accuracy (confusion matrix, per condition)

| Condition | TP | FN | TN | FP | Attack cases covered |
|---|---|---|---|---|---|
| S0 | 5 | 0 | 10 | 0 | #6, #7 |
| S1 | 5 | 0 | 10 | 0 | #3, #4 |
| S2 | 5 | 0 | 20 | 0 | #1, #2, #5, #9 |
| S3 | 5 | 0 | 0 | 0 | (none) |
| S4 | 5 | 0 | 20 | 0 | #10, #11, #12, #14 |
| S5 | 5 | 0 | 15 | 0 | #8, #13, #15 |

