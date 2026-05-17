"""Quality factor: ROE proxies profitability. Higher ROE = predicted winner."""
from __future__ import annotations

import pandas as pd

from ..data.types import MarketPanel
from .base import FactorSignal


class QualityFactor(FactorSignal):
    name = "quality"

    def compute_score(self, panel: MarketPanel) -> pd.DataFrame:
        return panel.roe
