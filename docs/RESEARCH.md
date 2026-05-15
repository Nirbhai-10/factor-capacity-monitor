# Factor Capacity & Crowding Monitor — Research Notes

> Internal research document. Captures the academic and industry literature, the
> design space, and the gaps in the prior in-house prototype that this project
> closes. Intended as both a working notebook for the author and as onboarding
> for a reviewer.

## 1. The problem

A factor strategy (e.g. 12-1 momentum, value, low-volatility, quality) generates
positive expected returns at small AUM but its **net** performance degrades as
AUM grows because:

1. **Trading costs scale super-linearly with size.** Spread is roughly constant
   per unit traded, but market impact grows like `sqrt(participation)`
   (Almgren-Chriss) or worse. At some AUM the marginal alpha is fully consumed
   by impact.
2. **The strategy gets crowded.** Other managers run the same signal. As more
   AUM piles in, the long basket gets bid up and the short basket gets squeezed.
   Expected alpha falls. Drawdowns become correlated across funds.
3. **Liquidity is regime-dependent.** ADV and bid-ask spreads collapse in
   stressed regimes exactly when crowded factors unwind. The capacity number
   computed in calm regimes overstates safe AUM.

This monitor answers, on a *live* basis, three questions a PM actually asks:

- **How much can this factor hold today, net of cost, before Net IR collapses?**
- **How crowded is the factor versus its own history, and versus other factors?**
- **What rebalancing frequency / no-trade buffer / hard cap minimises the
  damage as AUM scales?**

## 2. Literature review

### 2.1 Capacity & impact

| Reference | Contribution | What we use |
|---|---|---|
| Almgren, Chriss (2000) "Optimal execution of portfolio transactions" | Square-root impact model: `MI ≈ σ · η · √(Q/V)` | Baseline impact term |
| Almgren et al. (2005) "Direct estimation of equity market impact" | Calibrated impact: temporary `σ · 0.314 · sign(Q) · |Q/V|^0.6` and permanent `0.314σ · Q/V`. | Nonlinear tail |
| Frazzini, Israel, Moskowitz (2018) "Trading costs" | Real AQR fills: impact ≈ 0.20–0.35 × σ × √(participation), close to AC | Calibration prior, used to set `k ∈ [0.10, 0.30]` |
| Korajczyk, Sadka (2004) "Are momentum profits robust to trading costs?" | Capacity of momentum at $5B (US, 2003 data). | Methodology template |
| Novy-Marx, Velikov (2016) "A taxonomy of anomalies and their trading costs" | Cross-section of factor net Sharpe after costs | Multi-factor framing |
| Ratcliffe, Miranda, Ang (BlackRock 2017) "Capacity of smart beta" | Empirical capacity numbers for size, value, momentum, quality | Capacity zone thresholds |
| Pedersen (2015) "Efficiently Inefficient" ch.5 | Defines effective spread, holding-period scaling | Holding-period adjustment for round-trip cost |

Key take-aways for the model:

- Impact is **square-root in participation** for normal trades and turns
  steeper above ~10–15% of ADV. Use AC as base, switch to a 0.6 exponent
  above the cap.
- Round-trip cost amortises over the **holding period**. A 12-1 momentum
  portfolio rebalanced monthly with `T = 21d` holding amortises 2× spread + 2×
  impact across 21 days.
- Capacity is **not** the AUM where alpha goes to zero. It is the AUM where
  Net IR drops below the PM's hurdle (often 0.5).

### 2.2 Crowding measures

