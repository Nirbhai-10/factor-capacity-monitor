/** ₹ formatter using crore (1 cr = 1e7). */
export function fmtCr(v: number | null | undefined, digits = 1): string {
  if (v == null || !isFinite(v)) return "—";
  const cr = v / 1e7;
  return cr.toLocaleString("en-IN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }) + " cr";
}

export function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v == null || !isFinite(v)) return "—";
  return (v * 100).toLocaleString("en-IN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }) + "%";
}

export function fmtIR(v: number | null | undefined): string {
  if (v == null || !isFinite(v)) return "—";
  return (v >= 0 ? "+" : "") + v.toFixed(2);
}

export function fmtBps(v: number | null | undefined, digits = 0): string {
  if (v == null || !isFinite(v)) return "—";
  return v.toFixed(digits) + " bps";
}

export function fmtNum(v: number | null | undefined, digits = 2): string {
  if (v == null || !isFinite(v)) return "—";
  return v.toLocaleString("en-IN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function shortAum(v: number | null | undefined): string {
  if (v == null || !isFinite(v) || v <= 0) return "—";
  const cr = v / 1e7;
  if (cr >= 1000) return (cr / 1000).toFixed(1) + "k cr";
  if (cr >= 10) return cr.toFixed(0) + " cr";
  return cr.toFixed(1) + " cr";
}
