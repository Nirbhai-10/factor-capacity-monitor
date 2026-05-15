"""12-1 momentum (Jegadeesh-Titman / Asness): trailing 12m return excluding the
last 1m to avoid short-term reversal."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..data.types import MarketPanel
from .base import FactorSignal


class MomentumFactor(FactorSignal):
    name = "momentum"

    def __init__(self, lookback_days: int = 252, skip_days: int = 21):
        self.lookback_days = lookback_days
        self.skip_days = skip_days

    def compute_score(self, panel: MarketPanel) -> pd.DataFrame:
        close = panel.close
        # Return from t - lookback to t - skip
        prev = close.shift(self.lookback_days)
        recent = close.shift(self.skip_days)
        score = recent / prev - 1.0
        # Mask early period without enough history
        score = score.where(prev.notna() & recent.notna() & (prev > 0))
        return score
