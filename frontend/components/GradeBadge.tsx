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

import { useState, useCallback } from "react";
import useSWR from "swr";
import { fetchGradeHistory, type GradeHistoryPoint } from "../lib/api";

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

// ── Grade scoring breakdown reference ────────────────────────────────────────────

const GRADE_COMPONENTS = [
  {
    name: "GAS Score",
    maxPts: 40,
    description: "Primary composite signal. Maps GAS 30–100 → 0–40 pts.",
    thresholds: [
      { min: 75,  label: "Strong tailwind",  pts: "~33–40" },
      { min: 60,  label: "Mild support",      pts: "~20–32" },
      { min: 45,  label: "Mixed signals",     pts: "~10–19" },
      { min: 0,   label: "Weak environment",  pts: "0–9"   },
    ],
  },
  {
    name: "Component Alignment",
    maxPts: 30,
    description: "Do Technical, Sentiment, and Macro all agree?",
    thresholds: [
      { min: 30, label: "All 3 aligned bullish",    pts: "30" },
      { min: 22, label: "2/3 bullish, 1 neutral",   pts: "22" },
      { min: 20, label: "All 3 aligned bearish",    pts: "28" },
      { min: 0,  label: "Mixed / low conviction",   pts: "5–12" },
    ],
  },
  {
    name: "Model Sharpe",
    maxPts: 20,
    description: "Quality of the best ML model (Sharpe ratio on validation data).",
    thresholds: [
      { min: 2.0, label: "Sharpe ≥ 2.0 (exceptional)", pts: "20" },
      { min: 1.0, label: "Sharpe ≥ 1.0 (good)",        pts: "15" },
      { min: 0.5, label: "Sharpe ≥ 0.5 (acceptable)",  pts: "10" },
      { min: 0,   label: "Sharpe < 0.5 (weak)",       pts: "0–5" },
    ],
  },
  {
    name: "Signal Conviction",
    maxPts: 10,
    description: "How far GAS is from neutral (50). High conviction = far from 50.",
    thresholds: [
      { min: 20, label: "High conviction (≥20 pts from neutral)",   pts: "8–10" },
      { min: 10, label: "Moderate conviction (10–19 pts)",           pts: "4–7"  },
      { min: 0,  label: "Low conviction (near neutral)",            pts: "0–3"  },
    ],
  },
];

const GRADE_THRESHOLDS = [
  { grade: "A+", min: 88, color: "text-emerald-300", bg: "bg-emerald-950/40 border-emerald-800/50" },
  { grade: "A",  min: 78, color: "text-emerald-400", bg: "bg-emerald-950/30 border-emerald-900/40" },
  { grade: "B",  min: 65, color: "text-sky-400",     bg: "bg-sky-950/40 border-sky-800/50" },
  { grade: "C",  min: 50, color: "text-amber-400",   bg: "bg-amber-950/30 border-amber-900/40" },
  { grade: "D",  min: 35, color: "text-orange-400",  bg: "bg-orange-950/30 border-orange-900/40" },
  { grade: "F",  min: 0,  color: "text-rose-400",    bg: "bg-rose-950/30 border-rose-900/40" },
];

// ── Inline grade sparkline ────────────────────────────────────────────────────

const GRADE_TO_NUM: Record<string, number> = {
  "A+": 6, "A": 5, "B": 4, "C": 3, "D": 2, "F": 1,
};

