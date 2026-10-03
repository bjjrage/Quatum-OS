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
    bg: "bg-slate-800/60",
    text: "text-slate-300",
    border: "border-slate-700/60",
    dotColor: "bg-slate-400",
  },
  emerald: {
    bg: "bg-emerald-950/40",
    text: "text-emerald-400",
    border: "border-emerald-800/50",
    dotColor: "bg-emerald-500",
  },
  amber: {
    bg: "bg-amber-950/40",
    text: "text-amber-400",
    border: "border-amber-800/50",
    dotColor: "bg-amber-500",
  },
  rose: {
    bg: "bg-rose-950/40",
    text: "text-rose-400",
    border: "border-rose-800/50",
    dotColor: "bg-rose-500",
  },
  cyan: {
    bg: "bg-cyan-950/40",
    text: "text-cyan-400",
    border: "border-cyan-800/50",
    dotColor: "bg-cyan-500",
  },
  purple: {
    bg: "bg-purple-950/40",
    text: "text-purple-400",
    border: "border-purple-800/50",
    dotColor: "bg-purple-500",
  },
  blue: {
    bg: "bg-blue-950/40",
    text: "text-blue-400",
    border: "border-blue-800/50",
    dotColor: "bg-blue-500",
  },
  warning: {
    bg: "bg-yellow-950/50",
    text: "text-yellow-300",
    border: "border-yellow-700/60",
    dotColor: "bg-yellow-400",
  },
};

const sizeStyles = {
  xs: "text-[10px] px-1.5 py-0.5 font-medium tracking-wider",
  sm: "text-[11px] px-2 py-0.5 font-medium tracking-wide",
  md: "text-xs px-2.5 py-1 font-semibold tracking-wide",
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
