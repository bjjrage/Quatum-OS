import React from "react";
import { Badge, BadgeVariant } from "./Badge";

interface MetricCardProps {
  label: string;
  value: React.ReactNode;
  subtitle?: string;
  badge?: {
    text: string;
    variant: BadgeVariant;
  };
  icon?: React.ReactNode;
  trend?: {
    direction: "up" | "down" | "neutral";
    value: string;
  };
  onClick?: () => void;
  className?: string;
}

export function MetricCard({
  label,
  value,
  subtitle,
  badge,
  icon,
  trend,
  onClick,
  className = "",
}: MetricCardProps) {
  return (
    <div
      onClick={onClick}
      className={`rounded-lg border border-slate-300 dark:border-[#1b212f] bg-white dark:bg-[#11141c]/90 p-4 shadow-sm transition-all ${
        onClick ? "cursor-pointer hover:border-sky-500 hover:bg-slate-50/80 dark:hover:border-cyan-600/50 dark:hover:bg-[#141824]" : ""
      } ${className}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 font-mono-code">
          {label}
        </span>
        {icon && <span className="text-slate-500 dark:text-slate-500">{icon}</span>}
      </div>

      <div className="mt-2 flex items-baseline justify-between gap-2">
        <div className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 font-mono-code truncate">
          {value}
        </div>
        {badge && (
          <Badge variant={badge.variant} size="xs">
            {badge.text}
          </Badge>
        )}
      </div>

      {(subtitle || trend) && (
        <div className="mt-2 flex items-center justify-between text-[11px] text-slate-600 dark:text-slate-400 font-mono-code">
          {subtitle && <span className="truncate">{subtitle}</span>}
          {trend && (
            <span
              className={`font-semibold ${
                trend.direction === "up"
                  ? "text-emerald-700 dark:text-emerald-400"
                  : trend.direction === "down"
                  ? "text-rose-700 dark:text-rose-400"
                  : "text-slate-600 dark:text-slate-400"
              }`}
            >
              {trend.direction === "up" ? "↑" : trend.direction === "down" ? "↓" : "→"}{" "}
              {trend.value}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
