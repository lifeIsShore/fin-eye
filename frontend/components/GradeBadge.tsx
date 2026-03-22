"use client";

/**
 * components/GradeBadge.tsx — Sprint 21
 *
 * Reusable signal grade badge (A+ → F) drawn from the GAS snapshot.
 * Colour-coded, size-aware, with optional tooltip showing grade description.
 *
 * Usage:
 *   <GradeBadge grade="A+" score={91} tradeable={true} />
 *   <GradeBadge grade="C" size="sm" />
 */

import { useState } from "react";

// ── Grade config ──────────────────────────────────────────────────────────────

const GRADE_STYLES: Record<string, { bg: string; border: string; text: string; dot: string }> = {
  "A+": { bg: "bg-emerald-950/60", border: "border-emerald-600/70", text: "text-emerald-300", dot: "bg-emerald-400" },
  "A":  { bg: "bg-emerald-950/40", border: "border-emerald-700/50", text: "text-emerald-400", dot: "bg-emerald-500" },
  "B":  { bg: "bg-sky-950/50",     border: "border-sky-700/50",     text: "text-sky-300",     dot: "bg-sky-400"    },
  "C":  { bg: "bg-amber-950/40",   border: "border-amber-700/50",   text: "text-amber-400",   dot: "bg-amber-500"  },
  "D":  { bg: "bg-orange-950/40",  border: "border-orange-700/50",  text: "text-orange-400",  dot: "bg-orange-500" },
  "F":  { bg: "bg-rose-950/40",    border: "border-rose-700/50",    text: "text-rose-400",    dot: "bg-rose-500"   },
};

const GRADE_DESCRIPTIONS: Record<string, string> = {
  "A+": "Exceptional — all signals strongly aligned. High-conviction entry.",
  "A":  "Strong alignment — reliable signal with minor caveats.",
  "B":  "Good signal — some disagreement, use with standard risk controls.",
  "C":  "Mixed — caution advised. Monitor only, no new positions.",
  "D":  "Weak — significant disagreements or low model confidence.",
  "F":  "Do not use — conflicting signals or GAS below 30.",
};

function gradeToStyles(grade: string | null | undefined) {
  if (!grade) return GRADE_STYLES["C"];
  return GRADE_STYLES[grade] ?? GRADE_STYLES[grade.replace("+", "")] ?? GRADE_STYLES["C"];
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface GradeBadgeProps {
  grade: string | null | undefined;
  score?: number | null;
  tradeable?: boolean | null;
  size?: "xs" | "sm" | "md" | "lg";
  showTooltip?: boolean;
  showTradeable?: boolean;
  className?: string;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function GradeBadge({
  grade,
  score,
  tradeable,
  size = "sm",
  showTooltip = true,
  showTradeable = false,
  className = "",
}: GradeBadgeProps) {
  const [tooltipOpen, setTooltipOpen] = useState(false);

  if (!grade) return null;

  const styles = gradeToStyles(grade);
  const description = GRADE_DESCRIPTIONS[grade] ?? "";

  const sizeClasses = {
    xs: "text-[9px] px-1.5 py-0.5 font-bold",
    sm: "text-[11px] px-2 py-0.5 font-bold",
    md: "text-xs px-2.5 py-1 font-bold",
    lg: "text-sm px-3 py-1.5 font-bold",
  }[size];

  const dotSize = {
    xs: "h-1 w-1",
    sm: "h-1.5 w-1.5",
    md: "h-2 w-2",
    lg: "h-2.5 w-2.5",
  }[size];

  return (
    <div className={`relative inline-flex items-center gap-1 ${className}`}>
      <span
        className={`inline-flex items-center gap-1 rounded-full border ${styles.bg} ${styles.border} ${styles.text} ${sizeClasses} transition-all ${showTooltip ? "cursor-help" : ""}`}
        onMouseEnter={() => showTooltip && setTooltipOpen(true)}
        onMouseLeave={() => setTooltipOpen(false)}
      >
        <span className={`rounded-full flex-shrink-0 ${styles.dot} ${dotSize}`} />
        {grade}
        {score != null && size !== "xs" && (
          <span className="opacity-60 font-normal ml-0.5">{Math.round(score)}</span>
        )}
      </span>

      {/* Tradeable indicator */}
      {showTradeable && tradeable != null && (
        <span className={`text-[9px] font-semibold ${tradeable ? "text-emerald-500" : "text-slate-600"}`}>
          {tradeable ? "✓ tradeable" : "✗ no trade"}
        </span>
      )}

      {/* Tooltip */}
      {showTooltip && tooltipOpen && description && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 w-52 rounded-lg border border-slate-700 bg-slate-900 p-2.5 shadow-xl pointer-events-none">
          <div className="flex items-center gap-1.5 mb-1">
            <span className={`text-xs font-black ${styles.text}`}>{grade}</span>
            {score != null && (
              <span className="text-[10px] text-slate-500">({Math.round(score)}/100)</span>
            )}
            {tradeable != null && (
              <span className={`ml-auto text-[9px] font-bold ${tradeable ? "text-emerald-400" : "text-rose-400"}`}>
                {tradeable ? "Tradeable" : "No trade"}
              </span>
            )}
          </div>
          <p className="text-[10px] text-slate-400 leading-relaxed">{description}</p>
          {/* Arrow */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-700" />
        </div>
      )}
    </div>
  );
}
