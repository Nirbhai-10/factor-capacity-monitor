"""Threat Library v0 — synthetic adversary swarm scenarios.

DEFENSIVE VALIDATION ONLY. These describe drone *behaviors* against our own
simulated defended asset at the origin. No real targets. See SAFETY.md.

Target kinds carry distinct signatures so the classifier has real structure to
learn: small quads (low RCS, strong rotor micro-Doppler), fixed-wing OWA-style
(higher RCS, weak micro-Doppler), and decoys (bird-like, should NOT engage).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..schemas import GuidanceClass

# kind -> (rcs m^2, micro_doppler 0..1, default speed m/s, is_threat)
KINDS = {
    "quad":       (0.02, 0.85, 24.0, True),
    "fixed_wing": (0.15, 0.20, 38.0, True),
    "decoy_bird": (0.01, 0.05, 14.0, False),
}

# only RF-emitting generations are visible to the passive-RF mesh
_RF_EMITTING = (GuidanceClass.RF_REMOTE, GuidanceClass.GNSS_AIDED)


@dataclass
class ThreatSpec:
    p0: np.ndarray
    speed: float
    guidance: GuidanceClass = GuidanceClass.RF_REMOTE
    kind: str = "quad"
    jitter: float = 1.4
    is_mothership: bool = False
    spawns_at_range: float = 0.0          # >0: releases children at this range

    @property
    def rf_linked(self) -> bool:
        return self.guidance in _RF_EMITTING

    @property
    def rcs(self) -> float:
        return KINDS[self.kind][0]

    @property
    def micro_doppler(self) -> float:
        return KINDS[self.kind][1]

    @property
    def is_threat(self) -> bool:
        return KINDS[self.kind][3]

    def velocity_toward_origin(self) -> np.ndarray:
        d = -self.p0
        n = np.linalg.norm(d)
        return self.speed * d / n if n > 1e-6 else np.zeros(3)


@dataclass
class Scenario:
    name: str
    duration_s: float
    dt: float
    threats: list[ThreatSpec]
    description: str = ""

    @property
    def n_threats(self) -> int:
        return len(self.threats)


G = GuidanceClass


def _ring(n, radius, alt, rng, guidance, kind, spread_deg=360.0):
    out = []
    base = rng.uniform(0, 2 * np.pi)
    spd = KINDS[kind][2]
    for i in range(n):
        ang = base + np.deg2rad(spread_deg) * (i / max(n, 1))
        p0 = np.array([radius * np.cos(ang), radius * np.sin(ang),
                       alt + rng.uniform(-15, 15)])
        out.append(ThreatSpec(p0=p0, speed=spd, guidance=guidance, kind=kind))
    return out


def _cluster(n, bearing_deg, radius, alt, rng, guidance, kind, tight=160.0):
    """A concentrated sub-swarm on one attack axis."""
    out = []
    b = np.deg2rad(bearing_deg)
    c = np.array([radius * np.cos(b), radius * np.sin(b), alt])
    spd = KINDS[kind][2]
    for _ in range(n):
        p0 = c + rng.normal(0, tight, 3) * np.array([1, 1, 0.15])
        out.append(ThreatSpec(p0=p0, speed=spd, guidance=guidance, kind=kind))
    return out


def single_drone(seed: int = 0) -> Scenario:
    rng = np.random.default_rng(seed)
    return Scenario("single_drone", 60.0, 0.5,
                    _ring(1, 2500.0, 120.0, rng, G.RF_REMOTE, "quad"),
                    "Baseline: one RF-controlled quad ingress.")


def coordinated_formation(seed: int = 0) -> Scenario:
    rng = np.random.default_rng(seed)
    return Scenario("coordinated_formation", 70.0, 0.5,
                    _ring(8, 3000.0, 140.0, rng, G.RF_REMOTE, "quad", 35.0),
                    "8-ship coherent formation, single axis of attack.")


def mixed_dark_saturation(seed: int = 0) -> Scenario:
    """3-axis raid mixing RF-remote, GNSS-aided and RF-silent autonomous
    sub-swarms (the contingent older RF/GNSS EW cannot defeat) + decoys."""
    rng = np.random.default_rng(seed)
    th = []
    th += _cluster(12, 20.0, 3200.0, 130.0, rng, G.RF_REMOTE, "quad")
    th += _cluster(10, 150.0, 3000.0, 100.0, rng, G.AUTONOMOUS, "fixed_wing")
    th += _cluster(8, 255.0, 2900.0, 120.0, rng, G.GNSS_AIDED, "quad")
    th += _ring(4, 2600.0, 110.0, rng, G.RF_REMOTE, "decoy_bird")
    return Scenario("mixed_dark_saturation", 80.0, 0.5, th,
                    "30-threat 3-axis raid: RF-remote + GNSS-aided + "
                    "RF-silent autonomous + 4 bird decoys.")


def layered_raid(seed: int = 0) -> Scenario:
    """Flagship: ~90-drone saturation across all three autonomy
    generations, ~40% RF-silent autonomous (immune to RF/GNSS EW) — the
    case a single-layer defence fails and the layered framework must
    escalate to HPM/laser/net/counter-autonomy."""
    rng = np.random.default_rng(seed)
    th = []
    th += _cluster(26, 25.0, 3600.0, 140.0, rng, G.RF_REMOTE, "quad", 220.0)
    th += _cluster(20, 130.0, 3400.0, 110.0, rng, G.GNSS_AIDED, "quad", 220.0)
    th += _cluster(24, 235.0, 3300.0, 120.0, rng, G.AUTONOMOUS,
                   "fixed_wing", 240.0)
    th += _cluster(12, 310.0, 3000.0, 90.0, rng, G.AUTONOMOUS, "quad", 200.0)
    th += _ring(6, 2700.0, 110.0, rng, G.RF_REMOTE, "decoy_bird")
    return Scenario("layered_raid", 95.0, 0.5, th,
                    "~88-threat multi-generation saturation raid "
                    "(40% RF-silent autonomous) + 6 decoys.")


def mothership_release(seed: int = 0) -> Scenario:
    """A slow autonomous 'mothership' releasing a child swarm at range."""
    mom = ThreatSpec(p0=np.array([5200.0, 400.0, 240.0]), speed=34.0,
                     guidance=G.AUTONOMOUS, kind="fixed_wing",
                     is_mothership=True, spawns_at_range=3400.0)
    return Scenario("mothership_release", 90.0, 0.5, [mom],
                    "RF-silent autonomous mothership then 10-child release.")


def thousand_swarm(seed: int = 0, n: int = 1000) -> Scenario:
    rng = np.random.default_rng(seed)
    th = []
    th += _ring(int(n * 0.55), 4000.0, 150.0, rng, G.RF_REMOTE, "quad")
    th += _ring(int(n * 0.20), 3700.0, 120.0, rng, G.GNSS_AIDED, "quad")
    th += _ring(int(n * 0.25), 3500.0, 80.0, rng, G.AUTONOMOUS, "fixed_wing")
    return Scenario(f"thousand_swarm_{n}", 60.0, 1.0, th,
                    f"{n}-drone multi-generation mass raid (scaling).")


LIBRARY = {
    "single_drone": single_drone,
    "coordinated_formation": coordinated_formation,
    "mixed_dark_saturation": mixed_dark_saturation,
    "layered_raid": layered_raid,
    "mothership_release": mothership_release,
    "thousand_swarm": thousand_swarm,
}
