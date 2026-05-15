"""Internal liquidity-footprint crowding signal.

Inherited (and simplified) from the prior in-house prototype: how much of the
strategy's traded ADV the factor consumes at base AUM. Higher footprint =
internally crowded.
"""
from __future__ import annotations

import pandas as pd


def internal_liquidity_footprint(
    weights_ts: pd.DataFrame,
    adv_panel: pd.DataFrame,         # dates × symbols, $ ADV
    base_aum: float,
    rolling_window: int = 252 * 3,
) -> pd.Series:
    """For each rebalance, footprint = sum(|weight × AUM|) / sum(ADV of those names)."""
    rows = {}
    prev_w = None
    for d in weights_ts.index:
        w = weights_ts.loc[d]
        if d not in adv_panel.index:
            d_loc = adv_panel.index.asof(d)
        else:
            d_loc = d
        if d_loc is pd.NaT:
            continue
        adv_row = adv_panel.loc[d_loc]
        # Footprint of the trade = |Δw|
        if prev_w is None:
            trade_w = w
        else:
            trade_w = w - prev_w.reindex(w.index).fillna(0)
        prev_w = w
        active = trade_w.abs() > 0
        if active.sum() == 0:
            continue
        notional = (trade_w[active].abs() * base_aum)
        denom = adv_row.reindex(notional.index).fillna(0).sum()
        if denom <= 0:
            continue
        rows[d] = float(notional.sum() / denom)

    s = pd.Series(rows).sort_index()
    if s.empty:
        return s
    pct = s.rolling(rolling_window, min_periods=10).apply(
        lambda x: x.rank(pct=True).iloc[-1] * 100, raw=False
    )
    return pct.fillna((s.rank(pct=True) * 100))