| Reference | Contribution | What we use |
|---|---|---|
| Cahan, Luo (2013, Deutsche Bank) "Crowding and quant equity" | Composite of valuation spread, short interest, correlation, factor decay | Composite design |
| Asness (2000) "Bubble logic" / Asness-Friedman-Israel (2017) "Is (systematic) value investing dead?" | Valuation spread of factor's top-vs-bottom quintile as crowding proxy | Valuation-spread signal |
| Lou, Polk (2013) "Comomentum" | Pairwise correlation of momentum stocks within long leg: spike = crowd | Correlation signal |
| Sias, Turtle, Zykaj (2016) "Hedge-fund holdings and equity returns" | 13F overlap reveals real crowding by alpha-seekers | 13F overlap (proxied) |
| Lou-Polk-Skouras (2019) "A tug of war: Overnight versus intraday returns" | Overnight return persistence as a sign that crowded names are pre-positioned | Overnight/intraday split |
| Drechsler, Drechsler (2014) "The shorting premium" | Short interest fee as price of crowding on the short leg | Short interest signal |
| Stein (2009) "Sophisticated investors and market efficiency" | Theoretical crowding mechanism: arbitrageurs herd | Conceptual framing |
| Arnott, Hsu, West (Research Affiliates 2017) "How can smart beta go horribly wrong?" | Most factor outperformance post-publication came from factor getting *more* expensive — capacity meets crowding | Why we monitor live |

### 2.3 Crowding / capacity interaction

The two interact: **a crowded factor has lower capacity than its naive cost
model would suggest**, because if you and the herd unwind together, your
realised impact is the herd's impact, not yours alone. The model addresses this
with:

- **Effective participation** = `your_participation × herd_factor` where
  `herd_factor` rises with the crowding score.
- **Stress capacity** computed under a 1-in-20 redemption shock with widened
  spreads and higher impact coefficient.

## 3. Existing in-house prototype (`~/ProjectFactor`)

The earlier prototype (~7,900 lines, January 2026) covers the basics:

**What it does well**
- Almgren-Chriss impact with vol-scaling, Corwin-Schultz spread.
- 12-1 momentum, dollar-neutral, weekly rebalance.
- Capacity curve across an AUM grid with safe / caution / red zones.
- Internal pressure score: liquidity footprint + max participation + HHI.
- Streamlit dashboard, markdown memo.

**Gaps / why we are rewriting**
1. **Crowding is purely internal** — measures only how much *we* strain
   liquidity. Says nothing about whether the rest of the market is
   pre-positioned the same way (the Asness/Lou-Polk/Sias signals are absent).
2. **Single factor.** Real allocators run a sleeve of factors and need
   capacity *jointly*. The current tool would over-allocate to any factor in
   isolation because it ignores shared names across factors.
3. **No regime conditioning.** Capacity is reported at one set of
   spread/vol/ADV values. The same portfolio's capacity is materially lower in
   2008/2020-style regimes — we should report a stressed number alongside.
4. **No India-specific cost stack.** STT (0.1% delivery, 0.025% intraday sell),
   stamp duty (0.015%), SEBI charges (₹10/cr), GST on brokerage and exchange
   fees, plus the ban on intraday short for delivery shorts (we use SLB).
5. **No alpha decay tracker.** A factor whose rolling-1y Sharpe has been
   monotonically dropping for 3y is the *definition* of being crowded out, but
   the prototype doesn't watch this.
6. **Policy search is brute-force grid.** `policy/search.py` enumerates
   (rebalance_freq × buffer × constraint) combinations; we replace with a
   convex formulation where possible.
7. **Capacity is wall-clock at a point in time.** No live monitor / alert
   layer. A PM wants "ping me when free capacity drops below ₹X cr".

This new project keeps the AC/Corwin-Schultz primitives and replaces everything
above the cost-model layer.

## 4. Existing commercial / academic products

For context, when an analyst pitches this work it helps to be conversant with
the commercial alternatives:

- **MSCI Barra Liquidity / Trading Cost Model.** Per-name impact estimates
  blended with regression-driven spread. Closed-source factor library
  (BIM, USE4). Not capacity-aware out of the box.
- **Axioma Trade Cost Model** (now SimCorp). Similar, more granular by
  trade-size bucket.
- **ITG/Virtu ACE.** Pre-trade cost estimator widely used by buy-side
  execution desks. Realised-fill calibrated. Not factor-aware.
