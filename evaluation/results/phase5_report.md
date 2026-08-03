# Phase 5 Evaluation Report (auto-generated)

**Read `docs/PRD.md` § 10 before citing any number here.** Timing metrics are a sandbox-timing proxy, not hardware/real-mission timing. "Manual evidence-processing effort" is an evidence-record-count proxy, not measured human time. All results are against the stand-in stub artifact (`cfs-app/stub-telemetry-app`), not the real cFS build. See STATUS.md "Claims status" for the full caveat list.

## Happy path per condition

| Condition | Success rate | Reproducible rate | Mean time (s) | Traceability | Overhead vs S0 (bytes) | Mean attestation age (s) |
|---|---|---|---|---|---|---|
| S0 | 100% | 100% | 0.2529 | 100% | 0 | n/a |
| S1 | 100% | 100% | 0.2680 | 100% | 613 | n/a |
| S2 | 100% | 100% | 0.3042 | 100% | 1264 | n/a |
| S3 | 100% | 100% | 0.3063 | 100% | 1631 | 0.0074 |
| S4 | 100% | 100% | 0.3184 | 100% | 1624 | 0.0077 |
| S5 | 100% | 100% | 0.4112 | 100% | 5748 | 0.0079 |

## Attack matrix detection results (all 15 test cases)

| Test case | Condition | Detection rate | Metric | Mean time (s) | Stdev (s) |
|---|---|---|---|---|---|
| #1 | S2 | 100% | time_to_identify | 0.2558 | 0.0068 |
| #2 | S2 | 100% | time_to_identify | 0.1908 | 0.0077 |
| #3 | S1 | 100% | time_to_identify | 0.2429 | 0.0035 |
| #4 | S1 | 100% | time_to_identify | 0.2429 | 0.0076 |
| #5 | S2 | 100% | time_to_identify | 0.2615 | 0.0093 |
| #6 | S0 | 100% | time_to_identify | 0.2471 | 0.0127 |
| #7 | S0 | 100% | time_to_identify | 0.2523 | 0.0095 |
| #8 | S5 | 100% | time_to_identify | 0.2778 | 0.0090 |
| #9 | S2 | 100% | time_to_identify | 0.2761 | 0.0324 |
| #10 | S4 | 100% | time_to_trusted_restoration | 0.2807 | 0.0059 |
| #11 | S4 | 100% | time_to_trusted_restoration | 0.3480 | 0.0652 |
| #12 | S4 | 100% | time_to_trusted_restoration | 0.4507 | 0.0132 |
| #13 | S5 | 100% | time_to_identify | 0.0022 | 0.0007 |
| #14 | S4 | 100% | time_to_trusted_restoration | 0.4493 | 0.0481 |
| #15 | S5 | 100% | time_to_identify | 0.4953 | 0.1220 |

## Update acceptance accuracy (confusion matrix, per condition)

| Condition | TP | FN | TN | FP | Attack cases covered |
|---|---|---|---|---|---|
| S0 | 5 | 0 | 10 | 0 | #6, #7 |
| S1 | 5 | 0 | 10 | 0 | #3, #4 |
| S2 | 5 | 0 | 20 | 0 | #1, #2, #5, #9 |
| S3 | 5 | 0 | 0 | 0 | (none) |
| S4 | 5 | 0 | 20 | 0 | #10, #11, #12, #14 |
| S5 | 5 | 0 | 15 | 0 | #8, #13, #15 |

