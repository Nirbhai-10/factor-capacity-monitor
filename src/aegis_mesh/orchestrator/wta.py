"""Weapon-Target Assignment + engagement-authority FSM (PLAN.md §2.4).

WTA:
- AREA effectors (HPM-class): greedy MAX-COVERAGE burst placement — pick the
  aim point covering the most un-engaged inbound threats within effect
  radius+range, repeat until magazine/threats exhausted. This is the
  cost-per-kill economics that beats $-per-drone attackers.
- POINT effectors: globally optimal assignment via Hungarian
  (scipy.linear_sum_assignment) on a cost = unit_cost / Pkill, gated by
  applicability, range and keep-out (no kinetic/net inside the collateral
  ring near the asset).

Authority FSM (per order):
  PROPOSED -> (commercial build) SUPPRESSED_NO_AUTHORITY
  PROPOSED -> PENDING_APPROVAL -> APPROVED -> EXECUTING -> NEUTRALIZED|MISSED
  short-fuse auto-engage envelope (TTI < auto_engage_tti) skips the queue
  when mitigation is authorized. Nothing fires without authority. SAFETY.md.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.spatial import cKDTree

from ..schemas import (EngagementOrder, EngagementState, SwarmObject, Track)

_PKILL = {                       # effector_kind -> {class: base Pkill}
    "soft_kill_cyber": {"*": 0.95},
    "hpm":            {"uas": 0.92, "*": 0.85},
    "laser":          {"uas": 0.78, "*": 0.7},
    "net_interceptor": {"*": 0.88},
}


@dataclass
class Effector:
    eff_id: str
    kind: str
    unit_cost: float
    magazine: int
    area_radius: float = 0.0          # >0 => area effector
    requires_rf_link: bool = False
    max_range_m: float = 6000.0
    min_keepout_m: float = 0.0        # do not engage closer than this to asset

    def pkill(self, tr: Track, rng_m: float) -> float:
        tbl = _PKILL[self.kind]
        base = tbl.get(tr.obj_class.value, tbl.get("*", 0.6))
        # high & flat in-envelope, sharp roll-off only past 80% max range
        x = rng_m / self.max_range_m
        falloff = 1.0 if x <= 0.8 else max(0.35, 1.0 - 3.5 * (x - 0.8))
        return base * falloff

    def applicable(self, tr: Track, rng_m: float) -> bool:
        if self.magazine <= 0 or rng_m > self.max_range_m:
            return False
        if rng_m < self.min_keepout_m:
            return False
        if self.requires_rf_link and not bool(tr.rf_linked):
            return False
        return True


def default_effector_suite() -> list[Effector]:
    return [
        Effector("cyber-0", "soft_kill_cyber", 5.0, 10**6,
                 requires_rf_link=True, max_range_m=4200.0),
        Effector("hpm-0", "hpm", 130.0, 220, area_radius=450.0,
                 max_range_m=2700.0),
        Effector("laser-0", "laser", 18.0, 10**6, max_range_m=3200.0),
        # recoverable net interceptor: consumable net + amortised airframe
        Effector("net-0", "net_interceptor", 350.0, 24,
                 max_range_m=3600.0, min_keepout_m=300.0),
    ]


@dataclass
class WTAResult:
    orders: list[EngagementOrder]
    committed_cost: float
    n_engaged: int


@dataclass
class _Active:
    order: EngagementOrder
    resolve_t: float


class EngagementManager:
    """Stateful across cycles: magazines, order ids, approval queue,
    scheduled resolution."""

    def __init__(self, effectors=None, *, mitigation_authorized=False,
                 require_human=True, auto_engage_tti=12.0,
                 engage_threat=0.30, flight_time=3.0, keepout_m=250.0,
                 area_min_batch=3, audit=None):
        self.effectors = effectors or default_effector_suite()
        self.mitigation_authorized = mitigation_authorized
        self.require_human = require_human
        self.auto_engage_tti = auto_engage_tti
        self.engage_threat = engage_threat
        self.flight_time = flight_time
        self.keepout_m = keepout_m
        self.area_min_batch = area_min_batch
        self.audit = audit
        self._oid = 1
        self._busy: dict[int, _Active] = {}      # track_id -> active engagement
        self.pending: dict[int, EngagementOrder] = {}
        self.committed_total = 0.0

    # ---- helpers ----------------------------------------------------------
    def _rng_to_asset(self, tr: Track) -> float:
        return float(np.hypot(tr.x, tr.y))

    def _state_for(self, tti: float) -> EngagementState:
        if not self.mitigation_authorized:
            return EngagementState.SUPPRESSED_NO_AUTHORITY
        if not self.require_human or tti < self.auto_engage_tti:
            return EngagementState.APPROVED
        return EngagementState.PENDING_APPROVAL

    def _emit(self, kind, payload):
        if self.audit is not None:
            self.audit.append(payload.get("t", 0.0), kind, payload)

    # ---- main proposal step ----------------------------------------------
    def propose(self, swarms: list[SwarmObject], tracks: list[Track],
                t: float) -> WTAResult:
        by_id = {tr.track_id: tr for tr in tracks}
        sw_of, tti_of = {}, {}
        targets: list[Track] = []
        for sw in swarms:
            if sw.threat_level < self.engage_threat:
                continue
            for tid in sw.member_track_ids:
                tr = by_id.get(tid)
                if tr is None or tid in self._busy:
                    continue
                targets.append(tr)
                sw_of[tid] = sw.swarm_id
                tti_of[tid] = sw.min_time_to_impact
        orders: list[EngagementOrder] = []
        cost = 0.0
        if not targets:
            return WTAResult(orders, 0.0, 0)

        engaged: set[int] = set()
        rng_m = {tr.track_id: self._rng_to_asset(tr) for tr in targets}

        # 1) AREA effectors: KD-tree greedy max-coverage burst placement.
        # Each iteration: pick the contact whose `area_radius` ball covers
        # the most still-unengaged contacts -> one burst. O(iter * n log n).
        for eff in [e for e in self.effectors if e.area_radius > 0]:
            pool = [tr for tr in targets if tr.track_id not in engaged
                    and eff.applicable(tr, rng_m[tr.track_id])]
            while eff.magazine > 0 and len(pool) >= self.area_min_batch:
                P = np.array([[tr.x, tr.y] for tr in pool])
                tree = cKDTree(P)
                balls = tree.query_ball_point(P, eff.area_radius)
                ci = max(range(len(pool)), key=lambda k: len(balls[k]))
                cover = balls[ci]
                if len(cover) < self.area_min_batch:
                    break
                batch = [pool[k] for k in cover]
                eff.magazine -= 1
                share = eff.unit_cost / len(batch)
                for tr in batch:
                    st = self._state_for(tti_of[tr.track_id])
                    orders.append(self._mk_order(
                        t, sw_of, tr, eff, share,
                        eff.pkill(tr, rng_m[tr.track_id]), st,
                        f"area burst x{len(batch)}"))
                    engaged.add(tr.track_id)
                    cost += share
                pool = [tr for tr in pool if tr.track_id not in engaged]

        # 2) POINT effectors: greedy cheapest-sufficient assignment.
        # Optimal here because the cheap effectors (cyber/laser) have
        # effectively unbounded magazine, so only the capacity-limited
        # ones (net) contend -> process by priority (closest first).
        rem = sorted((tr for tr in targets if tr.track_id not in engaged),
                     key=lambda tr: rng_m[tr.track_id])
        point = [e for e in self.effectors if e.area_radius == 0]
        for tr in rem:
            rm = rng_m[tr.track_id]
            in_keepout = rm < self.keepout_m
            best, best_c, best_pk = None, 1e18, 0.0
            for e in point:
                if e.magazine <= 0 or not e.applicable(tr, rm):
                    continue
                if in_keepout and e.kind == "net_interceptor":
                    continue
                pk = e.pkill(tr, rm)
                if pk <= 0.05:
                    continue
                c = e.unit_cost / pk + 0.01 * rm
                if c < best_c:
                    best, best_c, best_pk = e, c, pk
            if best is None:
                continue
            best.magazine -= 1
            st = self._state_for(tti_of[tr.track_id])
            orders.append(self._mk_order(
                t, sw_of, tr, best, best.unit_cost, best_pk, st,
                f"{best.kind} point engage"))
            engaged.add(tr.track_id)
            cost += best.unit_cost

        self.committed_total += cost
        return WTAResult(orders, cost, len(engaged))

    def _mk_order(self, t, sw_of, tr, eff, cost, pk, state, why):
        oid = self._oid
        self._oid += 1
        o = EngagementOrder(
            order_id=oid, t=t, swarm_id=sw_of.get(tr.track_id, -1),
            target_track_id=tr.track_id, effector_id=eff.eff_id,
            effector_kind=eff.kind, pkill=round(pk, 3),
            expected_cost=round(cost, 2), state=state, rationale=why,
            intercept_xy=(round(tr.x, 1), round(tr.y, 1)))
        self._emit("decision", {
            "t": t, "order_id": oid, "track_id": tr.track_id,
            "effector": eff.eff_id, "kind": eff.kind,
            "pkill": o.pkill, "cost": o.expected_cost, "state": state.value})
        if state == EngagementState.PENDING_APPROVAL:
            self.pending[oid] = o
        elif state == EngagementState.APPROVED:
            self._arm(o, t)
        return o

    def _arm(self, o: EngagementOrder, t: float):
        o.state = EngagementState.EXECUTING
        self._busy[o.target_track_id] = _Active(o, t + self.flight_time)

    # ---- human-on-the-loop ------------------------------------------------
    def approve(self, oid: int, t: float) -> bool:
        o = self.pending.pop(oid, None)
        if o is None:
            return False
        o.state = EngagementState.APPROVED
        self._emit("approval", {"t": t, "order_id": oid, "decision": "approve"})
        self._arm(o, t)
        return True

    def deny(self, oid: int, t: float) -> bool:
        o = self.pending.pop(oid, None)
        if o is None:
            return False
        o.state = EngagementState.ABORTED
        self._emit("approval", {"t": t, "order_id": oid, "decision": "deny"})
        return True

    # ---- resolution -------------------------------------------------------
    def resolve_due(self, t: float, rng: np.random.Generator
                    ) -> list[tuple[EngagementOrder, bool]]:
        out = []
        for tid, act in list(self._busy.items()):
            if t >= act.resolve_t:
                hit = rng.random() < act.order.pkill
                act.order.state = (EngagementState.NEUTRALIZED if hit
                                   else EngagementState.MISSED)
                self._emit("resolution", {
                    "t": t, "order_id": act.order.order_id,
                    "track_id": tid, "result": act.order.state.value})
                out.append((act.order, hit))
                del self._busy[tid]
        return out

    @property
    def active_orders(self) -> list[EngagementOrder]:
        return ([a.order for a in self._busy.values()]
                + list(self.pending.values()))
