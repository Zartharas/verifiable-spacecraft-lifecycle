"""Regression tests for fixes made after the mutation experiment
(evaluation/mutation_attacks.py, revision 1): malformed documents must be
rejected cleanly (no exception), and the policy value vocabulary must treat
equivalent spellings alike."""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "evaluation"))

import mutation_attacks as ma  # noqa: E402
from attestation.attestation import generate_attestation, verify_attestation  # noqa: E402
from policy.policy import check_configuration  # noqa: E402
from provenance.provenance import generate_provenance, verify_provenance  # noqa: E402
from sbom.sbom import generate_sbom, verify_sbom  # noqa: E402

H = "0" * 64
BAD_DOCS = [b"", b"\xff\xfe\x00", b"{", b"[]", b"null", b'{"a": 1}', b'{"components": 5}', b'{"quote": 1, "signature": 2}']


@pytest.fixture(scope="module")
def artifacts():
    b = ma._make_binary("test_mut.elf", 99)
    return b, generate_sbom(b), generate_provenance(b), generate_attestation(b, "testmut")


@pytest.mark.parametrize("doc", BAD_DOCS)
def test_malformed_documents_rejected_without_exception(artifacts, doc):
    b, sbom, prov, att = artifacts
    originals = {p: p.read_bytes() for p in (sbom, prov, att)}
    try:
        for p in (sbom, prov, att):
            p.write_bytes(doc)
        assert verify_sbom(sbom, b) is False
        assert verify_provenance(b, prov)[0] is False
        assert verify_attestation(att, b)[0] is False
    finally:
        for p, data in originals.items():
            p.write_bytes(data)


def test_neutral_rewrites_still_accepted(artifacts):
    b, sbom, prov, att = artifacts
    for path, verifier in (
        (sbom, lambda p: verify_sbom(p, b)),
        (prov, lambda p: verify_provenance(b, p)[0]),
        (att, lambda p: verify_attestation(p, b)[0]),
    ):
        original = path.read_text()
        try:
            doc = json.loads(original)
            path.write_text(json.dumps(doc, separators=(",", ":")))
            assert verifier(path) is True
        finally:
            path.write_text(original)


@pytest.mark.parametrize("value", [True, "true", "TRUE", 1, "1", "yes", "on", "y", "t", "enabled", "enable", [True], {"enabled": True}])
def test_debug_on_spellings_rejected(value):
    assert check_configuration({"debug_mode": value}, H)[0] is False


@pytest.mark.parametrize("value", [False, "false", 0, "0", "no", "off", None, [], {}, [False], {"enabled": False}, "disabled"])
def test_debug_off_spellings_accepted(value):
    assert check_configuration({"debug_mode": value}, H)[0] is True


def test_unrecognized_string_fails_closed():
    assert check_configuration({"debug_mode": "maybe"}, H)[0] is False


def test_attestation_field_mutations_all_rejected(artifacts):
    b, _, _, att = artifacts
    original = att.read_text()
    doc = json.loads(original)
    try:
        for field in ("measured_binary", "measured_hash", "partition_id", "timestamp"):
            d = json.loads(original)
            d["quote"][field] = "x" if field != "timestamp" else d["quote"][field] + 1
            att.write_text(json.dumps(d))
            assert verify_attestation(att, b)[0] is False, field
    finally:
        att.write_text(original)


def test_uptane_analysis_covers_all_fifteen_cases():
    sys.path.insert(0, str(REPO_ROOT / "evaluation" / "baselines"))
    import uptane_spec_analysis as ua

    out = ua.build()
    assert sorted(out["cases"], key=int) == [str(i) for i in range(1, 16)]
    assert out["executed"] is False
    assert sum(out["counts"].values()) == 15
