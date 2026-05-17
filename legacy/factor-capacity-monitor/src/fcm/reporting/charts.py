"""Plotly charts for the dashboard / memo."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from ..capacity.curve import CapacityCurve
from ..crowding.composite import CrowdingScore


_ZONE_COLORS = {"safe": "#2ca02c", "caution": "#ff9f40", "red": "#d62728"}


def plot_capacity_curve(curve: CapacityCurve, unit_label: str = "cr") -> go.Figure:
    df = curve.to_frame()
    fig = go.Figure()
    for zone, color in _ZONE_COLORS.items():
        sub = df[df.zone == zone]
        if not sub.empty:
            fig.add_trace(go.Scatter(
                x=sub.aum, y=sub.net_ir, mode="markers",
                name=f"{zone} zone", marker=dict(color=color, size=12),
            ))
    fig.add_trace(go.Scatter(
        x=df.aum, y=df.net_ir, mode="lines", name="Net IR",
        line=dict(color="#1f77b4", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=df.aum, y=df.gross_ir, mode="lines", name="Gross IR",
        line=dict(color="#aaaaaa", width=1, dash="dot"),
    ))
    fig.add_hline(y=0.5, line_dash="dash", annotation_text="IR=0.5 hurdle")
    fig.update_layout(
        title=f"Capacity curve — {curve.factor_name}",
        xaxis_title=f"AUM ({unit_label})", yaxis_title="IR (annualised)",
        xaxis_type="log", template="plotly_white",
    )
    return fig


def plot_cost_breakdown(curve: CapacityCurve, unit_label: str = "cr") -> go.Figure:
    df = curve.to_frame()
    fig = go.Figure()
    for col, color in [
        ("spread_bps", "#1f77b4"),
        ("impact_bps", "#ff7f0e"),
        ("commission_bps", "#2ca02c"),
        ("borrow_bps", "#d62728"),
        ("india_bps", "#9467bd"),
    ]:
        fig.add_trace(go.Bar(x=df.aum, y=df[col], name=col.replace("_bps", "")))
    fig.update_layout(
        barmode="stack",
        title=f"Cost breakdown vs AUM — {curve.factor_name}",
        xaxis_title=f"AUM ({unit_label})",
        yaxis_title="Cost (bps annualised)",
        xaxis_type="log",
        template="plotly_white",
    )
    return fig


def plot_crowding(score: CrowdingScore) -> go.Figure:
    df = score.timeseries.copy()
    df["composite"] = score.composite
    fig = go.Figure()
    for col in df.columns:
        if col == "composite":
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col], name="Composite",
                line=dict(color="black", width=3),
            ))
        else:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col], name=col, opacity=0.6,
            ))
    fig.add_hline(y=75, line_dash="dash", line_color="red", annotation_text="red")
    fig.add_hline(y=50, line_dash="dash", line_color="orange", annotation_text="amber")
    fig.update_layout(
        title=f"Crowding score components — {score.factor_name}",
        yaxis_title="Score (0-100, higher = more crowded)",
        template="plotly_white",
    )
    return fig
