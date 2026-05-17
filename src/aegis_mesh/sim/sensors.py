"""Synthetic multi-sensor model: noisy detections, missed detections, clutter.

Models the design rule from PLAN.md §2.1: no single sensor is load-bearing.
- radar: 3D position, range-dependent noise, Pd<1, clutter false alarms
- passive_rf: present only for RF-linked threats; carries rf_linked=True
- eo_ir: only inside range/cone; gives a strong class hint
Truth propagation is simple Euler integration with autonomy 'wobble'.
"""

from __future__ import annotations

import numpy as np

from ..schemas import Detection, ObjectClass, SensorKind
from .scenarios import Scenario


class SimWorld:
    def __init__(self, scenario: Scenario, seed: int = 0):
        self.sc = scenario
        self.rng = np.random.default_rng(seed)
        self.t = 0.0
        self.pos = np.array([th.p0.copy() for th in scenario.threats], dtype=float)
        self.vel = np.array([th.velocity_toward_origin() for th in scenario.threats],
                            dtype=float)
        self.rf = np.array([th.rf_linked for th in scenario.threats], dtype=bool)
        self.jit = np.array([th.jitter for th in scenario.threats], dtype=float)
        self.alive = np.ones(len(scenario.threats), dtype=bool)
        self.neutralized = np.zeros(len(scenario.threats), dtype=bool)

    @property
    def n(self) -> int:
        return len(self.sc.threats)

    def neutralize(self, idx: int) -> None:
        if 0 <= idx < self.n and self.alive[idx]:
            self.alive[idx] = False
            self.neutralized[idx] = True

    def step(self) -> None:
        dt = self.sc.dt
        if self.jit.size:
            wob = self.rng.normal(0, 1.0, self.vel.shape) * self.jit[:, None] * dt
            self.vel += wob
        self.pos += self.vel * dt
        self.t += dt

    def range_to_asset(self) -> np.ndarray:
        return np.linalg.norm(self.pos, axis=1)

    def sense(self) -> list[Detection]:
        """One sensing cycle across the (modeled) site sensor mesh."""
        dets: list[Detection] = []
        live = np.where(self.alive)[0]
        rng = self.rng
        for i in live:
            p = self.pos[i]
            rng_m = float(np.linalg.norm(p))

            # --- radar: Pd falls with range; range-dependent noise ---
            pd = float(np.clip(1.05 - rng_m / 6000.0, 0.55, 0.97))
            if rng.random() < pd:
                std = 6.0 + 0.004 * rng_m
                dets.append(Detection(
                    t=self.t, sensor_id="radar-0", sensor_kind=SensorKind.RADAR,
                    x=p[0] + rng.normal(0, std), y=p[1] + rng.normal(0, std),
                    z=p[2] + rng.normal(0, std * 1.4), pos_std=std,
                    class_hint=ObjectClass.UNKNOWN))

            # --- passive RF: only RF-linked threats; coarse position ---
            if self.rf[i] and rng.random() < 0.9:
                std = 35.0 + 0.02 * rng_m
                dets.append(Detection(
                    t=self.t, sensor_id="rf-0", sensor_kind=SensorKind.PASSIVE_RF,
                    x=p[0] + rng.normal(0, std), y=p[1] + rng.normal(0, std),
                    z=p[2] + rng.normal(0, std), pos_std=std, rf_linked=True,
                    class_hint=ObjectClass.UAS))

            # --- EO/IR: short range, strong class, catches 'dark' threats ---
            if rng_m < 1800.0 and rng.random() < 0.85:
                std = 4.0 + 0.002 * rng_m
                dets.append(Detection(
                    t=self.t, sensor_id="eoir-0", sensor_kind=SensorKind.EO_IR,
                    x=p[0] + rng.normal(0, std), y=p[1] + rng.normal(0, std),
                    z=p[2] + rng.normal(0, std), pos_std=std,
                    class_hint=ObjectClass.UAS))

        # --- radar clutter / false alarms (birds, multipath) ---
        n_fa = rng.poisson(2.0)
        for _ in range(n_fa):
            ang = rng.uniform(0, 2 * np.pi)
            r = rng.uniform(400, 5000)
            dets.append(Detection(
                t=self.t, sensor_id="radar-0", sensor_kind=SensorKind.RADAR,
                x=r * np.cos(ang), y=r * np.sin(ang), z=rng.uniform(20, 300),
                pos_std=40.0, class_hint=ObjectClass.UNKNOWN))
        return dets
