"""Battle-grade algorithm tests: IMM, GM-PHD, TDOA/AOA, auction, TEWA."""

import numpy as np
from scipy.optimize import linear_sum_assignment

from aegis_mesh.fusion.gmphd import GMPHDTracker
from aegis_mesh.fusion.imm import IMM
from aegis_mesh.fusion.localization import aoa_triangulate, chan_ho_tdoa
from aegis_mesh.orchestrator.auction import auction_assign
from aegis_mesh.schemas import Detection, MeasKind, SensorKind
from aegis_mesh.sensemaking.threat_eval import evaluate
from aegis_mesh.schemas import ObjectClass, Track, TrackStatus


# ---- IMM ------------------------------------------------------------------
def test_imm_beats_cv_on_a_turning_target():
    """On a coordinated turn, IMM RMSE must clearly beat a single CV KF
    and its turn models must carry the mode probability."""
    from aegis_mesh.fusion.models import F_cv, H_POS, Q_disc
    rng = np.random.default_rng(0)
    dt, w = 0.5, 0.12
    s = np.array([0.0, 60.0, 0.0, 0.0])                 # x,vx,y,vy
    R = np.diag([9.0, 9.0])
    imm = IMM(s.copy(), np.diag([100.0, 100, 100, 100]))
    xcv = s.copy().astype(float)
    Pcv = np.eye(4) * 100.0
    e_imm = e_cv = 0.0
    max_turn = 0.0
    for _ in range(60):
        c, sn = np.cos(w * dt), np.sin(w * dt)
        vx, vy = s[1], s[3]
        s = np.array([s[0] + (c * vx - sn * vy) * dt, c * vx - sn * vy,
                      s[2] + (sn * vx + c * vy) * dt, sn * vx + c * vy])
        z = np.array([s[0], s[2]]) + rng.normal(0, 3, 2)
        imm.step(z, dt, R)
        max_turn = max(max_turn, 1.0 - imm.mu[0])
        F = F_cv(dt); xcv = F @ xcv; Pcv = F @ Pcv @ F.T + Q_disc(dt, 6.0)
        y = z - H_POS @ xcv; S = H_POS @ Pcv @ H_POS.T + R
        K = Pcv @ H_POS.T @ np.linalg.inv(S)
        xcv = xcv + K @ y; Pcv = (np.eye(4) - K @ H_POS) @ Pcv
        e_imm += np.hypot(*(imm.estimate[[0, 2]] - [s[0], s[2]]))
        e_cv += np.hypot(*(xcv[[0, 2]] - [s[0], s[2]]))
    assert e_imm < 0.9 * e_cv
    assert max_turn > 0.5 and imm.maneuvering


# ---- TDOA / AOA -----------------------------------------------------------
def test_aoa_triangulation_recovers_emitter():
    sites = np.array([[1600.0, 0.0], [-1600.0, 0.0], [0.0, 1600.0]])
    true = np.array([900.0, 1400.0])
    az = np.arctan2(true[1] - sites[:, 1], true[0] - sites[:, 0])
    xy, P = aoa_triangulate(sites, az, np.full(3, 0.01))
    assert np.linalg.norm(xy - true) < 60.0


def test_chan_ho_tdoa_recovers_emitter():
    sites = np.array([[1600., 0.], [-1600., 0.], [0., 1600.], [0., -1600.]])
    true = np.array([700.0, 1100.0])
    d = np.linalg.norm(sites - true, axis=1)
    r = d[1:] - d[0]
    xy, _ = chan_ho_tdoa(sites, r)
    assert np.linalg.norm(xy - true) < 50.0


# ---- Bertsekas auction ----------------------------------------------------
def test_auction_matches_hungarian_optimum():
    rng = np.random.default_rng(3)
    for _ in range(20):
        n = rng.integers(3, 12)
        C = rng.uniform(0, 100, (n, n))
        a = auction_assign(-C)
        ri, ci = linear_sum_assignment(C)
        opt = C[ri, ci].sum()
        got = sum(C[i, a[i]] for i in range(n) if a[i] >= 0)
        assert len(set(a)) == n                       # valid permutation
        assert abs(got - opt) <= 1e-6 * opt + 1.0     # optimal


# ---- TEWA -----------------------------------------------------------------
def test_tewa_inbound_scores_higher_than_outbound():
    inbound = Track(1, 0, 2000, 0, 120, -40, 0, 0, 9, 6, 0,
                    TrackStatus.CONFIRMED, obj_class=ObjectClass.UAS,
                    class_prob={"uas": 0.95})
    outbound = Track(2, 0, 2000, 0, 120, 40, 0, 0, 9, 6, 0,
                     TrackStatus.CONFIRMED, obj_class=ObjectClass.UAS,
                     class_prob={"uas": 0.95})
    si, so = evaluate(inbound), evaluate(outbound)
    assert si.score > so.score
    assert si.cpa < inbound.x and np.isfinite(si.tbh)
    assert not np.isfinite(so.tbh)


# ---- GM-PHD ---------------------------------------------------------------
def _cart(t, p, sid="radar-N", std=6.0):
    return Detection(t=t, sensor_id=sid, sensor_kind=SensorKind.RADAR,
                     meas_kind=MeasKind.CARTESIAN, site=(0.0, 1200.0, 12.0),
                     x=p[0], y=p[1], z=p[2], pos_std=std, rf_linked=True,
                     micro_doppler=0.85, rcs=0.02,
                     class_hint=ObjectClass.UAS)


def test_gmphd_tracks_three_targets_through_clutter():
    rng = np.random.default_rng(1)
    tr = GMPHDTracker()
    tracks0 = np.array([[1500., 400, 120], [1480, -300, 110],
                        [-1600, 200, 130]], float)
    vel = np.array([[-22., -4, 0], [-20, 6, 0], [24, -3, 0]])
    out = []
    for k in range(16):
        tracks0 += vel * 0.5
        dets = [_cart(k * 0.5, p + rng.normal(0, 4, 3)) for p in tracks0]
        for _ in range(3):                              # clutter
            dets.append(_cart(k * 0.5,
                        rng.uniform(-3000, 3000, 3), std=40.0))
        out = tr.step(dets, k * 0.5, 0.5)
    conf = [t for t in out if t.confirmed]
    assert 3 <= len(conf) <= 5                          # 3 targets, no blow-up
