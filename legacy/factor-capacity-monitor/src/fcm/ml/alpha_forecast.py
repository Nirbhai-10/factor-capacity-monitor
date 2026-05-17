"""Forecast forward-6m alpha (rolling Sharpe) of a factor using a simple
state-space model.

Model:
    s_t = trailing-1y Sharpe at time t  (observable)
    Δs_t = -κ (s_t - μ_t) + ε_t          (mean-reverting around regime mean)
    μ_t  = α + β · crowd_t                (regime-dependent attractor)

Fit (α, β, κ) via OLS on stacked (Δs_t, s_t, crowd_t) — closed form, no SGD.
Forecast 126 trading days forward by integrating the SDE deterministically.

Why this design:
- Linear / closed-form so it trains in milliseconds and is interpretable.
- Crowding feeds in as the attractor: the more crowded the factor, the lower
  the regime-mean Sharpe it pulls toward. This matches Asness et al.'s
  empirical observation that valuation spread predicts forward factor returns.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class AlphaDecayForecast:
    fitted_kappa: float                  # mean reversion speed
    fitted_alpha: float                  # baseline attractor
    fitted_beta: float                   # crowding loading
    rmse_in_sample: float
    forecast: pd.Series                  # forward dates × predicted Sharpe
    fan_lower: pd.Series                 # 1σ band
    fan_upper: pd.Series

    @property
    def half_life_days(self) -> float:
        """Days for the deviation from the attractor to halve."""
        if self.fitted_kappa <= 0:
            return float("inf")
        return float(np.log(2) / self.fitted_kappa)


def _trailing_sharpe(returns: pd.Series, window: int = 252) -> pd.Series:
    """Rolling annualised Sharpe."""
    mu = returns.rolling(window, min_periods=window // 2).mean()
    sd = returns.rolling(window, min_periods=window // 2).std()
    return (mu / sd) * np.sqrt(252)


def forecast_alpha_decay(
    daily_returns: pd.Series,
    crowding_score: pd.Series,
    horizon_days: int = 126,
    sharpe_window: int = 252,
) -> AlphaDecayForecast:
    """Fit OU-with-covariate model and forecast forward."""
    sharpe = _trailing_sharpe(daily_returns, sharpe_window).dropna()
    crowd = crowding_score.reindex(sharpe.index).ffill().bfill()

    # Daily increments
    ds = sharpe.diff().dropna()
    s_lag = sharpe.shift(1).reindex(ds.index)
    c_lag = crowd.shift(1).reindex(ds.index)

    # Δs_t = a + b·crowd_t - κ·s_{t-1}  →  Δs = Xβ + ε
    valid = ds.notna() & s_lag.notna() & c_lag.notna()
    y = ds[valid].values
    X = np.column_stack([
        np.ones(valid.sum()),
        c_lag[valid].values,
        -s_lag[valid].values,
    ])

    # OLS via lstsq — robust to rank deficiency.
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    a_hat, b_hat, kappa_hat = float(coef[0]), float(coef[1]), float(coef[2])
    kappa_hat = max(kappa_hat, 1e-6)
    alpha_hat = a_hat / kappa_hat
    beta_hat = b_hat / kappa_hat

    # In-sample residual
    pred = X @ coef
    rmse = float(np.sqrt(((y - pred) ** 2).mean()))

    # Forecast forward
    last_s = float(sharpe.iloc[-1])
    last_c = float(crowd.iloc[-1])
    # Simple deterministic projection: μ stays at last crowding value
    # (we don't try to forecast crowding itself).
    mu = alpha_hat + beta_hat * last_c
    days = np.arange(1, horizon_days + 1)
    decay = np.exp(-kappa_hat * days)
    forecast_vals = mu + (last_s - mu) * decay

    last_date = sharpe.index[-1]
    future_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1),
                                    periods=horizon_days)
    forecast = pd.Series(forecast_vals, index=future_dates, name="sharpe_forecast")

    # Fan: ±1σ scaled by sqrt(time)
    sigma_inc = rmse / max(kappa_hat, 1e-6)
    fan = sigma_inc * np.sqrt(1 - np.exp(-2 * kappa_hat * days))
    return AlphaDecayForecast(
        fitted_kappa=kappa_hat,
        fitted_alpha=alpha_hat,
        fitted_beta=beta_hat,
        rmse_in_sample=rmse,
        forecast=forecast,
        fan_lower=pd.Series(forecast_vals - fan, index=future_dates),
        fan_upper=pd.Series(forecast_vals + fan, index=future_dates),
    )
