"use client";

/**
 * components/CrossAssetRow.tsx
 *
 * Sprint 11 — Cross-asset mini GAS overview bar.
 *
 * Shows a compact horizontal row of GAS cards for SPY, QQQ, GLD, TLT, BTC-USD
 * (and any other symbols passed in). Gives dashboard users an instant
 * cross-market read before diving into their active symbol.
 *
 * Features:
 *   - Batch-fetches latest GAS snapshot for all assets via existing batch endpoint
 *   - Colour-coded per score (emerald / amber / rose)
 *   - Delta arrow vs previous snapshot
 *   - Clicking switches the active dashboard symbol
 *   - Horizontally scrollable on narrow screens
 *   - Refreshes every 5 minutes with SWR
 *   - Gracefully empty when no snapshots exist yet
 */

import React, { useMemo } from "react";
import useSWR from "swr";
import type { GasBatchEntry } from "./WhatChangedToday";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// ── Default cross-asset universe ──────────────────────────────────────────────

export const DEFAULT_CROSS_ASSETS = ["SPY", "QQQ", "GLD", "TLT", "BTC-USD", "DX-Y.NYB"];

const ASSET_LABELS: Record<string, { label: string; desc: string }> = {
  "SPY":      { label: "SPY",     desc: "S&P 500" },
  "QQQ":      { label: "QQQ",     desc: "Nasdaq 100" },
  "GLD":      { label: "GLD",     desc: "Gold" },
  "TLT":      { label: "TLT",     desc: "20Y Treasuries" },
  "BTC-USD":  { label: "BTC",     desc: "Bitcoin" },
  "DX-Y.NYB": { label: "DXY",     desc: "US Dollar Index" },
  "SLV":      { label: "SLV",     desc: "Silver" },
  "USO":      { label: "OIL",     desc: "Crude Oil" },
  "AAPL":     { label: "AAPL",    desc: "Apple" },
  "TSLA":     { label: "TSLA",    desc: "Tesla" },
  "NVDA":     { label: "NVDA",    desc: "NVIDIA" },
  "MSFT":     { label: "MSFT",    desc: "Microsoft" },
};

// ── Fetch ─────────────────────────────────────────────────────────────────────

async function fetchCrossAssetSnapshots(symbols: string[]): Promise<GasBatchEntry[]> {
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

function scoreColor(score: number): string {
  if (score >= 65) return "text-emerald-400";
  if (score >= 40) return "text-amber-400";
  return "text-rose-400";
}

function scoreBg(score: number): string {
  if (score >= 65) return "bg-emerald-950/40 border-emerald-800/50";
  if (score >= 40) return "bg-amber-950/30 border-amber-800/40";
  return "bg-rose-950/30 border-rose-800/40";
}

function scoreBar(score: number): string {
  if (score >= 65) return "bg-emerald-500";
  if (score >= 40) return "bg-amber-500";
  return "bg-rose-500";
}

function DeltaBadge({ delta }: { delta: number | null }) {
  if (delta === null) return null;
  if (Math.abs(delta) < 1) return <span className="text-slate-600 text-[9px]">→</span>;
  return (
    <span className={`text-[9px] font-bold ${delta > 0 ? "text-emerald-400" : "text-rose-400"}`}>
      {delta > 0 ? "↑" : "↓"}{Math.abs(delta).toFixed(0)}
    </span>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

interface CrossAssetRowProps {
  /** Symbols to show — defaults to DEFAULT_CROSS_ASSETS */
  symbols?:        string[];
  /** Called when user clicks an asset card */
  onSelectSymbol:  (symbol: string) => void;
  /** Currently active symbol — highlighted */
  activeSymbol?:   string;
}

export default function CrossAssetRow({
  symbols = DEFAULT_CROSS_ASSETS,
  onSelectSymbol,
  activeSymbol,
}: CrossAssetRowProps) {
  const { data, isLoading } = useSWR(
    ["cross-asset-batch", ...symbols],
    () => fetchCrossAssetSnapshots(symbols),
    { refreshInterval: 5 * 60_000, shouldRetryOnError: false },
  );

  // Build ordered map preserving symbols order, filling in nulls for missing
  const entries = useMemo(() => {
    const map: Record<string, GasBatchEntry> = {};
    (data ?? []).forEach((e) => (map[e.symbol] = e));
    return symbols.map((sym) => map[sym] ?? null);
  }, [data, symbols]);

  const hasAny = entries.some(Boolean);

  if (isLoading) {
    return (
      <div className="flex gap-2 overflow-x-auto pb-1">
        {symbols.map((sym) => (
          <div
            key={sym}
            className="flex-shrink-0 w-24 h-20 rounded-xl bg-slate-800/40 border border-slate-800 animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (!hasAny) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/20 px-4 py-3 text-xs text-slate-600">
        No cross-asset snapshots yet — run GAS precompute for SPY, QQQ, GLD, TLT, BTC-USD.
      </div>
    );
  }

  return (
    <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
      {symbols.map((sym, i) => {
        const entry = entries[i];
        const meta  = ASSET_LABELS[sym] ?? { label: sym, desc: "" };
        const isActive = sym === activeSymbol;

        if (!entry) {
          // Symbol has no snapshot yet — show greyed-out stub
          return (
            <button
              key={sym}
              onClick={() => onSelectSymbol(sym)}
              className={`flex-shrink-0 w-24 rounded-xl border border-slate-800 bg-slate-900/20 px-2.5 py-2.5 text-left transition-colors hover:border-slate-700 ${
                isActive ? "ring-1 ring-sky-500" : ""
              }`}
            >
              <span className="text-xs font-bold text-slate-500">{meta.label}</span>
              <p className="text-[10px] text-slate-700 mt-0.5 truncate">{meta.desc}</p>
              <p className="text-[10px] text-slate-700 mt-2">No data</p>
            </button>
          );
        }

        return (
          <button
            key={sym}
            onClick={() => onSelectSymbol(sym)}
            className={`flex-shrink-0 w-24 rounded-xl border px-2.5 py-2.5 text-left transition-all hover:scale-[1.03] active:scale-[0.98] ${scoreBg(entry.gas_score)} ${
              isActive ? "ring-1 ring-sky-500" : ""
            }`}
          >
            {/* Symbol + delta */}
            <div className="flex items-start justify-between gap-1">
              <div className="min-w-0">
                <span className="text-xs font-black text-slate-100">{meta.label}</span>
                <p className="text-[9px] text-slate-500 truncate leading-tight">{meta.desc}</p>
              </div>
              <DeltaBadge delta={entry.delta} />
            </div>

            {/* GAS score */}
            <div className={`mt-2 text-2xl font-black tabular-nums leading-none ${scoreColor(entry.gas_score)}`}>
              {entry.gas_score.toFixed(0)}
            </div>

            {/* Mini bar */}
            <div className="mt-2 h-1 w-full rounded-full bg-slate-800/60 overflow-hidden">
              <div
                className={`h-full rounded-full ${scoreBar(entry.gas_score)}`}
                style={{ width: `${Math.min(100, entry.gas_score)}%` }}
              />
            </div>

            {/* Regime */}
            <p className="mt-1 text-[9px] text-slate-600 truncate">
              {entry.regime || entry.weather_label}
            </p>
          </button>
        );
      })}
    </div>
  );
}
