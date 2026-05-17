import numpy as np

from aegis_mesh.fusion.tracker import Tracker
from aegis_mesh.schemas import Detection, ObjectClass, SensorKind


def _det(t, x, y, z, std=6.0, kind=SensorKind.RADAR):
    return Detection(t=t, sensor_id="r", sensor_kind=kind, x=x, y=y, z=z,
                     pos_std=std, class_hint=ObjectClass.UAS)


def test_single_target_confirms_and_estimates_velocity():
    tr = Tracker(confirm_hits=3)
    rng = np.random.default_rng(0)
    pos = np.array([1000.0, 500.0, 100.0])
    vel = np.array([-20.0, -10.0, 0.0])
    last = None
    for k in range(12):
        pos = pos + vel * 0.5
        d = _det(k * 0.5, *(pos + rng.normal(0, 4, 3)))
        tracks = tr.step([d], k * 0.5, 0.5)
        if tracks:
            last = max(tracks, key=lambda t: t.hits)
    assert last is not None and last.confirmed
    assert abs(last.vx - (-20.0)) < 6.0
    assert abs(last.vy - (-10.0)) < 6.0
    assert last.obj_class == ObjectClass.UAS


def test_clutter_does_not_confirm():
    tr = Tracker(confirm_hits=3, max_misses=2)
    rng = np.random.default_rng(1)
    for k in range(15):
        d = _det(k * 0.5, rng.uniform(-3000, 3000),
                 rng.uniform(-3000, 3000), rng.uniform(20, 300), std=40.0)
        tr.step([d], k * 0.5, 0.5)
    assert all(not t.confirmed for t in tr.confirmed_tracks)
