"""Heterogeneous-autonomy threat model: guidance-conditioned defeat,
engage-assess-reengage escalation, OSPA."""

import numpy as np

from aegis_mesh.engine import Engine
from aegis_mesh.metrics.ospa import ospa
from aegis_mesh.orchestrator.effectiveness import (base_pkill, expected_pkill,
                                                   is_soft_kill)
from aegis_mesh.schemas import GuidanceClass as G
from aegis_mesh.sim.scenarios import layered_raid, single_drone


def test_soft_kill_useless_vs_autonomous_hard_kill_agnostic():
    assert base_pkill("soft_kill_cyber", G.RF_REMOTE) > 0.9
    assert base_pkill("soft_kill_cyber", G.AUTONOMOUS) == 0.0
    assert base_pkill("gnss_spoof", G.AUTONOMOUS) == 0.0
    assert base_pkill("hpm", G.AUTONOMOUS) > 0.8          # generation-agnostic
    assert base_pkill("optical_dazzle", G.AUTONOMOUS) > \
        base_pkill("optical_dazzle", G.RF_REMOTE)         # counter-autonomy


def test_expected_pkill_marginalises_estimate():
    autonomous = {"rf_remote": 0.0, "gnss_aided": 0.0, "autonomous": 1.0}
    rf = {"rf_remote": 1.0, "gnss_aided": 0.0, "autonomous": 0.0}
    assert expected_pkill("soft_kill_cyber", autonomous) < 0.05
    assert expected_pkill("soft_kill_cyber", rf) > 0.9
    assert is_soft_kill("gnss_spoof") and not is_soft_kill("hpm")


def test_layered_raid_defeats_the_autonomous_contingent():
    """The drones the older RF/GNSS framework cannot touch must still be
    neutralised by the layered framework, with visible escalation."""
    m = Engine(layered_raid(seed=0), seed=0, tracker="gmphd").run()
    assert m.n_autonomous >= 30                            # real RF-silent set
    assert m.autonomous_neutralized == m.n_autonomous      # all defeated
    assert m.escalations > 0                               # engage-assess fired
    assert m.leakage_rate == 0.0
    assert m.audit_ok


def test_rf_drone_needs_no_escalation():
    m = Engine(single_drone(seed=0), seed=0, tracker="gmphd").run()
    assert m.n_autonomous == 0
    assert m.escalations == 0                               # soft-kill worked
    assert m.n_neutralized == 1


def test_ospa_properties():
    A = np.array([[0.0, 0.0], [100.0, 0.0]])
    assert ospa(A, A)[0] == 0.0                             # identical sets
    far = np.array([[0.0, 0.0], [100.0, 0.0], [9000.0, 0.0]])
    val, loc, card = ospa(A, far, c=150.0, p=2.0)
    assert card > 0 and val > 0                             # cardinality error
    # one big localisation error is capped at c
    v2, _, _ = ospa(np.array([[5000.0, 0.0]]), np.array([[0.0, 0.0]]),
                     c=150.0)
    assert abs(v2 - 150.0) < 1e-6
