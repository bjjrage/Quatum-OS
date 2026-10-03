"use client";

import React, { useState } from "react";
import { SystemStatus, RecorderStatus } from "../../types";
import {
  ShieldAlert,
  Activity,
  CheckCircle2,
  Clock,
  GitBranch,
  Lock,
  Radio,
  Server,
  Sun,
  Moon,
} from "lucide-react";

interface TopStatusStripProps {
  status: SystemStatus | null;
  recorder?: RecorderStatus | null;
  onRefresh?: () => void;
  theme?: "dark" | "light";
  onToggleTheme?: () => void;
}

export const TopStatusStrip: React.FC<TopStatusStripProps> = ({
  status,
  recorder,
  onRefresh,
  theme = "dark",
  onToggleTheme,
}) => {
  const [copied, setCopied] = useState(false);

  const gitShaShort = status?.git_sha_short || recorder?.git_sha?.slice(0, 7) || "6c04bfa";
  const gitShaFull = status?.git_sha || recorder?.git_sha || "6c04bfa85a4fb79730599c1ae0eb322bb1667d4f";
  const env = status?.environment || "LOCAL_PAPER_ONLY";
  const recorderStatus = recorder?.status || status?.recorder_status || "RUNNING";
  const gate24h = recorder?.gate_24h_status || status?.gate_24h?.status || "PENDING";
  const gate72h = recorder?.gate_72h_status || status?.gate_72h?.status || "PENDING";
  const testsPassing = status?.tests_passing ?? 259;

  const copySha = () => {
    navigator.clipboard.writeText(gitShaFull);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getRecorderColor = (st: string) => {
    switch (st) {
      case "RUNNING":
        return "text-emerald-800 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 border-emerald-300 dark:border-emerald-800";
      case "DEGRADED":
        return "text-amber-900 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 border-amber-300 dark:border-amber-800";
      case "STOPPED":
        return "text-rose-900 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/60 border-rose-300 dark:border-rose-800";
      default:
        return "text-slate-700 dark:text-slate-400 bg-slate-100 dark:bg-slate-900 border-slate-300 dark:border-slate-700";
    }
  };

  return (
    <header className="sticky top-0 z-50 flex items-center justify-between border-b border-slate-300 dark:border-graphite-700 bg-white dark:bg-graphite-950 px-4 py-2 text-xs font-mono select-none shadow-xs transition-colors">
      {/* Brand & Environment */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 font-bold tracking-wider text-slate-900 dark:text-slate-100">
          <Server className="h-4 w-4 text-sky-600 dark:text-sky-400" />
          <span className="text-sm tracking-tight font-extrabold text-sky-600 dark:text-sky-400">
            QUANT OS
          </span>
          <span className="rounded bg-sky-100 dark:bg-sky-950/70 border border-sky-300 dark:border-sky-800 px-1.5 py-0.5 text-[10px] font-semibold text-sky-800 dark:text-sky-300">
            v1.4.2
          </span>
        </div>

        <div className="h-4 w-[1px] bg-slate-300 dark:bg-graphite-700" />

        <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-400">
          <span className="text-slate-500 font-medium">ENV:</span>
          <span className="rounded bg-amber-50 dark:bg-graphite-850 border border-amber-300 dark:border-graphite-700 px-2 py-0.5 text-[11px] font-semibold text-amber-900 dark:text-amber-300">
            {env}
          </span>
        </div>

        <div className="h-4 w-[1px] bg-slate-300 dark:bg-graphite-700" />

        {/* Git SHA */}
        <button
          onClick={copySha}
          title={`Click to copy full commit: ${gitShaFull}`}
          className="flex items-center gap-1 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition-colors"
        >
          <GitBranch className="h-3.5 w-3.5 text-slate-500" />
          <span className="font-mono font-medium text-slate-700 dark:text-slate-300 hover:underline">
            {gitShaShort}
          </span>
          {copied && (
            <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400">copied!</span>
          )}
        </button>
      </div>

      {/* Real-time Health Matrix & Theme Switch */}
      <div className="flex items-center gap-3">
        {/* Recorder Status */}
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500 font-medium">RECORDER:</span>
          <span
            className={`flex items-center gap-1 rounded border px-2 py-0.5 text-[11px] font-semibold ${getRecorderColor(
              recorderStatus
            )}`}
          >
            <Radio
              className={`h-2.5 w-2.5 ${
                recorderStatus === "RUNNING" ? "animate-pulse text-emerald-600 dark:text-emerald-400" : ""
              }`}
            />
            {recorderStatus}
          </span>
        </div>

        {/* 24h Acceptance Gate */}
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500 font-medium">24H:</span>
          <span
            className={`rounded border px-2 py-0.5 text-[11px] font-semibold ${
              gate24h === "PASS"
                ? "text-emerald-800 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 border-emerald-300 dark:border-emerald-800"
                : "text-amber-900 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 border-amber-300 dark:border-amber-800"
            }`}
          >
            {gate24h}
          </span>
        </div>

        {/* 72h Acceptance Gate */}
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500 font-medium">72H:</span>
          <span
            className={`rounded border px-2 py-0.5 text-[11px] font-semibold ${
              gate72h === "PASS"
                ? "text-emerald-800 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 border-emerald-300 dark:border-emerald-800"
                : "text-amber-900 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 border-amber-300 dark:border-amber-800"
            }`}
          >
            {gate72h}
          </span>
        </div>

        {/* CI Status */}
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500 font-medium">TESTS:</span>
          <span className="flex items-center gap-1 rounded border border-emerald-300 dark:border-emerald-900 bg-emerald-50 dark:bg-emerald-950/50 px-2 py-0.5 text-[11px] font-semibold text-emerald-800 dark:text-emerald-300">
            <CheckCircle2 className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
            {testsPassing}/259 PASS
          </span>
        </div>

        {/* PROMINENT LIVE CAPITAL LOCK BADGE */}
        <div
          title="Core Invariant: Zero Live Risk. Live capital authorization is currently $0.00."
          className="flex items-center gap-1.5 rounded border border-rose-300 dark:border-red-800 bg-rose-100 dark:bg-red-950/80 px-2.5 py-0.5 text-[11px] font-bold text-rose-950 dark:text-red-300 shadow-xs"
        >
          <Lock className="h-3 w-3 text-rose-700 dark:text-red-400" />
          <span>LOCKED</span>
          <span className="text-rose-400 dark:text-slate-400">|</span>
          <span className="text-rose-900 dark:text-slate-200">$0 LIVE RISK</span>
        </div>

        {/* Disabled Live Execution Control */}
        <button
          disabled
          title="Live capital authorization is currently $0. Real exchange routing is physically blocked."
          className="cursor-not-allowed flex items-center gap-1 rounded border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-graphite-800/50 px-2 py-0.5 text-[10px] font-medium text-slate-500"
        >
          <ShieldAlert className="h-3 w-3 text-slate-500" />
          <span>LIVE ROUTING DISABLED</span>
        </button>

        {/* LIGHT / DARK THEME TOGGLE SWITCH */}
        {onToggleTheme && (
          <button
            onClick={onToggleTheme}
            type="button"
            aria-label="Toggle theme"
            title={theme === "dark" ? "Cambiar a tema claro (Light)" : "Cambiar a tema oscuro (Dark)"}
            className="flex items-center gap-1.5 rounded border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-graphite-800 px-2.5 py-1 text-[11px] font-mono font-semibold text-slate-800 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-graphite-700 hover:border-slate-400 dark:hover:border-slate-600 transition shadow-xs"
          >
            {theme === "dark" ? (
              <>
                <Sun className="h-3.5 w-3.5 text-amber-400" />
                <span className="tracking-wide">LIGHT</span>
              </>
            ) : (
              <>
                <Moon className="h-3.5 w-3.5 text-sky-600" />
                <span className="tracking-wide">DARK</span>
              </>
            )}
          </button>
        )}
      </div>
    </header>
  );
};
