"""Low-volatility factor: realised vol over a window; lower vol = predicted winner.

Score = -realised_vol so higher score = lower-vol name.
"""
from __future__ import annotations

import pandas as pd

from ..data.types import MarketPanel
from .base import FactorSignal


class LowVolFactor(FactorSignal):
    name = "low_vol"

    def __init__(self, window_days: int = 126):
        self.window_days = window_days

    def compute_score(self, panel: MarketPanel) -> pd.DataFrame:
        rets = panel.close.pct_change()
        vol = rets.rolling(self.window_days, min_periods=self.window_days // 2).std()
        return -vol
