"use client";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from "recharts";
import type { CurvePoint } from "@/lib/types";

const COMPONENTS = [
  { key: "spread_bps",     label: "spread",      color: "#1a3a5c" },
  { key: "impact_bps",     label: "impact",      color: "#a08c5d" },
  { key: "commission_bps", label: "commission",  color: "#7a5a3a" },
  { key: "borrow_bps",     label: "borrow",      color: "#5a4f7a" },
  { key: "india_bps",      label: "India tax",   color: "#2d7a4f" },
];

export function CostStack({ curve }: { curve: CurvePoint[] }) {
  const data = curve.map((p) => ({
    aum: p.aum,
    aumLabel: (p.aum / 1e7) >= 1
      ? `${(p.aum/1e7).toFixed(0)} cr` : `${(p.aum/1e7).toFixed(1)} cr`,
    spread_bps: p.spread_bps,
    impact_bps: p.impact_bps,
    commission_bps: p.commission_bps,
    borrow_bps: p.borrow_bps,
    india_bps: p.india_bps,
  }));

  return (
    <ResponsiveContainer width="100%" height={360}>
      <BarChart data={data} margin={{ top: 16, right: 24, left: 12, bottom: 24 }}>
        <CartesianGrid stroke="#e6e3da" strokeDasharray="3 3" />
        <XAxis dataKey="aumLabel" />
        <YAxis label={{ value: "Annualised cost (bps)", angle: -90, position: "insideLeft",
                         style: { fill: "#5a5a5a", fontFamily: "'Source Serif 4', serif" } }} />
        <Tooltip contentStyle={{
          background: "#fbfaf6", border: "1px solid #e6e3da",
          fontFamily: "'Source Serif 4', serif",
        }} />
        <Legend wrapperStyle={{ fontFamily: "'Source Serif 4', serif", fontSize: 13 }} />
        {COMPONENTS.map((c) => (
          <Bar key={c.key} dataKey={c.key} stackId="a" fill={c.color} name={c.label} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
