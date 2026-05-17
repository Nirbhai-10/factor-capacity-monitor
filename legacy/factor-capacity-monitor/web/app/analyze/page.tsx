"use client";
import { useMemo, useState } from "react";
import { UploadZone } from "@/components/UploadZone";
import { CostParamsForm } from "@/components/CostParamsForm";
import { StrategyResults } from "@/components/StrategyResults";
import { BenchmarkPanel } from "@/components/BenchmarkPanel";
import { RollingSharpe } from "@/components/RollingSharpe";
import { DrawdownAnalyzer } from "@/components/DrawdownAnalyzer";
import { WhatIfPanel } from "@/components/WhatIfPanel";
import { SensitivityHeatmap } from "@/components/SensitivityHeatmap";
import {
  defaultAumGrid, estimateCapacityCurve, ir50Capacity, safeCapacity,
} from "@/lib/engine/capacity";
import { fitOUForecast } from "@/lib/engine/forecast";
import { searchPolicy } from "@/lib/engine/policy";
import { classifyRegime } from "@/lib/engine/regime";
import {
  TRADING_DAYS, annualise, annualiseVol, maxDrawdown, mean, sharpe, std,
  topDrawdowns, winRate,
} from "@/lib/engine/stats";
import type { AnalysisResult, CostParams, Strategy } from "@/lib/engine/types";
import { curveToCsv, downloadFile, memoMarkdown } from "@/lib/engine/export";

function WhatIfWrapper({ children }: { children: React.ReactNode }) {
  // little vertical breathing room so each section stands on its own
  return <div className="mb-4">{children}</div>;
}

const DEFAULT_COST: CostParams = {
  sigmaAnnual: 0,
  impactCoefficient: 0.20,
  spreadBps: 8,
  commissionBps: 1,
  borrowBps: 50,
  annualTurnover: 2.0,
  representativeAdv: 100 * 1e7,    // 100 cr
  participationCap: 0.05,
  holdingDays: 21,
  indiaTaxes: true,
  shortBookFraction: 0.5,
};

