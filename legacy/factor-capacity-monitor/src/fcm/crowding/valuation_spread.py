"""Valuation-spread crowding signal (Asness et al.).

For each factor, compute the ratio of the long leg's mean P/B to the short
leg's mean P/B (or analogous valuation metric). When the spread is *narrow*
(mean P/B of cheap stocks creeping up vs. expensive stocks coming down), the
factor's underlying mispricing is being arbitraged out — a sign of crowding.

We invert and percentile-rank so that high score = compressed spread = crowded.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def valuation_spread(
    weights_ts: pd.DataFrame,             # rebalance × symbols
    pb: pd.DataFrame,                     # dates × symbols
    rolling_window: int = 252 * 3,
) -> pd.Series:
    """Returns a series indexed by rebalance date.

    Score is the *percentile-rank* of `1/spread` against its own rolling
    history. So 100 = most crowded ever in the window, 0 = least crowded.
    """
    rows = {}
    for d in weights_ts.index:
        if d not in pb.index:
            d_loc = pb.index.asof(d)
        else:
            d_loc = d
        if d_loc is pd.NaT:
            continue
        w = weights_ts.loc[d]
        pb_row = pb.loc[d_loc]

        long_mask = w > 0
        short_mask = w < 0
        if long_mask.sum() == 0 or short_mask.sum() == 0:
            continue
        long_pb = pb_row[long_mask].mean()
        short_pb = pb_row[short_mask].mean()
        spread = short_pb - long_pb        # short leg is expensive, long leg is cheap → spread > 0
        if spread <= 0 or np.isnan(spread):
            continue
        rows[d] = 1.0 / spread             # crowded = compressed spread → high 1/spread

    s = pd.Series(rows).sort_index()
    if s.empty:
        return s
    # rolling percentile
    rolling_pct = s.rolling(rolling_window, min_periods=10).apply(
        lambda x: (x.rank(pct=True).iloc[-1]) * 100, raw=False
    )
    return rolling_pct.fillna((s.rank(pct=True) * 100))
