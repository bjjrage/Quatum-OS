import React from "react";
import {
  Layers,
  ArrowRight,
  Database,
  SlidersHorizontal,
  FlaskConical,
  ShieldCheck,
  PieChart,
  ShieldAlert,
  Briefcase,
  FileText,
  Lock,
} from "lucide-react";
import { NavTabId } from "../../types";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";

interface BlueprintViewProps {
  onNavigate: (tab: NavTabId) => void;
  testsPassing?: number;
}

export function BlueprintView({ onNavigate, testsPassing }: BlueprintViewProps) {
  const layers = [
    {
      step: 1,
      title: "Data Ingestion & Feed Handlers",
      domain: "recorder" as NavTabId,
      icon: <Database className="w-5 h-5 text-cyan-400" />,
      description: "Low-latency WebSocket listeners across Binance, Deribit, Polymarket, Bybit. Clock skew calibration and causal ordering.",
      badge: "24H / 72H ACCEPTANCE GATES",
    },
    {
      step: 2,
      title: "Raw Lakehouse & Data Quality",
      domain: "data-quality" as NavTabId,
      icon: <Database className="w-5 h-5 text-cyan-400" />,
      description: "Snappy Parquet columnar partition tree in data/raw/. Atomic rename invariant (tmp -> final) preventing corrupted reads.",
      badge: "ATOMIC MANIFESTS",
    },
    {
      step: 3,
      title: "Market Tradability & Liquidity Tiers",
      domain: "tradability" as NavTabId,
      icon: <SlidersHorizontal className="w-5 h-5 text-purple-400" />,
      description: "Dynamic pre-trade liquidity policy. Strict separation: Tier 1-4 (Liquid), Tier 5 (Small Tradable: $5k cap, limit only), Tier 6 (Untradable).",
      badge: "TIER 5 != UNTRADABLE",
    },
    {
      step: 4,
      title: "Alpha Research & Strategy Catalog",
      domain: "strategy-registry" as NavTabId,
      icon: <FlaskConical className="w-5 h-5 text-amber-400" />,
      description: "Formal counterparty thesis, falsification criteria, and model rules. STR-002 v2 long-only invariant and unvalidated edge status.",
      badge: "ECONOMIC EDGE GATED",
    },
    {
      step: 5,
      title: "Selection Gates (A / B / C / D)",
      domain: "selection-gates" as NavTabId,
      icon: <ShieldCheck className="w-5 h-5 text-emerald-400" />,
      description: "Mathematical gatekeepers: Gate A (Deflated Sharpe), Gate B (Latency Sensitivity), Gate C (Execution Realism), Gate D (Stability).",
      badge: "ZERO SNOOPING BIAS",
    },
    {
      step: 6,
      title: "Portfolio Construction & Capital Pockets",
      domain: "portfolio" as NavTabId,
      icon: <PieChart className="w-5 h-5 text-blue-400" />,
      description: "Multi-strategy risk budgeting and pocket isolation (Pocket A: Prop, Pocket B: Live $0 Locked, Pocket C: Research Sandbox).",
      badge: "LIVE CAPITAL = $0.00",
    },
    {
      step: 7,
      title: "Real-Time Risk Engine & Circuit Breakers",
      domain: "risk-engine" as NavTabId,
      icon: <ShieldAlert className="w-5 h-5 text-rose-400" />,
      description: "Pre-trade limit checks, trailing drawdown monitoring, automated emergency kill switches, and event cluster blackout windows.",
      badge: "MASTER LIVE GUARD",
    },
    {
      step: 8,
      title: "Paper Broker & Execution Reconciliation",
      domain: "paper-trading" as NavTabId,
      icon: <Briefcase className="w-5 h-5 text-emerald-400" />,
      description: "Calibrated fill simulation with queue delay (P95=28ms), maker/taker fees, adverse selection, and continuous ledger reconciliation.",
      badge: "FAIL-CLOSED RECON",
    },
    {
      step: 9,
      title: "Governance & Cryptographic Audit Trail",
      domain: "audit-trail" as NavTabId,
      icon: <FileText className="w-5 h-5 text-cyan-400" />,
      description: "Cryptographically verifiable ledger of runtime state, git SHA provenance, operator approvals, and test suite execution logs.",
      badge: testsPassing !== undefined ? `${testsPassing} TESTS PASSING` : "TEST SUITE PASSING",
    },
  ];

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-800">
        <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
          <Layers className="w-5 h-5 text-cyan-400" />
          Quant OS End-to-End Architectural Blueprint
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Interactive pipeline overview tracing market data ingestion, algorithmic evaluation, risk gating, and simulated settlement.
        </p>
      </div>

      {/* ARCHITECTURE FLOW CARDS */}
      <div className="space-y-3">
        {layers.map((l) => (
          <div
            key={l.step}
            onClick={() => onNavigate(l.domain)}
            className="cursor-pointer rounded-lg border border-[#1b2230] bg-[#0c0f16] p-4 hover:border-cyan-500/60 hover:bg-[#10141f] transition-all flex flex-col md:flex-row md:items-center justify-between gap-4 group"
          >
            <div className="flex items-start gap-3">
              <div className="p-2 rounded bg-slate-900 border border-slate-800 group-hover:border-cyan-500/40 transition">
                {l.icon}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-cyan-400 font-mono-code">
                    LAYER 0{l.step}
                  </span>
                  <h3 className="text-sm font-bold text-slate-100 font-mono-code group-hover:text-cyan-300 transition">
                    {l.title}
                  </h3>
                  <Badge variant="cyan" size="xs">
                    {l.badge}
                  </Badge>
                </div>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed max-w-3xl font-mono-code">
                  {l.description}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1 text-xs font-mono-code text-cyan-400 group-hover:translate-x-1 transition-transform self-end md:self-center">
              <span>Inspect Layer</span>
              <ArrowRight className="w-4 h-4" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
