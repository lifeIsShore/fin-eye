"use client";

/**
 * LLMInsightCard.tsx — Sprint 12: fully wired to SSE streaming endpoint.
 *
 * Sections appear progressively as Ollama streams tokens — no more full-page
 * 15-second blank wait. Each section card fades in as soon as its text is
 * complete. Falls back gracefully to Groq / static when Ollama is offline.
 */

import React, { useState, useCallback, useEffect, useRef } from "react";
import {
  type TechnicalSignalDto,
  type LLMInsightResponse,
  type InsightSections,
  type LLMInsightRequest,
} from "../lib/api_llm_types";
import { interpretConfidence } from "../lib/signalUtils";

// ── SSE streaming hook ────────────────────────────────────────────────────────

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface StreamState {
  status:   "idle" | "streaming" | "done" | "error";
  rawText:  string;
  sections: Partial<InsightSections>;
  meta:     Partial<LLMInsightResponse>;
  cached:   boolean;
  error:    string | null;
}

const EMPTY_STREAM: StreamState = {
  status: "idle", rawText: "", sections: {}, meta: {}, cached: false, error: null,
};

const SECTION_HEADERS = [
  "[PRIMARY SIGNAL]",
  "[ENTRY]",
  "[TARGETS]",
  "[RISK MANAGEMENT]",
  "[TIMEFRAME SPLIT]",
  "[CAUTION]",
] as const;

const HEADER_KEY: Record<string, keyof InsightSections> = {
  "[PRIMARY SIGNAL]":  "primary_signal",
  "[ENTRY]":           "entry",
  "[TARGETS]":         "targets",
  "[RISK MANAGEMENT]": "risk_management",
  "[TIMEFRAME SPLIT]": "timeframe_split",
  "[CAUTION]":         "caution",
};

function parseStreamingSections(raw: string): Partial<InsightSections> {
  const result: Partial<InsightSections> = {};
  const upperRaw = raw.toUpperCase();

  for (let i = 0; i < SECTION_HEADERS.length; i++) {
    const header     = SECTION_HEADERS[i];
    const nextHeader = SECTION_HEADERS[i + 1];
    const start      = upperRaw.indexOf(header);
    if (start === -1) continue;

    const bodyStart = start + header.length;
    const end       = nextHeader ? upperRaw.indexOf(nextHeader) : raw.length;
    const body      = raw.slice(bodyStart, end === -1 ? raw.length : end).trim();

    if (body) result[HEADER_KEY[header]] = body;
  }
  return result;
}

function useStreamInsight(
  symbol: string,
  payload: LLMInsightRequest,
  enabled: boolean,
  triggerKey: number,
) {
  const [state, setState] = useState<StreamState>(EMPTY_STREAM);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!enabled) return;

    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setState({ ...EMPTY_STREAM, status: "streaming" });

    (async () => {
      const token =
        typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

      try {
        const res = await fetch(
          `${API_BASE_URL}/api/v1/explanation/${encodeURIComponent(symbol.toUpperCase())}/generate-insight-stream`,
          {
            method:  "POST",
            headers: {
              "Content-Type": "application/json",
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body:   JSON.stringify(payload),
            signal: ctrl.signal,
          },
        );

        if (!res.ok || !res.body) {
          setState((s) => ({ ...s, status: "error", error: `HTTP ${res.status}` }));
          return;
        }

        const reader  = res.body.getReader();
        const decoder = new TextDecoder();
        let   buffer  = "";
        let   accText = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const raw = line.slice(6).trim();
            if (!raw) continue;

            let evt: Record<string, unknown>;
            try { evt = JSON.parse(raw); } catch { continue; }

            const type = evt["type"] as string;

            if (type === "meta") {
              setState((s) => ({
                ...s,
                meta: {
                  agreement_count:     evt["agreement_count"]     as number,
                  total_timeframes:    evt["total_timeframes"]    as number,
                  dominant_direction:  evt["dominant_direction"]  as string,
                  backend_used:        evt["backend_used"]        as string,
                  model_used:          evt["model_used"]          as string,
                  expected_price:      evt["expected_price"]      as number | null,
                  upside_target:       evt["upside_target"]       as number | null,
                  downside_stop:       evt["downside_stop"]       as number | null,
                  expected_return_pct: evt["expected_return_pct"] as number | null,
                  atr_absolute:        evt["atr_absolute"]        as number | null,
                },
              }));
            } else if (type === "token") {
              accText += (evt["text"] as string) ?? "";
              const parsed = parseStreamingSections(accText);
              setState((s) => ({ ...s, rawText: accText, sections: parsed }));
            } else if (type === "sections") {
              setState((s) => ({
                ...s,
                sections: evt["sections"] as InsightSections,
              }));
            } else if (type === "done") {
              setState((s) => ({
                ...s,
                status: "done",
                cached: (evt["cached"] as boolean) ?? false,
              }));
            } else if (type === "error") {
              setState((s) => ({
                ...s,
                status: "error",
                error: (evt["message"] as string) ?? "Unknown error",
              }));
            }
          }
        }
        setState((s) => (s.status === "streaming" ? { ...s, status: "done" } : s));
      } catch (err: unknown) {
        if ((err as Error).name === "AbortError") return;
        setState((s) => ({
          ...s, status: "error",
          error: (err as Error).message ?? "Stream failed",
        }));
      }
    })();

    return () => { ctrl.abort(); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, enabled, triggerKey]);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setState(EMPTY_STREAM);
  }, []);

  return { state, reset };
}

