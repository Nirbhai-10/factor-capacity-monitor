"""Capacity-zone classifier."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Zone:
    name: str         # safe | caution | red
    color: str

ZONE_SAFE = Zone("safe", "#2ca02c")
ZONE_CAUTION = Zone("caution", "#ff9f40")
ZONE_RED = Zone("red", "#d62728")


def classify_zone(net_ir: float, max_exec_days: float, max_participation: float, cfg) -> Zone:
    safe = cfg.capacity.zones.safe
    caution = cfg.capacity.zones.caution

    if (net_ir >= safe.min_net_ir
            and max_exec_days <= safe.max_exec_days
            and max_participation < safe.max_participation):
        return ZONE_SAFE
    if (net_ir >= caution.min_net_ir
            and max_exec_days <= caution.max_exec_days
            and max_participation < caution.max_participation):
        return ZONE_CAUTION
    return ZONE_RED
