# Measuring Software Supply-Chain Assurance for Spacecraft Flight Software: A Controlled, Comparative Evaluation

**Status:** Revision 1 (major revision requested by JSSE, manuscript JSSE-D-26-00171, due 2026-11-22).
The text below the `MANUSCRIPT-START` marker is the submittable manuscript. The version
originally submitted on 2026-08-18 is preserved in `docs/Paper-Draft-v1-submitted.md`.
Revision notes and the point-by-point response are in `docs/Revision-1-Response.md`.

---

<!-- MANUSCRIPT-START -->

# Measuring Software Supply-Chain Assurance for Spacecraft Flight Software: A Controlled, Comparative Evaluation

**Aman Singh**

Independent Researcher

The Woodlands, Texas, USA

ORCID: 0009-0008-9752-3743

Corresponding author. E-mail: aman.singh2406@live.com

## Abstract

Flight software updates for spacecraft are commonly accepted on the basis of a digital signature alone. A signature does not establish that the software was built from the intended source, that its configuration was authorized, or that the installed software matches the approved release. This study evaluates a six-level additive assurance ladder (S0 to S5) in which S0 verifies a signature and each subsequent level adds one mechanism: a software bill of materials (SBOM), build provenance, onboard attestation, trusted A/B rollback, and machine-readable authorization evidence. Fifteen attack and failure cases, a per-mechanism ablation, and two multi-vector scenarios were executed in 30 trials on each of four targets, including the unmodified NASA cFS and JPL F Prime frameworks. Each mechanism detected its assigned failure class, and its removal eliminated that detection. Because the injected attacks and the detectors were specified by the same author, these results verify implementation correctness and do not estimate detection of unanticipated attacks. A supplementary mutation experiment, which applied systematic perturbations to the verifier inputs, identified two implementation defects that were subsequently corrected. The complete ladder increased mean pipeline time by 44% to 80% on the two stand-in applications and added 5.7 kB of storage. A hash-comparison baseline addressed 1 of the 15 cases and TUF addressed 3; a reading of the Uptane specification indicated 3 native mechanisms and 4 partial analogues. All results derive from simulation, without flight hardware or hardware-rooted attestation.

**Keywords:** Software supply chain security; Satellite and spacecraft cybersecurity; Cryptographic attestation; Trusted software rollback; Cyber-physical systems assurance

## 1. Introduction

A spacecraft that accepts a flight software update on the strength of a signature trusts the holder of the signing key and nothing else. The signature does not show that the binary was built from the intended source, that the configuration it carries was authorized by an operator, that the update is newer than the one it replaces, or that the spacecraft is running the update that was approved once installation is complete. These properties matter more in orbit than on the ground. Links are intermittent and high-latency, an operator is often not present when an anomaly occurs, and a faulty update to a single asset that cannot be reached cannot be corrected by shipping a new commit.

Operational space systems have already suffered attacks on their update and management paths. On 24 February 2022, the AcidRain wiper was delivered through the KA-SAT management segment to Viasat modems and overwrote their flash memory; a documented downstream effect was the loss of remote monitoring for roughly 5,800 Enercon wind turbines in Germany [1]; see also [2]. In March 2024 the AcidPour variant extended the same approach to embedded Linux and industrial-control devices [3]. Both are ground and terminal-segment incidents. No publicly documented compromise of an onboard flight-software build or update was identified in the sources reviewed, and this paper does not treat one as established. These incidents are cited to motivate update-path integrity; Section 3 specifies which parts of an AcidRain-class compromise the evaluated mechanisms address and which they do not.

It may be objected that a published hash already resolves the integrity problem. GitHub now publishes a SHA-256 digest for each release asset, computed at upload time [4]. If the bytes on the device match that digest, the device holds the bytes that were uploaded. This is the only property the comparison establishes. It does not show how the bytes were produced, because the digest is computed over whatever was uploaded, including output from a compromised build. It does not show who was authorized to publish, because whoever can upload an asset also produces its digest. It says nothing about the component inventory, the configuration, whether the release is older than the installed one, or the state of the spacecraft after installation. Section 6.8 tests this by executing a hash-comparison deployment against the same attack matrix. The deficiency is therefore not the absence of integrity checks: an integrity check binds bytes to a digest and nothing else on which a mission depends.

Terrestrial practice has addressed parts of this gap. SLSA and in-toto describe build provenance and attestations, Sigstore provides signing and transparency infrastructure, and TUF protects update metadata against key and repository compromise [5-8]. Uptane adapts TUF to vehicles [9]. None was designed around spacecraft constraints, and no study known to the author measures what each additional assurance mechanism provides for spacecraft flight software, or what it costs.

This paper has four objectives, stated as research questions.

- **RQ1 (attribution).** When each of five mechanisms is added to a signed pipeline, does it detect the failure class assigned to it, and is that detection attributable to the mechanism itself and not to one beneath it?
- **RQ2 (cost).** What does each added mechanism cost in pipeline time, storage, and evidence volume, and how does the cost compare across four target stacks, including two real NASA/JPL frameworks?
- **RQ3 (coverage).** Which of the 15 failure classes fall outside the scope of a hash comparison, TUF, and Uptane?
- **RQ4 (robustness).** When the verifiers are given systematically mutated artifacts and configurations, which changes do they reject, which do they accept, and do they fail cleanly on malformed input?

The paper makes four contributions.

1. A six-level additive assurance ladder (S0 to S5) and an open reference implementation in which all levels share one codebase and differ only by configuration, so that any difference between adjacent levels is attributable to one added mechanism.
2. A controlled evaluation of that ladder: a 15-case attack and failure matrix, a six-case ablation, and two multi-vector scenarios, with 30 trials each on four targets, reporting detection, time to detection and restoration, confusion matrices, overhead, evidence volume, traceability, and build reproducibility.
3. A coverage comparison against a hash-only deployment and TUF, both executed, and against Uptane, read from its specification, showing which failure classes each can and cannot address by design.
4. A mutation experiment that applies generic operators to the SBOM, provenance, attestation, binary, signature, and policy inputs. It reports which changes each verifier rejects and which it accepts, identified two implementation defects that the 15 manually specified cases had not exposed, and is repeated after their correction.

The evaluation has a defined scope. Each of the 15 failure cases is injected and detected by components implemented by the same author. A result of 100% therefore verifies that the implemented checks do what they are specified to do. It does not estimate how the mechanisms would perform against attacks that were not anticipated in the design. The mutation experiment reduces this dependence on manually specified cases for the document and configuration checks, but its operators were also chosen by the author, so the boundary remains. Section 5.1 states it and Section 7.1 discusses its consequences.

The remainder of the paper is organized as follows. Section 2 reviews related work. Section 3 gives the threat model and the ladder. Section 4 describes the implementation. Section 5 describes the methodology and Section 6 the results. Section 7 discusses them, Section 8 states limitations, and Section 9 concludes.

## 2. Related work

### 2.1 Terrestrial supply-chain security

Terrestrial practice has converged on three complementary properties. Provenance records how an artifact was built and from what (SLSA [5], in-toto [6]). Attestation and transparency allow a claim about an artifact to be verified independently (Sigstore [7]). Update resilience lets an update system survive the compromise of some of its own keys (TUF [8]). OSCAL [10] represents compliance and authorization evidence in a machine-readable form. These systems are cited through their current specifications, because the pipeline is compared with them and does not reimplement them. The ladder maps loosely onto them: SBOM (S1) and provenance (S2) to the first property, onboard attestation (S3) to the second, and machine-readable authorization evidence (S5) to the purpose of OSCAL. S0 checks a signature against a local revocation list. This is weaker than TUF's resilience property, which rests on signed metadata, threshold signatures, role separation, and signed key rotation.

