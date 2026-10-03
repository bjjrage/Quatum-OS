export type NavTabId =
  // OVERVIEW
  | "command-center"
  // DATA
  | "recorder"
  | "data-quality"
  | "tradability"
  // RESEARCH
  | "strategy-registry"
  | "strategy-detail"
  | "str002-specialized"
  | "experiments"
  | "backtests"
  | "holdouts"
  // PORTFOLIO
  | "selection-gates"
  | "portfolio"
  | "regimes"
  | "attribution"
  // TRADING
  | "paper-trading"
  | "orders-fills"
  | "positions"
  | "execution"
  // RISK
  | "risk-engine"
  | "event-clusters"
  | "kill-switches"
  // CAPITAL
  | "capital-pockets"
  | "prop-firms"
  | "prop-simulator"
  | "multi-account"
  // SYSTEM
  | "audit-trail"
  | "tests-ci"
  | "configuration"
  | "blueprint";

export interface SystemStatus {
  status: string;
  environment: string;
  git_sha: string;
  git_sha_short: string;
  branch: string;
  live_capital_state: string;
  authorized_live_capital_usd: number;
  live_trading_locked: boolean;
  recorder_status: string;
  recorder_continuity: string;
  gate_24h: {
    status: string;
    elapsed_seconds: number;
    required_seconds: number;
    passed: boolean;
    reasons: string[];
  };
  gate_72h: {
    status: string;
    elapsed_seconds: number;
    required_seconds: number;
    passed: boolean;
    reasons: string[];
  };
  strategies_total: number;
  strategies_by_stage: Record<string, number>;
  total_experiments: number;
  failed_gates: number;
  risk_state: string;
  paper_pnl_usd: number;
  system_alerts: Array<{
    level: string;
    code: string;
    message: string;
  }>;
  last_heartbeat: string;
  ci_state: string;
  tests_passing: number;
  tests_failing: number;
}

export interface VenueInfo {
  venue: string;
  connected: boolean;
  last_event_timestamp?: string | null;
  total_events: number;
  event_rate: number;
  lag_ms?: number;
  clock_skew_detected?: boolean;
  clock_skew_ms?: number;
  files_written?: number;
  manifest_health?: string;
  dropped_or_invalid_events?: number;
  storage_size_bytes?: number;
  unique_symbols_count?: number;
  status?: string;
  notes?: string;
}

export interface RecorderStatus {
  run_id?: string;
  git_sha?: string;
  pid?: number;
  is_process_alive?: boolean;
  started_at_utc?: string;
  heartbeat_at_utc?: string;
  config_fingerprint?: string;
  status: string;
  continuity_state: string;
  continuity_reason?: string;
  elapsed_seconds: number;
  elapsed_formatted?: string;
  progress_24h_pct: number;
  progress_72h_pct: number;
  gate_24h_status: string;
  gate_72h_status: string;
  venues: Record<string, VenueInfo>;
}

export interface DataQuality {
  status: string;
  report_metadata?: {
    generated_at_utc: string;
    overall_state: string;
    observational_notes: string[];
  };
  run_metadata?: {
    run_id: string;
    git_sha: string;
    config_fingerprint: string;
    started_at_utc: string;
    venues_configured: string[];
  };
  runtime_health?: {
    pid: number;
    is_process_alive: boolean;
    rss_ram_mb: number;
    cpu_percent: number;
    elapsed_seconds: number;
    elapsed_formatted: string;
  };
  storage_metrics?: {
    parquet_file_count: number;
    total_compressed_bytes: number;
    total_row_count: number;
    bytes_per_event: number;
    projected_gb_per_day: number;
    orphan_tmp_files: number;
    manifest_valid: boolean;
    manifest_errors: string[];
  };
  timestamp_integrity?: {
    negative_event_age_count: number;
    total_events_checked: number;
    latency_p50_ms: number;
    latency_p95_ms: number;
    latency_p99_ms: number;
    estimated_clock_offset_ms: number;
    is_host_clock_skew_detected: boolean;
    corrected_latency_p50_ms: number;
    corrected_latency_p95_ms: number;
    corrected_latency_p99_ms: number;
    true_causal_violations: number;
  };
  venue_feeds?: Record<string, any>;
  history?: Array<{
    filename: string;
    generated_at_utc: string;
    total_events: number;
    files_count: number;
    orphan_tmp_files: number;
    manifest_valid: boolean;
    clock_offset_ms: number;
    corrected_p50_ms: number;
    corrected_p95_ms: number;
    corrected_p99_ms: number;
  }>;
}

export interface TradabilityMarket {
  symbol: string;
  venue: string;
  tier_code: number;
  tier_name: string;
  tradable: boolean;
  spread_bps: number;
  depth_0_5pct_usd: number;
  volume_5m_usd: number;
  oi_usd?: number | null;
  rv_5m?: number | null;
  clock_sync_offset_ms: number;
  manifest_valid: boolean;
  max_position_usd?: number | null;
  limit_orders_only: boolean;
  rejection_reasons: string[];
  evaluated_at_ns: number;
}

export interface StrategySummary {
  strategy_id: string;
  name: string;
  family: string;
  origin: string;
  stage: string;
  description: string;
  version: string;
  display_name: string;
  is_privileged: boolean;
  math_foundation_validated: boolean;
  economic_edge_validated: boolean;
  economic_edge_status: string;
  trial_count: number;
  counterparty_thesis_status: string;
  rules_count: number;
  paper_eligibility: boolean;
  live_eligibility: boolean;
  execution_mode: string;
}

