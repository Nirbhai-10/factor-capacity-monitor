#!/usr/bin/env python3
"""Run the full pipeline including the ML layer and serialise everything
the Next.js app needs into a single JSON file: web/lib/data.json.

Run from repo root:
    python scripts/build_web_data.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd

from fcm import load_config
from fcm.capacity.curve import run_capacity_curve
from fcm.capacity.multi_factor import allocate_multifactor
from fcm.costs.spread import spread_panel
from fcm.crowding.composite import composite_crowding_score
from fcm.data.synthetic import generate_panel
from fcm.factors.registry import build_factor
from fcm.ml.alpha_forecast import forecast_alpha_decay
from fcm.ml.capacity_model import fit_capacity_ridge
from fcm.ml.regime import classify_regime
from fcm.policy.checkpoints import compute_checkpoints
from fcm.policy.search import search_policy
from fcm.portfolio.backtest import Backtest
from fcm.portfolio.construction import RebalanceSchedule
from fcm.stress.scenarios import run_stress


def _ts(s: pd.Series, sample: int = 200):
    """Downsample a series for the web (every kth point)."""
    if s.empty:
        return []
    step = max(1, len(s) // sample)
    s = s.iloc[::step]
    return [{"date": str(d.date()), "value": float(v) if pd.notna(v) else None}
            for d, v in s.items()]


def _components_ts(df: pd.DataFrame, sample: int = 200):
    if df.empty:
        return []
    step = max(1, len(df) // sample)
    df = df.iloc[::step]
    return [
        {"date": str(d.date()), **{c: float(df.loc[d, c]) for c in df.columns}}
        for d in df.index
    ]


def main():
    cfg = load_config()
    print("• generating synthetic panel")
    sp = generate_panel(
        n_symbols=cfg.universe.size,
        history_years=cfg.universe.history_years,
        seed=42,
    )
    panel = sp.market

    print("• estimating spreads")
    spreads = spread_panel(
        panel.high, panel.low, panel.dollar_volume,
        floor_bps=cfg.costs.spread.floor_bps,
        cap_bps=cfg.costs.spread.cap_bps,
    )

    base_aum = cfg.capacity.base_aum_units * cfg.market.unit_value
    schedule = RebalanceSchedule(freq=cfg.factors.rebalance_freq)
    factors = {n: build_factor(n, cfg) for n in cfg.factors.enabled}

    backtests, curves, crowding, stress, policy, checkpoints = {}, {}, {}, {}, {}, {}
    for name, fac in factors.items():
        print(f"• backtest {name}")
        rank = fac.compute(panel).rank
        bt = Backtest(panel=panel, long_q=cfg.factors.long_quantile,
                       short_q=cfg.factors.short_quantile,
                       rebalance=schedule, base_aum=base_aum)
        backtests[name] = bt.run(rank, factor_name=name)

    other_w = {n: bt.target_weights_ts for n, bt in backtests.items()}
    weight_cfg = {k: float(cfg.crowding.weights[k]) for k in cfg.crowding.weights.keys()}

    for name, bt_res in backtests.items():
        print(f"• capacity & crowding {name}")
        curves[name] = run_capacity_curve(
            backtest=bt_res, panel=panel, spreads=spreads, cfg=cfg,
        )
        crowding[name] = composite_crowding_score(
            factor_name=name, weights_ts=bt_res.target_weights_ts,
            panel=panel, daily_returns=bt_res.daily_returns,
            base_aum=base_aum, weights=weight_cfg,
            other_factor_weights=[w for n, w in other_w.items() if n != name],
            alert_thresholds=(cfg.crowding.alert_thresholds.score_amber,
                              cfg.crowding.alert_thresholds.score_red),
        )

    print("• regime classification (GMM)")
    regime = classify_regime(panel, spreads, k=3)

    for name, bt_res in backtests.items():
        print(f"• stress + policy {name}")
        stress[name] = run_stress(
            backtest=bt_res, panel=panel, spreads=spreads, cfg=cfg,
        )
        target_aum = curves[name].safe_capacity() or base_aum
        policy[name] = search_policy(
            factor=factors[name], panel=panel, cfg=cfg, target_aum=target_aum,
        )
        checkpoints[name] = compute_checkpoints(
            curves[name].safe_capacity() or 0,
            list(cfg.policy.checkpoints_pct_of_safe),
        )

    print("• ML: alpha-decay forecasts")
    forecasts = {}
    for name, bt_res in backtests.items():
        # Crowding score sampled daily by ffill (it's per-rebalance natively)
        crowd_daily = crowding[name].composite.reindex(
            bt_res.daily_returns.index, method="ffill"
        ).fillna(50.0)
        forecasts[name] = forecast_alpha_decay(
            bt_res.daily_returns, crowd_daily, horizon_days=126,
        )

    print("• ML: capacity ridge model")
    # Build a small training panel: rolling windows with (features, safe_aum)
    # We synthesise samples by running the curve over rolling windows of the
    # backtest. To keep build time small, sample 6 windows per factor.
    rows = []
    for name, bt_res in backtests.items():
        if len(bt_res.daily_returns) < 252:
            continue
        windows = np.linspace(0.5, 1.0, 6)
        for w in windows:
            end = int(len(bt_res.daily_returns) * w)
            start = max(0, end - 252)
            sub_dates = bt_res.daily_returns.index[start:end]
            sub_returns = bt_res.daily_returns.loc[sub_dates]
            if sub_returns.std() == 0:
                continue
            gross_ir = float(sub_returns.mean() / sub_returns.std() * np.sqrt(252))
            spread_med = float((spreads.loc[sub_dates] * 10_000).median().median())
            adv_med = float(np.log10(panel.dollar_volume.loc[sub_dates].median().median() + 1))
            vol_med = float(panel.realised_vol(20).loc[sub_dates].median().median())
            crowd_score = float(crowding[name].composite.reindex(sub_dates, method="ffill").mean())
            safe = curves[name].safe_capacity() or 1.0
            rows.append({
                "spread_bps": spread_med, "vol": vol_med, "log_adv": adv_med,
                "crowding": crowd_score, "gross_ir": gross_ir,
                "safe_aum": float(safe),
            })
    feat_panel = pd.DataFrame(rows)
    feature_names = ["spread_bps", "vol", "log_adv", "crowding", "gross_ir"]
    cap_model = fit_capacity_ridge(feat_panel, feature_names)

    print("• multi-factor allocation")
    crowding_latest = {n: cr.latest_composite for n, cr in crowding.items()}
    total_aum = max((c.safe_capacity() or 0 for c in curves.values()), default=base_aum) * 2
    multi = allocate_multifactor(
        curves=curves, total_aum=total_aum,
        crowding_scores=crowding_latest,
        max_crowding_score=cfg.crowding.alert_thresholds.score_red,
    )

    # Serialise -----------------------------------------------------------
    print("• writing JSON")
    payload = {
        "meta": {
            "currency": cfg.market.base_currency,
            "unit_label": cfg.market.unit_label,
            "unit_value": cfg.market.unit_value,
            "rebalance_freq": cfg.factors.rebalance_freq,
            "history_years": cfg.universe.history_years,
            "n_symbols": cfg.universe.size,
            "factors": list(factors.keys()),
        },
        "regime": {
            "current": regime.current_regime,
            "probabilities": regime.current_probabilities,
            "centroids": regime.centroids.to_dict(orient="index"),
            "history": _components_ts(regime.probabilities, sample=120),
        },
        "factors": {},
        "multi_factor": {
            "weights": multi.weights,
            "aum_allocations": multi.aum_allocations,
            "expected_net_return_pct": multi.expected_net_return_pct,
            "expected_net_return_dollars": multi.expected_net_return_dollars,
            "factor_irs": multi.factor_irs,
            "total_aum": float(total_aum),
        },
        "ml": {
            "capacity_model": {
                "coefficients": cap_model.coefficients,
                "intercept": cap_model.intercept,
                "lambda": cap_model.lambda_,
                "r2": cap_model.r2_in_sample,
                "feature_names": cap_model.feature_names,
            },
        },
    }

    for name in factors:
        c = curves[name]
        cs = crowding[name]
        st = stress[name]
        pol = policy[name]
        cps = checkpoints[name]
        bt = backtests[name]
        fc = forecasts[name]

        payload["factors"][name] = {
            "name": name,
            "gross_ir": float(c.points[0].gross_ir if c.points else 0),
            "safe_capacity": c.safe_capacity(),
            "ir50_capacity": c.ir_threshold_capacity(0.5),
            "stress_safe_capacity": st.stressed.safe_capacity(),
            "crowding_latest": cs.latest_composite,
            "alert_level": cs.alert_level,
            "crowding_components_latest": cs.latest,
            "best_policy": {
                "freq": pol.best_freq,
                "buffer_bps": pol.best_buffer_bps,
                "net_ir": pol.best_net_ir,
                "target_aum": pol.target_aum,
            },
            "policy_grid": pol.grid.to_dict(orient="records"),
            "checkpoints": [
                {"pct_of_safe": cp.pct_of_safe, "aum": cp.aum, "rule": cp.rule}
                for cp in cps
            ],
            "curve": c.to_frame().to_dict(orient="records"),
            "stress_curve": st.stressed.to_frame().to_dict(orient="records"),
            "redemption_unwind": [
                {"aum": float(a), "unwind_bps": float(b)} for a, b in st.redemption.items()
            ],
            "crowding_components": _components_ts(cs.timeseries, sample=120),
            "crowding_composite": _ts(cs.composite, sample=120),
            "ml_forecast": {
                "fitted_kappa": fc.fitted_kappa,
                "fitted_alpha": fc.fitted_alpha,
                "fitted_beta": fc.fitted_beta,
                "half_life_days": fc.half_life_days,
                "rmse": fc.rmse_in_sample,
                "forecast": _ts(fc.forecast, sample=120),
                "fan_lower": _ts(fc.fan_lower, sample=120),
                "fan_upper": _ts(fc.fan_upper, sample=120),
            },
            "daily_returns": _ts(bt.daily_returns.fillna(0).cumsum(), sample=200),
        }

    out = ROOT / "web" / "lib" / "data.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, default=str))
    print(f"  → {out} ({out.stat().st_size / 1024:.1f} KB)")
    print("done.")


if __name__ == "__main__":
    main()
