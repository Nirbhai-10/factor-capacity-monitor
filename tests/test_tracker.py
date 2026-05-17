import numpy as np

from aegis_mesh.fusion.tracker import Tracker
from aegis_mesh.schemas import Detection, MeasKind, SensorKind


def cart(t, p, std=6.0, **kw):
    return Detection(t=t, sensor_id="r", sensor_kind=SensorKind.RADAR,
                     meas_kind=MeasKind.CARTESIAN, site=(0.0, 1200.0, 12.0),
                     x=p[0], y=p[1], z=p[2], pos_std=std, **kw)


def bearing(t, p, site, ang=0.016):
    rel = np.array(p) - np.array(site)
    return Detection(t=t, sensor_id="rf", sensor_kind=SensorKind.PASSIVE_RF,
                     meas_kind=MeasKind.BEARING, site=site,
                     az=float(np.arctan2(rel[1], rel[0])),
                     el=float(np.arctan2(rel[2], np.hypot(rel[0], rel[1]))),
                     ang_std=ang, rf_linked=True)


def test_cartesian_track_confirms_and_estimates_velocity():
    tr = Tracker()
    rng = np.random.default_rng(0)
    p = np.array([1500.0, 400.0, 120.0])
    v = np.array([-22.0, -8.0, 0.0])
    last = None
    for k in range(14):
        p = p + v * 0.5
        out = tr.step([cart(k * 0.5, p + rng.normal(0, 4, 3))], k * 0.5, 0.5)
        if out:
            last = max(out, key=lambda x: x.hits)
    assert last.confirmed
    assert abs(last.vx + 22.0) < 6 and abs(last.vy + 8.0) < 6


def test_bearing_only_mesh_triangulates():
    """Two RF sites, bearing-only: the EKF must converge in range."""
    tr = Tracker()
    sA, sB = (1600.0, 0.0, 25.0), (-1600.0, 0.0, 25.0)
    p = np.array([900.0, 1400.0, 130.0])
    v = np.array([-10.0, -16.0, 0.0])
    seed_pos = p + np.array([300, -250, 10])
    tr.step([cart(0.0, seed_pos, std=60.0)], 0.0, 0.5)
    for k in range(1, 30):
        p = p + v * 0.5
        tr.step([bearing(k * 0.5, p, sA), bearing(k * 0.5, p, sB)],
                k * 0.5, 0.5)
    est = tr.confirmed_tracks[0]
    assert np.hypot(est.x - p[0], est.y - p[1]) < 220.0


def test_clutter_does_not_confirm():
    tr = Tracker()
    rng = np.random.default_rng(2)
    for k in range(16):
        tr.step([cart(k * 0.5, rng.uniform(-3000, 3000, 3), std=45.0)],
                k * 0.5, 0.5)
    assert all(not t.confirmed for t in tr.confirmed_tracks)


def test_scales_to_many_contacts_in_one_step():
    tr = Tracker()
    rng = np.random.default_rng(3)
    pts = rng.uniform(-4000, 4000, (600, 3))
    dets = [cart(0.0, p, std=8.0) for p in pts]
    out = tr.step(dets, 0.0, 0.5)
    assert len(out) >= 550        # near 1:1, no association blow-up
