"use client";
import { data } from "@/lib/data";
import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend,
} from "recharts";
import { fmtCr, fmtIR } from "@/lib/format";
import { ZonePill } from "@/components/ZonePill";

/**
 * Slim preview that overlays the four reference factors' capacity curves
 * on a single chart, plus the headline numbers for each. Lives on the
 * landing page so a visitor can see the tool's output without navigating.
 */
const FACTOR_COLORS: Record<string, string> = {
  momentum: "#1a3a5c",
  value: "#a08c5d",
  quality: "#2d6a45",
  low_vol: "#862f2f",
};

export function ReferencePreview() {
  const factors = data.meta.factors;

  // build a wide-format array: one row per AUM, columns per factor
  const aumGrid = data.factors[factors[0]].curve.map((p) => p.aum);
  const wide = aumGrid.map((aum) => {
    const row: Record<string, number | string> = { aum };
    for (const f of factors) {
      const pt = data.factors[f].curve.find((p) => p.aum === aum);
      row[f] = pt ? pt.net_ir : 0;
    }
    return row;
  });

  return (
    <div className="space-y-6">
      <div>
        <ResponsiveContainer width="100%" height={320}>
          <ComposedChart data={wide} margin={{ top: 16, right: 24, left: 12, bottom: 24 }}>
            <CartesianGrid stroke="#ebe8de" strokeDasharray="2 4" vertical={false} />
            <XAxis dataKey="aum" type="number" scale="log" domain={["auto", "auto"]}
                    tickFormatter={(v) => {
                      const cr = v / 1e7;
                      if (cr >= 1000) return `${(cr/1000).toFixed(0)}k`;
                      return cr.toFixed(0);
                    }}
                    label={{ value: "AUM (₹ cr, log)", position: "insideBottom", offset: -16, style: { fill: "#6b6b6b", fontSize: 11 } }} />
            <YAxis tickFormatter={(v) => v.toFixed(1)}
                    label={{ value: "Net IR", angle: -90, position: "insideLeft", style: { fill: "#6b6b6b", fontSize: 11 } }} />
            <Tooltip />
            <ReferenceLine y={0.5} stroke="#6b6b6b" strokeDasharray="3 3"
                            label={{ value: "IR=0.5", position: "right", fill: "#6b6b6b", fontSize: 10 }} />
            {factors.map((f) => (
              <Line key={f} type="monotone" dataKey={f}
                     stroke={FACTOR_COLORS[f] ?? "#1a1a1a"} strokeWidth={1.6}
                     dot={false} name={f} />
            ))}
            <Legend wrapperStyle={{ fontSize: 11 }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="overflow-x-auto">
        <table>
          <thead>
            <tr>
              <th>factor</th>
              <th className="text-right">gross IR</th>
              <th className="text-right">safe AUM</th>
              <th className="text-right">crowding</th>
              <th>policy</th>
            </tr>
          </thead>
          <tbody>
            {factors.map((f) => {
              const fb = data.factors[f];
              return (
                <tr key={f}>
                  <td><span style={{ color: FACTOR_COLORS[f] }}>●</span> {f}</td>
                  <td className="text-right">{fmtIR(fb.gross_ir)}</td>
                  <td className="text-right">{fmtCr(fb.safe_capacity)}</td>
                  <td className="text-right">{fb.crowding_latest.toFixed(0)} <ZonePill zone={fb.alert_level} /></td>
                  <td>{fb.best_policy.freq} / {fb.best_policy.buffer_bps}bps</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
