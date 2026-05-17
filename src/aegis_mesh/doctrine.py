"""Operator doctrine — make the system configured, not hardcoded.

A YAML file defines the ROE, the defended-asset keep-out, the effector
inventory and the attacker economics. Loaded at start; falls back to the
built-in defaults if absent. This is what turns a simulator into an
operated tool.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .orchestrator.wta import Effector, default_effector_suite

DEFAULT = Path(__file__).resolve().parents[2] / "doctrine" / "default.yaml"


@dataclass
class Doctrine:
    require_human: bool = False
    auto_engage_tti: float = 12.0
    keepout_m: float = 250.0
    engage_threat: float = 0.30
    attacker_unit_cost: float = 2000.0          # $ per attacking drone
    effectors: list[Effector] = field(default_factory=default_effector_suite)

    @staticmethod
    def load(path: str | Path | None = None) -> "Doctrine":
        p = Path(path) if path else DEFAULT
        if not p.exists():
            return Doctrine()
        d = yaml.safe_load(p.read_text()) or {}
        roe = d.get("roe", {})
        effs = [Effector(**e) for e in d["effectors"]] if d.get("effectors") \
            else default_effector_suite()
        return Doctrine(
            require_human=bool(roe.get("require_human", False)),
            auto_engage_tti=float(roe.get("auto_engage_tti", 12.0)),
            keepout_m=float(d.get("keepout_m", 250.0)),
            engage_threat=float(roe.get("engage_threat", 0.30)),
            attacker_unit_cost=float(d.get("attacker_unit_cost", 2000.0)),
            effectors=effs)
