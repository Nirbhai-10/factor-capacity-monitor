import type { ReturnPoint } from "./types";

export const TRADING_DAYS = 252;

export function mean(xs: number[]): number {
  if (xs.length === 0) return 0;
  let s = 0;
  for (const x of xs) s += x;
  return s / xs.length;
}

export function std(xs: number[]): number {
  const n = xs.length;
  if (n < 2) return 0;
  const m = mean(xs);
  let acc = 0;
  for (const x of xs) {
    const d = x - m;
    acc += d * d;
  }
  return Math.sqrt(acc / (n - 1));
}

export function annualise(daily: number, periodsPerYear = TRADING_DAYS): number {
  return daily * periodsPerYear;
}

export function annualiseVol(dailySd: number, periodsPerYear = TRADING_DAYS): number {
  return dailySd * Math.sqrt(periodsPerYear);
}

export function sharpe(returns: number[], riskFree = 0): number {
  const mu = mean(returns) - riskFree / TRADING_DAYS;
  const sd = std(returns);
  return sd > 0 ? (mu / sd) * Math.sqrt(TRADING_DAYS) : 0;
}

export function maxDrawdown(returns: number[]): number {
  let peak = 1;
  let trough = 1;
  let cum = 1;
  let mdd = 0;
  for (const r of returns) {
    cum *= 1 + r;
    if (cum > peak) {
      peak = cum;
      trough = cum;
    }
    if (cum < trough) trough = cum;
    const dd = trough / peak - 1;
    if (dd < mdd) mdd = dd;
  }
  return mdd;
}

export function rollingSharpe(
  returns: ReturnPoint[],
  window: number = 252,
): { date: string; value: number | null }[] {
  const n = returns.length;
  const out: { date: string; value: number | null }[] = [];
  for (let i = 0; i < n; i++) {
    if (i < window - 1) {
      out.push({ date: returns[i].date, value: null });
      continue;
    }
    const slice: number[] = [];
    for (let j = i - window + 1; j <= i; j++) slice.push(returns[j].ret);
    out.push({ date: returns[i].date, value: sharpe(slice) });
  }
  return out;
}

export function autocorr(xs: number[], lag = 1): number {
  const n = xs.length;
  if (n <= lag) return 0;
  const m = mean(xs);
  let num = 0;
  let den = 0;
  for (let i = 0; i < n; i++) {
    den += (xs[i] - m) ** 2;
  }
  for (let i = lag; i < n; i++) {
    num += (xs[i] - m) * (xs[i - lag] - m);
  }
  return den > 0 ? num / den : 0;
}

export function winRate(returns: number[]): number {
  if (returns.length === 0) return 0;
  let wins = 0;
  for (const r of returns) if (r > 0) wins++;
  return wins / returns.length;
}

export type Drawdown = {
  startDate: string;
  troughDate: string;
  endDate: string | null;          // null if still underwater
  depth: number;                   // negative number, e.g. -0.12
  lengthDays: number;              // peak → trough
  recoveryDays: number | null;     // trough → new high; null if still underwater
};

export function topDrawdowns(
  series: ReturnPoint[],
  k = 5,
): Drawdown[] {
  if (series.length === 0) return [];
  const equity: { date: string; v: number }[] = [];
  let cum = 1;
  for (const r of series) {
    cum *= 1 + r.ret;
    equity.push({ date: r.date, v: cum });
  }

  const drawdowns: Drawdown[] = [];
  let peakIdx = 0;
  let i = 1;
  while (i < equity.length) {
    if (equity[i].v >= equity[peakIdx].v) {
      peakIdx = i;
      i++;
      continue;
    }
    // start of a drawdown — find the trough
    const startIdx = peakIdx;
    let troughIdx = i;
    let j = i;
    while (j < equity.length && equity[j].v < equity[startIdx].v) {
      if (equity[j].v < equity[troughIdx].v) troughIdx = j;
      j++;
    }
    const recovered = j < equity.length;
    drawdowns.push({
      startDate: equity[startIdx].date,
      troughDate: equity[troughIdx].date,
      endDate: recovered ? equity[j].date : null,
      depth: equity[troughIdx].v / equity[startIdx].v - 1,
      lengthDays: troughIdx - startIdx,
      recoveryDays: recovered ? j - troughIdx : null,
    });
    peakIdx = recovered ? j : peakIdx;
    i = j + 1;
  }

  return drawdowns
    .sort((a, b) => a.depth - b.depth)
    .slice(0, k);
}
