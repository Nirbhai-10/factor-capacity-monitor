"""Base classes for factor signals.

A FactorSignal takes a MarketPanel and returns a `score` DataFrame
(dates × symbols). Higher score → predicted winner. The downstream
portfolio constructor turns this into long/short weights via cross-sectional
rank-quantile cutoffs.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..data.types import MarketPanel


@dataclass
class RankedSignal:
    name: str
    score: pd.DataFrame                # higher = predicted winner
    rank: pd.DataFrame                 # cross-sectional rank in [0, 1]


class FactorSignal(ABC):
    """Abstract factor signal. Subclasses implement `compute_score`."""

    name: str = "factor"

    @abstractmethod
    def compute_score(self, panel: MarketPanel) -> pd.DataFrame:
        """Return a dates × symbols score DataFrame."""

    def cross_sectional_rank(self, score: pd.DataFrame) -> pd.DataFrame:
        """Rank within each row, normalised to [0, 1]. NaNs preserved."""
        ranked = score.rank(axis=1, pct=True, method="average")
        return ranked

    def compute(self, panel: MarketPanel) -> RankedSignal:
        score = self.compute_score(panel)
        rank = self.cross_sectional_rank(score)
        return RankedSignal(name=self.name, score=score, rank=rank)


def winsorize_zscore(x: pd.DataFrame, limit: float = 3.0) -> pd.DataFrame:
    """Cross-sectional z-score per row, clipped to ±`limit`σ."""
    mean = x.mean(axis=1)
    std = x.std(axis=1).replace(0, np.nan)
    z = x.sub(mean, axis=0).div(std, axis=0)
    return z.clip(-limit, limit)
