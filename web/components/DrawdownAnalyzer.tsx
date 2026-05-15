"use client";
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceArea,
} from "recharts";
import type { ReturnPoint } from "@/lib/engine/types";
import type { Drawdown } from "@/lib/engine/stats";

/**
 * Underwater curve + top-N drawdown table.
 *
 *   underwater(t) = equity(t) / running_max(equity)(t) − 1   ∈ [-∞, 0]
 *
 * The headline statistic is the deepest drawdown (also returned by
 * `maxDrawdown`); the table adds duration + recovery time so a PM can see
 * how the strategy behaved in stress.
 */
export function DrawdownAnalyzer({
  returns, drawdowns,
}: { returns: ReturnPoint[]; drawdowns: Drawdown[] }) {
  // Build underwater curve
  const data: { date: string; underwater: number }[] = [];
  let cum = 1;
  let peak = 1;
  for (const r of returns) {
    cum *= 1 + r.ret;
    if (cum > peak) peak = cum;
    data.push({ date: r.date, underwater: cum / peak - 1 });
  }

  return (
    <div className="grid lg:grid-cols-2 gap-8 items-start">
      <div>
        <ResponsiveContainer width="100%" height={280}>
          <ComposedChart data={data} margin={{ top: 16, right: 16, left: 12, bottom: 24 }}>
            <CartesianGrid stroke="#ebe8de" strokeDasharray="2 4" vertical={false} />
            <XAxis dataKey="date" tickFormatter={(d) => String(d).slice(0, 7)}
                    interval="preserveStartEnd" />
            <YAxis tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                    domain={[(min: number) => Math.floor(min * 10) / 10, 0]} />
            <Tooltip formatter={(v: number) => `${(v * 100).toFixed(2)}%`} />
            {drawdowns.map((dd, i) => (
              <ReferenceArea key={i}
                              x1={dd.startDate}
                              x2={dd.endDate ?? dd.troughDate}
                              fill="#862f2f" fillOpacity={0.08} />
            ))}
            <Area type="monotone" dataKey="underwater" stroke="#862f2f" strokeWidth={1.5}
                  fill="#862f2f" fillOpacity={0.20} name="underwater" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div>
        <table>
          <thead>
            <tr>
              <th className="text-right">#</th>
              <th>peak</th>
              <th>trough</th>
              <th>recovery</th>
              <th className="text-right">depth</th>
              <th className="text-right">length</th>
              <th className="text-right">recover</th>
            </tr>
          </thead>
          <tbody>
            {drawdowns.length === 0 && (
              <tr><td colSpan={7} className="text-center text-[var(--muted)]">no drawdowns</td></tr>
            )}
            {drawdowns.map((dd, i) => (
              <tr key={i}>
                <td className="text-right">{i + 1}</td>
                <td>{dd.startDate}</td>
                <td>{dd.troughDate}</td>
                <td>{dd.endDate ?? "—"}</td>
                <td className="text-right">{(dd.depth * 100).toFixed(2)}%</td>
                <td className="text-right">{dd.lengthDays}d</td>
                <td className="text-right">{dd.recoveryDays != null ? `${dd.recoveryDays}d` : "ongoing"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="text-[var(--muted)] mt-2 text-xs">
          Length = peak → trough in trading days. Recovery = trough → next new high.
        </p>
      </div>
    </div>
  );
}
