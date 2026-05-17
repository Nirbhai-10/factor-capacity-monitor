import { SectionHeader } from "@/components/SectionHeader";
import { Block, Inline } from "@/components/Math";

export default function Methodology() {
  return (
    <article className="max-w-prose mx-auto px-6 py-16">
      <SectionHeader kicker="Reference"
                       title="Methodology"
                       lede="The mathematics behind every number in the dashboard. Each section is self-contained." />

      <h2 className="font-serif text-3xl mt-12 mb-3">1. Bid-ask spread (Corwin-Schultz)</h2>
      <p>
        Estimated from daily OHLC without requiring a quote tape. The two-day
        estimator is:
      </p>
      <Block tex={String.raw`\beta = \mathbb{E}\bigl[(\ln\tfrac{H_t}{L_t})^2 + (\ln\tfrac{H_{t+1}}{L_{t+1}})^2\bigr]`} />
      <Block tex={String.raw`\gamma = \mathbb{E}\bigl[(\ln\tfrac{H_{t,t+1}}{L_{t,t+1}})^2\bigr]`} />
      <Block tex={String.raw`\alpha = \frac{\sqrt{2\beta} - \sqrt{\beta}}{3-2\sqrt{2}} - \sqrt{\frac{\gamma}{3-2\sqrt{2}}}`} />
      <Block tex={String.raw`s = \frac{2(e^\alpha - 1)}{1 + e^\alpha}`} />
      <p>
        Rolling 21-day window, floored at zero. Where CS fails (insufficient
        intraday range, illiquid days), we fall back to an ADV-bucket regression:
        <Inline tex="\,s_{\text{bps}} = 50 - 5.5 \log_{10}\text{ADV}." />
      </p>

      <h2 className="font-serif text-3xl mt-12 mb-3">2. Market impact (Almgren-Chriss + tail)</h2>
      <p>
        Per-name impact as a fraction of trade value, with a piecewise tail
        above 10% participation following Almgren et al. (2005):
      </p>
      <Block tex={String.raw`
\text{impact}_i =
\begin{cases}
  \sigma_i\,k\sqrt{p_i}, & p_i \leq p^* \\[4pt]
  \sigma_i\,k\sqrt{p^*}\bigl(1 + \tfrac{p_i - p^*}{p^*}\bigr)^{0.6}, & p_i > p^*
\end{cases}`} />
      <p>
        with <Inline tex="p_i = |Q_i|/(V_i\,T_i)" /> the participation,
        <Inline tex="\,k\in[0.10,0.30]" /> calibrated by AQR fills
        (Frazzini-Israel-Moskowitz 2018), and <Inline tex="\,p^* = 10\%" /> the
        threshold above which impact departs from the square-root law.
      </p>

      <h2 className="font-serif text-3xl mt-12 mb-3">3. India NSE tax stack</h2>
      <p>STT, stamp, SEBI, exchange, GST stack on every leg of every trade:</p>
      <ul className="list-disc pl-6 my-3 space-y-1 text-sm">
        <li>STT (delivery): 0.10% on both legs</li>
        <li>Stamp duty: 0.015% on buy</li>
        <li>SEBI fee: ₹10 / cr</li>
        <li>Exchange (NSE cash): 0.00345%</li>
        <li>GST: 18% on (brokerage + SEBI + exch)</li>
      </ul>
      <p>
        For weekly rebalances, STT alone burns roughly 300 bps/yr &mdash; the policy
        optimiser correctly steers Indian factor sleeves toward monthly or
        quarterly rebalances.
      </p>

      <h2 className="font-serif text-3xl mt-12 mb-3">4. Capacity zone classifier</h2>
      <table className="w-full text-sm my-4 border-collapse">
        <thead><tr className="border-b border-rule text-left">
          <th className="py-2">zone</th><th>Net IR</th><th>max execution days</th><th>max participation</th>
        </tr></thead>
        <tbody>
          <tr className="border-b border-rule"><td className="py-2"><span className="zone-pill zone-safe">safe</span></td><td>≥ 0.5</td><td>≤ 3</td><td>&lt; 3%</td></tr>
          <tr className="border-b border-rule"><td className="py-2"><span className="zone-pill zone-caution">caution</span></td><td>≥ 0.2</td><td>≤ 5</td><td>&lt; 5%</td></tr>
          <tr><td className="py-2"><span className="zone-pill zone-red">red</span></td><td>&lt; 0.2</td><td>&gt; 5</td><td>≥ 5%</td></tr>
        </tbody>
      </table>

      <h2 className="font-serif text-3xl mt-12 mb-3">5. Composite crowding score</h2>
      <Block tex={String.raw`\text{Crowding}(t) = \sum_k w_k \cdot \text{pct\!-rank}\bigl(\text{signal}_k(t)\bigr), \quad \sum_k w_k = 1`} />
      <p>Six components, each rolling-percentile-ranked against its own 3-year history:</p>
      <ul className="list-disc pl-6 my-3 space-y-1 text-sm">
        <li><strong>Valuation spread</strong> &mdash; <Inline tex="1 / (\bar{P/B}_{\text{short}} - \bar{P/B}_{\text{long}})" /> &mdash; Asness, Friedman, Israel (2017)</li>
        <li><strong>Alpha decay</strong> &mdash; negative slope of trailing-1y IR over 2y &mdash; Arnott et al. (2017)</li>
        <li><strong>Short interest</strong> &mdash; weighted SI on the short leg &mdash; Drechsler (2014)</li>
        <li><strong>Comomentum</strong> &mdash; mean pairwise correlation of long-leg returns &mdash; Lou, Polk (2013)</li>
        <li><strong>Holdings overlap</strong> &mdash; fraction of long names also held by peers &mdash; Sias (2016)</li>
        <li><strong>Internal liquidity footprint</strong> &mdash; <Inline tex="\sum |\text{trade}_i| / \sum V_i" /> &mdash; legacy</li>
      </ul>

      <h2 className="font-serif text-3xl mt-12 mb-3">6. Stress regime</h2>
      <p>Single-quantile snapshot. Replace each per-symbol parameter with its tail value:</p>
      <ul className="list-disc pl-6 my-3 space-y-1 text-sm">
        <li>spread → 99th percentile</li>
        <li>ADV → 25th percentile</li>
        <li>vol → 95th percentile</li>
        <li>impact coefficient <Inline tex="k" /> → 1.5× nominal</li>
        <li>borrow premium → +200 bps</li>
        <li>short interest → +5 pp</li>
      </ul>
      <Block tex={String.raw`A_{\text{cap}} = \min\bigl(A_{\text{safe}}^{\text{nominal}}, A_{\text{safe}}^{\text{stressed}}\bigr)`} />
      <p>
        Plus a one-shot 30%-redemption unwind in 5 days, costed under the same
        stressed market state. The unwind cost is reported as basis points of
        the AUM being shed.
      </p>

      <h2 className="font-serif text-3xl mt-12 mb-3">7. Multi-factor allocation</h2>
      <Block tex={String.raw`\max_{w_1,\ldots,w_K}\;\sum_{k=1}^{K}\alpha_k(w_k\cdot A)\cdot w_k\cdot A
\quad \text{s.t.}\quad \sum_k w_k = 1,\; w_k\geq 0,\; \text{Crowding}_k\leq s_{\max}`} />
      <p>
        Each <Inline tex="\alpha_k(\cdot)" /> is the per-factor net-return-vs-AUM
        curve (concave). Exhaustive grid search at 21 points per dimension,
        K=4 → 200k combinations &lt; 100 ms. Coordinate descent for K&gt;6.
      </p>

      <h2 className="font-serif text-3xl mt-12 mb-3">8. ML &mdash; alpha decay forecast</h2>
      <p>State-space mean reversion with crowding as the regime covariate:</p>
      <Block tex={String.raw`\Delta s_t = -\kappa\,(s_t - \mu_t) + \varepsilon_t, \qquad \mu_t = \alpha + \beta \cdot \text{crowd}_t`} />
      <p>
        Fit <Inline tex="(\alpha,\beta,\kappa)" /> by OLS on the stacked
        increments. Forecast 126 trading days forward by integrating the SDE
        deterministically and reporting a <Inline tex="\pm 1\sigma" /> fan based
        on the residual RMSE scaled by <Inline tex="\sqrt{1 - e^{-2\kappa h}}" />.
      </p>

      <h2 className="font-serif text-3xl mt-12 mb-3">9. ML &mdash; capacity ridge model</h2>
      <Block tex={String.raw`\hat\beta = (X^\top X + \lambda I)^{-1} X^\top y`} />
      <p>
        Closed-form ridge regression on five features
        (spread, vol, log ADV, crowding, gross IR) → log<sub>10</sub>(safe AUM).
        Lambda picked by leave-one-out CV on a fixed grid. Lets you predict
        safe AUM from current market state without re-running the full curve scan.
      </p>

      <h2 className="font-serif text-3xl mt-12 mb-3">10. ML &mdash; regime classifier (GMM)</h2>
      <p>
        Three-component diagonal-covariance Gaussian mixture, fit by EM on
        standardised daily features (market vol, average pairwise correlation,
        median spread, log ADV). Components are post-hoc labelled by ranking
        the centroids on market vol &mdash; lowest = &quot;calm&quot;, highest = &quot;stressed&quot;.
      </p>
      <Block tex={String.raw`p(x) = \sum_{j=1}^{3} \pi_j \cdot \mathcal{N}(x \mid \mu_j, \mathrm{diag}(\sigma_j^2))`} />

      <h2 className="font-serif text-3xl mt-12 mb-3">References</h2>
      <ol className="list-decimal pl-6 text-sm space-y-1">
        <li>Almgren, Chriss (2000). &quot;Optimal execution of portfolio transactions&quot;.</li>
        <li>Almgren et al. (2005). &quot;Direct estimation of equity market impact&quot;.</li>
        <li>Lou, Polk (2013). &quot;Comomentum: Inferring arbitrage activity&quot;.</li>
        <li>Drechsler, Drechsler (2014). &quot;The shorting premium&quot;.</li>
        <li>Sias, Turtle, Zykaj (2016). &quot;Hedge-fund crowds and mispricing&quot;.</li>
        <li>Arnott, Hsu, West (2017). &quot;How can &lsquo;smart beta&rsquo; go horribly wrong?&quot;.</li>
        <li>Asness, Friedman, Israel (2017). &quot;Style timing: value vs growth&quot;.</li>
        <li>Frazzini, Israel, Moskowitz (2018). &quot;Trading costs&quot; (AQR).</li>
        <li>Corwin, Schultz (2012). &quot;A simple way to estimate bid-ask spreads from daily high and low prices&quot;.</li>
        <li>Lou, Polk, Skouras (2019). &quot;A tug of war: Overnight versus intraday returns&quot;.</li>
      </ol>
    </article>
  );
}
