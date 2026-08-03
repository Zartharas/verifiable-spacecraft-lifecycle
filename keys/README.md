# Keys directory

Test signing keypairs land here (`test_signing_key.pem`,
`test_signing_key.pub.pem`) and `revoked_keys.txt` for the revocation test
case. All of these are git-ignored (`*.pem`, `*.key`) — never commit real
or test key material, per SECURITY.md and Legal-Data-Sourcing-Notes.md.

To regenerate a fresh test keypair:

```
python3 src/signing/signing.py
```

This directory is intentionally kept in git via this README so a fresh
checkout has the directory ready without needing `mkdir -p keys` before
first run.
