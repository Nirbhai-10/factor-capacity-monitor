from aegis_mesh.engine import Engine
from aegis_mesh.mesh import EventBus
from aegis_mesh.sim.scenarios import (coordinated_formation,
                                      mixed_dark_saturation, single_drone)


def test_single_drone_clean_kill():
    m = Engine(single_drone(), seed=0).run()
    assert m.audit_ok and m.audit_records > 5
    assert m.detection_recall >= 0.95
    assert m.n_neutralized >= 1 and m.n_leaked == 0


def test_commercial_build_detects_but_does_not_engage():
    m = Engine(single_drone(), seed=0, mitigation_authorized=False).run()
    assert m.detection_recall >= 0.95
    assert m.n_neutralized == 0


def test_saturation_contained_and_cheap():
    m = Engine(mixed_dark_saturation(), seed=0).run()
    assert m.audit_ok
    assert m.detection_recall >= 0.85
    assert m.leakage_rate <= 0.15
    assert 0 < m.sim_cost_per_kill < 1500


def test_node_loss_degrades_gracefully():
    base = Engine(coordinated_formation(), seed=0).run()
    deg = Engine(coordinated_formation(), seed=0,
                 node_loss={10.0: "radar-N"}).run()
    assert deg.active_sites == base.active_sites - 1
    assert deg.audit_ok
    assert deg.detection_recall >= 0.80          # mesh still tracks


def test_bus_receives_frames():
    bus = EventBus()
    got = []
    bus.subscribe("frame", lambda f: got.append(f))
    Engine(single_drone(), seed=0, bus=bus).run()
    assert len(got) > 10 and "metrics" in got[-1]


def test_bus_isolates_faulty_subscriber():
    bus = EventBus()
    bus.subscribe("frame", lambda f: 1 / 0)      # misbehaving node
    m = Engine(single_drone(), seed=0, bus=bus).run()
    assert m.audit_ok and bus.dropped > 0        # fault contained
