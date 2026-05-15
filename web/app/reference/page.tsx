"use client";

import { useState } from "react";
import { data } from "@/lib/data";
import { fmtCr, fmtIR, fmtPct } from "@/lib/format";
import { Kpi } from "@/components/Kpi";
import { ZonePill } from "@/components/ZonePill";
import { SectionHeader } from "@/components/SectionHeader";
import { CapacityCurve } from "@/components/CapacityCurve";
import { CostStack } from "@/components/CostStack";
import { CrowdingChart } from "@/components/CrowdingChart";
import { CrowdingRadar } from "@/components/CrowdingRadar";
import { AlphaForecast } from "@/components/AlphaForecast";
import { FactorTabs } from "@/components/FactorTabs";
import { Block, Inline } from "@/components/Math";

export default function Page() {
  const factors = data.meta.factors;
  const [factor, setFactor] = useState(factors[0]);
  const f = data.factors[factor];

  return (
    <>
      <section className="section-narrow">
        <div className="kicker mb-3">Reference run</div>
        <h1 className="font-serif">Capacity & crowding on four reference factors</h1>
        <p className="lede mt-4">
          Synthetic NIFTY-100-like panel, five years, 100 names. Same engine
          you'd run on your own data via <a href="/analyze">/analyze</a>, plus
          the cross-sectional crowding signals that need universe-wide data.
        </p>
      </section>

      <hr className="divider mx-auto max-w-3xl" />

      {/* ─────────────  Why  ───────────── */}
      <section id="why" className="max-w-6xl mx-auto px-6 py-16">
        <SectionHeader
          kicker="Why this matters"
          title="Two compounding mechanisms degrade factor returns"
        />
        <div className="grid md:grid-cols-3 gap-8">
          <div className="md:col-span-2 prose-fcm space-y-4">
            <p>
              Every factor strategy &mdash; momentum, value, quality, low-volatility &mdash;
              earns positive expected returns at small AUM and earns less at larger AUM.
              The usual story is &quot;alpha decays as size grows.&quot; That story is incomplete.
              Two distinct mechanisms compound on each other:
            </p>
            <p>
              <strong>Trading-cost drag.</strong> Costs scale super-linearly with size.
              Spread is roughly constant per unit of trade, but market impact grows
              like <Inline tex="\sqrt{Q/V}" /> (Almgren&ndash;Chriss) and faster than that
              for large notionals. At some AUM the marginal alpha is fully consumed by impact.
            </p>
            <p>
              <strong>Crowding.</strong> Other managers run the same signal. As capital
              piles in, the long basket bids up and the short basket gets squeezed.
              Realised alpha decays <em>before</em> trading costs even fire. Drawdowns
              become correlated across funds and unwinds become reflexive.
            </p>
            <p>
              The PM-level question is not &quot;what&apos;s my Sharpe at infinite AUM&quot; &mdash;
              it is: <em>given my current AUM and my factors&apos; current crowding,
              what&apos;s my hard cap and what&apos;s my safe rebalancing rule?</em>
              This monitor answers exactly that.
            </p>
          </div>
          <aside className="card text-sm space-y-4">
            <div>
              <div className="kicker mb-1">Three numbers a PM quotes</div>
            </div>
            <div>
              <div className="font-medium">Safe AUM</div>
              <p className="text-muted text-sm">Largest AUM where Net IR ≥ 0.5,
                execution stays under 3 days, and no name exceeds 3% of ADV.</p>
            </div>
            <div>
              <div className="font-medium">Stress AUM</div>
              <p className="text-muted text-sm">Same definition under widened spreads,
                shrunken ADV, fattened vol. Hard cap = min(safe, stress).</p>
            </div>
            <div>
              <div className="font-medium">Crowding score (0–100)</div>
              <p className="text-muted text-sm">Composite of valuation spread, alpha
                decay, short interest, comomentum, holdings overlap, internal liquidity
                footprint &mdash; each rolling-percentile-ranked.</p>
            </div>
          </aside>
        </div>
      </section>

      {/* ─────────────  How  ───────────── */}
      <section id="how" className="max-w-6xl mx-auto px-6 py-12 border-t border-rule">
        <SectionHeader
          kicker="How it works"
          title="What the dashboard is computing in the background"
        />
        <p className="mb-6 max-w-prose">
          Five stages run in sequence whenever the data is refreshed.
          Each stage&apos;s output drives one section of the dashboard below.
        </p>
        <div className="grid md:grid-cols-5 gap-4">
          {[
            { n: 1, t: "Build factor scores",
              d: "Cross-sectional rank per factor: 12-1 momentum, P/B value, ROE quality, 6-month low-vol." },
            { n: 2, t: "Construct portfolio",
              d: "Top quintile long, bottom quintile short, dollar-neutral, equal-weighted." },
            { n: 3, t: "Backtest gross",
              d: "Daily gross-of-cost return series. Used as the alpha side of every capacity calculation." },
            { n: 4, t: "Cost & capacity scan",
              d: "At each AUM in the grid: spread + Almgren-Chriss impact + commission + borrow + India tax stack → Net IR." },
            { n: 5, t: "Crowding, ML, policy",
              d: "Composite crowding score, OU-model alpha forecast, regime classifier (GMM), optimal rebalance + buffer search." },
          ].map((s) => (
            <div key={s.n} className="card">
              <div className="font-mono text-xs text-gold mb-1">step {s.n}</div>
              <div className="font-serif text-lg mb-2">{s.t}</div>
              <p className="text-sm text-muted">{s.d}</p>
            </div>
          ))}
        </div>

        <details className="mt-6 card">
          <summary className="cursor-pointer font-serif text-lg">Per-rebalance equations</summary>
          <div className="mt-3 space-y-2">
            <Block tex={String.raw`\text{spread cost}_i = \tfrac{1}{2}\, s_i \cdot |Q_i|`} />
            <Block tex={String.raw`\text{impact cost}_i = \sigma_i \cdot k \cdot \sqrt{\frac{|Q_i|}{V_i \cdot T_i}} \cdot |Q_i|`} />
            <Block tex={String.raw`\text{borrow}_i = \max(0,-w_i)\cdot \text{AUM} \cdot r_i^{\text{borrow}} \cdot \frac{H}{252}`} />
            <Block tex={String.raw`\text{tax}_i = (\text{STT} + \text{stamp} + \text{SEBI} + \text{exch} + \text{GST})\cdot |Q_i|`} />
            <p className="text-sm text-muted">
              <Inline tex="s_i" /> is the bid-ask spread (Corwin-Schultz),
              <Inline tex="\,Q_i\," /> trade dollars, <Inline tex="\,\sigma_i\," /> annualised vol,
              <Inline tex="\,V_i\," /> daily ADV, <Inline tex="\,T_i\," /> chosen execution days,
              <Inline tex="\,k \in [0.10,0.30]\," /> the impact coefficient,
              <Inline tex="\,w_i\," /> target weight, <Inline tex="\,H\," /> holding period.
            </p>
          </div>
        </details>
      </section>

      {/* ─────────────  Regime  ───────────── */}
      <section className="max-w-6xl mx-auto px-6 py-12 border-t border-rule">
        <SectionHeader
          kicker="ML layer · Gaussian mixture model"
          title="Current market regime"
          lede="A 3-component GMM clusters daily market state (vol, average pairwise correlation, spread, ADV) into 'calm', 'normal', 'stressed'. The label drives whether nominal or stressed capacity should bind."
        />
        <div className="grid md:grid-cols-3 gap-4">
          <Kpi label="Today's regime"
                value={<span className={`zone-pill zone-${data.regime.current}`}>{data.regime.current}</span>}
                hint="argmax over the three GMM components" />
          {(["calm", "normal", "stressed"] as const).map((r) => (
            <Kpi key={r} label={`${r} probability`}
                  value={fmtPct(data.regime.probabilities[r] ?? 0, 0)} />
          ))}
        </div>
        <details className="card mt-6">
          <summary className="cursor-pointer font-serif text-lg">Regime centroids (interpretable axes)</summary>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-rule">
                  <th className="py-2 px-3">regime</th>
                  <th className="py-2 px-3">market vol (ann.)</th>
                  <th className="py-2 px-3">avg pairwise corr</th>
                  <th className="py-2 px-3">median spread</th>
                  <th className="py-2 px-3">log<sub>10</sub> ADV ($)</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.regime.centroids).map(([name, c]) => (
                  <tr key={name} className="border-b border-rule">
                    <td className="py-2 px-3"><span className={`zone-pill zone-${name}`}>{name}</span></td>
                    <td className="py-2 px-3 font-mono">{c.market_vol?.toFixed(3)}</td>
                    <td className="py-2 px-3 font-mono">{c.avg_corr?.toFixed(3)}</td>
                    <td className="py-2 px-3 font-mono">{(c.spread * 1e4)?.toFixed(0)} bps</td>
                    <td className="py-2 px-3 font-mono">{c.log_adv?.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </section>

      {/* ─────────────  Factor selector + KPIs  ───────────── */}
      <section id="factors" className="max-w-6xl mx-auto px-6 py-12 border-t border-rule">
        <SectionHeader
          kicker="Per-factor"
          title="Factor deep dive"
          lede="Select a factor to inspect its capacity curve, cost decomposition, crowding score, and ML forecast."
        />

        <FactorTabs factors={factors} current={factor} onChange={setFactor} />

        <div className="grid md:grid-cols-5 gap-4 mb-8">
          <Kpi label="Gross IR" value={fmtIR(f.gross_ir)} hint="annualised, before costs" />
          <Kpi label="Safe capacity" value={fmtCr(f.safe_capacity)} hint="Net IR ≥ 0.5 + zone constraints" />
          <Kpi label="Stress capacity" value={fmtCr(f.stress_safe_capacity)} hint="under tail-quantile market" />
          <Kpi label="Crowding"
                value={<><span>{f.crowding_latest.toFixed(0)}</span>
                          <span className={`zone-pill zone-${f.alert_level} ml-2 text-base align-middle`}>
                            {f.alert_level}
                          </span></>}
                hint="composite, 0-100, rolling-percentile" />
          <Kpi label="Best policy"
                value={`${f.best_policy.freq} / ${Math.round(f.best_policy.buffer_bps)}bps`}
                hint={`net IR ${f.best_policy.net_ir.toFixed(2)} at ${fmtCr(f.best_policy.target_aum)}`} />
        </div>

        {/* Capacity curve */}
        <div className="mb-12">
          <h3 className="font-serif text-2xl mb-2">Capacity curve</h3>
          <p className="text-muted mb-2 max-w-prose">
            Each point is the strategy run at a different AUM with trades scaled
            linearly. Y-axis is the Information Ratio after every cost; X-axis is
            AUM (log scale). The dashed line is the IR=0.5 PM hurdle.
          </p>
          <Block tex={String.raw`\text{Net IR}(A) = \frac{\mathbb{E}[r^{\text{gross}}_t] - c(A) / 252}{\sigma_t}, \quad c(A) = \frac{\sum_t \text{TotalCost}_t(A)}{A \cdot \text{years}}`} />
          <div className="card">
            <CapacityCurve curve={f.curve} stress={f.stress_curve} />
          </div>
        </div>

        {/* Cost stack */}
        <div className="mb-12">
          <h3 className="font-serif text-2xl mb-2">Cost decomposition</h3>
          <p className="text-muted mb-3 max-w-prose">
            Stacked annualised cost in bps, split by component. Spread, commission
            and India tax are roughly linear in turnover. Impact bends &mdash; square-root
            in participation up to the 10% of ADV threshold, then power-0.6.
          </p>
          <div className="card">
            <CostStack curve={f.curve} />
          </div>
        </div>

        {/* Crowding */}
        <div className="mb-12">
          <h3 className="font-serif text-2xl mb-2">Crowding score</h3>
          <p className="text-muted mb-3 max-w-prose">
            Six external + internal signals each rolling-percentile-ranked into 0&ndash;100,
            then weighted into a composite. Higher = more crowded.
          </p>
          <Block tex={String.raw`\text{Crowding}(t) = \sum_k w_k \cdot \text{pct\!-rank}\bigl(\text{signal}_k(t)\bigr), \quad \sum_k w_k = 1`} />
          <div className="card">
            <CrowdingChart components={f.crowding_components} composite={f.crowding_composite} />
          </div>
          <div className="grid md:grid-cols-2 gap-4 mt-4">
            <div className="card">
              <h4 className="font-serif text-xl mb-2">Latest snapshot</h4>
              <CrowdingRadar data={f.crowding_components_latest} />
            </div>
            <div className="card overflow-x-auto">
              <h4 className="font-serif text-xl mb-2">Component scores</h4>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-rule text-left">
                    <th className="py-2">signal</th>
                    <th className="py-2 text-right">score</th>
                    <th className="py-2">interpretation</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(f.crowding_components_latest).map(([k, v]) => (
                    <tr key={k} className="border-b border-rule">
                      <td className="py-2 font-mono">{k}</td>
                      <td className="py-2 text-right font-mono">{Math.round(v as number)}</td>
                      <td className="py-2 text-muted">{interpretation(k)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Alpha forecast (ML) */}
        <div className="mb-12">
          <h3 className="font-serif text-2xl mb-2">Alpha-decay forecast</h3>
          <p className="text-muted mb-3 max-w-prose">
            Six-month forward Sharpe projected via a mean-reverting state-space
            model fit on rolling 1-year IR. Crowding is the regime covariate &mdash;
            heavier crowding pulls the long-run attractor down.
          </p>
          <Block tex={String.raw`\Delta s_t = -\kappa\,(s_t - \mu_t) + \varepsilon_t, \qquad \mu_t = \alpha + \beta \cdot \text{crowd}_t`} />
          <div className="grid md:grid-cols-3 gap-4 mb-3 text-sm">
            <div className="card">
              <div className="kicker mb-1">half-life</div>
              <div className="font-serif text-2xl">{f.ml_forecast.half_life_days.toFixed(0)} days</div>
              <div className="text-muted text-xs">deviation from attractor halves in this many days</div>
            </div>
            <div className="card">
              <div className="kicker mb-1">crowding loading β</div>
              <div className="font-serif text-2xl">{f.ml_forecast.fitted_beta.toFixed(3)}</div>
              <div className="text-muted text-xs">slope of attractor on crowding score</div>
            </div>
            <div className="card">
              <div className="kicker mb-1">in-sample RMSE</div>
              <div className="font-serif text-2xl">{f.ml_forecast.rmse.toFixed(3)}</div>
              <div className="text-muted text-xs">daily increment residual, IR units</div>
            </div>
          </div>
          <div className="card">
            <AlphaForecast
              history={f.daily_returns}
              forecast={f.ml_forecast.forecast}
              fanLower={f.ml_forecast.fan_lower}
              fanUpper={f.ml_forecast.fan_upper}
            />
          </div>
        </div>

        {/* Policy table */}
        <div className="mb-12">
          <h3 className="font-serif text-2xl mb-2">Operating policy search</h3>
          <p className="text-muted mb-3 max-w-prose">
            Search over rebalance frequency × no-trade buffer at the safe-AUM target.
            The optimal point is highlighted.
          </p>
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-rule text-left">
                  <th className="py-2 px-2">freq</th>
                  <th className="py-2 px-2 text-right">buffer (bps)</th>
                  <th className="py-2 px-2 text-right">gross IR</th>
                  <th className="py-2 px-2 text-right">net IR</th>
                  <th className="py-2 px-2 text-right">cost (bps)</th>
                  <th className="py-2 px-2 text-right">max exec days</th>
                </tr>
              </thead>
              <tbody>
                {f.policy_grid.map((p, i) => {
                  const isBest = p.freq === f.best_policy.freq
                                  && p.buffer_bps === f.best_policy.buffer_bps;
                  return (
                    <tr key={i} className={`border-b border-rule ${isBest ? "bg-[#f7f4ec]" : ""}`}>
                      <td className="py-1 px-2 font-mono">{p.freq}</td>
                      <td className="py-1 px-2 font-mono text-right">{p.buffer_bps}</td>
                      <td className="py-1 px-2 font-mono text-right">{p.gross_ir.toFixed(2)}</td>
                      <td className={`py-1 px-2 font-mono text-right ${isBest ? "font-bold text-accent" : ""}`}>{p.net_ir.toFixed(2)}</td>
                      <td className="py-1 px-2 font-mono text-right">{Math.round(p.total_cost_bps)}</td>
                      <td className="py-1 px-2 font-mono text-right">{p.max_exec_days.toFixed(1)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Checkpoints */}
        <div className="mb-12">
          <h3 className="font-serif text-2xl mb-2">Capacity checkpoints</h3>
          <p className="text-muted mb-3 max-w-prose">
            As AUM utilisation climbs through 50% / 75% / 90% of safe capacity,
            execute these operational changes.
          </p>
          <div className="grid md:grid-cols-3 gap-4">
            {f.checkpoints.map((c, i) => (
              <div key={i} className="card">
                <div className="kicker mb-1">{Math.round(c.pct_of_safe * 100)}% checkpoint</div>
                <div className="font-serif text-2xl mb-2">{fmtCr(c.aum)}</div>
                <p className="text-sm text-muted">{c.rule}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─────────────  Multi-factor allocation  ───────────── */}
      <section className="max-w-6xl mx-auto px-6 py-12 border-t border-rule">
        <SectionHeader
          kicker="Joint capacity"
          title="Multi-factor allocation"
          lede="Total target AUM split across factors to maximise expected net return, constrained by the crowding red line."
        />
        <Block tex={String.raw`\max_{w_1,\ldots,w_K}\;\sum_{k=1}^{K}\alpha_k(w_k\cdot A)\cdot w_k\cdot A
\quad \text{s.t.}\quad \sum_k w_k = 1,\; w_k\geq 0,\; \text{Crowding}_k\leq s_{\max}`} />
        <div className="grid md:grid-cols-3 gap-4 mb-6">
          <Kpi label="Total AUM"
                value={fmtCr(data.multi_factor.total_aum)}
                hint="2× max single-factor safe capacity" />
          <Kpi label="Expected net return"
                value={fmtPct(data.multi_factor.expected_net_return_pct)}
                hint="annualised, after all costs" />
          <Kpi label="Selected factors"
                value={`${Object.values(data.multi_factor.weights).filter(w => w > 0).length}/${factors.length}`}
                hint="non-zero allocations" />
        </div>
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-rule text-left">
                <th className="py-2 px-2">factor</th>
                <th className="py-2 px-2 text-right">weight</th>
                <th className="py-2 px-2 text-right">AUM</th>
                <th className="py-2 px-2 text-right">net IR</th>
                <th className="py-2 px-2 text-right">crowding</th>
              </tr>
            </thead>
            <tbody>
              {factors.map((name) => {
                const w = data.multi_factor.weights[name] ?? 0;
                const aum = data.multi_factor.aum_allocations[name] ?? 0;
                const ir = data.multi_factor.factor_irs[name] ?? 0;
                const crowd = data.factors[name]?.crowding_latest ?? 0;
                return (
                  <tr key={name} className="border-b border-rule">
                    <td className="py-2 px-2 font-mono">{name}</td>
                    <td className="py-2 px-2 text-right font-mono">{(w * 100).toFixed(1)}%</td>
                    <td className="py-2 px-2 text-right font-mono">{fmtCr(aum)}</td>
                    <td className="py-2 px-2 text-right font-mono">{ir.toFixed(2)}</td>
                    <td className="py-2 px-2 text-right font-mono">{Math.round(crowd)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* ─────────────  ML capacity model  ───────────── */}
      <section className="max-w-6xl mx-auto px-6 py-12 border-t border-rule">
        <SectionHeader
          kicker="ML layer · ridge regression"
          title="Capacity prediction model"
          lede="A small ridge regressor that lets you predict 'safe AUM' from market state without re-running the full curve. Lambda picked by leave-one-out CV."
        />
        <Block tex={String.raw`\hat\beta = (X^\top X + \lambda I)^{-1} X^\top y, \qquad y = \log_{10}(\text{safe AUM})`} />
        <div className="grid md:grid-cols-3 gap-4 mb-6">
          <Kpi label="In-sample R²"
                value={data.ml.capacity_model.r2.toFixed(2)}
                hint="how much variance the linear model explains" />
          <Kpi label="Selected λ"
                value={data.ml.capacity_model.lambda.toFixed(2)}
                hint="ridge regularisation, picked by LOO-CV" />
          <Kpi label="Features"
                value={data.ml.capacity_model.feature_names.length}
                hint="spread, vol, ADV, crowding, gross IR" />
        </div>
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-rule text-left">
                <th className="py-2 px-2">feature</th>
                <th className="py-2 px-2 text-right">β coefficient</th>
                <th className="py-2 px-2 text-muted">interpretation</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(data.ml.capacity_model.coefficients).map(([k, v]) => (
                <tr key={k} className="border-b border-rule">
                  <td className="py-2 px-2 font-mono">{k}</td>
                  <td className="py-2 px-2 text-right font-mono">{(v as number).toFixed(4)}</td>
                  <td className="py-2 px-2 text-muted">{coefInterp(k, v as number)}</td>
                </tr>
              ))}
              <tr className="border-b border-rule">
                <td className="py-2 px-2 font-mono">intercept</td>
                <td className="py-2 px-2 text-right font-mono">{data.ml.capacity_model.intercept.toFixed(4)}</td>
                <td className="py-2 px-2 text-muted">log₁₀ AUM at zero feature values</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

function interpretation(key: string): string {
  return {
    valuation_spread: "narrow long-vs-short P/B spread → factor mispricing arbitraged out (Asness)",
    alpha_decay: "negative slope of trailing 1y IR → edge being competed away (Arnott)",
    short_interest: "weighted SI on the short leg → squeeze risk and high borrow (Drechsler)",
    comomentum: "long-leg names moving in lockstep → same arbitrageurs (Lou-Polk)",
    holdings_overlap: "fraction of long names also held long by other factors (Sias)",
    internal_footprint: "strategy's own liquidity strain at base AUM",
  }[key] ?? "";
}

function coefInterp(key: string, beta: number): string {
  const sign = beta >= 0 ? "increases" : "decreases";
  return {
    spread_bps: `+1 bp of spread ${sign} log-AUM by ${beta.toFixed(3)}`,
    vol: `+1pt vol ${sign} log-AUM by ${beta.toFixed(3)}`,
    log_adv: `+1 in log10(ADV) ${sign} log-AUM by ${beta.toFixed(3)}`,
    crowding: `+1pt crowding score ${sign} log-AUM by ${beta.toFixed(3)}`,
    gross_ir: `+1 unit of gross IR ${sign} log-AUM by ${beta.toFixed(3)}`,
  }[key] ?? "";
}
