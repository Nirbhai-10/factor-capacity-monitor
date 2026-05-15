"""Aggregator: spread + impact + commission + borrow + India taxes per rebalance."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .impact import almgren_chriss_impact, execution_days_for_cap
from .india import india_tax_bps


@dataclass
class RebalanceCost:
    date: pd.Timestamp
    aum: float
    spread_dollars: float
    impact_dollars: float
    commission_dollars: float
    borrow_dollars: float
    india_tax_dollars: float
    total_dollars: float
    max_participation: float
    max_execution_days: float
    avg_execution_days: float
    per_symbol: pd.DataFrame   # detailed per-name breakdown

    @property
    def total_bps(self) -> float:
        return 0 if self.aum <= 0 else self.total_dollars / self.aum * 10_000


def total_rebalance_cost(
    *,
    date: pd.Timestamp,
    target_weights: pd.Series,
    prev_weights: pd.Series,
    aum: float,
    spreads: pd.Series,            # fraction
    adv_dollars: pd.Series,
    volatility: pd.Series,         # annualised
    short_interest: pd.Series,     # fraction
    cfg,                           # full config
    holding_days: int = 21,
) -> RebalanceCost:
    """Compute every cost component at this rebalance for a given AUM."""

    trade_w = (target_weights - prev_weights).fillna(0.0)
    trade_dollars = trade_w * aum

    # Align everything on the union of names in target/prev
    syms = target_weights.index.union(prev_weights.index)
    trade_dollars = trade_dollars.reindex(syms).fillna(0)
    spreads = spreads.reindex(syms).fillna(spreads.median() if len(spreads) else 0.005)
    adv_dollars = adv_dollars.reindex(syms).fillna(adv_dollars.median() if len(adv_dollars) else 1e6)
    volatility = volatility.reindex(syms).fillna(volatility.median() if len(volatility) else 0.30)
    short_interest = short_interest.reindex(syms).fillna(0.02)

    # Execution days needed at participation cap
    exec_days = execution_days_for_cap(
        trade_dollars, adv_dollars, cfg.capacity.participation_cap
    ).clip(lower=1)

    # 1. Spread (one-sided, applied to absolute trade)
    spread_cost = 0.5 * spreads * trade_dollars.abs()

    # 2. Impact (Almgren-Chriss)
    impact_frac = almgren_chriss_impact(
        trade_dollars=trade_dollars,
        adv_dollars=adv_dollars,
        volatility=volatility,
        coefficient=cfg.costs.impact.coefficient,
        execution_days=exec_days.replace(0, 1),
        nonlinear_threshold=cfg.costs.impact.nonlinear_threshold,
        nonlinear_exponent=cfg.costs.impact.nonlinear_exponent,
    )
    impact_cost = impact_frac * trade_dollars.abs()

    # 3. Commission
    commission = cfg.costs.commission_bps / 10_000 * trade_dollars.abs()

    # 4. Borrow on the short leg
    short_notional = (-target_weights.clip(upper=0)).reindex(syms).fillna(0) * aum
    base_borrow = cfg.costs.borrow.base_bps / 10_000
    squeeze_premium = (
        cfg.costs.borrow.short_squeeze_premium_bps / 10_000
        * (short_interest > 0.10).astype(float)        # squeezable names
    )
    borrow_rate_annual = base_borrow + squeeze_premium
    borrow_cost = short_notional * borrow_rate_annual * (holding_days / 252.0)

    # 5. India tax stack (only when enabled). Apply on each leg by side.
    buy_dollars = trade_dollars.clip(lower=0)
    sell_dollars = (-trade_dollars).clip(lower=0)
    if cfg.costs.india.enable:
        buy_tax = india_tax_bps(buy_dollars, "buy", cfg.costs.india,
                                 brokerage_bps=cfg.costs.commission_bps) * buy_dollars
        sell_tax = india_tax_bps(sell_dollars, "sell", cfg.costs.india,
                                  brokerage_bps=cfg.costs.commission_bps) * sell_dollars
        india_tax = buy_tax + sell_tax
    else:
        india_tax = pd.Series(0.0, index=syms)

    # Per-symbol breakdown
    per_symbol = pd.DataFrame({
        "trade_dollars": trade_dollars,
        "exec_days": exec_days,
        "spread": spread_cost,
        "impact": impact_cost,
        "commission": commission,
        "borrow": borrow_cost,
        "india_tax": india_tax,
        "participation": trade_dollars.abs() / adv_dollars.replace(0, np.nan),
    })

    return RebalanceCost(
        date=date,
        aum=aum,
        spread_dollars=spread_cost.sum(),
        impact_dollars=impact_cost.sum(),
        commission_dollars=commission.sum(),
        borrow_dollars=borrow_cost.sum(),
        india_tax_dollars=india_tax.sum(),
        total_dollars=(spread_cost + impact_cost + commission + borrow_cost + india_tax).sum(),
        max_participation=float(per_symbol["participation"].max()),
        max_execution_days=float(exec_days.max()),
        avg_execution_days=float(exec_days[trade_dollars.abs() > 0].mean()
                                 if (trade_dollars.abs() > 0).any() else 0.0),
        per_symbol=per_symbol,
    )
