import React, { useState } from "react";
import { SlidersHorizontal, CheckCircle, XCircle, AlertTriangle, Search, Info } from "lucide-react";
import { TradabilityMarket } from "../../types";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";

interface TradabilityViewProps {
  markets: TradabilityMarket[];
  onRefresh?: () => void;
}

export function TradabilityView({ markets }: TradabilityViewProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [tierFilter, setTierFilter] = useState<string>("ALL");

  // Filter logic
  const filtered = markets.filter((m) => {
    const matchesSearch =
      m.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.venue.toLowerCase().includes(searchTerm.toLowerCase());
    if (tierFilter === "ALL") return matchesSearch;
    if (tierFilter === "TIER_5") return matchesSearch && m.tier_code === 5;
    if (tierFilter === "TRADABLE") return matchesSearch && m.tradable;
    if (tierFilter === "UNTRADABLE") return matchesSearch && !m.tradable;
    return matchesSearch;
  });

  const tradableCount = markets.filter((m) => m.tradable).length;
  const tier5Count = markets.filter((m) => m.tier_code === 5).length;
  const untradableCount = markets.filter((m) => !m.tradable).length;

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-200 dark:border-slate-800">
        <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 font-mono-code flex items-center gap-2">
          <SlidersHorizontal className="w-5 h-5 text-sky-600 dark:text-cyan-400" />
          Market Universe Tradability & Liquidity Tier Classification
        </h2>
        <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 font-mono-code">
          Automated pre-trade liquidity policy gating based on spread, depth, volume, and clock sync offset.
        </p>
      </div>

      {/* POLICY CALLOUT BANNER: TIER 5 VS UNTRADABLE */}
      <div className="rounded-lg border border-sky-300 dark:border-cyan-800/60 bg-sky-50 dark:bg-[#0e1724] p-4 text-xs font-mono-code space-y-1 shadow-sm">
        <div className="flex items-center gap-2 text-sky-900 dark:text-cyan-300 font-bold uppercase">
          <Info className="w-4 h-4" />
          Institutional Liquidity Tier Policy Invariant
        </div>
        <p className="text-slate-700 dark:text-slate-300 leading-relaxed font-mono-code">
          <strong className="text-purple-800 dark:text-purple-300 font-semibold">Tier 5 (Small Tradable):</strong> Symbol is <strong className="text-emerald-700 dark:text-emerald-400 font-bold">TRADABLE</strong> with strict constraints: maximum position cap of <strong className="text-slate-900 dark:text-slate-100 font-bold">$5,000 USD</strong> and <strong className="text-slate-900 dark:text-slate-100 font-bold">LIMIT ORDERS ONLY</strong> (passive posting only, market orders forbidden).
          Tier 5 must never be conflated with <strong className="text-rose-700 dark:text-rose-400 font-semibold">Untradable</strong> assets which fail basic liquidity/spread gates.
        </p>
      </div>

      {/* STATS TILES */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Total Universe Monitored"
          value={`${markets.length} Assets`}
          subtitle="Binance, Bybit, Deribit"
          badge={{ text: "CATALOG", variant: "slate" }}
        />
        <MetricCard
          label="Total Tradable Assets"
          value={`${tradableCount} Symbols`}
          subtitle="Tiers 1 through 5 eligible"
          badge={{ text: "ACTIVE", variant: "emerald" }}
        />
        <MetricCard
          label="Tier 5 Small Tradable"
          value={`${tier5Count} Symbols`}
          subtitle="Cap: $5,000 | Limit Orders Only"
          badge={{ text: "TRADABLE (RESTRICTED)", variant: "purple" }}
        />
        <MetricCard
          label="Untradable Assets"
          value={`${untradableCount} Symbols`}
          subtitle="Failed spread or depth gates"
          badge={{ text: "LOCKED / REJECTED", variant: "rose" }}
        />
      </div>

      {/* FILTER BAR & SEARCH */}
      <Card variant="terminal">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search symbol or venue..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded bg-white dark:bg-[#0b0e14] border border-slate-300 dark:border-slate-800 text-xs font-mono-code text-slate-900 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-sky-500 dark:focus:border-cyan-500 shadow-xs"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto overflow-x-auto">
            {["ALL", "TRADABLE", "TIER_5", "UNTRADABLE"].map((f) => (
              <button
                key={f}
                onClick={() => setTierFilter(f)}
                className={`px-3 py-1 rounded text-xs font-mono-code transition ${
                  tierFilter === f
                    ? "bg-sky-100 text-sky-900 border border-sky-400 font-bold shadow-xs dark:bg-cyan-950 dark:text-cyan-300 dark:border-cyan-700"
                    : "bg-slate-100 text-slate-700 border border-slate-300 hover:bg-slate-200 hover:text-slate-900 dark:bg-slate-900 dark:text-slate-400 dark:hover:text-slate-200 dark:border-slate-800"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* TRADABILITY DATA TABLE */}
      <Card variant="terminal">
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono-code text-left text-slate-300">
            <thead className="bg-[#0b0e14] text-slate-400 uppercase text-[11px] border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Symbol</th>
                <th className="py-2.5 px-3">Venue</th>
                <th className="py-2.5 px-3">Classification Tier</th>
                <th className="py-2.5 px-3">Tradable State</th>
                <th className="py-2.5 px-3">Spread</th>
                <th className="py-2.5 px-3">0.5% Depth</th>
                <th className="py-2.5 px-3">5m Volume</th>
                <th className="py-2.5 px-3">Max Position Cap</th>
                <th className="py-2.5 px-3">Order Mode</th>
                <th className="py-2.5 px-3">Rejection / Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {filtered.map((m) => {
                const isTier5 = m.tier_code === 5;
                const isUntradable = !m.tradable;

                return (
                  <tr key={`${m.venue}-${m.symbol}`} className="hover:bg-[#121622]/50 transition">
                    <td className="py-2.5 px-3 font-bold text-slate-100">{m.symbol}</td>
                    <td className="py-2.5 px-3 text-slate-400">{m.venue}</td>
                    <td className="py-2.5 px-3">
                      {isTier5 ? (
                        <Badge variant="purple" size="xs">
                          TIER 5 (SMALL TRADABLE)
                        </Badge>
                      ) : isUntradable ? (
                        <Badge variant="rose" size="xs">
                          TIER 6 (UNTRADABLE)
                        </Badge>
                      ) : (
                        <Badge variant="cyan" size="xs">
                          {m.tier_name || `TIER ${m.tier_code}`}
                        </Badge>
                      )}
                    </td>
                    <td className="py-2.5 px-3">
                      {isTier5 ? (
                        <span className="inline-flex items-center gap-1 text-purple-400 font-semibold">
                          <CheckCircle className="w-3.5 h-3.5" />
                          TRADABLE (RESTRICTED)
                        </span>
                      ) : isUntradable ? (
                        <span className="inline-flex items-center gap-1 text-rose-400 font-semibold">
                          <XCircle className="w-3.5 h-3.5" />
                          UNTRADABLE
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold">
                          <CheckCircle className="w-3.5 h-3.5" />
                          TRADABLE
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-slate-200">{m.spread_bps.toFixed(2)} bps</td>
                    <td className="py-2.5 px-3 text-slate-200">
                      ${m.depth_0_5pct_usd?.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </td>
                    <td className="py-2.5 px-3 text-slate-200">
                      ${m.volume_5m_usd?.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </td>
                    <td className="py-2.5 px-3">
                      {isTier5 ? (
                        <span className="text-purple-300 font-bold">$5,000 USD (HARD CAP)</span>
                      ) : isUntradable ? (
                        <span className="text-rose-400">$0</span>
                      ) : (
                        <span className="text-slate-300">
                          {m.max_position_usd ? `$${m.max_position_usd.toLocaleString()}` : "STANDARD"}
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3">
                      {m.limit_orders_only ? (
                        <Badge variant="warning" size="xs">
                          LIMIT ONLY
                        </Badge>
                      ) : (
                        <span className="text-slate-400">LIMIT + MARKET</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-slate-400">
                      {m.rejection_reasons && m.rejection_reasons.length > 0 ? (
                        <span className="text-rose-400/90 truncate block max-w-xs" title={m.rejection_reasons.join(", ")}>
                          {m.rejection_reasons.join(", ")}
                        </span>
                      ) : isTier5 ? (
                        <span className="text-purple-300/80">Restricted position sizing and passive orders</span>
                      ) : (
                        <span className="text-emerald-400/80">Passed all liquidity criteria</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
