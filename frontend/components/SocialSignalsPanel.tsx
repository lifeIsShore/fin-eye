"use client";
/**
 * components/SocialSignalsPanel.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Sprint 42 — Collapsible social signals panel on the dashboard.
 *
 * Shows:
 *   - Reddit mentions + sentiment trend
 *   - StockTwits bull/bear ratio
 *   - Insider net sentiment score
 *   - Composite social score (0-100)
 *
 * Placed below WhatChangedToday in the desktop sidebar and in the
 * mobile layout. Wires to GET /api/v1/sentiment/{symbol}/social.
 */

import React, { useState } from "react";
import useSWR from "swr";
import { fetchSocialSignals, type SocialSignalsDto } from "../lib/api";

interface SocialSignalsPanelProps {
  symbol: string;
}

export default function SocialSignalsPanel({ symbol }: SocialSignalsPanelProps) {
  const [open, setOpen] = useState(true);

  const { data, error, isLoading } = useSWR<SocialSignalsDto>(
    `social-signals-${symbol}`,
    () => fetchSocialSignals(symbol),
    {
      refreshInterval: 120_000,
      shouldRetryOnError: false,
      keepPreviousData: true,
    },
  );

  // Colour helpers
  const scoreColour = (score: number) =>
    score >= 60 ? "text-emerald-400" : score >= 40 ? "text-amber-400" : "text-rose-400";
  const bgColour = (score: number) =>
    score >= 60
      ? "bg-emerald-500"
      : score >= 40
        ? "bg-amber-500"
        : "bg-rose-500";
  const labelColour = (label: string) => {
    const l = label.toLowerCase();
    if (l.includes("bullish") || l.includes("positive")) return "text-emerald-400";
    if (l.includes("bearish") || l.includes("negative")) return "text-rose-400";
    return "text-amber-400";
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
      {/* Header — always visible */}
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-slate-800/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm">📊</span>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            Social Signals
          </span>
        </div>
        <div className="flex items-center gap-2">
          {data && (
            <span
              className={`text-xs font-bold tabular-nums ${scoreColour(data.composite_score)}`}
            >
              {data.composite_score.toFixed(0)}
            </span>
          )}
          <svg
            className={`h-3 w-3 text-slate-600 transition-transform duration-200 ${open ? "rotate-180" : "rotate-0"}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2.5}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Body — collapsible */}
      {open && (
        <div className="px-3 pb-3 space-y-3">
          {isLoading && !data && (
            <div className="h-16 flex items-center justify-center">
              <div className="h-4 w-4 border-2 border-slate-600 border-t-sky-400 rounded-full animate-spin" />
            </div>
          )}

          {error && !data && (
            <p className="text-[10px] text-slate-600 text-center py-2">
              Social signals unavailable
            </p>
          )}

          {data && (
            <>
              {/* Composite score bar */}
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider">
                    Composite
                  </span>
                  <span
                    className={`text-[10px] font-bold ${labelColour(data.composite_label)}`}
                  >
                    {data.composite_label}
                  </span>
                </div>
                <div className="relative h-1.5 rounded-full bg-slate-700 overflow-hidden">
                  <div
                    className={`absolute inset-y-0 left-0 rounded-full transition-all duration-700 ${bgColour(data.composite_score)}`}
                    style={{ width: `${data.composite_score}%` }}
                  />
                  <div className="absolute inset-y-0 left-1/2 w-px bg-slate-500/50" />
                </div>
              </div>

              {/* Reddit */}
              <SignalRow
                icon="🔴"
                label="Reddit"
                available={!!data.reddit}
                mainValue={data.reddit ? `${data.reddit.mentions} mentions` : "–"}
                subValue={
                  data.reddit
                    ? `${data.reddit.bullish_pct.toFixed(0)}% bull`
                    : ""
                }
                sentimentLabel={data.reddit?.sentiment_label}
              />

              {/* StockTwits */}
              <SignalRow
                icon="🐦"
                label="StockTwits"
                available={!!data.stocktwits}
                mainValue={
                  data.stocktwits
                    ? `${data.stocktwits.total_messages} msgs`
                    : "–"
                }
                subValue={
                  data.stocktwits
                    ? data.stocktwits.bull_bear_ratio != null
                      ? `${data.stocktwits.bull_bear_ratio.toFixed(1)}x B/B`
                      : `${data.stocktwits.bullish_pct.toFixed(0)}% bull`
                    : ""
                }
                sentimentLabel={data.stocktwits?.sentiment_label}
              />

              {/* Insider */}
              <SignalRow
                icon="👔"
                label="Insider"
                available={!!data.insider}
                mainValue={
                  data.insider
                    ? `${data.insider.sentiment_score.toFixed(0)}/100`
                    : "–"
                }
                subValue={
                  data.insider
                    ? `${data.insider.buy_transactions}B / ${data.insider.sell_transactions}S`
                    : ""
                }
                sentimentLabel={data.insider?.sentiment_label}
              />

              {/* Disclaimer */}
              <p className="text-[9px] text-slate-600 leading-tight mt-1">
                Social data from public sources. Not investment advice.
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}


// ── Sub-component: single signal row ────────────────────────────────────────

function SignalRow({
  icon,
  label,
  available,
  mainValue,
  subValue,
  sentimentLabel,
}: {
  icon: string;
  label: string;
  available: boolean;
  mainValue: string;
  subValue: string;
  sentimentLabel?: string;
}) {
  const sentCls = sentimentLabel
    ? sentimentLabel.toLowerCase().includes("bull") ||
      sentimentLabel.toLowerCase().includes("positive")
      ? "text-emerald-400 bg-emerald-950/40 border-emerald-800/50"
      : sentimentLabel.toLowerCase().includes("bear") ||
          sentimentLabel.toLowerCase().includes("negative")
        ? "text-rose-400 bg-rose-950/40 border-rose-800/50"
        : "text-amber-400 bg-amber-950/40 border-amber-800/50"
    : "";

  return (
    <div className="flex items-center gap-2 rounded-lg bg-slate-800/30 border border-slate-700/40 px-2.5 py-1.5">
      <span className="text-xs flex-shrink-0">{icon}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-semibold text-slate-400">{label}</span>
          {sentimentLabel && available && (
            <span
              className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full border ${sentCls}`}
            >
              {sentimentLabel}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs font-mono font-bold text-slate-200 tabular-nums">
            {mainValue}
          </span>
          {subValue && (
            <span className="text-[10px] text-slate-500">{subValue}</span>
          )}
        </div>
      </div>
    </div>
  );
}
