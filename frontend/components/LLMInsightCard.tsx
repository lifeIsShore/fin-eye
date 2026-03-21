"use client";

/**
 * LLMInsightCard.tsx — todos-v5 Sprint 1 (Phase 3.4)
 *
 * Structured investment manager insight card.
 * Renders the 6-section output from the LLM investment manager persona:
 *   [PRIMARY SIGNAL] [ENTRY] [TARGETS] [RISK MANAGEMENT] [TIMEFRAME SPLIT] [CAUTION]
 *
 * Falls back gracefully when Ollama is unavailable — shows static price targets
 * and a "Start Ollama" hint instead of crashing.
 *
 * Props:
 *   symbol        — active ticker
 *   signals       — ML signals from TechnicalConsensusDto (passed from page.tsx)
 *   currentPrice  — latest price (used for target computation)
 *   macroScore    — 0-100 macro composite
 *   vix           — current VIX level (optional)
 *   yieldSpread   — 10Y-2Y yield spread (optional)
 *   macroRegime   — e.g. "Risk-On", "Goldilocks"
 *   newsSentiment — { d1, d7, d30 } from sentiment API
 *   gasScore      — 0-100 GAS composite
 */

import React, { useState, useCallback } from "react";
import useSWR from "swr";
import {
  fetchLLMInsight,
  type TechnicalSignalDto,
  type LLMInsightResponse,
} from "../lib/api_llm_types";

// ── Section config ────────────────────────────────────────────────────────────

const SECTIONS: {
  key: keyof LLMInsightResponse["sections"];
  icon: string;
  label: string;
  color: string;
  borderColor: string;
  bgColor: string;
}[] = [
  {
    key: "primary_signal",
    icon: "📡",
    label: "Primary Signal",
    color: "text-sky-400",
    borderColor: "border-sky-800/50",
    bgColor: "bg-sky-950/20",
  },
  {
    key: "entry",
    icon: "🎯",
    label: "Entry",
    color: "text-emerald-400",
    borderColor: "border-emerald-800/50",
    bgColor: "bg-emerald-950/20",
  },
  {
    key: "targets",
    icon: "📊",
    label: "Targets",
    color: "text-violet-400",
    borderColor: "border-violet-800/50",
    bgColor: "bg-violet-950/20",
  },
  {
    key: "risk_management",
    icon: "🛡️",
    label: "Risk Management",
    color: "text-amber-400",
    borderColor: "border-amber-800/50",
    bgColor: "bg-amber-950/20",
  },
  {
    key: "timeframe_split",
    icon: "📅",
    label: "Timeframe Split",
    color: "text-slate-300",
    borderColor: "border-slate-700",
    bgColor: "bg-slate-800/30",
  },
  {
    key: "caution",
    icon: "⚠️",
    label: "Caution",
    color: "text-rose-400",
    borderColor: "border-rose-800/40",
    bgColor: "bg-rose-950/15",
  },
];

// ── Price target band ────────────────────────────────────────────────────────

function PriceTargetBand({
  currentPrice,
  expectedPrice,
  upsideTarget,
  downstopStop,
  expectedReturnPct,
  atrAbsolute,
}: {
  currentPrice: number;
  expectedPrice?: number | null;
  upsideTarget?: number | null;
  downstopStop?: number | null;
  expectedReturnPct?: number | null;
  atrAbsolute?: number | null;
}) {
  if (!expectedPrice || currentPrice <= 0) return null;

  const rows = [
    upsideTarget && {
      label: "Upside target",
      price: upsideTarget,
      pct: ((upsideTarget - currentPrice) / currentPrice) * 100,
      color: "text-emerald-400",
      dot: "bg-emerald-400",
      basis: "expected + 1 ATR",
    },
    {
      label: "Expected (~3 days)",
      price: expectedPrice,
      pct: expectedReturnPct ?? 0,
      color: "text-sky-400",
      dot: "bg-sky-400",
      basis: "model expected return",
    },
    {
      label: "Current price",
      price: currentPrice,
      pct: 0,
      color: "text-slate-300",
      dot: "bg-slate-400",
      basis: "now",
    },
    downstopStop && {
      label: "Stop loss",
      price: downstopStop,
      pct: ((downstopStop - currentPrice) / currentPrice) * 100,
      color: "text-rose-400",
      dot: "bg-rose-400",
      basis: "current − 1 ATR",
    },
  ].filter(Boolean) as {
    label: string;
    price: number;
    pct: number;
    color: string;
    dot: string;
    basis: string;
  }[];

  return (
    <div className="mt-3 rounded-xl border border-slate-700/60 bg-slate-900/50 p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">
          Probabilistic Price Targets
        </span>
        {atrAbsolute && (
          <span className="text-[10px] text-slate-600">
            ATR: ${atrAbsolute.toFixed(2)}
          </span>
        )}
      </div>
      <div className="space-y-2">
        {rows.map((row) => (
          <div key={row.label} className="flex items-center gap-3">
            <span className={`h-2 w-2 rounded-full flex-shrink-0 ${row.dot}`} />
            <div className="flex-1 min-w-0">
              <span className="text-xs text-slate-400">{row.label}</span>
            </div>
            <span className={`text-xs font-mono font-bold tabular-nums ${row.color}`}>
              ${row.price.toFixed(2)}
            </span>
            <span className={`text-[10px] font-mono tabular-nums w-14 text-right ${row.color}`}>
              {row.pct === 0 ? "—" : `${row.pct >= 0 ? "+" : ""}${row.pct.toFixed(1)}%`}
            </span>
          </div>
        ))}
      </div>
      <p className="mt-2 text-[10px] text-slate-600 leading-relaxed">
        Probabilistic estimates based on model expected return and ATR. Not a guarantee.
      </p>
    </div>
  );
}

