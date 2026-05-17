"use client";
import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend,
} from "recharts";
import type { SeriesPoint } from "@/lib/types";

export function AlphaForecast({
  history, forecast, fanLower, fanUpper,
}: {
  history: SeriesPoint[];
  forecast: SeriesPoint[];
  fanLower: SeriesPoint[];
  fanUpper: SeriesPoint[];
}) {
  // Combine: history is cumulative log returns? No, it's cumulative.
  // For visual purposes show forecast band against forecast line.
  const merge = forecast.map((p, i) => ({
    date: p.date,
    forecast: p.value,
    lower: fanLower[i]?.value ?? null,
    upper: fanUpper[i]?.value ?? null,
    band: (fanUpper[i]?.value != null && fanLower[i]?.value != null)
      ? (fanUpper[i].value as number) - (fanLower[i].value as number) : 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart data={merge} margin={{ top: 16, right: 24, left: 12, bottom: 24 }}>
        <CartesianGrid stroke="#e6e3da" strokeDasharray="3 3" />
        <XAxis dataKey="date" tickFormatter={(d) => String(d).slice(0, 7)} />
        <YAxis label={{ value: "Forecast Sharpe", angle: -90, position: "insideLeft",
                         style: { fill: "#5a5a5a", fontFamily: "'Source Serif 4', serif" } }} />
        <Tooltip contentStyle={{ background: "#fbfaf6", border: "1px solid #e6e3da",
                                    fontFamily: "'Source Serif 4', serif" }} />
        <ReferenceLine y={0.5} stroke="#5a5a5a" strokeDasharray="4 4" />
        <Area type="monotone" dataKey="upper" stroke="none" fill="#1a3a5c" fillOpacity={0.08} />
        <Area type="monotone" dataKey="lower" stroke="none" fill="#fbfaf6" fillOpacity={1} />
        <Line type="monotone" dataKey="forecast" stroke="#1a3a5c" strokeWidth={2} dot={false} name="forecast" />
        <Legend wrapperStyle={{ fontFamily: "'Source Serif 4', serif", fontSize: 12 }} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
