import React from "react";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  variant?: "default" | "warning" | "danger" | "terminal";
}

export function Card({
  children,
  className = "",
  title,
  subtitle,
  action,
  variant = "default",
}: CardProps) {
  const borderVariants = {
    default: "border-slate-300 dark:border-[#1c2230] bg-white dark:bg-[#11141c]/90 text-slate-800 dark:text-slate-200",
    warning: "border-amber-300 dark:border-amber-900/40 bg-amber-50/70 dark:bg-[#16130d]/90 text-amber-950 dark:text-amber-200",
    danger: "border-rose-300 dark:border-rose-900/40 bg-rose-50/70 dark:bg-[#170e10]/90 text-rose-950 dark:text-rose-200",
    terminal: "border-slate-300 dark:border-[#1c2230] bg-slate-50/80 dark:bg-[#0c0e13] text-slate-800 dark:text-slate-200",
  };

  return (
    <div
      className={`rounded-lg border p-4 shadow-sm backdrop-blur-sm transition-colors ${borderVariants[variant]} ${className}`}
    >
      {(title || subtitle || action) && (
        <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-200 dark:border-[#1c2230]/80">
          <div>
            {title && (
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-900 dark:text-slate-100 font-mono-code flex items-center gap-2">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-[11px] text-slate-600 dark:text-slate-400 mt-0.5">{subtitle}</p>
            )}
          </div>
          {action && <div className="flex items-center gap-2">{action}</div>}
        </div>
      )}
      {children}
    </div>
  );
}
