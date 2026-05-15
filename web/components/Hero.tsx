export function Hero() {
  return (
    <section className="border-b border-rule bg-cream">
      <div className="max-w-6xl mx-auto px-6 py-16">
        <div className="kicker mb-4">Buy-side research tool</div>
        <h1 className="font-serif text-5xl md:text-6xl leading-[1.05] text-ink max-w-3xl">
          How much money can a factor strategy run before it stops paying for itself?
        </h1>
        <p className="lede mt-6 text-lg max-w-prose">
          A live monitor that estimates safe AUM, scores how crowded a trade has
          become against six external signals, recommends the rebalance rule
          that maximises net Information Ratio, and projects forward Sharpe with
          a small ML layer.
        </p>
        <div className="mt-8 flex flex-wrap gap-3 text-sm">
          <a href="#why" className="card hover:border-accent transition-colors">Why it matters →</a>
          <a href="#how" className="card hover:border-accent transition-colors">How it works →</a>
          <a href="#factors" className="card hover:border-accent transition-colors">Factor deep dive →</a>
          <a href="/methodology" className="card hover:border-accent transition-colors">Mathematics →</a>
        </div>
      </div>
    </section>
  );
}
