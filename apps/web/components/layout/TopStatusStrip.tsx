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
} from "lucide-react";

interface TopStatusStripProps {
  status: SystemStatus | null;
  recorder?: RecorderStatus | null;
  onRefresh?: () => void;
}

export const TopStatusStrip: React.FC<TopStatusStripProps> = ({ status, recorder, onRefresh }) => {
  const [copied, setCopied] = useState(false);

  const gitShaShort = status?.git_sha_short || recorder?.git_sha?.slice(0, 7) || "UNKNOWN";
  const gitShaFull = status?.git_sha || recorder?.git_sha || "UNKNOWN";
  const env = status?.environment || "UNKNOWN";
  const recorderStatus = recorder?.status || status?.recorder_status || "UNKNOWN";
  const gate24h = recorder?.gate_24h_status || status?.gate_24h?.status || "UNKNOWN";
  const gate72h = recorder?.gate_72h_status || status?.gate_72h?.status || "UNKNOWN";
  const testsPassing = status?.tests_passing ?? null;

  const copySha = () => {
    navigator.clipboard.writeText(gitShaFull);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getRecorderColor = (st: string) => {
    switch (st) {
      case "RUNNING":
        return "text-emerald-400 bg-emerald-950/60 border-emerald-800";
      case "DEGRADED":
        return "text-amber-400 bg-amber-950/60 border-amber-800";
      case "STOPPED":
        return "text-red-400 bg-red-950/60 border-red-800";
      default:
        return "text-slate-400 bg-slate-900 border-slate-700";
    }
  };

  const getGateColor = (st: string) => {
    switch (st) {
      case "PASS":
        return "text-emerald-400 bg-emerald-950/60 border-emerald-800";
      case "PENDING":
        return "text-amber-400 bg-amber-950/60 border-amber-800";
      case "FAIL":
        return "text-red-400 bg-red-950/60 border-red-800";
      default:
        return "text-slate-400 bg-slate-900 border-slate-700";
    }
  };

  return (
    <header className="sticky top-0 z-50 flex items-center justify-between border-b border-graphite-700 bg-graphite-950 px-4 py-2 text-xs font-mono select-none">
      {/* Brand & Environment */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 font-bold tracking-wider text-slate-100">
          <Server className="h-4 w-4 text-sky-400" />
          <span className="text-sm tracking-tight font-extrabold text-sky-400">
            QUANT OS
          </span>
        </div>

        <div className="h-4 w-[1px] bg-graphite-700" />

        <div className="flex items-center gap-1.5 text-slate-400">
          <span className="text-slate-500">ENV:</span>
          <span className="rounded bg-graphite-850 border border-graphite-700 px-2 py-0.5 text-[11px] text-amber-300">
            {env}
          </span>
        </div>

        <div className="h-4 w-[1px] bg-graphite-700" />

        {/* Git SHA */}
        <button
          onClick={copySha}
          title={`Click to copy full commit: ${gitShaFull}`}
          className="flex items-center gap-1 text-slate-400 hover:text-slate-200 transition-colors"
        >
          <GitBranch className="h-3.5 w-3.5 text-slate-500" />
          <span className="font-mono text-slate-300 hover:underline">
            {gitShaShort}
          </span>
          {copied && (
            <span className="text-[10px] text-emerald-400">copied!</span>
          )}
        </button>
      </div>

      {/* Real-time Health Matrix */}
      <div className="flex items-center gap-3">
        {/* Recorder Status */}
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500">RECORDER:</span>
          <span
            className={`flex items-center gap-1 rounded border px-2 py-0.5 text-[11px] font-semibold ${getRecorderColor(
              recorderStatus
            )}`}
          >
            <Radio
              className={`h-2.5 w-2.5 ${
                recorderStatus === "RUNNING" ? "animate-pulse text-emerald-400" : ""
              }`}
            />
            {recorderStatus}
          </span>
        </div>

        {/* 24h Acceptance Gate */}
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500">24H:</span>
          <span
            className={`rounded border px-2 py-0.5 text-[11px] font-semibold ${getGateColor(
              gate24h
            )}`}
          >
            {gate24h}
          </span>
        </div>

        {/* 72h Acceptance Gate */}
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500">72H:</span>
          <span
            className={`rounded border px-2 py-0.5 text-[11px] font-semibold ${getGateColor(
              gate72h
            )}`}
          >
            {gate72h}
          </span>
        </div>

        {/* CI Status */}
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500">TESTS:</span>
          {testsPassing !== null ? (
            <span className="flex items-center gap-1 rounded border border-emerald-900 bg-emerald-950/50 px-2 py-0.5 text-[11px] text-emerald-300">
              <CheckCircle2 className="h-3 w-3 text-emerald-400" />
              {testsPassing} PASS
            </span>
          ) : (
            <span className="flex items-center gap-1 rounded border border-slate-700 bg-slate-900 px-2 py-0.5 text-[11px] text-slate-400">
              UNKNOWN
            </span>
          )}
        </div>

        {/* PROMINENT LIVE CAPITAL LOCK BADGE */}
        <div
          title="Core Invariant: Zero Live Risk. Live capital authorization is currently $0.00."
          className="flex items-center gap-1.5 rounded border border-red-800 bg-red-950/80 px-2.5 py-0.5 text-[11px] font-bold text-red-300 shadow-sm"
        >
          <Lock className="h-3 w-3 text-red-400" />
          <span>LOCKED</span>
          <span className="text-slate-400">|</span>
          <span className="text-slate-200">$0 LIVE RISK</span>
        </div>

        {/* Disabled Live Execution Control */}
        <button
          disabled
          title="Live capital authorization is currently $0. Real exchange routing is physically blocked."
          className="cursor-not-allowed flex items-center gap-1 rounded border border-slate-700 bg-graphite-800/50 px-2 py-0.5 text-[10px] font-medium text-slate-500"
        >
          <ShieldAlert className="h-3 w-3 text-slate-500" />
          <span>LIVE ROUTING DISABLED</span>
        </button>
      </div>
    </header>
  );
};
