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

# kind -> (rcs m^2, micro_doppler 0..1, default speed m/s, is_threat)
KINDS = {
    "quad":       (0.02, 0.85, 24.0, True),
    "fixed_wing": (0.15, 0.20, 38.0, True),
    "decoy_bird": (0.01, 0.05, 14.0, False),
}


@dataclass
class ThreatSpec:
    p0: np.ndarray
    speed: float
    rf_linked: bool
    kind: str = "quad"
    jitter: float = 1.4
    is_mothership: bool = False
    spawns_at_range: float = 0.0          # >0: releases children at this range

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


def _ring(n, radius, alt, rng, rf_linked, kind, spread_deg=360.0):
    out = []
    base = rng.uniform(0, 2 * np.pi)
    spd = KINDS[kind][2]
    for i in range(n):
        ang = base + np.deg2rad(spread_deg) * (i / max(n, 1))
        p0 = np.array([radius * np.cos(ang), radius * np.sin(ang),
                       alt + rng.uniform(-15, 15)])
        out.append(ThreatSpec(p0=p0, speed=spd, rf_linked=rf_linked, kind=kind))
    return out


def single_drone(seed: int = 0) -> Scenario:
    rng = np.random.default_rng(seed)
    return Scenario("single_drone", 60.0, 0.5,
                    _ring(1, 2500.0, 120.0, rng, True, "quad"),
                    "Baseline: one RF-controlled quad ingress.")


def coordinated_formation(seed: int = 0) -> Scenario:
    rng = np.random.default_rng(seed)
    return Scenario("coordinated_formation", 70.0, 0.5,
                    _ring(8, 3000.0, 140.0, rng, True, "quad", 35.0),
                    "8-ship coherent formation, single axis of attack.")


def _cluster(n, bearing_deg, radius, alt, rng, rf_linked, kind, tight=160.0):
    """A concentrated sub-swarm on one attack axis."""
    out = []
    b = np.deg2rad(bearing_deg)
    c = np.array([radius * np.cos(b), radius * np.sin(b), alt])
    spd = KINDS[kind][2]
    for _ in range(n):
        p0 = c + rng.normal(0, tight, 3) * np.array([1, 1, 0.15])
        out.append(ThreatSpec(p0=p0, speed=spd, rf_linked=rf_linked,
                               kind=kind))
    return out


def mixed_dark_saturation(seed: int = 0) -> Scenario:
    """Coordinated multi-axis raid: tight sub-swarms (HPM-relevant) from
    three bearings, RF-linked + RF-silent, plus bird decoys."""
    rng = np.random.default_rng(seed)
    th = []
    th += _cluster(12, 20.0, 3200.0, 130.0, rng, True, "quad")
    th += _cluster(10, 150.0, 3000.0, 100.0, rng, False, "fixed_wing")
    th += _cluster(8, 255.0, 2900.0, 120.0, rng, True, "quad")
    th += _ring(4, 2600.0, 110.0, rng, False, "decoy_bird")
    return Scenario("mixed_dark_saturation", 80.0, 0.5, th,
                    "30-threat 3-axis coordinated raid (RF + dark) "
                    "+ 4 bird decoys.")


def mothership_release(seed: int = 0) -> Scenario:
    """A slow 'mothership' that releases a child swarm at close range."""
    mom = ThreatSpec(p0=np.array([5200.0, 400.0, 240.0]), speed=34.0,
                     rf_linked=False, kind="fixed_wing", is_mothership=True,
                     spawns_at_range=3400.0)
    return Scenario("mothership_release", 90.0, 0.5, [mom],
                    "RF-silent mothership ingress then 10-child quad release.")


def thousand_swarm(seed: int = 0, n: int = 1000) -> Scenario:
    rng = np.random.default_rng(seed)
    th = []
    th += _ring(int(n * 0.7), 4000.0, 150.0, rng, True, "quad")
    th += _ring(int(n * 0.3), 3500.0, 80.0, rng, False, "fixed_wing")
    return Scenario(f"thousand_swarm_{n}", 60.0, 1.0, th,
                    f"{n}-drone mass raid for scaling validation.")


LIBRARY = {
    "single_drone": single_drone,
    "coordinated_formation": coordinated_formation,
    "mixed_dark_saturation": mixed_dark_saturation,
    "mothership_release": mothership_release,
    "thousand_swarm": thousand_swarm,
}
