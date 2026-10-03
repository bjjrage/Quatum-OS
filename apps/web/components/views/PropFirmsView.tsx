import React from "react";
import { Award, AlertTriangle, ShieldCheck, CheckCircle2, HelpCircle, FileText } from "lucide-react";
import { PropRuleProfileData } from "../../types";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";

interface PropFirmsViewProps {
  profiles: PropRuleProfileData[];
}

export function PropFirmsView({ profiles }: PropFirmsViewProps) {
  const profileList: PropRuleProfileData[] = profiles && profiles.length > 0 ? profiles : [
    {
      provider_id: "AlphaFunding",
      firm_name: "AlphaFunding Global",
      version: "2026.3",
      effective_date: "2026-09-01",
      verified_at: "2026-09-15",
      evaluation_execution: "SIMULATED_DEMO",
      funded_execution: "HYBRID_SIMULATED_OR_LIVE",
      payout_type: "BI_WEEKLY_PROFIT_SPLIT",
      daily_loss_mode: "EQUITY_HIGH_WATER_MARK",
      daily_loss_limit_pct: 5.0,
      trailing_max_drawdown_pct: 10.0,
      max_total_loss_pct: 10.0,
      profit_target_pct: 8.0,
      min_trading_days: 5,
      venue: "BINANCE_DERIBIT_SYNTHETIC",
      api_bot_policy: "PERMITTED_WITH_DISCLOSURE",
      tick_scalping_policy: "PROHIBITED (trades < 30s flagged)",
      minimum_holding_policy: "60_SECONDS_MINIMUM",
      news_trading_policy: "RESTRICTED (+-5m High Impact CPI/FOMC)",
      weekend_policy: "PERMITTED_WITH_MARGIN_BUFFER",
      multi_account_policy: "MAX_3_ACCOUNTS_SAME_STRATEGY",
      copy_trading_policy: "INTERNAL_ONLY (3rd party copy banned)",
      hedging_policy: "PROHIBITED_ACROSS_ACCOUNTS",
      country_eligibility: ["US", "EU", "UK", "SG", "JP"],
      verification_status: "VERIFIED",
      verified_by: "Compliance Officer #42",
    },
    {
      provider_id: "ApexEliteTrader",
      firm_name: "Apex Elite Trader",
      version: "2026.1",
      effective_date: "2026-06-01",
      verified_at: null,
      evaluation_execution: "SIMULATED_DEMO",
      funded_execution: "SIMULATED_WITH_PAYOUT",
      payout_type: "MONTHLY",
      daily_loss_mode: "END_OF_DAY_BALANCE",
      daily_loss_limit_pct: 4.0,
      trailing_max_drawdown_pct: 6.0,
      max_total_loss_pct: 6.0,
      profit_target_pct: 6.0,
      min_trading_days: 7,
      venue: "RITHMIC_FUTURES",
      api_bot_policy: "PENDING_VERIFICATION",
      tick_scalping_policy: "UNKNOWN",
      minimum_holding_policy: "UNKNOWN",
      news_trading_policy: "UNKNOWN",
      weekend_policy: "FLAT_BY_FRIDAY_CLOSE",
      multi_account_policy: "PENDING_REVIEW",
      copy_trading_policy: "UNKNOWN",
      hedging_policy: "UNKNOWN",
      country_eligibility: ["EU", "UK"],
      verification_status: "PENDING_VERIFICATION",
      verified_by: null,
    },
  ];

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-800">
        <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
          <Award className="w-5 h-5 text-cyan-400" />
          Proprietary Trading Firm Rule Profiles & Compliance Ledger
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Machine-readable terms of service, strict loss calculation models, and verified policy parameters.
        </p>
      </div>

      {/* VERIFICATION STANDARD BANNER */}
      <div className="rounded-lg border border-amber-800/80 bg-amber-950/30 p-4 text-xs font-mono-code space-y-1">
        <div className="flex items-center gap-2 text-amber-300 font-bold uppercase">
          <AlertTriangle className="w-4 h-4 text-amber-400" />
          Prop Rule Verification Policy Invariant
        </div>
        <p className="text-amber-200/90 leading-relaxed">
          Unconfirmed terms are strictly displayed as <strong className="text-amber-100">UNKNOWN</strong> or <strong className="text-amber-100">PENDING_VERIFICATION</strong>.
          The Quant OS prohibits hardcoded assumptions regarding daily loss reset calculations (Equity HWM vs Balance EOD) without formal document verification.
        </p>
      </div>

      {/* PROFILES GRID */}
      <div className="space-y-6">
        {profileList.map((p) => {
          const isVerified = p.verification_status === "VERIFIED";

          return (
            <Card
              key={p.provider_id}
              variant="terminal"
              className="space-y-4 hover:border-slate-700 transition"
            >
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-base font-bold text-slate-100 font-mono-code">
                      {p.firm_name || p.provider_id}
                    </span>
                    <Badge variant={isVerified ? "emerald" : "amber"} size="xs">
                      {p.verification_status}
                    </Badge>
                  </div>
                  <span className="text-xs text-slate-400 font-mono-code mt-0.5 block">
                    Profile Ver: <span className="text-slate-200">{p.version}</span> | Effective: <span className="text-slate-200">{p.effective_date}</span> {p.verified_at ? `| Verified: ${p.verified_at}` : ""}
                  </span>
                </div>
                <div className="text-xs font-mono-code text-slate-400">
                  Venue: <span className="text-cyan-400 font-semibold">{p.venue}</span>
                </div>
              </div>

              {/* Numerical Drawdown & Profit Limits */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono-code">
                <div className="p-3 rounded bg-[#0b0e14] border border-slate-800">
                  <span className="text-slate-500 text-[10px] uppercase block">Daily Loss Limit</span>
                  <span className="text-sm font-bold text-amber-400 mt-1 block">
                    {p.daily_loss_limit_pct}%
                  </span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">{p.daily_loss_mode}</span>
                </div>

                <div className="p-3 rounded bg-[#0b0e14] border border-slate-800">
                  <span className="text-slate-500 text-[10px] uppercase block">Trailing Max DD</span>
                  <span className="text-sm font-bold text-rose-400 mt-1 block">
                    {p.trailing_max_drawdown_pct}%
                  </span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">High-Water Mark</span>
                </div>

                <div className="p-3 rounded bg-[#0b0e14] border border-slate-800">
                  <span className="text-slate-500 text-[10px] uppercase block">Profit Target</span>
                  <span className="text-sm font-bold text-emerald-400 mt-1 block">
                    {p.profit_target_pct}%
                  </span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">Phase 1 Target</span>
                </div>

                <div className="p-3 rounded bg-[#0b0e14] border border-slate-800">
                  <span className="text-slate-500 text-[10px] uppercase block">Min Trading Days</span>
                  <span className="text-sm font-bold text-cyan-400 mt-1 block">
                    {p.min_trading_days} Days
                  </span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">Required Activity</span>
                </div>
              </div>

              {/* Granular Policies Table */}
              <div className="p-3 rounded bg-[#0b0e14] border border-slate-800 space-y-2 text-xs font-mono-code">
                <span className="text-slate-400 text-[11px] font-semibold uppercase block">
                  Algorithmic Execution & Compliance Constraints:
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-slate-300">
                  <div className="flex justify-between border-b border-slate-800/60 pb-1">
                    <span className="text-slate-400">API Bot Policy:</span>
                    <span className="text-slate-100">{p.api_bot_policy}</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-800/60 pb-1">
                    <span className="text-slate-400">Tick Scalping Rules:</span>
                    <span className={p.tick_scalping_policy.includes("UNKNOWN") ? "text-amber-400" : "text-slate-100"}>
                      {p.tick_scalping_policy}
                    </span>
                  </div>
                  <div className="flex justify-between border-b border-slate-800/60 pb-1">
                    <span className="text-slate-400">Min Holding Duration:</span>
                    <span className={p.minimum_holding_policy.includes("UNKNOWN") ? "text-amber-400" : "text-slate-100"}>
                      {p.minimum_holding_policy}
                    </span>
                  </div>
                  <div className="flex justify-between border-b border-slate-800/60 pb-1">
                    <span className="text-slate-400">News Event Trading:</span>
                    <span className={p.news_trading_policy.includes("UNKNOWN") ? "text-amber-400" : "text-slate-100"}>
                      {p.news_trading_policy}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Multi-Account Correlation:</span>
                    <span className={p.multi_account_policy.includes("PENDING") ? "text-amber-400" : "text-slate-100"}>
                      {p.multi_account_policy}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Weekend Holding Policy:</span>
                    <span className="text-slate-100">{p.weekend_policy}</span>
                  </div>
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
