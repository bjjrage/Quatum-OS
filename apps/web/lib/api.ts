import {
  SystemStatus,
  RecorderStatus,
  DataQuality,
  TradabilityMarket,
  StrategySummary,
  StrategyDetail,
  Str002Specialized,
  ExperimentRecord,
  GatePanel,
  PortfolioState,
  PaperAccount,
  CapitalPocketData,
  PropRuleProfileData,
} from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function fetchJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      console.warn(`[API] ${path} returned status ${res.status}`);
      return fallback;
    }
    return (await res.json()) as T;
  } catch (err) {
    console.warn(`[API] Failed fetching ${path}:`, err);
    return fallback;
  }
}

export const api = {
  getSystemStatus: () =>
    fetchJson<SystemStatus | null>("/api/system/status", null),

  getSystemGit: () =>
    fetchJson<{
      git_sha: string;
      git_sha_short: string;
      branch: string;
      recent_commits: Array<{ sha: string; message: string; author: string; date: string }>;
    } | null>("/api/system/git", null),

  getSystemCi: () =>
    fetchJson<{
      status: string;
      ci_provider: string;
      passing_tests: number;
      failing_tests: number;
      duration_seconds: number;
      github_actions_status: string;
      github_actions_reason: string;
    } | null>("/api/system/ci", null),

  getRecorderStatus: () =>
    fetchJson<RecorderStatus | null>("/api/recorder/status", null),

  getDataQuality: () =>
    fetchJson<DataQuality | null>("/api/data-quality", null),

  getMarketsTradability: () =>
    fetchJson<{
      status: string;
      policy: Record<string, any>;
      markets: TradabilityMarket[];
    } | null>("/api/markets/tradability", null),

  getStrategies: () =>
    fetchJson<StrategySummary[]>("/api/strategies", []),

  getStrategyDetail: (strategyId: string) =>
    fetchJson<StrategyDetail | null>(`/api/strategies/${strategyId}`, null),

  getStr002Specialized: () =>
    fetchJson<Str002Specialized | null>("/api/strategies/str002/specialized", null),

  getExperiments: () =>
    fetchJson<{
      status: string;
      total: number;
      strategy_trial_counts: Record<string, number>;
      experiments: ExperimentRecord[];
    }>("/api/experiments", { status: "LOADING", total: 0, strategy_trial_counts: {}, experiments: [] }),

  getHoldouts: () =>
    fetchJson<{
      status: string;
      warning: string;
      total_openings: number;
      audits: any[];
    }>("/api/holdouts", { status: "SEALED", warning: "HOLDOUT SEALED", total_openings: 0, audits: [] }),

  getGates: () =>
    fetchJson<{
      status: string;
      provenance_invariant: string;
      gates: GatePanel[];
    }>("/api/gates", { status: "PENDING", provenance_invariant: "", gates: [] }),

  getPortfolio: () =>
    fetchJson<PortfolioState | null>("/api/portfolio", null),

  getRegime: () =>
    fetchJson<{
      status: string;
      macro_regime: string;
      crypto_domain_regime: string;
      btc_trend_state: string;
      capital_allocation_multiplier: number;
      ai_metadata_advisory_state: string;
      notes: string;
    } | null>("/api/regime", null),

  getPaperAccount: () =>
    fetchJson<PaperAccount | null>("/api/paper/account", null),

  getExecutionStatus: () =>
    fetchJson<{
      execution_mode: string;
      live_execution_authority: boolean;
      live_capital_authorized: number;
      reconciliation_status: string;
      mismatch_detected: boolean;
      tracked_orders_count: number;
    } | null>("/api/execution/status", null),

  getRiskStatus: () =>
    fetchJson<{
      live_capital_state: string;
      authorized_live_capital_usd: number;
      kill_switch_active: boolean;
      kill_switch_reason: string | null;
      current_equity_usd: number;
      peak_equity_usd: number;
      current_drawdown_pct: number;
      limits: Record<string, any>;
      kill_switches: Record<string, { active: boolean; status: string }>;
      recent_decisions: any[];
    } | null>("/api/risk/status", null),

  getEventClusters: () =>
    fetchJson<any[]>("/api/event-clusters", []),

  getCapitalPockets: () =>
    fetchJson<{
      isolation_invariant: string;
      pockets: CapitalPocketData[];
    }>("/api/capital-pockets", { isolation_invariant: "", pockets: [] }),

  getPropProfiles: () =>
    fetchJson<PropRuleProfileData[]>("/api/prop/profiles", []),

  getPropSimulations: (strategyId = "STR-002", providerId = "AlphaFunding") =>
    fetchJson<any>(`/api/prop/simulations?strategy_id=${strategyId}&provider_id=${providerId}`, null),

  getMultiAccountCompliance: () =>
    fetchJson<any[]>("/api/prop/compliance", []),

  getAttribution: () =>
    fetchJson<any>("/api/attribution", null),

  getAuditTrail: () =>
    fetchJson<any[]>("/api/audit", []),
};
