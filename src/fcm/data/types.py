"""Common data containers."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class MarketPanel:
    """A panel of market data: prices, volumes, fundamentals, sector tags.

    All DataFrames are dates × symbols and share the same index/columns.
    Fundamentals are dates × symbols too, sampled at quarter-end and
    forward-filled.
    """

    close: pd.DataFrame                    # adjusted close
    high: pd.DataFrame
    low: pd.DataFrame
    open_: pd.DataFrame
    volume: pd.DataFrame                   # shares
    dollar_volume: pd.DataFrame            # close * volume
    pb: pd.DataFrame                       # price/book
    roe: pd.DataFrame                      # return on equity
    short_interest: pd.DataFrame           # SI as fraction of float
    sectors: dict[str, str] = field(default_factory=dict)

    @property
    def symbols(self) -> list[str]:
        return list(self.close.columns)

    @property
    def dates(self) -> pd.DatetimeIndex:
        return self.close.index

    def returns(self) -> pd.DataFrame:
        return self.close.pct_change()

    def adv(self, window: int = 20) -> pd.DataFrame:
        """Rolling median dollar ADV — robust to spike days."""
        return self.dollar_volume.rolling(window, min_periods=max(2, window // 2)).median()

    def realised_vol(self, window: int = 20, ann: float = 252.0) -> pd.DataFrame:
        return self.returns().rolling(window).std() * (ann ** 0.5)
