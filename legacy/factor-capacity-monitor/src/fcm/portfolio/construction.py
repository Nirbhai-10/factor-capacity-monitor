"""Portfolio construction: rank-quantile dollar-neutral long-short weights."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def build_long_short_weights(
    rank: pd.DataFrame,
    long_q: float = 0.20,
    short_q: float = 0.20,
) -> pd.DataFrame:
    """Equal-weighted long/short within top/bottom quantile.

    Long sums to +1, short sums to -1 → gross 2.0, net 0.
    Rows where the rank slice is empty (early in the sample) come out as zeros.
    """
    out = pd.DataFrame(0.0, index=rank.index, columns=rank.columns)

    # vectorise: per-row, sort ranks, set top long_q to 1 and bottom short_q to -1
    n = rank.shape[1]
    n_long = max(1, int(round(long_q * n)))
    n_short = max(1, int(round(short_q * n)))

    rank_arr = rank.values
    out_arr = out.values
    for i in range(rank.shape[0]):
        row = rank_arr[i]
        if np.isnan(row).all():
            continue
        order = np.argsort(np.where(np.isnan(row), -np.inf, row))   # asc
        valid = ~np.isnan(row[order])
        order = order[valid]
        if len(order) < (n_long + n_short):
            continue
        short_idx = order[:n_short]
        long_idx = order[-n_long:]
        out_arr[i, long_idx] = 1.0 / n_long
        out_arr[i, short_idx] = -1.0 / n_short

    return out


@dataclass
class RebalanceSchedule:
    """Generates rebalance dates from a frequency string."""

    freq: str = "W"           # D | W | BW | M | Q

    def dates(self, index: pd.DatetimeIndex) -> pd.DatetimeIndex:
        if self.freq == "D":
            return index
        if self.freq == "W":
            mask = index.to_series().dt.weekday == 4   # Friday
            return index[mask.values]
        if self.freq == "BW":
            mask = (index.to_series().dt.weekday == 4) & ((index.isocalendar().week % 2) == 0)
            return index[mask.values]
        if self.freq == "M":
            s = pd.Series(index, index=index)
            return s.resample("ME").last().dropna().values
        if self.freq == "Q":
            s = pd.Series(index, index=index)
            return s.resample("QE").last().dropna().values
        raise ValueError(f"Unknown freq '{self.freq}'")
