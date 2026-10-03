import React from "react";
import { AlertCircle, Clock, Lock } from "lucide-react";
import { Badge } from "./Badge";

interface EmptyStateProps {
  title: string;
  message: string;
  badge?: string;
  type?: "pending" | "locked" | "unavailable";
  className?: string;
}

export function EmptyState({
  title,
  message,
  badge = "NO LIVE DATA",
  type = "unavailable",
  className = "",
}: EmptyStateProps) {
  const icons = {
    pending: <Clock className="w-8 h-8 text-amber-500" />,
    locked: <Lock className="w-8 h-8 text-rose-500" />,
    unavailable: <AlertCircle className="w-8 h-8 text-slate-500" />,
  };

  const badgeVariants = {
    pending: "amber" as const,
    locked: "rose" as const,
    unavailable: "slate" as const,
  };

  return (
    <div
      className={`flex flex-col items-center justify-center p-8 rounded-lg border border-dashed border-slate-300 dark:border-[#232b3c] bg-slate-50/80 dark:bg-[#0c0e14]/50 text-center ${className}`}
    >
      <div className="mb-3 p-3 rounded-full bg-slate-200/70 dark:bg-slate-900/60 border border-slate-300 dark:border-slate-800">
        {icons[type]}
      </div>
      <div className="flex items-center gap-2 mb-2">
        <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-200 font-mono-code">{title}</h4>
        <Badge variant={badgeVariants[type]} size="xs">
          {badge}
        </Badge>
      </div>
      <p className="text-xs text-slate-600 dark:text-slate-400 max-w-md font-mono-code leading-relaxed">
        {message}
      </p>
    </div>
  );
}
