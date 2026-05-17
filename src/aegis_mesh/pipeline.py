"""End-to-end loop: sense -> fuse -> sensemake -> decide -> audit, with the
headline regression metrics from PLAN.md §10.

Neutralization is *simulated* and only applied when mitigation is authorized,
mirroring the authority gate in SAFETY.md / wta.py.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from .fusion.tracker import Tracker
from .orchestrator.audit import AuditLog
from .orchestrator.wta import Orchestrator
from .schemas import EngagementState
from .sensemaking.swarm_intent import estimate_swarms
from .sim.scenarios import Scenario
from .sim.sensors import SimWorld


@dataclass
class RunMetrics:
    scenario: str
    n_threats: int
    n_neutralized: int
    n_leaked: int
    leakage_rate: float
    detection_recall: float
    mean_cycle_latency_ms: float
    sim_cost_per_kill: float
    total_cost: float
    audit_ok: bool
    audit_records: int

    def summary(self) -> str:
        return (
            f"[{self.scenario}] threats={self.n_threats} "
            f"neutralized={self.n_neutralized} leaked={self.n_leaked} "
            f"leakage={self.leakage_rate:.1%} "
            f"recall={self.detection_recall:.1%} "
            f"latency={self.mean_cycle_latency_ms:.1f}ms "
            f"$/kill={self.sim_cost_per_kill:,.0f} "
            f"audit={'OK' if self.audit_ok else 'BROKEN'}"
        )


def run(scenario: Scenario, *, mitigation_authorized: bool = True,
        seed: int = 0, assoc_m: float = 180.0,
        leak_radius_m: float = 250.0) -> RunMetrics:
    world = SimWorld(scenario, seed=seed)
    tracker = Tracker()
    orch = Orchestrator(mitigation_authorized=mitigation_authorized)
    audit = AuditLog()
    audit.append(0.0, "policy",
                 {"mitigation_authorized": mitigation_authorized,
                  "scenario": scenario.name})

    n = world.n
    ever_tracked = np.zeros(n, dtype=bool)
    leaked = np.zeros(n, dtype=bool)
    latencies: list[float] = []
    total_cost = 0.0
    steps = int(scenario.duration_s / scenario.dt)

    for _ in range(steps):
        world.step()
        truth = world.pos.copy()
        alive = world.alive.copy()

        t0 = time.perf_counter()
        dets = world.sense()
        tracks = tracker.step(dets, world.t, scenario.dt)
        swarms = estimate_swarms(tracks, world.t)
        result = orch.assign(swarms, tracks, world.t)
        latencies.append((time.perf_counter() - t0) * 1000.0)

        # detection recall bookkeeping (confirmed track near a live threat)
        for tr in tracks:
            if not tr.confirmed:
                continue
            tp = np.array([tr.x, tr.y, tr.z])
            d = np.linalg.norm(truth - tp, axis=1)
            j = int(np.argmin(d)) if n else -1
            if j >= 0 and alive[j] and d[j] <= assoc_m:
                ever_tracked[j] = True

        # simulated effect (authority-gated)
        for o in result.orders:
            total_cost += o.expected_cost
            audit.append(world.t, "decision", {
                "swarm_id": o.swarm_id, "track_id": o.target_track_id,
                "effector": o.effector_id, "kind": o.effector_kind,
                "cost": round(o.expected_cost, 3), "state": o.state.value})
            if o.state == EngagementState.RECOMMENDED:
                tr = next((x for x in tracks
                           if x.track_id == o.target_track_id), None)
                if tr is None:
                    continue
                tp = np.array([tr.x, tr.y, tr.z])
                d = np.linalg.norm(world.pos - tp, axis=1)
                jj = int(np.argmin(d)) if n else -1
                if jj >= 0 and world.alive[jj] and d[jj] <= assoc_m:
                    world.neutralize(jj)

        rng = world.range_to_asset()
        for i in range(n):
            if world.alive[i] and rng[i] <= leak_radius_m:
                leaked[i] = True
                world.alive[i] = False  # past the wire; stop tracking

    n_neut = int(world.neutralized.sum())
    n_leak = int(leaked.sum())
    return RunMetrics(
        scenario=scenario.name, n_threats=n,
        n_neutralized=n_neut, n_leaked=n_leak,
        leakage_rate=(n_leak / n if n else 0.0),
        detection_recall=(float(ever_tracked.sum()) / n if n else 0.0),
        mean_cycle_latency_ms=float(np.mean(latencies)) if latencies else 0.0,
        sim_cost_per_kill=(total_cost / n_neut if n_neut else 0.0),
        total_cost=total_cost,
        audit_ok=audit.verify(), audit_records=len(audit.records))
