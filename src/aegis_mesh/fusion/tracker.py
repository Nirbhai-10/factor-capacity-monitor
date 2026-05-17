"""Multi-sensor EKF tracker (PLAN.md §2.3 stand-in for MHT/JPDA).

- 6-state constant-velocity EKF.
- Fuses CARTESIAN (radar/EO-IR/acoustic) AND BEARING-only (passive RF)
  measurements via per-measurement Jacobians — one site's bearing has no
  range, so the distributed RF mesh triangulates through the filter.
- KD-tree gating so association is ~O(n log n): scales to 1000+ contacts.
- Track lifecycle: TENTATIVE -> CONFIRMED -> COASTING -> DELETED with a
  log-likelihood-ratio score.
- Online classification: per-update class evidence is accumulated in log
  space and smoothed.
"""

from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

from ..schemas import (Detection, MeasKind, ObjectClass, Track, TrackStatus)
from .classifier import CLASSES, MODEL, featurize


class _Tr:
    __slots__ = ("x", "P", "tid", "hits", "misses", "status", "score",
                 "rf_linked", "rcs", "md", "logp", "last_t", "_seen")

    def __init__(self, p, std, tid, t):
        self.x = np.array([p[0], p[1], p[2], 0.0, 0.0, 0.0])
        v = std ** 2
        self.P = np.diag([v, v, v, 1600.0, 1600.0, 1600.0])
        self.tid = tid
        self.hits = 1
        self.misses = 0
        self.status = TrackStatus.TENTATIVE
        self.score = 1.0
        self.rf_linked = None
        self.rcs = 0.0
        self.md = 0.0
        self.logp = np.zeros(len(CLASSES))
        self.last_t = t
        self._seen = False

    def predict(self, dt):
        F = np.eye(6)
        F[0, 3] = F[1, 4] = F[2, 5] = dt
        q = 6.0
        g = np.array([0.5 * dt * dt] * 3 + [dt] * 3)
        self.P = F @ self.P @ F.T + np.outer(g, g) * q
        self.x = F @ self.x

    # ---- measurement models ----------------------------------------------
    def _h_cart(self):
        H = np.zeros((3, 6)); H[0, 0] = H[1, 1] = H[2, 2] = 1.0
        return H, self.x[:3]

    def _h_bear(self, site):
        dx, dy, dz = self.x[0] - site[0], self.x[1] - site[1], \
            self.x[2] - site[2]
        rg2 = dx * dx + dy * dy
        rg = np.sqrt(rg2) + 1e-6
        az = np.arctan2(dy, dx)
        el = np.arctan2(dz, rg)
        H = np.zeros((2, 6))
        H[0, 0] = -dy / rg2
        H[0, 1] = dx / rg2
        d = rg2 + dz * dz
        H[1, 0] = -dx * dz / (rg * d)
        H[1, 1] = -dy * dz / (rg * d)
        H[1, 2] = rg / d
        return H, np.array([az, el])

    def gate_cart(self, det: Detection) -> float:
        H, hx = self._h_cart()
        r = det.pos_std ** 2
        R = np.diag([r, r, r * 1.4])
        y = np.array([det.x, det.y, det.z]) - hx
        S = H @ self.P @ H.T + R
        return float(y @ np.linalg.solve(S, y))

    def gate_bear(self, det: Detection) -> float:
        H, hx = self._h_bear(det.site)
        z = np.array([det.az, det.el])
        y = np.arctan2(np.sin(z - hx), np.cos(z - hx))
        R = np.diag([det.ang_std ** 2, det.ang_std ** 2])
        S = H @ self.P @ H.T + R
        return float(y @ np.linalg.solve(S, y))

    def update_cart(self, det: Detection):
        H, hx = self._h_cart()
        r = det.pos_std ** 2
        R = np.diag([r, r, r * 1.4])
        y = np.array([det.x, det.y, det.z]) - hx
        self._kalman(H, y, R)
        if det.rcs > 0:
            self.rcs = 0.7 * self.rcs + 0.3 * det.rcs if self.rcs else det.rcs
        self.md = 0.7 * self.md + 0.3 * det.micro_doppler if self.md \
            else det.micro_doppler
        self._classify(det)
        self._on_hit(det)

    def update_bear(self, det: Detection):
        H, hx = self._h_bear(det.site)
        z = np.array([det.az, det.el])
        y = np.arctan2(np.sin(z - hx), np.cos(z - hx))
        R = np.diag([det.ang_std ** 2, det.ang_std ** 2])
        self._kalman(H, y, R)
        if det.micro_doppler:
            self.md = 0.7 * self.md + 0.3 * det.micro_doppler if self.md \
                else det.micro_doppler
        self._classify(det)
        self._on_hit(det)

    def _kalman(self, H, y, R):
        S = H @ self.P @ H.T + R
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(6) - K @ H) @ self.P

    def _on_hit(self, det):
        if det.rf_linked is not None:
            self.rf_linked = det.rf_linked
        self.hits += 1
        self.misses = 0
        self.score = min(self.score + 1.4, 24.0)
        self.last_t = det.t
        self._seen = True
        if self.hits >= 3 and self.status == TrackStatus.TENTATIVE:
            self.status = TrackStatus.CONFIRMED

    def _classify(self, det):
        spd = float(np.linalg.norm(self.x[3:6]))
        f = featurize(spd, self.x[2], self.rcs or det.rcs or 0.05,
                      self.md or det.micro_doppler,
                      bool(self.rf_linked), self.x[5])
        pr = MODEL.proba(f)
        self.logp += np.log(np.array([pr[c.value] for c in CLASSES]) + 1e-9)
        self.logp -= self.logp.max()

    def class_prob(self) -> dict[str, float]:
        p = np.exp(self.logp); p /= p.sum() if p.sum() else 1.0
        return {CLASSES[i].value: float(p[i]) for i in range(len(CLASSES))}

    def obj_class(self) -> ObjectClass:
        cp = self.class_prob()
        return ObjectClass(max(cp, key=cp.get)) if cp else ObjectClass.UNKNOWN

    def miss(self):
        self.misses += 1
        self.score -= 1.0
        if (self.status in (TrackStatus.CONFIRMED, TrackStatus.COASTING)
                and not self._seen):
            self.status = TrackStatus.COASTING

    def to_track(self, t) -> Track:
        return Track(
            track_id=self.tid, t=t,
            x=self.x[0], y=self.x[1], z=self.x[2],
            vx=self.x[3], vy=self.x[4], vz=self.x[5],
            pos_cov=float(np.trace(self.P[:3, :3]) / 3.0),
            hits=self.hits, misses=self.misses, status=self.status,
            score=self.score, obj_class=self.obj_class(),
            class_prob=self.class_prob(), rf_linked=self.rf_linked,
            rcs=self.rcs, micro_doppler=self.md)


