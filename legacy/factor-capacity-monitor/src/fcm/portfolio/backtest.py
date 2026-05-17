"""Backtester producing per-rebalance snapshots and a daily gross-return series."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..data.types import MarketPanel
from .construction import RebalanceSchedule, build_long_short_weights


@dataclass
class RebalanceSnapshot:
    date: pd.Timestamp
    target_weights: pd.Series       # index = symbols, dollar-neutral
    prev_weights: pd.Series
    trade_weights: pd.Series        # target - prev
    trade_dollars: pd.Series        # at base AUM
    base_aum: float


@dataclass
class BacktestResult:
    factor_name: str
    rebalances: list[RebalanceSnapshot]
    daily_weights: pd.DataFrame
    daily_returns: pd.Series        # gross daily returns (no costs)
    target_weights_ts: pd.DataFrame # weights at each rebalance, ffilled

    @property
    def annual_gross_return(self) -> float:
        return self.daily_returns.mean() * 252

    @property
    def annual_vol(self) -> float:
        return self.daily_returns.std() * np.sqrt(252)

    @property
    def gross_ir(self) -> float:
        v = self.annual_vol
        return self.annual_gross_return / v if v > 0 else 0.0


class Backtest:
    """Runs a long-short backtest given a rank DataFrame from a FactorSignal."""

    def __init__(
        self,
        panel: MarketPanel,
        long_q: float = 0.20,
        short_q: float = 0.20,
        rebalance: RebalanceSchedule | None = None,
        base_aum: float = 1.0,
        no_trade_buffer_bps: float = 0.0,
    ):
        self.panel = panel
        self.long_q = long_q
        self.short_q = short_q
        self.rebalance = rebalance or RebalanceSchedule("W")
        self.base_aum = base_aum
        self.no_trade_buffer = no_trade_buffer_bps / 10_000.0

    def run(self, rank: pd.DataFrame, factor_name: str = "factor") -> BacktestResult:
        full_weights = build_long_short_weights(rank, self.long_q, self.short_q)
        rebal_dates = pd.DatetimeIndex(self.rebalance.dates(full_weights.index))
        # only keep rebal dates that have a non-zero target row
        nonempty = full_weights.abs().sum(axis=1) > 0
        rebal_dates = rebal_dates[rebal_dates.isin(full_weights.index[nonempty])]

        symbols = full_weights.columns
        prev_w = pd.Series(0.0, index=symbols)
        snapshots: list[RebalanceSnapshot] = []
        snapshot_rows = {}

        for d in rebal_dates:
            target = full_weights.loc[d]
            if self.no_trade_buffer > 0:
                # only update weights that move by more than the buffer
                delta = target - prev_w
                stay = delta.abs() < self.no_trade_buffer
                target = target.where(~stay, prev_w)
            trade = target - prev_w
            snap = RebalanceSnapshot(
                date=d,
                target_weights=target.copy(),
                prev_weights=prev_w.copy(),
                trade_weights=trade.copy(),
                trade_dollars=trade * self.base_aum,
                base_aum=self.base_aum,
            )
            snapshots.append(snap)
            snapshot_rows[d] = target
            prev_w = target

        target_weights_ts = (
            pd.DataFrame(snapshot_rows).T
            .reindex(columns=symbols)
            .fillna(0.0)
            .sort_index()
        )
        # Forward-fill across all trading days
        daily_weights = target_weights_ts.reindex(full_weights.index, method="ffill").fillna(0.0)

        # Gross daily returns: lagged weights × today's returns
        rets = self.panel.returns().reindex_like(daily_weights).fillna(0.0)
        daily_returns = (daily_weights.shift(1).fillna(0.0) * rets).sum(axis=1)

        return BacktestResult(
            factor_name=factor_name,
            rebalances=snapshots,
            daily_weights=daily_weights,
            daily_returns=daily_returns,
            target_weights_ts=target_weights_ts,
        )