// ── Section config ─────────────────────────────────────────────────────────────

const SECTIONS: {
  key: keyof InsightSections;
  icon: string;
  label: string;
  color: string;
  borderColor: string;
  bgColor: string;
}[] = [
  { key: "primary_signal",  icon: "📡", label: "Primary Signal",   color: "text-sky-400",    borderColor: "border-sky-800/50",     bgColor: "bg-sky-950/20"     },
  { key: "entry",           icon: "🎯", label: "Entry",            color: "text-emerald-400", borderColor: "border-emerald-800/50", bgColor: "bg-emerald-950/20" },
  { key: "targets",         icon: "📊", label: "Targets",          color: "text-violet-400",  borderColor: "border-violet-800/50",  bgColor: "bg-violet-950/20"  },
  { key: "risk_management", icon: "🛡️", label: "Risk Management",  color: "text-amber-400",   borderColor: "border-amber-800/50",   bgColor: "bg-amber-950/20"   },
  { key: "timeframe_split", icon: "📅", label: "Timeframe Split",  color: "text-slate-300",   borderColor: "border-slate-700",      bgColor: "bg-slate-800/30"   },
  { key: "caution",         icon: "⚠️", label: "Caution",          color: "text-rose-400",    borderColor: "border-rose-800/40",    bgColor: "bg-rose-950/15"    },
];

// ── Streaming section skeleton (shown for in-progress section) ────────────────

function SectionSkeleton({ cfg }: { cfg: typeof SECTIONS[number] }) {
  return (
    <div className={`rounded-xl border p-4 ${cfg.bgColor} ${cfg.borderColor} animate-pulse`}>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-base leading-none opacity-40">{cfg.icon}</span>
        <div className="h-2.5 w-20 rounded bg-slate-700/60" />
      </div>
      <div className="space-y-1.5">
        <div className="h-3 w-full rounded bg-slate-700/40" />
        <div className="h-3 w-4/5 rounded bg-slate-700/30" />
      </div>
    </div>
  );
}

// ── Typing cursor ─────────────────────────────────────────────────────────────

function TypingCursor() {
  return (
    <span className="inline-block w-0.5 h-3.5 bg-slate-400 ml-0.5 animate-pulse align-middle" />
  );
}

// ── Price target band ──────────────────────────────────────────────────────────