Uptane [9] extends TUF for ground vehicles. It adds a Director repository that decides what each vehicle receives alongside the Image repository, requires an attacker to compromise both, and has each ECU report the hash of its installed image in a signed version report. The current standard (version 2.1.0 [21]) states that compromise of the supply chain, including the build system, and malicious software embedded in a trusted package are out of scope, and it names in-toto as a complement. No Uptane implementation was executed. Section 6.8 classifies each of the 15 cases from the text of the standard, and that classification is a reading of the specification, not a measurement.

### 2.2 Spacecraft and satellite software security

Published work on satellite security concentrates on the ground segment and the radio link. Manulis et al. [11] analyze historical incidents and find the ground segment and RF communications to be the most frequent targets. Their text names supply-chain attacks and outdated commercial software as threat categories but treats each in one paragraph, with no proposed verification or update-integrity mechanism. Ahmad et al. [12] and Kang et al. [2] survey satellite communication security at the protocol level. Neither develops onboard update assurance as a category; Ahmad et al. note only that on-orbit reprogramming technologies are immature.

Two arXiv preprints by Vanlyssel et al. are adjacent. SpyChain [13] describes supply-chain attacks on auxiliary commercial hardware in small satellites and contrasts them with flight software, which it describes as subject to strict security practices. "Trust Without Boundaries" [14] studies runtime trust boundaries among cFS components in the NOS3 simulator and shows that a compromised component can exploit broadly shared privileges. This concerns code that is already running and does not address whether the software that arrived was the software an operator authorized, which is the subject of this paper. Their finding that a compromised component can look legitimate at the architecture level is an independent argument for onboard attestation. Both are preprints and are cited as context.

### 2.3 Attestation and update assurance in adjacent domains

Usman et al. [15] combine remote attestation with secure updates for embedded systems (RASUES), extending the IETF RATS architecture [16] with a watchdog-supervised update procedure. It rests on a TPM 2.0 hardware root of trust and targets general embedded systems. This makes its attestation stronger than the software-only S3 evaluated here, while it does not cover build provenance, SBOM completeness, or ground-side authorization policy. Sahlmann et al. [17] describe a secure over-the-air update protocol for constrained IoT devices; when the post-update reboot fails, the server records a timeout and reports the error, with no recovery mechanism described. Qureshi et al. [18] propose a classifier that detects malicious update executables in vehicles, layered on Uptane; it is cited for malicious-update detection only.

### 2.4 Flight software engineering

Ganesan et al. [19] analyze unit testing in a flight-software product line that predates the open release of cFS, and Gonzalez et al. [20] evaluate architecture verification for CubeSat flight software built on a different framework. Neither addresses supply-chain assurance, and both show that verification tooling for flight software is an active concern.

## 3. Threat model and the assurance ladder

### 3.1 Actors and trust assumptions

The model considers six actors that span adversarial and non-adversarial causes of an untrustworthy update reaching a spacecraft.

1. An external attacker with access to the ground segment network or the uplink, who tampers with an update in transit, replays a prior one, or attempts a downgrade.
2. Compromised build infrastructure: an unauthorized or malicious build runner, or a poisoned dependency, producing an artifact that does not correspond to its claimed source.
3. An insider with legitimate signing access who approves a configuration that is authenticated but prohibited by policy, such as a debug flag that must not reach a flight build.
4. A compromised or leaked signing key. The case of interest is whether the system continues to accept updates signed with the key after it has been revoked.
5. An onboard software fault, such as a failed health check or an installation interrupted part way. This actor is not adversarial, but a rollback path that handles only adversarial failure would be incomplete for an operational spacecraft.
6. Ground and space state divergence: a disagreement between what the ground segment believes is installed and what is running, whether from falsified telemetry or from an honest missed update.

Table 1 lists what the model trusts. Neither actor 1 nor actor 3 controls the whole authorized update path. Actor 1 has no signing authority. Actor 3 can sign but cannot alter the policy check, which runs independently at ground authorization and again onboard.

**Table 1.** Trust assumptions of the threat model.

| Component | Treatment |
|---|---|
| Uplink and ground network | Untrusted (actor 1) |
| Build runner and dependencies | Untrusted (actor 2) |
| Signing key | Trusted until revoked (actor 4) |
| Person authorizing a release | Trusted to sign, not trusted on configuration content (actor 3) |
| Ground authorization logic and onboard verification code | Trusted |
| Signing HSM and its operators | Trusted (out of scope) |
| Onboard runtime state and telemetry | Verified by attestation and reconciliation (actors 5, 6) |

Three classes of threat are outside the model: RF jamming and spoofing, physical tampering with ground hardware, and an insider with root access to the signing HSM. A compromise that gives an attacker both the signing capability and control of the authorization process, as in the AcidRain management-segment incident, is also outside the model. In that situation every mechanism evaluated here would be operating under the attacker's control. The ladder addresses the cases in which an attacker, or a fault, lies at some point in the update path short of that complete control.

### 3.2 The S0 to S5 ladder

Each condition includes every mechanism of the one below it plus one new mechanism (Table 2). Because every condition above S0 is S0 plus one further mechanism, a difference in detection, time, or overhead between adjacent conditions is attributable to that mechanism.

**Table 2.** The assurance ladder and the actor each added mechanism mainly addresses.

| Condition | Mechanisms present | Added mechanism | Mainly addresses |
|---|---|---|---|
| S0 | Signature and local revocation list | (baseline) | External attacker (in-transit tampering); revoked signing key |
| S1 | S0 + SBOM | Software bill of materials | Compromised build (undisclosed or vulnerable dependencies) |
| S2 | S1 + provenance | SLSA/in-toto-style provenance | Compromised build (source-to-binary correspondence); downgrade |
| S3 | S2 + attestation | Boot and runtime attestation | State divergence (what is running, not only what was sent) |
| S4 | S3 + rollback | Verified A/B partition rollback | Onboard fault; interrupted installation |
| S5 | S4 + evidence | OSCAL-informed structured evidence and policy check | Insider with legitimate access (prohibited but signed configuration) |

The pipeline requires that the same artifact and code run under any of the six conditions through configuration alone. The ladder does not claim that these six mechanisms are the only ones worth measuring or that the order is the only defensible one. Placing SBOM before provenance, for example, is a design choice.

## 4. System design

### 4.1 Pipeline

The implementation moves an artifact through twelve stages (Fig. 1): source, reproducible build, provenance generation, SBOM generation, signed release, ground authorization, simulated uplink, onboard signature and policy verification, installation, boot and runtime attestation, health validation, and rollback or approval, followed by an updated authorization-evidence record that feeds the next cycle. Every stage that can produce audit value writes a structured record to one append-only evidence store, including at conditions below the one where a mechanism activates. This allows the evaluation to separate evidence that existed and was checked from evidence that existed and was not.

![](docs/assets/manuscript/fig1_pipeline.png)

A single configuration read at run time sets one boolean flag per mechanism. Each stage checks its own flag, and an inactive mechanism is skipped, not replaced by a stub that reports success. A detection at condition S(n) therefore shows that mechanism n caught the case.

