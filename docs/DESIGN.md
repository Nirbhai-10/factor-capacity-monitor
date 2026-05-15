# Design

## Module map

```
src/fcm/
├── data/         offline + synthetic data generation
├── factors/      momentum, value, quality, low-vol; multi-factor combiner
├── portfolio/    long-short construction + rebalance with no-trade buffer
├── costs/        spread, impact, borrow, India NSE tax stack
├── capacity/     AUM-grid simulator, multi-factor allocator, regime conditioner
├── crowding/     valuation spread, alpha decay, comomentum, short interest, composite score
├── policy/       rebalance frequency / buffer / checkpoint optimiser
├── stress/       redemption + liquidity + factor-crash scenarios
├── monitor/      live snapshot, alert thresholds
└── reporting/    PM memo (markdown), plotly charts
```

## Data flow (end-to-end run)

```
load_universe ──► fetch_prices ──► compute_factor_signals ──► build_portfolios
                                                              │
                                                              ▼
                                                     run_backtest (gross)
                                                              │
       ┌──────────────────────────────────────────────────────┤
       ▼                              ▼                       ▼
  cost_model         crowding_score (per factor)      stress_scenarios
       │                              │                       │
       ▼                              ▼                       ▼
 capacity_curve   ◄─── multi_factor_allocator ─────► stress_capacity
       │                              │                       │
       └──────────► policy_search ◄───┘                       │
                          │                                    │
                          └────────► reporting.memo + charts ◄┘
```

## Conventions

- **Returns**: daily, decimal (0.01 = 1%). Series indexed by `pd.DatetimeIndex`.
- **Weights**: dollar-neutral long-short. Long sums to +1, short sums to −1. Gross = 2.
- **Currency**: USD by default; the India profile flips to INR and the cost stack to NSE.
- **Time conventions**: 252 trading days/year, 21 days/month.
- **AUM grid**: `[10, 25, 50, 100, 250, 500, 1000, 2000, 5000]` × `unit` (cr INR or $M USD).

## Configuration

`config/default.yaml` is the source of truth for tunables. The runtime reads it
into a frozen `Config` dataclass (see `src/fcm/config.py`). Override per-run with
`--config path/to/override.yaml` or programmatically.

## Synthetic-data mode

`src/fcm/data/synthetic.py` produces a NIFTY-100-like panel:

- 100 names, 5y of daily data
- log returns drawn from a 3-factor model: market + size + value, with idiosyncratic vol
- ADV drawn from a Pareto distribution (heavy tail, like real Indian equities)
- spread inversely proportional to log(ADV) with a noise term

This is enough to exercise every module in the pipeline without an internet
connection or paid data.

## Testing

Each module has a `tests/test_<module>.py` covering:
- numerical sanity (impact ≥ 0, spread ≥ 0, capacity curve monotonic)
- conservation laws (long + short = 0 for dollar-neutral, weights sum properly)
- regression tests on the synthetic data fixture

Run `pytest -q` from repo root.

## Extension points

- **Add a factor**: subclass `factors.base.FactorSignal`, register in
  `factors/__init__.py`. The combiner picks it up automatically.
- **Plug in a real data source**: implement `data.base.DataSource` and pass to
  `Pipeline(data_source=...)`.
- **Custom cost component**: implement a callable `(weights, market_state) → bps`
  and add to `costs.total.TotalCost.components`.
