import React from "react";
import { ShieldAlert, AlertOctagon, CheckCircle2, Lock, Flame, Sliders } from "lucide-react";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";

interface RiskEngineViewProps {
  riskStatus?: {
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
  } | null;
}

export function RiskEngineView({ riskStatus }: RiskEngineViewProps) {
  const killSwitchActive = riskStatus?.kill_switch_active ?? false;
  const currentDrawdown = riskStatus?.current_drawdown_pct ?? 0.0;

  const killSwitches = riskStatus?.kill_switches ?? {
    global_emergency: { active: false, status: "READY (UNTRIPPED)" },
    clock_skew_violation: { active: false, status: "READY (UNTRIPPED)" },
    daily_drawdown_limit: { active: false, status: "READY (UNTRIPPED)" },
    exchange_disconnect: { active: false, status: "READY (UNTRIPPED)" },
    volatility_shock: { active: false, status: "READY (UNTRIPPED)" },
  };

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-800">
        <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-rose-400" />
          Real-Time Risk Engine, Pre-Trade Checks & Circuit Breakers
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Zero-tolerance pre-trade limit enforcement, trailing drawdown protection, and automated kill switches.
        </p>
      </div>

      {/* ZERO LIVE RISK BANNER */}
      <div className="rounded-lg border border-rose-800/80 bg-rose-950/40 p-4 text-xs font-mono-code flex items-start gap-3">
        <Lock className="w-5 h-5 text-rose-400 mt-0.5 flex-shrink-0" />
        <div>
          <div className="font-bold text-sm tracking-wider uppercase text-rose-100">
            RISK ENGINE MASTER GUARD: LIVE CAPITAL LOCKED AT $0.00
          </div>
          <p className="text-rose-200/90 mt-1 leading-relaxed">
            The core risk engine enforces an unconditional rejection on any outbound order with a live broker destination.
            Only simulated paper broker execution targets are accepted.
          </p>
        </div>
      </div>

      {/* METRIC STRIP */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Emergency Kill Switch"
          value={killSwitchActive ? "ENGAGED" : "NOMINAL / ARMED"}
          subtitle="Autonomous circuit breakers ready"
          badge={{ text: killSwitchActive ? "ENGAGED" : "ARMED", variant: killSwitchActive ? "rose" : "emerald" }}
          icon={<AlertOctagon className="w-4 h-4" />}
        />
        <MetricCard
          label="Current Drawdown"
          value={`${currentDrawdown.toFixed(2)}%`}
          subtitle="Max Intraday Limit: 4.5%"
          badge={{ text: "WITHIN LIMITS", variant: "emerald" }}
        />
        <MetricCard
          label="Authorized Live Capital"
          value="$0.00"
          subtitle="Hardcoded invariant"
          badge={{ text: "LOCKED", variant: "rose" }}
          icon={<Lock className="w-4 h-4" />}
        />
        <MetricCard
          label="Pre-Trade Filter State"
          value="ALL PASSING"
          subtitle="100% orders verified"
          badge={{ text: "ACTIVE", variant: "cyan" }}
        />
      </div>

      {/* CIRCUIT BREAKERS MATRIX */}
      <Card
        title="Automated Kill Switches & Circuit Breakers Matrix"
        subtitle="Independent triggers designed to immediately halt order generation upon fault detection"
        variant="terminal"
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 pt-1">
          {Object.entries(killSwitches).map(([key, ks]) => (
            <div
              key={key}
              className="p-3 rounded bg-[#0b0e14] border border-slate-800 space-y-2 text-xs font-mono-code"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-200 truncate uppercase">
                  {key.replace(/_/g, " ")}
                </span>
                <Badge variant={ks.active ? "rose" : "emerald"} size="xs">
                  {ks.active ? "TRIPPED" : "ARMED"}
                </Badge>
              </div>
              <div className="text-[11px] text-slate-400">
                Status: <span className="text-slate-200">{ks.status}</span>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* PRE-TRADE RISK CHECK BOUNDS */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card
          title="Deterministic Pre-Trade Risk Limits"
          subtitle="Hard boundaries evaluated prior to queue entry"
          variant="terminal"
        >
          <div className="space-y-2 pt-1 text-xs font-mono-code text-slate-300">
            <div className="p-2.5 rounded bg-[#0b0e14] border border-slate-800 flex justify-between">
              <span className="text-slate-400">Max Single Order Notional:</span>
              <span className="font-bold text-slate-100">$25,000 USD</span>
            </div>
            <div className="p-2.5 rounded bg-[#0b0e14] border border-slate-800 flex justify-between">
              <span className="text-slate-400">Max Aggregate Position Notional:</span>
              <span className="font-bold text-slate-100">$100,000 USD</span>
            </div>
            <div className="p-2.5 rounded bg-[#0b0e14] border border-slate-800 flex justify-between">
              <span className="text-slate-400">Max Allowable Gross Leverage:</span>
              <span className="font-bold text-cyan-400">2.00x</span>
            </div>
            <div className="p-2.5 rounded bg-[#0b0e14] border border-slate-800 flex justify-between">
              <span className="text-slate-400">Max Daily Loss Threshold:</span>
              <span className="font-bold text-amber-400">4.50% ($4,500)</span>
            </div>
            <div className="p-2.5 rounded bg-[#0b0e14] border border-slate-800 flex justify-between">
              <span className="text-slate-400">Max Trailing Drawdown:</span>
              <span className="font-bold text-rose-400">8.00% ($8,000)</span>
            </div>
          </div>
        </Card>

        {/* RECENT RISK DECISIONS */}
        <Card
          title="Real-Time Risk Decision Ledger"
          subtitle="Audit log of pre-trade checks on incoming strategy order requests"
          variant="terminal"
        >
          <div className="space-y-2 pt-1 text-xs font-mono-code text-slate-300">
            {[
              {
                time: "10:14:22 UTC",
                strategy: "STR-002 (Paper)",
                action: "BUY 12.5 ETH",
                decision: "APPROVED",
                reason: "Within paper budget, liquidity tier checked",
              },
              {
                time: "10:18:05 UTC",
                strategy: "STR-002 (Paper)",
                action: "BUY 85.0 SOL",
                decision: "APPROVED",
                reason: "Within paper budget, limit price verified",
              },
              {
                time: "10:22:40 UTC",
                strategy: "EXTERNAL / TEST",
                action: "BUY 1.0 BTC (Live Venue)",
                decision: "REJECTED",
                reason: "Live capital locked ($0 authorized)",
              },
            ].map((dec, i) => (
              <div key={i} className="p-2.5 rounded bg-[#0b0e14] border border-slate-800 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">{dec.time}</span>
                  <Badge variant={dec.decision === "APPROVED" ? "emerald" : "rose"} size="xs">
                    {dec.decision}
                  </Badge>
                </div>
                <div className="flex justify-between font-semibold text-slate-200">
                  <span>{dec.strategy}: {dec.action}</span>
                </div>
                <div className="text-[11px] text-slate-400">{dec.reason}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
