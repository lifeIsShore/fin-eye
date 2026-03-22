"use client";

/**
 * components/EarningsCalendarStrip.tsx — Sprint 14
 *
 * Compact upcoming-earnings strip for watchlist symbols shown on the dashboard.
 * Fetches the earnings calendar for all watchlist symbols via the batch endpoint
 * and displays them sorted by days_until ascending.
 *
 * Features:
 *   - Shows symbol, company name, date, days-until countdown, EPS estimate
 *   - Urgency colour coding: amber (<= 3 days), blue (<=14), slate (further)
 *   - Clicking navigates to the full /earnings page with that symbol
 *   - Gracefully empty when no earnings are upcoming in the next 30 days
 *   - Refreshes every 30 minutes
 */

import React, { useMemo } from "react";
import useSWR from "swr";
import Link from "next/link";
import { Calendar, ChevronRight } from "lucide-react";
import { fetchEarningsCalendar, type UpcomingEarningsDto } from "../lib/api";

interface Props {
  symbols: string[];
}

function fmtEps(v: number | null): string {
  if (v == null) return "";
  return `EPS est. ${v >= 0 ? "$" : "-$"}${Math.abs(v).toFixed(2)}`;
}

function fmtDate(d: string): string {
  return new Date(d + "T00:00:00").toLocaleDateString("en-US", {
    month: "short", day: "numeric",
  });
}

function urgencyClasses(daysUntil: number): {
  border: string; bg: string; dot: string; days: string;
} {
  if (daysUntil <= 3) return {
    border: "border-amber-700/50",
    bg:     "bg-amber-950/20",
    dot:    "bg-amber-400",
    days:   "text-amber-300 font-bold",
  };
  if (daysUntil <= 14) return {
    border: "border-sky-800/40",
    bg:     "bg-sky-950/15",
    dot:    "bg-sky-400",
    days:   "text-sky-300",
  };
  return {
    border: "border-slate-800",
    bg:     "bg-slate-900/30",
    dot:    "bg-slate-600",
    days:   "text-slate-400",
  };
}

export default function EarningsCalendarStrip({ symbols }: Props) {
  const { data, isLoading } = useSWR(
    symbols.length > 0 ? ["earnings-calendar", ...symbols] : null,
    () => fetchEarningsCalendar(symbols, 30),
    { refreshInterval: 30 * 60_000, shouldRetryOnError: false },
  );

  const sorted = useMemo(
    () => [...(data ?? [])].sort((a, b) => a.days_until - b.days_until),
    [data],
  );

  if (isLoading && !data) {
    return (
      <div className="space-y-2 animate-pulse">
        {[1, 2].map((i) => (
          <div key={i} className="h-12 rounded-xl bg-slate-800/50" />
        ))}
      </div>
    );
  }

  if (!sorted.length) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/20 px-4 py-3 text-xs text-slate-600">
        <Calendar className="h-3.5 w-3.5 flex-shrink-0" />
        No earnings in the next 30 days for watched symbols.
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {sorted.map((e: UpcomingEarningsDto) => {
        const cls = urgencyClasses(e.days_until);
        const daysLabel =
          e.days_until === 0 ? "Today!" :
          e.days_until === 1 ? "Tomorrow" :
          `${e.days_until}d`;

        return (
          <Link
            key={e.symbol}
            href={`/earnings?symbol=${e.symbol}`}
            className={`group flex items-center gap-3 rounded-xl border ${cls.border} ${cls.bg} px-3 py-2 hover:border-slate-600 transition-colors`}
          >
            {/* Dot + symbol */}
            <span className={`h-2 w-2 rounded-full flex-shrink-0 ${cls.dot}`} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-bold text-slate-100 font-mono">{e.symbol}</span>
                {e.eps_estimate != null && (
                  <span className="text-[10px] text-slate-600 hidden sm:inline">{fmtEps(e.eps_estimate)}</span>
                )}
              </div>
              <p className="text-[10px] text-slate-500 truncate">{e.company_name} · {fmtDate(e.earnings_date)}</p>
            </div>

            {/* Days countdown */}
            <div className="flex-shrink-0 flex items-center gap-1">
              <span className={`text-xs tabular-nums ${cls.days}`}>{daysLabel}</span>
              <ChevronRight className="h-3 w-3 text-slate-700 group-hover:text-slate-500 transition-colors" />
            </div>
          </Link>
        );
      })}

      <Link
        href="/earnings"
        className="flex items-center gap-1 text-[10px] text-slate-600 hover:text-sky-400 transition-colors pl-1 pt-0.5"
      >
        <Calendar className="h-3 w-3" /> Full earnings calendar →
      </Link>
    </div>
  );
}
