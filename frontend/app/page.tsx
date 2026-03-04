"use client";

import React, { useState, useMemo } from "react";
import useSWR from "swr";
import Link from "next/link";
import {
  fetchTechnicalLatest,
  fetchNewsSentiment,
  fetchMacroLatest,
} from "../lib/api";
import MarketWeatherWidget from "../components/MarketWeatherWidget";
import RegimeWidget from "../components/RegimeWidget";
import TimeframeGrid from "../components/TimeframeGrid";
import WhyMovingPanel from "../components/WhyMovingPanel";
import ConflictDetector from "../components/ConflictDetector";
import { GuidedTour } from "../components/onboarding/GuidedTour";

// ─── Helpers ────────────────────────────────────────────────────────────────

const DISCLAIMER =
  "This is educational analysis, not investment advice. " +
  "Fin-Eye surfaces data-driven signals to inform your thinking — " +
  "always conduct your own research before making any financial decisions.";

function directionLabel(score: number): string {
  if (score >= 65) return "Bullish";
  if (score <= 35) return "Bearish";
  return "Neutral";
}

function buildWhyBullets(
  techScore: number,
  signals: { direction: string; timeframe: string }[],
  sent30d: number | null,
  macroScore: number,
  macroLabel: string,
): string[] {
  const bullets: string[] = [];

  // Technical
  const bullishTfs = signals.filter((s) => s.direction === "Bullish").length;
  const bearishTfs = signals.filter((s) => s.direction === "Bearish").length;
  const total = signals.length;
  const techDir = directionLabel(techScore);
  if (total > 0) {
    bullets.push(
      `📈 Technical momentum is ${techDir.toLowerCase()} — ` +
      `${bullishTfs} of ${total} timeframes bullish, ${bearishTfs} bearish ` +
      `(confidence score: ${techScore.toFixed(0)}/100).`,
    );
  } else {
    bullets.push(
      "📈 Technical models have not been trained for this symbol yet; " +
      "technical signals are unavailable.",
    );
  }

  // Sentiment
  if (sent30d !== null) {
    const sentLabel =
      sent30d > 0.3
        ? "strongly positive"
        : sent30d > 0.05
          ? "mildly positive"
          : sent30d > -0.05
            ? "neutral"
            : sent30d > -0.3
              ? "mildly negative"
              : "strongly negative";
    bullets.push(
      `📰 News sentiment over the past 30 days is ${sentLabel} ` +
      `(score: ${sent30d >= 0 ? "+" : ""}${sent30d.toFixed(2)} on a −1 to +1 scale).`,
    );
  } else {
    bullets.push("📰 News sentiment data is not yet available for this symbol.");
  }

  // Macro
  const macroComment =
    macroScore >= 60
      ? "This provides a supportive backdrop for equities."
      : macroScore < 40
        ? "Macro conditions add headwinds to risk assets."
        : "Macro conditions are broadly neutral.";
  bullets.push(
    `🌐 Macro backdrop is '${macroLabel}' (score: ${macroScore.toFixed(0)}/100). ${macroComment}`,
  );

  return bullets;
}

interface ConflictItem {
  layers: string;
  magnitude: string;
  message: string;
}

function detectConflicts(
  techScore: number,
  sentScore0100: number,
  macroScore: number,
  signals: { direction: string }[],
): { hasConflict: boolean; conflicts: ConflictItem[]; summary: string } {
  const conflicts: ConflictItem[] = [];

  const scores: Record<string, number> = {
    Technical: techScore,
    Sentiment: sentScore0100,
    Macro: macroScore,
  };
  const pairs: [string, string][] = [
    ["Technical", "Sentiment"],
    ["Technical", "Macro"],
    ["Sentiment", "Macro"],
  ];

  for (const [a, b] of pairs) {
    const sa = scores[a];
    const sb = scores[b];
    if ((sa > 65 && sb < 35) || (sb > 65 && sa < 35)) {
      const diff = Math.abs(sa - sb);
      conflicts.push({
        layers: `${a} vs ${b}`,
        magnitude: `${diff.toFixed(0)} points apart (${sa.toFixed(0)} vs ${sb.toFixed(0)})`,
        message:
          `${a} is ${directionLabel(sa).toLowerCase()} while ${b} is ${directionLabel(sb).toLowerCase()}. ` +
          `This divergence suggests elevated uncertainty — exercise extra caution.`,
      });
    }
  }

  if (signals.length > 0) {
    const bullish = signals.filter((s) => s.direction === "Bullish").length;
    const bearish = signals.filter((s) => s.direction === "Bearish").length;
    const dominant = Math.max(bullish, bearish);
    const agreement = dominant / signals.length;
    if (agreement < 0.4) {
      conflicts.push({
        layers: "Timeframe Agreement",
        magnitude: `${(agreement * 100).toFixed(0)}% agreement across ${signals.length} timeframes`,
        message:
          `Only ${dominant} of ${signals.length} timeframes agree on direction. ` +
          `Low cross-timeframe consensus increases signal uncertainty.`,
      });
    }
  }

  const hasConflict = conflicts.length > 0;
  const summary = hasConflict
    ? `${conflicts.length} conflict(s) detected. Review the signals below carefully.`
    : "No major conflicts detected — layers are broadly aligned.";

  return { hasConflict, conflicts, summary };
}

