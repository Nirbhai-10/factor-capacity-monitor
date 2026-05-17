"""Swarm-intent estimation — the differentiator (PLAN.md §2.3).

DBSCAN over confirmed UAS tracks (KD-tree neighbourhoods, lone clutter falls
out as noise), then per-swarm: convex hull, heading coherence, formation
tightness, axis-of-attack, closing speed, time-to-impact distribution,
mothership heuristic, and a class-weighted threat score.
"""

from __future__ import annotations

import numpy as np
from scipy.spatial import ConvexHull, cKDTree

from ..schemas import ObjectClass, SwarmObject, Track
from .threat_eval import evaluate


def _dbscan(pts: np.ndarray, eps: float, min_samples: int) -> np.ndarray:
    n = len(pts)
    labels = np.full(n, -1, dtype=int)
    if n == 0:
        return labels
    tree = cKDTree(pts)
    neigh = tree.query_ball_point(pts, eps)
    visited = np.zeros(n, bool)
    cid = 0
    for i in range(n):
        if visited[i]:
            continue
        visited[i] = True
        if len(neigh[i]) < min_samples:
            continue
        labels[i] = cid
        queue = [j for j in neigh[i] if j != i]
        qi = 0
        while qi < len(queue):
            j = queue[qi]; qi += 1
            if labels[j] == -1:
                labels[j] = cid          # border / reachable point
            if not visited[j]:
                visited[j] = True
                if len(neigh[j]) >= min_samples:   # core: expand once
                    queue.extend(k for k in neigh[j] if not visited[k])
        cid += 1
    return labels


def _hull_xy(xy: np.ndarray) -> list[tuple[float, float]]:
    if len(xy) < 3:
        return [tuple(map(float, p)) for p in xy]
    try:
        h = ConvexHull(xy)
        return [tuple(map(float, xy[v])) for v in h.vertices]
    except Exception:
        return [tuple(map(float, p)) for p in xy]


def estimate_swarms(tracks: list[Track], t: float, eps: float = 360.0,
                    min_samples: int = 2,
                    lone_threshold: float = 0.45) -> list[SwarmObject]:
    cand = [tr for tr in tracks if tr.confirmed
            and tr.obj_class in (ObjectClass.UAS, ObjectClass.UNKNOWN)]
    if not cand:
        return []
    pos = np.array([[c.x, c.y, c.z] for c in cand])
    vel = np.array([[c.vx, c.vy, c.vz] for c in cand])
    labels = _dbscan(pos, eps, min_samples)

    swarms: list[SwarmObject] = []
    for cid in sorted(set(labels) - {-1}):
        idx = np.where(labels == cid)[0]
        gp, gv = pos[idx], vel[idx]
        centroid = gp.mean(0)

        speeds = np.linalg.norm(gv, axis=1)
        moving = speeds > 1e-3
        if moving.sum() >= 2:
            u = gv[moving] / speeds[moving][:, None]
            sim = u @ u.T
            m = len(u)
            coherence = float(np.clip((sim.sum() - m) / (m * (m - 1)), 0, 1))
            axis = u.mean(0)[:2]
            axis = axis / (np.linalg.norm(axis) + 1e-9)
        else:
            coherence, axis = 0.0, np.zeros(2)

        spread = float(np.linalg.norm(gp - centroid, axis=1).mean())
        tightness = float(np.clip(1.0 - spread / 600.0, 0, 1))

        rng = float(np.linalg.norm(centroid))
        to_asset = -centroid / rng if rng > 1e-6 else np.zeros(3)
        closing = float(gv.mean(0) @ to_asset)
        ranges = np.linalg.norm(gp, axis=1)
        radial = (gv * to_asset).sum(1)
        with np.errstate(divide="ignore", invalid="ignore"):
            ttis = np.where(radial > 0.5, ranges / radial, np.inf)
        min_tti = float(np.min(ttis))
        med_tti = float(np.median(ttis[np.isfinite(ttis)])) \
            if np.isfinite(ttis).any() else float("inf")

        cls_conf = float(np.mean([c.class_prob.get("uas", 0.0)
                                  for c in (cand[i] for i in idx)]))
        # mothership: exactly one member that is both markedly SLOW and
        # the REAR-MOST along the attack axis (a real carrier trails its
        # children) — geometric test kills false positives on uniform
        # ingress clusters.
        med_sp = float(np.median(speeds)) if len(speeds) else 0.0
        has_mom = False
        if 4 <= len(idx) <= 16 and med_sp > 14.0:
            slow = np.where(speeds < 0.30 * med_sp)[0]
            if len(slow) == 1:
                axis3 = np.array([axis[0], axis[1], 0.0])
                proj = (gp - centroid) @ (-axis3)   # +ve = behind the pack
                k = int(slow[0])
                rear = proj[k]
                others = np.delete(proj, k)
                has_mom = bool(rear == proj.max()
                               and rear - others.max() > spread)

        n_mem = len(idx)
        # TEWA per-member threat (CPA/TBH/range/class), aggregated and
        # amplified by swarm size + heading coherence
        te = float(np.mean([evaluate(cand[i]).score for i in idx]))
        threat = float(np.clip(
            0.55 * te + 0.25 * min(1.0, n_mem / 12.0)
            + 0.20 * coherence, 0, 1))

        swarms.append(SwarmObject(
            swarm_id=int(cid), t=t,
            member_track_ids=[cand[i].track_id for i in idx],
            centroid=tuple(float(v) for v in centroid),
            hull_xy=_hull_xy(gp[:, :2]),
            n_members=n_mem, coherence=coherence,
            formation_tightness=tightness,
            axis_of_attack=(float(axis[0]), float(axis[1])),
            closing_speed=closing, min_time_to_impact=min_tti,
            median_time_to_impact=med_tti, has_mothership=has_mom,
            class_confidence=cls_conf, threat_level=threat))

    # lone-wolf handling: DBSCAN noise points that are individually a
    # credible threat (TEWA) are emitted as single-member objects so a
    # single ingressing drone is still engaged (doctrinally TEWA scores
    # single tracks, not only swarms).
    sid = (max((s.swarm_id for s in swarms), default=-1)) + 1
    for k in np.where(labels == -1)[0]:
        tr = cand[k]
        ts = evaluate(tr)
        if tr.obj_class != ObjectClass.UAS or ts.score < lone_threshold:
            continue
        rr = float(np.hypot(tr.x, tr.y)) + 1e-6
        closing = -(tr.x * tr.vx + tr.y * tr.vy) / rr
        swarms.append(SwarmObject(
            swarm_id=sid, t=t, member_track_ids=[tr.track_id],
            centroid=(tr.x, tr.y, tr.z), hull_xy=[(tr.x, tr.y)],
            n_members=1, coherence=0.0, formation_tightness=1.0,
            axis_of_attack=(0.0, 0.0),
            closing_speed=max(0.0, closing),
            min_time_to_impact=(ts.tbh if np.isfinite(ts.tbh)
                                else float("inf")),
            median_time_to_impact=ts.tbh, has_mothership=False,
            class_confidence=ts.p_uas, threat_level=ts.score))
        sid += 1

    swarms.sort(key=lambda s: s.threat_level, reverse=True)
    return swarms