### 4.2 Fidelity of components

Several components are reduced-fidelity stand-ins chosen to test whether a mechanism provides its intended property without infrastructure unavailable in the build environment.

- Provenance and SBOM are JSON documents produced by the pipeline's own code and shaped after SLSA v1 and in-toto statements and after CycloneDX. They test whether the pipeline binds, checks, and rejects on this data. They are not conformant to either specification.
- Attestation is a software construction: a measurement (installed binary hash, partition identifier, timestamp) signed with a dedicated Ed25519 key. A software-held key can be exfiltrated in ways a hardware-sealed key cannot, and the results apply only to this construction.
- The simulated uplink offers three fixed link profiles (ideal, LEO-typical, deep-space-typical), informed to an order of magnitude by CCSDS-class link budgets and not validated against any mission's telemetry.
- Ground authorization policy is a short Python deny-list, not a general policy engine such as OPA.
- Authorization evidence is a JSON document modeled on the shape of OSCAL (subject, findings, overall result), not a conformant OSCAL implementation.

Each choice trades conformance for testability of the question under study. A production system would reasonably choose differently.

### 4.3 Target stacks

Four targets were used: two stand-in applications (a C telemetry stub modeled on cFS's message-bus architecture and a C++ component stub modeled on F Prime's component and port architecture), and the unmodified NASA Core Flight System (tag v7.0.1) and JPL F Prime (tag v4.2.2). Here "unmodified" refers to the frameworks: no framework source was changed, and only the pipeline's own adapters were. Moving from stubs to real frameworks required changes to two adapter modules (build and health check) that had assumed the shape of the first stub, and one correctness fix: the version ledger had been a single global file, which produced a false downgrade detection when a second stack was evaluated. It is now scoped per stack. Both real frameworks are long-running processes, so the health check for them waits for a boot-success line, determined by observation, on the binary's standard output. The absence of a crash is not treated as a health signal.

## 5. Evaluation methodology

### 5.1 What the evaluation can and cannot show

Each of the 15 cases injects the specific condition that its target mechanism is written to detect, on a deterministic path, using an injector and detector implemented by the same author. A detection rate of 100% therefore demonstrates that the implementation contains the checks it claims to contain and that they work. This is an integration-level result about implementation correctness. It is not an estimate of assurance against attackers who vary their methods, and it does not support a claim about the probability of detecting an unknown attack.

Four design features give the results additional meaning within that scope.

- **Attribution.** The additive design and the ablation (Section 5.2) test whether each mechanism's detection comes from that mechanism and not from one beneath it.
- **Cost.** The overhead measurements are independent of whether attacks are anticipated.
- **Coverage.** The baseline comparison (Section 5.4) is a statement about which failure classes a design can address, and it is reported as scope analysis, not as a detection experiment.
- **Robustness.** The mutation experiment (Section 5.7) feeds the verifiers systematically generated variants rather than the 15 manually specified cases, so it can reveal inputs that were not anticipated when the injectors were written. Its operators were nevertheless chosen by the author, and it covers the document, signature, and configuration checks, not the runtime mechanisms (attestation freshness against a running system, health checks, rollback).

The 15 cases and the metric definitions were written during design, before the full evaluation was run, and the repository history records this. The stated first-detection condition for each case is a hypothesis. A case detected earlier or later than expected is reported as such.

### 5.2 Attack matrix, ablation, and adaptive scenarios

Table 3 lists the 15 cases, the stage at which each is injected, and the condition at which it was expected to be detected first.

**Table 3.** Attack and failure matrix.

| # | Case | Injected at | Expected first detection |
|---|---|---|---|
| 1 | Binary does not match source | Build, provenance | S2 |
| 2 | Missing or false provenance | Provenance | S2 |
| 3 | Incomplete SBOM | SBOM generation | S1 |
| 4 | Dependency with known test vulnerability | SBOM, dependency scan | S1 |
| 5 | Unauthorized build runner | Build environment | S2 |
| 6 | Modified update in transit | Uplink | S0 |
| 7 | Revoked signing key | Signature verification | S0 or S2 |
| 8 | Correct signature, prohibited configuration | Ground authorization, policy | S5 |
| 9 | Downgrade attempt | Ground authorization, onboard verification | S2 or S4 |
| 10 | Interrupted installation | Installation | S4 |
| 11 | Failed health check | Post-install health validation | S3 or S4 |
| 12 | Stale attestation | Onboard attestation | S3 |
| 13 | Ground and spacecraft inventory disagreement | Operational monitoring | S5 |
| 14 | Invalid recovery image | Rollback | S4 |
| 15 | False "successful installation" telemetry | Operational monitoring, attestation | S3 or S5 |

The ablation removes one mechanism at a time from an otherwise fully active condition. It uses six cases: SBOM (case 4), provenance (case 5), onboard attestation (case 12), trusted rollback (case 11), and machine-readable authorization, tested by two cases (8 and 15). The ablation answers RQ1: if detection falls to zero when only that mechanism is removed, the detection was not supplied by another mechanism.

Two adaptive scenarios combine vectors in sequence: (A) a rogue build runner followed by in-transit tampering, and (B) an interrupted installation followed by a stale attestation. They test whether the pipeline halts at the first vector it has a mechanism for. They do not test an attacker who varies timing or evades detection.

### 5.3 Metrics

- **Detection rate:** the fraction of trials in which the pipeline rejects the injected case, read from the pipeline result fields.
- **Time to detection and time to trusted restoration:** wall-clock seconds for the relevant pipeline call, measured with `time.perf_counter()`. For cases that end in rollback the metric is time to restoration. These are timings on the evaluation machine, useful for comparing conditions on the same hardware and not as flight timings.
- **Update acceptance accuracy:** a confusion matrix per condition in which a legitimate update is the positive class: true positive (legitimate update approved), true negative (attack rejected), false positive (attack approved), false negative (legitimate update rejected).
- **Evidence-processing effort:** the number of evidence records per run, used as a proxy for review burden. No operator study was performed.
- **Traceability completeness:** the fraction of stages expected to be active at a condition that wrote at least one evidence record.
- **Storage overhead:** the size in bytes of the artifacts a condition adds beyond S0 (SBOM, provenance, attestation, evidence), measured from file sizes.
- **Reproducibility:** the fraction of build trials in which two independent builds from the same source gave identical binaries.

The baseline for every overhead metric is S0, since the comparison is among conditions and S0's own cost is the correct zero point.

### 5.4 Baselines

Three baselines are compared against the 15 cases. The first is a hash-only deployment: a release host stores an artifact and the SHA-256 digest of the uploaded bytes, as GitHub does for release assets [4], and the deployer installs the artifact if and only if its digest matches. The second is an unmodified python-tuf 7.0.0 repository and client. Both were executed. The third is Uptane, which was not executed: each case is classified from the text of the Uptane Standard 2.1.0 [21] as native (the standard requires a mechanism for it), partial analogue (a related mechanism exists but does not specify the behavior the case tests), stated out of scope (the standard says so), or not addressed (no concept found in the standard). Cases that a baseline's specification has no mechanism for are recorded as out of scope with a stated reason and are not run as scenarios. For all three the comparison is a coverage analysis. Where a check is deterministic, repeated trials confirm that the harness is stable and do not estimate a detection probability.

### 5.5 Protocol and environment

