import React from "react";
import { Compass, TrendingUp, AlertTriangle, Cpu, Sliders, ShieldCheck } from "lucide-react";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";

interface RegimesViewProps {
  regimeData?: {
    status: string;
    macro_regime: string;
    crypto_domain_regime: string;
    btc_trend_state: string;
    capital_allocation_multiplier: number;
    ai_metadata_advisory_state: string;
    notes: string;
  } | null;
}

export function RegimesView({ regimeData }: RegimesViewProps) {
  const data = regimeData ?? {
    status: "ACTIVE",
    macro_regime: "NEUTRAL_LIQUIDITY_EXPANSION",
    crypto_domain_regime: "HIGH_VOLATILITY_CHOP",
    btc_trend_state: "CONSOLIDATION_ABOVE_200EMA",
    capital_allocation_multiplier: 0.85,
    ai_metadata_advisory_state: "ADVISORY_ONLY (NON_EXECUTION)",
    notes: "AI and sentiment signals are strictly advisory and cannot bypass quantitative risk constraints.",
  };

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-800">
        <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
          <Compass className="w-5 h-5 text-cyan-400" />
          Market Regime Detection & Dynamic Sizing Conditioning
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Multi-layer classification combining macro liquidity, crypto domain volatility, and non-authoritative AI advisory signals.
        </p>
      </div>

      {/* AI ADVISORY SAFETY INVARIANT */}
      <div className="rounded-lg border border-purple-800/80 bg-purple-950/40 p-4 text-xs font-mono-code space-y-1">
        <div className="flex items-center gap-2 text-purple-300 font-bold uppercase">
          <Cpu className="w-4 h-4" />
          AI Metadata & Regime Advisory Guardrail
        </div>
        <p className="text-slate-300 leading-relaxed">
          AI metadata analysis, LLM market summaries, and external sentiment indicators are strictly <strong className="text-purple-200">ADVISORY ONLY</strong>.
          They possess zero direct execution authority, cannot submit orders, and cannot override mathematical risk gates or selection criteria.
        </p>
      </div>

      {/* METRIC ROW */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Macro Liquidity Regime"
          value={data.macro_regime.replace(/_/g, " ")}
          subtitle="Global liquidity impulse"
          badge={{ text: "EXPANSION", variant: "cyan" }}
          icon={<Compass className="w-4 h-4" />}
        />
        <MetricCard
          label="Crypto Domain Regime"
          value={data.crypto_domain_regime.replace(/_/g, " ")}
          subtitle="DVol & realized volatility"
          badge={{ text: "HIGH VOL", variant: "amber" }}
        />
        <MetricCard
          label="BTC Structural Trend"
          value={data.btc_trend_state.replace(/_/g, " ")}
          subtitle="Multi-timeframe trend filter"
          badge={{ text: "BULLISH BIAS", variant: "emerald" }}
        />
        <MetricCard
          label="Capital Multiplier"
          value={`${(data.capital_allocation_multiplier * 100).toFixed(0)}%`}
          subtitle="Macro risk budget scalar"
          badge={{ text: "0.85x SCALAR", variant: "blue" }}
          icon={<Sliders className="w-4 h-4" />}
        />
      </div>

      {/* REGIME MATRIX CARD */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card
          title="Regime Multiplier Breakdown"
          subtitle="Dynamic risk budget scaling by market environment"
          variant="terminal"
        >
          <div className="space-y-3 pt-1 text-xs font-mono-code text-slate-300">
            <div className="p-3 rounded bg-[#0b0e14] border border-slate-800 flex justify-between items-center">
              <div>
                <span className="font-bold text-slate-100 block">Bullish Trend / Low Vol</span>
                <span className="text-[11px] text-slate-400">Optimal environment for momentum & cascades</span>
              </div>
              <span className="text-emerald-400 font-bold">1.00x Allocation</span>
            </div>
            <div className="p-3 rounded bg-[#0b0e14] border border-slate-800 flex justify-between items-center">
              <div>
                <span className="font-bold text-slate-100 block">High-Vol Chop / Liquidity Transitions</span>
                <span className="text-[11px] text-slate-400">Current regime; defensive position sizing</span>
              </div>
              <span className="text-amber-400 font-bold">0.85x Allocation</span>
            </div>
            <div className="p-3 rounded bg-[#0b0e14] border border-slate-800 flex justify-between items-center">
              <div>
                <span className="font-bold text-slate-100 block">Severe Market Distress / Systemic Cascade</span>
                <span className="text-[11px] text-slate-400">Liquidity dry-up; automatic capital lock</span>
              </div>
              <span className="text-rose-400 font-bold">0.00x - 0.25x</span>
            </div>
          </div>
        </Card>

        <Card
          title="AI Advisory Advisory Engine (Read-Only)"
          subtitle="Telemetry from background LLM research summaries"
          variant="terminal"
        >
          <div className="p-3 rounded bg-[#0b0e14] border border-slate-800 space-y-3 text-xs font-mono-code">
            <div className="flex justify-between border-b border-slate-800 pb-2">
              <span className="text-slate-400">Engine State:</span>
              <Badge variant="purple" size="xs">ADVISORY ONLY</Badge>
            </div>
            <div className="flex justify-between border-b border-slate-800 pb-2">
              <span className="text-slate-400">Execution Authority:</span>
              <span className="text-rose-400 font-bold">STRICTLY FORBIDDEN</span>
            </div>
            <div className="flex justify-between border-b border-slate-800 pb-2">
              <span className="text-slate-400">Semantic Sentiment:</span>
              <span className="text-slate-200">Moderately Bullish (Score: 0.62)</span>
            </div>
            <div className="text-[11px] text-slate-400 leading-relaxed pt-1">
              {data.notes}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
