"""Market impact: Almgren-Chriss with a nonlinear tail.

    impact = σ × k × √(participation)        if participation ≤ p_threshold
           = σ × k × p_threshold^(0.5 - exp) × participation^exp   otherwise

The nonlinear tail (exponent 0.6 above 10% of ADV) follows
Almgren et al. (2005) — empirically impact is steeper than √· for large trades.
σ is annualised volatility; output is impact as a fraction of price.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def almgren_chriss_impact(
    trade_dollars: pd.Series,
    adv_dollars: pd.Series,
    volatility: pd.Series,
    coefficient: float = 0.20,
    execution_days: float = 1.0,
    nonlinear_threshold: float = 0.10,
    nonlinear_exponent: float = 0.6,
) -> pd.Series:
    """Per-name impact as a fraction of trade value (not bps).

    Args mirror the math:
      σ = volatility (annualised, decimal)
      k = coefficient
      Q = |trade_dollars|
      V = adv_dollars × execution_days
      participation = Q / V
    """
    q = trade_dollars.abs()
    v = (adv_dollars * execution_days).replace(0, np.nan)
    participation = q / v
    participation = participation.fillna(0)

    # Piecewise: sqrt below threshold, power above
    sqrt_part = np.sqrt(np.minimum(participation, nonlinear_threshold))
    excess = np.maximum(participation - nonlinear_threshold, 0)
    # Smooth join at threshold so derivative isn't insane
    extra = (
        np.sqrt(nonlinear_threshold) *
        ((1 + excess / max(nonlinear_threshold, 1e-9)) ** nonlinear_exponent - 1)
    )
    impact_frac = volatility * coefficient * (sqrt_part + extra)
    return impact_frac.fillna(0)


def impact_dollars(
    trade_dollars: pd.Series,
    adv_dollars: pd.Series,
    volatility: pd.Series,
    coefficient: float = 0.20,
    execution_days: float = 1.0,
    nonlinear_threshold: float = 0.10,
    nonlinear_exponent: float = 0.6,
) -> pd.Series:
    impact_frac = almgren_chriss_impact(
        trade_dollars, adv_dollars, volatility,
        coefficient, execution_days, nonlinear_threshold, nonlinear_exponent,
    )
    return impact_frac * trade_dollars.abs()


def execution_days_for_cap(
    trade_dollars: pd.Series,
    adv_dollars: pd.Series,
    participation_cap: float = 0.05,
) -> pd.Series:
    """How many days are needed if we cap daily participation at `cap`.

    days = ceil( |Q| / (cap × ADV) ).
    """
    q = trade_dollars.abs()
    v = (participation_cap * adv_dollars).replace(0, np.nan)
    days = np.ceil(q / v).fillna(0)
    return days.clip(lower=0)
