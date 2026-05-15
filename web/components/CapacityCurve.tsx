"use client";
import {
  ComposedChart, Line, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Legend,
} from "recharts";
import type { CurvePoint } from "@/lib/types";

const ZONE = { safe: "#2d7a4f", caution: "#b07c2c", red: "#a04040" } as const;

export function CapacityCurve({ curve, stress }: {
  curve: CurvePoint[];
  stress?: CurvePoint[];
}) {
  const data = curve.map((p) => ({
    aum: p.aum,
    netIR: p.net_ir,
    grossIR: p.gross_ir,
    zone: p.zone,
    stressedIR: stress?.find((s) => s.aum === p.aum)?.net_ir ?? null,
  }));

  return (
    <ResponsiveContainer width="100%" height={420}>
      <ComposedChart data={data} margin={{ top: 24, right: 28, left: 12, bottom: 36 }}>
        <CartesianGrid stroke="#e6e3da" strokeDasharray="3 3" />
        <XAxis
          dataKey="aum"
          scale="log"
          domain={["auto", "auto"]}
          type="number"
          tickFormatter={(v) => {
            const cr = v / 1e7;
            if (cr >= 1000) return `${(cr/1000).toFixed(0)}k cr`;
            if (cr >= 1) return `${cr.toFixed(0)} cr`;
            return `${cr.toFixed(1)} cr`;
          }}
          label={{ value: "AUM (₹)", position: "insideBottom", offset: -16,
                    style: { fill: "#5a5a5a", fontFamily: "'Source Serif 4', serif" } }}
        />
        <YAxis
          domain={[(min: number) => Math.min(min - 0.1, -0.5), (max: number) => Math.max(max + 0.1, 1.5)]}
          tickFormatter={(v) => v.toFixed(2)}
          label={{ value: "Information Ratio", angle: -90, position: "insideLeft",
                    style: { fill: "#5a5a5a", fontFamily: "'Source Serif 4', serif" } }}
        />
        <Tooltip
          contentStyle={{ background: "#fbfaf6", border: "1px solid #e6e3da", fontFamily: "'Source Serif 4', serif" }}
          labelFormatter={(v) => `AUM: ${(Number(v)/1e7).toLocaleString('en-IN',{maximumFractionDigits:1})} cr`}
          formatter={(v: number, name: string) => [v?.toFixed?.(2), name]}
        />
        <ReferenceLine y={0.5} stroke="#5a5a5a" strokeDasharray="4 4"
                        label={{ value: "IR = 0.5 hurdle", position: "right", fill: "#5a5a5a", fontSize: 11 }} />
        <Line type="monotone" dataKey="grossIR" stroke="#a08c5d" strokeDasharray="4 4"
              dot={false} name="Gross IR" />
        <Line type="monotone" dataKey="netIR" stroke="#1a3a5c" strokeWidth={2}
              dot={false} name="Net IR" />
        {stress && (
          <Line type="monotone" dataKey="stressedIR" stroke="#a04040" strokeDasharray="2 6"
                dot={false} name="Stressed Net IR" />
        )}
        <Scatter dataKey="netIR" name="zone"
                 shape={(props: any) => {
                   const { cx, cy, payload } = props;
                   if (cx == null || cy == null) return <g />;
                   return <circle cx={cx} cy={cy} r={5}
                                   fill={ZONE[payload.zone as keyof typeof ZONE]}
                                   stroke="#fff" strokeWidth={1} />;
                 }} />
        <Legend verticalAlign="top" height={28}
                 wrapperStyle={{ fontFamily: "'Source Serif 4', serif", fontSize: 13 }} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
