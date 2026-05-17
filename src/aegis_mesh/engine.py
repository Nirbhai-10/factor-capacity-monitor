"""Engine — the closed sense -> fuse -> sensemake -> decide -> effect -> audit
loop, emitting replay/stream frames and the PLAN.md §10 regression metrics.

Effects are simulated and authority-gated (SAFETY.md / wta.py). Supports
sensor-node-loss injection to demonstrate graceful degradation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from .fusion.gmphd import GMPHDTracker
from .fusion.tracker import Tracker
from .mesh import EventBus
from .orchestrator.audit import AuditLog
from .orchestrator.wta import EngagementManager
from .schemas import EngagementState, ObjectClass, TrackStatus, jsonable
from .sensemaking.swarm_intent import estimate_swarms
from .sim.scenarios import Scenario
from .sim.sensors import SimWorld, default_site_layout


@dataclass
class Metrics:
    scenario: str = ""
    t: float = 0.0
    n_threats: int = 0
    n_neutralized: int = 0
    n_leaked: int = 0
    leakage_rate: float = 0.0
    detection_recall: float = 0.0
    uas_precision: float = 0.0
    mean_cycle_latency_ms: float = 0.0
    committed_cost: float = 0.0
    sim_cost_per_kill: float = 0.0
    active_sites: int = 0
    audit_ok: bool = True
    audit_records: int = 0

    def summary(self) -> str:
        return (f"[{self.scenario}] threats={self.n_threats} "
                f"neutralized={self.n_neutralized} leaked={self.n_leaked} "
                f"leakage={self.leakage_rate:.1%} recall={self.detection_recall:.1%} "
                f"uas_prec={self.uas_precision:.1%} "
                f"lat={self.mean_cycle_latency_ms:.1f}ms "
                f"$/kill={self.sim_cost_per_kill:,.0f} "
                f"sites={self.active_sites} "
                f"audit={'OK' if self.audit_ok else 'BROKEN'}")


class Engine:
    def __init__(self, scenario: Scenario, *, seed: int = 0,
                 mitigation_authorized: bool = True, require_human: bool = False,
                 node_loss: dict[float, str] | None = None,
                 bus: EventBus | None = None, assoc_m: float = 200.0,
                 leak_radius_m: float = 250.0, tracker: str = "gmphd"):
        self.sc = scenario
        self.rng = np.random.default_rng(seed + 101)
        self.world = SimWorld(scenario, seed=seed)
        self.sites = default_site_layout()
        self.tracker_kind = tracker
        self.tracker = GMPHDTracker() if tracker == "gmphd" else Tracker()
        self.audit = AuditLog()
        self.mgr = EngagementManager(
            mitigation_authorized=mitigation_authorized,
            require_human=require_human, audit=self.audit)
        self.bus = bus or EventBus()
        self.assoc_m = assoc_m
        self.leak_radius_m = leak_radius_m
        self.node_loss = node_loss or {}
        self._active = {s.site_id for s in self.sites}
        self.audit.append(0.0, "policy", {
            "scenario": scenario.name,
            "mitigation_authorized": mitigation_authorized,
            "require_human": require_human})
        self.m = Metrics(scenario=scenario.name)
        self._ever = None
        self._lat: list[float] = []
        self._uas_tp = self._uas_fp = 0
        self._step = 0
        self.steps = int(scenario.duration_s / scenario.dt)
        self.done = False

    # --------------------------------------------------------------------- #
    def _apply_node_loss(self):
        for ts, sid in self.node_loss.items():
            if abs(self.world.t - ts) < self.sc.dt / 2 and sid in self._active:
                self._active.discard(sid)
                self.audit.append(self.world.t, "mesh",
                                  {"event": "node_loss", "site": sid})

    def step(self) -> dict:
        if self._ever is None:
            self._ever = np.zeros(self.world.n, bool)
        self.world.step()
        self._apply_node_loss()
        # grow recall mask if mothership spawned children
        if self.world.n > len(self._ever):
            self._ever = np.concatenate(
                [self._ever, np.zeros(self.world.n - len(self._ever), bool)])

        truth = self.world.pos.copy()
        alive = self.world.alive.copy()

        t0 = time.perf_counter()
        dets = self.world.sense(self.sites, self._active)
        self.bus.publish("detections", dets)
        tracks = self.tracker.step(dets, self.world.t, self.sc.dt)
        self.bus.publish("tracks", tracks)
        swarms = estimate_swarms(tracks, self.world.t)
        self.bus.publish("swarms", swarms)
        wta = self.mgr.propose(swarms, tracks, self.world.t)
        resolved = self.mgr.resolve_due(self.world.t, self.rng)
        self._lat.append((time.perf_counter() - t0) * 1000.0)
        self.bus.publish("orders", wta.orders)

        # recall + classification precision bookkeeping
        for tr in tracks:
            if not tr.confirmed:
                continue
            d = np.linalg.norm(truth - [tr.x, tr.y, tr.z], axis=1)
            j = int(np.argmin(d)) if self.world.n else -1
            if j >= 0 and d[j] <= self.assoc_m and alive[j]:
                self._ever[j] = True
                if tr.obj_class == ObjectClass.UAS:
                    if self.world.is_threat[j]:
                        self._uas_tp += 1
                    else:
                        self._uas_fp += 1

        # apply authority-gated, resolved effects to truth
        tby = {x.track_id: x for x in tracks}
        for order, hit in resolved:
            if order.state != EngagementState.NEUTRALIZED:
                continue
            tr = tby.get(order.target_track_id)
            if tr is None:
                continue
            d = np.linalg.norm(self.world.pos - [tr.x, tr.y, tr.z], axis=1)
            jj = int(np.argmin(d)) if self.world.n else -1
            if jj >= 0 and d[jj] <= self.assoc_m:
                self.world.neutralize(jj)

        # leakage
        rng_a = self.world.range_to_asset()
        leaked_now = 0
        for i in range(self.world.n):
            if (self.world.alive[i] and self.world.is_threat[i]
                    and rng_a[i] <= self.leak_radius_m):
                self.world.alive[i] = False
                self.world.neutralized[i] = False
                leaked_now += 1
                self.m.n_leaked += 1

        self._step += 1
        self._update_metrics()
        frame = self._frame(tracks, swarms)
        self.bus.publish("frame", frame)
        if self._step >= self.steps:
            self.done = True
        return frame

    def _update_metrics(self):
        m = self.m
        m.t = round(self.world.t, 2)
        m.n_threats = int(self.world.is_threat.sum())
        m.n_neutralized = int((self.world.neutralized
                               & self.world.is_threat).sum())
        m.leakage_rate = m.n_leaked / max(m.n_threats, 1)
        thr = np.where(self.world.is_threat)[0]
        m.detection_recall = (float(self._ever[thr].sum()) / len(thr)
                              if len(thr) else 0.0)
        tot = self._uas_tp + self._uas_fp
        m.uas_precision = self._uas_tp / tot if tot else 1.0
        m.mean_cycle_latency_ms = float(np.mean(self._lat)) if self._lat else 0.0
        m.committed_cost = round(self.mgr.committed_total, 2)
        m.sim_cost_per_kill = round(
            m.committed_cost / m.n_neutralized, 1) if m.n_neutralized else 0.0
        m.active_sites = len(self._active)
        if self.done or self._step % 25 == 0:
            m.audit_ok = self.audit.verify()
        m.audit_records = len(self.audit.records)

    def _frame(self, tracks, swarms) -> dict:
        keep = (TrackStatus.CONFIRMED, TrackStatus.COASTING)
        return jsonable({
            "t": round(self.world.t, 2),
            "scenario": self.sc.name,
            "asset": {"keepout": self.leak_radius_m},
            "sites": [{"id": s.site_id, "kind": s.kind.value,
                       "x": float(s.pos[0]), "y": float(s.pos[1]),
                       "range": s.max_range,
                       "active": s.site_id in self._active}
                      for s in self.sites],
            "tracks": [{"id": tr.track_id, "x": round(tr.x, 1),
                        "y": round(tr.y, 1), "z": round(tr.z, 1),
                        "vx": round(tr.vx, 1), "vy": round(tr.vy, 1),
                        "cls": tr.obj_class.value, "puas":
                        round(tr.class_prob.get("uas", 0.0), 2),
                        "status": tr.status.value, "rf": tr.rf_linked}
                       for tr in tracks if tr.status in keep],
            "swarms": [{"id": s.swarm_id, "n": s.n_members,
                        "threat": round(s.threat_level, 2),
                        "hull": [[round(x, 1), round(y, 1)]
                                 for x, y in s.hull_xy],
                        "tti": (None if not np.isfinite(s.min_time_to_impact)
                                else round(s.min_time_to_impact, 1)),
                        "mothership": s.has_mothership} for s in swarms],
            "orders": [{"id": o.order_id, "tid": o.target_track_id,
                        "eff": o.effector_id, "kind": o.effector_kind,
                        "pk": o.pkill, "state": o.state.value,
                        "xy": list(o.intercept_xy)}
                       for o in self.mgr.active_orders],
            "effectors": [{"id": e.eff_id, "kind": e.kind,
                           "mag": (None if e.magazine > 10**5
                                   else e.magazine)}
                          for e in self.mgr.effectors],
            "metrics": self.m.__dict__,
        })

    def run(self) -> Metrics:
        while not self.done:
            self.step()
        return self.m

    def record_replay(self) -> dict:
        frames = []
        while not self.done:
            frames.append(self.step())
        return {"scenario": self.sc.name,
                "dt": self.sc.dt, "frames": frames,
                "metrics": self.m.__dict__}
