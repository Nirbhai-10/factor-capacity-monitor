"""Weapon-Target Assignment + engagement-authority FSM (PLAN.md §2.4).

Cheapest-sufficient-effector assignment under magazine/applicability limits.
Area effectors (HPM-class) neutralize many co-located inbound threats per
burst — this is the cost-per-kill economics that beats $-per-threat attackers.

Authority: human-on-the-loop by default -> orders are RECOMMENDED. Commercial
(detect/track-only) builds set mitigation_authorized=False -> every order is
SUPPRESSED_NO_AUTHORITY. Mitigation is never auto-executed here. See SAFETY.md.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..schemas import EngagementOrder, EngagementState, SwarmObject, Track


@dataclass
class Effector:
    eff_id: str
    kind: str                       # soft_kill_cyber | hpm | net_interceptor | laser
    unit_cost: float                # $ per engagement
    magazine: int                   # engagements remaining (inf -> very large)
    area_capacity: int = 1          # targets neutralized per engagement
    requires_rf_link: bool = False  # cyber-takeover needs an RF control link
    max_range_m: float = 6000.0

    def applicable(self, tr: Track, rng_m: float) -> bool:
        if self.magazine <= 0 or rng_m > self.max_range_m:
            return False
        if self.requires_rf_link and not bool(tr.rf_linked):
            return False
        return True


def default_effector_suite() -> list[Effector]:
    """Layered, cheapest-first (PLAN.md §2.5)."""
    return [
        Effector("cyber-0", "soft_kill_cyber", 5.0, magazine=10**6,
                 area_capacity=1, requires_rf_link=True, max_range_m=4000.0),
        Effector("hpm-0", "hpm", 120.0, magazine=200, area_capacity=20,
                 max_range_m=2500.0),
        Effector("net-0", "net_interceptor", 1500.0, magazine=12,
                 area_capacity=1, max_range_m=3500.0),
        Effector("laser-0", "laser", 15.0, magazine=10**6, area_capacity=1,
                 max_range_m=3000.0),
    ]


@dataclass
class WTAResult:
    orders: list[EngagementOrder]
    total_cost: float
    n_engaged: int


class Orchestrator:
    def __init__(self, effectors: list[Effector] | None = None,
                 engage_threat: float = 0.25,
                 mitigation_authorized: bool = False):
        self.effectors = effectors if effectors is not None \
            else default_effector_suite()
        self.engage_threat = engage_threat
        self.mitigation_authorized = mitigation_authorized

    def _state(self) -> EngagementState:
        return (EngagementState.RECOMMENDED if self.mitigation_authorized
                else EngagementState.SUPPRESSED_NO_AUTHORITY)

    def assign(self, swarms: list[SwarmObject], tracks: list[Track],
               t: float) -> WTAResult:
        by_id = {tr.track_id: tr for tr in tracks}
        orders: list[EngagementOrder] = []
        total = 0.0
        state = self._state()

        # threats: members of swarms above engage threshold, sorted by urgency
        targets: list[Track] = []
        swarm_of: dict[int, int] = {}
        for sw in swarms:
            if sw.threat_level < self.engage_threat:
                continue
            for tid in sw.member_track_ids:
                tr = by_id.get(tid)
                if tr is not None:
                    targets.append(tr)
                    swarm_of[tid] = sw.swarm_id

        def rng(tr: Track) -> float:
            return float(np.linalg.norm([tr.x, tr.y, tr.z]))

        targets.sort(key=rng)  # closest first

        hpm = next((e for e in self.effectors
                    if e.kind == "hpm" and e.magazine > 0), None)
        engaged: set[int] = set()

        # 1) area effector batches co-located inbound threats (economics moat)
        if hpm is not None:
            pending = [tr for tr in targets if hpm.applicable(tr, rng(tr))]
            i = 0
            while i < len(pending) and hpm.magazine > 0:
                batch = pending[i:i + hpm.area_capacity]
                if not batch:
                    break
                hpm.magazine -= 1
                share = hpm.unit_cost / len(batch)
                for tr in batch:
                    total += share
                    engaged.add(tr.track_id)
                    orders.append(EngagementOrder(
                        t=t, swarm_id=swarm_of.get(tr.track_id, -1),
                        target_track_id=tr.track_id, effector_id=hpm.eff_id,
                        effector_kind=hpm.kind, expected_cost=share,
                        state=state,
                        rationale=f"area burst x{len(batch)} @ {rng(tr):.0f} m"))
                i += hpm.area_capacity

        # 2) residual: cheapest applicable point effector per remaining threat
        point = sorted((e for e in self.effectors if e.kind != "hpm"),
                       key=lambda e: e.unit_cost)
        for tr in targets:
            if tr.track_id in engaged:
                continue
            for e in point:
                if e.applicable(tr, rng(tr)):
                    e.magazine -= 1
                    total += e.unit_cost
                    engaged.add(tr.track_id)
                    orders.append(EngagementOrder(
                        t=t, swarm_id=swarm_of.get(tr.track_id, -1),
                        target_track_id=tr.track_id, effector_id=e.eff_id,
                        effector_kind=e.kind, expected_cost=e.unit_cost,
                        state=state,
                        rationale=f"{e.kind} point engage @ {rng(tr):.0f} m"))
                    break

        return WTAResult(orders=orders, total_cost=total,
                         n_engaged=len(engaged))
