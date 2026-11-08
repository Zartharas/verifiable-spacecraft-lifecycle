"""
Mutation robustness experiment (revision 1, reviewer 1).

The 15-case attack matrix uses injectors written by the same author as the
detectors. This harness removes that dependence for the *document* checks:
instead of hand-written attack cases it applies generic, systematic mutation
operators to valid artifacts and records what each verifier does.

Document types and verifiers under test
  sbom         sbom.verify_sbom(sbom, binary)              (S1)
  provenance   provenance.verify_provenance(binary, prov)  (S2)
  attestation  attestation.verify_attestation(att, binary) (S3)
  signature    signing.verify(binary, sig)                 (S0)
  policy       policy.check_configuration(config, hash)    (S5)

Mutation operators (document types that are JSON)
  bitflip      flip one random bit of the serialized bytes
  truncate     cut the serialized bytes at a random point
  delete       delete each key / list element in turn (systematic)
  retype       replace each leaf by a value of another type (systematic)
  change       change each leaf value (systematic)
  dupkey       insert a duplicate key with a different value (systematic)
  splice       replace each leaf by the same leaf from another valid artifact
  neutral      semantics-preserving rewrites (indent, key order, \\u-escapes)

Outcome classes
  rejected              verifier returned a clean rejection
  rejected_exception    verifier raised (fail closed, but unhandled)
  accepted_neutral      mutant parses to the same document, accepted
  accepted_semantic     mutant parses to a DIFFERENT document, accepted
  rejected_neutral      mutant parses to the same document, rejected (false reject)

`accepted_semantic` is the number that matters: a change to the document
that the verifier did not notice. It is broken down by changed JSON path so
that fields the verifier never reads (descriptive metadata) can be told
apart from fields whose change should have mattered.
"""

from __future__ import annotations

import copy
import hashlib
import json
import random
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from attestation.attestation import generate_attestation, verify_attestation  # noqa: E402
from policy.policy import check_configuration  # noqa: E402
from provenance.provenance import generate_provenance, verify_provenance  # noqa: E402
from sbom.sbom import generate_sbom, verify_sbom  # noqa: E402
from signing.signing import sign, verify  # noqa: E402

WORKDIR = REPO_ROOT / "work" / "mutation"
RESULTS = REPO_ROOT / "evaluation" / "results" / "phase10_mutation.json"
SEED = 20261028
N_BITFLIP = 400
N_TRUNCATE = 100
N_BIN_FLIP = 200


# ---------------------------------------------------------------- helpers
def _make_binary(name: str, seed: int) -> Path:
    WORKDIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    p = WORKDIR / name
    p.write_bytes(bytes(rng.getrandbits(8) for _ in range(4096)))
    return p


