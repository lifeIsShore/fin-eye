"use client";

/**
 * components/FreshnessIndicator.tsx
 *
 * todos-v3.md UX-TRUST-01 — Data freshness indicators on every section.
 *
 * Shows "Last updated X min ago" with a coloured dot:
 *   green  (●) — fresh:   < 30 minutes
 *   amber  (●) — aging:   30–60 minutes
 *   red    (●) — stale:   > 60 minutes
 *   slate  (●) — unknown: no timestamp
 *
 * Usage:
 *   <FreshnessIndicator updatedAt={gasSnapshot?.computed_at} label="GAS" />
 *   <FreshnessIndicator updatedAt={macroData?.fetched_at} label="Macro" maxFreshMinutes={60} />
 *
 * Also exports the raw `useFreshness` hook for when you need just the status.
 */

import React from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

export type FreshnessStatus = "fresh" | "aging" | "stale" | "unknown";

export interface FreshnessInfo {
  status:     FreshnessStatus;
  ageMinutes: number | null;
  label:      string;
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useFreshness(
  updatedAt: string | Date | undefined | null,
  freshMinutes   = 30,
  agingMinutes   = 60,
): FreshnessInfo {
  if (!updatedAt) {
    return { status: "unknown", ageMinutes: null, label: "unknown" };
  }

  const ageMs      = Date.now() - new Date(updatedAt).getTime();
  const ageMinutes = Math.floor(ageMs / 60_000);

  let status: FreshnessStatus;
  let label: string;

  if (ageMinutes < freshMinutes) {
    status = "fresh";
    label  = ageMinutes < 1 ? "just now" : `${ageMinutes}m ago`;
  } else if (ageMinutes < agingMinutes) {
    status = "aging";
    label  = `${ageMinutes}m ago`;
  } else {
    status = "stale";
    const hours = Math.floor(ageMinutes / 60);
    label  = hours >= 1 ? `${hours}h ago` : `${ageMinutes}m ago`;
  }

  return { status, ageMinutes, label };
}

// ── Dot colours ───────────────────────────────────────────────────────────────

const DOT_COLOR: Record<FreshnessStatus, string> = {
  fresh:   "text-emerald-400",
  aging:   "text-amber-400",
  stale:   "text-rose-400",
  unknown: "text-slate-600",
};

const TEXT_COLOR: Record<FreshnessStatus, string> = {
  fresh:   "text-slate-500",
  aging:   "text-amber-400",
  stale:   "text-rose-400",
  unknown: "text-slate-600",
};

// ── Component ─────────────────────────────────────────────────────────────────

interface FreshnessIndicatorProps {
  /** ISO string or Date of last update */
  updatedAt?:      string | Date | null;
  /** Short label for the data source, e.g. "GAS" or "Macro" */
  label?:          string;
  /** Minutes below which data is considered fresh (default 30) */
  freshMinutes?:   number;
  /** Minutes below which data is considered aging (default 60) */
  agingMinutes?:   number;
  /** Show the stale warning text ("data may be outdated") */
  showStaleWarning?: boolean;
  className?:      string;
}

export default function FreshnessIndicator({
  updatedAt,
  label,
  freshMinutes    = 30,
  agingMinutes    = 60,
  showStaleWarning = true,
  className       = "",
}: FreshnessIndicatorProps) {
  const { status, label: ageLabel } = useFreshness(updatedAt, freshMinutes, agingMinutes);

  return (
    <span className={`inline-flex items-center gap-1 ${className}`}>
      <span className={`text-[10px] leading-none ${DOT_COLOR[status]}`}>●</span>
      <span className={`text-[10px] ${TEXT_COLOR[status]}`}>
        {label && <span className="font-medium">{label} </span>}
        {ageLabel}
        {status === "stale" && showStaleWarning && (
          <span className="ml-1 text-rose-400">(stale)</span>
        )}
      </span>
    </span>
  );
}
