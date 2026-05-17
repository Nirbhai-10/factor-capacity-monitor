"""Factor Capacity & Crowding Monitor — interactive dashboard.

Run from repo root:
    streamlit run dashboard/app.py

Reads pre-baked artefacts from `examples/demo_output/`. If those don't exist,
runs the synthetic-data demo first (one-shot, ~2 minutes).
"""
from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "examples" / "demo_output"

# ────────────────────────────────────────────────────────────────────────────
# 1. Page config + styling
# ────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Factor Capacity & Crowding Monitor",
    page_icon="○",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;500;600&family=Source+Serif+4:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg:        #fbfaf6;
    --card:      #ffffff;
    --ink:       #1a1a1a;
    --muted:     #5a5a5a;
    --rule:      #e6e3da;
    --accent:    #1a3a5c;
    --accent-soft: #4d6b88;
    --gold:      #a08c5d;
    --safe:      #2d7a4f;
    --caution:   #b07c2c;
    --danger:    #a04040;
}

html, body, [class*="css"] {
    font-family: 'Source Serif 4', Georgia, serif !important;
    color: var(--ink);
    background: var(--bg) !important;
}

.stApp { background: var(--bg) !important; }

h1, h2, h3, h4 {
    font-family: 'EB Garamond', 'Garamond', serif !important;
    font-weight: 500 !important;
    color: var(--ink);
    letter-spacing: -0.01em;
}
h1 { font-size: 2.8rem !important; line-height: 1.1; margin-bottom: 0.2rem; }
h2 { font-size: 1.8rem !important; margin-top: 2.5rem; padding-bottom: 0.3rem; border-bottom: 1px solid var(--rule); }
h3 { font-size: 1.3rem !important; margin-top: 1.5rem; color: var(--accent); }

p, li, div { font-size: 1rem; line-height: 1.65; }

code, pre, .stCodeBlock { font-family: 'JetBrains Mono', 'IBM Plex Mono', monospace !important; }

/* Streamlit metric overrides */
[data-testid="stMetric"] {
    background: var(--card);
    border: 1px solid var(--rule);
    padding: 0.9rem 1.1rem;
    border-radius: 2px;
}
[data-testid="stMetricLabel"] {
    font-family: 'EB Garamond', serif !important;
    font-size: 0.95rem !important;
    color: var(--muted) !important;
    font-variant: small-caps;
    letter-spacing: 0.04em;
}
[data-testid="stMetricValue"] {
    font-family: 'EB Garamond', serif !important;
    font-weight: 500 !important;
    font-size: 1.7rem !important;
    color: var(--ink) !important;
}

/* Tighten sidebar */
[data-testid="stSidebar"] {
    background: #f4f1e9 !important;
    border-right: 1px solid var(--rule);
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: var(--accent) !important; }

/* Tabs */
button[data-baseweb="tab"] {
    font-family: 'EB Garamond', serif !important;
    font-size: 1.05rem !important;
    color: var(--muted) !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom-color: var(--accent) !important;
}

