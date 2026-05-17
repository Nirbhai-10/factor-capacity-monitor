"""Synthetic NIFTY-100-like panel generator.

Statistical properties we mimic:
- Daily log returns: 3-factor model (market + size + value) with idiosyncratic vol.
- Volatility clustering: GARCH(1,1)-ish persistence on idiosyncratic shocks.
- ADV: Pareto distribution (heavy tail) — large caps are 100× small caps.
- Spread: log-inversely related to ADV with noise (Hasbrouck-style).
- Fundamentals: synthetic P/B and ROE, persistent across time, correlated
  cross-sectionally with the value/quality "true" loadings (so the factors
  *should* generate alpha against the synthetic returns).
- Short interest: bursty, mean-reverting around 2% with occasional spikes.

This is enough to exercise every module in the pipeline without internet.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .types import MarketPanel


@dataclass
class SyntheticPanel:
    """Wraps a generated MarketPanel together with the latent factor exposures
    that drove it (useful for debugging — checks whether our factor signals
    actually pick up the true loadings)."""

    market: MarketPanel
    true_betas: pd.DataFrame   # symbols × {market, size, value}


def generate_panel(
    n_symbols: int = 100,
    history_years: int = 5,
    seed: int = 42,
    start: str = "2020-01-02",
) -> SyntheticPanel:
    rng = np.random.default_rng(seed)
    n_days = int(history_years * 252)

    dates = pd.bdate_range(start=start, periods=n_days)
    symbols = [f"SYM{i:03d}" for i in range(n_symbols)]

    # ---------- 1. Latent loadings ----------
    market_beta = rng.normal(1.0, 0.25, n_symbols)
    size_beta   = rng.normal(0.0, 0.7, n_symbols)
    value_beta  = rng.normal(0.0, 0.8, n_symbols)
    quality_beta = rng.normal(0.0, 0.8, n_symbols)
    lowvol_beta = rng.normal(0.0, 0.8, n_symbols)
    momentum_beta = rng.normal(0.0, 0.8, n_symbols)        # latent persistent return drift

    betas = pd.DataFrame(
        {"market": market_beta, "size": size_beta,
         "value": value_beta, "quality": quality_beta,
         "low_vol": lowvol_beta, "momentum": momentum_beta},
        index=symbols,
    )

    # ---------- 2. Latent factor returns (alphas calibrated to give IR ~ 1) ----------
    # Annualised target Sharpe per latent factor ≈ 1, except market.
    def _gen(mu_ann: float, vol_ann: float) -> np.ndarray:
        return rng.normal(mu_ann / 252, vol_ann / np.sqrt(252), n_days)

    daily_market = _gen(0.06, 0.15)
    daily_size   = _gen(0.04, 0.04)
    daily_value  = _gen(0.05, 0.05)
    daily_quality = _gen(0.05, 0.05)
    daily_lowvol = _gen(0.04, 0.04)
    daily_momentum = _gen(0.05, 0.05)

    factor_rets = np.column_stack([daily_market, daily_size, daily_value,
                                    daily_quality, daily_lowvol, daily_momentum])
    loadings = betas.values  # n_symbols × 6

    common = factor_rets @ loadings.T  # n_days × n_symbols

    # ---------- 3. Idiosyncratic returns with GARCH-ish clustering ----------
    # Per-symbol idiosyncratic vol is *higher* for negative low_vol_beta
    # (so high-lowvol-beta names are genuinely lower-vol — gives the LowVolFactor
    # a real signal to pick up).
    base_idio_vol_ann = 0.20 - 0.06 * np.tanh(lowvol_beta)
    base_idio_vol_ann = np.clip(base_idio_vol_ann, 0.08, 0.40)
    base_var = (base_idio_vol_ann / np.sqrt(252)) ** 2
    persistence = 0.92
    arch = 0.07
    idio_vol = np.zeros((n_days, n_symbols))
    var_t = base_var.copy()
    idio = np.zeros((n_days, n_symbols))
    for t in range(n_days):
        sd = np.sqrt(var_t)
        z = rng.standard_normal(n_symbols)
        idio[t] = sd * z
        var_t = (1 - persistence - arch) * base_var + persistence * var_t + arch * idio[t] ** 2
        idio_vol[t] = sd

    daily_returns = common + idio
    # truncate extremes to keep prices > 0
    daily_returns = np.clip(daily_returns, -0.20, 0.20)

    # ---------- 4. Prices ----------
    log_prices = np.cumsum(daily_returns, axis=0)
    base_price = rng.uniform(50, 5000, n_symbols)        # spread of price levels
    close = pd.DataFrame(base_price * np.exp(log_prices), index=dates, columns=symbols)

    # OHLC: simulate daily range as 1.5×|return|, drift open between prev close and today's close
    abs_ret = np.abs(daily_returns)
    daily_range = (1.5 * abs_ret + 0.005) * close.values
    high = close.values + 0.5 * daily_range
    low = close.values - 0.5 * daily_range
    low = np.maximum(low, 0.01)
    open_ = np.empty_like(close.values)
    open_[0] = close.values[0]
    open_[1:] = close.values[:-1] * (1 + 0.3 * (close.values[1:] / close.values[:-1] - 1))

    open_df = pd.DataFrame(open_, index=dates, columns=symbols)
    high_df = pd.DataFrame(high, index=dates, columns=symbols)
    low_df = pd.DataFrame(low, index=dates, columns=symbols)

    # ---------- 5. ADV (heavy-tailed; calibrated to real NIFTY-100) ----------
    # Real NIFTY-100 daily turnover spans ~₹20cr (smallest) to ~₹2000cr+
    # (largest). Synthesise share-volume scale so dollar ADV matches that range.
    pareto_alpha = 1.6
    base_share_vol = (rng.pareto(pareto_alpha, n_symbols) + 1) * 500_000
    # vol days: random walk around base, with occasional spikes
    vol_walk = np.exp(np.cumsum(rng.normal(0, 0.05, (n_days, n_symbols)), axis=0))
    vol_walk = vol_walk / vol_walk.mean(axis=0)
    spike = rng.binomial(1, 0.02, (n_days, n_symbols)) * rng.uniform(2, 6, (n_days, n_symbols))
    spike = np.where(spike == 0, 1, spike)
    share_volume = (base_share_vol * vol_walk * spike).clip(min=100)
    volume = pd.DataFrame(share_volume, index=dates, columns=symbols)
    dollar_volume = close * volume

    # ---------- 6. Fundamentals (persistent, tied to latent loadings) ----------
    # P/B: cheap names (high "value" beta) have lower P/B
    pb_mean = 3.0 - 1.2 * value_beta + rng.normal(0, 0.3, n_symbols)
    pb_mean = np.clip(pb_mean, 0.3, 10.0)
    # Drift slowly with random walk
    pb_walk = np.cumsum(rng.normal(0, 0.005, (n_days, n_symbols)), axis=0)
    pb = pb_mean[None, :] * np.exp(pb_walk * 0.5)
    pb = pd.DataFrame(pb, index=dates, columns=symbols)

    # ROE: high quality names have higher ROE
    roe_mean = 0.15 + 0.10 * quality_beta + rng.normal(0, 0.04, n_symbols)
    roe_walk = np.cumsum(rng.normal(0, 0.002, (n_days, n_symbols)), axis=0)
    roe = roe_mean[None, :] + roe_walk * 0.05
    roe = pd.DataFrame(roe, index=dates, columns=symbols).clip(-0.5, 0.6)

    # ---------- 7. Short interest (bursty) ----------
    si = np.full((n_days, n_symbols), 0.02)
    for t in range(1, n_days):
        # mean reverts toward 2%, with random spikes
        spike_mask = rng.binomial(1, 0.005, n_symbols)
        spike_size = rng.uniform(0.05, 0.15, n_symbols) * spike_mask
        si[t] = 0.95 * si[t - 1] + 0.05 * 0.02 + spike_size
        si[t] = np.clip(si[t], 0, 0.4)
    short_interest = pd.DataFrame(si, index=dates, columns=symbols)

    # Sectors (random, just for grouping in dashboard)
    sector_choices = ["Financials", "IT", "Energy", "Consumer", "Pharma",
                       "Materials", "Industrials", "Utilities"]
    sectors = {s: rng.choice(sector_choices) for s in symbols}

    panel = MarketPanel(
        close=close, high=high_df, low=low_df, open_=open_df,
        volume=volume, dollar_volume=dollar_volume,
        pb=pb, roe=roe, short_interest=short_interest, sectors=sectors,
    )

    return SyntheticPanel(market=panel, true_betas=betas)