class Tracker:
    def __init__(self, gate_cart=16.27, gate_bear=11.83,
                 assoc_radius=220.0, max_misses=5, del_score=-3.0):
        self.gc = gate_cart
        self.gb = gate_bear
        self.ar = assoc_radius
        self.max_misses = max_misses
        self.del_score = del_score
        self._tr: list[_Tr] = []
        self._next = 1

    def step(self, dets: list[Detection], t: float, dt: float) -> list[Track]:
        for tr in self._tr:
            tr.predict(dt)
            tr._seen = False

        cart = [d for d in dets if d.meas_kind == MeasKind.CARTESIAN]
        bear = [d for d in dets if d.meas_kind == MeasKind.BEARING]

        used_cart = self._assoc_cart(cart)
        self._assoc_bear(bear)

        for tr in self._tr:
            if not tr._seen:
                tr.miss()

        for j, d in enumerate(cart):
            if j not in used_cart:
                nt = _Tr((d.x, d.y, d.z), max(d.pos_std, 5.0), self._next, t)
                nt.rcs = d.rcs
                nt.md = d.micro_doppler
                nt.rf_linked = d.rf_linked
                self._tr.append(nt)
                self._next += 1

        self._tr = [tr for tr in self._tr
                    if tr.misses <= self.max_misses
                    and tr.score > self.del_score]
        return [tr.to_track(t) for tr in self._tr]

    def _assoc_cart(self, cart: list[Detection]) -> set[int]:
        """GNN: each det -> its k nearest tracks (KD-tree, bounded), gate,
        then greedy global assignment by ascending Mahalanobis. O(D log N)."""
        used: set[int] = set()
        if not cart or not self._tr:
            return used
        tpos = np.array([tr.x[:3] for tr in self._tr])
        tree = cKDTree(tpos)
        dpos = np.array([[d.x, d.y, d.z] for d in cart])
        k = min(4, len(self._tr))
        dist, idx = tree.query(dpos, k=k)
        if k == 1:
            dist, idx = dist[:, None], idx[:, None]
        cand: list[tuple[float, int, int]] = []
        for j in range(len(cart)):
            for col in range(k):
                if dist[j, col] > self.ar:
                    break
                i = int(idx[j, col])
                m = self._tr[i].gate_cart(cart[j])
                if m <= self.gc:
                    cand.append((m, i, j))
        cand.sort()
        taken: set[int] = set()
        for m, i, j in cand:
            if i in taken or j in used:
                continue
            self._tr[i].update_cart(cart[j])
            taken.add(i)
            used.add(j)
        return used

    def _assoc_bear(self, bear: list[Detection]) -> None:
        """Bearing-only association, vectorised per site (only a few RF
        sites). Predicted az/el for all tracks computed once per site."""
        if not bear or not self._tr:
            return
        T = np.array([[t.x[0], t.x[1], t.x[2]] for t in self._tr])
        # angular uncertainty contribution from track position covariance
        pc = np.array([float(np.trace(t.P[:3, :3]) / 3.0) for t in self._tr])
        by_site: dict[tuple, list[Detection]] = {}
        for d in bear:
            by_site.setdefault(d.site, []).append(d)
        for site, ds in by_site.items():
            rel = T - np.array(site)
            rg = np.hypot(rel[:, 0], rel[:, 1]) + 1e-6
            slant = np.linalg.norm(rel, axis=1) + 1e-6
            t_az = np.arctan2(rel[:, 1], rel[:, 0])
            t_el = np.arctan2(rel[:, 2], rg)
            for d in ds:
                av = d.ang_std ** 2 + pc / rg ** 2
                ev = d.ang_std ** 2 + pc / slant ** 2
                daz = np.arctan2(np.sin(d.az - t_az), np.cos(d.az - t_az))
                dele = np.arctan2(np.sin(d.el - t_el), np.cos(d.el - t_el))
                r = daz ** 2 / av + dele ** 2 / ev
                i = int(np.argmin(r))
                if r[i] <= self.gb and not self._tr[i]._seen:
                    self._tr[i].update_bear(d)

    @property
    def confirmed_tracks(self) -> list[Track]:
        return [tr.to_track(tr.last_t) for tr in self._tr if tr.status in
                (TrackStatus.CONFIRMED, TrackStatus.COASTING)]
