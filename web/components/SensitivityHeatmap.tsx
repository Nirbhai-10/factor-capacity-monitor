"use client";
import { useMemo } from "react";
import type { CostParams, ReturnPoint } from "@/lib/engine/types";
import { defaultAumGrid, estimateCapacityCurve, safeCapacity } from "@/lib/engine/capacity";

/**
 * 2-D sensitivity grid: how does Safe Capacity move as the impact coefficient
 * `k` and annual turnover both move ±50% around the user's chosen values?
 *
 * Cell colour is a centred red ↔ navy gradient — red = lower than baseline,
 * navy = higher.
 */
export function SensitivityHeatmap({
  returns, costs,
}: {
  returns: ReturnPoint[];
  costs: CostParams;
}) {
  const k_levels = [0.5, 0.75, 1.0, 1.25, 1.5];   // multipliers of baseline k
  const t_levels = [0.5, 0.75, 1.0, 1.25, 1.5];   // multipliers of baseline turnover
  const grid = defaultAumGrid();

  const baseline = useMemo(() => {
    const c = estimateCapacityCurve(returns, costs, grid);
    return safeCapacity(c) ?? 0;
  }, [returns, costs]);

  const cells = useMemo(() => {
    return k_levels.map((kMul) =>
      t_levels.map((tMul) => {
        const c: CostParams = {
          ...costs,
          impactCoefficient: costs.impactCoefficient * kMul,
          annualTurnover: costs.annualTurnover * tMul,
        };
        const curve = estimateCapacityCurve(returns, c, grid);
        return safeCapacity(curve) ?? 0;
      })
    );
  }, [returns, costs]);

  // Color scale: 0 → red, baseline → neutral, max → green-ish (navy)
  const flat = cells.flat();
  const maxV = Math.max(...flat, baseline, 1);
  function color(v: number): string {
    if (v <= 0) return "#f4dcdc";
    const ratio = v / maxV;            // 0..1
    // interpolate between cream and navy
    const r = Math.round(251 + (26 - 251) * ratio);
    const g = Math.round(250 + (58 - 250) * ratio);
    const b = Math.round(246 + (92 - 246) * ratio);
    return `rgb(${r},${g},${b})`;
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="text-center">
          <thead>
            <tr>
              <th></th>
              <th colSpan={t_levels.length} className="text-center">turnover multiplier</th>
            </tr>
            <tr>
              <th className="text-right">k mult.</th>
              {t_levels.map((t) => (
                <th key={t} className="text-center tabular">{t.toFixed(2)}×</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {k_levels.map((kMul, i) => (
              <tr key={kMul}>
                <td className="text-right tabular">{kMul.toFixed(2)}×</td>
                {cells[i].map((v, j) => (
                  <td key={j}
                       style={{ background: color(v) }}
                       className="tabular text-center">
                    {v > 0 ? `${(v / 1e7).toFixed(0)} cr` : "—"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[var(--muted)] mt-3 text-xs">
        Each cell: safe capacity if impact coefficient is multiplied by row, turnover by column.
        Baseline (1×, 1×) = <span className="tabular">{(baseline / 1e7).toFixed(0)} cr</span>.
        Read off how sensitive your safe AUM is to your two biggest assumptions.
      </p>
    </div>
  );
}
