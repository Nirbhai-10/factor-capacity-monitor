"""Capacity-engine smoke test on synthetic data."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd

from fcm import load_config
from fcm.capacity.curve import run_capacity_curve
from fcm.costs.spread import spread_panel
from fcm.data.synthetic import generate_panel
from fcm.factors.value import ValueFactor
from fcm.portfolio.backtest import Backtest
from fcm.portfolio.construction import RebalanceSchedule


def test_capacity_curve_monotone_decreasing_in_aum():
    cfg = load_config()
    sp = generate_panel(n_symbols=50, history_years=2, seed=7)
    panel = sp.market

    spreads = spread_panel(panel.high, panel.low, panel.dollar_volume)
    fac = ValueFactor()
    rank = fac.compute(panel).rank
    base_aum = cfg.capacity.base_aum_units * cfg.market.unit_value
    bt = Backtest(panel=panel, rebalance=RebalanceSchedule("M"), base_aum=base_aum)
    result = bt.run(rank, factor_name="value")
    curve = run_capacity_curve(backtest=result, panel=panel, spreads=spreads, cfg=cfg)

    df = curve.to_frame().sort_values("aum")
    # net_ir should be (weakly) decreasing in AUM
    assert df.net_ir.is_monotonic_decreasing or (df.net_ir.diff().dropna() <= 1e-6).all()
    # gross_ir should be constant — gross returns don't depend on AUM
    assert df.gross_ir.std() < 1e-6
    # cost should be (weakly) increasing in AUM in bps as well
    assert df.total_cost_bps.is_monotonic_increasing


def test_capacity_zones_sorted():
    """If we have any safe points, they should all sit at the lowest AUMs."""
    cfg = load_config()
    sp = generate_panel(n_symbols=50, history_years=2, seed=7)
    panel = sp.market

    spreads = spread_panel(panel.high, panel.low, panel.dollar_volume)
    fac = ValueFactor()
    rank = fac.compute(panel).rank
    base_aum = cfg.capacity.base_aum_units * cfg.market.unit_value
    bt = Backtest(panel=panel, rebalance=RebalanceSchedule("M"), base_aum=base_aum)
    result = bt.run(rank, factor_name="value")
    curve = run_capacity_curve(backtest=result, panel=panel, spreads=spreads, cfg=cfg)

    df = curve.to_frame().sort_values("aum")
    zones = df.zone.tolist()
    # Once we leave 'safe' we shouldn't go back
    leftsafe = False
    for z in zones:
        if z != "safe":
            leftsafe = True
        elif leftsafe:
            assert False, "saw 'safe' after a non-safe zone — non-monotonic capacity"
