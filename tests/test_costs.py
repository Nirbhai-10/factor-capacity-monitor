"""Cost-model sanity tests."""
import numpy as np
import pandas as pd
import pytest

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fcm.costs.impact import almgren_chriss_impact, execution_days_for_cap
from fcm.costs.spread import corwin_schultz_spread


def test_impact_monotonic_in_size():
    """Bigger trade → more impact."""
    adv = pd.Series([1e8, 1e8, 1e8], index=["A", "B", "C"])
    vol = pd.Series([0.30, 0.30, 0.30], index=["A", "B", "C"])
    trades_small = pd.Series([1e6, 1e6, 1e6], index=["A", "B", "C"])
    trades_big = pd.Series([1e7, 1e7, 1e7], index=["A", "B", "C"])

    impact_small = almgren_chriss_impact(trades_small, adv, vol)
    impact_big = almgren_chriss_impact(trades_big, adv, vol)

    assert (impact_big > impact_small).all()
    # roughly sqrt(10) ~ 3.16x for sqrt regime
    assert ((impact_big / impact_small).mean() > 2.5)


def test_impact_zero_when_no_trade():
    adv = pd.Series([1e8], index=["A"])
    vol = pd.Series([0.30], index=["A"])
    zero = pd.Series([0.0], index=["A"])
    assert almgren_chriss_impact(zero, adv, vol).iloc[0] == 0.0


def test_execution_days_satisfies_cap():
    adv = pd.Series([1e7, 1e8], index=["A", "B"])
    trade = pd.Series([1e6, 1e6], index=["A", "B"])  # 10% of A's ADV, 1% of B's
    days = execution_days_for_cap(trade, adv, participation_cap=0.05)
    # A needs 2 days (10% / 5%), B needs 1
    assert days.loc["A"] == 2.0
    assert days.loc["B"] == 1.0


def test_corwin_schultz_nonneg():
    """CS estimator is floored at 0 (negative values mean estimator failed)."""
    rng = np.random.default_rng(0)
    n = 100
    close = 100 + rng.standard_normal(n).cumsum()
    high = close + np.abs(rng.standard_normal(n)) * 0.3
    low = close - np.abs(rng.standard_normal(n)) * 0.3
    high_s = pd.Series(high, index=pd.date_range("2024-01-01", periods=n))
    low_s = pd.Series(low, index=pd.date_range("2024-01-01", periods=n))
    s = corwin_schultz_spread(high_s, low_s)
    assert (s.dropna() >= 0).all()
