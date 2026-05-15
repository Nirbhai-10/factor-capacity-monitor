import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FactorCapacity-Nirbhai · Capacity & Crowding Monitor",
  description:
    "Buy-side research tool that estimates safe AUM, scores how crowded a factor strategy "
    + "has become, forecasts forward Sharpe, and recommends an operating policy.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Header />
        <main>{children}</main>
        <Footer />
      </body>
    </html>
  );
}

function Header() {
  return (
    <header>
      <div className="max-w-6xl mx-auto px-6 py-5 flex items-baseline justify-between">
        <a href="/" className="font-serif text-lg no-underline">
          FactorCapacity<span className="text-[#a08c5d]">-</span>Nirbhai
        </a>
        <nav className="flex gap-6 text-sm text-[var(--muted)]">
          <a href="/" className="no-underline hover:text-ink">Overview</a>
          <a href="/analyze" className="no-underline hover:text-ink">Analyze</a>
          <a href="/reference" className="no-underline hover:text-ink">Reference</a>
          <a href="/crowding" className="no-underline hover:text-ink">Crowding notes</a>
          <a href="/methodology" className="no-underline hover:text-ink">Methods</a>
        </nav>
      </div>
      <hr className="border-t border-[var(--rule)] mb-0" />
    </header>
  );
}

function Footer() {
  return (
    <footer className="mt-32 border-t border-[var(--rule)]">
      <div className="max-w-6xl mx-auto px-6 py-10 text-sm text-[var(--muted)] flex flex-col md:flex-row justify-between gap-4">
        <div>
          <div className="font-serif text-base text-ink">FactorCapacity-Nirbhai</div>
          <div className="mt-1">v0.5 &middot; research prototype, not investment advice</div>
        </div>
        <div className="md:text-right">
          <div>Almgren-Chriss impact &middot; Corwin-Schultz spread</div>
          <div>Six-component composite crowding score</div>
        </div>
      </div>
    </footer>
  );
}
