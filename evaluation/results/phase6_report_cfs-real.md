# Phase 6 (stack: cfs-real) Evaluation Report (auto-generated)

**Read `docs/PRD.md` § 10 before citing any number here.** Timing metrics are a sandbox-timing proxy, not hardware/real-mission timing. "Manual evidence-processing effort" is an evidence-record-count proxy, not measured human time. All results are against the stand-in stub artifact for stack 'cfs-real'. See STATUS.md "Claims status" for the full caveat list.

**All rates below are 95% Wilson score intervals; all timing means are 95% normal-approximation intervals** (see this file's module docstring for why two different methods are used). n = number of trials, shown per row.

## Happy path per condition

| Condition | n | Success rate (95% CI) | Reproducible rate (95% CI) | Mean time s (95% CI) | Traceability | Overhead vs S0 (bytes) | Mean attestation age (s) |
|---|---|---|---|---|---|---|---|
| S0 | 5 | 100% (57%-100%) | 100% (57%-100%) | 0.2399 (0.2245-0.2553) | 100% | 0 | n/a |
| S1 | 5 | 100% (57%-100%) | 100% (57%-100%) | 0.2478 (0.2451-0.2505) | 100% | 595 | n/a |
| S2 | 5 | 100% (57%-100%) | 100% (57%-100%) | 0.2791 (0.2563-0.3019) | 100% | 1237 | n/a |
| S3 | 5 | 100% (57%-100%) | 100% (57%-100%) | 2.3784 (2.3661-2.3907) | 100% | 1594 | 0.0051 |
| S4 | 5 | 100% (57%-100%) | 100% (57%-100%) | 2.3782 (2.3570-2.3993) | 100% | 1597 | 0.0050 |
| S5 | 5 | 100% (57%-100%) | 100% (57%-100%) | 2.6059 (2.5658-2.6461) | 100% | 5721 | 0.0043 |

## Attack matrix detection results (all 15 test cases)

| Test case | Condition | n | Detection rate (95% CI) | Metric | Mean time s (95% CI) |
|---|---|---|---|---|---|
| #1 | S2 | 5 | 100% (57%-100%) | time_to_identify | 0.2362 (0.2190-0.2535) |
| #2 | S2 | 5 | 100% (57%-100%) | time_to_identify | 0.0558 (0.0541-0.0575) |
| #3 | S1 | 5 | 100% (57%-100%) | time_to_identify | 0.2038 (0.2021-0.2056) |
| #4 | S1 | 5 | 100% (57%-100%) | time_to_identify | 0.2089 (0.1931-0.2247) |
| #5 | S2 | 5 | 100% (57%-100%) | time_to_identify | 0.2170 (0.2091-0.2250) |
| #6 | S0 | 5 | 100% (57%-100%) | time_to_identify | 0.2109 (0.2045-0.2172) |
| #7 | S0 | 5 | 100% (57%-100%) | time_to_identify | 0.2048 (0.1894-0.2202) |
| #8 | S5 | 5 | 100% (57%-100%) | time_to_identify | 0.2150 (0.2085-0.2216) |
| #9 | S2 | 5 | 100% (57%-100%) | time_to_identify | 0.2221 (0.2112-0.2330) |
| #10 | S4 | 5 | 100% (57%-100%) | time_to_trusted_restoration | 0.2632 (0.2567-0.2698) |
| #11 | S4 | 5 | 100% (57%-100%) | time_to_trusted_restoration | 0.2916 (0.2773-0.3060) |
| #12 | S4 | 5 | 100% (57%-100%) | time_to_trusted_restoration | 2.3682 (2.3430-2.3933) |
| #13 | S5 | 5 | 100% (57%-100%) | time_to_identify | 0.0002 (0.0002-0.0002) |
| #14 | S4 | 5 | 100% (57%-100%) | time_to_trusted_restoration | 0.2927 (0.2641-0.3212) |
| #15 | S5 | 5 | 100% (57%-100%) | time_to_identify | 0.5051 (0.4609-0.5494) |

## Update acceptance accuracy (confusion matrix, per condition)

| Condition | TP | FN | TN | FP | Attack cases covered |
|---|---|---|---|---|---|
| S0 | 5 | 0 | 10 | 0 | #6, #7 |
| S1 | 5 | 0 | 10 | 0 | #3, #4 |
| S2 | 5 | 0 | 20 | 0 | #1, #2, #5, #9 |
| S3 | 5 | 0 | 0 | 0 | (none) |
| S4 | 5 | 0 | 20 | 0 | #10, #11, #12, #14 |
| S5 | 5 | 0 | 15 | 0 | #8, #13, #15 |