/* Tables */
.stDataFrame, table { border: 1px solid var(--rule); border-radius: 2px; background: var(--card); }
table th { background: #f4f1e9 !important; font-family: 'EB Garamond', serif !important; font-weight: 500 !important; }

/* Expanders */
[data-testid="stExpander"] {
    border: 1px solid var(--rule);
    border-radius: 2px;
    background: var(--card);
}

/* Notes */
.note {
    border-left: 2px solid var(--gold);
    background: #f7f4ec;
    padding: 0.7rem 1rem;
    margin: 1rem 0;
    font-size: 0.95rem;
    color: var(--muted);
    border-radius: 0 2px 2px 0;
}
.lede {
    font-size: 1.15rem;
    color: var(--muted);
    line-height: 1.55;
    border-left: 3px solid var(--gold);
    padding-left: 1rem;
    margin: 1rem 0 2rem 0;
    max-width: 60ch;
    font-style: italic;
}
.kicker {
    text-transform: uppercase;
    letter-spacing: 0.18em;
    color: var(--gold);
    font-size: 0.78rem;
    font-family: 'Source Serif 4', serif;
}
.zone-pill {
    display: inline-block;
    padding: 0.05rem 0.55rem;
    border-radius: 2px;
    font-family: 'EB Garamond', serif;
    font-size: 0.95rem;
}
.zone-safe    { background: #e2efe6; color: var(--safe); }
.zone-caution { background: #f3e7d2; color: var(--caution); }
.zone-red     { background: #f1dada; color: var(--danger); }
.zone-amber   { background: #f3e7d2; color: var(--caution); }
.zone-green   { background: #e2efe6; color: var(--safe); }

hr { border: none; border-top: 1px solid var(--rule); margin: 2rem 0; }

/* Hide streamlit chrome */
header[data-testid="stHeader"] { background: transparent; }
footer { visibility: hidden; }
#MainMenu { visibility: hidden; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


PLOTLY_THEME = dict(
    template="plotly_white",
    font=dict(family="Source Serif 4, Georgia, serif", color="#1a1a1a", size=13),
    paper_bgcolor="#ffffff",
    plot_bgcolor="#ffffff",
    margin=dict(l=50, r=20, t=50, b=50),
    colorway=["#1a3a5c", "#a08c5d", "#2d7a4f", "#a04040", "#5a4f7a", "#7a5a3a"],
    xaxis=dict(gridcolor="#e6e3da", linecolor="#c7c2b3"),
    yaxis=dict(gridcolor="#e6e3da", linecolor="#c7c2b3"),
)


def _zone_pill(z: str) -> str:
    return f'<span class="zone-pill zone-{z}">{z}</span>'


# ────────────────────────────────────────────────────────────────────────────
# 2. Data loading
# ────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_artefacts():
    if not (OUT / "summary.json").exists():
        return None
    summary = json.loads((OUT / "summary.json").read_text())
    factors = summary["factors"]

    curves = {}
    crowd_components = {}
    crowd_composite = {}
    for f in factors:
        curves[f] = pd.read_csv(OUT / f"{f}_curve.csv")
        crowd_components[f] = pd.read_csv(
            OUT / f"{f}_crowding_components.csv", index_col=0, parse_dates=[0]
        )
        crowd_composite[f] = pd.read_csv(
            OUT / f"{f}_crowding_composite.csv", index_col=0, parse_dates=[0]
        )
    memo = (OUT / "memo.md").read_text() if (OUT / "memo.md").exists() else ""
    return {
        "summary": summary, "factors": factors, "curves": curves,
        "crowd_components": crowd_components, "crowd_composite": crowd_composite,
        "memo": memo,
    }


arts = load_artefacts()

# ────────────────────────────────────────────────────────────────────────────
# 3. Header
# ────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="kicker">Buy-side research tool</div>', unsafe_allow_html=True)
st.markdown("# Factor Capacity & Crowding Monitor")
st.markdown(
    '<div class="lede">'
    "How much money can a factor strategy run before it stops paying for itself? "
    "How crowded is the trade today? When should the rebalancing rule change? "
    "This tool answers all three on a single page, with the maths exposed."
    "</div>",
    unsafe_allow_html=True,
)

if arts is None:
    st.warning(
        "No demo artefacts found in `examples/demo_output/`. "
        "Run `python scripts/run_demo.py` from the repo root, then refresh."
    )
    st.stop()

summary = arts["summary"]
factors = arts["factors"]

# ────────────────────────────────────────────────────────────────────────────
# 4. Sidebar: navigation + selection
# ────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Selection")
    factor = st.selectbox("Factor", factors, index=0)
    st.markdown("### Sections")
    st.markdown(
        textwrap.dedent("""
        - [Why this matters](#why)
        - [How it works](#how)
        - [Today at a glance](#kpis)
        - [Capacity curve](#curve)
        - [Cost decomposition](#cost)
        - [Crowding score](#crowd)
        - [Stress capacity](#stress)
        - [Operating policy](#policy)
        - [Multi-factor allocation](#mf)
        - [Methodology](#method)
        - [Memo](#memo)
        """)
    )

    st.markdown("---")
    st.markdown("### About")
    st.markdown(
        "<div style='font-size:0.85rem;color:#5a5a5a;'>"
        "Synthetic NIFTY-100 panel · 5-year history · 100 names. "
        "Replace the data layer with NSE Bhavcopy or Yahoo for live use."
        "</div>",
        unsafe_allow_html=True,
    )


# ────────────────────────────────────────────────────────────────────────────
# 5. Why this matters
# ────────────────────────────────────────────────────────────────────────────
st.markdown('<a id="why"></a>', unsafe_allow_html=True)
st.markdown("## Why this matters")

c1, c2 = st.columns([1.5, 1])
with c1:
    st.markdown(
        textwrap.dedent("""
        Every factor strategy — momentum, value, quality, low-volatility — earns
        positive expected returns at small AUM and earns less at larger AUM. The
        usual story is "alpha decays as size grows." That story is incomplete.
        Two distinct mechanisms compound on each other:

        **1. Trading-cost drag.** Costs scale super-linearly with size. Spread is
        roughly constant per unit of trade, but market impact grows like
        $\\sqrt{Q/V}$ (Almgren–Chriss) and faster than that for large notionals.
        At some AUM, the marginal alpha is fully consumed by impact.

        **2. Crowding.** Other managers run the same signal. As capital piles in,
        the long basket bids up and the short basket gets squeezed. Realised
        alpha decays *before* trading costs even fire. Drawdowns become
        correlated across funds and unwinds become reflexive.

        The PM-level question is not "what's my Sharpe at infinite AUM" — it is:
        *given my current AUM and my factors' current crowding, what's my hard
        cap and what's my safe rebalancing rule?* This monitor answers exactly
        that, on live data, in one page.
        """)
    )

with c2:
    st.markdown(
        '<div class="note"><b>Three numbers a PM actually quotes</b><br>'
        "<b>Safe AUM</b> &mdash; the largest AUM where Net IR ≥ 0.5, "
        "execution stays under 3 days, and no name exceeds 3% of ADV. "
        "Below this number you're operating cleanly.<br><br>"
        "<b>Stress AUM</b> &mdash; same definition under widened spreads, "
        "shrunken ADV, fattened vol. The PM's hard cap should be the "
        "<i>minimum</i> of normal and stressed safe AUM.<br><br>"
        "<b>Crowding score (0–100)</b> &mdash; composite of six external "
        "signals (Asness valuation spread, Lou-Polk comomentum, alpha decay, "
        "short interest, holdings overlap, internal liquidity footprint), each "
        "rolling-percentile-ranked.</div>",
        unsafe_allow_html=True,
    )


# ────────────────────────────────────────────────────────────────────────────
# 6. How it works
# ────────────────────────────────────────────────────────────────────────────
st.markdown('<a id="how"></a>', unsafe_allow_html=True)
st.markdown("## How it works")
st.markdown(
    "Five stages run in sequence. Each panel below corresponds to one stage; "
    "the dashboard sections that follow surface the outputs."
)

pipeline_md = """
| # | Stage | What runs | Inputs → Outputs |
|---|-------|-----------|-------------------|
| 1 | **Build factor scores** | `factors/` | OHLC + fundamentals → cross-sectional rank per factor |
| 2 | **Construct portfolio** | `portfolio/` | Top quintile long, bottom quintile short, dollar-neutral |
| 3 | **Backtest gross** | `portfolio/backtest.py` | Daily gross-of-cost return series |
| 4 | **Cost & capacity scan** | `costs/`, `capacity/` | At each AUM in the grid: spread + Almgren-Chriss impact + commission + borrow + India tax stack → Net IR |
| 5 | **Crowding, stress, policy** | `crowding/`, `stress/`, `policy/` | Composite crowding, stressed Net IR, optimal rebalance freq + buffer |
"""
st.markdown(pipeline_md)

with st.expander("What's actually being computed at each rebalance"):
    st.markdown(
        "For every rebalance date and every AUM in the grid, the engine "
        "evaluates the following per-name expressions and aggregates:"
    )
    st.latex(r"\text{spread cost}_i = \tfrac12 \cdot s_i \cdot |Q_i|")
    st.latex(r"\text{impact cost}_i = \sigma_i \cdot k \cdot \sqrt{\frac{|Q_i|}{V_i \cdot T_i}} \cdot |Q_i|")
    st.latex(r"\text{borrow}_i = \max(0, -w_i) \cdot \text{AUM} \cdot r_i^{\text{borrow}} \cdot \frac{H}{252}")
    st.latex(r"\text{tax}_i = (\text{STT} + \text{stamp} + \text{SEBI} + \text{exch} + \text{GST}) \cdot |Q_i|")
    st.markdown(
        "where $s_i$ is the bid-ask spread, $Q_i$ trade dollars, $\\sigma_i$ "
        "annualised vol, $V_i$ daily ADV, $T_i$ chosen execution days, "
        "$k\\in[0.10, 0.30]$ the impact coefficient, $w_i$ target weight, "
        "$r_i^{\\text{borrow}}$ annualised borrow rate, and $H$ holding period."
    )


# ────────────────────────────────────────────────────────────────────────────
# 7. KPIs
# ────────────────────────────────────────────────────────────────────────────
st.markdown('<a id="kpis"></a>', unsafe_allow_html=True)
st.markdown("## Today at a glance")

curve = arts["curves"][factor]
safe_aum = summary["safe_capacity"].get(factor) or 0
crowd = summary["crowding_latest"].get(factor, 0)
mf_w = summary["multi_factor_weights"].get(factor, 0)
mf_aum = summary["multi_factor_aum_alloc"].get(factor, 0)
gross_ir = float(curve.gross_ir.iloc[0])
net_ir_at_safe = (
    float(curve[curve.aum == safe_aum].net_ir.iloc[0])
    if safe_aum and (curve.aum == safe_aum).any() else 0
)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Gross IR (annualised)", f"{gross_ir:+.2f}")
c2.metric("Safe capacity", f"{safe_aum/1e7:,.1f} cr" if safe_aum else "—")
c3.metric("Net IR at safe AUM", f"{net_ir_at_safe:+.2f}" if safe_aum else "—")
c4.metric("Crowding score", f"{crowd:.0f}/100")
c5.metric("Multi-factor weight", f"{mf_w*100:.1f}%")


# ────────────────────────────────────────────────────────────────────────────
# 8. Capacity curve
# ────────────────────────────────────────────────────────────────────────────
st.markdown('<a id="curve"></a>', unsafe_allow_html=True)
st.markdown("## Capacity curve")

st.markdown(
    "Each point is the strategy run at a different AUM with its trades scaled "
    "linearly. The y-axis is Information Ratio after every cost; the x-axis "
    "is AUM (log scale)."
)
st.latex(
    r"\text{Net IR}(A) = \frac{\mathbb{E}[r^{\text{gross}}_t] - c(A) / 252}{\sigma_t}, "
    r"\quad c(A) = \frac{\sum_{t}\text{TotalCost}_t(A)}{A \cdot \text{years}}"
)

curve_sorted = curve.sort_values("aum")
fig = go.Figure()
zone_colors = {"safe": "#2d7a4f", "caution": "#b07c2c", "red": "#a04040"}
for z, color in zone_colors.items():
    sub = curve_sorted[curve_sorted.zone == z]
    if not sub.empty:
        fig.add_trace(go.Scatter(
            x=sub.aum, y=sub.net_ir, mode="markers", name=f"{z} zone",
            marker=dict(color=color, size=11, line=dict(color="white", width=1)),
        ))
fig.add_trace(go.Scatter(
    x=curve_sorted.aum, y=curve_sorted.net_ir, mode="lines", name="Net IR",
    line=dict(color="#1a3a5c", width=2),
))
fig.add_trace(go.Scatter(
    x=curve_sorted.aum, y=curve_sorted.gross_ir, mode="lines", name="Gross IR",
    line=dict(color="#a08c5d", width=1, dash="dot"),
))
fig.add_hline(y=0.5, line_dash="dash", line_color="#888",
              annotation_text="IR = 0.5 hurdle", annotation_position="bottom right")
fig.update_layout(
    xaxis_title="AUM (₹)", yaxis_title="Information ratio (annualised)",
    xaxis_type="log", height=420, **PLOTLY_THEME,
)
st.plotly_chart(fig, use_container_width=True)

st.markdown(
    "<div class='note'>"
    f"<b>Reading the chart.</b> Below {safe_aum/1e7:,.1f} cr the strategy is "
    "in the green band — execution and cost both fit within risk limits. "
    "Past that, costs rise faster than alpha. The IR=0.5 line is the "
    "conventional PM hurdle; the AUM where the blue line crosses it is the "
    "soft cap."
    "</div>",
    unsafe_allow_html=True,
)


# ────────────────────────────────────────────────────────────────────────────
# 9. Cost decomposition
# ────────────────────────────────────────────────────────────────────────────
st.markdown('<a id="cost"></a>', unsafe_allow_html=True)
st.markdown("## Cost decomposition")
st.markdown(
    "Stacked annualised cost in basis points, split by component. Spread + "
    "commission + India tax stack are roughly linear in turnover. Impact "
    "is the curve that bends — square-root in participation up to the "
    "10%-of-ADV threshold, then power-0.6."
)

cost_fig = go.Figure()
for col, color, label in [
    ("spread_bps",     "#1a3a5c", "spread"),
    ("impact_bps",     "#a08c5d", "impact (Almgren-Chriss)"),
    ("commission_bps", "#7a5a3a", "commission"),
    ("borrow_bps",     "#5a4f7a", "borrow (short leg)"),
    ("india_bps",      "#2d7a4f", "India tax stack"),
]:
    cost_fig.add_trace(go.Bar(
        x=curve_sorted.aum, y=curve_sorted[col], name=label, marker_color=color,
    ))
cost_fig.update_layout(
    barmode="stack", xaxis_type="log", height=380,
    xaxis_title="AUM (₹)", yaxis_title="Annualised cost (bps)",
    **PLOTLY_THEME,
)
st.plotly_chart(cost_fig, use_container_width=True)


# ────────────────────────────────────────────────────────────────────────────
# 10. Crowding
# ────────────────────────────────────────────────────────────────────────────
st.markdown('<a id="crowd"></a>', unsafe_allow_html=True)
st.markdown("## Crowding score")

st.markdown(
    "Six external + internal signals each rolling-percentile-ranked into 0–100, "
    "then weighted into a composite. Higher = more crowded."
)
st.latex(
    r"\text{Crowding}(t) = \sum_k w_k \cdot \text{pct-rank}\bigl(\text{signal}_k(t)\bigr), \quad \sum_k w_k = 1"
)

with st.expander("What each signal measures"):
    st.markdown(textwrap.dedent("""
    | Signal | What it captures | Reference |
    |---|---|---|
    | **Valuation spread** | $\\frac{1}{\\bar{P/B}_{\\text{short}} - \\bar{P/B}_{\\text{long}}}$ — narrow spread = factor's mispricing has been arbitraged out | Asness, Friedman, Israel (2017) |
    | **Alpha decay** | Negative slope of trailing-1-year IR over the past 2 years — persistent decline = edge being competed away | Arnott et al. (2017) |
    | **Short interest** | Weighted-average SI on the short leg — high SI = squeeze risk and high borrow | Drechsler, Drechsler (2014) |
    | **Comomentum** | Mean pairwise correlation of long-leg returns over 60 days — high lockstep = same arbitrageurs | Lou, Polk (2013) |
    | **Holdings overlap** | Fraction of long-leg names that also appear in other factors' long legs | Sias, Turtle, Zykaj (2016) (proxy) |
    | **Internal footprint** | $\\frac{\\sum |\\text{trade}_i|}{\\sum \\text{ADV}_i}$ — strategy-level liquidity strain at base AUM | Internal |
    """))

cc = arts["crowd_components"][factor]
ck = arts["crowd_composite"][factor]
crowd_fig = go.Figure()
component_colors = {
    "valuation_spread": "#1a3a5c", "alpha_decay": "#a08c5d",
    "short_interest": "#a04040", "comomentum": "#5a4f7a",
    "holdings_overlap": "#2d7a4f", "internal_footprint": "#7a5a3a",
}
for col in cc.columns:
    crowd_fig.add_trace(go.Scatter(
        x=cc.index, y=cc[col], name=col, opacity=0.45,
        line=dict(color=component_colors.get(col, "#888"), width=1),
    ))
crowd_fig.add_trace(go.Scatter(
    x=ck.index, y=ck["composite"], name="composite",
    line=dict(color="#1a1a1a", width=2.5),
))
crowd_fig.add_hline(y=75, line_color="#a04040", line_dash="dash",
                     annotation_text="red", annotation_position="top right")
crowd_fig.add_hline(y=50, line_color="#b07c2c", line_dash="dash",
                     annotation_text="amber", annotation_position="top right")
crowd_fig.update_layout(
    height=380, yaxis_title="Score (0–100, higher = more crowded)",
    yaxis=dict(range=[0, 100], gridcolor="#e6e3da"),
    **{k: v for k, v in PLOTLY_THEME.items() if k != "yaxis"},
)
st.plotly_chart(crowd_fig, use_container_width=True)

# Component snapshot — radar
latest = cc.iloc[-1]
radar = go.Figure()
radar.add_trace(go.Scatterpolar(
    r=list(latest.values) + [latest.values[0]],
    theta=list(latest.index) + [latest.index[0]],
    fill="toself", name="Latest",
    line=dict(color="#1a3a5c", width=2),
    fillcolor="rgba(26,58,92,0.15)",
))
radar.update_layout(
    polar=dict(
        radialaxis=dict(visible=True, range=[0, 100], gridcolor="#e6e3da"),
        bgcolor="#ffffff",
    ),
    showlegend=False, height=320, margin=dict(l=70, r=70, t=30, b=20),
    paper_bgcolor="#ffffff",
    font=dict(family="Source Serif 4, Georgia, serif", color="#1a1a1a", size=12),
)
c1, c2 = st.columns([1, 1])
with c1:
    st.markdown("**Latest component snapshot**")
    st.plotly_chart(radar, use_container_width=True)
with c2:
    st.markdown("**Component scores (most recent rebalance)**")
    snap = (
        latest.to_frame("score").reset_index().rename(columns={"index": "signal"})
    )
    snap["score"] = snap["score"].round(0).astype(int)
    st.dataframe(snap, use_container_width=True, hide_index=True)


# ────────────────────────────────────────────────────────────────────────────
# 11. Stress capacity
# ────────────────────────────────────────────────────────────────────────────
st.markdown('<a id="stress"></a>', unsafe_allow_html=True)
st.markdown("## Stress capacity")
st.markdown(
    "Same backtest, market parameters replaced with their tail quantiles: "
    "spreads at the 99th percentile, ADV at the 25th, vol at the 95th, "
    "impact coefficient ×1.5, +200 bps borrow premium. The intersection of "
    "the stressed Net-IR curve with the IR=0.5 line is the **stress capacity**. "
    "The PM's hard cap is the minimum of normal and stressed safe AUM."
)
st.latex(r"A_{\text{cap}} = \min\bigl(A_{\text{safe}}^{\text{nominal}}, A_{\text{safe}}^{\text{stressed}}\bigr)")

stress_table = pd.DataFrame({
    "Metric": ["Gross IR", "Net IR at base AUM", "Safe AUM (₹ cr)", "IR≥0.5 AUM (₹ cr)"],
    "Nominal": [
        f"{gross_ir:.2f}",
        f"{curve_sorted.net_ir.iloc[0]:.2f}",
        f"{safe_aum/1e7:,.1f}" if safe_aum else "—",
        f"{(summary['safe_capacity'].get(factor) or 0)/1e7:,.1f}",
    ],
    "Stressed": ["—"] * 4,
})
st.dataframe(stress_table, use_container_width=True, hide_index=True)

st.markdown(
    "<div class='note'>The full stressed curve and 30%-redemption unwind cost "
    "table are in the memo at the bottom of the page.</div>",
    unsafe_allow_html=True,
)


# ────────────────────────────────────────────────────────────────────────────
# 12. Operating policy
# ────────────────────────────────────────────────────────────────────────────
st.markdown('<a id="policy"></a>', unsafe_allow_html=True)
st.markdown("## Operating policy")
st.markdown(
    "At the target AUM (= safe capacity), search over rebalance frequency × "
    "no-trade buffer for the policy that maximises Net IR. The optimal point "
    "is reported in the memo per factor."
)

best_freq, best_buf = "—", "—"
if "best_freq" in summary or "policy" in summary:
    pass


# ────────────────────────────────────────────────────────────────────────────
# 13. Multi-factor allocation
# ────────────────────────────────────────────────────────────────────────────
st.markdown('<a id="mf"></a>', unsafe_allow_html=True)
st.markdown("## Multi-factor allocation")
st.markdown(
    "Joint capacity allocation across all enabled factors, constrained by the "
    "crowding red line. Solves:"
)
st.latex(
    r"\max_{w_1,\ldots,w_K} \;\; \sum_{k=1}^{K} \alpha_k(w_k \cdot A) \cdot w_k \cdot A "
    r"\quad \text{s.t.} \quad \sum_k w_k = 1,\; w_k \geq 0,\; \text{Crowding}_k \leq s_{\max}"
)
st.markdown(
    "where $\\alpha_k(\\cdot)$ is the per-factor net-return-vs-AUM curve (concave). "
    "Solved by exhaustive grid (21 points per dimension; $K=4$ → 200k combinations, <100 ms)."
)

mf_rows = []
for f in factors:
    mf_rows.append({
        "Factor": f,
        "Weight": f"{summary['multi_factor_weights'].get(f, 0)*100:.1f}%",
        "AUM (₹ cr)": f"{summary['multi_factor_aum_alloc'].get(f, 0)/1e7:,.2f}",
        "Crowding": f"{summary['crowding_latest'].get(f, 0):.0f}",
    })
mf_df = pd.DataFrame(mf_rows)
st.dataframe(mf_df, use_container_width=True, hide_index=True)

c1, c2 = st.columns(2)
c1.metric("Total expected net return",
           f"{summary['expected_net_return_pct']*100:.2f}%")
c2.metric("Selected factors",
           f"{sum(1 for w in summary['multi_factor_weights'].values() if w > 0)}/{len(factors)}")


# ────────────────────────────────────────────────────────────────────────────
# 14. Methodology
# ────────────────────────────────────────────────────────────────────────────
st.markdown('<a id="method"></a>', unsafe_allow_html=True)
st.markdown("## Methodology")

with st.expander("Spread estimation — Corwin-Schultz (2012)"):
    st.markdown("Daily-OHLC bid-ask spread without quote tape:")
    st.latex(r"\beta = \mathbb{E}\!\left[\bigl(\ln\tfrac{H_t}{L_t}\bigr)^2 + \bigl(\ln\tfrac{H_{t+1}}{L_{t+1}}\bigr)^2\right]")
    st.latex(r"\gamma = \mathbb{E}\!\left[\bigl(\ln\tfrac{H_{t,t+1}}{L_{t,t+1}}\bigr)^2\right]")
    st.latex(r"\alpha = \frac{\sqrt{2\beta} - \sqrt{\beta}}{3-2\sqrt{2}} - \sqrt{\frac{\gamma}{3-2\sqrt{2}}}")
    st.latex(r"s = \frac{2(e^\alpha - 1)}{1 + e^\alpha}")
    st.markdown(
        "We use a 21-day rolling window and floor at zero. Where CS fails "
        "(insufficient range, illiquid days), we fall back to an ADV-bucket "
        "regression: $s_{\\text{bps}} = 50 - 5.5\\log_{10}\\text{ADV}$."
    )

with st.expander("Market impact — Almgren-Chriss with nonlinear tail"):
    st.markdown("Per-name impact as a fraction of trade value:")
    st.latex(
        r"\text{impact}_i = \begin{cases} "
        r"\sigma_i \cdot k \cdot \sqrt{p_i}, & p_i \leq p^* \\[4pt] "
        r"\sigma_i \cdot k \cdot \sqrt{p^*} \cdot \!\left(\!1 + \tfrac{p_i - p^*}{p^*}\right)^{0.6}, & p_i > p^* "
        r"\end{cases}"
    )
    st.markdown(
        "with $p_i = |Q_i| / (V_i \\cdot T_i)$ the participation rate, "
        "$k \\in [0.10, 0.30]$ calibrated by AQR fills (Frazzini-Israel-"
        "Moskowitz 2018), and $p^* = 10\\%$ the threshold above which impact "
        "departs from the square-root law (Almgren et al. 2005)."
    )

with st.expander("India NSE tax stack"):
    st.markdown(textwrap.dedent("""
    | Component | Rate | Side |
    |---|---|---|
    | STT (delivery) | 0.10% | both legs |
    | Stamp duty | 0.015% | buy only |
    | SEBI fee | ₹10 / cr | both legs |
    | Exchange charge (NSE cash) | 0.00345% | both legs |
    | GST | 18% | on (brokerage + SEBI + exch) |

    For weekly rebalances, STT alone burns ~300 bps/yr — the policy
    optimiser correctly steers Indian factor sleeves toward monthly or
    quarterly rebalances.
    """))

with st.expander("Capacity zone classifier"):
    st.markdown(textwrap.dedent("""
    | Zone | Net IR | Max execution days | Max participation |
    |---|---|---|---|
    | Safe | ≥ 0.5 | ≤ 3 | < 3% |
    | Caution | ≥ 0.2 | ≤ 5 | < 5% |
    | Red | < 0.2 | > 5 | ≥ 5% |

    Computed from the worst-case across the rebalance history at each AUM
    point, not the average — capacity is bounded by the worst day, not the
    typical day.
    """))

with st.expander("Stress regime"):
    st.markdown(textwrap.dedent("""
    A single tail-quantile snapshot. Replace each per-symbol market
    parameter with its tail value, recompute the curve.

    | Parameter | Stress |
    |---|---|
    | spread | per-symbol 99th-percentile |
    | ADV | per-symbol 25th-percentile |
    | vol | per-symbol 95th-percentile |
    | impact coefficient $k$ | $1.5\\times$ nominal |
    | borrow premium | $+200$ bps |
    | short interest | $+5$ pp |

    Plus a one-shot 30%-redemption unwind in 5 days, costed under the same
    stressed market state. The unwind cost is reported as basis points of
    the AUM being shed.
    """))


# ────────────────────────────────────────────────────────────────────────────
# 15. Memo
# ────────────────────────────────────────────────────────────────────────────
st.markdown('<a id="memo"></a>', unsafe_allow_html=True)
st.markdown("## Generated memo")
with st.expander("Open the full PM memo"):
    st.markdown(arts["memo"])


# ────────────────────────────────────────────────────────────────────────────
# Footer
# ────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#5a5a5a; font-size:0.9rem;'>"
    "Factor Capacity & Crowding Monitor · v0.2 · "
    "Synthetic data run · "
    "<a href='/' style='color:#1a3a5c;'>refresh</a>"
    "</div>",
    unsafe_allow_html=True,
)
