export function SectionHeader({ kicker, title, lede }: {
  kicker?: string;
  title: string;
  lede?: string;
}) {
  return (
    <header className="mb-6">
      {kicker && <div className="kicker mb-2">{kicker}</div>}
      <h2 className="font-serif text-3xl md:text-4xl text-ink mb-2">{title}</h2>
      {lede && <p className="lede mt-3">{lede}</p>}
    </header>
  );
}
