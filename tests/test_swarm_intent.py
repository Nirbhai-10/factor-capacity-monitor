import numpy as np

from aegis_mesh.schemas import ObjectClass, Track, TrackStatus
from aegis_mesh.sensemaking.swarm_intent import estimate_swarms


def mk(tid, x, y, vx, vy, cls=ObjectClass.UAS):
    return Track(track_id=tid, t=0.0, x=x, y=y, z=120.0, vx=vx, vy=vy,
                 vz=0.0, pos_cov=10.0, hits=6, misses=0,
                 status=TrackStatus.CONFIRMED, obj_class=cls,
                 class_prob={"uas": 0.9}, rf_linked=True)


def test_two_separated_clusters_detected():
    a = [mk(i, 3000 + 40 * i, 100 + 30 * i, -20, -3) for i in range(6)]
    b = [mk(100 + i, -3200 - 35 * i, -200 - 25 * i, 22, 5) for i in range(5)]
    sw = estimate_swarms(a + b, 0.0)
    assert len(sw) == 2
    assert {s.n_members for s in sw} == {6, 5}


def test_coherent_inbound_swarm_is_high_threat():
    a = [mk(i, 2400 + 30 * i, 50 * i, -24, 0) for i in range(8)]
    sw = estimate_swarms(a, 0.0)[0]
    assert sw.coherence > 0.9
    assert sw.closing_speed > 0
    assert np.isfinite(sw.min_time_to_impact)
    assert sw.threat_level > 0.4
    assert len(sw.hull_xy) >= 3


def test_lone_clutter_is_noise_not_swarm():
    sw = estimate_swarms([mk(1, 1000, 1000, 1, 1)], 0.0)
    assert sw == []
