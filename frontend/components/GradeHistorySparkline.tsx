"use client";

/**
 * components/GradeHistorySparkline.tsx — Sprint 27
 *
 * A compact visual showing how the signal grade has changed over the last N
 * events for a symbol. Rendered as a row of grade chips (oldest → newest)
 * with directional arrows between them.
 */

import React from "react";
import useSWR from "swr";
import { fetchGradeHistory } from "@/lib/api";

// ── Grade colour map ──────────────────────────────────────────────────────────

const GRADE_TEXT: Record<string, string> = {
  "A+": "text-emerald-300",
  "A":  "text-emerald-400",
  "B":  "text-sky-400",
  "C":  "text-amber-400",
  "D":  "text-orange-400",
  "F":  "text-rose-400",
};

const GRADE_BG: Record<string, string> = {
  "A+": "bg-emerald-950/60 border-emerald-700/60",
  "A":  "bg-emerald-950/40 border-emerald-800/50",
  "B":  "bg-sky-950/50     border-sky-800/50",
  "C":  "bg-amber-950/40   border-amber-800/50",
  "D":  "bg-orange-950/40  border-orange-800/50",
  "F":  "bg-rose-950/40    border-rose-800/50",
};

function gradeText(g: string) { return GRADE_TEXT[g] ?? "text-slate-400"; }
function gradeBg(g: string)   { return GRADE_BG[g]   ?? "bg-slate-800 border-slate-700"; }

// ── Arrow between grades ──────────────────────────────────────────────────────

const GRADE_ORDER = ["F", "D", "C", "B", "A", "A+"];
function gradeRank(g: string) { return GRADE_ORDER.indexOf(g); }

function Arrow({ from, to }: { from: string; to: string }) {
  const delta = gradeRank(to) - gradeRank(from);
  if (delta > 0) return <span className="text-[9px] text-emerald-500 mx-0.5">▲</span>;
  if (delta < 0) return <span className="text-[9px] text-rose-500 mx-0.5">▼</span>;
  return <span className="text-[9px] text-slate-700 mx-0.5">→</span>;
}

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  symbol: string;
  limit?: number;
  /** If true, show a compact single-row chip strip. Default true. */
  compact?: boolean;
}

export default function GradeHistorySparkline({
  symbol,
  limit = 7,
  compact = true,
}: Props) {
  const { data, isLoading } = useSWR(
    symbol ? `grade-history-${symbol}-${limit}` : null,
    () => fetchGradeHistory(symbol, limit),
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );

  if (isLoading) {
    return (
      <div className="flex items-center gap-1 animate-pulse">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-4 w-6 bg-slate-800 rounded border border-slate-700" />
        ))}
      </div>
    );
  }

  if (!data || !data.history || data.history.length === 0) return null;

  // history is newest-first — reverse for left-to-right (oldest → newest)
  const pts = [...data.history].reverse();

  return (
    <div className={`flex items-center ${compact ? "gap-0" : "gap-1"}`}>
      {pts.map((p, i) => (
        <React.Fragment key={i}>
          <div className="flex items-center">
            <span className={`text-[9px] font-black px-1 py-0.5 rounded border transition-colors ${gradeBg(p.grade)} ${gradeText(p.grade)}`}>
              {p.grade}
            </span>
            {i < pts.length - 1 && <Arrow from={p.grade} to={pts[i + 1]?.grade ?? p.grade} />}
          </div>
        </React.Fragment>
      ))}
    </div>
  );
}