"use client";

/**
 * PriceTargetCard.tsx — todos-v5 Sprint 5 (Phase 6.1 + 7.2)
 *
 * Standalone probabilistic price target display with Kelly position sizing.
 * Renders independently of the LLM — works even when Ollama is offline.
 *
 * Data source: GET /api/v1/technical/{symbol}/price-targets
 *   - Real ATR from last 252 daily bars
 *   - Expected return from Sharpe-weighted ML signals
 *   - Kelly Criterion sizing from live prediction accuracy (falls back to validation)
 *
 * Design principles:
 *   - Always shows "Probabilistic estimate" framing — never presents targets as certain
 *   - Clicking any price level shows its calculation basis
 *   - Kelly fraction accompanied by formula tooltip + "not advice" label
 *   - Graceful empty states: no models, no price data, insufficient Kelly data
 */

import React, { useState } from "react";
import useSWR from "swr";

// ── Types ────────────────────────────────────────────────────────────────────

interface PriceLevel {
  price:      number;
  pct_change: number;
  basis:      string;
}

interface TargetsDto {
  upside:           PriceLevel;
  expected:         PriceLevel;
  stop:             PriceLevel;
  risk_reward_ratio: number;
  horizon_label:    string;
  atr_used:         number;
  confidence:       number;
  note:             string;
}

interface KellyDto {
  suggested_pct:       number;
  full_kelly:          number;
  half_kelly:          number;
  capped_at_25pct:     boolean;
  confidence_penalty:  number;
  inputs: {
    win_rate:     number;
    avg_win_pct:  number;
    avg_loss_pct: number;
  };
  source:             string;
  n_resolved:         number;
  insufficient_data:  boolean;
  formula:            string;
  note:               string;
}

interface PriceTargetResponse {
  symbol:           string;
  available:        boolean;
  message?:         string;
  current_price?:   number;
  atr_14?:          number;
  atr_pct?:         number;
  high_52w?:        number;
  low_52w?:         number;
  pct_from_52w_high?: number;
  pct_from_52w_low?:  number;
  targets?:         TargetsDto;
  kelly?:           KellyDto | null;
  expected_return?: number;
  model_confidence?: number;
  horizon_label?:   string;
  signals_used?:    { timeframe: string; direction: string; confidence: number; sharpe: number }[];
  models_trained?:  boolean;
  disclaimer?:      string;
}

// ── Fetch ─────────────────────────────────────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchPriceTargets(symbol: string): Promise<PriceTargetResponse> {
  const res = await fetch(
    `${API_BASE}/api/v1/technical/${encodeURIComponent(symbol.toUpperCase())}/price-targets`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error(`price-targets failed: ${res.status}`);
  return res.json();
}

// ── Price range visual ────────────────────────────────────────────────────────

