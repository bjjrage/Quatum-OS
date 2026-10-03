import React from "react";
import { Landmark, Lock, ShieldCheck, AlertCircle, DollarSign, Wallet } from "lucide-react";
import { CapitalPocketData } from "../../types";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";

interface CapitalPocketsViewProps {
  pocketsData?: {
    isolation_invariant: string;
    pockets: CapitalPocketData[];
  };
}

export function CapitalPocketsView({ pocketsData }: CapitalPocketsViewProps) {
  const pockets: CapitalPocketData[] = pocketsData?.pockets && pocketsData.pockets.length > 0
    ? pocketsData.pockets
    : [
        {
          pocket_id: "POCKET-A-PROP-01",
          pocket_type: "PROP_ALLOCATION",
          firm_name: "AlphaFunding Evaluator",
          account_id: "PROP-EVAL-8821",
          initial_equity_usd: 100000,
          current_equity_usd: 100000,
          peak_equity_usd: 100000,
          daily_starting_equity_usd: 100000,
          daily_loss_limit_pct: 5.0,
          trailing_drawdown_limit_pct: 10.0,
          is_frozen: false,
          freeze_reason: null,
        },
        {
          pocket_id: "POCKET-B-LIVE-ZERO",
          pocket_type: "LIVE_CAPITAL_ZERO",
          firm_name: "Internal Live Exchange",
          account_id: "LIVE-PRIMARY-NULL",
          initial_equity_usd: 0,
          current_equity_usd: 0,
          peak_equity_usd: 0,
          daily_starting_equity_usd: 0,
          daily_loss_limit_pct: 0.0,
          trailing_drawdown_limit_pct: 0.0,
          is_frozen: true,
          freeze_reason: "ZERO_CAPITAL_INVARIANT: Live trading permanently locked at $0.00",
        },
        {
          pocket_id: "POCKET-C-RESEARCH",
          pocket_type: "RESEARCH_SANDBOX",
          firm_name: "Quant OS Research Desk",
          account_id: "SANDBOX-001",
          initial_equity_usd: 50000,
          current_equity_usd: 50000,
          peak_equity_usd: 50000,
          daily_starting_equity_usd: 50000,
          daily_loss_limit_pct: 10.0,
          trailing_drawdown_limit_pct: 15.0,
          is_frozen: false,
          freeze_reason: null,
        },
      ];

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-800">
        <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
          <Landmark className="w-5 h-5 text-cyan-400" />
          Capital Pockets & Multi-Account Isolation Architecture
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Cryptographically isolated balance containers preventing contagion between research, prop firm evaluation, and live vaults.
        </p>
      </div>

      {/* ISOLATION INVARIANT BANNER */}
      <div className="rounded-lg border border-cyan-800/80 bg-[#0d1624] p-4 text-xs font-mono-code space-y-1">
        <div className="flex items-center gap-2 text-cyan-300 font-bold uppercase">
          <ShieldCheck className="w-4 h-4" />
          Capital Pocket Isolation Invariant
        </div>
        <p className="text-slate-300 leading-relaxed">
          {pocketsData?.isolation_invariant ||
            "Pockets are partitioned with strict firewalls. No pocket may borrow balance or absorb drawdowns from another pocket. Pocket B (Live Capital) is permanently locked at $0.00."}
        </p>
      </div>

      {/* METRIC STRIP */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <MetricCard
          label="Total Isolated Pockets"
          value={`${pockets.length} Pockets`}
          subtitle="Prop, Live Guard, Sandbox"
          badge={{ text: "PARTITIONED", variant: "cyan" }}
          icon={<Wallet className="w-4 h-4" />}
        />
        <MetricCard
          label="Live Capital Pocket B"
          value="$0.00 (LOCKED)"
          subtitle="Zero live capital invariant"
          badge={{ text: "FROZEN", variant: "rose" }}
          icon={<Lock className="w-4 h-4" />}
        />
        <MetricCard
          label="Simulated Balances"
          value="$150,000 USD"
          subtitle="Pocket A ($100k) + Pocket C ($50k)"
          badge={{ text: "SIMULATED", variant: "emerald" }}
          icon={<DollarSign className="w-4 h-4" />}
        />
      </div>

      {/* POCKETS CARDS */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {pockets.map((p) => {
          const isLiveZero = p.pocket_type === "LIVE_CAPITAL_ZERO" || p.pocket_id.includes("LIVE");

          return (
            <Card
              key={p.pocket_id}
              variant={isLiveZero ? "danger" : "terminal"}
              className="space-y-4"
            >
              {/* Header */}
              <div className="flex items-start justify-between border-b border-slate-800 pb-3">
                <div>
                  <span className="text-xs font-bold text-slate-100 font-mono-code block">
                    {p.pocket_id}
                  </span>
                  <span className="text-[11px] text-slate-400 font-mono-code mt-0.5 block">
                    {p.firm_name || p.account_id}
                  </span>
                </div>
                <Badge variant={p.is_frozen ? "rose" : "emerald"} size="xs">
                  {p.is_frozen ? "FROZEN / LOCKED" : "ACTIVE"}
                </Badge>
              </div>

              {/* Balances */}
              <div className="p-3 rounded bg-[#0b0e14] border border-slate-800 space-y-2 text-xs font-mono-code">
                <div className="flex justify-between">
                  <span className="text-slate-400">Current Equity:</span>
                  <span className={`font-bold ${isLiveZero ? "text-rose-400" : "text-slate-100"}`}>
                    ${p.current_equity_usd?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Initial Equity:</span>
                  <span className="text-slate-200">
                    ${p.initial_equity_usd?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Daily Loss Limit:</span>
                  <span className="text-amber-400">{p.daily_loss_limit_pct}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Trailing DD Limit:</span>
                  <span className="text-rose-400">{p.trailing_drawdown_limit_pct}%</span>
                </div>
              </div>

              {/* Freeze Reason */}
              {p.freeze_reason ? (
                <div className="p-2.5 rounded bg-rose-950/30 border border-rose-900/50 text-[11px] font-mono-code text-rose-300">
                  <span className="font-bold block mb-0.5">Freeze Invariant:</span>
                  {p.freeze_reason}
                </div>
              ) : (
                <div className="p-2.5 rounded bg-emerald-950/20 border border-emerald-900/40 text-[11px] font-mono-code text-emerald-300">
                  Isolation Status: Operational (No breach detected)
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
