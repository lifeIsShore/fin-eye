"use client";

/**
 * components/DailyMarketBrief.tsx — Sprint 16
 *
 * AI-powered daily market brief: a streaming LLM summary of the current
 * macro regime, sentiment environment, and cross-asset picture.
 *
 * Features:
 *   - Streams from POST /api/v1/explanation/daily-brief/generate-stream (SSE)
 *   - Caches the last generated brief in localStorage (4-hour TTL)
 *   - Displays time-stamped, collapsible, with a "Regenerate" button
 *   - Falls back gracefully if the backend is unavailable
 *   - Shows macro score, sentiment, GAS regime as input badges
 */

import React, { useState, useEffect, useRef, useCallback } from "react";
import { Newspaper, RefreshCw, ChevronDown, ChevronUp, Zap, Clock } from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface BriefCache {
  text: string;
  generatedAt: string; // ISO string
  macroScore: number;
  macroLabel: string;
  regime: string | null;
}

interface Props {
  macroScore: number;
  macroLabel: string;
  regime: string | null;
  sentimentScore: number | null; // -1 to +1
  gasScore: number;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const CACHE_KEY = "fin-eye-daily-brief-v1";
const CACHE_TTL_MS = 4 * 60 * 60 * 1000; // 4 hours

// ── Helpers ───────────────────────────────────────────────────────────────────

function ageLabel(isoStr: string): string {
  const diff = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h ago`;
}

function loadCache(): BriefCache | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const cached: BriefCache = JSON.parse(raw);
    const age = Date.now() - new Date(cached.generatedAt).getTime();
    if (age > CACHE_TTL_MS) return null;
    return cached;
  } catch { return null; }
}

function saveCache(entry: BriefCache) {
  if (typeof window === "undefined") return;
  try { localStorage.setItem(CACHE_KEY, JSON.stringify(entry)); } catch {}
}

function authHeaders(): Record<string, string> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function sentLabel(s: number | null): string {
  if (s == null) return "Unknown";
  if (s > 0.3) return "Bullish";
  if (s > 0.05) return "Mildly Bullish";
  if (s > -0.05) return "Neutral";
  if (s > -0.3) return "Mildly Bearish";
  return "Bearish";
}

function sentColor(s: number | null): string {
  if (s == null) return "text-slate-500";
  if (s > 0.05) return "text-emerald-400";
  if (s > -0.05) return "text-slate-400";
  return "text-rose-400";
}

function macroColor(score: number): string {
  return score >= 60 ? "text-emerald-400" : score >= 40 ? "text-amber-400" : "text-rose-400";
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function DailyMarketBrief({
  macroScore, macroLabel, regime, sentimentScore, gasScore,
}: Props) {
  const [open, setOpen]           = useState(true);
  const [text, setText]           = useState("");
  const [streaming, setStreaming] = useState(false);
  const [cached, setCached]       = useState<BriefCache | null>(null);
  const [error, setError]         = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // On mount: load from cache or auto-generate
  useEffect(() => {
    const c = loadCache();
    if (c) {
      setCached(c);
      setText(c.text);
    } else {
      generate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const generate = useCallback(async () => {
    if (streaming) return;
    if (abortRef.current) abortRef.current.abort();
    abortRef.current = new AbortController();

    setStreaming(true);
    setError(null);
    setText("");
    setCached(null);

    try {
      const res = await fetch(
        `${API}/api/v1/explanation/daily-brief/generate-stream`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            ...authHeaders(),
          },
          body: JSON.stringify({
            macro_score:     macroScore,
            macro_label:     macroLabel,
            regime:          regime ?? "unknown",
            sentiment_score: sentimentScore ?? 0,
            gas_score:       gasScore,
          }),
          signal: abortRef.current.signal,
        },
      );

      if (!res.ok || !res.body) {
        throw new Error(`Backend returned ${res.status}`);
      }

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        // SSE: parse "data: ..." lines
        for (const line of chunk.split("\n")) {
          if (line.startsWith("data: ")) {
            const payload = line.slice(6).trim();
            if (payload === "[DONE]") break;
            try {
              const parsed = JSON.parse(payload);
              const token = parsed.token ?? parsed.text ?? "";
              accumulated += token;
              setText(accumulated);
            } catch {
              // plain text token (non-JSON SSE)
              accumulated += payload;
              setText(accumulated);
            }
          }
        }
      }

      // Cache the result
      const entry: BriefCache = {
        text: accumulated,
        generatedAt: new Date().toISOString(),
        macroScore,
        macroLabel,
        regime: regime ?? null,
      };
      saveCache(entry);
      setCached(entry);
    } catch (err: any) {
      if (err?.name === "AbortError") return;
      setError(err?.message ?? "Failed to generate market brief.");
    } finally {
      setStreaming(false);
    }
  }, [streaming, macroScore, macroLabel, regime, sentimentScore, gasScore]);

  const paragraphs = text.split(/\n{2,}/).filter(Boolean);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/50 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-800/20 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <Newspaper className="h-4 w-4 text-sky-400 flex-shrink-0" />
          <span className="text-sm font-bold text-slate-100">Daily Market Brief</span>
          {streaming && (
            <span className="flex items-center gap-1 text-[10px] font-semibold text-sky-400 animate-pulse">
              <Zap className="h-3 w-3" /> Generating…
            </span>
          )}
          {cached && !streaming && (
            <span className="flex items-center gap-1 text-[10px] text-slate-600">
              <Clock className="h-3 w-3" />
              {ageLabel(cached.generatedAt)}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => { e.stopPropagation(); generate(); }}
            disabled={streaming}
            title="Regenerate brief"
            className="p-1.5 rounded-lg text-slate-600 hover:text-slate-300 hover:bg-slate-800 transition-colors disabled:opacity-40"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${streaming ? "animate-spin" : ""}`} />
          </button>
          {open
            ? <ChevronUp className="h-4 w-4 text-slate-500 flex-shrink-0" />
            : <ChevronDown className="h-4 w-4 text-slate-500 flex-shrink-0" />
          }
        </div>
      </button>

