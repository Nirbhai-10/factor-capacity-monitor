from aegis_mesh.orchestrator.wta import Effector, Orchestrator
from aegis_mesh.schemas import EngagementState, SwarmObject, Track


def _track(tid, x, rf=True):
    return Track(track_id=tid, t=0.0, x=x, y=0.0, z=100.0,
                 vx=-20.0, vy=0.0, vz=0.0, pos_cov=10.0, hits=5, misses=0,
                 confirmed=True, rf_linked=rf)


def _swarm(ids):
    return SwarmObject(swarm_id=0, t=0.0, member_track_ids=ids,
                       centroid=(800.0, 0.0, 100.0), n_members=len(ids),
                       coherence=0.9, closing_speed=20.0,
                       min_time_to_impact=40.0, threat_level=0.8)


def test_commercial_build_suppresses_mitigation():
    tracks = [_track(i, 800 + i) for i in range(5)]
    orch = Orchestrator(mitigation_authorized=False)
    r = orch.assign([_swarm([t.track_id for t in tracks])], tracks, 0.0)
    assert r.orders
    assert all(o.state == EngagementState.SUPPRESSED_NO_AUTHORITY
               for o in r.orders)


def test_area_effector_drives_down_cost_per_kill():
    tracks = [_track(i, 800 + i * 5) for i in range(20)]
    orch = Orchestrator(mitigation_authorized=True)
    r = orch.assign([_swarm([t.track_id for t in tracks])], tracks, 0.0)
    assert r.n_engaged == 20
    # 20 co-located threats neutralized by area bursts << 20x point cost
    assert r.total_cost < 20 * 1500.0
    assert r.total_cost / r.n_engaged < 50.0


def test_cyber_takeover_requires_rf_link():
    e = Effector("c", "soft_kill_cyber", 5.0, magazine=10,
                 requires_rf_link=True)
    assert not e.applicable(_track(1, 500, rf=False), 500.0)
    assert e.applicable(_track(2, 500, rf=True), 500.0)
