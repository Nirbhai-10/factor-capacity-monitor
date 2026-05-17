
from aegis_mesh.pipeline import run
from aegis_mesh.sim.scenarios import (coordinated_formation,
                                      mixed_dark_saturation, single_drone)


def test_single_drone_neutralized_and_audit_intact():
    m = run(single_drone(), mitigation_authorized=True, seed=0)
    assert m.audit_ok
    assert m.detection_recall >= 0.9
    assert m.n_neutralized >= 1
    assert m.leakage_rate == 0.0


def test_commercial_build_does_not_neutralize():
    m = run(single_drone(), mitigation_authorized=False, seed=0)
    assert m.audit_ok
    assert m.n_neutralized == 0  # detect/track-only: no effect applied


def test_saturation_mostly_contained():
    m = run(mixed_dark_saturation(), mitigation_authorized=True, seed=0)
    assert m.audit_ok
    assert m.detection_recall >= 0.8
    assert m.leakage_rate <= 0.25
    # economics moat: cheap per-kill even against a 30-drone raid
    assert 0 < m.sim_cost_per_kill < 2000.0


def test_formation_detected_as_swarm():
    m = run(coordinated_formation(), mitigation_authorized=True, seed=0)
    assert m.audit_ok
    assert m.n_neutralized >= 6
