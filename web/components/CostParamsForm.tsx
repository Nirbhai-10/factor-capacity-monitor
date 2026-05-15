"use client";
import type { CostParams } from "@/lib/engine/types";

export function CostParamsForm({
  value, onChange,
}: {
  value: CostParams;
  onChange: (cp: CostParams) => void;
}) {
  function set<K extends keyof CostParams>(k: K, v: CostParams[K]) {
    onChange({ ...value, [k]: v });
  }
  function num(k: keyof CostParams, scale = 1) {
    return (e: React.ChangeEvent<HTMLInputElement>) => {
      const x = Number(e.target.value);
      if (Number.isFinite(x)) set(k, (x * scale) as never);
    };
  }
  return (
    <div className="grid sm:grid-cols-2 gap-x-6 gap-y-4">
      <Field label="Spread (bps)" hint="typical bid-ask spread on traded names">
        <input type="number" min="0" max="500" step="0.5"
                value={value.spreadBps} onChange={num("spreadBps")} />
      </Field>
      <Field label="Impact coefficient k" hint="Almgren-Chriss; AQR fills imply 0.10–0.30">
        <input type="number" min="0" max="1" step="0.01"
                value={value.impactCoefficient} onChange={num("impactCoefficient")} />
      </Field>
      <Field label="Commission (bps / side)" hint="broker fee per leg, ex-tax">
        <input type="number" min="0" max="50" step="0.1"
                value={value.commissionBps} onChange={num("commissionBps")} />
      </Field>
      <Field label="Borrow (bps annualised)" hint="weighted-avg borrow cost on the short leg">
        <input type="number" min="0" max="2000" step="5"
                value={value.borrowBps} onChange={num("borrowBps")} />
      </Field>
      <Field label="Annual turnover (×)" hint="2.0 = portfolio rotates 200% / yr">
        <input type="number" min="0" max="20" step="0.1"
                value={value.annualTurnover} onChange={num("annualTurnover")} />
      </Field>
      <Field label="Holding period (days)" hint="round-trip cost amortises across this many days">
        <input type="number" min="1" max="252" step="1"
                value={value.holdingDays} onChange={num("holdingDays")} />
      </Field>
      <Field label="Representative ADV (₹ cr)"
              hint="median dollar-ADV of names you trade — used to estimate participation">
        <input type="number" min="0.1" max="10000" step="1"
                value={Math.round(value.representativeAdv / 1e7)}
                onChange={(e) => set("representativeAdv", Number(e.target.value) * 1e7)} />
      </Field>
      <Field label="Participation cap" hint="max % of ADV per name per day, e.g. 0.05 = 5%">
        <input type="number" min="0.005" max="0.5" step="0.005"
                value={value.participationCap} onChange={num("participationCap")} />
      </Field>
      <Field label="Annualised vol of strategy" hint="leave 0 to estimate from returns">
        <input type="number" min="0" max="3" step="0.01"
                value={value.sigmaAnnual} onChange={num("sigmaAnnual")} />
      </Field>
      <Field label="Short book fraction" hint="0.5 = dollar-neutral L/S, 0 = long-only">
        <input type="number" min="0" max="1" step="0.05"
                value={value.shortBookFraction} onChange={num("shortBookFraction")} />
      </Field>
      <Field label="Apply India NSE tax stack?" hint="STT, stamp, SEBI, exchange, GST">
        <select value={value.indiaTaxes ? "yes" : "no"}
                 onChange={(e) => set("indiaTaxes", e.target.value === "yes")}>
          <option value="yes">yes</option>
          <option value="no">no</option>
        </select>
      </Field>
    </div>
  );
}

function Field({ label, hint, children }: {
  label: string; hint?: string; children: React.ReactNode;
}) {
  return (
    <div>
      <label>{label}</label>
      {children}
      {hint && <div className="text-[0.72rem] text-[var(--muted)] mt-1">{hint}</div>}
    </div>
  );
}
