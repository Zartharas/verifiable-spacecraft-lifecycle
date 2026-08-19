# Keys directory

Test key material for every signing/attestation mechanism in the S0-S5
ladder lands here, generated locally rather than committed:

- `test_signing_key.pem` / `test_signing_key.pub.pem` — S0 release
  signing keypair
- `attestation_key.pem` / `attestation_key.pub.pem` — S3 onboard
  attestation keypair
- `authorization_evidence_key.pem` / `authorization_evidence_key.pub.pem`
  — S5 machine-readable authorization evidence signing keypair
- `state_integrity.key` — HMAC key for `src/state_integrity.py`'s
  protection of the version ledger and partition state
- `revoked_keys.txt` (+ `revoked_keys.txt.hmac`) — revocation list for
  the signing-key-compromise test case, HMAC-protected against tampering
- `attestation_revoked_keys.txt` (+ `.hmac`) — separate revocation list
  for attestation-key revocation (added when attestation-key revocation
  was implemented, see ISSUES-AND-FIXES-LOG.md)

All key material (`*.pem`, `*.key`) and the HMAC sidecars (`*.hmac`) are
git-ignored — never commit real or test key material, per SECURITY.md and
Legal-Data-Sourcing-Notes.md. `revoked_keys.txt` and
`attestation_revoked_keys.txt` are also git-ignored as of Phase 8 (they
are constantly-changing local test/dev state, not project source; see
STATUS.md for the one-time `git rm --cached` cleanup this required, since
`revoked_keys.txt` had been tracked from an earlier commit before this
convention existed).

To regenerate a fresh test keypair:

```
python3 src/signing/signing.py
```

This directory is intentionally kept in git via this README so a fresh
checkout has the directory ready without needing `mkdir -p keys` before
first run.
