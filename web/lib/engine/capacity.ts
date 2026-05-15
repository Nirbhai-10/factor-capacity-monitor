import type { CapacityPoint, CostParams, ReturnPoint } from "./types";
import { TRADING_DAYS, annualise, annualiseVol, mean, std } from "./stats";

/**
 * Estimate capacity curve from a returns series and cost parameters.
 *
 * Model
 *   For a given AUM A:
 *     turnover_$    = A · annualTurnover           (one-side)
 *     trades_per_yr = annualTurnover / 2           (round trips)
 *     spread_$      = ½ · spread · 2 · turnover_$  (two-sided)
 *     impact_$      = σ · k · √(p) · turnover_$    (Almgren-Chriss)
 *     where p = (A · annualTurnover) / (n_names · ADV · execDays)
 *     commission_$  = commission_bps · 2 · turnover_$
 *     borrow_$      = shortFraction · A · borrowBps · holdingDays/252 · n_round_trips
 *     india_$       = nse_stack · 2 · turnover_$        (if enabled)
 *
 *   Net IR(A) = (μ_daily − totalCost_$/(A·yrs)/252) / σ_daily
 *
 * Limitation: per-name ADV is approximated by `representativeAdv`. A real
 * deployment would feed a per-name ADV vector. This simplification is
 * conservative on the safe side because it averages out the worst-name
 * participation that drives most realised impact.
 */
export function estimateCapacityCurve(
  returns: ReturnPoint[],
  cost: CostParams,
  aumGrid: number[],
): CapacityPoint[] {
  const r = returns.map((p) => p.ret);
  const muDaily = mean(r);
  const sdDaily = std(r);
  const grossIR = sdDaily > 0 ? (muDaily / sdDaily) * Math.sqrt(TRADING_DAYS) : 0;

  // If the user didn't pass sigma, derive from returns.
  const sigmaAnn = cost.sigmaAnnual > 0 ? cost.sigmaAnnual : annualiseVol(sdDaily);

  const points: CapacityPoint[] = [];

  for (const A of aumGrid) {
    // turnover dollars per year (one-way notional traded)
    const turnoverPerYear = A * cost.annualTurnover;
    // half because each round-trip is 2 × turnover
    const oneWay = turnoverPerYear / 2;
    const nRoundTripsPerYear = oneWay / Math.max(1, oneWay) * (cost.annualTurnover / 2);

    // Spread: paid both ways
    const spreadDollarsAnnual = (cost.spreadBps / 1e4) * 2 * oneWay;

    // Participation: assume the strategy spreads across ~30 names; impact applied to one-way notional
    const nNames = 30;
    const participation = oneWay / (nNames * cost.representativeAdv);
    const cappedExecDays = Math.max(1, Math.ceil(participation / cost.participationCap));
    const adjustedParticipation = participation / cappedExecDays;
    const impactFrac =
      sigmaAnn * cost.impactCoefficient * Math.sqrt(Math.max(0, adjustedParticipation));
    const impactDollarsAnnual = impactFrac * 2 * oneWay;

    // Commission
    const commissionDollarsAnnual = (cost.commissionBps / 1e4) * 2 * oneWay;

    // Borrow on the short leg (carry cost on average outstanding short notional)
    const borrowDollarsAnnual =
      cost.shortBookFraction * A * (cost.borrowBps / 1e4);

    // India tax stack (per leg): STT 0.1% + stamp 0.015% + sebi 0.0001% + exch 0.00345% + GST on 18%·brokerage stack
    let taxDollarsAnnual = 0;
    if (cost.indiaTaxes) {
      const sttBuy = 0.001;
      const sttSell = 0.001;
      const stamp = 0.00015;
      const sebi = 1e-6;
      const exch = 0.0000345;
      const gst = 0.18 * (cost.commissionBps / 1e4 + sebi + exch);
      const perBuy = sttBuy + stamp + sebi + exch + gst;
      const perSell = sttSell + sebi + exch + gst;
      taxDollarsAnnual = (perBuy + perSell) * oneWay;
    }

    const totalDollars =
      spreadDollarsAnnual +
      impactDollarsAnnual +
      commissionDollarsAnnual +
      borrowDollarsAnnual +
      taxDollarsAnnual;

    const annualCostPct = totalDollars / Math.max(A, 1);
    const dailyCost = annualCostPct / TRADING_DAYS;
    const netDailyMu = muDaily - dailyCost;
    const netIR = sdDaily > 0 ? (netDailyMu / sdDaily) * Math.sqrt(TRADING_DAYS) : 0;

    const totalCostBps = annualCostPct * 1e4;

    const zone =
      netIR >= 0.5 && cappedExecDays <= 3 && participation < 0.03
        ? "safe"
        : netIR >= 0.2 && cappedExecDays <= 5 && participation < 0.05
        ? "caution"
        : "red";

    points.push({
      aum: A,
      netIR,
      grossIR,
      totalCostBps,
      spreadBps: (spreadDollarsAnnual / Math.max(A, 1)) * 1e4,
      impactBps: (impactDollarsAnnual / Math.max(A, 1)) * 1e4,
      commissionBps: (commissionDollarsAnnual / Math.max(A, 1)) * 1e4,
      borrowBps: (borrowDollarsAnnual / Math.max(A, 1)) * 1e4,
      taxBps: (taxDollarsAnnual / Math.max(A, 1)) * 1e4,
      participation,
      zone,
    });
  }

  return points;
}

export function safeCapacity(curve: CapacityPoint[]): number | null {
  const safe = curve.filter((p) => p.zone === "safe");
  if (safe.length === 0) return null;
  return Math.max(...safe.map((p) => p.aum));
}

export function ir50Capacity(curve: CapacityPoint[]): number | null {
  const sorted = [...curve].sort((a, b) => a.aum - b.aum);
  for (let i = sorted.length - 1; i >= 0; i--) {
    if (sorted[i].netIR >= 0.5) {
      if (i === sorted.length - 1) return sorted[i].aum;
      // linear interp between i and i+1
      const a = sorted[i];
      const b = sorted[i + 1];
      if (a.netIR === b.netIR) return a.aum;
      const t = (a.netIR - 0.5) / (a.netIR - b.netIR);
      return a.aum + t * (b.aum - a.aum);
    }
  }
  return null;
}

/** Default geometric AUM grid in INR. 10 cr → 5000 cr. */
export function defaultAumGrid(): number[] {
  return [10, 25, 50, 100, 250, 500, 1000, 2000, 5000].map((c) => c * 1e7);
}
