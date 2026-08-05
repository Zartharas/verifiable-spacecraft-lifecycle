"""
Prohibited-configuration policy — S5 assurance mechanism.

Decision (Technical-Design-Document.md § 7/7d): a **custom, hand-rolled
policy check**, not OPA/Rego. Real OPA would mean fetching an external
binary release with no clean verification path from this sandbox (no
package manager entry, would require a raw binary download and trust
decision this project isn't positioned to make lightly). A small,
explicit Python policy table is sufficient to test the assurance
mechanism itself — "can a correctly-signed, otherwise-valid release still
be rejected for policy reasons?" — without pulling in unverified
infrastructure. Swap in OPA/Rego later if the project moves to a real
ground system; the check-shape here (deny-list of prohibited config
patterns) maps cleanly onto a Rego `deny` rule set if that migration
happens.

Covers attack matrix test case #8 (correct signature but prohibited
configuration).
"""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_store import EvidenceStore  # noqa: E402

# Test-only prohibited-configuration table. A real ground system would
# load this from a versioned, ground-approved policy document, not a
# hardcoded Python list.
PROHIBITED_CONFIGURATIONS = [
    {"debug_mode": True},  # debug builds must never be authorized for flight
]


# Second red-team pass, finding #10 (2026-08-05): representations that
# should all count as "the pattern's True" for a security-relevant
# boolean flag, since a caller-supplied config can plausibly arrive as
# JSON-decoded (real bool), a raw string, or a loosely-typed int, and a
# deny-rule that only catches one of those representations is trivially
# bypassed by using a different one for the exact same intent.
_TRUTHY_STRINGS = {"true", "1", "yes", "on"}


def _values_match(config_value, pattern_value) -> bool:
    """Equality check for one field, deliberately more permissive than
    `==` when the pattern's value is a bool — `{"debug_mode": True}` must
    also match `{"debug_mode": "true"}` / `1` / `"1"`, not just the
    exact Python `True` singleton. Python's `"true" == True` is `False`,
    so a bare `==` on the pattern above lets a config that means the same
    thing but is spelled differently sail past the only rule in the
    deny-list. Non-bool pattern values keep exact-equality semantics —
    this coercion is specifically about the boolean-flag case, not a
    general fuzzy-match policy engine.

    Fourth independent (blind, AI) red-team pass, finding P4-V
    (2026-08-06): a boolean intent wrapped in a container —
    `{"debug_mode": [True]}` or `{"debug_mode": {"enabled": True}}` —
    fell through every branch above to the `return False` catch-all,
    meaning "wrap the same true value in a list or dict" was an
    unlimited bypass class of its own. Rather than hand-enumerate every
    container shape, fall back to Python's own truthiness: `bool(x)` is
    `False` only for the conventionally-empty/falsy values (`None`, `[]`,
    `{}`, `()`, `""`, `0`, `False`) and `True` for everything else,
    which matches the intent of a caller who nests the same flag one
    level deep. This is still scoped to boolean pattern values only."""
    if isinstance(pattern_value, bool):
        if isinstance(config_value, bool):
            return config_value == pattern_value
        if isinstance(config_value, str):
            return (config_value.strip().lower() in _TRUTHY_STRINGS) == pattern_value
        if isinstance(config_value, (int, float)):
            return bool(config_value) == pattern_value
        return bool(config_value) == pattern_value
    return config_value == pattern_value


