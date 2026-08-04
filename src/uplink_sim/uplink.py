"""
Simulated uplink v2 — pass-through transport with a tamper injection hook
(test case #6) plus a configurable, CCSDS-informed link profile
(latency, bandwidth ceiling, loss probability).

Still NOT an RF-accurate simulation — see PRD.md non-goals and
Pipeline-Flow-Document.md § 3.7. The link profile models transit time and
a simple loss/corruption probability so later phases can measure how
detection/recovery metrics vary under degraded-link conditions, which is
the actual spacecraft-relevant constraint this project cares about (not
RF physics).

Reference values loosely informed by CCSDS-class deep-space/LEO link
budgets (order-of-magnitude, not a specific mission): LEO_TYPICAL has
sub-second latency and decent bandwidth; DEEP_SPACE_TYPICAL has multi-
minute one-way latency and low bandwidth, reflecting real deep-space
comms constraints.
"""

from __future__ import annotations

import dataclasses
import hashlib
import random
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_store import EvidenceStore  # noqa: E402

RECEIVED_DIR = REPO_ROOT / "work" / "spacecraft_received"


@dataclasses.dataclass(frozen=True)
class LinkProfile:
    name: str
    latency_seconds: float
    bandwidth_bps: float
    loss_probability: float  # 0.0-1.0, chance a transmission is corrupted in transit


# Order-of-magnitude reference profiles, not tied to a specific mission.
LEO_TYPICAL = LinkProfile(name="LEO_TYPICAL", latency_seconds=0.05, bandwidth_bps=1_000_000, loss_probability=0.001)
DEEP_SPACE_TYPICAL = LinkProfile(
    name="DEEP_SPACE_TYPICAL", latency_seconds=600.0, bandwidth_bps=8_000, loss_probability=0.01
)
IDEAL = LinkProfile(name="IDEAL", latency_seconds=0.0, bandwidth_bps=float("inf"), loss_probability=0.0)


def transmit(
    binary_path: Path,
    sig_path: Path,
    condition_name: str = "S0",
    tamper: bool = False,
    link_profile: LinkProfile = IDEAL,
    rng_seed: Optional[int] = None,
) -> tuple[Path, Path]:
    """
    Simulate transmission of a signed release bundle over the uplink.

    If tamper=True, flips a byte in the transmitted binary to simulate
    test case #6 (deterministic — always corrupts). Independently,
    link_profile.loss_probability can also cause a random in-transit
    corruption, modeling a lossy link rather than an attacker; both use
    the same underlying corruption mechanism but are logged with
    different detail so the evidence trail distinguishes "attack" from
    "link noise."

    rng_seed: pass an explicit seed for reproducible tests; None uses a
    fresh, non-deterministic random source (appropriate for anything
    other than a test).
    """
    store = EvidenceStore()

    RECEIVED_DIR.mkdir(parents=True, exist_ok=True)
    data = bytearray(binary_path.read_bytes())
    original_hash = hashlib.sha256(bytes(data)).hexdigest()

    payload_bits = len(data) * 8
    transit_seconds = link_profile.latency_seconds + (
        payload_bits / link_profile.bandwidth_bps if link_profile.bandwidth_bps not in (0, float("inf")) else 0.0
    )

    rng = random.Random(rng_seed)
    link_noise_corruption = rng.random() < link_profile.loss_probability

    # Second red-team pass, finding #12 (2026-08-05): this used to always
    # flip the exact midpoint byte, meaning "modified in transit" (test
    # case #6) was only ever exercised as one specific single-byte-flip
    # location across the entire test suite. Whole-artifact signature
    # verification is location-agnostic so this was never a detection
    # gap, but it's needlessly narrow coverage — pick a pseudo-random
    # offset (from the same seeded `rng`, so `rng_seed` still makes a
    # test fully reproducible) instead of a fixed one.
    if tamper or link_noise_corruption:
        offset = rng.randrange(len(data)) if len(data) > 0 else 0
        data[offset] ^= 0xFF

    received_binary = RECEIVED_DIR / binary_path.name
    received_sig = RECEIVED_DIR / sig_path.name
    received_binary.write_bytes(bytes(data))
    received_sig.write_bytes(sig_path.read_bytes())

    received_hash = hashlib.sha256(bytes(data)).hexdigest()

    store.record(
        pipeline_stage="uplink",
        condition=condition_name,
        artifact_ref=original_hash,
        actor="uplink_simulator",
        result="n/a",  # transit itself has no pass/fail — verification does
        detail={
            "tampered_in_transit": tamper,
            "link_noise_corruption": link_noise_corruption,
            "link_profile": link_profile.name,
            "simulated_transit_seconds": round(transit_seconds, 6),
            "hash_before_transmission": original_hash,
            "hash_after_transmission": received_hash,
        },
        test_case_injected="6" if tamper else None,
    )

    return received_binary, received_sig