// ─── Page Component ─────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [tickerInput, setTickerInput] = useState("AAPL");
  const [activeSymbol, setActiveSymbol] = useState("AAPL");

  const { data: techData, error: techError } = useSWR(
    `tech-${activeSymbol}`,
    () => fetchTechnicalLatest(activeSymbol),
    { refreshInterval: 60000, shouldRetryOnError: false },
  );

  const { data: sentData, error: sentError } = useSWR(
    `sent-${activeSymbol}`,
    () => fetchNewsSentiment(activeSymbol),
    { refreshInterval: 60000, shouldRetryOnError: false },
  );

  const { data: macroData, error: macroError } = useSWR(
    "macro-latest",
    () => fetchMacroLatest(),
    { refreshInterval: 300000, shouldRetryOnError: false },
  );

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (tickerInput.trim()) {
      setActiveSymbol(tickerInput.trim().toUpperCase());
    }
  };

  const isLoading = !techData && !techError && !sentError && !macroError;

  // ── Derived scores ──────────────────────────────────────────────────────
  const techScore = techData?.technical_confidence_score ?? 50;
  const sent30d = sentData?.sentiment_30d ?? null;
  const macroScore = macroData?.macro_score?.score ?? 50;
  const macroLabel = macroData?.macro_score?.label ?? "Neutral";
  const vixLevel = macroData?.data?.vix?.value ?? null;
  const signals = techData?.signals ?? [];

  const gasScore = useMemo(() => {
    if (techData && sentData && macroData?.macro_score) {
      const sentNorm = ((sent30d ?? 0) + 1) / 2;
      return techScore * 0.4 + sentNorm * 100 * 0.3 + macroScore * 0.3;
    }
    return 50;
  }, [techData, sentData, macroData, techScore, sent30d, macroScore]);

  // ── EXPL-01 – Why is this moving? ──────────────────────────────────────
  const whyBullets = useMemo(
    () => buildWhyBullets(techScore, signals, sent30d, macroScore, macroLabel),
    [techScore, signals, sent30d, macroScore, macroLabel],
  );

  // ── EXPL-02 – Conflict detection ───────────────────────────────────────
  const sentScore0100 = ((sent30d ?? 0) + 1) / 2 * 100;
  const conflictData = useMemo(
    () => detectConflicts(techScore, sentScore0100, macroScore, signals),
    [techScore, sentScore0100, macroScore, signals],
  );

  return (
    <div className="space-y-6">
      <GuidedTour />
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-3xl font-black tracking-tight text-slate-100">
            {activeSymbol} Intelligence
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Real-time GAS, Regime, and Multi-Timeframe layers.
          </p>
        </div>

        <form onSubmit={handleSearch} className="flex gap-2 w-full sm:w-auto">
          <input
            type="text"
            value={tickerInput}
            onChange={(e) => setTickerInput(e.target.value)}
            placeholder="Enter Ticker..."
            className="w-full sm:w-48 rounded-md bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
          />
          <button
            type="submit"
            className="rounded-md bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 transition-colors"
          >
            Analyze
          </button>
          <button
            type="button"
            onClick={() => {
              if (typeof window !== "undefined" && (window as any).restartFinEyeTour) {
                (window as any).restartFinEyeTour();
              }
            }}
            className="rounded-md bg-slate-800 border border-slate-700 px-3 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-700 transition-colors"
          >
            Tour
          </button>
        </form>
      </header>

      {isLoading ? (
        <div className="py-20 text-center animate-pulse text-slate-500">
          Gathering market intelligence for {activeSymbol}...
        </div>
      ) : (
        <div className="space-y-6">
          {/* Row 1 – GAS + Regime + Timeframe Grid */}
          <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="tour-gas-score">
              <MarketWeatherWidget gasScore={gasScore} />
            </div>

            <div className="flex flex-col space-y-4">
              <div className="tour-regime">
                <RegimeWidget technicalScore={techScore} vixLevel={vixLevel} />
              </div>

              <div className="tour-timeframes p-5 rounded-2xl border border-slate-800 bg-slate-900/40">
                <div className="flex justify-between items-center mb-1">
                  <h3 className="text-sm font-semibold text-slate-100">
                    Technical Consensus
                  </h3>
                  <span className="text-sky-400 font-bold text-sm">
                    {techData?.technical_confidence_score.toFixed(1)} / 100
                  </span>
                </div>
                {techData?.signals?.length ? (
                  <TimeframeGrid signals={techData.signals} />
                ) : (
                  <p className="text-xs text-rose-400 mt-4 px-3 py-2 bg-rose-950/20 rounded border border-rose-900">
                    {techError?.message ||
                      "Technical models are not trained for this symbol."}
                  </p>
                )}
              </div>
            </div>
          </section>

          {/* Row 2 – EXPL-01 + EXPL-02 (MVP-EXPL-01, MVP-EXPL-02) */}
          <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="tour-why-moving">
              <WhyMovingPanel
                symbol={activeSymbol}
                bullets={whyBullets}
                disclaimer={DISCLAIMER}
              />
            </div>
            <ConflictDetector
              hasConflict={conflictData.hasConflict}
              conflicts={conflictData.conflicts}
              conflictSummary={conflictData.summary}
            />
          </section>

          {/* Row 3 – Quick links */}
          <section className="flex flex-wrap gap-4 pt-4 border-t border-slate-800/50">
            <Link
              href="/macro"
              className="text-sm text-sky-400 hover:text-sky-300 font-medium transition-colors"
            >
              View Full Macro Intel &rarr;
            </Link>
            <Link
              href="/news-sentiment"
              className="text-sm text-sky-400 hover:text-sky-300 font-medium transition-colors"
            >
              View Full Sentiment Intel &rarr;
            </Link>
          </section>
        </div>
      )}
    </div>
  );
}
