# Issues & Fixes Log

Every bug, security finding, or design flaw discovered during this project
gets an entry here — both because it makes for a clean, citable
contribution history on GitHub, and because some findings (e.g., a real
vulnerability in a dependency or in cFS itself) may warrant a responsible
disclosure per `SECURITY.md` rather than just a code fix.

**Template for each entry — copy this block for every new issue:**

```
## [ISSUE-###] Short title

- **Date found:** YYYY-MM-DD
- **Found during:** (phase / test case / activity)
- **Category:** bug | security finding | design flaw | dependency vulnerability
- **Severity:** low | medium | high | critical
- **Description:** what happened / what was found
- **Root cause:** why it happened
- **Fix:** what was changed, with commit hash/link once pushed
- **Disclosure status:** n/a | reported upstream (link) | pending disclosure timeline | disclosed publicly (date)
- **Verified fixed:** yes/no, how verified (e.g., regression test added)
```

---

## Log

*(No issues logged yet — project is in documentation phase, no code
written.)*

---

## Notes on responsible disclosure

If a real vulnerability is found in an upstream dependency (cFS itself,
SLSA/in-toto/Sigstore tooling, etc.) rather than in this project's own
code, follow the upstream project's own disclosure process rather than
disclosing it here first — link to the upstream report from this log once
it's public, and note the disclosure timeline in the "Disclosure status"
field above. See `SECURITY.md` for this repo's own policy on findings
reported against this project's code.
