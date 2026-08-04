# Phase 6 (stack: fprime-real) Evaluation Report (auto-generated)

**Read `docs/PRD.md` § 10 before citing any number here.** Timing metrics are a sandbox-timing proxy, not hardware/real-mission timing. "Manual evidence-processing effort" is an evidence-record-count proxy, not measured human time. All results are against the stand-in stub artifact for stack 'fprime-real'. See STATUS.md "Claims status" for the full caveat list.

**All rates below are 95% Wilson score intervals; all timing means are 95% normal-approximation intervals** (see this file's module docstring for why two different methods are used). n = number of trials, shown per row.

## Happy path per condition

| Condition | n | Success rate (95% CI) | Reproducible rate (95% CI) | Mean time s (95% CI) | Traceability | Overhead vs S0 (bytes) | Mean attestation age (s) |
|---|---|---|---|---|---|---|---|
| S0 | 5 | 100% (57%-100%) | 100% (57%-100%) | 0.2828 (0.2737-0.2919) | 100% | 0 | n/a |
| S1 | 5 | 100% (57%-100%) | 100% (57%-100%) | 0.2684 (0.2521-0.2846) | 100% | 583 | n/a |
| S2 | 5 | 100% (57%-100%) | 100% (57%-100%) | 0.3084 (0.2985-0.3183) | 100% | 1219 | n/a |
| S3 | 5 | 100% (57%-100%) | 100% (57%-100%) | 1.8457 (1.8166-1.8749) | 100% | 1570 | 0.0078 |
| S4 | 5 | 100% (57%-100%) | 100% (57%-100%) | 1.8436 (1.8197-1.8675) | 100% | 1578 | 0.0071 |
| S5 | 5 | 100% (57%-100%) | 100% (57%-100%) | 2.0766 (2.0395-2.1137) | 100% | 5702 | 0.0074 |

## Attack matrix detection results (all 15 test cases)

| Test case | Condition | n | Detection rate (95% CI) | Metric | Mean time s (95% CI) |
|---|---|---|---|---|---|
| #1 | S2 | 5 | 100% (57%-100%) | time_to_identify | 0.3049 (0.2805-0.3293) |
| #2 | S2 | 5 | 100% (57%-100%) | time_to_identify | 0.1239 (0.1017-0.1461) |
| #3 | S1 | 5 | 100% (57%-100%) | time_to_identify | 0.3517 (0.2536-0.4497) |
| #4 | S1 | 5 | 100% (57%-100%) | time_to_identify | 0.2559 (0.2202-0.2916) |
| #5 | S2 | 5 | 100% (57%-100%) | time_to_identify | 0.2732 (0.2534-0.2929) |
| #6 | S0 | 5 | 100% (57%-100%) | time_to_identify | 0.3001 (0.2619-0.3382) |
| #7 | S0 | 5 | 100% (57%-100%) | time_to_identify | 0.2565 (0.2382-0.2748) |
| #8 | S5 | 5 | 100% (57%-100%) | time_to_identify | 0.2972 (0.2741-0.3202) |
| #9 | S2 | 5 | 100% (57%-100%) | time_to_identify | 0.2847 (0.2786-0.2908) |
| #10 | S4 | 5 | 100% (57%-100%) | time_to_trusted_restoration | 0.3336 (0.3218-0.3453) |
| #11 | S4 | 5 | 100% (57%-100%) | time_to_trusted_restoration | 0.3522 (0.3351-0.3694) |
| #12 | S4 | 5 | 100% (57%-100%) | time_to_trusted_restoration | 1.8901 (1.8760-1.9042) |
| #13 | S5 | 5 | 100% (57%-100%) | time_to_identify | 0.0003 (0.0002-0.0003) |
| #14 | S4 | 5 | 100% (57%-100%) | time_to_trusted_restoration | 0.3779 (0.3604-0.3954) |
| #15 | S5 | 5 | 100% (57%-100%) | time_to_identify | 0.5383 (0.5231-0.5534) |

## Update acceptance accuracy (confusion matrix, per condition)

| Condition | TP | FN | TN | FP | Attack cases covered |
|---|---|---|---|---|---|
| S0 | 5 | 0 | 10 | 0 | #6, #7 |
| S1 | 5 | 0 | 10 | 0 | #3, #4 |
| S2 | 5 | 0 | 20 | 0 | #1, #2, #5, #9 |
| S3 | 5 | 0 | 0 | 0 | (none) |
| S4 | 5 | 0 | 20 | 0 | #10, #11, #12, #14 |
| S5 | 5 | 0 | 15 | 0 | #8, #13, #15 |