Each condition and case was run for 30 trials. Each trial applies the same scenario input to a deterministic code path, so the detect or no-detect outcome does not vary between trials. What varies is execution time: across ablation trials on identical inputs, times ranged from 0.73 s to 1.55 s on the cFS stand-in and up to 3.57 s on the real frameworks. Wilson 95% intervals for rates are therefore a formally correct summary of a rate observed over repeated runs and are not evidence that detection could have failed on a trial. Confidence intervals for mean times describe real run-to-run variation. The interval code was checked against a third-party implementation (statsmodels) and an independent closed-form calculation.

All reported results were produced on one machine: an Intel Core i9-9980HK with 64 GB RAM running macOS 26.5.2, Docker 29.6.2, and Python 3.11.7. Because every figure comes from one machine, within-stack and cross-stack timings are measured under the same conditions. They are not flight timings, and the real-framework figures include container launch overhead (Section 8).

### 5.6 Internal review of the implementation

The implementation was reviewed in four separate passes by AI systems, each given the source with no prior findings: one by Claude in a separate session, and one each by OpenAI models, Zhipu AI's GLM, and DeepSeek. These passes led to fixes for 21 defects, and a further 10 were found during real-hardware validation (31 logged defects in total). The passes are reported as a validation procedure for the implementation, not as a research result, and Section 8 states what they do not substitute for.

### 5.7 Mutation experiment

The experiment gives each verifier inputs that were generated by generic operators, rather than by an injector written for a named case. It targets the checks that parse a document or a configuration: SBOM verification (S1), provenance verification (S2), attestation verification (S3), signature verification (S0), and the prohibited-configuration policy (S5). Each run starts from valid artifacts generated by the pipeline's own code.

For the three JSON documents the operators are: random single-bit flips of the serialized bytes (400 per document); truncation at a random offset (100); deletion of every key and list element in turn; replacement of every leaf by values of eleven other types and values; a change to every scalar leaf; insertion of a duplicate key with a different value; replacement of each scalar by the value from a valid document for a different binary; and six semantics-preserving rewrites (indentation, key order, escapes, whitespace) as controls. For the binary, 200 single-bit flips are checked against the signature, the SBOM's declared hash, and the provenance subject digest, and four truncations or extensions against the signature. For the signature file, 200 bit flips and four other malformations (truncated, extended, empty, half length) are checked against the signature check. For the policy, a grid of 14 spellings of the key `debug_mode` (case, whitespace, fullwidth characters, hyphen, camel case, a zero-width character, a Cyrillic look-alike, and others) against 16 spellings of the value meaning on and 13 meaning off, plus four structural wrappers.

A mutant is first parsed with the same JSON parser the verifier uses. If it parses to the same document, it is a neutral rewrite and should be accepted. If it parses to a different document, it is a changed document, and the outcome is recorded as rejected cleanly, rejected only by an unhandled exception, or accepted. Every accepted changed document is attributed to the JSON path that changed. A field whose every change was rejected is one the verifier checks, and a field whose changes were accepted is one it does not read. The random seed was 20261028. Because the artifacts contain timestamps, exact counts vary by a few mutants between runs.

## 6. Results

All figures are from 30 trials per condition and case unless noted. Rates carry Wilson 95% intervals (n = 30 gives 89% to 100% for 30 of 30). Times are means.

### 6.1 Detection and time to detection

All 15 cases were detected in 30 of 30 trials at their tested condition on all four targets, with no false positives or false negatives. Table 4 gives the mean time to detection, or to trusted restoration for cases that end in rollback. Case 13 is a direct call to the reconciliation check and not a full pipeline run, so its time is not comparable with the others. Differences among cases depend in part on the stage at which the pipeline halts, which was not decomposed.

**Table 4.** Mean time to detection (D) or trusted restoration (R), in seconds, at the tested condition.

| Case | Condition | Metric | cfs | fprime | cfs-real | fprime-real |
|---|---|---|---|---|---|---|
| 1 | S2 | D | 0.263 | 0.325 | 0.335 | 0.392 |
| 2 | S2 | D | 0.252 | 0.250 | 0.064 | 0.094 |
| 3 | S1 | D | 0.260 | 0.301 | 0.278 | 0.352 |
| 4 | S1 | D | 0.272 | 0.329 | 0.252 | 0.351 |
| 5 | S2 | D | 0.254 | 0.302 | 0.319 | 0.384 |
| 6 | S0 | D | 0.263 | 0.320 | 0.310 | 0.386 |
| 7 | S0 | D | 0.251 | 0.301 | 0.275 | 0.341 |
| 8 | S5 | D | 0.285 | 0.323 | 0.329 | 0.409 |
| 9 | S2 | D | 0.268 | 0.356 | 0.331 | 0.438 |
| 10 | S4 | R | 0.303 | 0.359 | 0.352 | 0.505 |
| 11 | S4 | R | 0.297 | 0.356 | 0.426 | 0.539 |
| 12 | S4 | R | 0.320 | 0.382 | 2.581 | 2.130 |
| 13 | S5 | D | 0.0002 | 0.0002 | 0.0003 | 0.0003 |
| 14 | S4 | R | 0.301 | 0.385 | 0.467 | 0.621 |
| 15 | S5 | D | 0.402 | 0.533 | 0.720 | 1.033 |

### 6.2 Update acceptance accuracy

The confusion matrices were identical on all four targets (Table 5). No attack case is tested at S3, because the cases whose mechanism activates at S3 (11, 12, 15) are tested at S4 or S5, so the S3 row contains only legitimate updates.

**Table 5.** Confusion matrix per condition, identical on all four targets (30 trials per case).

| Condition | TP | FN | TN | FP | Attack cases tested |
|---|---|---|---|---|---|
| S0 | 30 | 0 | 60 | 0 | 6, 7 |
| S1 | 30 | 0 | 60 | 0 | 3, 4 |
| S2 | 30 | 0 | 120 | 0 | 1, 2, 5, 9 |
| S3 | 30 | 0 | 0 | 0 | none |
| S4 | 30 | 0 | 120 | 0 | 10, 11, 12, 14 |
| S5 | 30 | 0 | 90 | 0 | 8, 13, 15 |

### 6.3 Cost of each added mechanism

Happy-path success and reproducibility were 100% (89% to 100%) at every condition on all four targets, and traceability completeness was 100% at every condition. Table 6 and Fig. 2 give the cost progression.

**Table 6.** Mean happy-path pipeline time in seconds, and evidence records per run.

| Condition | Evidence records | cfs | fprime | cfs-real | fprime-real |
|---|---|---|---|---|---|
| S0 | 7 | 0.228 | 0.288 | 0.287 | 0.375 |
| S1 | 9 | 0.237 | 0.298 | 0.267 | 0.385 |
| S2 | 12 | 0.253 | 0.291 | 0.305 | 0.445 |
| S3 | 15 | 0.272 | 0.353 | 2.512 | 2.002 |
| S4 | 17 | 0.295 | 0.364 | 2.483 | 1.976 |
| S5 | 21 | 0.328 | 0.518 | 2.774 | 2.325 |

**Table 7.** Storage added relative to S0, in bytes.