export function GradeSparkline({ symbol }: { symbol: string }) {
  const { data } = useSWR(
    symbol ? `grade-history-${symbol}` : null,
    () => fetchGradeHistory(symbol, 10),
    { revalidateOnFocus: false, shouldRetryOnError: false },
  );

  if (!data || data.history.length < 2) return null;

  // history is newest-first — reverse for left-to-right
  const pts = [...data.history].reverse();
  const values = pts.map((p) => GRADE_TO_NUM[p.grade] ?? 3);
  const minV = 1, maxV = 6;
  const w = 40, h = 16;
  const xStep = w / (values.length - 1);

  const pathD = values
    .map((v, i) => {
      const x = i * xStep;
      const y = h - ((v - minV) / (maxV - minV)) * h;
      return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");

  const latestGrade = pts[pts.length - 1]?.grade ?? "C";
  const styles = gradeToStyles(latestGrade);
  const strokeColor =
    latestGrade === "A+" || latestGrade === "A" ? "#34d399" :
    latestGrade === "B"  ? "#38bdf8" :
    latestGrade === "C"  ? "#fbbf24" :
    "#f87171";

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="flex-shrink-0">
      <polyline
        points={values
          .map((v, i) => {
            const x = i * xStep;
            const y = h - ((v - minV) / (maxV - minV)) * h;
            return `${x.toFixed(1)},${y.toFixed(1)}`;
          })
          .join(" ")}
        fill="none"
        stroke={strokeColor}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.8"
      />
      {/* Current value dot */}
      {(() => {
        const last = values[values.length - 1];
        const x = (values.length - 1) * xStep;
        const y = h - ((last - minV) / (maxV - minV)) * h;
        return <circle cx={x.toFixed(1)} cy={y.toFixed(1)} r="2" fill={strokeColor} />;
      })()}
    </svg>
  );
}

// ── Grade Explain Modal (full breakdown) ───────────────────────────────────

function GradeExplainModal({
  grade,
  score,
  tradeable,
  symbol,
  reasons,
  onClose,
}: {
  grade: string;
  score: number | null | undefined;
  tradeable: boolean | null | undefined;
  symbol?: string;
  reasons?: string[];
  onClose: () => void;
}) {
  const styles = gradeToStyles(grade);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 w-full max-w-lg mx-4 shadow-2xl space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className={`text-3xl font-black ${styles.text}`}>{grade}</span>
            {score != null && (
              <span className="text-slate-400 text-sm">{score}/100 points</span>
            )}
            {tradeable != null && (
              <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${
                tradeable
                  ? "text-emerald-400 bg-emerald-950/40 border-emerald-800/50"
                  : "text-slate-500 bg-slate-800/40 border-slate-700/50"
              }`}>
                {tradeable ? "✓ Tradeable" : "✗ No trade"}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-300 text-xl leading-none transition-colors"
          >×</button>
        </div>

        {/* Grade scale reference */}
        <div className="space-y-1.5">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Grade Scale</p>
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-1">
            {GRADE_THRESHOLDS.map((t) => (
              <div
                key={t.grade}
                className={`rounded-lg border px-2 py-1.5 text-center ${
                  t.grade === grade
                    ? `${t.bg} ring-1 ring-offset-1 ring-offset-slate-900 ring-current/30`
                    : "bg-slate-900/30 border-slate-800"
                }`}
              >
                <p className={`text-sm font-black ${
                  t.grade === grade ? t.color : "text-slate-600"
                }`}>{t.grade}</p>
                <p className={`text-[9px] ${
                  t.grade === grade ? "text-slate-400" : "text-slate-700"
                }`}>≥{t.min}pts</p>
              </div>
            ))}
          </div>
        </div>

        {/* Scoring components */}
        <div className="space-y-1.5">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Scoring Components</p>
          <div className="space-y-2">
            {GRADE_COMPONENTS.map((comp) => (
              <div key={comp.name} className="rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2.5 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-300">{comp.name}</span>
                  <span className="text-[10px] text-slate-500">max {comp.maxPts} pts</span>
                </div>
                <p className="text-[10px] text-slate-500 leading-relaxed">{comp.description}</p>
                <div className="h-1 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-sky-600/60"
                    style={{ width: `${(comp.maxPts / 100) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Why this grade — from snapshot reasons */}
        {reasons && reasons.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Why this grade</p>
            <ul className="space-y-1">
              {reasons.map((r, i) => (
                <li key={i} className="text-xs text-slate-400 flex items-start gap-2">
                  <span className="text-slate-600 mt-0.5 flex-shrink-0">•</span>
                  {r}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Grade history sparkline */}
        {symbol && (
          <GradeHistoryRow symbol={symbol} />
        )}

        {/* What would improve it */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/30 px-4 py-3 space-y-1.5">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">What improves the grade?</p>
          <ul className="space-y-1 text-[10px] text-slate-500">
            <li>• <span className="text-slate-400">Higher GAS score</span> — drives 40% of the total</li>
            <li>• <span className="text-slate-400">All 3 components agreeing</span> (Tech + Sent + Macro all bullish or all bearish)</li>
            <li>• <span className="text-slate-400">Better ML model Sharpe</span> — train more data or wait for regime stabilisation</li>
            <li>• <span className="text-slate-400">Stronger conviction</span> — GAS moving further from neutral (50)</li>
          </ul>
        </div>

        <p className="text-[10px] text-slate-600">
          Grades are updated every time a GAS snapshot is computed (approximately every 15 minutes).
          This is an educational signal — not investment advice.
        </p>
      </div>
    </div>
  );
}

function GradeHistoryRow({ symbol }: { symbol: string }) {
  const { data } = useSWR(
    `grade-history-modal-${symbol}`,
    () => fetchGradeHistory(symbol, 10),
    { revalidateOnFocus: false, shouldRetryOnError: false },
  );

  if (!data || data.history.length === 0) return null;

  const pts = [...data.history].reverse(); // oldest first

  return (
    <div className="space-y-1.5">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
        Grade history (last {pts.length} changes)
      </p>
      <div className="flex items-center gap-1.5 overflow-x-auto py-1">
        {pts.map((p, i) => {
          const styles = gradeToStyles(p.grade);
          return (
            <div key={i} className="flex flex-col items-center gap-0.5 flex-shrink-0">
              <span className={`text-[10px] font-black px-1.5 py-0.5 rounded border ${
                styles.bg
              } ${styles.border} ${styles.text}`}>{p.grade}</span>
              <span className="text-[8px] text-slate-700">
                {new Date(p.recorded_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface GradeBadgeProps {
  grade: string | null | undefined;
  score?: number | null;
  tradeable?: boolean | null;
  size?: "xs" | "sm" | "md" | "lg";
  showTooltip?: boolean;
  showTradeable?: boolean;
  showSparkline?: boolean;   // Sprint 28 — inline grade history sparkline
  clickable?: boolean;       // Sprint 28 — click opens full breakdown modal
  symbol?: string;           // Sprint 28 — symbol for history sparkline + modal
  reasons?: string[];        // Sprint 28 — grade reasons from snapshot
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
  showSparkline = false,
  clickable = false,
  symbol,
  reasons,
  className = "",
}: GradeBadgeProps) {
  const [tooltipOpen, setTooltipOpen] = useState(false);
  const [modalOpen, setModalOpen]     = useState(false);

  const handleClick = useCallback((e: React.MouseEvent) => {
    if (!clickable) return;
    e.stopPropagation();
    setModalOpen(true);
  }, [clickable]);

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
    <>
    {modalOpen && (
      <GradeExplainModal
        grade={grade}
        score={score}
        tradeable={tradeable}
        symbol={symbol}
        reasons={reasons}
        onClose={() => setModalOpen(false)}
      />
    )}
    <div className={`relative inline-flex items-center gap-1 ${className}`}>
      {/* Sparkline to the left */}
      {showSparkline && symbol && <GradeSparkline symbol={symbol} />}
      <span
        className={`inline-flex items-center gap-1 rounded-full border ${styles.bg} ${styles.border} ${styles.text} ${sizeClasses} transition-all ${showTooltip ? "cursor-help" : ""} ${clickable ? "cursor-pointer hover:brightness-110" : ""}`}
        onMouseEnter={() => showTooltip && setTooltipOpen(true)}
        onMouseLeave={() => setTooltipOpen(false)}
        onClick={handleClick}
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
    </>
  );
}
