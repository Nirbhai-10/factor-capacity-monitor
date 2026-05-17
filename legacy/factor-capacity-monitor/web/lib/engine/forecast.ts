import type { ReturnPoint } from "./types";
import { TRADING_DAYS, mean, std } from "./stats";

/**
 * OU mean-reversion fit on rolling 1-year Sharpe.
 *
 *   s_t       = trailing-1y Sharpe (observable)
 *   Δs_t      = a + b·z_t − κ·s_{t−1} + ε_t          (regression of OU form)
 *   μ_t       = (a + b·z_t) / κ                       (regime-mean attractor)
 *
 * `z` here is left as zero (no covariate) when we don't have a per-strategy
 * crowding feed; in that case the fit is a plain OU and the attractor is just
 * `a/κ`. If you supply a crowding score (0–100 series) it acts as the regime
 * covariate.
 */
export function fitOUForecast(
  returns: ReturnPoint[],
  horizonDays = 126,
  sharpeWindow = 252,
  crowdingSeries?: { date: string; value: number }[],
): {
  kappa: number;
  alpha: number;
  beta: number;
  rmse: number;
  series: { date: string; sharpe: number; lower: number; upper: number }[];
} {
  if (returns.length < sharpeWindow + 60) {
    return {
      kappa: 0, alpha: 0, beta: 0, rmse: 0,
      series: [],
    };
  }

  // 1) build trailing Sharpe
  const sharpes: { date: string; value: number }[] = [];
  for (let i = sharpeWindow; i < returns.length; i++) {
    const slice = returns.slice(i - sharpeWindow, i).map((p) => p.ret);
    const m = mean(slice);
    const s = std(slice);
    if (s > 0) {
      sharpes.push({ date: returns[i].date, value: (m / s) * Math.sqrt(TRADING_DAYS) });
    }
  }
  if (sharpes.length < 30) {
    return { kappa: 0, alpha: 0, beta: 0, rmse: 0, series: [] };
  }

  // 2) build regression rows
  const ds: number[] = [];
  const sLag: number[] = [];
  const cLag: number[] = [];
  const cmap = new Map<string, number>();
  if (crowdingSeries) {
    for (const r of crowdingSeries) cmap.set(r.date, r.value);
  }
  for (let i = 1; i < sharpes.length; i++) {
    ds.push(sharpes[i].value - sharpes[i - 1].value);
    sLag.push(sharpes[i - 1].value);
    cLag.push(cmap.get(sharpes[i - 1].date) ?? 0);
  }

  // OLS on Δs ~ a + b·c − κ·sLag (3 columns)
  // Solve via normal equations. Stable enough for n~hundreds.
  const n = ds.length;
  const X: number[][] = [];
  for (let i = 0; i < n; i++) X.push([1, cLag[i], -sLag[i]]);
  const Xt = transpose(X);
  const XtX = matMul(Xt, X);
  const Xty = matVecMul(Xt, ds);
  const coef = solve3x3(XtX, Xty);
  if (!coef) return { kappa: 0, alpha: 0, beta: 0, rmse: 0, series: [] };

  const a = coef[0];
  const b = coef[1];
  const kappaHat = Math.max(coef[2], 1e-6);

  // residual rmse
  let rss = 0;
  for (let i = 0; i < n; i++) {
    const pred = a + b * cLag[i] - kappaHat * sLag[i];
    rss += (ds[i] - pred) ** 2;
  }
  const rmse = Math.sqrt(rss / n);

  // 3) project forward
  const lastSharpe = sharpes[sharpes.length - 1].value;
  const lastCrowd = cLag[cLag.length - 1];
  const muT = a + b * lastCrowd;
  const attractor = muT / kappaHat;

  const sigmaInc = rmse / kappaHat;
  const series: { date: string; sharpe: number; lower: number; upper: number }[] = [];
  const last = new Date(sharpes[sharpes.length - 1].date);
  for (let h = 1; h <= horizonDays; h++) {
    const decay = Math.exp(-kappaHat * h);
    const sharpe = attractor + (lastSharpe - attractor) * decay;
    const fan = sigmaInc * Math.sqrt(1 - Math.exp(-2 * kappaHat * h));
    last.setDate(last.getDate() + 1);
    series.push({
      date: last.toISOString().slice(0, 10),
      sharpe,
      lower: sharpe - fan,
      upper: sharpe + fan,
    });
  }

  return {
    kappa: kappaHat,
    alpha: a / kappaHat,
    beta: b / kappaHat,
    rmse,
    series,
  };
}

/* ───────── linalg helpers ───────── */
function transpose(M: number[][]): number[][] {
  const rows = M.length;
  const cols = M[0].length;
  const out: number[][] = [];
  for (let j = 0; j < cols; j++) {
    out.push(new Array(rows).fill(0));
    for (let i = 0; i < rows; i++) out[j][i] = M[i][j];
  }
  return out;
}
function matMul(A: number[][], B: number[][]): number[][] {
  const r = A.length;
  const c = B[0].length;
  const k = B.length;
  const out: number[][] = Array.from({ length: r }, () => new Array(c).fill(0));
  for (let i = 0; i < r; i++)
    for (let j = 0; j < c; j++) {
      let s = 0;
      for (let m = 0; m < k; m++) s += A[i][m] * B[m][j];
      out[i][j] = s;
    }
  return out;
}
function matVecMul(A: number[][], v: number[]): number[] {
  return A.map((row) => row.reduce((s, x, i) => s + x * v[i], 0));
}
function solve3x3(A: number[][], b: number[]): number[] | null {
  // copy
  const M = A.map((row) => [...row, b[A.indexOf(row)]]);
  for (let i = 0; i < 3; i++) M[i].push(b[i]);
  // build augmented
  const Ab: number[][] = [
    [A[0][0], A[0][1], A[0][2], b[0]],
    [A[1][0], A[1][1], A[1][2], b[1]],
    [A[2][0], A[2][1], A[2][2], b[2]],
  ];
  // Gaussian elimination with partial pivot
  for (let col = 0; col < 3; col++) {
    let pivot = col;
    for (let r = col + 1; r < 3; r++) {
      if (Math.abs(Ab[r][col]) > Math.abs(Ab[pivot][col])) pivot = r;
    }
    if (Math.abs(Ab[pivot][col]) < 1e-12) return null;
    [Ab[col], Ab[pivot]] = [Ab[pivot], Ab[col]];
    for (let r = col + 1; r < 3; r++) {
      const f = Ab[r][col] / Ab[col][col];
      for (let c = col; c < 4; c++) Ab[r][c] -= f * Ab[col][c];
    }
  }
  const x = [0, 0, 0];
  for (let i = 2; i >= 0; i--) {
    let s = Ab[i][3];
    for (let j = i + 1; j < 3; j++) s -= Ab[i][j] * x[j];
    x[i] = s / Ab[i][i];
  }
  return x;
}
