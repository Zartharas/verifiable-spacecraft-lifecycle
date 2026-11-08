"""Tests for the hash-only baseline (evaluation/baselines/hash_only_baseline.py)."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from evaluation.baselines import hash_only_baseline as h  # noqa: E402


def test_only_in_transit_tamper_is_rejected():
    res = h.run_baseline(n_trials=5)
    rejected = {c for c, r in res.items()
                if r["applicable"] and not r["sensitivity_variant"] and r["caught_count"] == r["n_trials"]}
    assert rejected == {"6"}


def test_all_other_applicable_cases_pass_the_hash_check():
    res = h.run_baseline(n_trials=5)
    for c in ["1", "2", "3", "4", "5", "7", "8", "9"]:
        assert res[c]["caught_count"] == 0, c


def test_digest_rewrite_defeats_case_6():
    assert h.case_06b_digest_rewritten()["caught"] is False


def test_post_install_cases_are_out_of_scope_not_scored():
    res = h.run_baseline(n_trials=2)
    for c in ["10", "11", "12", "13", "14", "15"]:
        assert res[c]["applicable"] is False


def test_hash_check_is_correct_on_genuine_artifact():
    host = h.ReleaseHost()
    data = h._fresh_firmware()
    host.upload("fw.bin", data)
    received, digest = host.fetch("fw.bin")
    assert h.hash_only_deploy(received, digest) is True
