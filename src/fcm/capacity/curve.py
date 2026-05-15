"""Capacity curve: scan an AUM grid, compute Net IR after costs at each level.

The base backtest gives us *gross* returns at AUM = base_aum. We re-cost the
same trades at each AUM in the grid (linear scaling) and amortise the round-trip
cost across the holding period to get net daily returns:

    annualised_cost_pct = total_cost_$ / (aum × years_simulated)
    net_daily_return = gross_daily_return − annualised_cost_pct / 252
    net_IR = mean(net) / std(net) × √252

That's the curve point. Vectorisable across rebalances.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..costs.total import RebalanceCost, total_rebalance_cost
from ..data.types import MarketPanel
from ..portfolio.backtest import BacktestResult
from .zones import Zone, classify_zone


@dataclass
class CapacityPoint:
    aum: float
    gross_ir: float
    net_ir: float
    gross_return_ann: float
    net_return_ann: float
    total_cost_bps: float
    spread_bps: float
    impact_bps: float
    commission_bps: float
    borrow_bps: float
    india_bps: float
    max_exec_days: float
    avg_exec_days: float
    max_participation: float
    avg_participation: float
    zone: Zone


@dataclass
class CapacityCurve:
    factor_name: str
    points: list[CapacityPoint]

    def to_frame(self) -> pd.DataFrame:
        rows = []
        for p in self.points:
            rows.append({
                "aum": p.aum,
                "gross_ir": p.gross_ir,
                "net_ir": p.net_ir,
                "gross_return_ann": p.gross_return_ann,
                "net_return_ann": p.net_return_ann,
                "total_cost_bps": p.total_cost_bps,
                "spread_bps": p.spread_bps,
                "impact_bps": p.impact_bps,
                "commission_bps": p.commission_bps,
                "borrow_bps": p.borrow_bps,
                "india_bps": p.india_bps,
                "max_exec_days": p.max_exec_days,
                "max_participation": p.max_participation,
                "zone": p.zone.name,
            })
        return pd.DataFrame(rows)

    def safe_capacity(self) -> float | None:
        safe_points = [p.aum for p in self.points if p.zone.name == "safe"]
        return max(safe_points) if safe_points else None

    def caution_capacity(self) -> float | None:
        ok = [p.aum for p in self.points if p.zone.name in ("safe", "caution")]
        return max(ok) if ok else None

    def ir_threshold_capacity(self, threshold: float = 0.5) -> float | None:
        """Largest AUM where net_ir ≥ threshold (interpolated linearly between grid points)."""
        df = self.to_frame().sort_values("aum").reset_index(drop=True)
        ok = df[df.net_ir >= threshold]
        if ok.empty:
            return None
        if df.net_ir.iloc[-1] >= threshold:
            return float(df.aum.iloc[-1])
        # interpolate between last ok point and the next
        last_ok_idx = ok.index.max()
        if last_ok_idx + 1 >= len(df):
            return float(df.aum.iloc[last_ok_idx])
        a1, a2 = df.aum.iloc[last_ok_idx], df.aum.iloc[last_ok_idx + 1]
        i1, i2 = df.net_ir.iloc[last_ok_idx], df.net_ir.iloc[last_ok_idx + 1]
        if i1 == i2:
            return float(a1)
        # linear in AUM (could use log-linear; AUM steps are coarse)
        w = (i1 - threshold) / (i1 - i2)
        return float(a1 + w * (a2 - a1))


def run_capacity_curve(
    *,
    backtest: BacktestResult,
    panel: MarketPanel,
    spreads: pd.DataFrame,
    cfg,
    aum_grid: list[float] | None = None,
    base_aum: float | None = None,
    adv_override: pd.DataFrame | None = None,
    vol_override: pd.DataFrame | None = None,
) -> CapacityCurve:
    """Run the capacity curve scan.

    Args:
      backtest: result from `Backtest.run`. The trade dollars therein are at base_aum.
      panel: MarketPanel for spreads/ADV/vol/SI
      spreads: precomputed spread DataFrame (dates × symbols, fraction)
      cfg: full Config
      aum_grid: list of AUM values in the same units as base_aum. Defaults to
                cfg.capacity.aum_grid_units × cfg.market.unit_value
      base_aum: AUM at which the trade_dollars in `backtest` were measured. Defaults
                to cfg.capacity.base_aum_units × cfg.market.unit_value
    """
    unit = cfg.market.unit_value
    if aum_grid is None:
        aum_grid = [u * unit for u in cfg.capacity.aum_grid_units]
    if base_aum is None:
        base_aum = cfg.capacity.base_aum_units * unit

    adv_panel = adv_override if adv_override is not None else panel.adv(window=20)
    vol_panel = vol_override if vol_override is not None else panel.realised_vol(window=20)

    # Pre-fetch per-rebalance market state
    rebal_states = []
    for snap in backtest.rebalances:
        d = snap.date
        if d not in spreads.index:
            d_loc = spreads.index.asof(d)
        else:
            d_loc = d
        if d_loc is pd.NaT:
            continue
        rebal_states.append({
            "snapshot": snap,
            "spread_row": spreads.loc[d_loc],
            "adv_row": adv_panel.loc[d_loc] if d_loc in adv_panel.index else adv_panel.iloc[-1],
            "vol_row": vol_panel.loc[d_loc] if d_loc in vol_panel.index else vol_panel.iloc[-1],
            "si_row": panel.short_interest.loc[d_loc] if d_loc in panel.short_interest.index
                      else panel.short_interest.iloc[-1],
        })

    holding_days = cfg.factors.holding_days

    # Derive sample length in years from the daily return series
    ann_factor = 252.0
    n_days = backtest.daily_returns.dropna().size
    years = max(n_days / ann_factor, 1e-6)

    points: list[CapacityPoint] = []
    for aum in aum_grid:
        scale = aum / base_aum
        spread_sum = impact_sum = commission_sum = borrow_sum = india_sum = 0.0
        max_part = 0.0
        all_exec_days = []
        for st in rebal_states:
            snap = st["snapshot"]
            # Scaling: trade weights stay the same, AUM grows → trade_dollars grow linearly
            scaled_target = snap.target_weights        # weights, unchanged
            scaled_prev = snap.prev_weights
            cost = total_rebalance_cost(
                date=snap.date,
                target_weights=scaled_target,
                prev_weights=scaled_prev,
                aum=aum,
                spreads=st["spread_row"],
                adv_dollars=st["adv_row"],
                volatility=st["vol_row"],
                short_interest=st["si_row"],
                cfg=cfg,
                holding_days=holding_days,
            )
            spread_sum += cost.spread_dollars
            impact_sum += cost.impact_dollars
            commission_sum += cost.commission_dollars
            borrow_sum += cost.borrow_dollars
            india_sum += cost.india_tax_dollars
            max_part = max(max_part, cost.max_participation)
            if cost.avg_execution_days > 0:
                all_exec_days.append(cost.avg_execution_days)

        total_cost = spread_sum + impact_sum + commission_sum + borrow_sum + india_sum

        # Annualised cost as % of AUM
        ann_cost_pct = total_cost / (aum * years) if aum > 0 else 0
        cost_per_day = ann_cost_pct / 252

        net_daily = backtest.daily_returns - cost_per_day
        gross_mu = backtest.daily_returns.mean()
        gross_sd = backtest.daily_returns.std()
        net_mu = net_daily.mean()
        net_sd = net_daily.std()

        gross_ir = (gross_mu / gross_sd * np.sqrt(252)) if gross_sd > 0 else 0.0
        net_ir = (net_mu / net_sd * np.sqrt(252)) if net_sd > 0 else 0.0

        max_exec = max(all_exec_days) if all_exec_days else 0
        avg_exec = float(np.mean(all_exec_days)) if all_exec_days else 0
        zone = classify_zone(net_ir, max_exec, max_part, cfg)

        points.append(CapacityPoint(
            aum=aum,
            gross_ir=gross_ir,
            net_ir=net_ir,
            gross_return_ann=gross_mu * 252,
            net_return_ann=net_mu * 252,
            total_cost_bps=ann_cost_pct * 10_000,
            spread_bps=(spread_sum / (aum * years) * 10_000) if aum * years > 0 else 0,
            impact_bps=(impact_sum / (aum * years) * 10_000) if aum * years > 0 else 0,
            commission_bps=(commission_sum / (aum * years) * 10_000) if aum * years > 0 else 0,
            borrow_bps=(borrow_sum / (aum * years) * 10_000) if aum * years > 0 else 0,
            india_bps=(india_sum / (aum * years) * 10_000) if aum * years > 0 else 0,
            max_exec_days=max_exec,
            avg_exec_days=avg_exec,
            max_participation=max_part,
            avg_participation=0.0,        # filled by allocator if needed
            zone=zone,
        ))

    return CapacityCurve(factor_name=backtest.factor_name, points=points)
