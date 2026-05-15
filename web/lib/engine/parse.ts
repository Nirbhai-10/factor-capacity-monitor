import Papa from "papaparse";
import type { ReturnPoint, Strategy } from "./types";

export type ParseError = { kind: "ParseError"; message: string };
export type ParseResult = { ok: true; strategy: Strategy } | { ok: false; error: ParseError };

/**
 * Parse a user-uploaded CSV.
 *
 * Accepted shapes:
 *   1) Two columns: [date, ret]                      ← already daily returns
 *   2) Two columns: [date, equity] or [date, nav]    ← we differentiate to returns
 *   3) Two columns: [date, pnl%]                     ← already in %, we divide by 100
 *
 * Heuristic: if any value's |x| > 1, we assume percentage and convert.
 * If returns trend monotonically and avg(|x|) > 0.5, we assume NAV/equity.
 *
 * Date parsing accepts: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, "1 Jan 2024".
 */
export function parseCsv(text: string, name: string): ParseResult {
  const cleaned = text.trim();
  if (!cleaned) return { ok: false, error: { kind: "ParseError", message: "Empty file" } };

  const result = Papa.parse<Record<string, string>>(cleaned, {
    header: true,
    skipEmptyLines: true,
    transformHeader: (h) => h.trim().toLowerCase(),
  });

  if (result.errors.length > 0) {
    return {
      ok: false,
      error: { kind: "ParseError", message: result.errors[0].message },
    };
  }

  const fields = result.meta.fields ?? [];
  const dateCol = pickColumn(fields, ["date", "day", "trade_date", "asof"]);
  const valCol = pickColumn(fields, [
    "ret", "return", "returns", "daily_return", "pnl",
    "pnl%", "pct", "percent", "performance",
    "nav", "equity", "balance", "value",
  ]);

  if (!dateCol || !valCol) {
    return {
      ok: false,
      error: {
        kind: "ParseError",
        message: `Need a date column and one of: ret/return/pnl/nav/equity. Found: ${fields.join(", ")}`,
      },
    };
  }

  const rows: { date: Date; v: number }[] = [];
  for (const r of result.data) {
    const d = parseDate(r[dateCol]);
    const v = parseNumber(r[valCol]);
    if (d && Number.isFinite(v)) rows.push({ date: d, v });
  }
  if (rows.length < 30) {
    return {
      ok: false,
      error: {
        kind: "ParseError",
        message: `Need at least 30 rows; got ${rows.length}. Check your CSV.`,
      },
    };
  }
  rows.sort((a, b) => a.date.getTime() - b.date.getTime());

  // Decide return vs NAV
  const vals = rows.map((r) => r.v);
  const absMean = vals.reduce((a, b) => a + Math.abs(b), 0) / vals.length;
  const monotonicRising = vals.slice(1).every((v, i) => v >= vals[i] || Math.abs(v - vals[i]) < absMean * 0.5);

  let returns: ReturnPoint[] = [];
  if (absMean > 5) {
    // looks like NAV / equity / index level — differentiate
    for (let i = 1; i < rows.length; i++) {
      const r = rows[i].v / rows[i - 1].v - 1;
      if (Number.isFinite(r)) {
        returns.push({ date: rows[i].date.toISOString().slice(0, 10), ret: r });
      }
    }
  } else if (absMean > 1) {
    // looks like percentages
    returns = rows.map((r) => ({ date: r.date.toISOString().slice(0, 10), ret: r.v / 100 }));
  } else {
    returns = rows.map((r) => ({ date: r.date.toISOString().slice(0, 10), ret: r.v }));
  }

  if (returns.length < 30) {
    return {
      ok: false,
      error: { kind: "ParseError", message: "After differencing, fewer than 30 valid return rows." },
    };
  }

  return {
    ok: true,
    strategy: {
      name,
      returns,
      meta: {
        rows: returns.length,
        startDate: returns[0].date,
        endDate: returns[returns.length - 1].date,
      },
    },
  };
}

function pickColumn(fields: string[], candidates: string[]): string | null {
  const lower = fields.map((f) => f.toLowerCase());
  for (const c of candidates) {
    const i = lower.indexOf(c);
    if (i >= 0) return fields[i];
  }
  return null;
}

function parseNumber(s: string | undefined): number {
  if (s == null) return NaN;
  const cleaned = s.replace(/[,_\s%]/g, "");
  if (!cleaned) return NaN;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : NaN;
}

function parseDate(s: string | undefined): Date | null {
  if (!s) return null;
  const t = s.trim();
  // ISO
  if (/^\d{4}-\d{2}-\d{2}/.test(t)) return new Date(t);
  // DD/MM/YYYY or MM/DD/YYYY  — assume DD/MM if first part > 12
  const slash = t.match(/^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})/);
  if (slash) {
    const a = +slash[1], b = +slash[2];
    let yr = +slash[3];
    if (yr < 100) yr += 2000;
    if (a > 12) {
      // DD/MM/YYYY
      return new Date(yr, b - 1, a);
    } else if (b > 12) {
      // MM/DD/YYYY
      return new Date(yr, a - 1, b);
    }
    // ambiguous — default to DD/MM (Indian-friendly)
    return new Date(yr, b - 1, a);
  }
  const generic = new Date(t);
  return isNaN(generic.getTime()) ? null : generic;
}

/** Tiny sample CSV for the empty-state demo button. */
export function sampleCsv(): string {
  // 1y of synthetic daily returns, mean 0.1%/day, vol 1.5%/day, slight AR(1)
  const rows = ["date,ret"];
  let prev = 0;
  const start = new Date("2024-04-01");
  for (let i = 0; i < 252; i++) {
    const eps = (Math.random() - 0.5) * 0.03;
    const r = 0.5 * prev + 0.001 + eps;
    prev = r;
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    if (d.getDay() === 0 || d.getDay() === 6) continue;
    rows.push(`${d.toISOString().slice(0, 10)},${r.toFixed(6)}`);
  }
  return rows.join("\n");
}
