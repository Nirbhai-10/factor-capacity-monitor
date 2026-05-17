"use client";
import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, ReferenceArea, Legend,
} from "recharts";
import type { ReturnPoint } from "@/lib/engine/types";
import { rollingSharpe } from "@/lib/engine/stats";

/**
 * Rolling 1-year Sharpe + 6-month forecast on a single timeline.
 *
 * The vertical separator marks "today" — left of it is realised history,
 * right is the OU mean-reversion projection with a ±1σ fan.
 */
export function RollingSharpe({
  returns,
  forecast,
}: {
  returns: ReturnPoint[];
  forecast: { date: string; sharpe: number; lower: number; upper: number }[];
}) {
  const history = rollingSharpe(returns, 252)
    .filter((p) => p.value != null)
    .map((p) => ({ date: p.date, history: p.value }));

  const cutoffDate = history.length > 0 ? history[history.length - 1].date : "";

  const forecastRows = forecast.map((p) => ({
    date: p.date,
    forecast: p.sharpe,
    lower: p.lower,
    upper: p.upper,
  }));

  // Concatenate history + forecast on a single date axis
  const data = [...history, ...forecastRows];

  if (data.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height={340}>
      <ComposedChart data={data} margin={{ top: 16, right: 24, left: 12, bottom: 24 }}>
        <CartesianGrid stroke="#ebe8de" strokeDasharray="2 4" vertical={false} />
        <XAxis dataKey="date" tickFormatter={(d) => String(d).slice(0, 7)}
                interval="preserveStartEnd" />
        <YAxis tickFormatter={(v) => v.toFixed(1)}
                label={{ value: "Sharpe (annualised)", angle: -90, position: "insideLeft",
                          style: { fill: "#6b6b6b" } }} />
        <Tooltip />
        <ReferenceLine y={0.5} stroke="#6b6b6b" strokeDasharray="3 3" />
        {cutoffDate && (
          <ReferenceLine x={cutoffDate} stroke="#a08c5d" strokeDasharray="2 2"
                          label={{ value: "today", position: "top", fill: "#a08c5d", fontSize: 11 }} />
        )}
        <Area type="monotone" dataKey="upper" stroke="none" fill="#1a3a5c" fillOpacity={0.08} />
        <Area type="monotone" dataKey="lower" stroke="none" fill="#fbfaf6" fillOpacity={1} />
        <Line type="monotone" dataKey="history" stroke="#1a1a1a" strokeWidth={2} dot={false}
              name="rolling 1y Sharpe" connectNulls={false} />
        <Line type="monotone" dataKey="forecast" stroke="#1a3a5c" strokeWidth={2}
              strokeDasharray="4 3" dot={false} name="OU forecast" connectNulls={false} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