- **Northfield, AQR-internal tools.** Use Frazzini-style calibrated impact.
- **Novus / Backstop hedge fund holdings overlap.** The crowding side. Maps
  13F holdings to detect which names are owned by which set of funds.
- **Bloomberg PORT, Bloomberg LQA.** Liquidity scores per security, but again
  not joint with a factor strategy.

Our tool sits at the intersection — factor-aware capacity *and* live crowding
in one place — which is the spot where the existing internal prototype was
also aimed but with the gaps above.

## 5. Methodology

### 5.1 Cost model (per rebalance)

For each name `i` at rebalance date `t`:

```
spread_cost_i  = 0.5 · spread_i_t · |trade_dollars_i|              (one-side)
impact_cost_i  = σ_i · k · sqrt(|trade_dollars_i| / (ADV_i · T))   (Almgren–Chriss)
                 ↑ if participation > p_cap, use exponent 0.6      (nonlinear tail)
commission_i   = c_bps · |trade_dollars_i|
borrow_cost_i  = (max(0, -position_i)) · borrow_bps_i · holding_days/252
india_taxes_i  = STT + stamp + SEBI_fee + GST_on_brokerage         (NSE only)
```

Round-trip cost amortises over the next holding period. Net daily return is
gross daily return minus annualised cost / 252.

### 5.2 Capacity curve

Simulate a grid of AUM levels `[10cr, 25cr, 50cr, ..., 5000cr]`. At each AUM,
scale historical trade dollars proportionally and recompute net IR. The curve
`Net IR(AUM)` is monotonically non-increasing.

Capacity zones (configurable):

| Zone | Net IR | Max execution days | Max participation |
|------|--------|-------------------|------------------|
| Safe    | ≥ 0.5 | ≤ 3 | < 3% |
| Caution | ≥ 0.2 | ≤ 5 | < 5% |
| Red     | < 0.2 | > 5 | > 5% |

### 5.3 Multi-factor capacity allocation

If you run K factors (momentum, value, quality, low-vol) jointly, capacity is
**not** the sum of single-factor capacities. Shared positions imply that
trading factor 1 moves prices on names also held by factor 2.

We solve:

```
maximise   Σ_k  w_k · α_k(C · w_k)        # alpha at allocated capital, factor k
subject to  Σ_k w_k = 1
            w_k ≥ 0
            participation_i ≤ p_cap   ∀ i      # joint, sums shared names
            crowding_score_k ≤ s_max  ∀ k
```

where `α_k(·)` is the empirical capacity curve for factor `k`. Since `α_k` is
monotonically decreasing and concave (typical), the problem is concave — solved
with `cvxpy` and a piecewise-linear approximation of α.

### 5.4 Crowding score (composite)

Per factor, per date, score on 0–100 (higher = more crowded):

```
crowding_score = w1 · pct_rank(valuation_spread_top_vs_bottom)
               + w2 · pct_rank(rolling_3y_alpha_decay)
               + w3 · pct_rank(short_interest_long_leg)
               + w4 · pct_rank(comomentum)        # Lou-Polk pairwise corr
               + w5 · pct_rank(13f_overlap_with_peers)
               + w6 · pct_rank(internal_liquidity_footprint)
```

Defaults: equal weights, normalised by a ~10y rolling window. Each component
is the percentile against its own history, so the score is regime-agnostic.

### 5.5 Stress capacity

Fix the portfolio. Replace:
- spread → 99th percentile spread
- ADV → 25th percentile ADV
- vol → 95th percentile vol
- impact coefficient → 1.5× nominal
- borrow → +200bps for top short-interest names

Recompute Net IR(AUM). The intersection of stressed Net IR with the IR≥0.5
line is the **stress capacity**. The PM's hard AUM cap should be the *minimum*
of normal and stressed capacity.

### 5.6 Policy recommendations

Three knobs:

1. **Rebalance frequency.** More frequent → fresher signal but more cost.
   Search on `{D, W, BW, M, Q}`. Optimal is the frequency that maximises Net
   IR at target AUM.
