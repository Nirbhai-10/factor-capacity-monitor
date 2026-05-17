"""Stress capacity: capacity curve under widened spreads, halved ADV, fattened
volatility, and a one-shot redemption shock that forces unwinding 30% of the
book in 5 days.

Implementation: build a stressed copy of the spread/ADV/vol arrays at the
appropriate quantiles, then re-run `run_capacity_curve` on the same backtest
but with the stressed market state.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..capacity.curve import CapacityCurve, CapacityPoint, run_capacity_curve
from ..costs.total import total_rebalance_cost
from ..data.types import MarketPanel
from ..portfolio.backtest import BacktestResult


@dataclass
class StressResult:
    factor_name: str
    nominal: CapacityCurve
    stressed: CapacityCurve
    redemption: dict           # {aum: realised_unwind_cost_bps}


def _stressed_panel(panel: MarketPanel, spreads: pd.DataFrame, cfg) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sp_q = cfg.stress.spread_pct_quantile
    adv_q = cfg.stress.adv_pct_quantile
    vol_q = cfg.stress.vol_pct_quantile

    # Stressed spread: per-symbol high quantile; broadcast over time
    sp_high = spreads.quantile(sp_q, axis=0)
    spreads_stressed = pd.DataFrame(
        np.broadcast_to(sp_high.values, spreads.shape),
        index=spreads.index, columns=spreads.columns,
    )

    adv = panel.adv(window=20)
    adv_low = adv.quantile(adv_q, axis=0)
    adv_stressed = pd.DataFrame(
        np.broadcast_to(adv_low.values, adv.shape),
        index=adv.index, columns=adv.columns,
    )

    vol = panel.realised_vol(window=20)
    vol_high = vol.quantile(vol_q, axis=0)
    vol_stressed = pd.DataFrame(
        np.broadcast_to(vol_high.values, vol.shape),
        index=vol.index, columns=vol.columns,
    )

    # Bump short interest at the long-tail by 5pp to model a squeeze regime
    si_stressed = (panel.short_interest + 0.05).clip(upper=0.4)
    return spreads_stressed, adv_stressed, vol_stressed, si_stressed


def run_stress(
    *,
    backtest: BacktestResult,
    panel: MarketPanel,
    spreads: pd.DataFrame,
    cfg,
) -> StressResult:
    nominal = run_capacity_curve(
        backtest=backtest, panel=panel, spreads=spreads, cfg=cfg,
    )

    sp_s, adv_s, vol_s, si_s = _stressed_panel(panel, spreads, cfg)

    # Bump impact coefficient via a temporary swap on cfg
    nominal_impact_k = cfg.costs.impact.coefficient
    nominal_borrow_premium = cfg.costs.borrow.short_squeeze_premium_bps

    # Build a shallow copy of cfg with stressed values
    stressed_cfg_dict = cfg.to_dict()
    stressed_cfg_dict["costs"]["impact"]["coefficient"] = nominal_impact_k * cfg.stress.impact_multiplier
    stressed_cfg_dict["costs"]["borrow"]["short_squeeze_premium_bps"] = (
        nominal_borrow_premium + cfg.stress.borrow_premium_bps
    )

    from ..config import Config
    stressed_cfg = Config(stressed_cfg_dict)

    # Stressed panel keeps prices but replaces short_interest. We pass the
    # stressed ADV and vol explicitly via overrides — cleaner than mutating
    # the panel.
    panel_stressed = MarketPanel(
        close=panel.close, high=panel.high, low=panel.low, open_=panel.open_,
        volume=panel.volume, dollar_volume=panel.dollar_volume,
        pb=panel.pb, roe=panel.roe, short_interest=si_s, sectors=panel.sectors,
    )

    stressed = run_capacity_curve(
        backtest=backtest, panel=panel_stressed, spreads=sp_s, cfg=stressed_cfg,
        adv_override=adv_s, vol_override=vol_s,
    )

    # Redemption-shock unwind: for each AUM, compute the cost of shedding
    # `redemption_shock_pct` of the book in the cfg's stressed regime, over 5 days.
    redemption: dict[float, float] = {}
    shock_pct = cfg.stress.redemption_shock_pct
    last_snap = backtest.rebalances[-1] if backtest.rebalances else None
    if last_snap is not None:
        for p in nominal.points:
            unwind_target = last_snap.target_weights * (1 - shock_pct)
            cost = total_rebalance_cost(
                date=last_snap.date,
                target_weights=unwind_target,
                prev_weights=last_snap.target_weights,
                aum=p.aum,
                spreads=sp_s.iloc[-1],
                adv_dollars=adv_s.iloc[-1],
                volatility=vol_s.iloc[-1],
                short_interest=si_s.iloc[-1],
                cfg=stressed_cfg,
                holding_days=5,
            )
            redemption[p.aum] = cost.total_bps

    return StressResult(
        factor_name=backtest.factor_name,
        nominal=nominal,
        stressed=stressed,
        redemption=redemption,
    )
