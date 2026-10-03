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
  unvalidatedStrategiesCount?: number;
  failedGatesCount?: number;
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
}) => {
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
          badge: "100ms",
          badgeColor: "bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-400 border-emerald-300 dark:border-emerald-800",
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
          badge: "4",
        },
        {
          id: "str002-specialized",
          label: "STR-002 v2 Models",
          icon: Zap,
          badge: "M0-M7",
          badgeColor: "bg-purple-100 dark:bg-purple-950 text-purple-800 dark:text-purple-300 border-purple-300 dark:border-purple-800",
        },
        {
          id: "experiments",
          label: "Experiment Registry",
          icon: Terminal,
        },
        {
          id: "backtests",
          label: "Backtests & Deflated",
          icon: TrendingUp,
        },
        {
          id: "holdouts",
          label: "Sealed Holdouts",
          icon: Lock,
        },
        {
          id: "selection-gates",
          label: "Selection Gates (A-D)",
          icon: Shield,
        },
      ],
    },
    {
      title: "PORTFOLIO & EXECUTION",
      items: [
        {
          id: "portfolio",
          label: "Portfolio Construction",
          icon: PieChart,
        },
        {
          id: "regimes",
          label: "Regimes & Policies",
          icon: Sliders,
        },
        {
          id: "risk-engine",
          label: "Deterministic Risk",
          icon: ShieldAlert,
        },
        {
          id: "event-clusters",
          label: "Event Clusters",
          icon: Flame,
        },
        {
          id: "paper-trading",
          label: "Paper Broker (Calibrated)",
          icon: LineChart,
        },
        {
          id: "execution",
          label: "Live Execution Plane",
          icon: Cpu,
          badge: "$0 LOCKED",
          badgeColor: "bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-400 border-rose-300 dark:border-rose-800 font-bold",
        },
        {
          id: "attribution",
          label: "PnL & Alpha Attribution",
          icon: BarChart3,
        },
      ],
    },
    {
      title: "CAPITAL POCKETS & PROP",
      items: [
        {
          id: "capital-pockets",
          label: "OWN vs PROP Pockets",
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
          badge: "259 PASS",
          badgeColor: "bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-400 border-emerald-300 dark:border-emerald-800",
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
    <aside className="w-64 flex-shrink-0 flex flex-col border-r border-slate-300 dark:border-graphite-700 bg-slate-50 dark:bg-graphite-900 overflow-y-auto select-none font-sans text-xs transition-colors">
      <div className="p-3">
        {sections.map((sec, idx) => (
          <div key={sec.title} className={idx > 0 ? "mt-4" : ""}>
            <div className="px-2 mb-1.5 text-[10px] font-bold tracking-wider text-slate-600 dark:text-slate-500 font-mono">
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
                        ? "bg-sky-100 dark:bg-sky-950/80 text-sky-900 dark:text-sky-300 border border-sky-300 dark:border-sky-800/80 shadow-xs font-semibold"
                        : "text-slate-700 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200/80 dark:hover:bg-graphite-800/70 border border-transparent"
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <Icon
                        className={`h-4 w-4 flex-shrink-0 ${
                          isActive ? "text-sky-700 dark:text-sky-400" : "text-slate-500"
                        }`}
                      />
                      <span className="truncate">{item.label}</span>
                    </div>
                    {item.badge && (
                      <span
                        className={`ml-1.5 rounded px-1.5 py-0.2 text-[9px] font-mono border ${
                          item.badgeColor ||
                          "bg-slate-200 dark:bg-graphite-800 text-slate-800 dark:text-slate-400 border-slate-300 dark:border-graphite-700"
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
      <div className="mt-auto border-t border-slate-300 dark:border-graphite-700 p-3 bg-white dark:bg-graphite-950/70 text-[10px] font-mono text-slate-600 dark:text-slate-500">
        <div className="flex items-center gap-1.5 text-amber-700 dark:text-amber-400 font-semibold mb-1">
          <Lock className="h-3 w-3" />
          <span>ZERO LIVE CAPITAL INVARIANT</span>
        </div>
        <p className="leading-tight text-slate-600 dark:text-slate-500">
          Live capital strictly $0. Real routing physically prevented. Paper/virtual only.
        </p>
      </div>
    </aside>
  );
};
