"""Back-compat: pipeline.run thin wrapper still returns engine Metrics."""

from aegis_mesh.pipeline import run
from aegis_mesh.sim.scenarios import single_drone


def test_pipeline_run_wrapper():
    m = run(single_drone(), mitigation_authorized=True, seed=0)
    assert m.audit_ok
    assert m.n_neutralized >= 1
    assert hasattr(m, "sim_cost_per_kill")
