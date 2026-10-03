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
    default: "border-[#1c2230] bg-[#11141c]/90",
    warning: "border-amber-900/40 bg-[#16130d]/90",
    danger: "border-rose-900/40 bg-[#170e10]/90",
    terminal: "border-[#1c2230] bg-[#0c0e13]",
  };

  return (
    <div
      className={`rounded-lg border p-4 shadow-sm backdrop-blur-sm transition-colors ${borderVariants[variant]} ${className}`}
    >
      {(title || subtitle || action) && (
        <div className="flex items-center justify-between pb-3 mb-3 border-b border-[#1c2230]/80">
          <div>
            {title && (
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200 font-mono-code flex items-center gap-2">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-[11px] text-slate-400 mt-0.5">{subtitle}</p>
            )}
          </div>
          {action && <div className="flex items-center gap-2">{action}</div>}
        </div>
      )}
      {children}
    </div>
  );
}
