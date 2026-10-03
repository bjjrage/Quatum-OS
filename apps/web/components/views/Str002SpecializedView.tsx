import React from "react";
import { Zap, AlertTriangle, ShieldCheck, CheckCircle, Sliders, TrendingUp, Info } from "lucide-react";
import { Str002Specialized } from "../../types";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";

interface Str002SpecializedViewProps {
  data: Str002Specialized | null;
}

export function Str002SpecializedView({ data }: Str002SpecializedViewProps) {
  const variants = data?.model_variants ?? [
    {
      variant_id: "M0",
      name: "Raw Cascade Baseline",
      description: "Standard liquidation spike detector with fixed threshold",
      factor_model: "Single Asset Z-Score",
      btc_conditioning: false,
      reversal_filter: false,
      status: "BENCHMARK",
    },
    {
      variant_id: "M1",
      name: "Factor Residual Model",
      description: "Extracts idiosyncratic shock orthogonal to BTC/ETH beta",
      factor_model: "Cross-Sectional OLS",
      btc_conditioning: false,
      reversal_filter: false,
      status: "ACTIVE",
    },
    {
      variant_id: "M2",
      name: "BTC Trend Filtered",
      description: "Suppresses long entries when BTC 15m trend is strongly negative",
      factor_model: "Beta Residual + Trend",
      btc_conditioning: true,
      reversal_filter: false,
      status: "ACTIVE",
    },
    {
      variant_id: "M3",
      name: "Multi-Horizon BTC Matrix",
      description: "Evaluates 1m, 5m, 15m joint states before authorizing trigger",
      factor_model: "Multi-Horizon State",
      btc_conditioning: true,
      reversal_filter: false,
      status: "PRIMARY_CANDIDATE",
    },
    {
      variant_id: "M4",
      name: "Microstructure Reversal Detector",
      description: "Requires book delta absorption confirmation before entry",
      factor_model: "Orderbook Imbalance",
      btc_conditioning: true,
      reversal_filter: true,
      status: "EXPERIMENTAL",
    },
    {
      variant_id: "M5",
      name: "Vol-Scaled Sizing",
      description: "Normalizes trade size by realized high-frequency variance",
      factor_model: "Realized Volatility GARCH",
      btc_conditioning: true,
      reversal_filter: false,
      status: "ACTIVE",
    },
    {
      variant_id: "M6",
      name: "Combined Dynamic Architecture",
      description: "Joint conditioning: Residual Z-Score + Multi-horizon BTC + Delta",
      factor_model: "Full Dynamic Factor",
      btc_conditioning: true,
      reversal_filter: true,
      status: "RESEARCH",
    },
    {
      variant_id: "M7",
      name: "Execution Realism Optimized",
      description: "Calibrated with passive queue placement and adverse selection buffer",
      factor_model: "Execution Queue Model",
      btc_conditioning: true,
      reversal_filter: true,
      status: "RESEARCH",
    },
  ];

  const btcMatrix = data?.btc_decision_matrix ?? [
    {
      state: "BTC Bullish Impulse",
      horizon_1m: "Trend UP",
      horizon_5m: "Trend UP",
      decision: "FULL_ALLOW",
      sizing: "1.00x",
      action: "Execute long entry at standard limit",
    },
    {
      state: "BTC Range / Neutral",
      horizon_1m: "Mean Reverting",
      horizon_5m: "Flat",
      decision: "STANDARD_ALLOW",
      sizing: "0.85x",
      action: "Execute long entry with standard limit",
    },
    {
      state: "BTC Mild Retracement",
      horizon_1m: "Trend DOWN",
      horizon_5m: "Neutral",
      decision: "REDUCE_SIZE",
      sizing: "0.50x",
      action: "Half-size entry, tighter stop buffer",
    },
    {
      state: "BTC Severe Cascade / Crash",
      horizon_1m: "Severe Fall",
      horizon_5m: "Cascade Active",
      decision: "STRICT_BLOCK",
      sizing: "0.00x",
      action: "BLOCK ALL ENTRIES (Cascade veto in effect)",
    },
  ];

  const factor = data?.live_factor_state;

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-800">
        <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
          <Zap className="w-5 h-5 text-amber-400" />
          STR-002 v2: Liquidity Shock Post-Cascade Reversal (Deep Dive)
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Specialized quant cockpit for idiosyncratic altcoin liquidation cascades with multi-horizon BTC conditioning.
        </p>
      </div>

      {/* TWO MANDATORY BANNERS */}
      <div className="space-y-3">
        {/* 1. STRICT LONG-ONLY INVARIANT */}
        <div className="rounded-lg border border-purple-800/80 bg-purple-950/40 p-4 text-xs font-mono-code text-purple-200 flex items-start gap-3">
          <Info className="w-5 h-5 text-purple-400 mt-0.5 flex-shrink-0" />
          <div>
            <div className="font-bold text-sm tracking-wider uppercase text-purple-100">
              MANDATORY INVARIANT: STR-002 v2 IS STRICTLY LONG-ONLY
            </div>
            <p className="text-purple-300/90 mt-1 leading-relaxed">
              Short-side signals are intentionally unsupported and hard-blocked in the strategy logic. STR-002 strictly trades the transient liquidity vacuum following panic forced selling on long liquidations.
            </p>
          </div>
        </div>

        {/* 2. ECONOMIC EDGE NOT VALIDATED */}
        <div className="rounded-lg border border-amber-800/80 bg-amber-950/40 p-4 text-xs font-mono-code text-amber-200 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" />
          <div>
            <div className="font-bold text-sm tracking-wider uppercase text-amber-100">
              WARNING: STR-002 ECONOMIC EDGE IS EXPLICITLY NOT VALIDATED
            </div>
            <p className="text-amber-300/90 mt-1 leading-relaxed">
              While the mathematical foundation and backtesting code are validated, the empirical economic edge of STR-002 remains unproven in live market execution. Real capital allocation is strictly locked ($0.00) until paper execution passes all 4 Selection Gates.
            </p>
          </div>
        </div>
      </div>

      {/* METRIC STRIP */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Execution Mode"
          value="LONG ONLY"
          subtitle="Short side: Hard disabled"
          badge={{ text: "INVARIANT", variant: "purple" }}
        />
        <MetricCard
          label="Model Variants"
          value="8 Models (M0-M7)"
          subtitle="Primary: M3 Multi-Horizon"
          badge={{ text: "CATALOG", variant: "blue" }}
        />
        <MetricCard
          label="BTC Conditioning"
          value="1m / 5m / 15m"
          subtitle="Cascade veto logic active"
          badge={{ text: "DYNAMIC VETO", variant: "cyan" }}
        />
        <MetricCard
          label="Live Factor Telemetry"
          value={factor?.status || "NO LIVE DATA"}
          subtitle="Socket factor calculations"
          badge={{ text: factor?.status ? "ONLINE" : "PENDING DATA", variant: "amber" }}
        />
      </div>

      {/* 8 MODEL VARIANTS TABLE */}
      <Card
        title="STR-002 Model Variant Matrix (M0 — M7)"
        subtitle="Controlled architectural variations for idiosyncratic shock capture and BTC beta decoupling"
        variant="terminal"
      >
        <div className="overflow-x-auto pt-1">
          <table className="w-full text-xs font-mono-code text-left text-slate-300">
            <thead className="bg-[#0b0e14] text-slate-400 uppercase text-[11px] border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Variant ID</th>
                <th className="py-2.5 px-3">Variant Name</th>
                <th className="py-2.5 px-3">Description</th>
                <th className="py-2.5 px-3">Factor Architecture</th>
                <th className="py-2.5 px-3">BTC Filter</th>
                <th className="py-2.5 px-3">Reversal Det</th>
                <th className="py-2.5 px-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {variants.map((v) => (
                <tr key={v.variant_id} className="hover:bg-[#121622]/50 transition">
                  <td className="py-2.5 px-3 font-bold text-amber-400">{v.variant_id}</td>
                  <td className="py-2.5 px-3 font-semibold text-slate-200">{v.name}</td>
                  <td className="py-2.5 px-3 text-slate-400">{v.description}</td>
                  <td className="py-2.5 px-3 text-cyan-400">{v.factor_model}</td>
                  <td className="py-2.5 px-3">
                    <Badge variant={v.btc_conditioning ? "emerald" : "slate"} size="xs">
                      {v.btc_conditioning ? "ENABLED" : "NONE"}
                    </Badge>
                  </td>
                  <td className="py-2.5 px-3">
                    <Badge variant={v.reversal_filter ? "emerald" : "slate"} size="xs">
                      {v.reversal_filter ? "ENABLED" : "NONE"}
                    </Badge>
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <Badge
                      variant={
                        v.status === "PRIMARY_CANDIDATE"
                          ? "emerald"
                          : v.status === "ACTIVE"
                          ? "cyan"
                          : "slate"
                      }
                      size="xs"
                    >
                      {v.status}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* MULTI-HORIZON BTC DECISION MATRIX */}
      <Card
        title="Multi-Horizon BTC Conditioning Matrix"
        subtitle="Hierarchical time-series filter protecting against market-wide systematic liquidations"
        variant="terminal"
      >
        <div className="overflow-x-auto pt-1">
          <table className="w-full text-xs font-mono-code text-left text-slate-300">
            <thead className="bg-[#0b0e14] text-slate-400 uppercase text-[11px] border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">BTC Macro/Micro State</th>
                <th className="py-2.5 px-3">1m Horizon</th>
                <th className="py-2.5 px-3">5m Horizon</th>
                <th className="py-2.5 px-3">Entry Decision</th>
                <th className="py-2.5 px-3">Position Sizing</th>
                <th className="py-2.5 px-3">Operational Directive</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {btcMatrix.map((bm, i) => (
                <tr key={i} className="hover:bg-[#121622]/50 transition">
                  <td className="py-2.5 px-3 font-semibold text-slate-100">{bm.state}</td>
                  <td className="py-2.5 px-3 text-slate-300">{bm.horizon_1m}</td>
                  <td className="py-2.5 px-3 text-slate-300">{bm.horizon_5m}</td>
                  <td className="py-2.5 px-3">
                    <Badge
                      variant={
                        bm.decision === "STRICT_BLOCK"
                          ? "rose"
                          : bm.decision === "REDUCE_SIZE"
                          ? "amber"
                          : "emerald"
                      }
                      size="xs"
                    >
                      {bm.decision}
                    </Badge>
                  </td>
                  <td className="py-2.5 px-3 font-bold text-slate-200">{bm.sizing}</td>
                  <td className="py-2.5 px-3 text-slate-400">{bm.action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* LIVE FACTOR STATE TELEMETRY */}
      <Card
        title="Real-Time Factor State Monitor"
        subtitle="Online calculation of Beta Down, Beta Up, Gamma ETH, and Residual Z-Score"
        variant="terminal"
      >
        <div className="p-4 rounded bg-[#0b0e14] border border-slate-800 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
            <span className="text-xs font-semibold text-slate-300 font-mono-code">
              Microstructure Factors (ETH/USDT, SOL/USDT Shock Basket)
            </span>
            <Badge variant="amber" size="xs">
              {factor?.status || "NO LIVE DATA / STREAMING PENDING"}
            </Badge>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono-code text-slate-400">
            <div className="p-2.5 rounded bg-[#121622] border border-slate-800">
              <span className="text-[10px] text-slate-400 block">Beta Down (BTC)</span>
              <span className="text-sm font-bold text-slate-200">
                {typeof factor?.beta_down === "number" ? factor.beta_down.toFixed(2) : "— (PENDING DATA)"}
              </span>
            </div>
            <div className="p-2.5 rounded bg-[#121622] border border-slate-800">
              <span className="text-[10px] text-slate-400 block">Beta Up (BTC)</span>
              <span className="text-sm font-bold text-slate-200">
                {typeof factor?.beta_up === "number" ? factor.beta_up.toFixed(2) : "— (PENDING DATA)"}
              </span>
            </div>
            <div className="p-2.5 rounded bg-[#121622] border border-slate-800">
              <span className="text-[10px] text-slate-400 block">Gamma (ETH)</span>
              <span className="text-sm font-bold text-slate-200">
                {typeof factor?.gamma_eth === "number" ? factor.gamma_eth.toFixed(2) : "— (PENDING DATA)"}
              </span>
            </div>
            <div className="p-2.5 rounded bg-[#121622] border border-slate-800">
              <span className="text-[10px] text-slate-400 block">Residual Z-Score</span>
              <span className="text-sm font-bold text-amber-400">
                {typeof factor?.residual_z_score === "number"
                  ? `${factor.residual_z_score.toFixed(2)} (Threshold: -3.0)`
                  : "— (PENDING DATA)"}
              </span>
            </div>
          </div>

          <div className="text-[11px] font-mono-code text-slate-400 bg-[#0f121a] p-3 rounded border border-slate-800 leading-relaxed">
            <span className="text-amber-400 font-bold block mb-1">Live Factor Telemetry Status:</span>
            Socket calculation engine active. Because live capital is strictly locked at $0.00, factor outputs run exclusively in shadow simulation mode and do not emit outbound exchange orders.
          </div>
        </div>
      </Card>
    </div>
  );
}
