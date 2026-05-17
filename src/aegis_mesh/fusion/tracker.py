"""Multi-target tracker: constant-velocity Kalman filter + global-nearest-
neighbor association (scipy linear_sum_assignment) with Mahalanobis gating
and M-of-N confirm/delete logic.

This is a tractable stand-in for the MHT/JPDA fusion in PLAN.md §2.3; the
interface (Detection[] -> Track[]) is what later Rust services implement.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment

from ..schemas import Detection, ObjectClass, Track


class _KF:
    __slots__ = ("x", "P", "track_id", "hits", "misses", "confirmed",
                 "rf_linked", "last_t", "class_votes")

    def __init__(self, det: Detection, track_id: int):
        self.x = np.array([det.x, det.y, det.z, 0.0, 0.0, 0.0])
        p = det.pos_std ** 2
        self.P = np.diag([p, p, p, 900.0, 900.0, 900.0])
        self.track_id = track_id
        self.hits = 1
        self.misses = 0
        self.confirmed = False
        self.rf_linked = det.rf_linked
        self.last_t = det.t
        self.class_votes: dict[ObjectClass, int] = {}
        self._vote(det.class_hint)

    def _vote(self, c: ObjectClass) -> None:
        if c != ObjectClass.UNKNOWN:
            self.class_votes[c] = self.class_votes.get(c, 0) + 1

    @property
    def obj_class(self) -> ObjectClass:
        if not self.class_votes:
            return ObjectClass.UNKNOWN
        return max(self.class_votes, key=self.class_votes.get)

    def predict(self, dt: float) -> None:
        F = np.eye(6)
        F[0, 3] = F[1, 4] = F[2, 5] = dt
        q = 8.0
        G = np.array([0.5 * dt * dt, 0.5 * dt * dt, 0.5 * dt * dt, dt, dt, dt])
        Q = np.outer(G, G) * q
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q

    def innovation(self, det: Detection) -> tuple[np.ndarray, np.ndarray]:
        H = np.zeros((3, 6))
        H[0, 0] = H[1, 1] = H[2, 2] = 1.0
        r = det.pos_std ** 2
        R = np.diag([r, r, r * 1.4])
        y = np.array([det.x, det.y, det.z]) - H @ self.x
        S = H @ self.P @ H.T + R
        return y, S

    def update(self, det: Detection) -> None:
        H = np.zeros((3, 6))
        H[0, 0] = H[1, 1] = H[2, 2] = 1.0
        y, S = self.innovation(det)
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(6) - K @ H) @ self.P
        self.hits += 1
        self.misses = 0
        self.last_t = det.t
        if det.rf_linked is not None:
            self.rf_linked = det.rf_linked
        self._vote(det.class_hint)

    def to_track(self, t: float) -> Track:
        return Track(
            track_id=self.track_id, t=t,
            x=self.x[0], y=self.x[1], z=self.x[2],
            vx=self.x[3], vy=self.x[4], vz=self.x[5],
            pos_cov=float(np.trace(self.P[:3, :3]) / 3.0),
            hits=self.hits, misses=self.misses, confirmed=self.confirmed,
            obj_class=self.obj_class, rf_linked=self.rf_linked)


class Tracker:
    def __init__(self, gate_chi2: float = 16.27, confirm_hits: int = 3,
                 max_misses: int = 4):
        self.gate = gate_chi2          # 99% gate, 3 dof
        self.confirm_hits = confirm_hits
        self.max_misses = max_misses
        self._tracks: list[_KF] = []
        self._next_id = 1

    def step(self, dets: list[Detection], t: float, dt: float) -> list[Track]:
        for tr in self._tracks:
            tr.predict(dt)

        unassigned = list(range(len(dets)))
        if self._tracks and dets:
            n_t, n_d = len(self._tracks), len(dets)
            BIG = 1e6
            cost = np.full((n_t, n_d), BIG)
            for i, tr in enumerate(self._tracks):
                for j, d in enumerate(dets):
                    y, S = tr.innovation(d)
                    md2 = float(y @ np.linalg.inv(S) @ y)
                    if md2 <= self.gate:
                        cost[i, j] = md2
            rows, cols = linear_sum_assignment(cost)
            assigned_d: set[int] = set()
            for i, j in zip(rows, cols):
                if cost[i, j] < BIG:
                    self._tracks[i].update(dets[j])
                    assigned_d.add(j)
            unassigned = [j for j in range(n_d) if j not in assigned_d]

        # miss bookkeeping
        updated_ids = {id(tr) for tr in self._tracks if tr.last_t == t}
        for tr in self._tracks:
            if id(tr) not in updated_ids:
                tr.misses += 1
            if tr.hits >= self.confirm_hits:
                tr.confirmed = True

        # spawn tentative tracks from leftover detections
        for j in unassigned:
            self._tracks.append(_KF(dets[j], self._next_id))
            self._next_id += 1

        self._tracks = [tr for tr in self._tracks if tr.misses <= self.max_misses]
        return [tr.to_track(t) for tr in self._tracks]

    @property
    def confirmed_tracks(self) -> list[Track]:
        return [tr.to_track(tr.last_t) for tr in self._tracks if tr.confirmed]