def _leaves(obj, path=()):
    """Yield (path, value) for every leaf and every container member."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield path + (k,), v
            yield from _leaves(v, path + (k,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield path + (i,), v
            yield from _leaves(v, path + (i,))


def _get(obj, path):
    for p in path:
        obj = obj[p]
    return obj


def _set(obj, path, value):
    parent = _get(obj, path[:-1]) if len(path) > 1 else obj
    parent[path[-1]] = value


def _delete(obj, path):
    parent = _get(obj, path[:-1]) if len(path) > 1 else obj
    del parent[path[-1]]


def _diff(a, b, path=()):
    """List of dotted paths at which two parsed JSON values differ."""
    if type(a) is not type(b):
        return [".".join(map(str, path)) or "<root>"]
    if isinstance(a, dict):
        out = []
        for k in set(a) | set(b):
            if k not in a or k not in b:
                out.append(".".join(map(str, path + (k,))))
            else:
                out += _diff(a[k], b[k], path + (k,))
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [".".join(map(str, path)) or "<root>"]
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += _diff(x, y, path + (i,))
        return out
    return [] if a == b else [".".join(map(str, path)) or "<root>"]


def _norm_path(p: str) -> str:
    # collapse list indices so equivalent positions group together
    return ".".join("[]" if s.isdigit() else s for s in p.split("."))


def _original_paths(original) -> set[str]:
    return {".".join(map(str, p)) for p, _ in _leaves(original)}


def _attribute(changed, original_paths):
    """Map each changed path to a path that exists in the ORIGINAL document.
    A path that does not exist there is a key that was renamed or added; it
    is reported once as '<unknown key under PARENT>' so random bit flips
    inside key names do not create hundreds of one-off rows."""
    out = set()
    for c in changed:
        if c in original_paths or c == "<root>":
            out.add(_norm_path(c))
        else:
            parent = c.rsplit(".", 1)[0] if "." in c else "<root>"
            out.add(f"<unknown key under {_norm_path(parent)}>")
    return out


_ALT_TYPES = [None, 0, 1, "x", "", True, False, [], {}, [1], {"a": 1}]


def _change_value(v):
    if isinstance(v, bool):
        return not v
    if isinstance(v, int):
        return v + 1
    if isinstance(v, float):
        return v + 1.0
    if isinstance(v, str):
        return v + "x" if len(v) < 3 or v[-1] != "x" else v[:-1] + "y"
    return None


# ------------------------------------------------- mutant generation (JSON)
def json_mutants(original: dict, donors: list[dict], rng: random.Random):
    """Yield (operator, mutated_bytes). Deterministic given rng."""
    base = json.dumps(original, indent=2).encode()

    for _ in range(N_BITFLIP):
        b = bytearray(base)
        i = rng.randrange(len(b))
        b[i] ^= 1 << rng.randrange(8)
        yield "bitflip", bytes(b)

    for _ in range(N_TRUNCATE):
        yield "truncate", base[: rng.randrange(len(base))]

    paths = [p for p, _ in _leaves(original)]
    for p in paths:
        d = copy.deepcopy(original)
        _delete(d, p)
        yield "delete", json.dumps(d, indent=2).encode()

    for p in paths:
        v = _get(original, p)
        for alt in _ALT_TYPES:
            if type(alt) is type(v) and alt == v:
                continue
            d = copy.deepcopy(original)
            _set(d, p, alt)
            yield "retype", json.dumps(d, indent=2).encode()

    for p in paths:
        v = _get(original, p)
        if isinstance(v, (dict, list)):
            continue
        d = copy.deepcopy(original)
        _set(d, p, _change_value(v))
        yield "change", json.dumps(d, indent=2).encode()

    # duplicate key: append a second definition of every dict key, last wins
    for p in paths:
        if isinstance(p[-1], int):
            continue
        parent_path = p[:-1]
        d = copy.deepcopy(original)
        parent = _get(d, parent_path) if parent_path else d
        if not isinstance(parent, dict):
            continue
        v = _get(original, p)
        alt = _change_value(v) if not isinstance(v, (dict, list)) else None
        text = json.dumps(d, indent=2)
        # textual duplicate: re-insert key with new value right after the
        # opening brace of its parent object (last definition wins in json)
        marker = json.dumps(p[-1]) + ":"
        pos = text.rfind(marker)
        if pos < 0:
            continue
        end = text.find("\n", pos)
        dup = f'{json.dumps(p[-1])}: {json.dumps(alt)},'
        yield "dupkey", (text[: end + 1] + dup + "\n" + text[end + 1 :]).encode()

    for donor in donors:
        for p in paths:
            try:
                dv = _get(donor, p)
            except (KeyError, IndexError, TypeError):
                continue
            if isinstance(dv, (dict, list)) or dv == _get(original, p):
                continue
            if isinstance(_get(original, p), (dict, list)):
                continue
            d = copy.deepcopy(original)
            _set(d, p, dv)
            yield "splice", json.dumps(d, indent=2).encode()

    # neutral controls
    yield "neutral", json.dumps(original, indent=4).encode()
    yield "neutral", json.dumps(original, separators=(",", ":")).encode()
    yield "neutral", json.dumps(original, sort_keys=True, indent=1).encode()
    yield "neutral", json.dumps(dict(reversed(list(original.items()))), indent=2).encode()
    yield "neutral", json.dumps(original, ensure_ascii=True, indent=2).replace("a", "\\u0061", 3).encode()
    yield "neutral", b"\xef\xbb\xbf"[:0] + b"\n\n" + base + b"\n\n"


# ---------------------------------------------------------- verifier runners
def _run(fn):
    try:
        return ("accept" if fn() else "reject"), None
    except Exception as e:  # noqa: BLE001 - classification is the point
        return "exception", type(e).__name__


def _classify(original, mutated_bytes):
    try:
        parsed = json.loads(mutated_bytes)
    except Exception:  # noqa: BLE001
        return "malformed", []
    changed = _diff(original, parsed)
    return ("same" if not changed else "different"), changed


def run_json_doc(name, original, donors, make_path, verifier, rng, equivalent=None):
    orig_paths = _original_paths(original)
    field_stats = defaultdict(lambda: [0, 0])  # path -> [mutants, accepted]
    counts = defaultdict(Counter)
    accepted_paths = defaultdict(Counter)  # operator -> normalized path -> n
    exc_types = Counter()
    false_reject_examples = []
    total = 0
    for op, data in json_mutants(original, donors, rng):
        path = make_path()
        path.write_bytes(data)
        verdict, exc = _run(lambda: verifier(path))
        sem, changed = _classify(original, data)
        total += 1
        if verdict == "exception":
            exc_types[exc] += 1
        if verdict == "reject":
            cls = "rejected" if sem != "same" else "rejected_neutral"
        elif verdict == "exception":
            cls = "rejected_exception" if sem != "same" else "rejected_neutral"
        else:  # accept
            if sem == "same":
                cls = "accepted_neutral"
            elif sem == "malformed":
                cls = "accepted_malformed"
            elif equivalent is not None and equivalent(original, json.loads(data)):
                cls = "accepted_equivalent"
            else:
                cls = "accepted_semantic"
                for c in _attribute(changed, orig_paths):
                    accepted_paths[op][c] += 1
        counts[op][cls] += 1
        if op in ("delete", "retype", "change", "splice", "dupkey") and sem == "different":
            for c in _attribute(changed, orig_paths):
                field_stats[c][0] += 1
                field_stats[c][1] += verdict == "accept"
        if cls == "rejected_neutral" and len(false_reject_examples) < 3:
            false_reject_examples.append({"operator": op, "exception": exc})
    return {
        "document": name,
        "total_mutants": total,
        "by_operator": {k: dict(v) for k, v in counts.items()},
        "accepted_semantic_paths": {k: dict(v) for k, v in accepted_paths.items()},
        "field_stats": {k: {"mutants": v[0], "accepted": v[1]} for k, v in sorted(field_stats.items())},
        "exception_types": dict(exc_types),
        "false_reject_examples": false_reject_examples,
    }


# ------------------------------------------------------------ binary mutants
def run_binary_and_signature(rng):
    b = _make_binary("mut_bin.elf", 1)
    sig = sign(b, condition_name="S0")
    good_sig = sig.read_bytes()
    out = {}

    # (a) binary mutations against signature, SBOM, provenance
    prov = generate_provenance(b, condition_name="S2")
    sbom = generate_sbom(b, condition_name="S1")
    orig = b.read_bytes()
    res = {"signature": Counter(), "sbom_binding": Counter(), "provenance_binding": Counter()}
    for i in range(N_BIN_FLIP):
        m = bytearray(orig)
        m[rng.randrange(len(m))] ^= 1 << rng.randrange(8)
        b.write_bytes(bytes(m))
        for key, fn in (
            ("signature", lambda: verify(b, sig)),
            ("sbom_binding", lambda: verify_sbom(sbom, b)),
            ("provenance_binding", lambda: verify_provenance(b, prov)[0]),
        ):
            v, _ = _run(fn)
            res[key][v] += 1
    for n in (1, 16, 4095):  # truncations and extension
        b.write_bytes(orig[:-n])
        res["signature"][_run(lambda: verify(b, sig))[0]] += 1
    b.write_bytes(orig + b"\x00")
    res["signature"][_run(lambda: verify(b, sig))[0]] += 1
    b.write_bytes(orig)
    out["binary_mutation"] = {k: dict(v) for k, v in res.items()}

    # (b) signature-file mutations
    c = Counter()
    for _ in range(N_BIN_FLIP):
        m = bytearray(good_sig)
        m[rng.randrange(len(m))] ^= 1 << rng.randrange(8)
        sig.write_bytes(bytes(m))
        c[_run(lambda: verify(b, sig))[0]] += 1
    for variant in (good_sig[:-1], good_sig + b"\x00", b"", good_sig[:32]):
        sig.write_bytes(variant)
        c[_run(lambda: verify(b, sig))[0]] += 1
    sig.write_bytes(good_sig)
    out["signature_file_mutation"] = dict(c)
    return out


# ------------------------------------------------------------ policy variants
_KEY_FORMS = {
    "exact": "debug_mode",
    "upper": "DEBUG_MODE",
    "title": "Debug_Mode",
    "lead_space": " debug_mode",
    "trail_space": "debug_mode ",
    "fullwidth": "Ｄebug_mode",
    "hyphen": "debug-mode",
    "camel": "debugMode",
    "dotted_prefix": "build.debug_mode",
    "zero_width": "debug​_mode",
    "cyrillic_e": "dеbug_mode",
    "double_underscore": "debug__mode",
    "plural": "debug_modes",
    "short": "debug",
}
_TRUE_FORMS = {
    "True": True,
    "'true'": "true",
    "'TRUE'": "TRUE",
    "1": 1,
    "'1'": "1",
    "1.0": 1.0,
    "'yes'": "yes",
    "'on'": "on",
    "'enabled'": "enabled",
    "'y'": "y",
    "'t'": "t",
    "'enable'": "enable",
    "[True]": [True],
    "{'enabled': True}": {"enabled": True},
    "'true '": "true ",
    "2": 2,
}
_FALSE_FORMS = {
    "False": False,
    "'false'": "false",
    "0": 0,
    "'0'": "0",
    "'no'": "no",
    "'off'": "off",
    "None": None,
    "[]": [],
    "{}": {},
    "[False]": [False],
    "{'enabled': False}": {"enabled": False},
    "'disabled'": "disabled",
    "''": "",
}


def run_policy():
    h = "0" * 64
    rows = []
    for kn, k in _KEY_FORMS.items():
        for vn, v in _TRUE_FORMS.items():
            ok, _ = check_configuration({k: v}, h)
            rows.append({"key": kn, "value": vn, "intent": "debug_on", "accepted": ok})
        for vn, v in _FALSE_FORMS.items():
            ok, _ = check_configuration({k: v}, h)
            rows.append({"key": kn, "value": vn, "intent": "debug_off", "accepted": ok})
    # nested containers around the whole flag
    for label, cfg in {
        "nested_dict": {"build": {"debug_mode": True}},
        "list_of_dicts": {"flags": [{"debug_mode": True}]},
        "json_string": {"config": '{"debug_mode": true}'},
        "second_key_shadow": {"debug_mode": True, "DEBUG_MODE": False},
    }.items():
        ok, _ = check_configuration(cfg, h)
        rows.append({"key": label, "value": "structure", "intent": "debug_on", "accepted": ok})

    on = [r for r in rows if r["intent"] == "debug_on"]
    off = [r for r in rows if r["intent"] == "debug_off"]
    # canonical = exact key only; others are "variants"
    summary = {
        "debug_on_total": len(on),
        "debug_on_accepted": sum(r["accepted"] for r in on),
        "debug_off_total": len(off),
        "debug_off_rejected": sum(not r["accepted"] for r in off),
    }
    return {
        "summary": summary,
        "accepted_debug_on": [(r["key"], r["value"]) for r in on if r["accepted"]],
        "rejected_debug_off": [(r["key"], r["value"]) for r in off if not r["accepted"]],
        "rows": rows,
    }


def _same_signature_bytes(orig: dict, mutant: dict) -> bool:
    """Attestation: the mutant differs from the original only in how the
    signature hex is spelled (case, whitespace), not in the signed quote or
    the decoded signature bytes."""
    try:
        return mutant["quote"] == orig["quote"] and bytes.fromhex(mutant["signature"]) == bytes.fromhex(
            orig["signature"]
        ) and set(mutant) == set(orig)
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------- main
def main():
    rng = random.Random(SEED)
    t0 = time.time()

    b1 = _make_binary("mut_a.elf", 11)
    b2 = _make_binary("mut_b.elf", 12)

    # SBOM
    sb1 = generate_sbom(b1, condition_name="S1")
    sb2 = generate_sbom(b2, condition_name="S1")
    sbom_orig = json.loads(sb1.read_text())
    sbom_donor = json.loads(sb2.read_text())
    sbom_tmp = WORKDIR / "mut.cdx.json"
    sbom_res = run_json_doc(
        "sbom", sbom_orig, [sbom_donor], lambda: sbom_tmp, lambda p: verify_sbom(p, b1), rng
    )

    # Provenance
    pv1 = generate_provenance(b1, condition_name="S2", version=1)
    pv1_text = json.loads(pv1.read_text())
    pv2 = generate_provenance(b2, condition_name="S2", version=2, builder_id="trusted-ci-runner-01")
    pv_donor = json.loads(pv2.read_text())
    pv1.write_text(json.dumps(pv1_text, indent=2))
    pv_tmp = WORKDIR / "mut.provenance.json"
    prov_res = run_json_doc(
        "provenance",
        pv1_text,
        [pv_donor],
        lambda: pv_tmp,
        lambda p: verify_provenance(b1, p)[0],
        rng,
    )

    # Attestation
    a1 = generate_attestation(b1, "mutA", condition_name="S3")
    a1_text = json.loads(a1.read_text())
    a2 = generate_attestation(b2, "mutB", condition_name="S3")
    a_donor = json.loads(a2.read_text())
    a_tmp = WORKDIR / "mut.attestation.json"
    att_res = run_json_doc(
        "attestation", a1_text, [a_donor], lambda: a_tmp, lambda p: verify_attestation(p, b1)[0], rng,
        equivalent=_same_signature_bytes,
    )

    bin_sig = run_binary_and_signature(rng)
    pol = run_policy()

    out = {
        "seed": SEED,
        "elapsed_seconds": round(time.time() - t0, 1),
        "parameters": {
            "bitflip": N_BITFLIP,
            "truncate": N_TRUNCATE,
            "binary_bitflip": N_BIN_FLIP,
        },
        "json_documents": [sbom_res, prov_res, att_res],
        "binary_and_signature": bin_sig,
        "policy": pol,
    }
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(out, indent=2))
    return out


def summarize(out) -> str:
    lines = []
    for d in out["json_documents"]:
        tot = Counter()
        for op, c in d["by_operator"].items():
            tot.update(c)
        lines.append(f"{d['document']}: {d['total_mutants']} mutants -> {dict(tot)}")
        lines.append(f"   exceptions: {d['exception_types']}")
        acc = defaultdict(int)
        for op, paths in d["accepted_semantic_paths"].items():
            for p, n in paths.items():
                acc[p] += n
        for p, n in sorted(acc.items(), key=lambda x: -x[1]):
            lines.append(f"   accepted-semantic path {p}: {n}")
    lines.append(f"binary/sig: {out['binary_and_signature']}")
    lines.append(f"policy: {out['policy']['summary']}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(summarize(main()))
