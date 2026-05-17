import numpy as np

from aegis_mesh.orchestrator.audit import AuditLog
from aegis_mesh.orchestrator.wta import EngagementManager
from aegis_mesh.schemas import (EngagementState, ObjectClass, SwarmObject,
                                Track, TrackStatus)


def trk(tid, x, y=0.0, rf=True, cls=ObjectClass.UAS):
    return Track(track_id=tid, t=0.0, x=x, y=y, z=110.0, vx=-22.0, vy=0.0,
                 vz=0.0, pos_cov=9.0, hits=6, misses=0,
                 status=TrackStatus.CONFIRMED, obj_class=cls,
                 class_prob={"uas": 0.95}, rf_linked=rf)


def swarm(ids, threat=0.8, tti=40.0):
    return SwarmObject(swarm_id=0, t=0.0, member_track_ids=ids,
                       centroid=(900.0, 0.0, 110.0), hull_xy=[(0, 0)],
                       n_members=len(ids), coherence=0.9,
                       formation_tightness=0.8, axis_of_attack=(-1.0, 0.0),
                       closing_speed=22.0, min_time_to_impact=tti,
                       median_time_to_impact=tti, has_mothership=False,
                       class_confidence=0.95, threat_level=threat)


def test_commercial_build_suppresses_all_mitigation():
    tr = [trk(i, 1500 + i) for i in range(4)]
    mgr = EngagementManager(mitigation_authorized=False)
    r = mgr.propose([swarm([t.track_id for t in tr])], tr, 0.0)
    assert r.orders
    assert all(o.state == EngagementState.SUPPRESSED_NO_AUTHORITY
               for o in r.orders)


def test_human_on_the_loop_queues_then_approves():
    tr = [trk(0, 2500.0)]
    mgr = EngagementManager(mitigation_authorized=True, require_human=True,
                            auto_engage_tti=5.0)
    r = mgr.propose([swarm([0], tti=60.0)], tr, 0.0)
    o = r.orders[0]
    assert o.state == EngagementState.PENDING_APPROVAL
    assert o.order_id in mgr.pending
    assert mgr.approve(o.order_id, 1.0)
    assert o.state == EngagementState.EXECUTING


def test_short_fuse_auto_engages():
    tr = [trk(0, 400.0)]
    mgr = EngagementManager(mitigation_authorized=True, require_human=True,
                            auto_engage_tti=12.0)
    r = mgr.propose([swarm([0], tti=6.0)], tr, 0.0)
    assert r.orders[0].state == EngagementState.EXECUTING


def test_area_effector_economics_beats_point_on_dense_cluster():
    # 12 tightly co-located inbound threats
    tr = [trk(i, 1800 + (i % 4) * 30, (i // 4) * 30) for i in range(12)]
    mgr = EngagementManager(mitigation_authorized=True, area_min_batch=3)
    r = mgr.propose([swarm([t.track_id for t in tr])], tr, 0.0)
    kinds = {o.effector_kind for o in r.orders}
    assert "hpm" in kinds
    assert r.committed_cost / 12 < 60.0          # cheap per kill


def test_pkill_resolution_and_audit_chain():
    tr = [trk(0, 1200.0)]
    audit = AuditLog()
    mgr = EngagementManager(mitigation_authorized=True, audit=audit,
                            flight_time=2.0)
    mgr.propose([swarm([0], tti=8.0)], tr, 0.0)
    res = mgr.resolve_due(5.0, np.random.default_rng(0))
    assert len(res) == 1
    order, hit = res[0]
    assert order.state in (EngagementState.NEUTRALIZED,
                           EngagementState.MISSED)
    assert audit.verify()
