import React from "react";

export type BadgeVariant =
  | "slate"
  | "emerald"
  | "amber"
  | "rose"
  | "cyan"
  | "purple"
  | "blue"
  | "warning";

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: "xs" | "sm" | "md";
  dot?: boolean;
  className?: string;
}

const variantStyles: Record<BadgeVariant, { bg: string; text: string; border: string; dotColor: string }> = {
  slate: {
    bg: "bg-slate-100 dark:bg-slate-800/60",
    text: "text-slate-800 dark:text-slate-300",
    border: "border-slate-300 dark:border-slate-700/60",
    dotColor: "bg-slate-600 dark:bg-slate-400",
  },
  emerald: {
    bg: "bg-emerald-100 dark:bg-emerald-950/40",
    text: "text-emerald-900 dark:text-emerald-400",
    border: "border-emerald-300 dark:border-emerald-800/50",
    dotColor: "bg-emerald-600 dark:bg-emerald-500",
  },
  amber: {
    bg: "bg-amber-100 dark:bg-amber-950/40",
    text: "text-amber-950 dark:text-amber-400",
    border: "border-amber-300 dark:border-amber-800/50",
    dotColor: "bg-amber-600 dark:bg-amber-500",
  },
  rose: {
    bg: "bg-rose-100 dark:bg-rose-950/40",
    text: "text-rose-950 dark:text-rose-400",
    border: "border-rose-300 dark:border-rose-800/50",
    dotColor: "bg-rose-600 dark:bg-rose-500",
  },
  cyan: {
    bg: "bg-sky-100 dark:bg-cyan-950/40",
    text: "text-sky-950 dark:text-cyan-400",
    border: "border-sky-300 dark:border-cyan-800/50",
    dotColor: "bg-sky-600 dark:bg-cyan-500",
  },
  purple: {
    bg: "bg-purple-100 dark:bg-purple-950/40",
    text: "text-purple-950 dark:text-purple-400",
    border: "border-purple-300 dark:border-purple-800/50",
    dotColor: "bg-purple-600 dark:bg-purple-500",
  },
  blue: {
    bg: "bg-blue-100 dark:bg-blue-950/40",
    text: "text-blue-950 dark:text-blue-400",
    border: "border-blue-300 dark:border-blue-800/50",
    dotColor: "bg-blue-600 dark:bg-blue-500",
  },
  warning: {
    bg: "bg-yellow-100 dark:bg-yellow-950/50",
    text: "text-yellow-950 dark:text-yellow-300",
    border: "border-yellow-300 dark:border-yellow-700/60",
    dotColor: "bg-yellow-600 dark:bg-yellow-400",
  },
};

const sizeStyles = {
  xs: "text-[10px] px-1.5 py-0.5 font-semibold tracking-wider",
  sm: "text-[11px] px-2 py-0.5 font-semibold tracking-wide",
  md: "text-xs px-2.5 py-1 font-bold tracking-wide",
};

export function Badge({
  children,
  variant = "slate",
  size = "xs",
  dot = false,
  className = "",
}: BadgeProps) {
  const v = variantStyles[variant] || variantStyles.slate;
  const s = sizeStyles[size];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded border uppercase font-mono-code ${v.bg} ${v.text} ${v.border} ${s} ${className}`}
    >
      {dot && (
        <span className={`w-1.5 h-1.5 rounded-full ${v.dotColor} animate-pulse-subtle`} />
      )}
      {children}
    </span>
  );
}
