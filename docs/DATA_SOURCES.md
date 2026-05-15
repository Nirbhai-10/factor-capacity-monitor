# Data sources

Where each input to the pipeline comes from, what its known issues are, and
how the synthetic generator approximates it for offline demos.

## Equity OHLCV

| Source | Cost | Latency | Quality notes |
|---|---|---|---|
| `yfinance` (Yahoo) | Free | ~15-min lag | Throttling; some Indian symbols dirty (splits/bonus) |
| NSE Bhavcopy | Free | EOD | Authoritative for NSE; CSV files per day |
| Kite Connect (Zerodha) | Paid (Rs 2k/mo) | Real-time | Best quality for NSE intraday |
| Bloomberg | Paid (corporate) | Real-time | Gold standard, but licence overhead |

Use `data/yfinance_loader.py` for a free Yahoo path and the NSE Bhavcopy
loader for production.

## Spread

Estimated from OHLC via Corwin-Schultz (`costs/spread.py`) — no L1 quotes
required. Cross-check against:
- NSE quote-by-quote tape (paid, Refinitiv) for backtest calibration
- Realised execution slippage from broker fills (post-trade)

Synthetic generator: spread is constructed inversely with log(ADV) plus
GARCH-like noise.

## ADV

Computed from OHLCV as `close × volume`, 20-day rolling median (robust to
spike days). Real implementation reads from the same source as OHLCV.

## Fundamentals (P/B for value, ROE for quality)

| Source | Cost | Cadence | Notes |
|---|---|---|---|
| `yfinance.Ticker.info` | Free | Quarterly | Inconsistent across tickers |
| screener.in | Free (rate-limited) | Quarterly | Good for India |
| Bloomberg `BS_TOT_ASSET`, `RETURN_ON_EQUITY` | Paid | Real-time | Gold standard |
| Refinitiv (LSEG) | Paid | Real-time | Standard alternative |

Synthetic generator: P/B drawn around 3.0 with cross-sectional dispersion
tied to a latent value beta; ROE drawn around 15% with dispersion tied to a
quality beta. Both drift slowly over time.

## Short interest

| Source | Cost | Cadence | Notes |
|---|---|---|---|
| NSE F&O OI / SLB rates | Free | Daily | India proxy for short interest; SLB is the borrow market |
| FINRA Short Interest | Free | Bi-monthly | US |
| S3 Partners | Paid | Real-time | Comprehensive |
| IBKR Short-availability API | Free w/ acct | Real-time | Borrow rates and quantity |

## Holdings (for crowding overlap)

| Source | Cost | Cadence | Notes |
|---|---|---|---|
| SEC Edgar 13F | Free | Quarterly (45-day lag) | US institutional holdings |
| NSE Shareholding Pattern | Free | Quarterly | India — promoter, FII, DII, public |
| Novus / Backstop | Paid | Quarterly | Cleaned holdings overlap analytics |

In the synthetic / demo path we use the long-leg overlap *across the project's
own factors* as a proxy for inter-fund overlap, which is enough to demonstrate
the metric.

## Borrow rates / SLB

NSE has a Securities Lending and Borrowing (SLB) segment. For each name,
the indicative borrow rate and quantity are published daily. We approximate
this as a tiered curve based on ADV bucket plus a short-interest premium for
squeezable names.

## Costs / taxes (India)

The NSE/SEBI fee schedule changes annually. Current values in
`config/default.yaml` (FY26):
- STT delivery: 0.1% on both legs
- STT intraday sell: 0.025%
- Stamp: 0.015% on buy
- SEBI: ₹10/cr
- Exchange: 0.00345%
- GST: 18% on (brokerage + SEBI + exchange)

Change one-time annually after the Union Budget. SEBI fee was ₹15/cr earlier;
Stamp duty changed from state-by-state to a centralised 0.015% in 2020.
