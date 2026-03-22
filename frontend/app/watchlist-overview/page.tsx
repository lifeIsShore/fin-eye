"use client";

/**
 * /watchlist-overview — Watchlist Overview page (todos-v3.md POLISH-01)
 *
 * Shows a compact GAS card for every watchlist symbol at a glance:
 *   symbol · company name (where available) · GAS score · weather label ·
 *   regime · delta vs previous snapshot · component bars
 *
 * Sort modes: GAS desc (default), alpha, delta (biggest movers first)
 * Clicking any row navigates to the Dashboard with that symbol active.
 */

import React, { useState, useMemo } from "react";
import useSWR from "swr";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowUpDown, TrendingUp, TrendingDown, Minus, RefreshCw, GitCompare, X as XIcon } from "lucide-react";
import { fetchWatchlist } from "../../lib/api";
import { useSymbol } from "../../lib/symbolContext";
import type { GasBatchEntry } from "../../components/WhatChangedToday";
import GasSparkline from "../../components/GasSparkline";
import GradeBadge from "../../components/GradeBadge";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

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

// ── Helpers ───────────────────────────────────────────────────────────────────

function gasScoreColor(score: number): string {
  if (score >= 65) return "text-emerald-400";
  if (score >= 40) return "text-amber-400";
  return "text-rose-400";
}

function gasBarColor(score: number): string {
  if (score >= 65) return "bg-emerald-500";
  if (score >= 40) return "bg-amber-500";
  return "bg-rose-500";
}

function regimeBadgeClass(regime: string): string {
  if (regime === "Risk-On")  return "text-emerald-400 bg-emerald-950/40 border-emerald-800/50";
  if (regime === "Risk-Off") return "text-rose-400 bg-rose-950/40 border-rose-800/50";
  return "text-amber-400 bg-amber-950/30 border-amber-800/40";
}

function DeltaDisplay({ delta }: { delta: number | null }) {
  if (delta === null) return <span className="text-slate-600 text-xs">—</span>;
  if (delta >=  2)    return <span className="text-emerald-400 text-xs font-bold">↑ +{delta.toFixed(1)}</span>;
  if (delta <= -2)    return <span className="text-rose-400 text-xs font-bold">↓ {delta.toFixed(1)}</span>;
  return                     <span className="text-slate-500 text-xs">→ {delta >= 0 ? "+" : ""}{delta.toFixed(1)}</span>;
}

function ComponentBar({ label, value }: { label: string; value: number | undefined }) {
  const v = value ?? 50;
  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-[9px] text-slate-600">
        <span>{label}</span>
        <span>{v.toFixed(0)}</span>
      </div>
      <div className="h-1 rounded-full bg-slate-800 overflow-hidden">
        <div
          className={`h-full rounded-full ${gasBarColor(v)}`}
          style={{ width: `${Math.min(100, v)}%` }}
        />
      </div>
    </div>
  );
}

// ── Sort types ────────────────────────────────────────────────────────────────

type SortMode = "gas_desc" | "gas_asc" | "alpha" | "delta_desc";
type GradeFilter = "all" | "A+" | "A_above" | "B_above" | "tradeable";

const GRADE_ORDER = ["A+", "A", "B", "C", "D", "F"];

function gradeRank(g: string | null | undefined): number {
  if (!g) return 99;
  return GRADE_ORDER.indexOf(g) === -1 ? 99 : GRADE_ORDER.indexOf(g);
}

function passesGradeFilter(entry: GasBatchEntry, filter: GradeFilter): boolean {
  if (filter === "all") return true;
  const g = entry.signal_grade;
  if (!g) return false;
  if (filter === "A+")      return g === "A+";
  if (filter === "A_above") return gradeRank(g) <= 1;  // A+ or A
  if (filter === "B_above") return gradeRank(g) <= 2;  // A+, A, B
  if (filter === "tradeable") return entry.signal_tradeable === true;
  return true;
}

