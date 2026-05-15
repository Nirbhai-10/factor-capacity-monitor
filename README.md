# Factor Capacity & Crowding Monitor

A buy-side research tool that estimates **how much money a factor strategy can
safely manage** before its net Information Ratio collapses, monitors how
**crowded** that factor has become, and recommends operating policies
(rebalance frequency, no-trade buffers, hard AUM caps) that maximise the
strategy's net-of-cost edge as it scales.

This is the second-generation rewrite of an earlier in-house prototype
(`~/ProjectFactor`). The redesign closes four big gaps in the prior tool:

1. **External crowding signals** — valuation spread (Asness), comomentum
   (Lou-Polk), short-interest pressure, holdings overlap, factor-alpha decay.
   The prototype only saw *internal* liquidity footprint.
2. **Multi-factor capacity allocation** — joint capacity across a sleeve of
   factors, recognising shared positions, solved as a concave program.
3. **Regime / stress capacity** — capacity reported in calm and stressed
   regimes (1-in-20 redemption shock, widened spreads, tail vol).
4. **India / NSE cost stack** — STT, stamp, SEBI, GST on brokerage modelled
   alongside spread + AC impact.

## What you get

| Output | Where |
|---|---|
| Capacity curve (Net IR vs AUM) per factor | `examples/demo_output/capacity_curve.html` |
| Composite crowding score (0–100), 6-component breakdown | `examples/demo_output/crowding_score.html` |
| Stress capacity table | memo |
| Recommended rebalance frequency, no-trade buffer, hard AUM cap | memo |
| PM-style markdown memo | `examples/demo_output/memo.md` |
| Streamlit dashboard | `streamlit run dashboard/app.py` |

## Quick start

```bash
cd FactorCapacityMonitor
python -m venv .venv && source .venv/bin/activate
pip install -e .
python scripts/run_demo.py            # synthetic NIFTY-100-like data, ~10s
streamlit run dashboard/app.py        # optional, interactive
```

`run_demo.py` ships a synthetic generator so the full pipeline runs offline.
For real data, edit `config/default.yaml` to point at NSE Bhavcopy or Yahoo.

## Documentation

- [docs/RESEARCH.md](docs/RESEARCH.md) — literature, methodology, references
- [docs/DESIGN.md](docs/DESIGN.md) — module map and conventions
- [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) — where each input comes from

## Status

Single-author research project. Not production. No real money should hit the
broker on signals from this code without an institutional execution review.
