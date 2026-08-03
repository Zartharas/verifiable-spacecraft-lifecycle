# Phase 6 (stack: cfs-real) Evaluation Report (auto-generated)

**Read `docs/PRD.md` § 10 before citing any number here.** Timing metrics are a sandbox-timing proxy, not hardware/real-mission timing. "Manual evidence-processing effort" is an evidence-record-count proxy, not measured human time. All results are against the stand-in stub artifact for stack 'cfs-real'. See STATUS.md "Claims status" for the full caveat list.

## Happy path per condition

| Condition | Success rate | Reproducible rate | Mean time (s) | Traceability | Overhead vs S0 (bytes) | Mean attestation age (s) |
|---|---|---|---|---|---|---|
| S0 | 100% | 100% | 0.2399 | 100% | 0 | n/a |
| S1 | 100% | 100% | 0.2478 | 100% | 595 | n/a |
| S2 | 100% | 100% | 0.2791 | 100% | 1237 | n/a |
| S3 | 100% | 100% | 2.3784 | 100% | 1594 | 0.0051 |
| S4 | 100% | 100% | 2.3782 | 100% | 1597 | 0.0050 |
| S5 | 100% | 100% | 2.6059 | 100% | 5721 | 0.0043 |

## Attack matrix detection results (all 15 test cases)

| Test case | Condition | Detection rate | Metric | Mean time (s) | Stdev (s) |
|---|---|---|---|---|---|
| #1 | S2 | 100% | time_to_identify | 0.2362 | 0.0197 |
| #2 | S2 | 100% | time_to_identify | 0.0558 | 0.0020 |
| #3 | S1 | 100% | time_to_identify | 0.2038 | 0.0020 |
| #4 | S1 | 100% | time_to_identify | 0.2089 | 0.0180 |
| #5 | S2 | 100% | time_to_identify | 0.2170 | 0.0091 |
| #6 | S0 | 100% | time_to_identify | 0.2109 | 0.0073 |
| #7 | S0 | 100% | time_to_identify | 0.2048 | 0.0175 |
| #8 | S5 | 100% | time_to_identify | 0.2150 | 0.0075 |
| #9 | S2 | 100% | time_to_identify | 0.2221 | 0.0125 |
| #10 | S4 | 100% | time_to_trusted_restoration | 0.2632 | 0.0074 |
| #11 | S4 | 100% | time_to_trusted_restoration | 0.2916 | 0.0164 |
| #12 | S4 | 100% | time_to_trusted_restoration | 2.3682 | 0.0287 |
| #13 | S5 | 100% | time_to_identify | 0.0002 | 0.0000 |
| #14 | S4 | 100% | time_to_trusted_restoration | 0.2927 | 0.0326 |
| #15 | S5 | 100% | time_to_identify | 0.5051 | 0.0505 |

## Update acceptance accuracy (confusion matrix, per condition)

| Condition | TP | FN | TN | FP | Attack cases covered |
|---|---|---|---|---|---|
| S0 | 5 | 0 | 10 | 0 | #6, #7 |
| S1 | 5 | 0 | 10 | 0 | #3, #4 |
| S2 | 5 | 0 | 20 | 0 | #1, #2, #5, #9 |
| S3 | 5 | 0 | 0 | 0 | (none) |
| S4 | 5 | 0 | 20 | 0 | #10, #11, #12, #14 |
| S5 | 5 | 0 | 15 | 0 | #8, #13, #15 |