const GRADE_FILTER_LABELS: Record<GradeFilter, string> = {
  all:       "All",
  A_above:   "A & above",
  "A+":      "A+ only",
  B_above:   "B & above",
  tradeable: "Tradeable",
};

// -- Comparison Panel (Sprint 19) --

function ComparisonPanel({
  a,
  b,
  onClose,
}: {
  a: GasBatchEntry;
  b: GasBatchEntry;
  onClose: () => void;
}) {
  const rows = [
    { label: "GAS Score",  key: "gas_score",  fmt: (v: any) => typeof v === "number" ? v.toFixed(0) : "--" },
    { label: "Delta",      key: "delta",       fmt: (v: any) => v != null ? `${v >= 0 ? "+" : ""}${v.toFixed(1)}` : "--" },
    { label: "Regime",     key: "regime",      fmt: (v: any) => v ?? "--" },
    { label: "Signal",     key: "weather_label", fmt: (v: any) => v ?? "--" },
    { label: "Technical",  key: "tech",        fmt: (v: any) => typeof v === "number" ? v.toFixed(0) : "--" },
    { label: "Sentiment",  key: "sent",        fmt: (v: any) => typeof v === "number" ? v.toFixed(0) : "--" },
    { label: "Macro",      key: "macro",       fmt: (v: any) => typeof v === "number" ? v.toFixed(0) : "--" },
  ];

  const getVal = (entry: GasBatchEntry, key: string): any => {
    if (key === "tech")  return entry.component_scores?.technical;
    if (key === "sent")  return entry.component_scores?.sentiment;
    if (key === "macro") return entry.component_scores?.macro;
    return (entry as any)[key];
  };

  const numColor = (v: number | null | undefined) =>
    v == null ? "text-slate-500" : v >= 65 ? "text-emerald-400" : v >= 40 ? "text-amber-400" : "text-rose-400";

  return (
    <div className="rounded-2xl border border-sky-800/40 bg-sky-950/20 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitCompare className="h-4 w-4 text-sky-400" />
          <h2 className="text-sm font-bold text-slate-100">
            <span className="text-sky-300 font-mono">{a.symbol}</span>
            {" vs "}
            <span className="text-violet-300 font-mono">{b.symbol}</span>
          </h2>
        </div>
        <button onClick={onClose} className="p-1 rounded text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors">
          <XIcon className="h-4 w-4" />
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-800">
              <th className="text-left py-2 pr-4 text-slate-500 font-medium">Metric</th>
              <th className="text-center py-2 px-3 text-sky-300 font-mono font-bold">{a.symbol}</th>
              <th className="text-center py-2 px-3 text-violet-300 font-mono font-bold">{b.symbol}</th>
              <th className="text-left py-2 pl-3 text-slate-500 font-medium">Edge</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {rows.map(({ label, key, fmt }) => {
              const va = getVal(a, key);
              const vb = getVal(b, key);
              const numA = typeof va === "number" ? va : null;
              const numB = typeof vb === "number" ? vb : null;
              const edge = numA !== null && numB !== null
                ? numA > numB + 2 ? a.symbol : numB > numA + 2 ? b.symbol : "Tied"
                : null;
              return (
                <tr key={key} className="hover:bg-slate-800/20">
                  <td className="py-2 pr-4 text-slate-400">{label}</td>
                  <td className={`py-2 px-3 text-center font-mono font-semibold ${numA !== null ? numColor(numA) : "text-slate-300"}`}>{fmt(va)}</td>
                  <td className={`py-2 px-3 text-center font-mono font-semibold ${numB !== null ? numColor(numB) : "text-slate-300"}`}>{fmt(vb)}</td>
                  <td className="py-2 pl-3">
                    {edge === a.symbol && <span className="text-[10px] font-bold text-sky-400">{a.symbol} ↑</span>}
                    {edge === b.symbol && <span className="text-[10px] font-bold text-violet-400">{b.symbol} ↑</span>}
                    {edge === "Tied"    && <span className="text-[10px] text-slate-600">≈</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {[a, b].map((entry) => (
          <div key={entry.symbol} className="space-y-1">
            <p className="text-[10px] font-mono text-slate-400">{entry.symbol} &mdash; 7-day GAS</p>
            <div onClick={(e) => e.stopPropagation()}>
              <GasSparkline symbol={entry.symbol} limit={7} width={200} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const SORT_LABELS: Record<SortMode, string> = {
  gas_desc:   "GAS ↓",
  gas_asc:    "GAS ↑",
  alpha:      "A–Z",
  delta_desc: "Biggest Move",
};

// ── Main page ─────────────────────────────────────────────────────────────────

export default function WatchlistOverviewPage() {
  const router = useRouter();
  const { setSymbol } = useSymbol();
  const [sort, setSort]             = useState<SortMode>("gas_desc");
  const [gradeFilter, setGradeFilter]   = useState<GradeFilter>("all");
  const [compareMode, setCompareMode]   = useState(false);
  const [compareA, setCompareA]         = useState<GasBatchEntry | null>(null);
  const [compareB, setCompareB]         = useState<GasBatchEntry | null>(null);

  // Load watchlist symbols
  const { data: watchlist, isLoading: wlLoading } = useSWR(
    "watchlist",
    fetchWatchlist,
    { shouldRetryOnError: false },
  );
  const symbols = useMemo(
    () => (watchlist ?? []).map((w) => w.symbol),
    [watchlist],
  );

  // Load GAS batch
  const {
    data: snapshots,
    isLoading: snapLoading,
    mutate: refreshSnapshots,
  } = useSWR(
    symbols.length > 0 ? ["gas-batch-overview", ...symbols] : null,
    () => fetchBatchSnapshots(symbols),
    { refreshInterval: 5 * 60_000, shouldRetryOnError: false },
  );

  // Build a map so missing symbols still show a stub
  const snapMap = useMemo(() => {
    const m: Record<string, GasBatchEntry> = {};
    (snapshots ?? []).forEach((s) => (m[s.symbol] = s));
    return m;
  }, [snapshots]);

  // Sort + filter
  const sorted = useMemo(() => {
    const list = symbols
      .map((sym) => snapMap[sym] ?? null)
      .filter((entry): entry is GasBatchEntry =>
        entry !== null && passesGradeFilter(entry, gradeFilter)
      );
    return [...list].sort((a, b) => {
      if (sort === "gas_desc")   return b.gas_score - a.gas_score;
      if (sort === "gas_asc")    return a.gas_score - b.gas_score;
      if (sort === "alpha")      return a.symbol.localeCompare(b.symbol);
      if (sort === "delta_desc") return Math.abs(b.delta ?? 0) - Math.abs(a.delta ?? 0);
      return 0;
    });
  }, [symbols, snapMap, sort, gradeFilter]);

  const hiddenCount = symbols.length - sorted.length;

  const isLoading = wlLoading || snapLoading;

  const handleSelect = (symbol: string) => {
    setSymbol(symbol);
    router.push("/");
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-slate-100">
            Watchlist Overview
          </h1>
          <p className="text-sm text-slate-400 mt-0.5">
            GAS snapshot for all {symbols.length} tracked symbol{symbols.length !== 1 ? "s" : ""}.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2">
          {/* Grade filter */}
          <div className="flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900 p-0.5">
            {(Object.keys(GRADE_FILTER_LABELS) as GradeFilter[]).map((f) => (
              <button
                key={f}
                onClick={() => setGradeFilter(f)}
                className={`px-2.5 py-1.5 rounded text-[11px] font-semibold transition-colors ${
                  gradeFilter === f
                    ? "bg-slate-700 text-slate-100"
                    : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {GRADE_FILTER_LABELS[f]}
              </button>
            ))}
          </div>

          {/* Sort selector */}
          <div className="flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900 p-0.5">
            {(Object.keys(SORT_LABELS) as SortMode[]).map((s) => (
              <button
                key={s}
                onClick={() => setSort(s)}
                className={`px-2.5 py-1.5 rounded text-[11px] font-medium transition-colors ${
                  sort === s
                    ? "bg-slate-700 text-slate-100"
                    : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {SORT_LABELS[s]}
              </button>
            ))}
          </div>

          {/* Compare mode toggle */}
          <button
            onClick={() => {
              setCompareMode(m => !m);
              setCompareA(null);
              setCompareB(null);
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
              compareMode
                ? "border-sky-600 bg-sky-950/40 text-sky-400"
                : "border-slate-700 bg-slate-900 text-slate-400 hover:text-slate-200"
            }`}
          >
            <GitCompare className="h-3.5 w-3.5" />
            {compareMode ? "Exit Compare" : "Compare"}
          </button>

          {/* Refresh */}
          <button
            onClick={() => refreshSnapshots()}
            className="p-2 rounded-lg border border-slate-700 text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors"
            title="Refresh"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Grade filter summary */}
      {gradeFilter !== "all" && !isLoading && (
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span>Showing <span className="font-semibold text-slate-300">{sorted.length}</span> of {symbols.length} symbols</span>
          {hiddenCount > 0 && (
            <span>({hiddenCount} hidden by grade filter)</span>
          )}
          <button
            onClick={() => setGradeFilter("all")}
            className="text-sky-500 hover:text-sky-400 transition-colors ml-1"
          >
            Clear filter
          </button>
        </div>
      )}

      {/* Compare instruction banner */}
      {compareMode && !(compareA && compareB) && (
        <div className="rounded-xl border border-sky-800/40 bg-sky-950/15 px-4 py-3 text-sm text-sky-300 flex items-center gap-3">
          <GitCompare className="h-4 w-4 flex-shrink-0" />
          <span>
            {!compareA
              ? "Click a symbol card to select the first symbol to compare."
              : `${compareA.symbol} selected — now click a second symbol to compare.`}
          </span>
        </div>
      )}

      {/* Comparison Panel */}
      {compareMode && compareA && compareB && (
        <ComparisonPanel
          a={compareA}
          b={compareB}
          onClose={() => { setCompareA(null); setCompareB(null); }}
        />
      )}

      {/* Empty watchlist */}
      {!isLoading && symbols.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 gap-4 text-center">
          <span className="text-4xl">📋</span>
          <div>
            <p className="text-slate-300 font-semibold">Your watchlist is empty</p>
            <p className="text-slate-500 text-sm mt-1">
              Add symbols from the Dashboard to see their GAS scores here.
            </p>
          </div>
          <Link
            href="/"
            className="mt-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium px-4 py-2 transition-colors"
          >
            Go to Dashboard
          </Link>
        </div>
      )}

      {/* Skeleton */}
      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: Math.max(symbols.length, 3) }).map((_, i) => (
            <div
              key={i}
              className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 animate-pulse space-y-3"
            >
              <div className="flex justify-between">
                <div className="h-4 w-16 rounded bg-slate-800" />
                <div className="h-6 w-10 rounded bg-slate-800" />
              </div>
              <div className="h-2 w-full rounded-full bg-slate-800" />
              <div className="grid grid-cols-3 gap-2">
                {[0, 1, 2].map((j) => (
                  <div key={j} className="space-y-1">
                    <div className="h-2 w-full rounded bg-slate-800" />
                    <div className="h-1.5 w-full rounded-full bg-slate-800" />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Symbol cards */}
      {!isLoading && sorted.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {sorted.map((entry) => {
            const sym = entry?.symbol ?? "";
            if (!sym) return null;

            if (!entry) {
              // Symbol in watchlist but no snapshot yet
              return (
                <div
                  key={sym}
                  className="rounded-2xl border border-slate-800 bg-slate-900/20 p-4 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold text-slate-400">{sym}</span>
                    <span className="text-[10px] text-slate-600">No snapshot</span>
                  </div>
                  <p className="text-xs text-slate-600">
                    Train models and run GAS precompute to see this symbol&apos;s score.
                  </p>
                </div>
              );
            }

            const isSelectedA  = compareA?.symbol === sym;
            const isSelectedB  = compareB?.symbol === sym;
            const isHighlighted = isSelectedA || isSelectedB;

            const handleCardClick = () => {
              if (!compareMode) { handleSelect(sym); return; }
              if (!compareA) { setCompareA(entry); return; }
              if (!compareB && entry.symbol !== compareA.symbol) { setCompareB(entry); return; }
              // clicking same as A resets A
              if (entry.symbol === compareA.symbol) { setCompareA(compareB); setCompareB(null); return; }
              // clicking same as B resets B
              if (entry.symbol === compareB?.symbol) { setCompareB(null); return; }
            };

            return (
              <button
                key={sym}
                onClick={handleCardClick}
                className={`rounded-2xl border ${
                  isSelectedA ? "border-sky-500 ring-1 ring-sky-500/40" :
                  isSelectedB ? "border-violet-500 ring-1 ring-violet-500/40" :
                  compareMode ? "border-slate-700 hover:border-sky-700" :
                  "border-slate-800 hover:border-slate-600"
                } bg-slate-900/40 hover:bg-slate-900/70 p-4 text-left transition-all space-y-3 group relative`}
              >
                {/* Compare badge */}
                {isSelectedA && (
                  <span className="absolute top-2 right-2 text-[9px] font-bold bg-sky-600 text-white rounded px-1.5 py-0.5">A</span>
                )}
                {isSelectedB && (
                  <span className="absolute top-2 right-2 text-[9px] font-bold bg-violet-600 text-white rounded px-1.5 py-0.5">B</span>
                )}

                {/* Top row: symbol + GAS score + delta */}
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-black text-slate-100 font-mono">
                        {sym}
                      </span>
                      <GradeBadge
                        grade={entry.signal_grade}
                        score={entry.signal_grade_score}
                        tradeable={entry.signal_tradeable}
                        size="xs"
                      />
                      <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-full border ${regimeBadgeClass(entry.regime)}`}>
                        {entry.regime}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-0.5 truncate">
                      {entry.weather_label}
                    </p>
                  </div>

                  <div className="flex-shrink-0 text-right">
                    <p className={`text-2xl font-black tabular-nums leading-none ${gasScoreColor(entry.gas_score)}`}>
                      {entry.gas_score.toFixed(0)}
                    </p>
                    <div className="mt-0.5 flex justify-end">
                      <DeltaDisplay delta={entry.delta} />
                    </div>
                  </div>
                </div>

                {/* GAS bar */}
                <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${gasBarColor(entry.gas_score)}`}
                    style={{ width: `${Math.min(100, entry.gas_score)}%` }}
                  />
                </div>

                {/* Component sub-bars */}
                <div className="grid grid-cols-3 gap-2">
                  <ComponentBar label="Tech"  value={entry.component_scores?.technical} />
                  <ComponentBar label="Sent"  value={entry.component_scores?.sentiment} />
                  <ComponentBar label="Macro" value={entry.component_scores?.macro} />
                </div>

                {/* 7-day GAS sparkline */}
                <div onClick={(e) => e.stopPropagation()}>
                  <GasSparkline symbol={sym} limit={7} width={220} />
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between pt-1 border-t border-slate-800/60">
                  <span className="text-[10px] text-slate-600">
                    {entry.computed_at
                      ? new Date(entry.computed_at).toLocaleTimeString([], {
                          hour: "2-digit", minute: "2-digit",
                        })
                      : ""}
                  </span>
                  <span className="text-[10px] text-slate-600 group-hover:text-sky-400 transition-colors">
                    Open →
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      )}

      {/* Add more hint */}
      {!isLoading && symbols.length > 0 && symbols.length < 5 && (
        <p className="text-center text-xs text-slate-600 pb-2">
          Add more symbols to your watchlist from the Dashboard to track them here.
        </p>
      )}
    </div>
  );
}