function PriceTargetBand({
  currentPrice, expectedPrice, upsideTarget, downstopStop, expectedReturnPct, atrAbsolute,
}: {
  currentPrice: number; expectedPrice?: number | null; upsideTarget?: number | null;
  downstopStop?: number | null; expectedReturnPct?: number | null; atrAbsolute?: number | null;
}) {
  if (!expectedPrice || currentPrice <= 0) return null;

  const rows = [
    upsideTarget && {
      label: "Upside target", price: upsideTarget,
      pct: ((upsideTarget - currentPrice) / currentPrice) * 100,
      color: "text-emerald-400", dot: "bg-emerald-400",
    },
    { label: "Expected (~3 days)", price: expectedPrice, pct: expectedReturnPct ?? 0, color: "text-sky-400", dot: "bg-sky-400" },
    { label: "Current price",      price: currentPrice,  pct: 0,                      color: "text-slate-300", dot: "bg-slate-400" },
    downstopStop && {
      label: "Stop loss", price: downstopStop,
      pct: ((downstopStop - currentPrice) / currentPrice) * 100,
      color: "text-rose-400", dot: "bg-rose-400",
    },
  ].filter(Boolean) as { label: string; price: number; pct: number; color: string; dot: string }[];

  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-900/50 p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">
          Probabilistic Price Targets
        </span>
        {atrAbsolute && <span className="text-[10px] text-slate-600">ATR: ${atrAbsolute.toFixed(2)}</span>}
      </div>
      <div className="space-y-2">
        {rows.map((row) => (
          <div key={row.label} className="flex items-center gap-3">
            <span className={`h-2 w-2 rounded-full flex-shrink-0 ${row.dot}`} />
            <div className="flex-1 min-w-0"><span className="text-xs text-slate-400">{row.label}</span></div>
            <span className={`text-xs font-mono font-bold tabular-nums ${row.color}`}>${row.price.toFixed(2)}</span>
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

// ── Consensus badge ────────────────────────────────────────────────────────────

function ConsensusBadge({
  agreementCount, totalTimeframes, dominantDirection,
}: { agreementCount: number; totalTimeframes: number; dominantDirection: string }) {
  if (totalTimeframes === 0) return null;
  const pct      = Math.round((agreementCount / totalTimeframes) * 100);
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

// ── Ollama hint ────────────────────────────────────────────────────────────────

function OllamaHint() {
  return (
    <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 px-4 py-3">
      <p className="text-xs font-semibold text-slate-400 mb-1">💡 Start Ollama for AI analysis</p>
      <p className="text-[11px] text-slate-500 leading-relaxed">
        Run <code className="text-sky-400 bg-slate-900 px-1 rounded">ollama serve</code> in a terminal, then refresh.
        <br />
        Pull a model first: <code className="text-sky-400 bg-slate-900 px-1 rounded">ollama pull llama3:8b</code>
      </p>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

interface LLMInsightCardProps {
  symbol:         string;
  signals:        TechnicalSignalDto[];
  currentPrice:   number;
  macroScore?:    number | null;
  vix?:           number | null;
  yieldSpread?:   number | null;
  macroRegime?:   string | null;
  newsSentiment?: { d1?: number | null; d7?: number | null; d30?: number | null };
  gasScore?:      number | null;
  atrAbsolute?:   number | null;
}

export default function LLMInsightCard({
  symbol, signals, currentPrice, macroScore, vix, yieldSpread,
  macroRegime, newsSentiment, gasScore, atrAbsolute,
}: LLMInsightCardProps) {
  const [viewMode, setViewMode] = useState<"short" | "medium" | "long">("short");
  const [triggerKey, setTriggerKey] = useState(0);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const payload = React.useMemo<LLMInsightRequest>(() => ({
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
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [symbol, signals, currentPrice, macroScore, vix, yieldSpread,
      macroRegime, newsSentiment, gasScore, atrAbsolute]);

  const shouldFetch = signals.length > 0 && currentPrice > 0;

  const { state: stream, reset: resetStream } = useStreamInsight(
    symbol, payload, shouldFetch, triggerKey,
  );

  const handleRegenerate = useCallback(() => {
    resetStream();
    setTriggerKey((k) => k + 1);
  }, [resetStream]);

  const isStreaming = stream.status === "streaming";
  const isDone      = stream.status === "done";
  const hasError    = stream.status === "error";
  const sections    = (isDone || isStreaming) ? stream.sections : undefined;
  const isFallback  = stream.meta.backend_used === "fallback";
  const meta        = stream.meta;

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

  // ── Idle (pre-stream start) ────────────────────────────────────────────────
  if (stream.status === "idle") {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-xl">🤖</span>
          <h3 className="text-sm font-bold text-slate-100">Investment Manager Insight</h3>
        </div>
        <div className="space-y-3 animate-pulse">
          {SECTIONS.map((s) => <SectionSkeleton key={s.key} cfg={s} />)}
        </div>
        <p className="mt-3 text-center text-xs text-slate-500 animate-pulse">
          Starting analysis…
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xl">🤖</span>
            <h3 className="text-sm font-bold text-slate-100">Investment Manager Insight</h3>
            {(isDone || isStreaming) && meta.agreement_count != null && (
              <ConsensusBadge
                agreementCount={meta.agreement_count as number}
                totalTimeframes={meta.total_timeframes as number}
                dominantDirection={meta.dominant_direction as string}
              />
            )}
            {isStreaming && (
              <span className="inline-flex items-center gap-1 text-[10px] text-sky-400 font-medium">
                <span className="h-1.5 w-1.5 rounded-full bg-sky-400 animate-ping" />
                Generating…
              </span>
            )}
          </div>
          <p className="text-[10px] text-slate-500 mt-0.5 ml-7">
            {stream.cached
              ? "Cached analysis"
              : meta.backend_used === "ollama"
              ? `Ollama · ${meta.model_used}`
              : meta.backend_used === "groq"
              ? `Groq · ${meta.model_used}`
              : isStreaming
              ? "Connecting…"
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
                viewMode === v ? "bg-slate-700 text-slate-100" : "text-slate-500 hover:text-slate-300"
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
            {hasError
              ? `⚠️ Stream error: ${stream.error}`
              : "⚠️ Ollama is offline — showing pre-computed data only"}
          </p>
          {!hasError && (
            <p className="text-[11px] text-amber-500/70 mt-0.5">
              Start Ollama to get the full investment manager analysis.
            </p>
          )}
        </div>
      )}

      {/* Sections — appear progressively as tokens arrive */}
      <div className="space-y-3">
        {SECTIONS.map((cfg, i) => {
          const text = sections?.[cfg.key];

          // Section is complete or partially written
          if (text) {
            // Determine if this is the currently-streaming (last populated) section
            const allKeys = SECTIONS.map((s) => s.key);
            const populatedIdx = allKeys.reduce((last, k, idx) =>
              sections?.[k] ? idx : last, -1);
            const isCurrentSection = isStreaming && i === populatedIdx;

            return (
              <div
                key={cfg.key}
                className={`rounded-xl border p-4 ${cfg.bgColor} ${cfg.borderColor} transition-all duration-300`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-base leading-none">{cfg.icon}</span>
                  <span className={`text-[10px] font-bold uppercase tracking-widest ${cfg.color}`}>
                    {cfg.label}
                  </span>
                </div>
                <p className="text-sm text-slate-300 leading-relaxed">
                  {text}
                  {isCurrentSection && <TypingCursor />}
                </p>
              </div>
            );
          }

          // Section not yet started — show skeleton while streaming, nothing when done
          if (isStreaming) {
            return <SectionSkeleton key={cfg.key} cfg={cfg} />;
          }
          return null;
        })}
      </div>

      {/* Price target band — show as soon as meta arrives */}
      {meta.expected_price != null && (
        <PriceTargetBand
          currentPrice={currentPrice}
          expectedPrice={meta.expected_price}
          upsideTarget={meta.upside_target}
          downstopStop={meta.downside_stop}
          expectedReturnPct={meta.expected_return_pct}
          atrAbsolute={meta.atr_absolute}
        />
      )}

      {/* Ollama hint when fallback */}
      {isFallback && <OllamaHint />}

      {/* Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-slate-800">
        <p className="text-[10px] text-slate-600 max-w-xs leading-relaxed">
          ⚠️ Educational analysis only. Not investment advice.
        </p>
        <button
          onClick={handleRegenerate}
          disabled={isStreaming}
          className="flex items-center gap-1.5 text-[10px] text-slate-500 hover:text-slate-300 transition-colors disabled:opacity-40"
        >
          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {isStreaming ? "Generating…" : "Regenerate"}
        </button>
      </div>
    </div>
  );
}
