"""Rolling alpha-decay crowding signal.

A persistently declining trailing IR is *the* signature of a factor whose
edge is being arbitraged away. We measure the slope of rolling-1y IR over
the past `decay_window` days; a steeper negative slope = more crowded.
Score is percentile-rank of (-slope) against rolling history.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def rolling_alpha_decay(
    daily_returns: pd.Series,
    rolling_ir_window: int = 252,
    decay_window: int = 252 * 2,
) -> pd.Series:
    """Returns daily series of crowding score (0-100)."""
    rolling_ir = (
        daily_returns.rolling(rolling_ir_window, min_periods=rolling_ir_window // 2).mean()
        / daily_returns.rolling(rolling_ir_window, min_periods=rolling_ir_window // 2).std()
    ) * np.sqrt(252)

    # Slope of rolling_ir over decay_window via simple OLS on (t, IR)
    def _slope(y: np.ndarray) -> float:
        if np.isnan(y).any():
            return np.nan
        x = np.arange(len(y))
        x_mean = x.mean()
        y_mean = y.mean()
        denom = ((x - x_mean) ** 2).sum()
        if denom == 0:
            return 0
        return ((x - x_mean) * (y - y_mean)).sum() / denom

    slopes = rolling_ir.rolling(decay_window, min_periods=decay_window // 2).apply(_slope, raw=True)

    # Higher crowding = more negative slope. Take -slope, then percentile-rank.
    decay = -slopes
    pct = decay.rank(pct=True) * 100
    return pct.fillna(50.0)
