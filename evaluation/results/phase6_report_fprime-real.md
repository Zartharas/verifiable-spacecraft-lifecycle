# Phase 6 (stack: fprime-real) Evaluation Report (auto-generated)

**Read `docs/PRD.md` § 10 before citing any number here.** Timing metrics are a sandbox-timing proxy, not hardware/real-mission timing. "Manual evidence-processing effort" is an evidence-record-count proxy, not measured human time. All results are against the stand-in stub artifact for stack 'fprime-real'. See STATUS.md "Claims status" for the full caveat list.

## Happy path per condition

| Condition | Success rate | Reproducible rate | Mean time (s) | Traceability | Overhead vs S0 (bytes) | Mean attestation age (s) |
|---|---|---|---|---|---|---|
| S0 | 100% | 100% | 0.2828 | 100% | 0 | n/a |
| S1 | 100% | 100% | 0.2684 | 100% | 583 | n/a |
| S2 | 100% | 100% | 0.3084 | 100% | 1219 | n/a |
| S3 | 100% | 100% | 1.8457 | 100% | 1570 | 0.0078 |
| S4 | 100% | 100% | 1.8436 | 100% | 1578 | 0.0071 |
| S5 | 100% | 100% | 2.0766 | 100% | 5702 | 0.0074 |

## Attack matrix detection results (all 15 test cases)

| Test case | Condition | Detection rate | Metric | Mean time (s) | Stdev (s) |
|---|---|---|---|---|---|
| #1 | S2 | 100% | time_to_identify | 0.3049 | 0.0278 |
| #2 | S2 | 100% | time_to_identify | 0.1239 | 0.0253 |
| #3 | S1 | 100% | time_to_identify | 0.3517 | 0.1119 |
| #4 | S1 | 100% | time_to_identify | 0.2559 | 0.0407 |
| #5 | S2 | 100% | time_to_identify | 0.2732 | 0.0225 |
| #6 | S0 | 100% | time_to_identify | 0.3001 | 0.0435 |
| #7 | S0 | 100% | time_to_identify | 0.2565 | 0.0209 |
| #8 | S5 | 100% | time_to_identify | 0.2972 | 0.0263 |
| #9 | S2 | 100% | time_to_identify | 0.2847 | 0.0070 |
| #10 | S4 | 100% | time_to_trusted_restoration | 0.3336 | 0.0134 |
| #11 | S4 | 100% | time_to_trusted_restoration | 0.3522 | 0.0196 |
| #12 | S4 | 100% | time_to_trusted_restoration | 1.8901 | 0.0161 |
| #13 | S5 | 100% | time_to_identify | 0.0003 | 0.0000 |
| #14 | S4 | 100% | time_to_trusted_restoration | 0.3779 | 0.0200 |
| #15 | S5 | 100% | time_to_identify | 0.5383 | 0.0173 |

## Update acceptance accuracy (confusion matrix, per condition)

| Condition | TP | FN | TN | FP | Attack cases covered |
|---|---|---|---|---|---|
| S0 | 5 | 0 | 10 | 0 | #6, #7 |
| S1 | 5 | 0 | 10 | 0 | #3, #4 |
| S2 | 5 | 0 | 20 | 0 | #1, #2, #5, #9 |
| S3 | 5 | 0 | 0 | 0 | (none) |
| S4 | 5 | 0 | 20 | 0 | #10, #11, #12, #14 |
| S5 | 5 | 0 | 15 | 0 | #8, #13, #15 |

