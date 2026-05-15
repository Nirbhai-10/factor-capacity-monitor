import type { CostParams, PolicyRow, ReturnPoint } from "./types";
import { estimateCapacityCurve } from "./capacity";

/**
 * Operating-policy search. We don't have the user's full position history,
 * so we approximate the effect of changing rebalance frequency on turnover
 * (more frequent → more turnover) and the effect of a no-trade buffer
 * (cuts turnover by an empirical fraction calibrated on the Python sims).
 */
const FREQ_TURNOVER_FACTORS: Record<string, number> = {
  D: 4.0,    // daily
  W: 2.0,    // weekly
  BW: 1.4,   // bi-weekly
  M: 1.0,    // monthly (the baseline at which user's turnover is reported)
  Q: 0.5,    // quarterly
};

/** No-trade buffer cuts turnover roughly linearly up to ~50%. */
function bufferTurnoverMultiplier(bufferBps: number): number {
  const cut = Math.min(0.55, bufferBps / 600);
  return 1 - cut;
}

export function searchPolicy(
  returns: ReturnPoint[],
  baseCost: CostParams,
  targetAum: number,
  freqs: string[] = ["D", "W", "BW", "M", "Q"],
  buffersBps: number[] = [0, 25, 50, 100, 200],
): { bestFreq: string; bestBufferBps: number; bestNetIR: number; grid: PolicyRow[] } {
  const baseTurnover = baseCost.annualTurnover;

  const grid: PolicyRow[] = [];

  for (const f of freqs) {
    for (const buf of buffersBps) {
      const adjustedTurnover =
        baseTurnover * FREQ_TURNOVER_FACTORS[f] * bufferTurnoverMultiplier(buf);
      const adjustedCost: CostParams = { ...baseCost, annualTurnover: adjustedTurnover };
      const point = estimateCapacityCurve(returns, adjustedCost, [targetAum])[0];
      grid.push({
        freq: f,
        bufferBps: buf,
        netIR: point.netIR,
        totalCostBps: point.totalCostBps,
        turnover: adjustedTurnover,
      });
    }
  }

  let best = grid[0];
  for (const r of grid) if (r.netIR > best.netIR) best = r;

  return {
    bestFreq: best.freq,
    bestBufferBps: best.bufferBps,
    bestNetIR: best.netIR,
    grid,
  };
}
