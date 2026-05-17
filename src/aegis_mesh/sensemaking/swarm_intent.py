"""Swarm-intent estimation — the differentiator (PLAN.md §2.3).

Groups confirmed tracks into swarm-level threat objects by spatial proximity
and velocity coherence, then estimates axis-of-attack closing speed, minimum
time-to-impact against the defended asset (origin), and a 0..1 threat level.
"""

from __future__ import annotations

import numpy as np

from ..schemas import ObjectClass, SwarmObject, Track


def _components(points: np.ndarray, radius: float) -> list[list[int]]:
    """Single-linkage clusters via union-find within `radius` (m)."""
    n = len(points)
    parent = list(range(n))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    r2 = radius * radius
    for i in range(n):
        for j in range(i + 1, n):
            d = points[i] - points[j]
            if d @ d <= r2:
                parent[find(i)] = find(j)
    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def estimate_swarms(tracks: list[Track], t: float,
                    link_radius: float = 350.0) -> list[SwarmObject]:
    cand = [tr for tr in tracks
            if tr.confirmed and tr.obj_class in (ObjectClass.UAS,
                                                 ObjectClass.UNKNOWN)]
    if not cand:
        return []

    pos = np.array([[c.x, c.y, c.z] for c in cand])
    vel = np.array([[c.vx, c.vy, c.vz] for c in cand])

    swarms: list[SwarmObject] = []
    for sid, idxs in enumerate(_components(pos, link_radius)):
        gp = pos[idxs]
        gv = vel[idxs]
        centroid = gp.mean(axis=0)

        # velocity coherence: mean pairwise cos-similarity of headings
        speeds = np.linalg.norm(gv, axis=1)
        moving = speeds > 1e-3
        if moving.sum() >= 2:
            u = gv[moving] / speeds[moving][:, None]
            sim = u @ u.T
            m = len(u)
            coherence = float((sim.sum() - m) / (m * (m - 1)))
        else:
            coherence = 0.0
        coherence = max(0.0, min(1.0, coherence))

        # closing speed toward asset (origin) and time-to-impact
        rng = np.linalg.norm(centroid)
        to_asset = -centroid / rng if rng > 1e-6 else np.zeros(3)
        mean_v = gv.mean(axis=0)
        closing = float(mean_v @ to_asset)              # +ve = inbound
        tti = rng / closing if closing > 0.5 else float("inf")

        n_mem = len(idxs)
        size_term = min(1.0, n_mem / 12.0)
        prox_term = max(0.0, 1.0 - rng / 6000.0)
        urgency = 0.0 if np.isinf(tti) else max(0.0, 1.0 - tti / 120.0)
        threat = float(np.clip(
            0.35 * size_term + 0.25 * coherence + 0.20 * prox_term
            + 0.20 * urgency, 0.0, 1.0))

        swarms.append(SwarmObject(
            swarm_id=sid, t=t,
            member_track_ids=[cand[i].track_id for i in idxs],
            centroid=tuple(float(v) for v in centroid),
            n_members=n_mem, coherence=coherence,
            closing_speed=closing, min_time_to_impact=tti,
            threat_level=threat))
    swarms.sort(key=lambda s: s.threat_level, reverse=True)
    return swarms