2. **No-trade buffer.** Only trade if `|target_w − current_w| > buffer`. Cuts
   turnover ~30–60% with minimal IR drop. We sweep `[0, 25, 50, 100, 200] bps`.
3. **Capacity checkpoints.** As AUM utilisation climbs through 50% / 75% / 90%
   of safe capacity, downshift turnover, raise buffer, or close the strategy
   to new flows.

## 6. Data sources

| Item | Source | Notes |
|------|--------|-------|
| OHLCV (NIFTY 100 / S&P 500) | `yfinance` | Free, ~10y history. Throttle-prone. |
| OHLCV (NSE intraday) | NSE Bhavcopy / Kite Connect | Better fills than yfinance |
| Fundamentals | `yfinance` `.info`, screener.in (NSE) | For value/quality factors |
| ADV | Computed from OHLCV (`close × volume`) 20-day median | Robust to spike days |
| Spread | Corwin-Schultz from OHLC (no L1 needed) | + ADV-bucket fallback |
| Short interest | NSE F&O OI / SEC short interest reports | Monthly granularity in India |
| 13F holdings | SEC Edgar (US) / shareholding patterns (India quarterly) | Quarterly only |
| ETF flows | issuer disclosure, Bloomberg, MFI India | Daily for big ETFs |
| Borrow rate | Broker SLB rates / TickRabbi / IBKR | Tiered by ADV |
| India costs | STT, stamp, SEBI schedule | Hard-coded, updated annually |

For a self-contained demo, the project ships a **synthetic data generator**
that mimics NIFTY-100 statistical properties (vol clustering, ADV power-law,
spread inversely related to ADV) so the full pipeline runs offline.

## 7. Open questions / future work

- **Real fills.** Without execution-tape data, impact is estimated. A v2 should
  ingest actual fills to recalibrate `k` per-name.
- **Factor timing.** A natural extension: tilt away from crowded factors. We
  *measure* but don't *time* in v1.
- **Cross-asset.** Currently equity-only. Capacity for fixed-income carry,
  currency carry, macro futures has different cost stacks.
- **Intraday capacity.** All work is end-of-day. For an HFT-adjacent factor,
  intraday participation matters more than daily.

## 8. References (chronological)

1. Almgren R., Chriss N. (2000). "Optimal execution of portfolio transactions". *J. Risk* 3(2).
2. Korajczyk R., Sadka R. (2004). "Are momentum profits robust to trading costs?". *J. Finance* 59(3).
3. Almgren R. et al. (2005). "Direct estimation of equity market impact". *Risk*.
4. Stein J. (2009). "Sophisticated investors and market efficiency". *J. Finance* 64(4).
5. Lou D., Polk C. (2013). "Comomentum: Inferring arbitrage activity from return correlations". Working paper, LSE.
6. Cahan R., Luo Y. (2013). "Crowding and quant equity". Deutsche Bank Quant Research.
7. Drechsler I., Drechsler Q. (2014). "The shorting premium and asset pricing anomalies".
8. Sias R., Turtle H., Zykaj B. (2016). "Hedge-fund crowds and mispricing". *Mgmt Sci.*
9. Novy-Marx R., Velikov M. (2016). "A taxonomy of anomalies and their trading costs". *RFS* 29(1).
10. Ratcliffe R., Miranda P., Ang A. (2017). "Capacity of smart beta strategies". *J. Portfolio Management*.
11. Arnott R., Hsu J., West J. (2017). "How can 'smart beta' go horribly wrong?". Research Affiliates.
12. Asness C., Friedman J., Israel R. (2017). "Style timing: Value versus growth". *J. Portfolio Management*.
13. Frazzini A., Israel R., Moskowitz T. (2018). "Trading costs". AQR working paper.
14. Lou D., Polk C., Skouras S. (2019). "A tug of war: Overnight versus intraday expected returns". *J. Financial Econ.*
