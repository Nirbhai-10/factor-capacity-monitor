import type { AnalysisResult } from "./types";

export function downloadFile(filename: string, text: string, mime = "text/plain") {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function curveToCsv(r: AnalysisResult): string {
  const header = [
    "aum", "net_ir", "gross_ir", "total_cost_bps",
    "spread_bps", "impact_bps", "commission_bps", "borrow_bps", "tax_bps",
    "participation", "zone",
  ].join(",");
  const rows = r.curve.map((p) =>
    [
      p.aum, p.netIR.toFixed(4), p.grossIR.toFixed(4), p.totalCostBps.toFixed(2),
      p.spreadBps.toFixed(2), p.impactBps.toFixed(2), p.commissionBps.toFixed(2),
      p.borrowBps.toFixed(2), p.taxBps.toFixed(2),
      p.participation.toFixed(4), p.zone,
    ].join(",")
  );
  return [header, ...rows].join("\n");
}

export function memoMarkdown(r: AnalysisResult): string {
  const fmtCr = (v: number | null | undefined) =>
    v == null ? "—" : `${(v / 1e7).toLocaleString("en-IN", { maximumFractionDigits: 1 })} cr`;
  const lines: string[] = [];
  lines.push(`# ${r.strategy.name} — capacity & policy memo\n`);
  lines.push(`Computed at ${r.computedAt}.\n`);
  lines.push(`## Summary\n`);
  lines.push(`- **Sample**: ${r.strategy.meta.startDate} → ${r.strategy.meta.endDate} (${r.strategy.meta.rows} rows)`);
  lines.push(`- **Sharpe (gross)**: ${r.stats.sharpe.toFixed(2)}`);
  lines.push(`- **Annual return / vol**: ${(r.stats.annualReturn*100).toFixed(2)}% / ${(r.stats.annualVol*100).toFixed(2)}%`);
  lines.push(`- **Max drawdown**: ${(r.stats.maxDrawdown*100).toFixed(2)}%`);
  lines.push(`- **Win rate**: ${(r.stats.winRate*100).toFixed(1)}%`);
  lines.push(`- **Safe capacity**: ${fmtCr(r.safeCapacity)}`);
  lines.push(`- **IR≥0.5 capacity**: ${fmtCr(r.ir50Capacity)}`);
  lines.push(`- **Optimal policy**: rebalance ${r.policy.bestFreq}, no-trade buffer ${r.policy.bestBufferBps} bps → net IR ${r.policy.bestNetIR.toFixed(2)}`);
  lines.push(`- **Regime**: ${r.regime.label} (60d ann. vol ${(r.regime.annVol*100).toFixed(1)}%, AR(1) ${r.regime.autocorr.toFixed(2)})\n`);

  lines.push(`## Cost parameters used\n`);
  for (const [k, v] of Object.entries(r.costParams)) {
    lines.push(`- **${k}**: ${v}`);
  }
  lines.push("");

  lines.push(`## Capacity curve\n`);
  lines.push(`| AUM (cr) | gross IR | net IR | total cost (bps) | participation | zone |`);
  lines.push(`|----------:|---------:|-------:|-----------------:|--------------:|:-----|`);
  for (const p of r.curve) {
    lines.push(
      `| ${(p.aum/1e7).toFixed(1)} | ${p.grossIR.toFixed(2)} | ${p.netIR.toFixed(2)} | ${p.totalCostBps.toFixed(0)} | ${(p.participation*100).toFixed(1)}% | ${p.zone} |`
    );
  }
  lines.push("");

  if (r.forecast.series.length > 0) {
    lines.push(`## Forward Sharpe forecast\n`);
    lines.push(`OU mean reversion fit on rolling-1y Sharpe.`);
    lines.push(`- Half-life: ${r.forecast.halfLifeDays.toFixed(0)} days`);
    lines.push(`- Attractor: ${r.forecast.fittedAlpha.toFixed(2)}`);
    lines.push(`- Mean-reversion speed κ: ${r.forecast.kappa.toFixed(4)}\n`);
  }

  lines.push(`## Policy grid\n`);
  lines.push(`| freq | buffer (bps) | turnover | net IR | cost (bps) |`);
  lines.push(`|:-----|------------:|---------:|-------:|----------:|`);
  for (const row of r.policy.grid) {
    const best = row.freq === r.policy.bestFreq && row.bufferBps === r.policy.bestBufferBps;
    lines.push(
      `| ${best ? "**" + row.freq + "**" : row.freq} | ${row.bufferBps} | ${row.turnover.toFixed(2)}× | ${row.netIR.toFixed(2)} | ${row.totalCostBps.toFixed(0)} |`
    );
  }
  lines.push("");
  return lines.join("\n");
}