function PriceRangeBar({
  currentPrice,
  targets,
}: {
  currentPrice: number;
  targets: TargetsDto;
}) {
  const [tooltip, setTooltip] = useState<string | null>(null);

  const levels = [
    { label: "Upside",   price: targets.upside.price,   pct: targets.upside.pct_change,   basis: targets.upside.basis,   color: "bg-emerald-400", dot: "bg-emerald-400", text: "text-emerald-400" },
    { label: "Expected", price: targets.expected.price,  pct: targets.expected.pct_change,  basis: targets.expected.basis,  color: "bg-sky-400",     dot: "bg-sky-400",     text: "text-sky-400"     },
    { label: "Current",  price: currentPrice,             pct: 0,                            basis: "latest closing price",  color: "bg-slate-400",   dot: "bg-slate-300",   text: "text-slate-300"   },
    { label: "Stop",     price: targets.stop.price,      pct: targets.stop.pct_change,      basis: targets.stop.basis,      color: "bg-rose-400",    dot: "bg-rose-400",    text: "text-rose-400"    },
  ];

  // Build bar scale: stop is 0%, upside is 100%
  const lo  = Math.min(targets.stop.price, currentPrice) * 0.995;
  const hi  = Math.max(targets.upside.price, currentPrice) * 1.005;
  const span = hi - lo;
  const pos  = (p: number) => Math.max(0, Math.min(100, ((p - lo) / span) * 100));

  return (
    <div className="space-y-4">
      {/* Horizontal range bar */}
      <div className="relative h-8 rounded-full bg-slate-800 overflow-visible mx-1">
        {/* Stop → current zone (risk area, rose tint) */}
        <div
          className="absolute inset-y-0 rounded-l-full bg-rose-950/40"
          style={{ left: `${pos(targets.stop.price)}%`, width: `${pos(currentPrice) - pos(targets.stop.price)}%` }}
        />
        {/* Current → upside zone (reward area, emerald tint) */}
        <div
          className="absolute inset-y-0 bg-emerald-950/30"
          style={{ left: `${pos(currentPrice)}%`, width: `${pos(targets.upside.price) - pos(currentPrice)}%` }}
        />

        {/* Level markers */}
        {levels.map((l) => (
          <button
            key={l.label}
            onClick={() => setTooltip(tooltip === l.label ? null : l.label)}
            className={`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 h-4 w-4 rounded-full border-2 border-slate-950 ${l.dot} hover:scale-125 transition-transform cursor-pointer z-10`}
            style={{ left: `${pos(l.price)}%` }}
            title={`${l.label}: $${l.price.toFixed(2)}`}
          />
        ))}
      </div>

      {/* Tooltip */}
      {tooltip && (() => {
        const lv = levels.find(l => l.label === tooltip);
        if (!lv) return null;
        return (
          <div className="rounded-lg border border-slate-700/60 bg-slate-800/80 px-3 py-2 text-xs space-y-0.5">
            <p className={`font-bold ${lv.text}`}>{lv.label}</p>
            <p className="text-slate-200 font-mono">${lv.price.toFixed(2)}{lv.pct !== 0 && ` (${lv.pct >= 0 ? "+" : ""}${lv.pct.toFixed(1)}%)`}</p>
            <p className="text-slate-500">{lv.basis}</p>
          </div>
        );
      })()}

      {/* Level rows */}
      <div className="space-y-2">
        {levels.map((l) => (
          <div key={l.label} className="flex items-center gap-3">
            <span className={`h-2 w-2 rounded-full flex-shrink-0 ${l.dot}`} />
            <span className="text-xs text-slate-400 w-16 flex-shrink-0">{l.label}</span>
            <span className={`text-xs font-mono font-bold tabular-nums ${l.text}`}>${l.price.toFixed(2)}</span>
            {l.pct !== 0 && (
              <span className={`text-[10px] font-mono tabular-nums ${l.pct >= 0 ? "text-emerald-500" : "text-rose-500"}`}>
                {l.pct >= 0 ? "+" : ""}{l.pct.toFixed(1)}%
              </span>
            )}
            <span className="text-[10px] text-slate-600 ml-auto truncate max-w-[140px]">{l.basis}</span>
          </div>
        ))}
      </div>

      {/* R:R ratio */}
      <div className="flex items-center justify-between text-[10px] text-slate-500 border-t border-slate-800 pt-2">
        <span>Risk/Reward: <span className={`font-bold ${targets.risk_reward_ratio >= 1.5 ? "text-emerald-400" : targets.risk_reward_ratio >= 1.0 ? "text-amber-400" : "text-rose-400"}`}>{targets.risk_reward_ratio.toFixed(2)}</span></span>
        <span>ATR: <span className="text-slate-400 font-mono">${targets.atr_used.toFixed(2)}</span></span>
        <span>Horizon: <span className="text-slate-400">{targets.horizon_label}</span></span>
      </div>
    </div>
  );
}

// ── Kelly sizing display ──────────────────────────────────────────────────────

