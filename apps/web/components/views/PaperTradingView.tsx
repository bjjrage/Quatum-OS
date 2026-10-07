import React, { useState } from "react";
import { Briefcase, ArrowUpRight, ArrowDownRight, Clock, ShieldCheck, DollarSign, RefreshCw } from "lucide-react";
import { PaperAccount } from "../../types";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";
import { FlujoPaperPanel } from "./FlujoPaperPanel";
import { PumpPaperPanel } from "./PumpPaperPanel";
import { LiderPaperPanel } from "./LiderPaperPanel";
import { PolyPaperPanel } from "./PolyPaperPanel";

interface PaperTradingViewProps {
  paperAccount: PaperAccount | null;
  onRefresh?: () => void;
}

export function PaperTradingView({ paperAccount, onRefresh }: PaperTradingViewProps) {
  const [activeTab, setActiveTab] = useState<"POSITIONS" | "ORDERS" | "FILLS">("POSITIONS");

  const isAccountActive = paperAccount !== null && paperAccount !== undefined && paperAccount.status !== "NOT_STARTED";
  const equity = paperAccount?.equity_usd;
  const cash = paperAccount?.cash_usd;
  const realizedPnl = paperAccount?.realized_pnl_usd;
  const unrealizedPnl = paperAccount?.unrealized_pnl_usd;

  const hasEquity = equity !== undefined && equity !== null;
  const hasCash = cash !== undefined && cash !== null;
  const hasRealizedPnl = realizedPnl !== undefined && realizedPnl !== null;
  const hasUnrealizedPnl = unrealizedPnl !== undefined && unrealizedPnl !== null;

  const positions = paperAccount?.positions ?? [];
  const orders = paperAccount?.orders ?? [];
  const fills = paperAccount?.fills ?? [];

  return (
    <div className="space-y-6">
      <PolyPaperPanel />
      <FlujoPaperPanel />
      <LiderPaperPanel />
      <PumpPaperPanel />
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
            <Briefcase className="w-5 h-5 text-cyan-400" />
            Institutional Paper Broker & Simulated Execution Engine
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Realistic order lifecycle simulation with calibrated latency (P95=28ms), maker/taker fees, and queue slippage.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={isAccountActive ? "cyan" : "slate"} size="sm">
            {isAccountActive ? "BROKER MODE: SIMULATED" : "BROKER: NOT STARTED"}
          </Badge>
          <Badge variant="rose" size="sm">
            LIVE: LOCKED ($0)
          </Badge>
        </div>
      </div>

      {/* METRIC STRIP */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Account Equity"
          value={hasEquity ? `$${equity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "NOT INITIALIZED"}
          subtitle={hasCash ? `Cash: $${cash.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : "Paper account unallocated"}
          badge={{ text: isAccountActive ? "SIMULATED" : "NOT STARTED", variant: isAccountActive ? "emerald" : "slate" }}
          icon={<DollarSign className="w-4 h-4" />}
        />
        <MetricCard
          label="Realized PnL"
          value={hasRealizedPnl ? `$${realizedPnl >= 0 ? "+" : ""}${realizedPnl.toFixed(2)}` : "—"}
          subtitle="Net of exchange fees"
          badge={{
            text: !isAccountActive ? "NOT STARTED" : hasRealizedPnl && realizedPnl >= 0 ? "PROFIT" : "LOSS",
            variant: !isAccountActive ? "slate" : hasRealizedPnl && realizedPnl >= 0 ? "emerald" : "rose",
          }}
          trend={hasRealizedPnl ? { direction: realizedPnl >= 0 ? "up" : "down", value: `$${Math.abs(realizedPnl).toFixed(2)}` } : undefined}
        />
        <MetricCard
          label="Unrealized MTM PnL"
          value={hasUnrealizedPnl ? `$${unrealizedPnl >= 0 ? "+" : ""}${unrealizedPnl.toFixed(2)}` : "—"}
          subtitle="Marked to market via socket"
          badge={{ text: isAccountActive ? "LIVE MTM" : "NOT STARTED", variant: isAccountActive ? "cyan" : "slate" }}
        />
        <MetricCard
          label="Simulated Latency"
          value={paperAccount?.simulated_latency_ms !== undefined ? `${paperAccount.simulated_latency_ms} ms` : "—"}
          subtitle="Taker: 5.0 bps | Maker: 2.0 bps"
          badge={{ text: isAccountActive ? "REALISTIC" : "UNINITIALIZED", variant: isAccountActive ? "purple" : "slate" }}
          icon={<Clock className="w-4 h-4" />}
        />
      </div>

      {/* TABS FOR POSITIONS / ORDERS / FILLS */}
      <Card variant="terminal">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
          <div className="flex items-center gap-2">
            {[
              { id: "POSITIONS", label: `Open Positions (${positions.length})` },
              { id: "ORDERS", label: `Order History (${orders.length})` },
              { id: "FILLS", label: `Execution Fills (${fills.length})` },
            ].map((t) => (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id as any)}
                className={`px-3 py-1.5 rounded text-xs font-mono-code transition ${
                  activeTab === t.id
                    ? "bg-cyan-950 text-cyan-300 border border-cyan-700"
                    : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="text-xs font-mono-code text-slate-400 hover:text-slate-200 flex items-center gap-1"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Refresh
            </button>
          )}
        </div>

        {/* TAB 1: POSITIONS */}
        {activeTab === "POSITIONS" && (
          positions.length === 0 ? (
            <div className="py-12 text-center text-xs font-mono-code text-slate-400">
              <p className="text-slate-200 font-bold mb-1">0 OPEN POSITIONS</p>
              <p className="text-slate-500">Paper broker initialized with $100,000 cash. No paper positions currently open.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono-code text-left text-slate-300">
                <thead className="bg-[#0b0e14] text-slate-400 uppercase text-[11px] border-b border-slate-800">
                  <tr>
                    <th className="py-2.5 px-3">Symbol</th>
                    <th className="py-2.5 px-3">Position Size</th>
                    <th className="py-2.5 px-3">Avg Entry Price</th>
                    <th className="py-2.5 px-3">Notional USD</th>
                    <th className="py-2.5 px-3">Realized PnL</th>
                    <th className="py-2.5 px-3 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80">
                  {positions.map((p, i) => {
                    const notional = p.quantity * p.average_entry_price;
                    return (
                      <tr key={i} className="hover:bg-[#121622]/50 transition">
                        <td className="py-2.5 px-3 font-bold text-slate-100">{p.symbol}</td>
                        <td className="py-2.5 px-3 text-cyan-400 font-semibold">{p.quantity}</td>
                        <td className="py-2.5 px-3 text-slate-200">${p.average_entry_price.toFixed(2)}</td>
                        <td className="py-2.5 px-3 text-slate-200">${notional.toFixed(2)}</td>
                        <td className={`py-2.5 px-3 font-bold ${p.realized_pnl_usd >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                          {p.realized_pnl_usd >= 0 ? "+" : ""}${p.realized_pnl_usd.toFixed(2)}
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <Badge variant="emerald" size="xs">OPEN (LONG)</Badge>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )
        )}

        {/* TAB 2: ORDERS */}
        {activeTab === "ORDERS" && (
          orders.length === 0 ? (
            <div className="py-12 text-center text-xs font-mono-code text-slate-400">
              <p className="text-slate-200 font-bold mb-1">0 ORDERS RECORDED</p>
              <p className="text-slate-500">No simulated orders submitted to the paper broker yet.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono-code text-left text-slate-300">
                <thead className="bg-[#0b0e14] text-slate-400 uppercase text-[11px] border-b border-slate-800">
                  <tr>
                    <th className="py-2.5 px-3">Order ID</th>
                    <th className="py-2.5 px-3">Symbol</th>
                    <th className="py-2.5 px-3">Venue</th>
                    <th className="py-2.5 px-3">Side</th>
                    <th className="py-2.5 px-3">Type</th>
                    <th className="py-2.5 px-3">Qty</th>
                    <th className="py-2.5 px-3">Limit Price</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3 text-right">Fee</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80">
                  {orders.map((o) => (
                    <tr key={o.order_id} className="hover:bg-[#121622]/50 transition">
                      <td className="py-2.5 px-3 font-semibold text-cyan-400">{o.order_id}</td>
                      <td className="py-2.5 px-3 text-slate-200 font-bold">{o.symbol}</td>
                      <td className="py-2.5 px-3 text-slate-400">{o.venue}</td>
                      <td className="py-2.5 px-3 font-bold text-emerald-400">{o.side}</td>
                      <td className="py-2.5 px-3 text-slate-300">{o.order_type}</td>
                      <td className="py-2.5 px-3 text-slate-200">{o.quantity}</td>
                      <td className="py-2.5 px-3 text-slate-200">${o.limit_price?.toFixed(2) ?? "MKT"}</td>
                      <td className="py-2.5 px-3">
                        <Badge variant={o.status === "FILLED" ? "emerald" : "amber"} size="xs">
                          {o.status}
                        </Badge>
                      </td>
                      <td className="py-2.5 px-3 text-right text-slate-400">${o.fee_paid.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}

        {/* TAB 3: FILLS */}
        {activeTab === "FILLS" && (
          fills.length === 0 ? (
            <div className="py-12 text-center text-xs font-mono-code text-slate-400">
              <p className="text-slate-200 font-bold mb-1">0 EXECUTED FILLS</p>
              <p className="text-slate-500">No simulated trades executed yet.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono-code text-left text-slate-300">
                <thead className="bg-[#0b0e14] text-slate-400 uppercase text-[11px] border-b border-slate-800">
                  <tr>
                    <th className="py-2.5 px-3">Trade ID</th>
                    <th className="py-2.5 px-3">Order ID</th>
                    <th className="py-2.5 px-3">Symbol</th>
                    <th className="py-2.5 px-3">Execution Price</th>
                    <th className="py-2.5 px-3">Qty</th>
                    <th className="py-2.5 px-3">Fee Paid</th>
                    <th className="py-2.5 px-3">Slippage USD</th>
                    <th className="py-2.5 px-3 text-right">Liquidity</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80">
                  {fills.map((f) => (
                    <tr key={f.trade_id} className="hover:bg-[#121622]/50 transition">
                      <td className="py-2.5 px-3 font-semibold text-cyan-400">{f.trade_id}</td>
                      <td className="py-2.5 px-3 text-slate-400">{f.order_id}</td>
                      <td className="py-2.5 px-3 font-bold text-slate-100">{f.symbol}</td>
                      <td className="py-2.5 px-3 text-slate-200">${f.price.toFixed(2)}</td>
                      <td className="py-2.5 px-3 text-slate-200">{f.quantity}</td>
                      <td className="py-2.5 px-3 text-slate-300">${f.fee.toFixed(2)}</td>
                      <td className="py-2.5 px-3 text-amber-400">${f.slippage_usd.toFixed(2)}</td>
                      <td className="py-2.5 px-3 text-right">
                        <Badge variant={f.is_taker ? "purple" : "emerald"} size="xs">
                          {f.is_taker ? "TAKER" : "MAKER"}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
      </Card>
    </div>
  );
}
