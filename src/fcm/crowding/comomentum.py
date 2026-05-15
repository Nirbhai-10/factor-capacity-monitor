"""Comomentum (Lou-Polk 2013): pairwise return correlation of long-leg names.

When the long-leg names move increasingly in lock-step, that's a sign that
the same set of arbitrageurs is driving them. Quantitative implementation:

    For each rebalance date, take the long-leg names. Compute pairwise
    correlations of their daily returns over the past `window` days. Average
    the upper-triangle. Percentile-rank against history.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def comomentum(
    weights_ts: pd.DataFrame,        # rebalance × symbols
    daily_returns: pd.DataFrame,     # dates × symbols
    window: int = 60,
    rolling_pct_window: int = 252 * 3,
) -> pd.Series:
    rows = {}
    for d in weights_ts.index:
        long_names = weights_ts.loc[d][weights_ts.loc[d] > 0].index
        if len(long_names) < 5:
            continue
        # Use up to `window` days ending at d
        if d not in daily_returns.index:
            d_loc = daily_returns.index.asof(d)
        else:
            d_loc = d
        if d_loc is pd.NaT:
            continue
        end_pos = daily_returns.index.get_loc(d_loc)
        start_pos = max(0, end_pos - window)
        sub = daily_returns.iloc[start_pos:end_pos][long_names].dropna(how="any", axis=1)
        if sub.shape[1] < 5 or sub.shape[0] < window // 2:
            continue
        corr = sub.corr().values
        upper = corr[np.triu_indices_from(corr, k=1)]
        rows[d] = float(np.nanmean(upper))

    s = pd.Series(rows).sort_index()
    if s.empty:
        return s
    pct = s.rolling(rolling_pct_window, min_periods=10).apply(
        lambda x: x.rank(pct=True).iloc[-1] * 100, raw=False
    )
    return pct.fillna((s.rank(pct=True) * 100))