      {open && (
        <div className="border-t border-slate-800 px-5 pb-5 pt-4 space-y-4">
          {/* Input signal badges */}
          <div className="flex flex-wrap gap-2">
            <span className={`text-[10px] font-semibold rounded-full border px-2 py-0.5 ${macroColor(macroScore) === "text-emerald-400" ? "bg-emerald-950/30 border-emerald-800/40 text-emerald-400" : macroColor(macroScore) === "text-rose-400" ? "bg-rose-950/30 border-rose-800/40 text-rose-400" : "bg-amber-950/30 border-amber-800/40 text-amber-400"}`}>
              Macro: {macroLabel} ({macroScore.toFixed(0)})
            </span>
            <span className={`text-[10px] font-semibold rounded-full border px-2 py-0.5 ${sentColor(sentimentScore) === "text-emerald-400" ? "bg-emerald-950/30 border-emerald-800/40 text-emerald-400" : sentColor(sentimentScore) === "text-rose-400" ? "bg-rose-950/30 border-rose-800/40 text-rose-400" : "bg-slate-800/60 border-slate-700/40 text-slate-400"}`}>
              Sentiment: {sentLabel(sentimentScore)}
            </span>
            {regime && (
              <span className="text-[10px] font-semibold rounded-full border bg-sky-950/30 border-sky-800/40 text-sky-400 px-2 py-0.5">
                Regime: {regime.replace(/_/g, " ")}
              </span>
            )}
            <span className={`text-[10px] font-semibold rounded-full border px-2 py-0.5 ${gasScore >= 60 ? "bg-emerald-950/30 border-emerald-800/40 text-emerald-400" : gasScore < 40 ? "bg-rose-950/30 border-rose-800/40 text-rose-400" : "bg-amber-950/30 border-amber-800/40 text-amber-400"}`}>
              GAS: {gasScore.toFixed(0)}
            </span>
          </div>

          {/* Content */}
          {error && !text && (
            <div className="rounded-xl border border-amber-800/30 bg-amber-950/15 px-4 py-3 text-xs text-amber-400 space-y-1">
              <p className="font-semibold">Could not generate brief</p>
              <p className="opacity-75">{error} — ensure Ollama is running and the backend is reachable.</p>
              <button onClick={generate} className="mt-1 text-sky-400 hover:text-sky-300 underline text-[10px]">Retry</button>
            </div>
          )}

          {!text && !error && !streaming && (
            <div className="flex items-center gap-2 text-sm text-slate-600 py-4">
              <span>No brief generated yet.</span>
              <button onClick={generate} className="text-sky-400 hover:text-sky-300 underline text-xs">Generate now</button>
            </div>
          )}

          {text && (
            <div className="space-y-3">
              {paragraphs.map((para, i) => (
                <p key={i} className="text-xs text-slate-300 leading-relaxed">
                  {para}
                  {/* Typing cursor on the last paragraph while streaming */}
                  {streaming && i === paragraphs.length - 1 && (
                    <span className="ml-0.5 inline-block w-0.5 h-3 bg-sky-400 animate-pulse align-middle" />
                  )}
                </p>
              ))}
            </div>
          )}

          <p className="text-[10px] text-slate-600 border-t border-slate-800/50 pt-3">
            AI-generated summary for educational purposes only. Not investment advice. Cached for 4 hours. Powered by Ollama (local LLM).
          </p>
        </div>
      )}
    </div>
  );
}
