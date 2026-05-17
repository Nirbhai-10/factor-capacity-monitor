export type Meta = {
  currency: string;
  unit_label: string;
  unit_value: number;
  rebalance_freq: string;
  history_years: number;
  n_symbols: number;
  factors: string[];
};

export type CurvePoint = {
  aum: number;
  gross_ir: number;
  net_ir: number;
  gross_return_ann: number;
  net_return_ann: number;
  total_cost_bps: number;
  spread_bps: number;
  impact_bps: number;
  commission_bps: number;
  borrow_bps: number;
  india_bps: number;
  max_exec_days: number;
  max_participation: number;
  zone: "safe" | "caution" | "red";
};

export type PolicyRow = {
  freq: string;
  buffer_bps: number;
  gross_ir: number;
  net_ir: number;
  total_cost_bps: number;
  max_exec_days: number;
  max_participation: number;
};

export type Checkpoint = { pct_of_safe: number; aum: number; rule: string };

export type CrowdComponent = {
  date: string;
  valuation_spread: number;
  alpha_decay: number;
  short_interest: number;
  comomentum: number;
  holdings_overlap: number;
  internal_footprint: number;
};

export type SeriesPoint = { date: string; value: number | null };

export type FactorBundle = {
  name: string;
  gross_ir: number;
  safe_capacity: number | null;
  ir50_capacity: number | null;
  stress_safe_capacity: number | null;
  crowding_latest: number;
  alert_level: "green" | "amber" | "red";
  crowding_components_latest: Record<string, number>;
  best_policy: { freq: string; buffer_bps: number; net_ir: number; target_aum: number };
  policy_grid: PolicyRow[];
  checkpoints: Checkpoint[];
  curve: CurvePoint[];
  stress_curve: CurvePoint[];
  redemption_unwind: { aum: number; unwind_bps: number }[];
  crowding_components: CrowdComponent[];
  crowding_composite: SeriesPoint[];
  ml_forecast: {
    fitted_kappa: number;
    fitted_alpha: number;
    fitted_beta: number;
    half_life_days: number;
    rmse: number;
    forecast: SeriesPoint[];
    fan_lower: SeriesPoint[];
    fan_upper: SeriesPoint[];
  };
  daily_returns: SeriesPoint[];
};

export type Payload = {
  meta: Meta;
  regime: {
    current: "calm" | "normal" | "stressed";
    probabilities: Record<string, number>;
    centroids: Record<string, Record<string, number>>;
    history: Array<Record<string, number | string>>;
  };
  factors: Record<string, FactorBundle>;
  multi_factor: {
    weights: Record<string, number>;
    aum_allocations: Record<string, number>;
    expected_net_return_pct: number;
    expected_net_return_dollars: number;
    factor_irs: Record<string, number>;
    total_aum: number;
  };
  ml: {
    capacity_model: {
      coefficients: Record<string, number>;
      intercept: number;
      lambda: number;
      r2: number;
      feature_names: string[];
    };
  };
};
