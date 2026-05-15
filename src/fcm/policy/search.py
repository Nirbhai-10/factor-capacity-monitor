"""Policy search: optimal rebalance frequency × no-trade buffer.

We re-run the (cheap) backtest + capacity simulation for each (freq, buffer)
combination at the *target* AUM and pick the one that maximises Net IR.

This is independent of the capacity-curve scan: there we vary AUM with freq
and buffer fixed; here we vary policy with AUM fixed at the safe-capacity
target.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..capacity.curve import run_capacity_curve
from ..costs.spread import spread_panel
from ..data.types import MarketPanel
from ..factors.base import FactorSignal
from ..portfolio.backtest import Backtest
from ..portfolio.construction import RebalanceSchedule


@dataclass
class PolicyResult:
    factor_name: str
    target_aum: float
    grid: pd.DataFrame                # (freq, buffer_bps, net_ir, total_cost_bps, gross_ir)
    best_freq: str
    best_buffer_bps: float
    best_net_ir: float


def search_policy(
    *,
    factor: FactorSignal,
    panel: MarketPanel,
    cfg,
    target_aum: float,
    freqs: list[str] | None = None,
    buffers_bps: list[float] | None = None,
) -> PolicyResult:
    freqs = freqs or list(cfg.policy.rebalance_candidates)
    buffers_bps = buffers_bps or list(cfg.policy.buffer_candidates_bps)

    # Pre-compute the spread panel once (independent of freq/buffer)
    spreads = spread_panel(
        panel.high, panel.low, panel.dollar_volume,
        floor_bps=cfg.costs.spread.floor_bps,
        cap_bps=cfg.costs.spread.cap_bps,
    )

    rank = factor.compute(panel).rank
    base_aum = cfg.capacity.base_aum_units * cfg.market.unit_value

    rows = []
    for freq in freqs:
        for buf in buffers_bps:
            sched = RebalanceSchedule(freq=freq)
            bt = Backtest(
                panel=panel,
                long_q=cfg.factors.long_quantile,
                short_q=cfg.factors.short_quantile,
                rebalance=sched,
                base_aum=base_aum,
                no_trade_buffer_bps=buf,
            )
            try:
                result = bt.run(rank, factor_name=factor.name)
            except Exception:
                continue
            if not result.rebalances:
                continue
            curve = run_capacity_curve(
                backtest=result, panel=panel, spreads=spreads, cfg=cfg,
                aum_grid=[target_aum], base_aum=base_aum,
            )
            point = curve.points[0]
            rows.append({
                "freq": freq, "buffer_bps": buf,
                "gross_ir": point.gross_ir, "net_ir": point.net_ir,
                "total_cost_bps": point.total_cost_bps,
                "max_exec_days": point.max_exec_days,
                "max_participation": point.max_participation,
            })

    grid = pd.DataFrame(rows)
    if grid.empty:
        return PolicyResult(
            factor.name, target_aum, grid, freqs[0], buffers_bps[0], 0.0,
        )
    best = grid.loc[grid.net_ir.idxmax()]
    return PolicyResult(
        factor_name=factor.name,
        target_aum=target_aum,
        grid=grid,
        best_freq=str(best["freq"]),
        best_buffer_bps=float(best["buffer_bps"]),
        best_net_ir=float(best["net_ir"]),
    )