function KellySizing({ kelly }: { kelly: KellyDto }) {
  const [showFormula, setShowFormula] = useState(false);

  if (kelly.insufficient_data) {
    return (
      <div className="rounded-xl border border-slate-700/40 bg-slate-800/20 p-4">
        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1">Position Sizing (Kelly)</p>
        <p className="text-xs text-slate-500">{kelly.note}</p>
      </div>
    );
  }

  const pct = kelly.suggested_pct;
  const barWidth = Math.min(pct / 25 * 100, 100); // scale to 25% max
  const barColor =
    pct >= 15 ? "bg-amber-500" :
    pct >= 8  ? "bg-sky-500"   :
    pct >= 3  ? "bg-emerald-500" : "bg-slate-500";

  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-900/40 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
          Position Sizing (Half-Kelly)
        </span>
        <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${
          kelly.source === "live"
            ? "text-emerald-400 bg-emerald-950/30 border-emerald-800/40"
            : "text-slate-400 bg-slate-800/40 border-slate-700/40"
        }`}>
          {kelly.source === "live" ? `Live · ${kelly.n_resolved} predictions` : "Validation fallback"}
        </span>
      </div>

      <div className="flex items-baseline gap-3">
        <span className={`text-3xl font-black tabular-nums ${
          pct >= 15 ? "text-amber-400" : pct >= 8 ? "text-sky-400" : "text-emerald-400"
        }`}>
          {pct.toFixed(1)}%
        </span>
        <span className="text-xs text-slate-500">of portfolio</span>
        {kelly.capped_at_25pct && (
          <span className="text-[10px] text-amber-500">← capped at 25%</span>
        )}
      </div>

      <div className="space-y-1">
        <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
          <div className={`h-full rounded-full transition-all duration-700 ${barColor}`} style={{ width: `${barWidth}%` }} />
        </div>
        <div className="flex justify-between text-[10px] text-slate-600">
          <span>0%</span>
          <span>12.5%</span>
          <span>25% max</span>
        </div>
      </div>

      {/* Input stats */}
      <div className="grid grid-cols-3 gap-2 text-[10px]">
        <div className="rounded bg-slate-800/50 px-2 py-1.5">
          <p className="text-slate-500">Win rate</p>
          <p className="font-bold text-slate-200">{(kelly.inputs.win_rate * 100).toFixed(1)}%</p>
        </div>
        <div className="rounded bg-slate-800/50 px-2 py-1.5">
          <p className="text-slate-500">Avg win</p>
          <p className="font-bold text-emerald-400">+{kelly.inputs.avg_win_pct.toFixed(2)}%</p>
        </div>
        <div className="rounded bg-slate-800/50 px-2 py-1.5">
          <p className="text-slate-500">Avg loss</p>
          <p className="font-bold text-rose-400">{kelly.inputs.avg_loss_pct.toFixed(2)}%</p>
        </div>
      </div>

      {/* Formula toggle */}
      <button
        onClick={() => setShowFormula(v => !v)}
        className="flex items-center gap-1.5 text-[10px] text-slate-600 hover:text-slate-400 transition-colors"
      >
        <svg className={`h-3 w-3 transition-transform ${showFormula ? "rotate-90" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        {showFormula ? "Hide formula" : "Show Kelly formula"}
      </button>

      {showFormula && (
        <div className="rounded-lg bg-slate-800/50 border border-slate-700/40 px-3 py-2.5 space-y-1.5">
          <p className="text-[10px] font-mono text-sky-400">{kelly.formula}</p>
          <p className="text-[10px] text-slate-500">
            Full Kelly = {kelly.full_kelly.toFixed(4)} → Half Kelly = {kelly.half_kelly.toFixed(4)}
            {kelly.confidence_penalty < 1.0 && ` × ${kelly.confidence_penalty.toFixed(2)} (sample penalty)`}
            {" "}→ capped: {pct.toFixed(1)}%
          </p>
        </div>
      )}

      <p className="text-[10px] text-slate-600 leading-relaxed">{kelly.note}</p>
    </div>
  );
}

// ── 52-week range bar ─────────────────────────────────────────────────────────

