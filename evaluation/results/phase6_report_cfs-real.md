# Phase 6 (stack: cfs-real) Evaluation Report (auto-generated)

**Read `docs/PRD.md` § 10 before citing any number here.** Timing metrics are a sandbox-timing proxy, not hardware/real-mission timing. "Manual evidence-processing effort" is an evidence-record-count proxy, not measured human time. All results are against the stand-in stub artifact for stack 'cfs-real'. See STATUS.md "Claims status" for the full caveat list.

**All rates below are 95% Wilson score intervals; all timing means are 95% normal-approximation intervals** (see this file's module docstring for why two different methods are used). n = number of trials, shown per row.

## Happy path per condition

| Condition | n | Success rate (95% CI) | Reproducible rate (95% CI) | Mean time s (95% CI) | Traceability | Overhead vs S0 (bytes) | Mean attestation age (s) |
|---|---|---|---|---|---|---|---|
| S0 | 30 | 100% (89%-100%) | 100% (89%-100%) | 0.2872 (0.2738-0.3006) | 100% | 0 | n/a |
| S1 | 30 | 100% (89%-100%) | 100% (89%-100%) | 0.2671 (0.2585-0.2757) | 100% | 595 | n/a |
| S2 | 30 | 100% (89%-100%) | 100% (89%-100%) | 0.3049 (0.2962-0.3136) | 100% | 1237 | n/a |
| S3 | 30 | 100% (89%-100%) | 100% (89%-100%) | 2.5118 (2.4813-2.5423) | 100% | 1593 | 0.0055 |
| S4 | 30 | 100% (89%-100%) | 100% (89%-100%) | 2.4831 (2.4322-2.5340) | 100% | 1596 | 0.0050 |
| S5 | 30 | 100% (89%-100%) | 100% (89%-100%) | 2.7743 (2.7250-2.8236) | 100% | 5720 | 0.0049 |

## Attack matrix detection results (all 15 test cases)

| Test case | Condition | n | Detection rate (95% CI) | Metric | Mean time s (95% CI) |
|---|---|---|---|---|---|
| #1 | S2 | 30 | 100% (89%-100%) | time_to_identify | 0.3353 (0.3214-0.3492) |
| #2 | S2 | 30 | 100% (89%-100%) | time_to_identify | 0.0644 (0.0626-0.0662) |
| #3 | S1 | 30 | 100% (89%-100%) | time_to_identify | 0.2779 (0.2616-0.2942) |
| #4 | S1 | 30 | 100% (89%-100%) | time_to_identify | 0.2523 (0.2446-0.2601) |
| #5 | S2 | 30 | 100% (89%-100%) | time_to_identify | 0.3186 (0.3009-0.3363) |
| #6 | S0 | 30 | 100% (89%-100%) | time_to_identify | 0.3097 (0.2888-0.3306) |
| #7 | S0 | 30 | 100% (89%-100%) | time_to_identify | 0.2754 (0.2600-0.2908) |
| #8 | S5 | 30 | 100% (89%-100%) | time_to_identify | 0.3289 (0.3098-0.3480) |
| #9 | S2 | 30 | 100% (89%-100%) | time_to_identify | 0.3307 (0.3112-0.3502) |
| #10 | S4 | 30 | 100% (89%-100%) | time_to_trusted_restoration | 0.3524 (0.3405-0.3644) |
| #11 | S4 | 30 | 100% (89%-100%) | time_to_trusted_restoration | 0.4261 (0.4008-0.4514) |
| #12 | S4 | 30 | 100% (89%-100%) | time_to_trusted_restoration | 2.5810 (2.5313-2.6308) |
| #13 | S5 | 30 | 100% (89%-100%) | time_to_identify | 0.0003 (0.0003-0.0004) |
| #14 | S4 | 30 | 100% (89%-100%) | time_to_trusted_restoration | 0.4672 (0.4268-0.5076) |
| #15 | S5 | 30 | 100% (89%-100%) | time_to_identify | 0.7201 (0.6989-0.7413) |

## Update acceptance accuracy (confusion matrix, per condition)

| Condition | TP | FN | TN | FP | Attack cases covered |
|---|---|---|---|---|---|
| S0 | 30 | 0 | 60 | 0 | #6, #7 |
| S1 | 30 | 0 | 60 | 0 | #3, #4 |
| S2 | 30 | 0 | 120 | 0 | #1, #2, #5, #9 |
| S3 | 30 | 0 | 0 | 0 | (none) |
| S4 | 30 | 0 | 120 | 0 | #10, #11, #12, #14 |
| S5 | 30 | 0 | 90 | 0 | #8, #13, #15 |

