"use client";
import {
  ComposedChart, Line, Area, Scatter, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine, Legend,
} from "recharts";
import type { AnalysisResult } from "@/lib/engine/types";
import { fmtCr, fmtIR, fmtPct } from "@/lib/format";
import { ZonePill } from "@/components/ZonePill";

const COST_FIELDS = [
  { key: "spreadBps",     label: "spread",     color: "#1a3a5c" },
  { key: "impactBps",     label: "impact",     color: "#a08c5d" },
  { key: "commissionBps", label: "commission", color: "#7a5a3a" },
  { key: "borrowBps",     label: "borrow",     color: "#5a4f7a" },
  { key: "taxBps",        label: "India tax",  color: "#2d6a45" },
];

const ZONE_COLOR = { safe: "#2d6a45", caution: "#8a5a1f", red: "#862f2f" } as const;

export function StrategyResults({ r }: { r: AnalysisResult }) {
  return (
    <>
      {/* Strategy header */}
      <div className="flex flex-wrap items-baseline gap-3 mb-6">
        <h2 className="font-serif text-3xl">{r.strategy.name}</h2>
        <span className="text-sm text-[var(--muted)] tabular">
          {r.strategy.meta.startDate} → {r.strategy.meta.endDate} &middot; {r.strategy.meta.rows} rows
        </span>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[var(--rule)] border border-[var(--rule)] mb-12">
        <Kpi label="Sharpe" value={fmtIR(r.stats.sharpe)} />
        <Kpi label="Annual return" value={fmtPct(r.stats.annualReturn)} />
        <Kpi label="Annual vol" value={fmtPct(r.stats.annualVol)} />
        <Kpi label="Max drawdown" value={fmtPct(r.stats.maxDrawdown)} />
        <Kpi label="Safe AUM"
              value={fmtCr(r.safeCapacity)}
              hint={r.safeCapacity == null ? "Net IR never crosses zone constraints" : "Net IR ≥ 0.5 + zone limits"} />
        <Kpi label="IR ≥ 0.5 AUM"
              value={fmtCr(r.ir50Capacity)}
              hint="interpolated soft cap" />
        <Kpi label="Best policy"
              value={`${r.policy.bestFreq} / ${r.policy.bestBufferBps}bps`}
              hint={`net IR ${r.policy.bestNetIR.toFixed(2)}`} />
        <Kpi label="Regime"
              value={<ZonePill zone={r.regime.label} />}
              hint={`${(r.regime.annVol * 100).toFixed(0)}% vol · AR(1) ${r.regime.autocorr.toFixed(2)}`} />
      </div>

      {/* Capacity curve */}
      <h3 className="font-serif text-2xl mt-12 mb-2">Capacity curve</h3>
      <p className="text-[var(--muted)] mb-4 max-w-prose text-sm">
        Net Information Ratio after spread, Almgren-Chriss impact, commission,
        borrow and (optionally) the India tax stack, plotted across the AUM grid.
        Coloured dots are zone classifications.
      </p>
      <CapacityChart curve={r.curve} />

      {/* Cost stack */}
      <h3 className="font-serif text-2xl mt-12 mb-2">Cost decomposition</h3>
      <p className="text-[var(--muted)] mb-4 max-w-prose text-sm">
        Stacked annualised cost in basis points. Spread, commission and tax stack
        scale ~linearly with turnover. Impact bends — square-root in participation.
      </p>
      <CostStack curve={r.curve} />

      {/* Forward forecast */}
      {r.forecast.series.length > 0 && (
        <>
          <h3 className="font-serif text-2xl mt-12 mb-2">Forward Sharpe — OU forecast</h3>
          <p className="text-[var(--muted)] mb-4 max-w-prose text-sm">
            Six-month projection from a mean-reverting state-space model fit on
            rolling 1-year Sharpe.
            Half-life <span className="tabular">{r.forecast.halfLifeDays.toFixed(0)}d</span>,
            attractor <span className="tabular">{r.forecast.fittedAlpha.toFixed(2)}</span>,
            in-sample RMSE <span className="tabular">{r.forecast.series[0]
              ? Math.abs(r.forecast.series[0].upper - r.forecast.series[0].lower).toFixed(3) : "—"}</span>.
          </p>
          <ForecastChart series={r.forecast.series} />
        </>
      )}

      {/* Policy table */}
      <h3 className="font-serif text-2xl mt-12 mb-2">Operating policy search</h3>
      <p className="text-[var(--muted)] mb-4 max-w-prose text-sm">
        Net IR at the safe-AUM target across rebalance frequency × no-trade buffer.
        The optimal row is highlighted.
      </p>
      <div className="overflow-x-auto">
        <table>
          <thead>
            <tr>
              <th>freq</th>
              <th className="text-right">buffer (bps)</th>
              <th className="text-right">turnover</th>
              <th className="text-right">net IR</th>
              <th className="text-right">cost (bps)</th>
            </tr>
          </thead>
          <tbody>
            {r.policy.grid.map((row, i) => {
              const best = row.freq === r.policy.bestFreq && row.bufferBps === r.policy.bestBufferBps;
              return (
                <tr key={i} className={best ? "highlight" : ""}>
                  <td>{row.freq}</td>
                  <td className="text-right">{row.bufferBps}</td>
                  <td className="text-right">{row.turnover.toFixed(2)}×</td>
                  <td className="text-right">{row.netIR.toFixed(2)}</td>
                  <td className="text-right">{row.totalCostBps.toFixed(0)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}

function Kpi({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="bg-[var(--bg)] p-4">
      <div className="kicker mb-1">{label}</div>
      <div className="font-serif text-2xl text-ink leading-tight">{value}</div>
      {hint && <div className="text-[0.72rem] text-[var(--muted)] mt-1">{hint}</div>}
    </div>
  );
}

function CapacityChart({ curve }: { curve: AnalysisResult["curve"] }) {
  const data = curve.map((p) => ({
    aum: p.aum,
    netIR: p.netIR,
    grossIR: p.grossIR,
    zone: p.zone,
  }));
  return (
    <ResponsiveContainer width="100%" height={420}>
      <ComposedChart data={data} margin={{ top: 24, right: 28, left: 12, bottom: 36 }}>
        <CartesianGrid stroke="#ebe8de" strokeDasharray="2 4" vertical={false} />
        <XAxis dataKey="aum" type="number" scale="log" domain={["auto", "auto"]}
                tickFormatter={(v) => {
                  const cr = v / 1e7;
                  if (cr >= 1000) return `${(cr/1000).toFixed(0)}k`;
                  if (cr >= 1) return `${cr.toFixed(0)}`;
                  return cr.toFixed(1);
                }}
                label={{ value: "AUM (₹ cr, log)", position: "insideBottom", offset: -16,
                          style: { fill: "#6b6b6b" } }}
        />
        <YAxis tickFormatter={(v) => v.toFixed(2)}
                label={{ value: "Information Ratio", angle: -90, position: "insideLeft",
                          style: { fill: "#6b6b6b" } }} />
        <Tooltip labelFormatter={(v) => `AUM: ${(Number(v)/1e7).toLocaleString('en-IN',{maximumFractionDigits:1})} cr`}
                  formatter={(v: number, name: string) => [v?.toFixed?.(2), name]} />
        <ReferenceLine y={0.5} stroke="#6b6b6b" strokeDasharray="3 3"
                        label={{ value: "IR = 0.5", position: "right", fill: "#6b6b6b", fontSize: 11 }} />
        <Line type="monotone" dataKey="grossIR" stroke="#a08c5d" strokeDasharray="3 3"
              dot={false} name="Gross IR" />
        <Line type="monotone" dataKey="netIR" stroke="#1a3a5c" strokeWidth={2}
              dot={false} name="Net IR" />
        <Scatter dataKey="netIR" name="zone"
                 shape={(p: any) => {
                   const { cx, cy, payload } = p;
                   if (cx == null || cy == null) return <g />;
                   return <circle cx={cx} cy={cy} r={4.5}
                                   fill={ZONE_COLOR[payload.zone as keyof typeof ZONE_COLOR]}
                                   stroke="#fbfaf6" strokeWidth={1} />;
                 }} />
        <Legend verticalAlign="top" height={28}
                 wrapperStyle={{ fontSize: 12 }} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

function CostStack({ curve }: { curve: AnalysisResult["curve"] }) {
  const data = curve.map((p) => {
    const cr = p.aum / 1e7;
    const lbl = cr >= 1 ? `${cr.toFixed(0)}` : `${cr.toFixed(1)}`;
    return {
      aumLabel: lbl,
      ...Object.fromEntries(COST_FIELDS.map((f) => [f.key, (p as any)[f.key]])),
    } as any;
  });
  return (
    <ResponsiveContainer width="100%" height={340}>
      <BarChart data={data} margin={{ top: 16, right: 24, left: 12, bottom: 24 }}>
        <CartesianGrid stroke="#ebe8de" strokeDasharray="2 4" vertical={false} />
        <XAxis dataKey="aumLabel"
                label={{ value: "AUM (₹ cr)", position: "insideBottom", offset: -10,
                          style: { fill: "#6b6b6b" } }} />
        <YAxis label={{ value: "Annualised cost (bps)", angle: -90, position: "insideLeft",
                         style: { fill: "#6b6b6b" } }} />
        <Tooltip />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {COST_FIELDS.map((c) => (
          <Bar key={c.key} dataKey={c.key} stackId="a" fill={c.color} name={c.label} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

function ForecastChart({ series }: { series: AnalysisResult["forecast"]["series"] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={series} margin={{ top: 16, right: 24, left: 12, bottom: 24 }}>
        <CartesianGrid stroke="#ebe8de" strokeDasharray="2 4" vertical={false} />
        <XAxis dataKey="date" tickFormatter={(d) => String(d).slice(0, 7)}
                interval="preserveStartEnd" />
        <YAxis label={{ value: "Sharpe", angle: -90, position: "insideLeft",
                         style: { fill: "#6b6b6b" } }} />
        <Tooltip />
        <ReferenceLine y={0.5} stroke="#6b6b6b" strokeDasharray="3 3" />
        <Area type="monotone" dataKey="upper" stroke="none" fill="#1a3a5c" fillOpacity={0.08} />
        <Area type="monotone" dataKey="lower" stroke="none" fill="#fbfaf6" fillOpacity={1} />
        <Line type="monotone" dataKey="sharpe" stroke="#1a3a5c" strokeWidth={2} dot={false} name="forecast" />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
