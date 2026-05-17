"""Distributed multi-site sensor mesh (PLAN.md §2.1/§2.2).

Geographically separated sites, each with its own physics:
- RADAR        : Cartesian, RCS+range Pd, range-dependent noise, clutter
- PASSIVE_RF   : bearing-only (az/el), RF-linked threats only -> needs the
                 multi-site mesh to triangulate (no range from one site)
- EO_IR        : short range, narrow, accurate, strong class evidence
- ACOUSTIC     : very short range, catches low/slow 'dark' contacts

`sense()` honours an `active` site mask so the engine can inject node loss
and demonstrate graceful degradation (a core resilience selling point).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..schemas import (Detection, GuidanceClass, MeasKind, ObjectClass,
                       SensorKind)
from .scenarios import Scenario, ThreatSpec


@dataclass
class SensorSite:
    site_id: str
    kind: SensorKind
    pos: np.ndarray
    max_range: float


def default_site_layout() -> list[SensorSite]:
    K = SensorKind
    return [
        SensorSite("radar-N", K.RADAR, np.array([0.0, 1200.0, 12.0]), 6500.0),
        SensorSite("radar-S", K.RADAR, np.array([0.0, -1200.0, 12.0]), 6500.0),
        SensorSite("rf-E", K.PASSIVE_RF, np.array([1600.0, 0.0, 25.0]), 7000.0),
        SensorSite("rf-W", K.PASSIVE_RF, np.array([-1600.0, 0.0, 25.0]), 7000.0),
        SensorSite("rf-N", K.PASSIVE_RF, np.array([0.0, 1600.0, 25.0]), 7000.0),
        SensorSite("eoir-0", K.EO_IR, np.array([0.0, 0.0, 30.0]), 2000.0),
        SensorSite("acou-0", K.ACOUSTIC, np.array([0.0, 0.0, 3.0]), 900.0),
    ]


class SimWorld:
    def __init__(self, scenario: Scenario, seed: int = 0):
        self.sc = scenario
        self.rng = np.random.default_rng(seed)
        self.t = 0.0
        self._init_state(scenario.threats)

    def _init_state(self, threats: list[ThreatSpec]) -> None:
        self.specs = list(threats)
        self.pos = np.array([t.p0.copy() for t in threats], dtype=float)
        self.vel = np.array([t.velocity_toward_origin() for t in threats],
                            dtype=float)
        self.rf = np.array([t.rf_linked for t in threats], dtype=bool)
        self.guid = [t.guidance for t in threats]
        self.jit = np.array([t.jitter for t in threats], dtype=float)
        self.rcs = np.array([t.rcs for t in threats], dtype=float)
        self.md = np.array([t.micro_doppler for t in threats], dtype=float)
        self.is_threat = np.array([t.is_threat for t in threats], dtype=bool)
        self.alive = np.ones(len(threats), dtype=bool)
        self.neutralized = np.zeros(len(threats), dtype=bool)
        self._spawned = np.zeros(len(threats), dtype=bool)

    @property
    def n(self) -> int:
        return len(self.specs)

    def neutralize(self, idx: int) -> bool:
        if 0 <= idx < self.n and self.alive[idx]:
            self.alive[idx] = False
            self.neutralized[idx] = True
            return True
        return False

    def _release_children(self, mom_idx: int) -> None:
        rng = self.rng
        p = self.pos[mom_idx]
        new = []
        for k in range(10):
            ang = 2 * np.pi * k / 10
            off = np.array([60 * np.cos(ang), 60 * np.sin(ang),
                            rng.uniform(-20, 20)])
            sp = ThreatSpec(p0=p + off, speed=26.0,
                            guidance=GuidanceClass.RF_REMOTE, kind="quad")
            new.append(sp)
        # append children to truth arrays
        self.specs += new
        self.pos = np.vstack([self.pos, [s.p0 for s in new]])
        cv = np.array([s.velocity_toward_origin() for s in new])
        self.vel = np.vstack([self.vel, cv])
        self.guid += [s.guidance for s in new]
        self.rf = np.concatenate([self.rf, np.ones(len(new), bool)])
        self.jit = np.concatenate([self.jit, [s.jitter for s in new]])
        self.rcs = np.concatenate([self.rcs, [s.rcs for s in new]])
        self.md = np.concatenate([self.md, [s.micro_doppler for s in new]])
        self.is_threat = np.concatenate([self.is_threat,
                                         np.ones(len(new), bool)])
        self.alive = np.concatenate([self.alive, np.ones(len(new), bool)])
        self.neutralized = np.concatenate([self.neutralized,
                                           np.zeros(len(new), bool)])
        self._spawned = np.concatenate([self._spawned,
                                        np.zeros(len(new), bool)])

    def step(self) -> None:
        dt = self.sc.dt
        if self.jit.size:
            self.vel += (self.rng.normal(0, 1.0, self.vel.shape)
                         * self.jit[:, None] * dt)
        self.pos += self.vel * dt
        self.t += dt
        for i, sp in enumerate(self.specs):
            if (sp.is_mothership and not self._spawned[i] and self.alive[i]
                    and np.linalg.norm(self.pos[i]) <= sp.spawns_at_range):
                self._spawned[i] = True
                self._release_children(i)

    def range_to_asset(self) -> np.ndarray:
        return np.linalg.norm(self.pos, axis=1)

    # ---- sensor physics ---------------------------------------------------
    def _radar(self, site, i, p, dets):
        rng = self.rng
        d = float(np.linalg.norm(p - site.pos))
        if d > site.max_range:
            return
        # Pd rises with RCS, falls with range^4-ish (clamped)
        snr = (self.rcs[i] + 0.01) / (d / 1500.0) ** 2
        pd = float(np.clip(0.45 + 0.6 * np.tanh(snr * 4.0), 0.4, 0.985))
        if rng.random() >= pd:
            return
        std = 5.0 + 0.0045 * d
        dets.append(Detection(
            t=self.t, sensor_id=site.site_id, sensor_kind=SensorKind.RADAR,
            meas_kind=MeasKind.CARTESIAN,
            site=tuple(site.pos),
            x=p[0] + rng.normal(0, std), y=p[1] + rng.normal(0, std),
            z=p[2] + rng.normal(0, std * 1.4), pos_std=std,
            micro_doppler=max(0.0, self.md[i] + rng.normal(0, 0.08)),
            rcs=max(1e-3, self.rcs[i] * rng.lognormal(0, 0.3)),
            class_hint=ObjectClass.UNKNOWN))

    def _passive_rf(self, site, i, p, dets):
        if not self.rf[i]:
            return
        rng = self.rng
        rel = p - site.pos
        d = float(np.linalg.norm(rel))
        if d > site.max_range or rng.random() >= 0.92:
            return
        ang = 0.9 / 57.3 + 0.02      # ~0.9 deg base + bias
        az = np.arctan2(rel[1], rel[0]) + rng.normal(0, ang)
        el = np.arctan2(rel[2], np.linalg.norm(rel[:2])) + rng.normal(0, ang)
        dets.append(Detection(
            t=self.t, sensor_id=site.site_id,
            sensor_kind=SensorKind.PASSIVE_RF, meas_kind=MeasKind.BEARING,
            site=tuple(site.pos), az=float(az), el=float(el),
            ang_std=ang, rf_linked=True,
            micro_doppler=max(0.0, self.md[i] + rng.normal(0, 0.06)),
            class_hint=ObjectClass.UAS))

    def _eoir(self, site, i, p, dets):
        rng = self.rng
        d = float(np.linalg.norm(p - site.pos))
        if d > site.max_range or rng.random() >= 0.88:
            return
        std = 3.0 + 0.0015 * d
        dets.append(Detection(
            t=self.t, sensor_id=site.site_id, sensor_kind=SensorKind.EO_IR,
            meas_kind=MeasKind.CARTESIAN, site=tuple(site.pos),
            x=p[0] + rng.normal(0, std), y=p[1] + rng.normal(0, std),
            z=p[2] + rng.normal(0, std), pos_std=std,
            micro_doppler=max(0.0, self.md[i] + rng.normal(0, 0.04)),
            rcs=max(1e-3, self.rcs[i] * rng.lognormal(0, 0.2)),
            class_hint=(ObjectClass.UAS if self.is_threat[i]
                        else ObjectClass.BIRD)))

    def _acoustic(self, site, i, p, dets):
        rng = self.rng
        d = float(np.linalg.norm(p - site.pos))
        if d > site.max_range or rng.random() >= 0.7:
            return
        std = 25.0 + 0.05 * d
        dets.append(Detection(
            t=self.t, sensor_id=site.site_id, sensor_kind=SensorKind.ACOUSTIC,
            meas_kind=MeasKind.CARTESIAN, site=tuple(site.pos),
            x=p[0] + rng.normal(0, std), y=p[1] + rng.normal(0, std),
            z=p[2] + rng.normal(0, std), pos_std=std,
            micro_doppler=max(0.0, self.md[i] + rng.normal(0, 0.1)),
            class_hint=ObjectClass.UNKNOWN))

    def sense(self, sites: list[SensorSite],
              active: set[str] | None = None) -> list[Detection]:
        dets: list[Detection] = []
        live = np.where(self.alive)[0]
        for site in sites:
            if active is not None and site.site_id not in active:
                continue
            for i in live:
                p = self.pos[i]
                if site.kind == SensorKind.RADAR:
                    self._radar(site, i, p, dets)
                elif site.kind == SensorKind.PASSIVE_RF:
                    self._passive_rf(site, i, p, dets)
                elif site.kind == SensorKind.EO_IR:
                    self._eoir(site, i, p, dets)
                elif site.kind == SensorKind.ACOUSTIC:
                    self._acoustic(site, i, p, dets)
            # radar clutter
            if site.kind == SensorKind.RADAR and (
                    active is None or site.site_id in active):
                for _ in range(self.rng.poisson(1.6)):
                    a = self.rng.uniform(0, 2 * np.pi)
                    r = self.rng.uniform(400, site.max_range)
                    dets.append(Detection(
                        t=self.t, sensor_id=site.site_id,
                        sensor_kind=SensorKind.RADAR,
                        meas_kind=MeasKind.CARTESIAN, site=tuple(site.pos),
                        x=site.pos[0] + r * np.cos(a),
                        y=site.pos[1] + r * np.sin(a),
                        z=self.rng.uniform(20, 320), pos_std=45.0,
                        micro_doppler=self.rng.uniform(0, 0.15),
                        rcs=self.rng.lognormal(-1, 0.6),
                        class_hint=ObjectClass.UNKNOWN))
        return dets
