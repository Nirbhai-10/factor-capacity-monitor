"""Bid-ask spread estimation from OHLC.

Implements the Corwin-Schultz (2012, JF) high-low estimator:

    β = E[(ln(H_t/L_t))^2 + (ln(H_{t+1}/L_{t+1}))^2]
    γ = E[(ln(H_{t,t+1}/L_{t,t+1}))^2]
    α = (sqrt(2β) - sqrt(β)) / (3 - 2*sqrt(2)) - sqrt(γ / (3 - 2*sqrt(2)))
    spread = 2 (e^α - 1) / (1 + e^α)

This is order-free (no L1 quotes needed), works on daily OHLC.
We add an ADV-bucket fallback for names where CS returns negative or
unrealistic spreads (a known issue on illiquid days).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _corwin_schultz_pair(h1, l1, h2, l2, h12, l12) -> float:
    """Two-day estimator. NaN-safe; returns NaN if any input is invalid."""
    if any(np.isnan([h1, l1, h2, l2, h12, l12])) or l1 <= 0 or l2 <= 0 or l12 <= 0:
        return np.nan
    beta = np.log(h1 / l1) ** 2 + np.log(h2 / l2) ** 2
    gamma = np.log(h12 / l12) ** 2
    denom = 3 - 2 * np.sqrt(2)
    inner_alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / denom - np.sqrt(max(gamma, 0) / denom)
    spread = 2 * (np.exp(inner_alpha) - 1) / (1 + np.exp(inner_alpha))
    return float(spread)


def corwin_schultz_spread(high: pd.Series, low: pd.Series, window: int = 21) -> pd.Series:
    """Rolling Corwin-Schultz spread estimate (one symbol).

    Returns spread as a fraction (e.g. 0.005 = 50 bps round-trip).
    """
    h = high.values
    l = low.values
    n = len(h)
    out = np.full(n, np.nan)
    pair = np.full(n, np.nan)
    for t in range(1, n):
        h12 = max(h[t - 1], h[t])
        l12 = min(l[t - 1], l[t])
        pair[t] = _corwin_schultz_pair(h[t - 1], l[t - 1], h[t], l[t], h12, l12)
    s = pd.Series(pair, index=high.index)
    rolling = s.rolling(window, min_periods=max(2, window // 2)).mean()
    # Floor at 0 (negative CS values mean low liquidity → use ADV fallback elsewhere)
    return rolling.clip(lower=0)


def spread_panel(
    high: pd.DataFrame,
    low: pd.DataFrame,
    dollar_volume: pd.DataFrame,
    window: int = 21,
    floor_bps: float = 1.0,
    cap_bps: float = 200.0,
) -> pd.DataFrame:
    """Per-symbol spread estimates with ADV-bucket fallback.

    For names where Corwin-Schultz is missing or 0, fall back to a heuristic:
      spread_bps = a + b / log10(ADV_$)   (calibrated to typical NSE)
    """
    spreads = pd.DataFrame(
        {sym: corwin_schultz_spread(high[sym], low[sym], window) for sym in high.columns},
        index=high.index,
    )

    # Convert to bps so the fallback is on the same units
    spreads_bps = spreads * 10_000

    # ADV fallback
    adv = dollar_volume.rolling(window, min_periods=max(2, window // 2)).median()
    log_adv = np.log10(adv.replace(0, np.nan))
    fallback_bps = (50.0 - 5.5 * log_adv).clip(lower=floor_bps, upper=cap_bps)

    spreads_bps = spreads_bps.where(spreads_bps > floor_bps, fallback_bps)
    spreads_bps = spreads_bps.clip(lower=floor_bps, upper=cap_bps)
    return spreads_bps / 10_000.0    # back to fraction
