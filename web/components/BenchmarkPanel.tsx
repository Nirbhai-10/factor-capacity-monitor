"use client";
import { data as benchData } from "@/lib/data";
import type { AnalysisResult } from "@/lib/engine/types";
import { fmtCr, fmtIR } from "@/lib/format";

/**
 * Side-by-side: user's strategy vs the four reference factors that were
 * pre-computed in Python (momentum, value, quality, low_vol). Same number
 * format, immediate eyeballing.
 */
export function BenchmarkPanel({ user }: { user: AnalysisResult }) {
  const factors = benchData.meta.factors;
  return (
    <div className="overflow-x-auto">
      <table>
        <thead>
          <tr>
            <th>strategy</th>
            <th className="text-right">gross IR</th>
            <th className="text-right">safe AUM</th>
            <th className="text-right">IR≥0.5 AUM</th>
            <th className="text-right">crowding</th>
            <th className="text-right">best policy</th>
          </tr>
        </thead>
        <tbody>
          <tr className="highlight">
            <td>{user.strategy.name} (you)</td>
            <td className="text-right">{fmtIR(user.stats.grossIR)}</td>
            <td className="text-right">{fmtCr(user.safeCapacity)}</td>
            <td className="text-right">{fmtCr(user.ir50Capacity)}</td>
            <td className="text-right text-[var(--muted)]">—</td>
            <td className="text-right">{user.policy.bestFreq}/{user.policy.bestBufferBps}b</td>
          </tr>
          {factors.map((f) => {
            const fb = benchData.factors[f];
            return (
              <tr key={f}>
                <td>{f}</td>
                <td className="text-right">{fmtIR(fb.gross_ir)}</td>
                <td className="text-right">{fmtCr(fb.safe_capacity)}</td>
                <td className="text-right">{fmtCr(fb.ir50_capacity)}</td>
                <td className="text-right">{fb.crowding_latest.toFixed(0)}</td>
                <td className="text-right">{fb.best_policy.freq}/{fb.best_policy.buffer_bps}b</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