function WeeklyRange({
  currentPrice,
  high52w,
  low52w,
  pctFromHigh,
  pctFromLow,
}: {
  currentPrice: number;
  high52w: number;
  low52w: number;
  pctFromHigh: number;
  pctFromLow: number;
}) {
  const pct = ((currentPrice - low52w) / Math.max(high52w - low52w, 0.01)) * 100;
  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-900/40 p-4 space-y-2">
      <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">52-Week Range</p>
      <div className="flex items-center gap-3">
        <span className="text-[10px] text-slate-500 font-mono w-16">${low52w.toFixed(2)}</span>
        <div className="flex-1 relative h-3 rounded-full bg-slate-800 overflow-hidden">
          <div className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-rose-600/50 to-emerald-600/50" style={{ width: "100%" }} />
          <div className="absolute inset-y-0 w-1 bg-white/80 rounded-full -translate-x-0.5" style={{ left: `${pct}%` }} />
        </div>
        <span className="text-[10px] text-slate-500 font-mono w-16 text-right">${high52w.toFixed(2)}</span>
      </div>
      <div className="flex justify-between text-[10px] text-slate-500">
        <span className="text-rose-400">{pctFromLow >= 0 ? "+" : ""}{pctFromLow.toFixed(1)}% from low</span>
        <span className="text-slate-300 font-mono font-bold">${currentPrice.toFixed(2)}</span>
        <span className="text-emerald-400">{pctFromHigh.toFixed(1)}% from high</span>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface PriceTargetCardProps {
  symbol:      string;
  isVisible?:  boolean;  // gate render until signals exist
}

export default function PriceTargetCard({ symbol, isVisible = true }: PriceTargetCardProps) {
  const { data, isLoading, error } = useSWR<PriceTargetResponse>(
    isVisible ? `price-targets-${symbol}` : null,
    () => fetchPriceTargets(symbol),
    { revalidateOnFocus: false, shouldRetryOnError: false, refreshInterval: 300_000 },
  );

  if (!isVisible) return null;

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-3 animate-pulse">
        <div className="flex items-center gap-2">
          <span className="text-xl">🎯</span>
          <div className="h-4 w-40 rounded bg-slate-700" />
        </div>
        <div className="h-8 w-full rounded-full bg-slate-800" />
        <div className="space-y-2">
          {[1, 2, 3, 4].map(i => <div key={i} className="h-4 w-full rounded bg-slate-800/60" />)}
        </div>
      </div>
    );
  }

  if (error || !data?.available) {
    const msg = data?.message ?? "Could not load price targets.";
    const noModels = data?.models_trained === false;
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xl">🎯</span>
          <h3 className="text-sm font-bold text-slate-100">Price Targets & Position Sizing</h3>
        </div>
        <p className="text-xs text-slate-500">
          {noModels
            ? `No ML models trained for ${symbol} yet. Train models first to enable price targets.`
            : msg}
        </p>
      </div>
    );
  }

  const { current_price: price, targets, kelly, high_52w, low_52w, pct_from_52w_high, pct_from_52w_low,
          model_confidence, expected_return, horizon_label, signals_used } = data;

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-5">

      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">🎯</span>
            <h3 className="text-sm font-bold text-slate-100">Price Targets & Position Sizing</h3>
          </div>
          <p className="text-[10px] text-slate-500 mt-0.5 ml-7">
            Model-driven · ATR-based · Probabilistic
            {model_confidence != null && ` · ${model_confidence.toFixed(0)}% model confidence`}
          </p>
        </div>

        {/* Direction consensus mini-badge */}
        {signals_used && signals_used.length > 0 && (() => {
          const bull = signals_used.filter(s => s.direction === "Bullish").length;
          const bear = signals_used.filter(s => s.direction === "Bearish").length;
          const dom  = bull > bear ? "Bullish" : bear > bull ? "Bearish" : "Mixed";
          const col  = dom === "Bullish" ? "text-emerald-400 bg-emerald-950/30 border-emerald-800/40"
                     : dom === "Bearish" ? "text-rose-400 bg-rose-950/30 border-rose-800/40"
                     : "text-amber-400 bg-amber-950/30 border-amber-800/40";
          return (
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${col}`}>
              {dom} · {Math.max(bull, bear)}/{signals_used.length}
            </span>
          );
        })()}
      </div>

      {/* Expected return summary */}
      {expected_return != null && (
        <div className="flex items-center gap-4 rounded-xl border border-slate-700/50 bg-slate-800/30 px-4 py-3">
          <div>
            <p className="text-[10px] text-slate-500 mb-0.5">Expected return</p>
            <p className={`text-lg font-black tabular-nums ${
              expected_return >= 0 ? "text-emerald-400" : "text-rose-400"
            }`}>
              {expected_return >= 0 ? "+" : ""}{expected_return.toFixed(2)}%
            </p>
          </div>
          <div className="h-8 w-px bg-slate-700/50" />
          <div>
            <p className="text-[10px] text-slate-500 mb-0.5">Horizon</p>
            <p className="text-sm font-semibold text-slate-200">{horizon_label}</p>
          </div>
          <div className="h-8 w-px bg-slate-700/50" />
          <div>
            <p className="text-[10px] text-slate-500 mb-0.5">Current price</p>
            <p className="text-sm font-mono font-bold text-slate-200">${price?.toFixed(2)}</p>
          </div>
        </div>
      )}

      {/* Price range bar + levels */}
      {targets && price && (
        <div className="rounded-xl border border-slate-700/60 bg-slate-900/50 p-4 space-y-3">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
            Probabilistic Price Levels
          </p>
          <PriceRangeBar currentPrice={price} targets={targets} />
          <p className="text-[10px] text-slate-600 leading-relaxed">{targets.note}</p>
        </div>
      )}

      {/* 52-week range */}
      {high_52w && low_52w && price && (
        <WeeklyRange
          currentPrice={price}
          high52w={high_52w}
          low52w={low_52w}
          pctFromHigh={pct_from_52w_high ?? 0}
          pctFromLow={pct_from_52w_low ?? 0}
        />
      )}

      {/* Kelly position sizing */}
      {kelly && <KellySizing kelly={kelly} />}

      {/* Disclaimer */}
      <p className="text-[10px] text-slate-600 leading-relaxed border-t border-slate-800 pt-3">
        ⚠️ {data.disclaimer}
      </p>
    </div>
  );
}
