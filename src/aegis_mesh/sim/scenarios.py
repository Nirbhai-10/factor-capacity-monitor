"""Threat Library v0 — synthetic adversary swarm scenarios.

DEFENSIVE VALIDATION ONLY. These describe drone *behaviors* against our own
simulated defended asset at the origin. No real targets. See SAFETY.md.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ThreatSpec:
    """One synthetic threat: straight-ish ingress toward the asset (origin)."""

    p0: np.ndarray                 # start position ENU (m)
    speed: float                   # m/s
    rf_linked: bool                # False = "dark"/fiber-optic-like profile
    jitter: float = 1.5            # m/s random-walk on velocity (autonomy wobble)

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


def _ring(n: int, radius: float, alt: float, rng: np.random.Generator,
          rf_linked: bool, speed: float, spread_deg: float = 360.0) -> list[ThreatSpec]:
    out = []
    base = rng.uniform(0, 2 * np.pi)
    for i in range(n):
        ang = base + np.deg2rad(spread_deg) * (i / max(n, 1))
        p0 = np.array([radius * np.cos(ang), radius * np.sin(ang),
                       alt + rng.uniform(-15, 15)])
        out.append(ThreatSpec(p0=p0, speed=speed, rf_linked=rf_linked))
    return out


def single_drone(seed: int = 0) -> Scenario:
    rng = np.random.default_rng(seed)
    return Scenario(
        name="single_drone",
        duration_s=60.0,
        dt=0.5,
        threats=_ring(1, 2500.0, 120.0, rng, rf_linked=True, speed=22.0),
        description="Baseline: one RF-controlled quad ingress.",
    )


def coordinated_formation(seed: int = 0) -> Scenario:
    rng = np.random.default_rng(seed)
    return Scenario(
        name="coordinated_formation",
        duration_s=70.0,
        dt=0.5,
        threats=_ring(8, 3000.0, 140.0, rng, rf_linked=True, speed=24.0,
                      spread_deg=35.0),
        description="8-ship coherent formation, single axis of attack.",
    )


def mixed_dark_saturation(seed: int = 0) -> Scenario:
    """Saturation: many drones, mix of RF-linked and 'dark' (no RF) profiles
    arriving from multiple bearings — stresses fusion + WTA economics."""
    rng = np.random.default_rng(seed)
    threats: list[ThreatSpec] = []
    threats += _ring(18, 3200.0, 130.0, rng, rf_linked=True, speed=26.0)
    threats += _ring(12, 2800.0, 90.0, rng, rf_linked=False, speed=30.0)
    return Scenario(
        name="mixed_dark_saturation",
        duration_s=80.0,
        dt=0.5,
        threats=threats,
        description="30-drone saturation, 40% 'dark' (RF-silent) profiles.",
    )


def thousand_swarm(seed: int = 0, n: int = 1000) -> Scenario:
    """Scale stress: large coordinated swarm for WTA / fusion scaling tests."""
    rng = np.random.default_rng(seed)
    threats: list[ThreatSpec] = []
    threats += _ring(int(n * 0.7), 4000.0, 150.0, rng, rf_linked=True, speed=25.0)
    threats += _ring(int(n * 0.3), 3500.0, 80.0, rng, rf_linked=False, speed=28.0)
    return Scenario(
        name=f"thousand_swarm_{n}",
        duration_s=60.0,
        dt=1.0,
        threats=threats,
        description=f"{n}-drone mass raid for scaling validation.",
    )


LIBRARY = {
    "single_drone": single_drone,
    "coordinated_formation": coordinated_formation,
    "mixed_dark_saturation": mixed_dark_saturation,
    "thousand_swarm": thousand_swarm,
}
