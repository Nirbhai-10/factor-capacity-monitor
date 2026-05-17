# Audit findings & improvements

Self-review of the v0.1 codebase. Each item is graded **fixed-now / queued / accepted-tradeoff**.

## Bugs

| # | Location | Issue | Status |
|---|----------|-------|--------|
| 1 | `crowding/composite.py` | Builds the weights dict from `cfg.crowding.weights._data.keys()` — relies on a private dataclass field. | **fixed** — `Config` now exposes `keys()` / `items()` / `__iter__`. |
| 2 | `stress/scenarios.py` | Reconstructs `MarketPanel` with `dollar_volume * (cfg.stress.adv_pct_quantile / 0.50)` — magic 0.50 baseline. | **fixed** — pass an `adv_override` straight into `run_capacity_curve`. |
| 3 | `crowding/valuation_spread.py` | Rolling-percentile `apply` is O(n²); fine at 1 260 dates, slow at 25 000. | **accepted** — vectorise if we ever go intraday. |
| 4 | `portfolio/backtest.py` | `target_weights_ts = pd.DataFrame(snapshot_rows).T` relies on dict-insertion order. | **fixed** — explicit `sort_index()`. |
| 5 | `data/synthetic.py` | `LowVol` factor stays at IR≈0 in synthetic: dispersion in idio-vol is small relative to common-factor variance. | **accepted** — synthetic-only, real data fixes it. Documented. |
| 6 | `factors/momentum.py` | If a name has any prior NaN, score is masked even when current price is fine. | **accepted** — that's the intended conservatism. |

## Design / UX gaps

| # | Issue | Resolution |
|---|-------|-----------|
| A | The Streamlit dashboard was bare — no methodology, no math, no explanation of what's running underneath. | **fixed** — full rewrite with sectioned narrative, LaTeX formulas, and a "How it works" pipeline graphic. |
| B | No traditional, restrained styling — the default Streamlit palette is loud. | **fixed** — Garamond/Source Serif headers, Crimson Pro body, warm cream `#fbfaf6` background, navy `#1a3a5c` accent only for emphasis. |
| C | KPIs were plain `st.metric` calls without context. | **fixed** — KPI strip + subtle annotations + zone colour coding. |
| D | No per-component crowding breakdown — only the composite chart. | **fixed** — radar of components alongside the timeseries. |
| E | "Why does it matter" message was missing for non-quant readers. | **fixed** — opening section explaining the problem and stakes plainly. |

## Things deliberately not changed

- Cost-model still uses Almgren-Chriss `√participation` with a 0.6-exponent tail; we don't try to recalibrate `k` from real fills.
- Multi-factor allocator stays as exhaustive grid search (K=4 → 200k points → <100 ms). Coordinate descent would only help past K=6.
- Stress regime is still a single-quantile snapshot, not a Monte-Carlo over regime states. Listed in `RESEARCH.md §7`.

## What to add next (queued)

1. **Real-fill calibration**: ingest broker fill prices vs Almgren-Chriss prediction and refit `k` per-name.
2. **Survivorship-aware universe**: snapshots of NIFTY-100 / NIFTY-500 membership over time.
3. **Live monitor + alerts**: cron the daily refresh, push to Slack/email when crowding flips amber→red.
4. **Streamlit caching** for slow steps (`@st.cache_data`) — the demo recomputes everything on every page load right now; OK because we read pre-baked artefacts.
