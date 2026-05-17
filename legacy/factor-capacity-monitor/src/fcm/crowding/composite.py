"""Composite crowding score (0-100) per factor.

Weighted average of six component scores (each percentile-ranked vs own
history, so all on a common 0-100 scale):
  - valuation_spread (Asness deep-value)
  - alpha_decay (rolling-IR slope)
  - short_interest_pressure (Drechsler)
  - comomentum (Lou-Polk)
  - holdings_overlap (Sias proxy)
  - internal_liquidity_footprint (legacy)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .alpha_decay import rolling_alpha_decay
from .comomentum import comomentum
from .holdings_overlap import holdings_overlap
from .internal_footprint import internal_liquidity_footprint
from .short_pressure import short_interest_pressure
from .valuation_spread import valuation_spread


@dataclass
class CrowdingScore:
    factor_name: str
    timeseries: pd.DataFrame              # rebalance × component score
    composite: pd.Series                  # rebalance × score
    latest: dict[str, float]              # most recent component values
    latest_composite: float
    alert_level: str                      # red | amber | green


def composite_crowding_score(
    factor_name: str,
    weights_ts: pd.DataFrame,
    panel,
    daily_returns: pd.Series,
    base_aum: float,
    weights: dict[str, float],
    other_factor_weights: list[pd.DataFrame] | None = None,
    alert_thresholds: tuple[float, float] = (50.0, 75.0),
) -> CrowdingScore:
    """Compute composite score per rebalance date.

    `weights` is the cfg.crowding.weights block (mapping component → weight).
    `alert_thresholds` = (amber, red). Below amber = green.
    """
    val = valuation_spread(weights_ts, panel.pb)
    decay = rolling_alpha_decay(daily_returns).reindex(weights_ts.index, method="ffill")
    si = short_interest_pressure(weights_ts, panel.short_interest)
    com = comomentum(weights_ts, panel.close.pct_change())
    overlap = holdings_overlap(weights_ts, other_factor_weights)
    foot = internal_liquidity_footprint(weights_ts, panel.adv(20), base_aum)

    df = pd.DataFrame({
        "valuation_spread": val,
        "alpha_decay": decay,
        "short_interest": si,
        "comomentum": com,
        "holdings_overlap": overlap,
        "internal_footprint": foot,
    }).reindex(weights_ts.index)

    df = df.fillna(50.0)        # neutral when not enough history yet

    w_total = sum(weights.values())
    composite = sum(df[c] * weights.get(c, 0) for c in df.columns) / max(w_total, 1e-9)
    composite = composite.reindex(weights_ts.index).ffill().fillna(50.0)

    latest = df.iloc[-1].to_dict() if len(df) > 0 else {c: 50.0 for c in df.columns}
    latest_comp = float(composite.iloc[-1]) if len(composite) > 0 else 50.0

    amber, red = alert_thresholds
    if latest_comp >= red:
        level = "red"
    elif latest_comp >= amber:
        level = "amber"
    else:
        level = "green"

    return CrowdingScore(
        factor_name=factor_name,
        timeseries=df,
        composite=composite,
        latest=latest,
        latest_composite=latest_comp,
        alert_level=level,
    )
