"""Gaussian-Mixture PHD filter + label manager (battle-grade swarm tracker).

Vo & Ma, "The Gaussian Mixture Probability Hypothesis Density Filter,"
IEEE Trans. Signal Processing, 54(11), 2006. Closed-form recursion that
propagates the multi-target posterior intensity as a Gaussian mixture —
no explicit measurement-to-track association, robust to clutter, missed
detections and an unknown, time-varying number of targets. This is the
recognised state of the art for dense-swarm tracking.

Extensions used here:
- Measurement-driven adaptive birth (Ristic et al.) for new ingress.
- Ellipsoidal gating via KD-tree so update is ~O((J+m) log J): scales
  to 1000+ contacts in real time.
- A label manager gives the unlabelled PHD output persistent track IDs
  (needed downstream for swarm clustering, the engagement-authority FSM
  and the audit trail) — nearest-gated assignment, M/N confirmation.
- Online classification (softmax over the sim's signature model) folded
  in per label from the nearest gated measurement.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.spatial import cKDTree

from ..schemas import (Detection, GuidanceClass, MeasKind, ObjectClass,
                       Track, TrackStatus)
from ..schemas import GuidanceClass as G
from .classifier import CLASSES, MODEL, featurize
from .localization import aoa_triangulate

H = np.zeros((3, 6))
H[0, 0] = H[1, 1] = H[2, 2] = 1.0


def _F(dt):
    F = np.eye(6)
    F[0, 3] = F[1, 4] = F[2, 5] = dt
    return F


def _Q(dt, q=9.0):
    g = np.array([dt * dt / 2] * 3 + [dt] * 3)
    return np.outer(g, g) * q


@dataclass
class _Comp:
    w: float
    m: np.ndarray
    P: np.ndarray


@dataclass
class _Label:
    tid: int
    m: np.ndarray
    P: np.ndarray
    age: int = 1
    missed: int = 0
    status: TrackStatus = TrackStatus.TENTATIVE
    rf: bool | None = None
    rcs: float = 0.0
    md: float = 0.0
    logp: np.ndarray = field(default_factory=lambda: np.zeros(len(CLASSES)))
    rf_hits: int = 0          # frames an RF link was observed
    obs: int = 0              # frames observed (for guidance inference)
    auto_bias: float = 0.0    # external evidence toward AUTONOMOUS (probe)


class GMPHDTracker:
    def __init__(self, ps=0.99, pd=0.90, clutter_kappa=1e-9,
                 prune_T=1e-4, merge_U=16.0, cap_J=1500,
                 birth_w=0.02, gate=29.0, confirm=3, max_missed=4,
                 merge_radius=140.0):
        self.ps, self.pd, self.kappa = ps, pd, clutter_kappa
        self.T, self.U, self.Jmax = prune_T, merge_U, cap_J
        self.merge_radius = merge_radius
        self.birth_w, self.gate = birth_w, gate
        self.confirm, self.max_missed = confirm, max_missed
        self.comps: list[_Comp] = []
        self.labels: dict[int, _Label] = {}
        self._next = 1

    # ---- measurement assembly (multi-sensor -> position fixes) -----------
    def _measurements(self, dets: list[Detection]):
        Z, R, feat = [], [], []
        rf_sites: dict[float, list] = {}
        for d in dets:
            if d.meas_kind == MeasKind.CARTESIAN:
                Z.append([d.x, d.y, d.z])
                r = d.pos_std ** 2
                R.append(np.diag([r, r, r * 1.4]))
                feat.append((d.rf_linked, d.micro_doppler, d.rcs,
                             d.class_hint))
            else:  # BEARING -> bin by ~az for cross-site triangulation
                key = round(d.az, 1)
                rf_sites.setdefault(key, []).append(d)
        for ds in rf_sites.values():
            if len(ds) < 2:
                continue
            sites = np.array([d.site[:2] for d in ds])
            az = np.array([d.az for d in ds])
            astd = np.array([d.ang_std for d in ds])
            fix = aoa_triangulate(sites, az, astd)
            if fix is None:
                continue
            xy, P2 = fix
            zz = np.mean([d.site[2] + np.tan(d.el) *
                          np.hypot(xy[0] - d.site[0], xy[1] - d.site[1])
                          for d in ds])
            Z.append([xy[0], xy[1], zz])
            R.append(np.diag([P2[0, 0], P2[1, 1], 1600.0]))
            md = float(np.mean([d.micro_doppler for d in ds]))
            feat.append((True, md, 0.0, ObjectClass.UAS))
        return (np.array(Z) if Z else np.zeros((0, 3))), R, feat

    # ---- GM-PHD recursion -------------------------------------------------
    def step(self, dets, t, dt) -> list[Track]:
        Z, R, feat = self._measurements(dets)

        # predict
        F, Q = _F(dt), _Q(dt)
        for c in self.comps:
            c.w *= self.ps
            c.m = F @ c.m
            c.P = F @ c.P @ F.T + Q
        # gated measurement-driven birth: only spawn a birth component for
        # a measurement not already explained by a surviving component
        # (keeps the mixture size ~O(#targets), not O(#measurements)).
        if len(Z):
            if self.comps:
                etree = cKDTree(np.array([c.m[:3] for c in self.comps]))
                unexplained = etree.query_ball_point(Z, 120.0)
            else:
                unexplained = [[]] * len(Z)
            for zi, z in enumerate(Z):
                if not unexplained[zi]:
                    self.comps.append(_Comp(
                        self.birth_w,
                        np.array([z[0], z[1], z[2], 0, 0, 0.0]),
                        np.diag([60.0**2, 60.0**2, 60.0**2,
                                 900., 900., 400.])))

        if not self.comps:
            return self._emit(t)

        Hm = np.array([H @ c.m for c in self.comps])      # (J,3)
        # gating tree on predicted measurement means
        tree = cKDTree(Hm)
        # missed-detection term
        upd: list[_Comp] = [_Comp((1 - self.pd) * c.w, c.m.copy(), c.P.copy())
                            for c in self.comps]

        for zi in range(len(Z)):
            z, Rz = Z[zi], R[zi]
            cand = tree.query_ball_point(z, 250.0)
            if not cand:
                continue
            qs, news = [], []
            for ci in cand:
                c = self.comps[ci]
                S = H @ c.P @ H.T + Rz
                Si = np.linalg.inv(S)
                y = z - H @ c.m
                md2 = float(y @ Si @ y)
                if md2 > self.gate:
                    qs.append(0.0)
                    news.append(None)
                    continue
                det = max(np.linalg.det(2 * np.pi * S), 1e-12)
                q = np.exp(-0.5 * md2) / np.sqrt(det)
                K = c.P @ H.T @ Si
                m = c.m + K @ y
                P = (np.eye(6) - K @ H) @ c.P
                qs.append(self.pd * c.w * q)
                news.append((m, P))
            denom = self.kappa + sum(qs)
            if denom <= 0:
                continue
            for k, ci in enumerate(cand):
                if news[k] is None or qs[k] <= 0:
                    continue
                w = qs[k] / denom
                upd.append(_Comp(w, news[k][0], news[k][1]))

        self.comps = self._prune_merge(upd)
        return self._label(t, Z, feat)

    def _prune_merge(self, comps):
        comps = [c for c in comps if c.w > self.T]
        if not comps:
            return []
        comps.sort(key=lambda c: -c.w)
        M = np.array([c.m[:3] for c in comps])
        tree = cKDTree(M)                       # spatial gating for merge
        out: list[_Comp] = []
        used = np.zeros(len(comps), bool)
        for i, c in enumerate(comps):
            if used[i]:
                continue
            Pi = np.linalg.inv(c.P)
            grp = [i]
            for j in tree.query_ball_point(c.m[:3], self.merge_radius):
                if j <= i or used[j]:
                    continue
                d = comps[j].m - c.m
                if float(d @ Pi @ d) < self.U:
                    grp.append(j)
                    used[j] = True
            w = sum(comps[g].w for g in grp)
            m = sum(comps[g].w * comps[g].m for g in grp) / w
            P = sum(comps[g].w * (comps[g].P +
                    np.outer(m - comps[g].m, m - comps[g].m))
                    for g in grp) / w
            out.append(_Comp(w, m, P))
            used[i] = True
        out.sort(key=lambda c: -c.w)
        return out[:self.Jmax]

    # ---- label manager (PHD output -> persistent tracks) -----------------
    def _label(self, t, Z, feat):
        ext = [c for c in self.comps if c.w > 0.5]
        prev = list(self.labels.values())
        for lb in prev:
            lb.missed += 1
        if ext:
            E = np.array([c.m[:3] for c in ext])
            if prev:
                pm = np.array([lb.m[:3] for lb in prev])
                tree = cKDTree(pm)
                dist, idx = tree.query(E, k=1)
            else:
                dist = np.full(len(ext), 1e9)
                idx = np.zeros(len(ext), int)
            taken = set()
            for k, c in enumerate(ext):
                if prev and dist[k] < 160.0 and idx[k] not in taken:
                    lb = prev[idx[k]]
                    taken.add(idx[k])
                    lb.m, lb.P = c.m, c.P
                    lb.age += 1
                    lb.missed = 0
                    if lb.age >= self.confirm:
                        lb.status = TrackStatus.CONFIRMED
                else:
                    lb = _Label(self._next, c.m, c.P)
                    self.labels[self._next] = lb
                    self._next += 1
                self._classify(lb, Z, feat)
        # cull
        for tid in [k for k, lb in self.labels.items()
                    if lb.missed > self.max_missed]:
            del self.labels[tid]
        for lb in self.labels.values():
            if lb.missed > 0 and lb.status == TrackStatus.CONFIRMED:
                lb.status = TrackStatus.COASTING
        return self._emit(t)

    def _classify(self, lb: _Label, Z, feat):
        if len(Z) == 0:
            return
        d = np.linalg.norm(Z - lb.m[:3], axis=1)
        j = int(np.argmin(d))
        if d[j] > 180.0:
            return
        rf, md, rcs, _hint = feat[j]
        lb.obs += 1
        if rf is not None:
            lb.rf = rf
            if rf:
                lb.rf_hits += 1
        lb.md = 0.7 * lb.md + 0.3 * md if lb.md else md
        if rcs > 0:
            lb.rcs = 0.7 * lb.rcs + 0.3 * rcs if lb.rcs else rcs
        spd = float(np.linalg.norm(lb.m[3:6]))
        f = featurize(spd, lb.m[2], lb.rcs or 0.05, lb.md,
                      bool(lb.rf), lb.m[5])
        pr = MODEL.proba(f)
        lb.logp += np.log(np.array([pr[c.value] for c in CLASSES]) + 1e-9)
        lb.logp -= lb.logp.max()

    def apply_probe(self, tid: int, toward_autonomous: float = 2.5) -> None:
        """External evidence from engage-assess: a soft-kill that had no
        effect is strong evidence the track is RF-silent / autonomous."""
        lb = self.labels.get(tid)
        if lb is not None:
            lb.auto_bias += toward_autonomous

    def _guidance(self, lb: _Label) -> dict[str, float]:
        rfr = lb.rf_hits / max(lb.obs, 1)
        silent = 1.0 - rfr
        s_rf = 2.4 * rfr
        s_gnss = 1.0 * rfr + 0.4
        s_auto = 2.2 * silent + lb.auto_bias + (
            0.6 if (lb.obs >= 5 and lb.rf_hits == 0) else 0.0)
        z = np.array([s_rf, s_gnss, s_auto])
        z = np.exp(z - z.max())
        z /= z.sum()
        return {G.RF_REMOTE.value: float(z[0]),
                G.GNSS_AIDED.value: float(z[1]),
                G.AUTONOMOUS.value: float(z[2])}

    def _emit(self, t) -> list[Track]:
        out = []
        for lb in self.labels.values():
            p = np.exp(lb.logp)
            p = p / p.sum() if p.sum() else np.ones(len(CLASSES)) / len(CLASSES)
            cp = {CLASSES[i].value: float(p[i]) for i in range(len(CLASSES))}
            oc = ObjectClass(max(cp, key=cp.get))
            gp = self._guidance(lb)
            out.append(Track(
                track_id=lb.tid, t=t,
                x=lb.m[0], y=lb.m[1], z=lb.m[2],
                vx=lb.m[3], vy=lb.m[4], vz=lb.m[5],
                pos_cov=float(np.trace(lb.P[:3, :3]) / 3.0),
                hits=lb.age, misses=lb.missed, status=lb.status,
                score=lb.age - lb.missed, obj_class=oc, class_prob=cp,
                rf_linked=lb.rf, rcs=lb.rcs, micro_doppler=lb.md,
                guidance=GuidanceClass(max(gp, key=gp.get)),
                guidance_prob=gp))
        return out

    @property
    def confirmed_tracks(self):
        return [tr for tr in self._emit(0.0)
                if tr.status in (TrackStatus.CONFIRMED, TrackStatus.COASTING)]
