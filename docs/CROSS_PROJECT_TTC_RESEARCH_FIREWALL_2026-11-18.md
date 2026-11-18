# Related-work firewall: independent TT&C resynchronization manuscript

**Recorded:** 2026-11-18. **Scope:** documentation-only research non-overlap and cross-chat handoff, not a modification to verifiable spacecraft software lifecycle science, journal revision, or prototype runtime.

## Authority

The `main` snapshot of this repository is `f0a26d2edd974827741a53c566b6c79ca2ebdd0b`. Follow `STATUS.md`, `docs/Paper-Draft.md`, frozen evaluation records and `docs/Revision-1-Response.md` (private/local) for this program. The latest recorded status identifies JSSE-D-26-00171 Revision 1 prepared for resubmission with a November 22, 2026 deadline; **the official journal portal state and final author submission decision are not verified by this cross-project note**.

A *separate*, author-owned repository, [satcom-ttc-post-compromise-recovery](https://github.com/Zartharas/satcom-ttc-post-compromise-recovery), is preparing an IEEE TAES original paper on post-compromise TT&C resynchronization. Its `main` snapshot is `1bda511862f104e82bddcbf95db1ee97702e6c02`. See its [tracking issue #29](https://github.com/Zartharas/satcom-ttc-post-compromise-recovery/issues/29) and [Branch 2 handoff](https://github.com/Zartharas/satcom-ttc-post-compromise-recovery/blob/handoff/taes-branch2-20261118/paper/submission/TAES_BRANCH2_NEXT_CHAT_HANDOFF_2026-11-18.md).

## Non-overlap table

| Lifecycle program (this repo) | Independent TT&C program | Restriction |
|---|---|---|
| S0-S5 software artifact integrity ladder, signed release, SBOM, provenance, attestation, onboard policy, tamper detection, trusted rollback, and authorization evidence | TT&C model of key epoch resynchronization, ground/space candidate/activation state, replay/stale-state rejection, bounded retransmissions, availability and post-convergence command/telemetry evidence | Do not present software-release integrity, attestation or rollback results as TT&C key recovery, CCSDS SDLS conformance or independent cryptographic validation. |
| Existing tests, four-target evaluation and journal revision response remain separate frozen evidence/populations | TT&C Studies A-D are separately frozen, with 4 matched families, 40 deterministic schedules, 100 mixed schedules and 108 sensitivity executions | No copying, pooling, re-labeling or reusing any observations as fresh TT&C data. |
| Real cFS/F Prime builds in this program, with stated evaluation limitations | Prospective `TTCSIL-SA-RST-001` NOS3/cFS/CryptoLib integration subject to F1-F4 security and genuine process-restart gates | Existing real-binary pipeline checks are not a verified TT&C SA restart, authenticated TC/TM return or independent TT&C oracle. |

The two bodies of work may share public NASA software **as independently sourced and pinned upstream dependencies** under applicable licenses, but cannot recycle same-author tests, diagrams or results as independent observations. If an adjacent claim becomes necessary, cite it accurately only after source and publication-status review.

## Preserve publication and technical gates

- Do not alter this repo's `docs/Paper-Draft.md`, `STATUS.md` publication history, active/revision submission files, source results, tests, archive DOIs or source-code licensing as part of the TT&C handoff.
- The TT&C IEEE TAES sample/template check and S0/S1 reviewer PDFs are *publication formatting work only*, not experimental spacecraft results.
- No new runtime, live RF, operational keys, exposed command channel or raw bundle release. TT&C F1-F4 stays **HOLD** for SA/GVCID authorization, cFE length checks, isolated graph, real restart, cryptographically verified end-to-end command/status and independent evidence oracle.
- Journal declarations and any private correspondence must be confirmed and handled independently for each manuscript; do not transplant author/AI-use/COI/funding statements between programs.

**Next action:** When assessing the TT&C extension's originality, independently compare exact question, intervention, unit, endpoint, artifacts and publication status against this repo's current `STATUS.md` and frozen work. Open substantive conflicts as a separate reviewed issue; do not silently update either manuscript.