| Condition | cfs | fprime | cfs-real | fprime-real |
|---|---|---|---|---|
| S0 | 0 | 0 | 0 | 0 |
| S1 | 613 | 613 | 595 | 583 |
| S2 | 1264 | 1264 | 1237 | 1219 |
| S3 | 1631 | 1631 | 1593 | 1569 |
| S4 | 1624 | 1623 | 1596 | 1578 |
| S5 | 5747 | 5747 | 5720 | 5703 |

![](docs/assets/manuscript/fig2_cost.png)

On the cFS stand-in, the full ladder raises mean time from 0.228 s to 0.328 s (44%), triples the evidence records (7 to 21), and adds 5747 bytes, of which S5 contributes 4123. S5 is the most expensive single step in storage: its increment is more than twice the combined increment of S1 through S4. The S4 value is 7 bytes below S3 on the cFS stand-in; no significance test was run on that difference, and it is small compared with the S5 step. On the real frameworks the step from S2 to S3 (0.305 s to 2.512 s for cFS, 0.445 s to 2.002 s for F Prime) coincides with the introduction of the container-based health check (container launch and a wait for a boot-success line), and its components were not separated (Section 8). Between S0 and S2, the real frameworks add 6% (cFS) and 19% (F Prime). On the F Prime stand-in the full ladder adds 80% (0.288 s to 0.518 s). The 95% intervals for S0 and S5 do not overlap on either stand-in, but the per-step increments at S1 and S2 are within run-to-run noise on some targets (S1 is below S0 on cfs-real), so only the cumulative difference should be read as an effect.

### 6.4 Real frameworks and build reproducibility

Detection, ablation, and adaptive-scenario results on the real frameworks match those on the stand-ins. Build reproducibility differs. Two independent from-scratch builds of the real F Prime binary were byte-for-byte identical. Two builds of the real cFS binary differed in 22 of about 915,000 bytes. Using `cmp -l` and a diff of printable strings, the differences were isolated to a build timestamp string that cFS's build system embeds at two offsets, and to a 20-byte ELF build-ID hash that changes as a consequence. All other bytes, including all flight-software logic, were identical. This is a property of the two frameworks' own build systems, not of the pipeline. The reproducibility metric therefore means bit-identical for F Prime and identical apart from a known, explained, non-functional difference for cFS.

### 6.5 Divergence from the expected detection condition

Cases 7 and 9 were detected at S0 and S2 respectively, the earlier of their two expected conditions. Case 12 (stale attestation) was expected to be detected first at S3, where attestation activates. The harness tests it at S4, with a backdated attestation timestamp, and measures whether the system completes a rollback. The test is therefore stronger than detection alone, and the S3 entry in Table 3 should be read as the condition at which the detecting mechanism becomes available.

### 6.6 Ablation

Table 8 gives the ablation results. In every case detection was 100% with the mechanism active and 0% with it removed, on all four targets (n = 30 each). This shows that detection of each failure class depends on its own mechanism and is not supplied by another mechanism. Removing a check removes its detection by construction, so the result establishes non-redundancy and provides no information about robustness to attack variants.

**Table 8.** Ablation results (identical on all four targets).

| Mechanism removed | Case | Condition | Detection active | Detection ablated |
|---|---|---|---|---|
| SBOM | 4 | S1 | 100% | 0% |
| Build provenance | 5 | S2 | 100% | 0% |
| Onboard attestation | 12 | S4 | 100% | 0% |
| Trusted rollback | 11 | S4 | 100% | 0% |
| Machine-readable authorization | 15 | S5 | 100% | 0% |
| Machine-readable authorization | 8 | S5 | 100% | 0% |

### 6.7 Adaptive scenarios

Both scenarios were caught in 30 of 30 trials on all four targets, and in both the pipeline halted before the second vector was attempted: scenario A at ground authorization and scenario B at installation. The scenarios test a halt on the first of two vectors the pipeline already detects. They do not test an attacker who attempts the second vector independently or times an attack around a detection window.

### 6.8 Baseline coverage

Table 9 and Fig. 3 compare the baselines with the ladder. The hash-only and TUF columns come from executed harnesses. The Uptane column comes from reading the standard and was not executed.

A hash-only deployment rejects case 6, and only when the digest reaches the deployer by a path the attacker cannot rewrite. When the attacker controls the host or channel that serves both artifact and digest, the same attack passes (0 of 30 rejected). The hash check passes the artifact in cases 1, 2, 3, 4, 5, 7, 8, and 9, because in each the malicious or superseded artifact is published with its own correct digest. These outcomes follow from what a digest is, and the harness demonstrates them with real bytes and real SHA-256 comparisons. Cases 10 to 15 concern state after installation, which a pre-install check does not address.

TUF has a native mechanism for three cases: 6 (target hash and length), 7 (key revocation through root rotation), and 9 (version monotonicity). All three were caught in 30 of 30 trials. The other 12 cases have no corresponding mechanism in TUF's specification. For case 1, a binary built from other source and then signed is consistent with its own signed metadata, so TUF has no notion of source-to-binary correspondence. TUF's metadata expiration partly overlaps with case 12 but concerns the repository's own metadata, not the state of running software, and it is not scored as coverage.

Uptane is the closer comparison for a system with a ground-side decision service and a vehicle-side verifier. Reading the standard [21], three cases have a native mechanism: 6 (hashes and length in the Targets metadata must match the image), 7 (the Root role distributes and revokes keys), and 9 (release counters and metadata version checks against rollback). Four have a partial analogue: 10 (installation should occur with a backup of the current image, but no detection or recovery procedure is specified), 12 (the ECU version report carries a verifiable time and a nonce that the Director checks, but staleness of an installed-state quote is not specified), 13 (the Director compares the version manifest with its inventory database, but the required checks cover ECU presence, signatures, and time, and the database records identities and keys, not installed images or policy), and 15 (the ECU-signed version report contains the hash of the installed image, but it is self-reported and the threat model assumes at most one compromised ECU per vehicle). Cases 1, 2, and 5 are stated to be out of scope, since the standard excludes compromise of the supply chain and the build system. Cases 3, 4, 8, 11, and 14 are not addressed: the standard contains no SBOM, dependency data, policy language, health check, or verification of a recovery image. Uptane therefore shares TUF's boundaries for provenance, SBOM, policy, health validation, and recovery, and comes closer than TUF to the state-reconciliation cases (12, 13, and 15) through its version report and Director checks. The classification is conservative in one respect: a standard that says "SHOULD" for a behavior is counted as a partial analogue, not as coverage.

These are statements about design scope. They show that the failure classes in this matrix lie outside what the baselines were built to address. They do not show that TUF or Uptane is weak, they are not a measured comparison of detection performance, and the Uptane column has not been confirmed by running an implementation.

**Table 9.** Coverage of the 15 cases. Hash-only and TUF were executed. Uptane is read from the standard. Partial means a related mechanism exists that does not specify the behavior tested.

| Case | Hash-only | TUF | Uptane (specification) | Ladder (first condition) |
|---|---|---|---|---|
| 1 | not covered | not covered | out of scope | S2 |
| 2 | not covered | not covered | out of scope | S2 |
| 3 | not covered | not covered | not addressed | S1 |
| 4 | not covered | not covered | not addressed | S1 |
| 5 | not covered | not covered | out of scope | S2 |
| 6 | caught (digest on independent path) | caught | native | S0 |
| 7 | not covered | caught | native | S0 |
| 8 | not covered | not covered | not addressed | S5 |
| 9 | not covered | caught | native | S2 |
| 10 | not covered | not covered | partial | S4 |
| 11 | not covered | not covered | not addressed | S4 |
| 12 | not covered | not covered | partial | S4 |
| 13 | not covered | not covered | partial | S5 |
| 14 | not covered | not covered | not addressed | S4 |
| 15 | not covered | not covered | partial | S5 |

