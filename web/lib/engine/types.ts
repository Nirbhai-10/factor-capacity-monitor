export type ReturnPoint = { date: string; ret: number };

export type Strategy = {
  name: string;
  returns: ReturnPoint[];          // daily decimal returns
  meta: {
    rows: number;
    startDate: string;
    endDate: string;
  };
};

export type CostParams = {
  /** annualised volatility used in impact (estimated from returns if missing) */
  sigmaAnnual: number;
  /** Almgren-Chriss coefficient. AQR fills imply 0.10–0.30 */
  impactCoefficient: number;
  /** strategy's typical bid-ask spread, bps */
  spreadBps: number;
  /** commission, bps per side */
  commissionBps: number;
  /** typical short-leg borrow, bps annualised */
  borrowBps: number;
  /** annual turnover (1.0 = 100% rotation/year) */
  annualTurnover: number;
  /** representative dollar ADV across the strategy's positions, ₹ */
  representativeAdv: number;
  /** participation cap per name per day (e.g. 0.05 = 5%) */
  participationCap: number;
  /** holding-period in trading days (used for round-trip amortisation) */
  holdingDays: number;
  /** include India NSE tax stack? */
  indiaTaxes: boolean;
  /** % of book that is short (for borrow cost). 0.5 for L/S equal-weight */
  shortBookFraction: number;
};

export type CapacityPoint = {
  aum: number;
  netIR: number;
  grossIR: number;
  totalCostBps: number;
  spreadBps: number;
  impactBps: number;
  commissionBps: number;
  borrowBps: number;
  taxBps: number;
  participation: number;
  zone: "safe" | "caution" | "red";
};

export type AnalysisResult = {
  strategy: Strategy;
  stats: {
    grossIR: number;
    sharpe: number;
    annualReturn: number;
    annualVol: number;
    maxDrawdown: number;
    winRate: number;
    bestDay: number;
    worstDay: number;
    drawdowns: import("./stats").Drawdown[];
  };
  curve: CapacityPoint[];
  safeCapacity: number | null;
  ir50Capacity: number | null;
  forecast: {
    kappa: number;
    halfLifeDays: number;
    fittedAlpha: number;
    series: { date: string; sharpe: number; lower: number; upper: number }[];
  };
  policy: {
    bestFreq: string;
    bestBufferBps: number;
    bestNetIR: number;
    grid: PolicyRow[];
  };
  regime: {
    label: "calm" | "normal" | "stressed";
    annVol: number;
    autocorr: number;
  };
  costParams: CostParams;
  computedAt: string;
};

export type PolicyRow = {
  freq: string;
  bufferBps: number;
  netIR: number;
  totalCostBps: number;
  turnover: number;
};
