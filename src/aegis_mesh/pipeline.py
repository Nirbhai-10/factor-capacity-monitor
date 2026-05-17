"""Back-compat thin wrapper over Engine (headless run -> metrics)."""

from __future__ import annotations

from .engine import Engine, Metrics
from .sim.scenarios import Scenario


def run(scenario: Scenario, *, mitigation_authorized: bool = True,
        require_human: bool = False, seed: int = 0,
        node_loss: dict | None = None) -> Metrics:
    return Engine(scenario, seed=seed,
                  mitigation_authorized=mitigation_authorized,
                  require_human=require_human,
                  node_loss=node_loss).run()