export default function AnalyzePage() {
  const [strategy, setStrategy] = useState<Strategy | null>(null);
  const [costs, setCosts] = useState<CostParams>(DEFAULT_COST);
  const [showParams, setShowParams] = useState(true);

  const result = useMemo<AnalysisResult | null>(() => {
    if (!strategy) return null;
    const r = strategy.returns.map((p) => p.ret);
    const sd = std(r);
    const mu = mean(r);
    const grid = defaultAumGrid();
    const curve = estimateCapacityCurve(strategy.returns, costs, grid);
    const forecast = fitOUForecast(strategy.returns);
    const targetAum = safeCapacity(curve) ?? grid[0];
    const policy = searchPolicy(strategy.returns, costs, targetAum);
    const regime = classifyRegime(strategy.returns);

    const stats = {
      grossIR: sd > 0 ? (mu / sd) * Math.sqrt(TRADING_DAYS) : 0,
      sharpe: sharpe(r),
      annualReturn: annualise(mu),
      annualVol: annualiseVol(sd),
      maxDrawdown: maxDrawdown(r),
      winRate: winRate(r),
      bestDay: Math.max(...r),
      worstDay: Math.min(...r),
      drawdowns: topDrawdowns(strategy.returns, 5),
    };

    return {
      strategy,
      stats,
      curve,
      safeCapacity: safeCapacity(curve),
      ir50Capacity: ir50Capacity(curve),
      forecast: {
        kappa: forecast.kappa,
        halfLifeDays: forecast.kappa > 0 ? Math.log(2) / forecast.kappa : 0,
        fittedAlpha: forecast.alpha,
        series: forecast.series,
      },
      policy,
      regime,
      costParams: costs,
      computedAt: new Date().toISOString(),
    };
  }, [strategy, costs]);

  return (
    <div className="section">
      <header className="mb-10">
        <div className="kicker mb-2">Tool</div>
        <h1 className="font-serif">Analyze your strategy</h1>
        <p className="lede mt-3">
          Upload a daily P&amp;L or returns CSV. We estimate your capacity curve,
          forecast forward Sharpe, search the optimal rebalance policy, and
          benchmark you against four reference factors. All computation runs
          locally in your browser.
        </p>
      </header>

      {/* Upload */}
      {!strategy && (
        <section className="mb-12">
          <UploadZone onLoaded={setStrategy} />
          <div className="note mt-6">
            <strong>Privacy.</strong> Your CSV is parsed entirely in this tab. Nothing
            leaves your machine — there is no upload endpoint, no telemetry, no logs.
          </div>
        </section>
      )}

      {/* Loaded strategy header + actions */}
      {strategy && (
        <section className="mb-8 flex flex-wrap items-baseline justify-between gap-4 pb-4 border-b border-[var(--rule)]">
          <div>
            <div className="kicker">strategy</div>
            <div className="font-serif text-2xl">{strategy.name}</div>
            <div className="text-sm text-[var(--muted)] tabular">
              {strategy.meta.rows} daily rows · {strategy.meta.startDate} → {strategy.meta.endDate}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button className="btn" onClick={() => setShowParams((s) => !s)}>
              {showParams ? "hide parameters" : "edit parameters"}
            </button>
            {result && (
              <>
                <button className="btn" onClick={() => downloadFile(`${strategy.name}_curve.csv`, curveToCsv(result), "text/csv")}>
                  download curve.csv
                </button>
                <button className="btn" onClick={() => downloadFile(`${strategy.name}_memo.md`, memoMarkdown(result), "text/markdown")}>
                  download memo.md
                </button>
              </>
            )}
            <button className="btn" onClick={() => setStrategy(null)}>
              clear
            </button>
          </div>
        </section>
      )}

      {/* Parameters */}
      {strategy && showParams && (
        <section className="mb-12">
          <h2 className="font-serif text-2xl mb-3">Cost parameters</h2>
          <p className="text-[var(--muted)] mb-4 max-w-prose text-sm">
            These tune the cost model. Defaults are calibrated to a NSE-listed
            mid-cap L/S sleeve. Overwrite any field to match your own broker
            terms; the curves redraw immediately.
          </p>
          <CostParamsForm value={costs} onChange={setCosts} />
        </section>
      )}

      {/* Results */}
      {strategy && result && (
        <>
          <StrategyResults r={result} />

          <hr className="divider" />
          <h3 className="font-serif text-2xl mb-2">Rolling Sharpe + 6-month forecast</h3>
          <p className="text-[var(--muted)] mb-4 max-w-prose text-sm">
            Trailing 1-year Sharpe (solid line) extended by the OU
            mean-reversion projection (dashed) with a ±1σ fan. The vertical mark
            is &quot;today&quot; — left of it is realised, right is the model&apos;s expectation.
          </p>
          <WhatIfWrapper>
            <RollingSharpe returns={strategy.returns} forecast={result.forecast.series} />
          </WhatIfWrapper>

          <hr className="divider" />
          <h3 className="font-serif text-2xl mb-2">Drawdown profile</h3>
          <p className="text-[var(--muted)] mb-4 max-w-prose text-sm">
            Underwater curve and the five deepest drawdowns. Length is the
            peak-to-trough span; recovery is the time from the trough back to a
            new equity high. Long recoveries imply high real-world tail risk
            even when the average Sharpe looks fine.
          </p>
          <WhatIfWrapper>
            <DrawdownAnalyzer returns={strategy.returns} drawdowns={result.stats.drawdowns} />
          </WhatIfWrapper>

          <hr className="divider" />
          <h3 className="font-serif text-2xl mb-2">What-if calculator</h3>
          <p className="text-[var(--muted)] mb-4 max-w-prose text-sm">
            Pick a target AUM. The capacity model recomputes immediately, so
            you can size up to your safe cap and see exactly which cost
            component eats the IR first.
          </p>
          <WhatIfWrapper>
            <WhatIfPanel returns={strategy.returns} costs={costs} safeCap={result.safeCapacity} />
          </WhatIfWrapper>

          <hr className="divider" />
          <h3 className="font-serif text-2xl mb-2">Sensitivity to cost assumptions</h3>
          <p className="text-[var(--muted)] mb-4 max-w-prose text-sm">
            Safe AUM under perturbations of impact coefficient (rows) and
            annual turnover (columns). If your safe AUM swings dramatically
            across the table, the headline number is fragile to the calibration
            you used.
          </p>
          <WhatIfWrapper>
            <SensitivityHeatmap returns={strategy.returns} costs={costs} />
          </WhatIfWrapper>

          <hr className="divider" />
          <h3 className="font-serif text-2xl mb-3">Benchmark vs reference factors</h3>
          <p className="text-[var(--muted)] mb-4 max-w-prose text-sm">
            Reference factors run on a synthetic NIFTY-100-like panel using the
            same cost model. Useful sanity check: a well-built sleeve should
            sit near or above the value/quality factors.
          </p>
          <BenchmarkPanel user={result} />
        </>
      )}
    </div>
  );
}