export interface StrategyDetail extends StrategySummary {
  metadata: Record<string, any>;
  counterparty_thesis?: {
    counterparty_type: string;
    economic_mechanism: string;
    why_trade_now: string;
    why_impact_may_be_transient: string;
    why_it_may_be_information: string;
    observable_evidence: string[];
    falsification_conditions: string[];
    evidence_status: string;
    is_complete_for_validation: boolean;
  } | null;
  rules_evidence: Array<{
    rule_id: string;
    strategy_id: string;
    description: string;
    status: string;
    experiment_ids: string[];
    strategy_version: string;
    first_proposed_at: string;
    last_validated_at?: string | null;
    notes: string;
  }>;
  parameters: Record<string, any>;
}

export interface Str002Specialized {
  strategy_id: string;
  version: string;
  display_name: string;
  execution_mode: string;
  short_side: string;
  economic_edge_status: string;
  math_foundation_status: string;
  model_variants: Array<{
    variant_id: string;
    name: string;
    description: string;
    factor_model: string;
    btc_conditioning: boolean;
    reversal_filter: boolean;
    status: string;
  }>;
  btc_decision_matrix: Array<{
    state: string;
    horizon_1m: string;
    horizon_5m: string;
    decision: string;
    sizing: string;
    action: string;
  }>;
  live_factor_state: {
    beta_down: number | null;
    beta_up: number | null;
    gamma_eth: number | null;
    residual_z_score: number | null;
    reversal_detector: string | null;
    pre_shock_vwap: number | null;
    reference_price: number | null;
    mfe_usd: number | null;
    mae_usd: number | null;
    time_to_retracement_s: number | null;
    status: string;
    message: string;
  };
}

export interface ExperimentRecord {
  experiment_id: string;
  strategy_id: string;
  strategy_version: string;
  git_sha: string;
  dataset_fingerprint: string;
  config_fingerprint: string;
  feature_definition_hash: string;
  parameters: Record<string, any>;
  entry_model: string;
  exit_model: string;
  factor_model: string;
  regime_definition: string;
  universe_definition: string;
  cost_model_version: string;
  research_period: string;
  validation_period: string;
  holdout_period: string;
  random_seed: number;
  result_metrics: Record<string, any>;
  gate_result: string;
  created_at: string;
  falsification_evidence?: string | null;
  reasons: string[];
}

export interface GatePanel {
  gate_id: string;
  gate_name: string;
  gate_type: string;
  thresholds: Record<string, number>;
  threshold_is_provisional: boolean;
  evaluation_status: string;
  description: string;
  metrics_evaluated: string[];
}

export interface PortfolioAllocation {
  strategy_id: string;
  stage: string;
  base_budget_usd: number;
  allocated_capital_usd: number;
  allocation_pct: number;
  is_live_eligible: boolean;
  authorized_live_budget: number;
  paper_budget_usd: number;
  action: string;
  capacity_cap_usd: number;
  notes: string;
}

export interface PortfolioState {
  total_portfolio_equity_usd: number;
  live_capital_state: string;
  authorized_live_capital_usd: number;
  allocations: PortfolioAllocation[];
  event_cluster_exposures: Record<
    string,
    {
      gross_usd: number;
      net_usd: number;
      cap_usd: number;
      utilization_pct: number;
    }
  >;
}

export interface PaperAccount {
  initial_cash_usd: number;
  cash_usd: number;
  equity_usd: number;
  realized_pnl_usd: number;
  unrealized_pnl_usd: number;
  simulated_latency_ms: number;
  maker_fee_bps: number;
  taker_fee_bps: number;
  base_slippage_bps: number;
  positions: Array<{
    symbol: string;
    quantity: number;
    average_entry_price: number;
    realized_pnl_usd: number;
  }>;
  orders: Array<{
    order_id: string;
    symbol: string;
    venue: string;
    side: string;
    order_type: string;
    quantity: number;
    limit_price?: number | null;
    status: string;
    submitted_at_ns: number;
    filled_qty: number;
    filled_price?: number | null;
    fee_paid: number;
    slippage_usd: number;
    is_taker: boolean;
  }>;
  fills: Array<{
    trade_id: string;
    order_id: string;
    symbol: string;
    venue: string;
    side: string;
    price: number;
    quantity: number;
    fee: number;
    slippage_usd: number;
    timestamp_ns: number;
    is_taker: boolean;
  }>;
}

export interface CapitalPocketData {
  pocket_id: string;
  pocket_type: string;
  firm_name?: string | null;
  account_id: string;
  initial_equity_usd: number;
  current_equity_usd: number;
  peak_equity_usd: number;
  daily_starting_equity_usd: number;
  daily_loss_limit_pct: number;
  trailing_drawdown_limit_pct: number;
  is_frozen: boolean;
  freeze_reason?: string | null;
}

export interface PropRuleProfileData {
  provider_id: string;
  firm_name?: string | null;
  version: string;
  effective_date: string;
  verified_at?: string | null;
  evaluation_execution: string;
  funded_execution: string;
  payout_type: string;
  daily_loss_mode: string;
  daily_loss_limit_pct: number;
  trailing_max_drawdown_pct: number;
  max_total_loss_pct: number;
  profit_target_pct: number;
  min_trading_days: number;
  venue: string;
  api_bot_policy: string;
  tick_scalping_policy: string;
  minimum_holding_policy: string;
  news_trading_policy: string;
  weekend_policy: string;
  multi_account_policy: string;
  copy_trading_policy: string;
  hedging_policy: string;
  country_eligibility: string[];
  verification_status: string;
  verified_by?: string | null;
}
