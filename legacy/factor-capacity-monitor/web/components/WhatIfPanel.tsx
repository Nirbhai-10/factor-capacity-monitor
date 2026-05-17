"use client";
import { useMemo, useState } from "react";
import type { CostParams, ReturnPoint } from "@/lib/engine/types";
import { estimateCapacityCurve, safeCapacity } from "@/lib/engine/capacity";
import { ZonePill } from "@/components/ZonePill";
import { fmtCr, fmtIR, fmtPct } from "@/lib/format";

/**
 * "If I run my strategy at AUM = X, what's my net IR and how much
 * headroom do I have to the safe cap?"
 *
 * Recomputes the capacity curve at the user-supplied AUM (single point),
 * displays Net IR, zone, total cost, max participation, and headroom.
 */
export function WhatIfPanel({
  returns, costs, safeCap,
}: {
  returns: ReturnPoint[];
  costs: CostParams;
  safeCap: number | null;
}) {
  const [aumCr, setAumCr] = useState<number>(safeCap ? Math.max(1, Math.round(safeCap / 1e7 / 2)) : 50);

  const point = useMemo(() => {
    const aum = aumCr * 1e7;
    const curve = estimateCapacityCurve(returns, costs, [aum]);
    return curve[0];
  }, [returns, costs, aumCr]);

  const headroom = safeCap != null ? safeCap - aumCr * 1e7 : null;
  const utilisation = safeCap && safeCap > 0 ? (aumCr * 1e7) / safeCap : null;

  return (
    <div className="space-y-6">
      <div className="grid sm:grid-cols-[1fr_auto] gap-4 items-end">
        <div>
          <label htmlFor="aum-slider">target AUM (₹ cr)</label>
          <div className="flex items-center gap-3">
            <input id="aum-slider"
                   type="range" min="1" max="5000" step="1"
                   value={aumCr}
                   onChange={(e) => setAumCr(Number(e.target.value))}
                   className="flex-1 accent-[#1a3a5c]" />
            <input type="number" min="0" max="100000" step="1"
                    value={aumCr}
                    onChange={(e) => setAumCr(Math.max(0, Number(e.target.value) || 0))}
                    className="!w-32" />
          </div>
        </div>
        <div className="text-right">
          <div className="kicker">at this AUM</div>
          <div className="font-serif text-3xl">{fmtCr(aumCr * 1e7)}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[var(--rule)] border border-[var(--rule)]">
        <Cell label="Net IR" value={fmtIR(point.netIR)} />
        <Cell label="Zone" value={<ZonePill zone={point.zone} />} />
        <Cell label="Total cost" value={`${point.totalCostBps.toFixed(0)} bps`}
               hint="annualised" />
        <Cell label="Max name participation" value={`${(point.participation * 100).toFixed(1)}%`}
               hint={`exec days ≈ ${Math.max(1, Math.ceil(point.participation / costs.participationCap))}`} />
        <Cell label="Spread cost" value={`${point.spreadBps.toFixed(0)} bps`} />
        <Cell label="Impact cost" value={`${point.impactBps.toFixed(0)} bps`} />
        <Cell label="Borrow + tax" value={`${(point.borrowBps + point.taxBps).toFixed(0)} bps`} />
        <Cell label="Headroom to safe cap"
               value={headroom == null
                 ? "—"
                 : headroom > 0
                   ? fmtCr(headroom)
                   : `${fmtCr(Math.abs(headroom))} over`}
               hint={utilisation != null ? `${(utilisation * 100).toFixed(0)}% of safe cap` : ""} />
      </div>

      <div className="note">
        At <span className="tabular">{fmtCr(aumCr * 1e7)}</span>, the strategy is in the
        <span className={`zone-pill zone-${point.zone} mx-1`}>{point.zone}</span>
        zone with <span className="tabular">{fmtBps(point.totalCostBps)}</span> of round-trip cost
        eating <span className="tabular">{((point.grossIR - point.netIR) > 0 ? (point.grossIR - point.netIR).toFixed(2) : "0.00")}</span>
        IR units off the gross. {utilisation != null && utilisation > 1 && (
          <span className="text-[#862f2f]"> You are running over your safe cap by {fmtCr(Math.abs(headroom!))}; expect realised slippage to outpace this static estimate in stress.</span>
        )}
      </div>
    </div>
  );
}

function Cell({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="bg-[var(--bg)] p-4">
      <div className="kicker mb-1">{label}</div>
      <div className="font-serif text-xl text-ink leading-tight">{value}</div>
      {hint && <div className="text-[0.72rem] text-[var(--muted)] mt-1">{hint}</div>}
    </div>
  );
}

function fmtBps(bps: number) {
  return `${bps.toFixed(0)} bps`;
}
