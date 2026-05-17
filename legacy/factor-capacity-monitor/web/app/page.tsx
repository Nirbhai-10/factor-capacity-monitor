import { Block, Inline } from "@/components/Math";
import { ReferencePreview } from "@/components/ReferencePreview";

export default function Home() {
  return (
    <>
      {/* Hero */}
      <section className="section-narrow text-left">
        <div className="kicker mb-3">FactorCapacity-Nirbhai · buy-side research tool</div>
        <h1 className="font-serif">
          What is the largest AUM at which your factor still pays for itself?
        </h1>
        <p className="lede mt-6">
          Drop a daily P&amp;L CSV. The tool estimates your capacity curve, forecasts
          forward Sharpe, computes a drawdown profile, runs a what-if AUM
          calculator and a cost-sensitivity heatmap, finds the rebalance rule
          that maximises net IR after costs, and benchmarks you against four
          reference factors run on the same machinery.
        </p>
        <div className="flex flex-wrap gap-3 mt-8">
          <a href="/analyze" className="btn btn-primary no-underline">
            Open the tool →
          </a>
          <a href="#preview" className="btn no-underline">
            See it on reference factors ↓
          </a>
        </div>
      </section>

      <hr className="divider mx-auto max-w-3xl" />

      {/* Reference preview — embedded so visitors don't have to navigate */}
      <section id="preview" className="section">
        <div className="kicker mb-3">Demo · reference run</div>
        <h2 className="font-serif mb-3">A live look at the same machinery on four reference factors.</h2>
        <p className="text-[var(--muted)] mb-8 max-w-prose">
          Synthetic NIFTY-100-like panel, 5 years, 100 names. Capacity curves
          on one axis, headline numbers below. Click any row through to the
          full <a href="/reference">reference run</a> for the cost decomposition,
          composite crowding score and ML forecast.
        </p>
        <ReferencePreview />
        <div className="mt-6">
          <a href="/reference" className="btn no-underline">Full reference run →</a>
        </div>
      </section>

      <hr className="divider mx-auto max-w-3xl" />

      {/* Why */}
      <section className="section-narrow">
        <div className="kicker mb-3">Why</div>
        <h2 className="font-serif mb-6">
          Two compounding mechanisms degrade factor returns at scale.
        </h2>
        <div className="space-y-4 text-[1.02rem]">
          <p>
            Every factor strategy &mdash; momentum, value, quality, low-volatility &mdash; earns
            positive expected returns at small AUM and earns less at larger AUM.
            The usual story is &quot;alpha decays as size grows.&quot; That story is
            incomplete. Two distinct mechanisms compound on each other:
          </p>
          <p>
            <strong>Trading-cost drag.</strong> Costs scale super-linearly with size.
            Spread is roughly constant per unit of trade, but market impact grows
            like <Inline tex="\sqrt{Q/V}" /> (Almgren&ndash;Chriss) and faster than that
            for large notionals. At some AUM the marginal alpha is fully consumed
            by impact.
          </p>
          <p>
            <strong>Crowding.</strong> Other managers run the same signal. As capital
            piles in, the long basket bids up and the short basket gets squeezed.
            Realised alpha decays <em>before</em> trading costs even fire. Drawdowns
            become correlated across funds and unwinds become reflexive.
          </p>
          <p>
            The PM-level question is not &quot;what is my Sharpe at infinite AUM&quot; &mdash; it is:
            <em> given my AUM today, my factors&apos; current crowding, and my real cost
            stack, what is my hard cap and what is my safe rebalancing rule?</em>
          </p>
        </div>
      </section>

      <hr className="divider mx-auto max-w-3xl" />

      {/* What you get */}
      <section className="section-narrow">
        <div className="kicker mb-3">Workflow</div>
        <h2 className="font-serif mb-6">From CSV to memo in under a minute.</h2>
        <ol className="space-y-5 list-none">
          {[
            { n: "1", t: "Drop your CSV", d: "Two columns: date and either daily return, P&L %, NAV, or equity. Auto-detected." },
            { n: "2", t: "Confirm cost parameters",
              d: "Spread, impact coefficient, commission, borrow, turnover, ADV bucket, India tax stack on/off. Defaults match an NSE mid-cap L/S sleeve." },
            { n: "3", t: "Read the answers",
              d: "Capacity curve, cost decomposition, drawdown profile, rolling Sharpe + 6-month forecast, what-if AUM calculator, sensitivity heatmap, optimal policy." },
            { n: "4", t: "Export", d: "Download the memo.md and curve.csv. Share with risk, ops, or the IC." },
          ].map((s) => (
            <li key={s.n} className="grid grid-cols-[2rem_1fr] gap-3 items-baseline">
              <div className="font-serif text-2xl text-[#a08c5d]">{s.n}</div>
              <div>
                <div className="font-serif text-xl mb-1">{s.t}</div>
                <p className="text-[var(--muted)]">{s.d}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <hr className="divider mx-auto max-w-3xl" />

      {/* Math sample */}
      <section className="section-narrow">
        <div className="kicker mb-3">The model</div>
        <h2 className="font-serif mb-4">The capacity curve in one equation.</h2>
        <Block tex={String.raw`\text{Net IR}(A) = \frac{\mathbb{E}[r^{\text{gross}}_t] - c(A)/252}{\sigma_t}`} />
        <p className="text-[var(--muted)]">
          where <Inline tex="c(A)" /> is the annualised round-trip cost at AUM
          <Inline tex="\,A" />, summed across spread, Almgren&ndash;Chriss impact,
          commission, short-leg borrow and (optionally) the NSE tax stack.
          A separate ridge regression learns to predict
          <Inline tex="\,A_{\text{safe}}" /> from market state without re-running
          the curve. See the <a href="/methodology">full methodology</a> for the
          stress regime, multi-factor allocation, and the OU forecast.
        </p>
        <div className="mt-8">
          <a href="/analyze" className="btn btn-primary no-underline">
            Run it on your strategy →
          </a>
        </div>
      </section>
    </>
  );
}
