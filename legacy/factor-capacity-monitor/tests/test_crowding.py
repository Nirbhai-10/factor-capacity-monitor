"""Crowding-monitor smoke tests."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fcm import load_config
from fcm.crowding.composite import composite_crowding_score
from fcm.data.synthetic import generate_panel
from fcm.factors.value import ValueFactor
from fcm.portfolio.backtest import Backtest
from fcm.portfolio.construction import RebalanceSchedule


def test_composite_score_in_range():
    cfg = load_config()
    sp = generate_panel(n_symbols=50, history_years=3, seed=11)
    panel = sp.market

    fac = ValueFactor()
    rank = fac.compute(panel).rank
    base_aum = cfg.capacity.base_aum_units * cfg.market.unit_value
    bt = Backtest(panel=panel, rebalance=RebalanceSchedule("M"), base_aum=base_aum)
    result = bt.run(rank, factor_name="value")

    weights = {k: float(cfg.crowding.weights[k]) for k in cfg.crowding.weights.keys()}
    score = composite_crowding_score(
        factor_name="value",
        weights_ts=result.target_weights_ts,
        panel=panel,
        daily_returns=result.daily_returns,
        base_aum=base_aum,
        weights=weights,
        other_factor_weights=None,
    )

    # Composite should be 0-100
    assert 0 <= score.latest_composite <= 100
    # Each component too
    for k, v in score.latest.items():
        assert 0 <= v <= 100, f"{k} = {v} out of range"
    # Alert level is one of three valid values
    assert score.alert_level in ("green", "amber", "red")
