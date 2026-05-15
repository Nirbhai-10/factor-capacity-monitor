"""Holdings-overlap crowding signal.

Real implementation: parse 13F filings (US) or quarterly shareholding
patterns (India) and compute the fraction of factor names that appear in
the top-10 holdings of named hedge funds.

This module exposes a `holdings_overlap` function with a clean API; in the
synthetic / demo mode we substitute a *proxy*: the dispersion of weights
within the top 10 names of the long leg. A factor whose top names also
appear concentrated across other factors' long legs implies overlap.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def holdings_overlap(
    weights_ts: pd.DataFrame,
    other_factor_weights: list[pd.DataFrame] | None = None,
    rolling_window: int = 252 * 3,
) -> pd.Series:
    """Score: fraction of long-leg names that appear in the long leg of any
    other factor at the same rebalance.

    `other_factor_weights`: list of weights_ts DataFrames for *other* factors.
    If empty / None we fall back to a self-overlap proxy (top-10 weight share),
    which still moves with crowding because crowded factors get more concentrated.
    """
    rows = {}
    for d in weights_ts.index:
        long_names = set(weights_ts.loc[d][weights_ts.loc[d] > 0].index)
        if not long_names:
            continue
        if other_factor_weights:
            overlapped = set()
            for other in other_factor_weights:
                if d in other.index:
                    other_long = set(other.loc[d][other.loc[d] > 0].index)
                    overlapped |= long_names & other_long
            score = len(overlapped) / len(long_names)
        else:
            # Fallback: top-10 weight share of the long leg
            ws = weights_ts.loc[d][weights_ts.loc[d] > 0].sort_values(ascending=False)
            score = float(ws.iloc[: min(10, len(ws))].sum() / ws.sum()) if ws.sum() > 0 else 0
        rows[d] = score

    s = pd.Series(rows).sort_index()
    if s.empty:
        return s
    pct = s.rolling(rolling_window, min_periods=10).apply(
        lambda x: x.rank(pct=True).iloc[-1] * 100, raw=False
    )
    return pct.fillna((s.rank(pct=True) * 100))
