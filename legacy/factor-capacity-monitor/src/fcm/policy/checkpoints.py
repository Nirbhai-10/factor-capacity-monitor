"""Capacity-utilisation checkpoints.

A scaling AUM should hit operational checkpoints — defaults at 50%, 75%, 90%
of safe capacity. Each checkpoint gives the PM a rule:
  50%: stay the course, no policy change
  75%: raise no-trade buffer to mid value, slow rebalance one tier
  90%: close to new flows, raise buffer to top, switch to monthly rebalance
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CapacityCheckpoint:
    pct_of_safe: float
    aum: float
    rule: str


def compute_checkpoints(
    safe_capacity: float,
    pct_levels: list[float],
) -> list[CapacityCheckpoint]:
    rules = {
        0.50: "Routine — keep current rebalance + buffer.",
        0.75: "Raise no-trade buffer to 100bps, downshift rebalance by one tier.",
        0.90: "Soft-close to new flows. Raise buffer to 200bps, switch to monthly rebalance.",
    }
    out = []
    for p in pct_levels:
        rule = rules.get(p, f"At {int(p*100)}% — review.")
        out.append(CapacityCheckpoint(pct_of_safe=p, aum=p * safe_capacity, rule=rule))
    return out