![](docs/assets/manuscript/fig3_coverage.png)

### 6.9 Mutation experiment

Binary and signature. All 204 mutations of the binary (200 bit flips and four truncations or extensions) were rejected by the signature check, and the 200 bit flips were also rejected by the SBOM's declared-hash check and by the provenance subject-digest check. All 204 mutations of the signature file were rejected. No exception was raised.

Documents. Table 10 gives the outcomes for the three JSON documents. In the first run, 408 of the 523 rejections of mutated SBOMs, 107 of 465 for provenance, and 336 of 579 for attestation were not clean rejections: the verifier raised an unhandled exception (a JSON decoding error, a type error, a missing key). The update was still not accepted, because the exception propagates out of the pipeline run, but no evidence record of the rejection was written. This is a defect in a design that treats evidence as primary. The 15 manually specified cases did not expose it, because each of them presents a well-formed document that fails a check. The three verifiers now convert parse and structure errors into a clean rejection with an evidence record, and the repeated run produced no exceptions.

**Table 10.** Outcomes for mutated documents after the fix. "Unhandled before fix" is the number of rejections in the first run that were unhandled exceptions.

| Document (verifier) | Mutants | Rejected | Unhandled before fix | Accepted, content changed | Accepted, same content |
|---|---|---|---|---|---|
| SBOM (S1) | 793 | 523 | 408 | 264 | 6 |
| Provenance (S2) | 749 | 465 | 107 | 278 | 6 |
| Attestation (S3) | 594 | 585 | 336 | 0 | 9 |

The accepted changed documents show which fields each verifier reads. Every change to the declared artifact hash in the SBOM was rejected, as was every deletion of a required component field (name, version, or type, for each component). Changes to `bomFormat`, `specVersion`, `serialNumber`, `version`, the hash algorithm label, and the name, type, and version of the other components were accepted. For provenance, every change to the subject digest and to the builder identity was rejected. Changes to `_type`, `predicateType`, `buildType`, the recorded source commit, the dirty-tree flag, the recorded release version, and the subject name were accepted. Two consequences follow. First, the source commit in the provenance record is stored and never compared with anything, so S2 attests the builder identity and the binding to the binary and does not verify the source. Second, the SBOM and provenance documents are not signed in this implementation, so a party able to write both can produce a consistent pair; the checks establish that each document is consistent with the binary, not who produced it. For attestation, which is signed over a canonical form of the quote, no change to the quote or the signature was accepted. The nine accepted attestation mutants were six neutral rewrites and three that changed only the letter case of the signature's hex digits and decode to the same bytes.

Policy. Table 11 gives the results for the prohibited-configuration rule. Before the fix, the rule accepted four spellings of the value meaning on (`"y"`, `"t"`, `"enabled"`, `"enable"`) under every equivalent spelling of the key, 24 of 96 combinations, and it rejected a flag whose value was `[false]` or `{"enabled": false}`, 12 of the 182 combinations meaning off, which is a false positive. The value vocabulary was extended, containers are now judged by their members, and a string that is neither a recognized on-value nor a recognized off-value is treated as on, so an unrecognized spelling fails closed. After the fix, no equivalent spelling of the key with any on-value was accepted, and no off-value was rejected. Eight alternative key names (`debug-mode`, `debugMode`, `build.debug_mode`, a name containing a zero-width character, a Cyrillic look-alike, `debug__mode`, `debug_modes`, `debug`) and three structural wrappers (a nested object, a list of objects, a JSON-encoded string) are accepted under every value. Whether these mean "debug on" depends on how the flight software parses its configuration, which a deny-list on the ground cannot know. These cases are reported as a structural limitation of deny-list policies and not as defects that a longer list would remove.

**Table 11.** Policy rule outcomes on the configuration grid (accepted means the configuration passes the rule).

| Group | Configurations | Accepted before fix | Accepted after fix |
|---|---|---|---|
| Equivalent key spelling (6), on-value (16) | 96 | 24 | 0 |
| Equivalent key spelling (6), off-value (13) | 78 | 66 | 78 |
| Alternative key name (8), on-value (16) | 128 | 128 | 128 |
| Structural wrapper, on | 4 | 3 | 3 |

The regression suite, which exercises all 15 cases at every condition, passes after the changes (Section 6.10), and 37 new tests cover the fixes. The mutation counts are for one run. The 30-trial timing and detection experiments of Sections 6.1 to 6.8 were not rerun after the fixes, which change only the error path of three verifiers and the value vocabulary of one rule.

### 6.10 Reproducing the results

