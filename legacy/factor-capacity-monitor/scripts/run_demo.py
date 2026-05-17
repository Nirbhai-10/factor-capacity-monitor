#!/usr/bin/env python3
"""End-to-end demo on synthetic NIFTY-100-like data.

Run from repo root:
    python scripts/run_demo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make src/ importable when running directly without `pip install -e`
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import json
import time

import pandas as pd
import plotly.io as pio
from rich.console import Console
from rich.table import Table

from fcm import load_config
from fcm.capacity.curve import run_capacity_curve
from fcm.capacity.multi_factor import allocate_multifactor
from fcm.costs.spread import spread_panel
from fcm.crowding.composite import composite_crowding_score
from fcm.data.synthetic import generate_panel
from fcm.factors.registry import build_factor
from fcm.policy.checkpoints import compute_checkpoints
from fcm.policy.search import search_policy
from fcm.portfolio.backtest import Backtest
from fcm.portfolio.construction import RebalanceSchedule
from fcm.reporting.charts import (
    plot_capacity_curve, plot_cost_breakdown, plot_crowding,
)
from fcm.reporting.memo import write_memo
from fcm.stress.scenarios import run_stress

console = Console()


def main():
    cfg = load_config()
    out_dir = ROOT / cfg.reporting.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    unit_value = cfg.market.unit_value
    unit_label = cfg.market.unit_label

    # 1. Generate synthetic panel
    console.rule("[bold cyan]1/7 generate synthetic panel")
    t0 = time.time()
    sp = generate_panel(
        n_symbols=cfg.universe.size,
        history_years=cfg.universe.history_years,
        seed=42,
    )
    panel = sp.market
    console.log(f"  panel: {panel.close.shape[0]} dates × {panel.close.shape[1]} symbols  "
                f"({time.time()-t0:.1f}s)")

    # 2. Spreads
    console.rule("[bold cyan]2/7 estimate spreads (Corwin-Schultz)")
    t0 = time.time()
    spreads = spread_panel(
        panel.high, panel.low, panel.dollar_volume,
        floor_bps=cfg.costs.spread.floor_bps,
        cap_bps=cfg.costs.spread.cap_bps,
    )
    median_spread_bps = (spreads.iloc[-1] * 10_000).median()
    console.log(f"  spread panel built. Latest median spread: {median_spread_bps:.0f} bps  "
                f"({time.time()-t0:.1f}s)")

    # 3. Per-factor backtest
    console.rule("[bold cyan]3/7 build factors and backtest")
    base_aum = cfg.capacity.base_aum_units * unit_value
    schedule = RebalanceSchedule(freq=cfg.factors.rebalance_freq)

    factors = {name: build_factor(name, cfg) for name in cfg.factors.enabled}
    backtests = {}
    for name, fac in factors.items():
        ranked = fac.compute(panel)
        bt = Backtest(
            panel=panel,
            long_q=cfg.factors.long_quantile,
            short_q=cfg.factors.short_quantile,
            rebalance=schedule,
            base_aum=base_aum,
        )
        result = bt.run(ranked.rank, factor_name=name)
        backtests[name] = result
        console.log(f"  {name}: gross IR = {result.gross_ir:.2f}, "
                    f"{len(result.rebalances)} rebalances")

    # 4. Capacity curves
    console.rule("[bold cyan]4/7 capacity curves")
    curves = {}
    for name, bt_res in backtests.items():
        t0 = time.time()
        curve = run_capacity_curve(
            backtest=bt_res, panel=panel, spreads=spreads, cfg=cfg,
        )
        curves[name] = curve
        safe = curve.safe_capacity() or 0
        ir50 = curve.ir_threshold_capacity(0.5) or 0
        console.log(
            f"  {name}: safe={safe / unit_value:,.1f}{unit_label} "
            f"  IR≥0.5={ir50 / unit_value:,.1f}{unit_label}  "
            f"({time.time()-t0:.1f}s)"
        )

    # 5. Crowding scores
    console.rule("[bold cyan]5/7 crowding scores")
    crowding = {}
    other_weights = {n: bt.target_weights_ts for n, bt in backtests.items()}
    for name, bt_res in backtests.items():
        others = [w for n, w in other_weights.items() if n != name]
        score = composite_crowding_score(
            factor_name=name,
            weights_ts=bt_res.target_weights_ts,
            panel=panel,
            daily_returns=bt_res.daily_returns,
            base_aum=base_aum,
            weights={k: float(cfg.crowding.weights[k]) for k in cfg.crowding.weights.keys()},
            other_factor_weights=others,
            alert_thresholds=(cfg.crowding.alert_thresholds.score_amber,
                              cfg.crowding.alert_thresholds.score_red),
        )
        crowding[name] = score
        console.log(f"  {name}: composite = {score.latest_composite:.0f}  "
                    f"({score.alert_level})")

    # 6. Stress + policy + checkpoints
    console.rule("[bold cyan]6/7 stress, policy, checkpoints")
    stress = {}
    policy = {}
    checkpoints = {}
    for name, bt_res in backtests.items():
        st = run_stress(
            backtest=bt_res, panel=panel, spreads=spreads, cfg=cfg,
        )
        stress[name] = st
        target_aum = curves[name].safe_capacity() or base_aum
        pol = search_policy(
            factor=factors[name], panel=panel, cfg=cfg, target_aum=target_aum,
        )
        policy[name] = pol
        checkpoints[name] = compute_checkpoints(
            curves[name].safe_capacity() or 0,
            list(cfg.policy.checkpoints_pct_of_safe),
        )
        console.log(
            f"  {name}: stress safe={(st.stressed.safe_capacity() or 0)/unit_value:,.1f}{unit_label}  "
            f"  best policy = {pol.best_freq}/{int(pol.best_buffer_bps)}bps "
            f"(net IR {pol.best_net_ir:.2f})"
        )

    # 7. Multi-factor allocation + memo + charts
    console.rule("[bold cyan]7/7 multi-factor allocation + reports")
    total_aum = max((c.safe_capacity() or 0 for c in curves.values()), default=base_aum) * 2
    crowding_latest = {n: cr.latest_composite for n, cr in crowding.items()}
    multi = allocate_multifactor(
        curves=curves,
        total_aum=total_aum,
        crowding_scores=crowding_latest,
        max_crowding_score=cfg.crowding.alert_thresholds.score_red,
    )

    # Charts: write each to HTML
    for name, curve in curves.items():
        pio.write_html(plot_capacity_curve(curve, unit_label),
                       file=str(out_dir / f"{name}_capacity_curve.html"), auto_open=False)
        pio.write_html(plot_cost_breakdown(curve, unit_label),
                       file=str(out_dir / f"{name}_cost_breakdown.html"), auto_open=False)
    for name, score in crowding.items():
        pio.write_html(plot_crowding(score),
                       file=str(out_dir / f"{name}_crowding.html"), auto_open=False)

    memo_path = write_memo(
        output_path=out_dir / "memo.md",
        factor_curves=curves,
        crowding_scores=crowding,
        stress_results=stress,
        policy_results=policy,
        checkpoints=checkpoints,
        multi_factor=multi,
        unit_value=unit_value,
        unit_label=unit_label,
    )

    # CSV dumps for the dashboard
    for name, curve in curves.items():
        curve.to_frame().to_csv(out_dir / f"{name}_curve.csv", index=False)
        crowding[name].timeseries.to_csv(out_dir / f"{name}_crowding_components.csv")
        crowding[name].composite.to_csv(out_dir / f"{name}_crowding_composite.csv",
                                         header=["composite"])

    summary = {
        "factors": list(factors),
        "safe_capacity": {n: c.safe_capacity() for n, c in curves.items()},
        "crowding_latest": crowding_latest,
        "multi_factor_weights": multi.weights,
        "multi_factor_aum_alloc": multi.aum_allocations,
        "expected_net_return_pct": multi.expected_net_return_pct,
        "memo_path": str(memo_path),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))

    # Pretty print
    console.rule("[bold green]Done")
    table = Table(title="Capacity & crowding summary")
    table.add_column("Factor")
    table.add_column("Safe AUM")
    table.add_column("IR≥0.5 AUM")
    table.add_column("Stress safe")
    table.add_column("Crowding (level)")
    table.add_column("Best policy")
    for name in factors:
        c = curves[name]
        st = stress[name]
        cr = crowding[name]
        pol = policy[name]
        table.add_row(
            name,
            f"{(c.safe_capacity() or 0) / unit_value:,.1f}{unit_label}",
            f"{(c.ir_threshold_capacity(0.5) or 0) / unit_value:,.1f}{unit_label}",
            f"{(st.stressed.safe_capacity() or 0) / unit_value:,.1f}{unit_label}",
            f"{cr.latest_composite:.0f} ({cr.alert_level})",
            f"{pol.best_freq}/{int(pol.best_buffer_bps)}bps",
        )
    console.print(table)
    console.print(f"\nMemo:    [cyan]{memo_path}[/cyan]")
    console.print(f"Charts:  [cyan]{out_dir}/*.html[/cyan]")


if __name__ == "__main__":
    main()