def _fold_key(key) -> Optional[str]:
    """Canonical form of a config key for whitespace/case/Unicode-
    insensitive comparison against a pattern's field name.

    Fourth independent (blind, AI) red-team pass (2026-08-06), three
    related findings this addresses together:

    - P4-K (whitespace): the third pass's fix case-folded with `.lower()`
      but never stripped, so `{" debug_mode": True}` / `{"debug_mode ":
      True}` never matched `"debug_mode"` at all.
    - P4-U (Unicode): `.lower()` alone does not normalize width variants —
      `"Ｄebug_mode"` (fullwidth D, U+FF24) lower-cases to
      `"ｄebug_mode"` (still fullwidth), never to ASCII `"debug_mode"`.
      NFKC normalization *before* casefolding is required to fold
      fullwidth Latin back to its ASCII equivalent — confirmed by direct
      test before writing this fix, not assumed:
      `unicodedata.normalize("NFKC", "Ｄebug_mode").casefold() ==
      "debug_mode"` is `True`; `"Ｄebug_mode".casefold()` alone is not.
    - P4-N (non-string key crash): the third pass's fix called `k.lower()`
      unconditionally, so a non-string key (e.g. `{1: True}`) raised
      `AttributeError` with no `try`/`except` anywhere between
      `check_configuration` and `pipeline.run()` — a malformed config
      could crash the whole pipeline run instead of producing a clean
      fail-closed deny record. A non-string key can never equal a
      pattern's string field name under any reasonable definition of
      "the same key," so it is skipped (returns `None`) rather than
      raising."""
    if not isinstance(key, str):
        return None
    return unicodedata.normalize("NFKC", key.strip()).casefold()


def _matches(config: dict, pattern: dict) -> bool:
    """A config matches a prohibited pattern if every key/value in the
    pattern is present and equal in the config (a simple deny-rule
    semantics — real Rego would express this more richly).

    History: the third red-team pass fixed exact-case key lookup
    (`config.get(k)` never catching `{"DEBUG_MODE": True}` against a
    `"debug_mode"` rule) by building one case-folded dict up front and
    looking each pattern key up in that. The fourth pass showed that fix
    was too narrow in two ways, both fixed here:

    1. It case-folded with `.lower()` (see `_fold_key` above for why that
       misses whitespace and Unicode width variants).
    2. Building a single `{folded_key: value}` dict is fail-*open* on a
       key collision: if `config` contains two keys that fold to the
       same canonical form with different values — e.g. `{"debug_mode":
       True, "DEBUG_MODE": False}` — a plain dict comprehension keeps
       whichever key dict-iteration order visits last, so an attacker
       can shadow the prohibited value with a second, differently-cased,
       benign-valued key in the same request (fourth pass, finding
       P4-C). The prior fix's own docstring predicted this exact path
       and dismissed it as "a caller sending contradictory casings...
       is itself a malformed request" — true, but a malformed-looking
       request from an attacker's deliberate crafting is not the same
       thing as an accident, and a security deny-rule should not give
       an attacker a way to make its own bypass "look malformed." Fixed
       by checking *every* config key that folds to a given pattern key,
       not just one collapsed dict entry, and failing closed: if *any*
       of them has a matching value, the pattern key matches."""
    for pattern_key, pattern_value in pattern.items():
        folded_pattern_key = _fold_key(pattern_key)
        if folded_pattern_key is None:
            # Every entry in PROHIBITED_CONFIGURATIONS is authored in this
            # file with string keys; a None here would mean the pattern
            # itself is malformed, not the caller's config. Guard against
            # None == None ever matching a non-string config key by value
            # coincidence — no config key can legitimately match a
            # non-string pattern key.
            return False
        matched = False
        for config_key, config_value in config.items():
            if _fold_key(config_key) == folded_pattern_key and _values_match(config_value, pattern_value):
                matched = True
                break
        if not matched:
            return False
    return True


def check_configuration(
    config: dict, artifact_hash: str, condition_name: str = "S5"
) -> tuple[bool, Optional[str]]:
    store = EvidenceStore()

    for pattern in PROHIBITED_CONFIGURATIONS:
        if _matches(config, pattern):
            store.record(
                pipeline_stage="configuration_policy_check",
                condition=condition_name,
                artifact_ref=artifact_hash,
                actor="ground_authorization_service",
                result="fail",
                detail={"reason": "prohibited configuration", "matched_pattern": pattern, "config": config},
                test_case_injected="8",
            )
            return False, f"prohibited configuration: {pattern}"

    store.record(
        pipeline_stage="configuration_policy_check",
        condition=condition_name,
        artifact_ref=artifact_hash,
        actor="ground_authorization_service",
        result="pass",
        detail={"config": config},
    )
    return True, None