// ── Consensus badge ──────────────────────────────────────────────────────────

function ConsensusBadge({
  agreementCount,
  totalTimeframes,
  dominantDirection,
}: {
  agreementCount: number;
  totalTimeframes: number;
  dominantDirection: string;
}) {
  if (totalTimeframes === 0) return null;
  const pct = Math.round((agreementCount / totalTimeframes) * 100);
  const isStrong = pct >= 80;
  const isMixed  = dominantDirection === "Mixed";
  const color    = isMixed
    ? "text-amber-400 bg-amber-950/30 border-amber-800/40"
    : dominantDirection === "Bullish"
    ? "text-emerald-400 bg-emerald-950/30 border-emerald-800/40"
    : "text-rose-400 bg-rose-950/30 border-rose-800/40";

  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border ${color}`}>
      {isMixed ? "⚡ Mixed" : isStrong ? `⬆ Strong ${dominantDirection}` : `~ Mild ${dominantDirection}`}
      <span className="opacity-60">· {agreementCount}/{totalTimeframes} agree</span>
    </span>
  );
}

// ── Ollama hint ──────────────────────────────────────────────────────────────

function OllamaHint() {
  return (
    <div className="mt-3 rounded-lg border border-slate-700/50 bg-slate-800/30 px-4 py-3">
      <p className="text-xs font-semibold text-slate-400 mb-1">💡 Start Ollama for AI analysis</p>
      <p className="text-[11px] text-slate-500 leading-relaxed">
        Run{" "}
        <code className="text-sky-400 bg-slate-900 px-1 rounded">ollama serve</code>{" "}
        in a terminal, then refresh. No API key or cost required.
        <br />
        Pull a model first:{" "}
        <code className="text-sky-400 bg-slate-900 px-1 rounded">ollama pull llama3:8b</code>
      </p>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface LLMInsightCardProps {
  symbol:           string;
  signals:          TechnicalSignalDto[];
  currentPrice:     number;
  macroScore?:      number | null;
  vix?:             number | null;
  yieldSpread?:     number | null;
  macroRegime?:     string | null;
  newsSentiment?:   { d1?: number | null; d7?: number | null; d30?: number | null };
  gasScore?:        number | null;
  atrAbsolute?:     number | null;   // passed from technical service if available
}

export default function LLMInsightCard({
  symbol,
  signals,
  currentPrice,
  macroScore,
  vix,
  yieldSpread,
  macroRegime,
  newsSentiment,
  gasScore,
  atrAbsolute,
}: LLMInsightCardProps) {
  const [viewMode, setViewMode] = useState<"short" | "medium" | "long">("short");
  const [manualRefresh, setManualRefresh] = useState(0);

  // Build the request payload from props
  const payload = React.useMemo(() => ({
    current_price:      currentPrice,
    signals: signals.map((s) => ({
      timeframe:       s.timeframe,
      direction:       s.direction,
      confidence:      s.confidence,
      sharpe:          s.sharpe_weight ?? 0,
      horizon_periods: 3,
      model_used:      s.model_used ?? "unknown",
    })),
    macro_score:        macroScore ?? null,
    vix:                vix ?? null,
    yield_spread:       yieldSpread ?? null,
    macro_regime:       macroRegime ?? null,
    news_sentiment_1d:  newsSentiment?.d1 ?? null,
    news_sentiment_7d:  newsSentiment?.d7 ?? null,
    news_sentiment_30d: newsSentiment?.d30 ?? null,
    gas_score:          gasScore ?? null,
    atr_absolute:       atrAbsolute ?? null,
  }), [symbol, signals, currentPrice, macroScore, vix, yieldSpread,
      macroRegime, newsSentiment, gasScore, atrAbsolute]);

  // Only fetch when there are trained signals — avoid hitting the LLM for untrained symbols
  const shouldFetch = signals.length > 0 && currentPrice > 0;

  const { data, isLoading, error, mutate } = useSWR<LLMInsightResponse>(
    shouldFetch ? [`llm-insight-${symbol}`, symbol, manualRefresh] : null,
    () => fetchLLMInsight(symbol, payload),
    {
      refreshInterval: 0,         // never auto-refresh — LLM calls are expensive
      shouldRetryOnError: false,
      revalidateOnFocus: false,
    },
  );

  const handleRegenerate = useCallback(() => {
    setManualRefresh((n) => n + 1);
    mutate(undefined, { revalidate: true });
  }, [mutate]);

  // ── Loading state ─────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-xl">🤖</span>
          <h3 className="text-sm font-bold text-slate-100">Investment Manager Insight</h3>
        </div>
        <div className="space-y-3 animate-pulse">
          {SECTIONS.map((s) => (
            <div key={s.key} className={`rounded-xl border p-4 ${s.bgColor} ${s.borderColor}`}>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-base">{s.icon}</span>
                <div className="h-3 w-24 rounded bg-slate-700" />
              </div>
              <div className="space-y-1.5">
                <div className="h-3 w-full rounded bg-slate-700/60" />
                <div className="h-3 w-3/4 rounded bg-slate-700/40" />
              </div>
            </div>
          ))}
        </div>
        <p className="mt-3 text-center text-xs text-slate-500 animate-pulse">
          Consulting investment manager… (~15–30 seconds on first load)
        </p>
      </div>
    );
  }

  // ── No signals yet ────────────────────────────────────────────────────────
  if (!shouldFetch) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
        <div className="flex items-center gap-3 mb-3">
          <span className="text-xl">🤖</span>
          <h3 className="text-sm font-bold text-slate-100">Investment Manager Insight</h3>
        </div>
        <p className="text-xs text-slate-500">
          Train ML models for {symbol} first to unlock the investment manager analysis.
        </p>
      </div>
    );
  }

  const sections = data?.sections;
  const isFallback = data?.backend_used === "fallback";
  const hasError   = !!error || !!data?.error;

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">🤖</span>
            <h3 className="text-sm font-bold text-slate-100">Investment Manager Insight</h3>
            {data && (
              <ConsensusBadge
                agreementCount={data.agreement_count}
                totalTimeframes={data.total_timeframes}
                dominantDirection={data.dominant_direction}
              />
            )}
          </div>
          <p className="text-[10px] text-slate-500 mt-0.5 ml-7">
            {data?.cached
              ? "Cached analysis"
              : data?.backend_used === "ollama"
              ? `Ollama · ${data.model_used}`
              : data?.backend_used === "groq"
              ? `Groq · ${data.model_used}`
              : "Analysis"}
            {" "}· Probabilistic, not financial advice
          </p>
        </div>

        {/* Timeframe view selector */}
        <div className="flex items-center gap-1 rounded-lg border border-slate-700/50 bg-slate-800/40 p-0.5 flex-shrink-0">
          {(["short", "medium", "long"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setViewMode(v)}
              className={`px-2 py-1 rounded text-[10px] font-medium transition-colors capitalize ${
                viewMode === v
                  ? "bg-slate-700 text-slate-100"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {v === "short" ? "1–3d" : v === "medium" ? "1–2wk" : "Monthly"}
            </button>
          ))}
        </div>
      </div>

      {/* Error / fallback notice */}
      {(hasError || isFallback) && (
        <div className="rounded-lg border border-amber-800/40 bg-amber-950/20 px-3 py-2.5">
          <p className="text-xs text-amber-400 font-medium">
            {isFallback
              ? "⚠️ Ollama is offline — showing pre-computed data only"
              : "⚠️ Could not reach LLM — showing static fallback"}
          </p>
          <p className="text-[11px] text-amber-500/70 mt-0.5">
            Start Ollama to get the full investment manager analysis.
          </p>
        </div>
      )}

      {/* Sections */}
      {sections && (
        <div className="space-y-3">
          {SECTIONS.map((cfg) => {
            const text = sections[cfg.key];
            if (!text) return null;
            return (
              <div
                key={cfg.key}
                className={`rounded-xl border p-4 ${cfg.bgColor} ${cfg.borderColor}`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-base leading-none">{cfg.icon}</span>
                  <span className={`text-[10px] font-bold uppercase tracking-widest ${cfg.color}`}>
                    {cfg.label}
                  </span>
                </div>
                <p className="text-sm text-slate-300 leading-relaxed">{text}</p>
              </div>
            );
          })}
        </div>
      )}

      {/* Price target band */}
      {data && (
        <PriceTargetBand
          currentPrice={currentPrice}
          expectedPrice={data.expected_price}
          upsideTarget={data.upside_target}
          downstopStop={data.downside_stop}
          expectedReturnPct={data.expected_return_pct}
          atrAbsolute={data.atr_absolute}
        />
      )}

      {/* Ollama hint when fallback */}
      {isFallback && <OllamaHint />}

      {/* Footer: regenerate + disclaimer */}
      <div className="flex items-center justify-between pt-2 border-t border-slate-800">
        <p className="text-[10px] text-slate-600 max-w-xs leading-relaxed">
          ⚠️ Educational analysis only. Not investment advice.
        </p>
        <button
          onClick={handleRegenerate}
          disabled={isLoading}
          className="flex items-center gap-1.5 text-[10px] text-slate-500 hover:text-slate-300 transition-colors disabled:opacity-40"
        >
          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Regenerate
        </button>
      </div>
    </div>
  );
}
