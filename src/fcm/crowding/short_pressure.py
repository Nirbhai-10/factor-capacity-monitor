"""Short-interest crowding signal.

A factor whose short leg has high short interest is exposed to short-squeeze
risk and is paying high borrow. This signal is the weighted-average SI on the
short leg, percentile-ranked.
"""
from __future__ import annotations

import pandas as pd


def short_interest_pressure(
    weights_ts: pd.DataFrame,        # rebalance × symbols
    short_interest: pd.DataFrame,    # dates × symbols, fraction of float
    rolling_window: int = 252 * 3,
) -> pd.Series:
    rows = {}
    for d in weights_ts.index:
        if d not in short_interest.index:
            d_loc = short_interest.index.asof(d)
        else:
            d_loc = d
        if d_loc is pd.NaT:
            continue
        w = weights_ts.loc[d]
        si_row = short_interest.loc[d_loc]
        short_w = -w.clip(upper=0)        # positive on the short leg
        if short_w.sum() == 0:
            continue
        rows[d] = float((short_w * si_row.reindex(short_w.index).fillna(0)).sum() / short_w.sum())

    s = pd.Series(rows).sort_index()
    if s.empty:
        return s
    pct = s.rolling(rolling_window, min_periods=10).apply(
        lambda x: x.rank(pct=True).iloc[-1] * 100, raw=False
    )
    return pct.fillna((s.rank(pct=True) * 100))
