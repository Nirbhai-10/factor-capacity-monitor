"""Factory: build a FactorSignal from a config block."""
from __future__ import annotations

from .momentum import MomentumFactor
from .value import ValueFactor
from .quality import QualityFactor
from .low_vol import LowVolFactor
from .base import FactorSignal


_REGISTRY = {
    "momentum": MomentumFactor,
    "value": ValueFactor,
    "quality": QualityFactor,
    "low_vol": LowVolFactor,
}


def build_factor(name: str, cfg) -> FactorSignal:
    cls = _REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"Unknown factor '{name}'. Known: {list(_REGISTRY)}")

    params = {}
    if name == "momentum":
        params = {
            "lookback_days": cfg.factors.momentum.lookback_days,
            "skip_days": cfg.factors.momentum.skip_days,
        }
    elif name == "low_vol":
        params = {"window_days": cfg.factors.low_vol.window_days}
    return cls(**params)
