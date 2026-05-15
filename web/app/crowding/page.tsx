import { Block, Inline } from "@/components/Math";

export const metadata = {
  title: "Measuring crowding — research notes · FactorCapacity-Nirbhai",
};

export default function CrowdingPage() {
  return (
    <article className="section-narrow">
      <div className="kicker mb-3">Research notes</div>
      <h1 className="font-serif">Measuring crowding for factor strategies</h1>
      <p className="lede mt-6">
        How I thought about this, what I built, what literature I leaned on, and
        what the tool is actually doing in the background.
      </p>

      <hr className="divider" />

      {/* ───────────── Premise ───────────── */}
      <h2 className="font-serif mt-12">Why crowding deserves its own monitor</h2>
      <div className="space-y-4 mt-4">
        <p>
          A factor gets &quot;crowded&quot; when too many managers are running the same
          playbook at the same time. What this looks like in your P&amp;L is
          actually pretty simple. Your alpha starts decaying even before
          trading costs kick in. Drawdowns of multiple funds line up together,
          which never used to happen. Valuation spread between the long basket
          and short basket compresses, so the thing you were trying to exploit
          is already in the price. And the worst part is the unwind. When one
          fund decides to cut, everyone else is forced into selling the same
          twenty names in the same week, because every other fund holds the
          same twenty names.
        </p>
        <p>
          If you only watch realised Sharpe, you don&apos;t see any of this
          coming. Sharpe is a lagging indicator, it drops <em>after</em> the
          damage is done. You want something that looks at the structure of
          the trade itself, not just the outcome.
        </p>
        <p>
          The prototype I inherited was measuring exactly one thing, how much
          of the daily ADV my own trades were eating up. That tells you if
          you&apos;re crowding yourself out of the trade. It tells you nothing
          about whether half the buyside is positioned identical to you. Useful
          but it&apos;s missing most of the picture itself.
        </p>
        <p>
          So I treated crowding as a multi-signal problem. Sat with the
          literature for couple of weeks, picked out the proxies that capture
          different parts of what crowding does to a factor, and implemented
          each one as its own small module. Each signal can be swapped, dropped,
          reweighted, without breaking anything else in the pipeline. Six
          signals fell out of the reading. I built all six.
        </p>
      </div>

      <hr className="divider" />

      {/* ───────────── Six signals overview ───────────── */}
      <h2 className="font-serif mt-12">The six signals</h2>
      <p className="mt-3">
        Each signal gives back a time series indexed on rebalance dates. Then
        it&apos;s rolling-percentile-ranked against its own 3-year history. The
        ranking is what makes the six numbers addable. Without it they live in
        totally different units and averaging them is meaningless, I cover
        this more below.
      </p>
      <p className="mt-3">
        I&apos;ll go through them one by one.
      </p>

      {/* 1 */}
      <h3 className="font-serif mt-10">1 · Valuation spread <span className="text-[var(--muted)] font-normal text-base">(Asness, Friedman, Israel 2017)</span></h3>
      <Block tex={String.raw`\text{score}_t = \mathrm{pct\!-rank}\!\left(\frac{1}{\overline{P/B}_{\text{short},t} - \overline{P/B}_{\text{long},t}}\right)`} />
      <p>
        A value factor that is actually working should have a healthy gap
        between the average P/B of its long leg and the average P/B of its
        short leg. Long leg at P/B around 1.5, short leg at 4.0, gives you a
        spread of 2.5. That spread is, in a sense, the size of the mispricing
        you are harvesting.
      </p>
      <p>
        When the spread tightens — say the long leg gets bid up to 2.5 and
        the short leg falls to 3.0, gap is now only 0.5 — the mispricing has
        been arbitraged out. The market is figured out the value trade and
        priced it in. So I take reciprocal, so that compressed spread reads
        as a higher number.
      </p>
      <p>
        Important thing: I run this on every factor, not only value. Sounds
        weird because the construction is a P/B based diagnostic, but think
        about it this way. A momentum portfolio that is increasingly long on
        names which are also expensive is structurally weaker than a momentum
        portfolio that&apos;s long on cheap names with momentum. The valuation
        spread of the momentum long-leg vs short-leg tells me something even
        though &quot;value&quot; isn&apos;t what the strategy is trading on. Asness wrote
        the original paper as value-timing tool. I am repurposing it as
        generic crowding gauge for any factor.
      </p>

      {/* 2 */}
      <h3 className="font-serif mt-10">2 · Alpha-decay slope <span className="text-[var(--muted)] font-normal text-base">(Arnott, Hsu, West 2017)</span></h3>
      <Block tex={String.raw`\text{score}_t = \mathrm{pct\!-rank}\!\left(-\hat\beta_t\right), \quad
\hat\beta_t = \arg\min_\beta \sum_{s=t-2y}^{t}\bigl(\mathrm{IR}_s - \alpha - \beta s\bigr)^2`} />
      <p>
        For each rebalance date I compute trailing 1-year IR. Then I fit a
        simple linear regression of that IR series against time, over the
        past 2 years window. The slope of that regression is what I care
        about. If IR is consistently declining over the last 24 months,
        slope will be negative, and I&apos;m saying the factor&apos;s edge is being
        competed away in real time. Sign flip so &quot;decaying&quot; = higher score.
      </p>
      <p>
        Why this signal: Arnott, Hsu and West have a really good paper called
        &quot;How can smart beta go horribly wrong?&quot; from 2017, where they argue
        most of the published factor outperformance after the original paper
        is published, is just the factor getting more expensive. Not new alpha
        at all, just the original mispricing being priced in. They use
        valuation spread as evidence. I am using the actual rolling IR slope
        as a faster moving sibling.
      </p>
      <p>
        One thing I noticed when I was implementing this: a 2-year window is
        actually quite long. Quant strategies often have 6-month rolling
        cycles where IR drops, then recovers, then drops again. Using 2 years
        smooths out that noise but it also means the signal is slow — by the
        time the slope turns negative, the factor has been crowded for a
        while already. I could shorten the window to 1 year but then false
        positives go up a lot. 2 years felt like reasonable tradeoff.
      </p>

      {/* 3 */}
      <h3 className="font-serif mt-10">3 · Short-interest pressure <span className="text-[var(--muted)] font-normal text-base">(Drechsler &amp; Drechsler 2014)</span></h3>
      <Block tex={String.raw`\text{score}_t = \mathrm{pct\!-rank}\!\left(\frac{\sum_i \mathbf{1}[w_{i,t}<0]\cdot|w_{i,t}|\cdot SI_{i,t}}{\sum_i \mathbf{1}[w_{i,t}<0]\cdot|w_{i,t}|}\right)`} />
      <p>
        Weighted average of short interest on my short leg, where weights are
        the absolute short weights of each name in the leg. Concrete example.
        Suppose I&apos;m short 4 names equally. Their short interest as % of
        float are 15%, 20%, 5%, 2%. Equal weighted average = 10.5%. So my
        signal value is 10.5%, and then I rank that 10.5% against the past 3
        years of my own history of this number to get the percentile score.
      </p>
      <p>
        Why high SI on my shorts is bad — three reasons at once, all
        compounding. One, other funds are short the same names, so we are
        all positioned same. Two, my borrow rate is being squeezed by the
        demand for shares, so the carry cost on the short leg goes up. Three,
        if any of these names rallies sharply, all those shorts get force
        covered together. That&apos;s a short squeeze cascade, and historically
        these are the worst single-week losses for L/S funds. Volkswagen
        2008. GameStop 2021. Same mechanic.
      </p>
      <p>
        Drechsler &amp; Drechsler&apos;s paper from 2014 made this very clear, the
        cost of shorting <em>is</em> the price of crowding on the short side.
        Their result is asset-pricing oriented (they show short premium
        explains anomaly returns), but for my purpose I&apos;m just using it as
        regime indicator. If SI level is in 90th percentile of its 3-year
        history, something is up.
      </p>

      {/* 4 */}
      <h3 className="font-serif mt-10">4 · Comomentum <span className="text-[var(--muted)] font-normal text-base">(Lou &amp; Polk 2013)</span></h3>
      <Block tex={String.raw`\text{score}_t = \mathrm{pct\!-rank}\!\left(\frac{2}{N(N-1)}\sum_{i<j\in L_t}\hat\rho_{ij,[t-60,t]}\right)`} />
      <p>
        Take all the names on my long leg. For every pair of names in that
        leg, compute their daily return correlation over last 60 trading
        days. Average all those pairwise correlations (that&apos;s the upper
        triangle of correlation matrix). That average is the signal.
      </p>
      <p>
        Intuition is the cleanest of all six in my opinion. If all the names
        on my long leg are moving in lockstep, beyond what their
        fundamentals or sector would justify, then somebody is buying them
        all together. That &quot;somebody&quot; is likely a basket of arbitrageurs who
        are also positioned on this exact same factor. The names start to
        move together not because of news, but because of capital flow.
      </p>
      <p>
        This is the signal I trust most for early warning. Reason being:
        valuation spread can stay tight for years without anything bad
        happening (Japan value spreads were tight for decade plus, no crash).
        Alpha decay is slow to turn. Short interest can spike for
        idiosyncratic reasons. But unusually high pairwise correlation in my
        long basket is hard to explain with anything except common ownership
        — and common ownership is literally crowding.
      </p>
      <p>
        Lou and Polk&apos;s paper is from 2013, working paper at LSE. Their
        contribution was to apply this specifically to momentum, to predict
        momentum crashes. I borrowed the construction and applied it as a
        generic crowding signal to all factors.
      </p>

      {/* 5 */}
      <h3 className="font-serif mt-10">5 · Holdings overlap <span className="text-[var(--muted)] font-normal text-base">(Sias, Turtle, Zykaj 2016)</span></h3>
      <Block tex={String.raw`\text{score}_t = \mathrm{pct\!-rank}\!\left(\frac{|L_t^{\,k}\cap (\bigcup_{j\neq k} L_t^{\,j})|}{|L_t^{\,k}|}\right)`} />
      <p>
        Cleanest version of this signal uses 13F filings (US) or quarterly
        shareholding patterns (India, where you can see how much of a
        company&apos;s float is held by FIIs, DIIs, mutual funds, etc). With those
        feeds you can directly compute &quot;what fraction of my long-leg names is
        also being held in size by other crowded funds&quot;. That&apos;s the real
        signal.
      </p>
      <p>
        In the demo I don&apos;t have a live 13F or shareholding-pattern feed, so
        I&apos;m using a proxy. The proxy is: out of my long-leg names for factor k,
        what fraction also appear in the long leg of any of my other factors?
        Concrete: momentum long has 20 names today. Quality long has 20
        names. Low-vol long has 20 names. If 14 of momentum&apos;s 20 also appear
        in quality and low-vol&apos;s long legs, my overlap proxy is 14/20 = 0.7.
      </p>
      <p>
        Why this proxy makes sense even though it&apos;s only measuring overlap
        within my own factor sleeve and not against the wider hedge fund
        universe: when momentum, quality, and low-vol all want to own the
        same twenty stocks, the AUM is concentrated systemically. Those
        twenty stocks are the ones that will get hammered if my full sleeve
        unwinds together. Same logic Sias et al. applied to hedge fund
        holdings, just at smaller scale and with internal data.
      </p>
      <p>
        Production version of this should definitely use 13F feed (or NSE
        shareholding pattern for India). The architecture is set up such
        that you drop in a real feed without touching anything downstream,
        only the function inside <code>holdings_overlap.py</code> changes.
      </p>

      {/* 6 */}
      <h3 className="font-serif mt-10">6 · Internal liquidity footprint <span className="text-[var(--muted)] font-normal text-base">(legacy)</span></h3>
      <Block tex={String.raw`\text{score}_t = \mathrm{pct\!-rank}\!\left(\frac{\sum_i |\text{trade}_{i,t}|}{\sum_i V_{i,t}}\right)`} />
      <p>
        Sum of absolute trade dollars I&apos;m putting through, divided by sum
        of the ADV (in dollars) of all the names I&apos;m trading. Basically
        &quot;what fraction of the daily volume am I personally going to
        consume?&quot; Higher number means I&apos;m a bigger fraction of the market
        for the day.
      </p>
      <p>
        This signal is qualitatively different from the other five. The
        other five are all asking &quot;is the rest of the world positioned
        same as me?&quot; This one is asking &quot;am I crowding myself out?&quot; You
        can be crowded all by yourself, even if literally nobody else in
        the world is on this trade, simply because your AUM is too big
        relative to the names you&apos;re trading. A small fund running a
        microcap value strategy can have 100% liquidity footprint without
        ever meeting another fund.
      </p>
      <p>
        I inherited this signal from the prior in-house prototype. Kept it
        because self-crowding is real, but I down-weighted it from
        roughly 1.0 in the old tool to 0.15 in the new composite. Reason:
        on its own this captures only one out of six ways a factor gets
        crowded, and the old tool was treating it as if it&apos;s the whole
        story. It&apos;s not. It&apos;s one input.
      </p>

      <hr className="divider" />

      {/* ───────────── Composite ───────────── */}
      <h2 className="font-serif mt-12">The composite</h2>
      <Block tex={String.raw`\text{Crowding}(t) = \sum_{k=1}^{6} w_k \cdot \text{signal}_k(t), \qquad \sum_k w_k = 1`} />
      <p>
        Default weights, which I keep in <code>config/default.yaml</code>:
      </p>
      <div className="overflow-x-auto my-4">
        <table>
          <thead>
            <tr><th>Component</th><th className="text-right">Weight</th></tr>
          </thead>
          <tbody>
            <tr><td>valuation spread</td><td className="text-right">0.20</td></tr>
            <tr><td>alpha decay</td><td className="text-right">0.20</td></tr>
            <tr><td>short interest</td><td className="text-right">0.15</td></tr>
            <tr><td>comomentum</td><td className="text-right">0.15</td></tr>
            <tr><td>holdings overlap</td><td className="text-right">0.15</td></tr>
            <tr><td>internal footprint</td><td className="text-right">0.15</td></tr>
          </tbody>
        </table>
      </div>
      <p>
        Thresholds: composite ≥ 75 is red zone, ≥ 50 is amber, anything else
        is green. These are tunable in the config too.
      </p>
      <p>
        How I picked the weights: I leaned slightly heavier on valuation
        spread and alpha decay (0.20 each) because they have the strongest
        academic backing for actually predicting forward returns. The other
        four are 0.15 each, equal weight, because honestly I don&apos;t have
        enough live data to differentiate between them statistically. If I
        had 10 years of live crowding episodes to backtest against, I would
        fit the weights by maximum likelihood on which composite best
        anticipates the drawdowns. With synthetic data I can&apos;t do that
        honestly, so I chose roughly equal weights with a slight bias to the
        better-studied signals.
      </p>
      <p>
        Important caveat for anyone using this on real money: the weights
        should be tuned to the strategy. A long-only mutual fund manager
        should zero out short-interest weight (no shorts). A US fund with
        access to 13F feed should up-weight holdings overlap and down-weight
        internal footprint proxy. A high-turnover stat-arb shop should
        up-weight internal footprint significantly because self-crowding
        dominates external. The default config is starting point, not
        doctrine.
      </p>

      <hr className="divider" />

      {/* ───────────── Why rolling percentile ───────────── */}
      <h2 className="font-serif mt-12">Why rolling percentile instead of raw values</h2>
      <p>
        Each of the six raw signals lives in totally different units. Just
        look at them:
      </p>
      <ul className="list-disc pl-6 my-3 space-y-1">
        <li>Valuation spread is in P/B units. Mean around 1.5, can spike to 5+.</li>
        <li>Alpha-decay slope is IR-per-day. Very tiny absolute numbers like 0.0003.</li>
        <li>Comomentum is bounded in <Inline tex="[-1, 1]" />, typically 0.2 to 0.6.</li>
        <li>Short interest is a percentage of float, usually 1% to 30%.</li>
        <li>Holdings overlap is a fraction, 0 to 1.</li>
        <li>Internal footprint is a ratio, can range from 0.001 to 1+.</li>
      </ul>
      <p>
        You cannot just take a weighted average of these. The number 0.5
        means &quot;hot&quot; for comomentum but &quot;cold&quot; for internal footprint, and it
        doesn&apos;t even make sense to compare 0.5 of one to 0.5 of the other
        because the underlying distributions are totally different.
      </p>
      <p>
        I considered three options before settling on rolling-percentile-rank:
      </p>
      <p>
        <strong>Option 1: z-score each signal.</strong> Subtract the long-run
        mean, divide by the long-run standard deviation. This is the
        standard quant move. Problem is, it assumes the underlying
        distribution is roughly Gaussian, which most of these signals are
        not. Comomentum is bounded in [-1,1] and the empirical distribution
        is left-skewed, so z-scoring gives you wrong tail behaviour.
        Alpha-decay slope has heavy tails because of rare regime changes.
        Z-scoring penalises actually-informative tail events.
      </p>
      <p>
        <strong>Option 2: min-max scale to [0, 100] using all-time range.</strong>
        Cleaner than z-score. But sensitive to outliers — one extreme event
        in the historical data permanently rescales everything else. And it
        doesn&apos;t handle secular drift: if valuation spreads have been
        structurally compressed for 10 years, the all-time max was set in
        2008, and current readings always look &quot;low&quot; relative to it.
      </p>
      <p>
        <strong>Option 3: rolling-percentile rank against last 3 years.</strong>
        What I went with. Score of 80 means &quot;more crowded than 80% of the
        past 3 years on this dimension&quot;. The rolling window means the
        baseline updates over time, so secular drift gets handled
        automatically. The percentile transform is robust to outliers
        because it&apos;s rank based, not magnitude based. And it puts all six
        signals on a comparable 0-100 scale that&apos;s actually meaningful when
        you add them.
      </p>
      <p>
        Window length of 3 years is a tradeoff. Shorter (1 year) makes the
        signal more responsive but you get false positives from
        idiosyncratic short-term moves. Longer (5 years) misses regime
        changes. 3 years roughly matches one full quant-strategy life cycle
        (publish, exploit, decay, dead) so it&apos;s the right horizon for
        crowding detection.
      </p>

      <hr className="divider" />

      {/* ───────────── Pipeline placement ───────────── */}
      <h2 className="font-serif mt-12">Where the composite plugs in</h2>
      <p>
        Walking through the actual data flow:
      </p>
      <pre className="font-mono text-xs bg-[#f4f1e9] p-4 my-4 overflow-x-auto leading-tight border border-[var(--rule)]">{`backtest produces  →  rebalance schedule + weights_ts + daily_returns
                       │
                       ▼
   composite_crowding_score(weights_ts, panel, daily_returns, ...)
                       │
                       ▼
              CrowdingScore object
                ├─ timeseries        (rebalance × 6 components)
                ├─ composite          (rebalance × 1)
                ├─ latest             (most recent component snapshot)
                ├─ latest_composite   (0–100 scalar)
                └─ alert_level        ("green" / "amber" / "red")`}</pre>
      <p>
        The CrowdingScore object isn&apos;t just for showing on dashboard. It
        flows into two downstream places. First, the multi-factor allocator,
        which solves:
      </p>
      <Block tex={String.raw`\max_{w_1,\ldots,w_K}\sum_k \alpha_k(w_k\!\cdot\! A)\cdot w_k\!\cdot\! A
\quad\text{s.t.}\quad
\sum_k w_k = 1,\;\; w_k \geq 0,\;\;\text{Crowding}_k \leq s_{\max}`} />
      <p>
        Any factor with crowding score above red threshold gets dropped from
        eligible set. The AUM that was going to that factor gets reallocated
        to the remaining factors. So if momentum is at 80 composite and
        threshold is 75, momentum gets zero weight in the joint allocation
        and the AUM goes to value/quality/low-vol instead.
      </p>
      <p>
        Second place is the stress capacity simulation. When I compute &quot;safe
        AUM in a stressed regime&quot;, I bump the impact coefficient by 1.5x to
        capture the herd-effect implicitly. A crowded factor should run
        smaller than its naive cost model says because in a real unwind your
        realised impact is the herd&apos;s impact, not your own. The 1.5x is a
        rough number, based on the Frazzini-Israel-Moskowitz fills data from
        AQR showing impact during high-volatility regimes is roughly 1.3 to
        1.7 times normal. So I picked 1.5 as the middle.
      </p>
      <p>
        Net effect: a factor that&apos;s flashing red on crowding gets less AUM
        from the allocator, AND any AUM it does get is capped more tightly
        by the stressed capacity number. Two layers of protection working
        together.
      </p>

      <hr className="divider" />

      {/* ───────────── Findings ───────────── */}
      <h2 className="font-serif mt-12">What the synthetic run actually shows</h2>
      <div className="overflow-x-auto my-4">
        <table>
          <thead>
            <tr>
              <th>Factor</th><th className="text-right">Composite</th>
              <th>Alert</th><th>Top drivers</th>
            </tr>
          </thead>
          <tbody>
            <tr><td>momentum</td><td className="text-right">57</td><td><span className="zone-pill zone-amber">amber</span></td>
                <td className="text-[var(--muted)] text-sm">val_spread 81, short_interest 100, holdings_overlap 98</td></tr>
            <tr><td>value</td><td className="text-right">38</td><td><span className="zone-pill zone-green">green</span></td>
                <td className="text-[var(--muted)] text-sm">balanced</td></tr>
            <tr><td>quality</td><td className="text-right">44</td><td><span className="zone-pill zone-green">green</span></td>
                <td className="text-[var(--muted)] text-sm">balanced</td></tr>
            <tr><td>low_vol</td><td className="text-right">48</td><td><span className="zone-pill zone-green">green</span></td>
                <td className="text-[var(--muted)] text-sm">balanced</td></tr>
          </tbody>
        </table>
      </div>
      <p>
        The result that surprised me: momentum lit up amber even on
        synthetic data, with no actual arbitrageurs in the simulation.
        Three of the six components were near the top of their own
        historical distribution. Let me explain each:
      </p>
      <p>
        <strong>Valuation spread of 81.</strong> Recent winners (the long leg
        of momentum) had been bid up such that their average P/B was closer
        to the average P/B of the losers (the short leg). So the spread had
        compressed. On synthetic data this is happening because high-recent-
        return names also tend to be high-realized-vol names, and high-vol
        names in my synthetic generator have somewhat elevated P/B due to
        the correlation I built in between the latent value beta and the
        momentum beta. Real markets show the same pattern for different
        reasons (winners get bid up, losers get marked down) — but the
        synthetic case reproduces it as an artifact, which is honestly fine
        because it shows the signal is doing what it should.
      </p>
      <p>
        <strong>Short interest of 100.</strong> Means SI on momentum&apos;s short
        leg is at the literal top of its 3-year history in the synthetic data.
        Recent losers have high short interest because in the synthetic
        generator I gave bursty short-interest behaviour to high-vol names,
        and recent losers are often high-vol. Real momentum shorts also
        accumulate high SI for similar reasons (everyone is short the recent
        losers) so the signal is at least directionally right.
      </p>
      <p>
        <strong>Holdings overlap of 98.</strong> Momentum&apos;s long-leg names
        overlap significantly with quality and low-vol&apos;s long-leg names.
        That makes sense in the synthetic data because of how the latent
        betas are constructed — high-quality names also tend to have decent
        momentum, and low-vol names with positive drift end up in momentum&apos;s
        long. Real markets show this empirically too. Quality and momentum
        are well known to overlap in expansion phases.
      </p>
      <p>
        So even with no real-world crowding mechanism (no arbitrageurs in
        the synthetic data, no flows, no actual fund overlap), the composite
        score is correctly flagging that momentum is the most structurally
        fragile factor in this sleeve. Value, quality, low-vol all came in
        green with balanced components. That&apos;s the signature the tool was
        supposed to surface, so it&apos;s working as designed.
      </p>

      <hr className="divider" />

      {/* ───────────── Takeaways ───────────── */}
      <h2 className="font-serif mt-12">Takeaways</h2>
      <p className="mt-4">
        First takeaway, the most important one: different signals catch
        different failure modes, and each one has blind spots that the
        others fill in. Valuation spread catches the case where the trade
        is already priced in. Comomentum catches the case where the same
        hands are pushing the same names. Short interest catches the borrow
        market knowing what you don&apos;t. Alpha decay catches the empirical
        fact of IR slowly dying. None of them is sufficient on its own,
        which is exactly why a composite is the right structure. If I had
        to keep only one signal, I&apos;d keep comomentum, because it&apos;s the
        hardest to fake. But ideally you want all of them.
      </p>
      <p>
        Rolling percentile is the only honest aggregation method I could
        find. Raw averaging across signals in different units doesn&apos;t mean
        anything. Z-scoring assumes Gaussian distributions which most of
        these signals don&apos;t have. Min-max scaling is fragile to outliers.
        Rolling-percentile-rank gets you robust, regime-aware, comparable
        scores without making distributional assumptions you can&apos;t verify.
      </p>
      <p>
        Crowding tightens capacity, not just IR. This is the connection
        back to the rest of the tool. A crowded factor has lower real
        capacity than its naive cost model would suggest, because in a
        coordinated unwind your impact isn&apos;t yours alone — it&apos;s the herd&apos;s.
        The allocator uses the crowding score as a hard constraint, and the
        stress capacity simulation amplifies impact by 1.5x. Both are
        rough but they capture the structural effect.
      </p>
      <p>
        Two of my six signals are still proxies and need real data feeds in
        production. Holdings overlap really wants 13F data (US) or
        shareholding patterns (India). Short interest really wants a broker
        SLB feed at higher resolution than my current snapshot data. The
        architecture is set up so these drop in cleanly without breaking
        anything else, but the demo as it stands is using simplified
        proxies. Not ideal but it&apos;s honest about what it&apos;s doing.
      </p>
      <p>
        The biggest lesson from building this was the internal-vs-external
        split. The old prototype I started from was measuring only
        self-crowding — only how much of the daily volume I was eating up
        myself. That number is real and important, but it&apos;s only one out of
        the six ways a factor gets crowded. The other five are about
        external pressure: are other funds positioned same as me? Is the
        borrow market squeezing? Is the alpha already in the price? The new
        composite puts 15% of the weight on internal and 85% on external.
        That ratio is the single most important design choice in the entire
        module, more important than any individual signal&apos;s formula.
      </p>

      <hr className="divider" />

      {/* ───────────── Known problems ───────────── */}
      <h2 className="font-serif mt-12">Known problems with this approach</h2>
      <p className="mt-4">
        Being honest about the four biggest weaknesses. These would all come up in
        a real diligence conversation and the tool doesn&apos;t hide from them.
      </p>

      <h3 className="font-serif mt-8">1 · Synthetic data is the foundation of every reference number</h3>
      <p>
        Every headline number on the reference run, including the &quot;momentum lit up
        amber at 57&quot; result, is computed on a NIFTY-100 panel I generated myself.
        The composite scores are a function of my generator&apos;s latent betas. I
        haven&apos;t run this on a single real crowding episode — no 2007 quant
        quake, no 2018 vol blowup, no March 2020. Until I do that backtest, a PM
        has no way to verify whether the tool would have warned them in advance
        of any actual factor crash. This is the single biggest weakness.
      </p>

      <h3 className="font-serif mt-8">2 · The six signals are correlated, weights are arbitrary</h3>
      <p>
        Comomentum and holdings overlap measure essentially the same thing
        (overlapping baskets produce correlated returns). Valuation spread and
        alpha decay both pick up the &quot;factor matured&quot; story. So the
        composite is double-counting. There&apos;s no orthogonalisation step (PCA,
        residualisation) to extract the independent information. And the weights
        themselves (0.20/0.20/0.15×4) are picked by narrative argument, not fit
        to data. The right way is to fit them to predictive power for forward
        drawdowns in a held-out sample. Same story for the 75/50 thresholds, no
        statistical basis.
      </p>

      <h3 className="font-serif mt-8">3 · Two of the six signals are proxies, not the real thing</h3>
      <p>
        Holdings overlap is supposed to use 13F filings (US) or NSE shareholding
        patterns (India). I&apos;m using &quot;overlap within my own sleeve&quot; because I
        don&apos;t have a live feed. That measures something different. Short
        interest is supposed to come from a broker SLB feed at name-level
        granularity; I&apos;m using snapshot SI from the data panel. Both signals
        are weaker than the academic versions they claim to implement. The
        architecture is set up to drop in real feeds without touching anything
        downstream, but until that happens, two-thirds of the &quot;external&quot;
        weight in the composite is sitting on shaky ground.
      </p>

      <h3 className="font-serif mt-8">4 · The cost and capacity models are too parametric</h3>
      <p>
        Almgren-Chriss square-root impact is textbook but real impact is
        path-dependent, time-of-day dependent, has adverse-selection components
        I&apos;m not modelling. The 0.10-0.30 coefficient range is a guess. I
        assume linear scaling of trade dollars with AUM, but at large AUM the
        portfolio construction itself changes — you can&apos;t hold the same 20
        names, you have to spread thinner. The 1.5× stress multiplier on impact
        is a single number hiding huge heterogeneity. Realised crash-impact in
        2020 was 3-5× normal for crowded factors, not 1.5×. So the stress
        capacity number is optimistic, possibly by a wide margin.
      </p>

      <p className="mt-6">
        If I had to rank the top three things to fix before someone runs this on
        a real strategy: backtest the composite against at least one real
        crowding episode, orthogonalise the six signals or fit the weights to
        data, and drop in real 13F / NSE shareholding-pattern feeds so two of
        the signals stop being proxies.
      </p>

      <hr className="divider" />

      {/* ───────────── References ───────────── */}
      <h2 className="font-serif mt-12">References</h2>
      <ol className="list-decimal pl-6 text-sm space-y-1">
        <li>
          Cahan R., Luo Y. (2013). &quot;Crowding and quant equity&quot;. Deutsche
          Bank Quant Research. <span className="text-[var(--muted)]">— composite design template.</span>
        </li>
        <li>
          Lou D., Polk C. (2013). &quot;Comomentum: Inferring arbitrage activity
          from return correlations&quot;. LSE working paper.{" "}
          <span className="text-[var(--muted)]">— signal 4 (comomentum).</span>
        </li>
        <li>
          Drechsler I., Drechsler Q. (2014). &quot;The shorting premium and asset
          pricing anomalies&quot;.{" "}
          <span className="text-[var(--muted)]">— signal 3 (short interest pressure).</span>
        </li>
        <li>
          Sias R., Turtle H., Zykaj B. (2016). &quot;Hedge-fund crowds and
          mispricing&quot;. <em>Management Science</em>.{" "}
          <span className="text-[var(--muted)]">— signal 5 (holdings overlap).</span>
        </li>
        <li>
          Arnott R., Hsu J., West J. (2017). &quot;How can &lsquo;smart beta&rsquo;
          go horribly wrong?&quot;. Research Affiliates.{" "}
          <span className="text-[var(--muted)]">— signal 2 (alpha decay framing).</span>
        </li>
        <li>
          Asness C., Friedman J., Israel R. (2017). &quot;Style timing: Value
          versus growth&quot;. <em>J. Portfolio Management</em>.{" "}
          <span className="text-[var(--muted)]">— signal 1 (valuation spread).</span>
        </li>
        <li>
          Stein J. (2009). &quot;Sophisticated investors and market efficiency&quot;.{" "}
          <em>J. Finance</em> 64(4).{" "}
          <span className="text-[var(--muted)]">— theoretical framing of herding mechanism.</span>
        </li>
        <li>
          Pedersen L. H. (2015). <em>Efficiently Inefficient</em>, Princeton
          UP, ch. 5.{" "}
          <span className="text-[var(--muted)]">— general framework on crowding and capacity.</span>
        </li>
        <li>
          Lou D., Polk C., Skouras S. (2019). &quot;A tug of war: Overnight versus
          intraday expected returns&quot;. <em>J. Financial Economics</em>.{" "}
          <span className="text-[var(--muted)]">— motivates overnight vs intraday split, future signal 7.</span>
        </li>
        <li>
          Frazzini A., Israel R., Moskowitz T. (2018). &quot;Trading costs&quot;. AQR
          working paper.{" "}
          <span className="text-[var(--muted)]">— calibrates the 1.5x impact bump for stressed regimes.</span>
        </li>
      </ol>

      <hr className="divider" />

      <p className="text-[var(--muted)] text-sm">
        The composite crowding score is shown live on the{" "}
        <a href="/reference">reference run</a>, which uses the synthetic
        NIFTY-100 panel. The user-uploaded CSV on{" "}
        <a href="/analyze">/analyze</a> doesn&apos;t carry cross-sectional data
        so crowding isn&apos;t computed for uploads, but the capacity engine and
        operating-policy search both consume the composite as a sizing
        constraint when it is available.
      </p>
    </article>
  );
}