The code, test suite, raw results, and this paper's figures are in the archived release cited in the Data and code availability statement. Python 3.10 or newer is required, and Docker is needed only for the real-framework targets. From the repository root:

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python3 -m pytest -q                           # regression suite
python3 evaluation/experiment.py               # Sections 6.1 to 6.3 (stand-in cfs)
python3 evaluation/experiment.py fprime        # second stand-in
python3 evaluation/ablation.py                 # Section 6.6
python3 evaluation/baselines/tuf_baseline.py   # Section 6.8, TUF
python3 evaluation/baselines/hash_only_baseline.py   # Section 6.8, hash-only
python3 evaluation/baselines/uptane_spec_analysis.py # Section 6.8, Uptane (specification)
python3 evaluation/mutation_attacks.py               # Section 6.9
python3 docs/assets/make_manuscript_figures.py       # Figures 1 to 3
```

Raw outputs are written to `evaluation/results/`. Runs of the full 30-trial evaluation take several minutes per target. Absolute times depend on the machine, and the comparisons among conditions are the reproducible quantity. The real-framework targets require building the pinned cFS and F Prime images, as described in the repository's `cfs-app` and `fprime-app` directories.

## 7. Discussion

### 7.1 What the results show and what they do not

The 100% detection and 0% ablated results of the 15-case matrix are interpreted as verification of the implementation. Each of the 15 injections was written to trigger a specific check, and each check fires. This outcome is useful, because an assurance mechanism that does not detect what it is designed to detect has no value, and the evaluation identified and corrected several such defects during development. It is not evidence that the mechanisms would detect an attacker who varies the method. The ablation adds a different kind of evidence: it shows that no mechanism's detection is carried by another, so each line item of the ladder is a distinct unit of assurance.

The measurements that do not depend on the attacker's behavior are the cost figures (Section 6.3), the build reproducibility finding (Section 6.4), and the coverage analysis (Section 6.8). The first two describe the pipeline and its targets, and the last describes the scope of the compared designs.

The mutation experiment (Section 6.9) was added to move beyond that boundary for the document and configuration checks. It identified two defects that the 15 cases had not exposed: malformed input was rejected only by unhandled exceptions, and the policy rule missed equivalent spellings of the prohibited flag. Both were corrected, which indicates that generated variants can reveal problems that manually specified cases do not. The experiment also established which fields each verifier evaluates. The attestation verifier, which is cryptographically bound to its content, accepted no change. The SBOM and provenance verifiers accepted changes to every field they do not read, among them the recorded source commit, so a pass at S2 should be interpreted as "built by an authorized builder identity and bound to this binary", and not as "built from this source".

The experiment does not substitute for an independent evaluation. The operators and the grid of configuration spellings were selected by the author, the documents are the pipeline's own formats, and the experiment does not exercise the runtime mechanisms (attestation freshness, health checks, rollback). An evaluation that supports claims about unanticipated attacks would additionally require injectors and variants produced by a party other than the author of the detectors, a human red team attempting to defeat the pipeline with knowledge of its design, and real operational artifacts and link traces. None of these is part of the present study; Section 8 lists them as the principal direction for follow-on work.

### 7.2 Implications for mission design

The cost results give a mission designer a graded set of options. On the cFS stand-in, SBOM and provenance (S1 and S2) add 613 and 651 bytes and about 10 ms and 25 ms of cumulative time over S0, although the time increments are within noise on some targets (Section 6.3). In this matrix they are the levels at which the failure classes of cases 1 to 5 become detectable. S5 is the most expensive single step in storage (4123 bytes against 1624 for S1 to S4 combined) and adds 33 ms over S4 on the cFS stand-in. It is also the level at which cases 8, 13, and 15 become detectable, and the ablation shows that removing the machine-readable authorization mechanism removes their detection (Table 8). A mission with tight storage and link budgets could stop at S4 and would then forgo coverage of those three failure classes, which concern prohibited but signed configurations, disagreement between ground and spacecraft inventory, and false installation telemetry. A mission that must show an auditor what was approved and what is running would need S5 for the evidence itself.

### 7.3 Why a matching hash does not close the problem

A natural question is what remains once the deployed bytes match a published release hash. The baseline results answer it directly. The digest binds bytes to bytes. Whoever can publish an asset also publishes its digest, so the check cannot distinguish an authorized release from an unauthorized one. The digest is computed over the upload and therefore says nothing about the source, the build, or the dependencies that produced it. A superseded release has a valid digest, and nothing in a digest describes the configuration or the state of the spacecraft after installation. An onboard verifier also needs a trust root that it holds independently, which a digest served from the same host does not provide. Release digests are useful and should be used. The point of the ladder is that integrity of the bytes is one property among several that a flight update depends on.

### 7.4 Relation to composed terrestrial tooling

The coverage analysis does not show that no combination of existing tools could address the 15 cases. Reading the specifications, a composition could plausibly cover most of the matrix. Uptane or TUF covers cases 6, 7, and 9 and, for Uptane, part of 12, 13, and 15. SLSA provenance and in-toto attestations address the subject of cases 1, 2, and 5 (the Uptane standard itself names in-toto as a complement). CycloneDX or SPDX tooling with a vulnerability scanner addresses cases 3 and 4, a general policy engine addresses case 8, and the RATS architecture addresses attestation (case 12). Cases 10, 11, and 14 (interrupted installation, failed health check, invalid recovery image) concern the installer, boot loader, and health monitor, not the supply-chain frameworks, and would need an A/B update mechanism with health-gated rollback from elsewhere. The ladder can be read as one such composition with its marginal costs measured. SLSA, in-toto, Sigstore, RATS, and Uptane were not executed against the matrix, and this mapping is a reading of their specifications and not a measurement. What the present evaluation does not show is whether such a composition would work as a whole without the integration the ladder provides, or what it would cost. Two properties of the spacecraft setting remain less clearly covered by the tools reviewed: an autonomous rollback decision with no operator in the loop (S4), and evidence aggregated for a ground or audit consumer who cannot inspect the artifact (S5). This is an observation about the literature reviewed. Evaluating a composed terrestrial pipeline against the same matrix is a direction for future work.

### 7.5 Threats to validity

Construct validity: the injections and detectors are author-specified, so detection rates measure implementation correctness, and the mutation operators and the policy spelling grid are also the author's. Internal validity: outcomes are deterministic, so only timing varies between trials, and all results come from one machine. External validity: the pipeline is a simulation. It has no flight hardware, no CCSDS-conformant link, and no hardware root of trust, and the two real frameworks are run unmodified inside containers. Conclusion validity: confidence intervals for rates describe repeated execution and not sampling from an uncertain process, and timing intervals describe machine-level variation.

## 8. Limitations

1. **Author-specified injections.** Detection results verify the implementation against anticipated failures. The mutation experiment adds generated variants, but its operators, documents, and policy grid are the author's, and it does not cover the runtime mechanisms. The results do not estimate performance against an adversary who adapts, as discussed in Section 7.1.
2. **Uplink realism.** The link model is informed only to an order of magnitude by CCSDS-class link budgets and has not been validated against any mission's telemetry. No RF or physical-layer behavior is simulated.
3. **No hardware root of trust.** Attestation is a software-held Ed25519 signature over a measurement. The results show that the attestation concept works in this pipeline. They do not show resistance to extraction of the attestation key, which a hardware root exists to prevent.
4. **Container overhead.** The real cFS and F Prime binaries run inside Docker. The persistent-process health check that makes S3 and above measurable launches a container and waits for a boot-success line. Mean happy-path times on the real frameworks rise from 0.3 to 0.4 s at S0 to S2 to 2.0 to 2.8 s at S3 to S5. This increase is attributed to the container launch and the boot wait; the two were not separated, and the attestation cost within them was not measured. The timings do not approximate flight-computer execution.
5. **Reproducibility.** The reproducibility figures come mainly from the stand-in stubs. The two real-framework data points apply to the pinned versions (cFS v7.0.1, F Prime v4.2.2) and not to flight software in general.
6. **Adaptive scenarios.** The two scenarios test whether the pipeline halts at the first vector. They do not model an attacker who varies timing or evades the checks.
7. **Baselines.** Only a hash-only deployment and TUF were executed. Uptane was classified from its specification and has not been confirmed by running an implementation. SLSA, in-toto, Sigstore, and RATS were not evaluated. All comparisons are scope analyses.
8. **Independent review.** No human domain expert has completed a review of the threat model and mitigations. The four AI-driven review passes (Section 5.6) found and led to fixes for real defects, including defects in earlier fixes. The first pass used the same AI system that did most of the implementation work, in a separate session, so it was independent in context but not in system. The other three used different systems. All four were directed by one author, and none was conducted by a party outside the author-plus-AI process. This does not substitute for human review.
9. **Unsigned SBOM and provenance, unchecked fields, and rerun scope.** In this implementation the SBOM and provenance documents are not signed, and the verifiers do not read several fields, including the recorded source commit (Section 6.9). The fixes made after the mutation experiment changed the error path of three verifiers and the value vocabulary of the policy rule. The regression suite passes after them, and the 30-trial experiments of Sections 6.1 to 6.8 were not rerun.

## 9. Conclusion

This paper measured what each of five added mechanisms contributes to a signed spacecraft update pipeline, and what it costs. On four targets, including the unmodified NASA cFS and JPL F Prime frameworks, each mechanism detected its assigned failure class and no other mechanism supplied that detection. The full ladder adds 44% (cFS stand-in) and 80% (F Prime stand-in) to mean pipeline time, triples evidence records, and adds 5.7 kB of storage, with S5 the largest single step in storage. Two builds of F Prime were bit-identical and two builds of cFS differed in 22 bytes traced to a timestamp. A hash comparison and TUF each address only a small subset of the 15 failure classes, because the rest lie outside their design scope, and a reading of the Uptane standard finds three native mechanisms, four partial analogues, and eight cases that are out of scope or not addressed. A mutation experiment on the document, signature, and policy checks identified two defects not exposed by the manually specified cases, both subsequently corrected, and showed that the SBOM and provenance verifiers do not read several fields, including the source commit.

These results verify an implementation and quantify its cost. They do not establish detection against unanticipated attacks, behavior on flight hardware, or hardware-rooted attestation. The most direct next steps are variants and injectors produced by an independent party and a human red team, an executed Uptane baseline and composed terrestrial pipeline against the same matrix, signing of the SBOM and provenance documents with verification of the source commit, and measurement on flight-representative hardware.

---

## CRediT authorship contribution statement

**Aman Singh:** Conceptualization, Methodology, Software, Validation, Formal analysis, Investigation, Resources, Data curation, Writing – original draft, Writing – review & editing, Visualization, Supervision, Project administration.

## Declaration of competing interest

The author declares no competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.

## Funding

This research did not receive any specific grant from funding agencies in the public, commercial, or not-for-profit sectors.

## Data and code availability statement

The source code, test suite, evaluation harness, raw results, and figure scripts are archived as a versioned release at Zenodo (DOI: [ZENODO-DOI]). Development continues at https://github.com/Zartharas/verifiable-spacecraft-lifecycle.

## Declaration of generative AI and AI-assisted technologies in the manuscript preparation process

During the preparation of this work the author used Claude (Anthropic), OpenAI's models, Zhipu AI's GLM, and DeepSeek. Claude wrote most of the pipeline's source code, test suite, and documentation to the author's specifications, diagnosed the root cause of several environment-dependent defects during real-hardware validation, designed the ablation study and adaptive scenarios, and assisted in drafting and revising this manuscript, including the revision in response to peer review. Four independent review passes of the codebase were run in fresh contexts without access to prior findings: the first with Claude in a separate session, and the second, third, and fourth with OpenAI's models, Zhipu AI's GLM, and DeepSeek respectively. Together they led to fixes for 21 defects, and 10 further defects were found during real-hardware validation.

AI-generated code, diagnoses, and findings were verified before being accepted. Root-cause claims were confirmed by direct testing, every fix was checked against the regression suite and, where applicable, against the real target frameworks, and all test executions on physical hardware, repository operations, and acceptance decisions were performed by the author. AI is not listed as an author. After using these tools, the author reviewed and edited the content as needed and takes full responsibility for the content of the publication. The process that designed the mitigations also designed and reviewed them, a limitation discussed in Section 8.

## References

[1] SentinelLabs. AcidRain: a modem wiper rains down on Europe. SentinelOne, 2022. https://www.sentinelone.com/labs/acidrain-a-modem-wiper-rains-down-on-europe/ (accessed 7 August 2026).

[2] M. Kang, S. Park, Y. Lee, A survey on satellite communication system security, Sensors 24 (2024) 2897. https://doi.org/10.3390/s24092897.

[3] SentinelLabs. AcidPour: new embedded wiper variant of AcidRain appears in Ukraine. SentinelOne, 2024. https://www.sentinelone.com/labs/acidpour-new-embedded-wiper-variant-of-acidrain-appears-in-ukraine/ (accessed 7 August 2026).

[4] GitHub. Releases now expose digests for release assets. GitHub Changelog, 3 June 2025. https://github.blog/changelog/2025-06-03-releases-now-expose-digests-for-release-assets/ (accessed 28 October 2026).

[5] SLSA. Supply-chain Levels for Software Artifacts (SLSA) specification, v1.2. https://slsa.dev/spec/v1.2/ (accessed 7 August 2026).

[6] in-toto. in-toto attestation framework, v1.0.2. https://in-toto.io/docs/specs (accessed 7 August 2026).

[7] Open Source Security Foundation. Sigstore. https://sigstore.dev (accessed 7 August 2026).

[8] The Update Framework. The Update Framework specification, v1.0.34. https://theupdateframework.io/spec/ (accessed 7 August 2026).

[9] T.K. Kuppusamy, A. Brown, S. Awwad, D. McCoy, R. Bielawski, C. Mott, S. Lauzon, A. Weimerskirch, J. Cappos, Uptane: securing software updates for automobiles, in: 14th escar Europe, 2016. https://ssl.engineering.nyu.edu/papers/kuppusamy_escar_16.pdf (accessed 28 October 2026).

[10] National Institute of Standards and Technology. Open Security Controls Assessment Language (OSCAL). https://pages.nist.gov/OSCAL/ (accessed 7 August 2026).

[11] M. Manulis, C.P. Bridges, R. Harrison, V. Sekar, A. Davis, Cyber security in New Space, Int. J. Inf. Secur. 20 (2021) 287-311. https://doi.org/10.1007/s10207-020-00503-w.

[12] I. Ahmad, J. Suomalainen, P. Porambage, A. Gurtov, J. Huusko, M. Höyhtyä, Security of satellite-terrestrial communications: challenges and potential solutions, IEEE Access 10 (2022) 96038-96052. https://doi.org/10.1109/ACCESS.2022.3205426.

[13] J. Vanlyssel, E. Sobrados, R. Anwar, G.C. Roman, A. Anwar, SpyChain: multi-vector supply chain attacks on small satellite systems, arXiv preprint arXiv:2510.06535, 2025. https://doi.org/10.48550/arXiv.2510.06535.

[14] J. Vanlyssel, G.C. Roman, K. Cook, S. Rahaman, A. Anwar, Trust without boundaries: an architectural analysis of satellite flight software, arXiv preprint arXiv:2608.14532, 2026. https://doi.org/10.48550/arXiv.2608.14532.

[15] A.B. Usman, Z. Afzal, M. Asplund, Bridging remote attestation and secure software updates in embedded systems, Int. J. Inf. Secur. 25 (2026) 75. https://doi.org/10.1007/s10207-026-01233-1.

[16] H. Birkholz, D. Thaler, M. Richardson, N. Smith, W. Pan, Remote ATtestation procedureS (RATS) architecture, RFC 9334, IETF, 2023. https://doi.org/10.17487/RFC9334.

[17] K. Sahlmann, V. Clemens, M. Nowak, B. Schnor, MUP: simplifying secure over-the-air update with MQTT for constrained IoT devices, Sensors 21 (2021) 10. https://doi.org/10.3390/s21010010.

[18] A. Qureshi, M. Marvi, J.A. Shamsi, A. Aijaz, eUF: a framework for detecting over-the-air malicious updates in autonomous vehicles, J. King Saud Univ. Comput. Inf. Sci. 34 (2022) 5456-5467. https://doi.org/10.1016/j.jksuci.2021.05.005.

[19] D. Ganesan, M. Lindvall, D. McComas, M. Bartholomew, S. Slegel, B. Medina, et al., An analysis of unit tests of a flight software product line, Sci. Comput. Program. 78 (2013) 2360-2380. https://doi.org/10.1016/j.scico.2012.02.006.

[20] C.E. Gonzalez, C.J. Rojas, A. Bergel, M.A. Diaz, An architecture-tracking approach to evaluate a modular and extensible flight software for CubeSat nanosatellites, IEEE Access 7 (2019) 126409-126429. https://doi.org/10.1109/ACCESS.2019.2927931.

[21] Uptane. Uptane Standard for Design and Implementation, version 2.1.0. https://uptane.org/docs/2.1.0/standard/uptane-standard (accessed 28 October 2026).
