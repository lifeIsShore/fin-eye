"use client";

/**
 * components/WhatChangedToday.tsx
 *
 * todos-v3.md UX-GROWTH-02 — "What Changed Today" widget.
 *
 * Shows GAS score changes for all watchlist symbols since the last snapshot.
 * Gives power users a daily reason to return — they can see at a glance
 * which symbols moved, by how much, and in which direction.
 *
 * Features:
 *   - Delta arrows: ↑ (improved), ↓ (degraded), → (stable, < 1pt change)
 *   - Colour-coded by direction: emerald / rose / slate
 *   - Sorted by absolute delta descending (biggest movers first)
 *   - Clicking a row switches the dashboard to that symbol
 *   - Refreshes every 5 minutes via SWR
 *   - Graceful empty state when no watchlist symbols have snapshots yet
 */

import React from "react";
import useSWR from "swr";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface GasBatchEntry {
  symbol:           string;
  gas_score:        number;
  weather_label:    string;
  regime:           string;
  component_scores: { technical?: number; sentiment?: number; macro?: number };
  computed_at:      string;
  prev_gas_score:   number | null;
  delta:            number | null;
  // Signal grade — Sprint 21
  signal_grade?:       string | null;
  signal_grade_score?: number | null;
  signal_tradeable?:   boolean | null;
}

// ── Fetch ─────────────────────────────────────────────────────────────────────

async function fetchBatchSnapshots(symbols: string[]): Promise<GasBatchEntry[]> {
  if (symbols.length === 0) return [];
  const res = await fetch(`${API_BASE}/api/v1/admin/gas/snapshots/batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbols }),
    cache: "no-store",
  });
  if (!res.ok) return [];
  return res.json();
}

// ── Helper ────────────────────────────────────────────────────────────────────

function deltaLabel(delta: number | null): { icon: string; color: string; text: string } {
  if (delta === null) return { icon: "—", color: "text-slate-600", text: "no prev" };
  if (delta >=  2) return { icon: "↑", color: "text-emerald-400", text: `+${delta.toFixed(1)}` };
  if (delta <= -2) return { icon: "↓", color: "text-rose-400",    text: delta.toFixed(1) };
  return             { icon: "→", color: "text-slate-500",    text: delta >= 0 ? `+${delta.toFixed(1)}` : delta.toFixed(1) };
}

function gasColor(score: number): string {
  if (score >= 65) return "text-emerald-400";
  if (score >= 40) return "text-amber-400";
  return "text-rose-400";
}

function regimeColor(regime: string): string {
  if (regime === "Risk-On")     return "text-emerald-400";
  if (regime === "Risk-Off")    return "text-rose-400";
  return "text-amber-400";
}

// ── Component ─────────────────────────────────────────────────────────────────

interface WhatChangedTodayProps {
  /** Symbols to check — typically from the watchlist */
  symbols:        string[];
  /** Called when user clicks a symbol row */
  onSelectSymbol: (symbol: string) => void;
  /** Currently active symbol — highlighted in the list */
  activeSymbol?:  string;
}

export default function WhatChangedToday({
  symbols,
  onSelectSymbol,
  activeSymbol,
}: WhatChangedTodayProps) {
  const { data, isLoading, error } = useSWR(
    symbols.length > 0 ? ["gas-batch", ...symbols] : null,
    () => fetchBatchSnapshots(symbols),
    { refreshInterval: 5 * 60_000, shouldRetryOnError: false },
  );

  // Sort: biggest absolute delta first, then alphabetical
  const sorted = React.useMemo(() => {
    if (!data) return [];
    return [...data].sort((a, b) => {
      const da = Math.abs(a.delta ?? 0);
      const db = Math.abs(b.delta ?? 0);
      if (da !== db) return db - da;
      return a.symbol.localeCompare(b.symbol);
    });
  }, [data]);

  const hasChanges = sorted.some((s) => s.delta !== null && Math.abs(s.delta) >= 2);

  if (symbols.length === 0) return null;

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <span className="text-base">📊</span>
          <h3 className="text-sm font-semibold text-slate-200">What Changed</h3>
          {hasChanges && (
            <span className="rounded-full bg-amber-900/40 border border-amber-700/40 px-2 py-0.5 text-[10px] font-bold text-amber-400">
              MOVES
            </span>
          )}
        </div>
        <span className="text-[10px] text-slate-600">GAS vs prev snapshot</span>
      </div>

      {/* Body */}
      <div className="divide-y divide-slate-800/60">
        {isLoading && (
          <div className="space-y-2 p-3">
            {Array.from({ length: Math.min(symbols.length, 4) }).map((_, i) => (
              <div key={i} className="flex items-center gap-3 animate-pulse">
                <div className="h-3 w-12 rounded bg-slate-800" />
                <div className="h-3 w-8 rounded bg-slate-800 ml-auto" />
                <div className="h-3 w-10 rounded bg-slate-800" />
              </div>
            ))}
          </div>
        )}

        {!isLoading && (error || sorted.length === 0) && (
          <div className="px-4 py-5 text-center">
            <p className="text-xs text-slate-500">
              {error
                ? "Could not load snapshot data."
                : "No snapshots yet — run GAS precompute to see changes."}
            </p>
          </div>
        )}

        {!isLoading && sorted.map((entry) => {
          const dl        = deltaLabel(entry.delta);
          const isActive  = entry.symbol === activeSymbol;

          return (
            <button
              key={entry.symbol}
              onClick={() => onSelectSymbol(entry.symbol)}
              className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors hover:bg-slate-800/50 ${
                isActive ? "bg-slate-800/60" : ""
              }`}
            >
              {/* Symbol */}
              <span className={`text-sm font-bold font-mono w-14 flex-shrink-0 ${
                isActive ? "text-sky-400" : "text-slate-200"
              }`}>
                {entry.symbol}
              </span>

              {/* GAS score */}
              <span className={`text-sm font-bold tabular-nums w-10 flex-shrink-0 ${gasColor(entry.gas_score)}`}>
                {entry.gas_score.toFixed(0)}
              </span>

              {/* Weather label — truncated */}
              <span className="text-[11px] text-slate-500 flex-1 truncate hidden sm:block">
                {entry.weather_label}
              </span>

              {/* Regime */}
              <span className={`text-[10px] font-medium flex-shrink-0 hidden md:block ${regimeColor(entry.regime)}`}>
                {entry.regime}
              </span>

              {/* Delta */}
              <div className="flex items-center gap-1 flex-shrink-0 w-16 justify-end">
                <span className={`text-base leading-none ${dl.color}`}>{dl.icon}</span>
                <span className={`text-xs font-mono tabular-nums font-bold ${dl.color}`}>
                  {dl.text}
                </span>
              </div>
            </button>
          );
        })}
      </div>

      {/* Footer */}
      {sorted.length > 0 && (
        <div className="px-4 py-2 border-t border-slate-800/60">
          <p className="text-[10px] text-slate-600">
            {sorted.length} symbol{sorted.length !== 1 ? "s" : ""} · updates every 5 min
          </p>
        </div>
      )}
    </div>
  );
}
