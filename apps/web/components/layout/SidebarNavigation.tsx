"use client";

import React from "react";
import { NavTabId } from "../../types";
import {
  Activity,
  BarChart3,
  BookOpen,
  Boxes,
  CheckSquare,
  Cpu,
  Database,
  Flame,
  Gauge,
  History,
  Layers,
  LineChart,
  Lock,
  PieChart,
  Radio,
  Scale,
  Settings,
  Shield,
  ShieldAlert,
  Sliders,
  Terminal,
  TrendingUp,
  Wallet,
  Zap,
} from "lucide-react";

interface SidebarProps {
  activeTab: NavTabId;
  onSelectTab: (tab: NavTabId) => void;
  strategiesCount?: number;
  holdoutsStatus?: string;
  killSwitchActive?: boolean;
  testsPassing?: number | null;
}

interface NavSection {
  title: string;
  items: Array<{
    id: NavTabId;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    badge?: string;
    badgeColor?: string;
  }>;
}

export const SidebarNavigation: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  strategiesCount,
  holdoutsStatus,
  killSwitchActive,
  testsPassing,
}) => {
  const holdoutBadge = !holdoutsStatus || holdoutsStatus === "UNKNOWN"
    ? { badge: "UNKNOWN", badgeColor: "bg-slate-900 text-slate-400 border-slate-700" }
    : holdoutsStatus === "SEALED"
    ? { badge: "SEALED", badgeColor: "bg-amber-950 text-amber-400 border-amber-800" }
    : { badge: holdoutsStatus, badgeColor: "bg-red-950 text-red-400 border-red-800" };

  const killSwitchBadge = killSwitchActive === undefined
    ? { badge: "UNKNOWN", badgeColor: "bg-slate-900 text-slate-400 border-slate-700" }
    : killSwitchActive
    ? { badge: "TRIPPED", badgeColor: "bg-red-950 text-red-400 border-red-800" }
    : { badge: "ARMED", badgeColor: "bg-emerald-950 text-emerald-400 border-emerald-800" };

  const testsBadge = testsPassing === undefined || testsPassing === null
    ? { badge: "UNKNOWN", badgeColor: "bg-slate-900 text-slate-400 border-slate-700" }
    : { badge: `${testsPassing} PASS`, badgeColor: "bg-emerald-950 text-emerald-400 border-emerald-800" };

  const sections: NavSection[] = [
    {
      title: "OVERVIEW",
      items: [
        {
          id: "command-center",
          label: "Command Center",
          icon: Gauge,
        },
      ],
    },
    {
      title: "DATA FABRIC",
      items: [
        {
          id: "recorder",
          label: "Data Recorder",
          icon: Radio,
          badge: "TARGET 100ms",
          badgeColor: "bg-slate-900 text-slate-400 border-slate-700",
        },
        {
          id: "data-quality",
          label: "Data Quality & 72h",
          icon: Activity,
        },
        {
          id: "tradability",
          label: "Markets / Tradability",
          icon: Scale,
        },
      ],
    },
    {
      title: "RESEARCH & ALPHA",
      items: [
        {
          id: "strategy-registry",
          label: "Strategy Registry",
          icon: Boxes,
          badge: strategiesCount !== undefined ? String(strategiesCount) : undefined,
          badgeColor: "bg-graphite-800 text-slate-300 border-graphite-700",
        },
        {
          id: "str002-specialized",
          label: "STR-002 v2 Models",
          icon: Zap,
          badge: "M0-M7",
          badgeColor: "bg-purple-950 text-purple-400 border-purple-800",
        },
        {
          id: "experiments",
          label: "Experiment Explorer",
          icon: Sliders,
        },
        {
          id: "backtests",
          label: "Backtests & Replays",
          icon: LineChart,
        },
        {
          id: "holdouts",
          label: "Holdout Governance",
          icon: Lock,
          badge: holdoutBadge.badge,
          badgeColor: holdoutBadge.badgeColor,
        },
      ],
    },
    {
      title: "PORTFOLIO & GATES",
      items: [
        {
          id: "selection-gates",
          label: "Selection Gates (A-D)",
          icon: CheckSquare,
        },
        {
          id: "portfolio",
          label: "Multi-Edge Allocator",
          icon: PieChart,
        },
        {
          id: "regimes",
          label: "Regimes & Policies",
          icon: Cpu,
        },
        {
          id: "attribution",
          label: "PnL Attribution",
          icon: BarChart3,
        },
      ],
    },
    {
      title: "TRADING & EXECUTION",
      items: [
        {
          id: "paper-trading",
          label: "Paper Trading Terminal",
          icon: Terminal,
        },
        {
          id: "orders-fills",
          label: "Orders & Fills",
          icon: History,
        },
        {
          id: "positions",
          label: "Positions Ledger",
          icon: TrendingUp,
        },
        {
          id: "execution",
          label: "Execution Reconciliation",
          icon: Layers,
        },
      ],
    },
    {
      title: "DETERMINISTIC RISK",
      items: [
        {
          id: "risk-engine",
          label: "Risk Engine & Limits",
          icon: Shield,
        },
        {
          id: "event-clusters",
          label: "Event Clusters",
          icon: Flame,
        },
        {
          id: "kill-switches",
          label: "Kill Switches",
          icon: ShieldAlert,
          badge: killSwitchBadge.badge,
          badgeColor: killSwitchBadge.badgeColor,
        },
      ],
    },
    {
      title: "CAPITAL & PROP FIRMS",
      items: [
        {
          id: "capital-pockets",
          label: "Capital Pockets (Own/Prop)",
          icon: Wallet,
        },
        {
          id: "prop-firms",
          label: "Prop Firm Profiles",
          icon: BookOpen,
        },
        {
          id: "prop-simulator",
          label: "Monte Carlo Exam Simulator",
          icon: Sliders,
        },
        {
          id: "multi-account",
          label: "Multi-Account Compliance",
          icon: Database,
        },
      ],
    },
    {
      title: "SYSTEM & AUDIT",
      items: [
        {
          id: "audit-trail",
          label: "Audit Trail",
          icon: History,
        },
        {
          id: "tests-ci",
          label: "Tests & Red-Team CI",
          icon: CheckSquare,
          badge: testsBadge.badge,
          badgeColor: testsBadge.badgeColor,
        },
        {
          id: "blueprint",
          label: "Master Blueprint",
          icon: BookOpen,
        },
      ],
    },
  ];

  return (
    <aside className="w-64 flex-shrink-0 flex flex-col border-r border-graphite-700 bg-graphite-900 overflow-y-auto select-none font-sans text-xs">
      <div className="p-3">
        {sections.map((sec, idx) => (
          <div key={sec.title} className={idx > 0 ? "mt-4" : ""}>
            <div className="px-2 mb-1.5 text-[10px] font-bold tracking-wider text-slate-500 font-mono">
              {sec.title}
            </div>
            <nav className="space-y-0.5">
              {sec.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onSelectTab(item.id)}
                    className={`w-full flex items-center justify-between rounded px-2.5 py-1.5 text-left font-medium transition-all ${
                      isActive
                        ? "bg-sky-950/80 text-sky-300 border border-sky-800/80 shadow-sm"
                        : "text-slate-400 hover:text-slate-200 hover:bg-graphite-800/70 border border-transparent"
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <Icon
                        className={`h-4 w-4 flex-shrink-0 ${
                          isActive ? "text-sky-400" : "text-slate-500"
                        }`}
                      />
                      <span className="truncate">{item.label}</span>
                    </div>
                    {item.badge && (
                      <span
                        className={`ml-1.5 rounded px-1.5 py-0.2 text-[9px] font-mono border ${
                          item.badgeColor ||
                          "bg-graphite-800 text-slate-400 border-graphite-700"
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </nav>
          </div>
        ))}
      </div>

      {/* Footer System Invariant Notice */}
      <div className="mt-auto border-t border-graphite-700 p-3 bg-graphite-950/70 text-[10px] font-mono text-slate-500">
        <div className="flex items-center gap-1.5 text-amber-400/90 font-semibold mb-1">
          <Lock className="h-3 w-3" />
          <span>ZERO LIVE CAPITAL INVARIANT</span>
        </div>
        <p className="leading-tight text-slate-500">
          Live capital strictly $0. Real routing physically prevented. Paper/virtual only.
        </p>
      </div>
    </aside>
  );
};
