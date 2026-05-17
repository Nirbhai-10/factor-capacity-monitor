"use client";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine,
} from "recharts";
import type { CrowdComponent, SeriesPoint } from "@/lib/types";

const COMP = [
  { key: "valuation_spread",  color: "#1a3a5c" },
  { key: "alpha_decay",       color: "#a08c5d" },
  { key: "short_interest",    color: "#a04040" },
  { key: "comomentum",        color: "#5a4f7a" },
  { key: "holdings_overlap",  color: "#2d7a4f" },
  { key: "internal_footprint", color: "#7a5a3a" },
];

export function CrowdingChart({
  components, composite,
}: { components: CrowdComponent[]; composite: SeriesPoint[] }) {
  const compMap = new Map(composite.map((p) => [p.date, p.value]));
  const data = components.map((row) => ({ ...row, composite: compMap.get(row.date) ?? null }));

  return (
    <ResponsiveContainer width="100%" height={360}>
      <LineChart data={data} margin={{ top: 16, right: 24, left: 12, bottom: 24 }}>
        <CartesianGrid stroke="#e6e3da" strokeDasharray="3 3" />
        <XAxis dataKey="date" tickFormatter={(d) => String(d).slice(0, 7)}
                interval="preserveStartEnd" />
        <YAxis domain={[0, 100]}
                label={{ value: "Score (0–100)", angle: -90, position: "insideLeft",
                         style: { fill: "#5a5a5a", fontFamily: "'Source Serif 4', serif" } }} />
        <Tooltip contentStyle={{ background: "#fbfaf6", border: "1px solid #e6e3da",
                                    fontFamily: "'Source Serif 4', serif" }} />
        <Legend wrapperStyle={{ fontFamily: "'Source Serif 4', serif", fontSize: 12 }} />
        <ReferenceLine y={75} stroke="#a04040" strokeDasharray="4 4" />
        <ReferenceLine y={50} stroke="#b07c2c" strokeDasharray="4 4" />
        {COMP.map((c) => (
          <Line key={c.key} type="monotone" dataKey={c.key} stroke={c.color}
                 strokeWidth={1} dot={false} strokeOpacity={0.5} name={c.key} />
        ))}
        <Line type="monotone" dataKey="composite" stroke="#1a1a1a"
               strokeWidth={2.5} dot={false} name="composite" />
      </LineChart>
    </ResponsiveContainer>
  );
}
