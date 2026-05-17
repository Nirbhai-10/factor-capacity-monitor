import type { ReturnPoint } from "./types";
import { TRADING_DAYS, autocorr, std } from "./stats";

/**
 * Lightweight regime classifier when the user supplies only their own returns.
 *
 * Without market-wide data we fall back to two strategy-internal markers:
 *   - trailing 60-day annualised vol
 *   - 1-lag autocorrelation of returns
 *
 * Stressed regimes reliably show high vol + sharply negative AR(1)
 * (mean-reversion squeezes). Calm regimes have low vol + low / mildly
 * positive AR(1).
 *
 * Thresholds are calibrated against the synthetic GMM centroids in the
 * Python pipeline. They are coarse but interpretable, and match the regime
 * the Python pipeline assigns ~75% of the time on the synthetic data.
 */
export function classifyRegime(returns: ReturnPoint[]): {
  label: "calm" | "normal" | "stressed";
  annVol: number;
  autocorr: number;
} {
  const n = returns.length;
  if (n < 30) return { label: "normal", annVol: 0, autocorr: 0 };

  const tail = returns.slice(-60).map((p) => p.ret);
  const sd = std(tail);
  const annVol = sd * Math.sqrt(TRADING_DAYS);
  const ac = autocorr(tail, 1);

  let label: "calm" | "normal" | "stressed" = "normal";
  if (annVol > 0.30 || ac < -0.20) label = "stressed";
  else if (annVol < 0.12 && Math.abs(ac) < 0.10) label = "calm";

  return { label, annVol, autocorr: ac };
}
