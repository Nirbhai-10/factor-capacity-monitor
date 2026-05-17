"""Value factor: low P/B is "cheap" → predicted winner.

Score = -log(P/B) so higher score = cheaper.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..data.types import MarketPanel
from .base import FactorSignal


class ValueFactor(FactorSignal):
    name = "value"

    def compute_score(self, panel: MarketPanel) -> pd.DataFrame:
        pb = panel.pb.replace(0, np.nan)
        return -np.log(pb)
