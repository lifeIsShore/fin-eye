"use client";

import React, { useState, useMemo, useCallback, useRef } from "react";
import useSWR from "swr";
import Link from "next/link";
import { searchTickers } from "../lib/tickers";
import { useSymbol } from "../lib/symbolContext";
import {
  fetchTechnicalLatest,
  fetchNewsSentiment,
  fetchMacroLatest,
  fetchGasSnapshot,
  fetchExplanationSummary,
  type GasSnapshotDto,
} from "../lib/api";
import MarketWeatherWidget from "../components/MarketWeatherWidget";
import RegimeWidget from "../components/RegimeWidget";
import TimeframeGrid from "../components/TimeframeGrid";
import WhyMovingPanel from "../components/WhyMovingPanel";
import ConflictDetector from "../components/ConflictDetector";
import { GuidedTour } from "../components/onboarding/GuidedTour";
import { WatchlistWidget } from "../components/WatchlistWidget";
import ScoreExplainPanel, {
  type ExplainPayload,
  type SubComponent,
} from "../components/ScoreExplainPanel";

// ─── Constants ───────────────────────────────────────────────────────────────

const DISCLAIMER =
  "This is educational analysis, not investment advice. " +
  "Fin-Eye surfaces data-driven signals to inform your thinking — " +
  "always conduct your own research before making any financial decisions.";

const STALE_THRESHOLD_MS = 30 * 60 * 1000;

// ─── Helpers ────────────────────────────────────────────────────────────────

function directionLabel(score: number): string {
  if (score >= 65) return "Bullish";
  if (score <= 35) return "Bearish";
  return "Neutral";
}

function snapshotAgeMinutes(computedAt: string | undefined): number | null {
  if (!computedAt) return null;
  const ageMs = Date.now() - new Date(computedAt).getTime();
  return Math.floor(ageMs / 60_000);
}

function buildWhyBullets(
  techScore: number,
  signals: { direction: string; timeframe: string }[],
  sent30d: number | null,
  macroScore: number,
  macroLabel: string,
): string[] {
  const bullets: string[] = [];
  const bullishTfs = signals.filter((s) => s.direction === "Bullish").length;
  const bearishTfs = signals.filter((s) => s.direction === "Bearish").length;
  const total      = signals.length;
  const techDir    = directionLabel(techScore);

  if (total > 0) {
    bullets.push(
      `📈 Technical momentum is ${techDir.toLowerCase()} — ` +
      `${bullishTfs} of ${total} timeframes bullish, ${bearishTfs} bearish ` +
      `(confidence score: ${techScore.toFixed(0)}/100).`,
    );
  } else {
    bullets.push(
      "📈 Technical models have not been trained for this symbol yet; technical signals are unavailable.",
    );
  }

  if (sent30d !== null) {
    const sentLabel =
      sent30d > 0.3  ? "strongly positive" :
      sent30d > 0.05 ? "mildly positive"   :
      sent30d > -0.05 ? "neutral"           :
      sent30d > -0.3  ? "mildly negative"   : "strongly negative";
    bullets.push(
      `📰 News sentiment over the past 30 days is ${sentLabel} ` +
      `(score: ${sent30d >= 0 ? "+" : ""}${sent30d.toFixed(2)} on a −1 to +1 scale).`,
    );
  } else {
    bullets.push("📰 News sentiment data is not yet available for this symbol.");
  }

  const macroComment =
    macroScore >= 60 ? "This provides a supportive backdrop for equities." :
    macroScore < 40  ? "Macro conditions add headwinds to risk assets."     :
                       "Macro conditions are broadly neutral.";
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
  const scores: Record<string, number> = { Technical: techScore, Sentiment: sentScore0100, Macro: macroScore };
  const pairs: [string, string][] = [["Technical", "Sentiment"], ["Technical", "Macro"], ["Sentiment", "Macro"]];

  for (const [a, b] of pairs) {
    const sa = scores[a]; const sb = scores[b];
    if ((sa > 65 && sb < 35) || (sb > 65 && sa < 35)) {
      conflicts.push({
        layers:    `${a} vs ${b}`,
        magnitude: `${Math.abs(sa - sb).toFixed(0)} points apart (${sa.toFixed(0)} vs ${sb.toFixed(0)})`,
        message:   `${a} is ${directionLabel(sa).toLowerCase()} while ${b} is ${directionLabel(sb).toLowerCase()}. This divergence suggests elevated uncertainty — exercise extra caution.`,
      });
    }
  }

  if (signals.length > 0) {
    const bullish  = signals.filter((s) => s.direction === "Bullish").length;
    const bearish  = signals.filter((s) => s.direction === "Bearish").length;
    const dominant = Math.max(bullish, bearish);
    const agreement = dominant / signals.length;
    if (agreement < 0.4) {
      conflicts.push({
        layers:    "Timeframe Agreement",
        magnitude: `${(agreement * 100).toFixed(0)}% agreement across ${signals.length} timeframes`,
        message:   `Only ${dominant} of ${signals.length} timeframes agree on direction. Low cross-timeframe consensus increases signal uncertainty.`,
      });
    }
  }

  const hasConflict = conflicts.length > 0;
  return {
    hasConflict,
    conflicts,
    summary: hasConflict
      ? `${conflicts.length} conflict(s) detected. Review the signals below carefully.`
      : "No major conflicts detected — layers are broadly aligned.",
  };
}

// ─── Explain payload builders ─────────────────────────────────────────────────

function buildGasPayload(
  gasScore: number,
  techScore: number,
  sent30d: number | null,
  macroScore: number,
  macroLabel: string,
): ExplainPayload {
  const sentScore0100 = ((sent30d ?? 0) + 1) / 2 * 100;
  const sentRaw = sent30d !== null ? `${sent30d >= 0 ? "+" : ""}${sent30d.toFixed(2)}` : "N/A";

  const scoreColor = (s: number): SubComponent["color"] =>
    s >= 65 ? "emerald" : s >= 55 ? "teal" : s >= 45 ? "amber" : s >= 35 ? "orange" : "rose";

  return {
    target: "gas",
    title: "Global Alignment Score (GAS)",
    score: gasScore,
    scoreLabel: "/ 100",
    summary: `The GAS is a composite signal that blends three independent layers — Technical momentum (40%), News Sentiment (30%), and Macro conditions (30%). A score above 60 indicates bullish alignment; below 40 signals bearish pressure.`,
    subComponents: [
      {
        label:       "Technical Score",
        value:       techScore,
        rawLabel:    `${techScore.toFixed(0)} / 100`,
        color:       scoreColor(techScore),
        description: `ML-driven consensus across multiple timeframes. Contributes 40% to GAS. Score reflects how many timeframes and signals align in the same direction.`,
      },
      {
        label:       "Sentiment Score",
        value:       sentScore0100,
        rawLabel:    sentRaw,
        color:       scoreColor(sentScore0100),
        description: `Aggregated news sentiment from the past 30 days. Normalised from a −1/+1 raw score to 0–100 for GAS weighting. Contributes 30% to GAS.`,
      },
      {
        label:       "Macro Score",
        value:       macroScore,
        rawLabel:    `${macroScore.toFixed(0)} / 100 (${macroLabel})`,
        color:       scoreColor(macroScore),
        description: `Composite of FRED macro indicators: yield curve, unemployment, CPI, PMI, and VIX. Contributes 30% to GAS.`,
      },
    ],
    methodology: `GAS = (Technical × 0.40) + (Sentiment × 0.30) + (Macro × 0.30). All three components are independently computed and normalised to 0–100. The GAS is pre-computed every 15 minutes during US market hours and cached for sub-200ms response times.`,
  };
}

function buildTechnicalPayload(
  techScore: number,
  signals: { direction: string; timeframe: string }[],
): ExplainPayload {
  const bullish = signals.filter((s) => s.direction === "Bullish").length;
  const bearish = signals.filter((s) => s.direction === "Bearish").length;
  const neutral = signals.length - bullish - bearish;

  const tfSubs: SubComponent[] = signals.map((s) => ({
    label:       s.timeframe,
    value:       s.direction === "Bullish" ? 75 : s.direction === "Bearish" ? 25 : 50,
    rawLabel:    s.direction,
    color:       (s.direction === "Bullish" ? "emerald" : s.direction === "Bearish" ? "rose" : "amber") as SubComponent["color"],
    description: `${s.timeframe} timeframe ML model output. Each timeframe is trained independently on OHLCV features.`,
  }));

  return {
    target: "technical",
    title: "Technical Confidence Score",
    score: techScore,
    scoreLabel: "/ 100",
    weight: "40% of GAS",
    summary: `${bullish} of ${signals.length} timeframes are bullish, ${bearish} bearish, ${neutral} neutral. The score reflects the weighted agreement of ML models across multiple timeframes.`,
    subComponents: tfSubs.length > 0 ? tfSubs : [
      {
        label: "No signals", value: 50, rawLabel: "N/A", color: "slate",
        description: "Models have not yet been trained for this symbol. A neutral 50 is used as a fallback.",
      },
    ],
    methodology: `Each timeframe uses a trained scikit-learn classifier on rolling OHLCV features (RSI, MACD, Bollinger Bands, volume ratios, etc.). Outputs are aggregated into a 0–100 confidence score using weighted voting. Models are retrained periodically from the JSONL artifact registry.`,
  };
}

function buildSentimentPayload(
  sent30d: number | null,
  sent7d: number | null,
  sent1d: number | null,
): ExplainPayload {
  const toScore = (v: number | null) => v !== null ? ((v + 1) / 2) * 100 : 50;
  const toLabel = (v: number | null) => v !== null ? `${v >= 0 ? "+" : ""}${v.toFixed(3)}` : "N/A";
  const scoreColor = (s: number): SubComponent["color"] =>
    s >= 65 ? "emerald" : s >= 55 ? "teal" : s >= 45 ? "amber" : s >= 35 ? "orange" : "rose";

  const score30 = toScore(sent30d);

  return {
    target: "sentiment",
    title: "News Sentiment",
    score: score30,
    scoreLabel: "/ 100 (30d)",
    weight: "30% of GAS",
    summary: `Sentiment is derived from news articles about this symbol using VADER NLP. Scores run from −1 (very negative) to +1 (very positive). The 30-day rolling average is used for GAS weighting.`,
    subComponents: [
      {
        label: "30-Day Sentiment", value: score30, rawLabel: toLabel(sent30d),
        color: scoreColor(score30),
        description: "Average VADER compound score across all articles in the past 30 days. Primary input into GAS (30% weight).",
      },
      {
        label: "7-Day Sentiment", value: toScore(sent7d), rawLabel: toLabel(sent7d),
        color: scoreColor(toScore(sent7d)),
        description: "Shorter-term sentiment window — useful for detecting recent narrative shifts vs the 30d baseline.",
      },
      {
        label: "1-Day Sentiment", value: toScore(sent1d), rawLabel: toLabel(sent1d),
        color: scoreColor(toScore(sent1d)),
        description: "Most recent 24h sentiment. High variance due to small sample size — treat as directional signal only.",
      },
    ],
    methodology: `Articles are fetched from Finnhub News and scored using the VADER (Valence Aware Dictionary and sEntiment Reasoner) NLP model. Each article's compound score (−1 to +1) is averaged over the window. Source breakdown is available on the full Sentiment page.`,
  };
}

function buildMacroPayload(
  macroScore: number,
  macroLabel: string,
  macroData: any,
  vixLevel: number | null,
): ExplainPayload {
  const scoreColor = (s: number): SubComponent["color"] =>
    s >= 65 ? "emerald" : s >= 55 ? "teal" : s >= 45 ? "amber" : s >= 35 ? "orange" : "rose";

  const vixScore = vixLevel !== null
    ? vixLevel < 15 ? 75 : vixLevel <= 25 ? 50 : 25
    : 50;

  const subs: SubComponent[] = [
    {
      label: "Macro Composite",
      value: macroScore,
      rawLabel: `${macroScore.toFixed(0)} / 100 (${macroLabel})`,
      color: scoreColor(macroScore),
      description: "Weighted composite of all FRED macro indicators. Contributes 30% to GAS.",
    },
    {
      label: "VIX (Volatility Index)",
      value: vixScore,
      rawLabel: vixLevel !== null ? vixLevel.toFixed(2) : "N/A",
      color: (vixLevel === null ? "slate" : vixLevel < 15 ? "sky" : vixLevel <= 25 ? "amber" : "rose") as SubComponent["color"],
      description: "CBOE Volatility Index. Below 15 = calm markets (bullish bias). Above 25 = elevated fear (bearish bias).",
    },
  ];

  const yc = macroData?.data?.yield_curve;
  if (yc) {
    const ycScore = yc.shape === "Normal" ? 65 : yc.shape === "Inverted" ? 30 : 50;
    subs.push({
      label: "Yield Curve",
      value: ycScore,
      rawLabel: yc.shape ?? "Unknown",
      color: scoreColor(ycScore),
      description: `Current yield curve shape: ${yc.shape ?? "Unknown"}. An inverted curve historically precedes recessions. Fin-Eye uses the 2Y–10Y spread as the primary signal.`,
    });
  }

  return {
    target: "macro",
    title: "Macro Score",
    score: macroScore,
    scoreLabel: `/ 100 (${macroLabel})`,
    weight: "30% of GAS",
    summary: `Macro conditions are currently '${macroLabel}'. This layer aggregates economic health indicators from the FRED API to assess whether the broad environment supports or opposes equity risk-taking.`,
    subComponents: subs,
    methodology: `Five FRED indicators are fetched and scored individually: Yield Curve (2Y/10Y spread), VIX, Unemployment Rate, CPI YoY, and ISM PMI. Each is normalised to 0–100 based on historical ranges and averaged into the macro composite score. Data refreshes every 5 minutes.`,
  };
}

function buildVolatilityPayload(vixLevel: number | null): ExplainPayload {
  const vixScore = vixLevel !== null
    ? vixLevel < 15 ? 80 : vixLevel <= 25 ? 50 : 20
    : 50;

  return {
    target: "macro",
    title: "Volatility Regime",
    score: vixScore,
    scoreLabel: vixLevel !== null ? `VIX ${vixLevel.toFixed(1)}` : "VIX N/A",
    summary: `The Volatility Regime is derived solely from the CBOE VIX level. It provides a quick read on market fear and option pricing pressure, independent of directional signals.`,
    subComponents: [
      {
        label: "VIX Level",
        value: vixScore,
        rawLabel: vixLevel !== null ? vixLevel.toFixed(2) : "N/A",
        color: vixLevel === null ? "slate" : vixLevel < 15 ? "sky" : vixLevel <= 25 ? "amber" : "rose",
        description:
          vixLevel === null
            ? "VIX data unavailable."
            : vixLevel < 15
              ? "VIX below 15 — markets are calm. Options are cheap, implied volatility is low."
              : vixLevel <= 25
                ? "VIX 15–25 — moderate uncertainty. Normal trading conditions."
                : "VIX above 25 — elevated fear. Options are expensive; markets pricing in sharp moves.",
      },
    ],
    methodology: `The VIX (CBOE Volatility Index) measures 30-day implied volatility on S&P 500 options. Thresholds: <15 = Low Volatility, 15–25 = Medium Volatility, >25 = High Volatility. VIX data is sourced from FRED (VIXCLS series).`,
  };
}

// ─── Staleness badge ─────────────────────────────────────────────────────────

function SnapshotMeta({ snapshot }: { snapshot: GasSnapshotDto | undefined }) {
  if (!snapshot) return null;
  const ageMin = snapshotAgeMinutes(snapshot.computed_at);
  const isStale = ageMin !== null && ageMin * 60_000 > STALE_THRESHOLD_MS;
  const ageLabel = ageMin === null ? "age unknown" : ageMin < 1 ? "just now" : `${ageMin}m ago`;
  const sourceColor =
    snapshot.source === "cache" ? "text-emerald-400" :
    snapshot.source === "db_snapshot" ? "text-sky-400" : "text-amber-400";

  return (
    <div className="flex items-center gap-2 text-xs text-slate-500">
      <span className={sourceColor}>●</span>
      <span>
        GAS computed {ageLabel}
        {isStale && <span className="ml-1 text-amber-400 font-medium">(stale — refreshing)</span>}
      </span>
      {snapshot.component_scores && (
        <span className="hidden sm:inline text-slate-600">
          T:{snapshot.component_scores.technical?.toFixed(0)}
          {" "}S:{snapshot.component_scores.sentiment?.toFixed(0)}
          {" "}M:{snapshot.component_scores.macro?.toFixed(0)}
        </span>
      )}
    </div>
  );
}

// ─── Page Component ──────────────────────────────────────────────────────────

const TICKER_REGEX = /^[A-Z]{1,5}(-[A-Z]{2,4})?$/;

function normalizeTicker(raw: string): string {
  return raw.trim().toUpperCase().replace(/\s+/g, "");
}

export default function DashboardPage() {
  const { symbol: activeSymbol, setSymbol: setActiveSymbol } = useSymbol();

  // Collapsible tech explanation — collapsed by default for experienced users
  const [techExplainOpen, setTechExplainOpen] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem('fin-eye-tech-explain-open') === 'true';
  });
  const toggleTechExplain = useCallback(() => {
    setTechExplainOpen((v) => {
      const next = !v;
      localStorage.setItem('fin-eye-tech-explain-open', String(next));
      return next;
    });
  }, []);

  const [explainPayload, setExplainPayload] = useState<ExplainPayload | null>(null);
  const closeExplain = useCallback(() => setExplainPayload(null), []);

  const { data: gasSnapshot, error: gasError, isLoading: gasLoading } = useSWR(
    `gas-snapshot-${activeSymbol}`,
    () => fetchGasSnapshot(activeSymbol),
    { refreshInterval: 60_000, shouldRetryOnError: false, keepPreviousData: true },
  );

  const { data: techData, error: techError } = useSWR(
    `tech-${activeSymbol}`,
    () => fetchTechnicalLatest(activeSymbol),
    { refreshInterval: 120_000, shouldRetryOnError: false, keepPreviousData: true },
  );

  const { data: sentData } = useSWR(
    `sent-${activeSymbol}`,
    () => fetchNewsSentiment(activeSymbol),
    { refreshInterval: 120_000, shouldRetryOnError: false, keepPreviousData: true },
  );

  const { data: macroData } = useSWR(
    "macro-latest",
    () => fetchMacroLatest(),
    { refreshInterval: 300_000, shouldRetryOnError: false, keepPreviousData: true },
  );

  const gasScore: number = gasSnapshot?.gas_score
    ?? (() => {
      const ts = techData?.technical_confidence_score ?? 50;
      const sm = ((sentData?.sentiment_30d ?? 0) + 1) / 2 * 100;
      const ms = macroData?.macro_score?.score ?? 50;
      return ts * 0.4 + sm * 0.3 + ms * 0.3;
    })();

  const regimeFromSnapshot = gasSnapshot?.regime;
  const techScore  = gasSnapshot?.component_scores?.technical ?? techData?.technical_confidence_score ?? 50;
  const sent30d    = sentData?.sentiment_30d ?? null;
  const sent7d     = sentData?.sentiment_7d ?? null;
  const sent1d     = sentData?.sentiment_1d ?? null;
  const macroScore = gasSnapshot?.component_scores?.macro ?? macroData?.macro_score?.score ?? 50;
  const macroLabel = macroData?.macro_score?.label ?? "Neutral";
  const vixLevel   = macroData?.data?.vix?.value ?? null;
  const signals    = techData?.signals ?? [];
  const isLoading  = gasLoading && !gasSnapshot && !gasError;

  const explainParamsStr = !isLoading ? JSON.stringify({
    tech_score: techScore,
    sent_30d: sent30d,
    macro_score: macroScore,
    macro_label: macroLabel,
    gas_score: gasScore,
    tech_signals: JSON.stringify(signals),
  }) : null;

  const { data: explanationData } = useSWR(
    explainParamsStr ? [`explanation-${activeSymbol}`, explainParamsStr] : null,
    ([_, paramsStr]) => {
      const p = JSON.parse(paramsStr);
      return fetchExplanationSummary(activeSymbol, p as any);
    },
    { refreshInterval: 60_000, shouldRetryOnError: false, keepPreviousData: true },
  );

  const whyBullets = explanationData?.why_moving ?? useMemo(
    () => buildWhyBullets(techScore, signals, sent30d, macroScore, macroLabel),
    [techScore, signals, sent30d, macroScore, macroLabel],
  );

  const sentScore0100 = ((sent30d ?? 0) + 1) / 2 * 100;
  const conflictData  = explanationData ? {
    hasConflict: explanationData.has_conflict,
    conflicts: explanationData.conflicts,
    summary: explanationData.conflict_summary,
  } : useMemo(
    () => detectConflicts(techScore, sentScore0100, macroScore, signals),
    [techScore, sentScore0100, macroScore, signals],
  );
  
  const initialAiSummary = explanationData?.ai_summary ?? null;

  const openGasExplain = useCallback(() =>
    setExplainPayload(buildGasPayload(gasScore, techScore, sent30d, macroScore, macroLabel)),
    [gasScore, techScore, sent30d, macroScore, macroLabel],
  );
  const openTechnicalExplain = useCallback(() =>
    setExplainPayload(buildTechnicalPayload(techScore, signals)),
    [techScore, signals],
  );
  const openMacroExplain = useCallback(() =>
    setExplainPayload(buildMacroPayload(macroScore, macroLabel, macroData, vixLevel)),
    [macroScore, macroLabel, macroData, vixLevel],
  );
  const openVolatilityExplain = useCallback(() =>
    setExplainPayload(buildVolatilityPayload(vixLevel)),
    [vixLevel],
  );

  return (
    <div className="space-y-6">
      <GuidedTour />

      <ScoreExplainPanel payload={explainPayload} onClose={closeExplain} />

      <div className="flex gap-6">
        <aside className="hidden xl:block w-48 flex-shrink-0">
          <WatchlistWidget
            activeSymbol={activeSymbol}
            onSelectSymbol={(sym) => setActiveSymbol(sym)}
          />
        </aside>

        <div className="min-w-0 flex-1 space-y-6">
          <header className="flex flex-col gap-1 border-b border-slate-800 pb-5">
            <h1 className="text-3xl font-black tracking-tight text-slate-100">
              {activeSymbol} Intelligence
            </h1>
            <p className="text-sm text-slate-400">
              Real-time GAS, Regime, and Multi-Timeframe layers.
            </p>
            <div className="mt-0.5">
              <SnapshotMeta snapshot={gasSnapshot} />
            </div>
          </header>

          <div className="xl:hidden">
            <WatchlistWidget
              activeSymbol={activeSymbol}
              onSelectSymbol={(sym) => setActiveSymbol(sym)}
            />
          </div>

          {isLoading ? (
            <div className="py-20 text-center animate-pulse text-slate-500">
              Gathering market intelligence for {activeSymbol}…
            </div>
          ) : (
            <div className="space-y-6">

              {/* Row 1 – GAS + Regime */}
              <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="tour-gas-score">
                  <MarketWeatherWidget gasScore={gasScore} onExplain={openGasExplain} />
                </div>
                <div className="tour-regime">
                  <RegimeWidget
                    technicalScore={techScore}
                    vixLevel={vixLevel}
                    regimeOverride={regimeFromSnapshot}
                    onExplainTechnical={openTechnicalExplain}
                    onExplainVolatility={openVolatilityExplain}
                  />
                </div>
              </section>

              {/* Row 2 – Technical Consensus (full width) */}
              <section className="tour-timeframes p-5 rounded-2xl border border-slate-800 bg-slate-900/40 space-y-4">

                {/* Score header */}
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div>
                    <h3 className="text-base font-bold text-slate-100">Technical Consensus</h3>
                    <p className="text-xs text-slate-500 mt-0.5">Sharpe-weighted ML signal across all trained timeframes</p>
                  </div>
                  <div className="flex items-baseline gap-2 flex-shrink-0">
                    <span className={`text-4xl font-black tabular-nums ${
                      techScore >= 60 ? 'text-emerald-400' :
                      techScore >= 40 ? 'text-amber-400' : 'text-rose-400'
                    }`}>{techScore.toFixed(1)}</span>
                    <span className="text-slate-500 text-base">/ 100</span>
                    <span className={`ml-1 text-xs font-bold px-2 py-0.5 rounded-full border ${
                      techScore >= 60 ? 'text-emerald-400 bg-emerald-950/40 border-emerald-800/50' :
                      techScore >= 40 ? 'text-amber-400 bg-amber-950/40 border-amber-800/50' :
                                        'text-rose-400 bg-rose-950/40 border-rose-800/50'
                    }`}>
                      {techScore >= 80 ? 'Strong Bullish' : techScore >= 60 ? 'Bullish Lean' :
                       techScore >= 40 ? 'Mixed / Neutral' : techScore >= 20 ? 'Bearish Lean' : 'Strong Bearish'}
                    </span>
                  </div>
                </div>

                {/* Collapsible explanation — collapsed by default, toggle persisted */}
                {signals.length > 0 && (
                  <div>
                    <button
                      onClick={toggleTechExplain}
                      className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors group"
                    >
                      <svg
                        className={`h-3.5 w-3.5 transition-transform duration-200 ${techExplainOpen ? 'rotate-90' : 'rotate-0'}`}
                        fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                      </svg>
                      <span className="group-hover:underline">
                        {techExplainOpen ? 'Hide explanation' : 'How is this score calculated?'}
                      </span>
                    </button>

                    {techExplainOpen && (
                      <div className="mt-3 rounded-xl bg-slate-800/50 border border-slate-700/60 px-4 py-3 space-y-3">

                        {/* Progress bar */}
                        <div className="flex items-center gap-3">
                          <span className="text-[10px] text-slate-600 w-12 flex-shrink-0">0 Bear</span>
                          <div className="relative flex-1 h-2.5 rounded-full bg-slate-700 overflow-hidden">
                            <div className={`absolute inset-y-0 left-0 rounded-full transition-all duration-700 ${
                              techScore >= 60 ? 'bg-emerald-500' : techScore >= 40 ? 'bg-amber-500' : 'bg-rose-500'
                            }`} style={{ width: `${techScore}%` }} />
                            <div className="absolute inset-y-0 left-1/2 w-px bg-slate-400/50" title="50 = neutral" />
                          </div>
                          <span className="text-[10px] text-slate-600 w-14 flex-shrink-0 text-right">100 Bull</span>
                        </div>

                        {/* 3 stat cards */}
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                          <div className="rounded-lg bg-slate-900/60 border border-slate-700/50 px-3 py-2">
                            <p className="text-slate-500 mb-0.5">Scale</p>
                            <p className="text-slate-200 font-semibold">0 &ndash; 100</p>
                            <p className="text-slate-500 text-[10px] mt-0.5">50 = perfectly neutral</p>
                          </div>
                          <div className="rounded-lg bg-slate-900/60 border border-slate-700/50 px-3 py-2">
                            <p className="text-slate-500 mb-0.5">Score {techScore.toFixed(1)}</p>
                            <p className={`font-semibold ${
                              techScore >= 60 ? 'text-emerald-400' : techScore >= 40 ? 'text-amber-400' : 'text-rose-400'
                            }`}>
                              {techScore < 40 ? `${(50 - techScore).toFixed(0)} pts below neutral` :
                               techScore > 60 ? `${(techScore - 50).toFixed(0)} pts above neutral` : 'Near neutral (50)'}
                            </p>
                            <p className="text-slate-500 text-[10px] mt-0.5">vs midpoint of 50</p>
                          </div>
                          <div className="rounded-lg bg-slate-900/60 border border-slate-700/50 px-3 py-2">
                            <p className="text-slate-500 mb-0.5">Method</p>
                            <p className="text-slate-200 font-semibold">Sharpe-weighted avg</p>
                            <p className="text-slate-500 text-[10px] mt-0.5">better models count more</p>
                          </div>
                        </div>

                        {/* Plain-English formula */}
                        <p className="text-[11px] text-slate-500 leading-relaxed">
                          Each timeframe outputs a signal from{' '}
                          <span className="text-rose-400 font-medium">-1 (bearish)</span> to{' '}
                          <span className="text-emerald-400 font-medium">+1 (bullish)</span>,
                          averaged weighted by each model&apos;s{' '}
                          <span className="text-sky-400 font-medium">Sharpe Ratio</span>{' '}
                          (better historical performance = more weight),
                          then mapped to 0&ndash;100 where 50 = neutral.
                          A score of{' '}
                          <span className={`font-bold ${
                            techScore >= 60 ? 'text-emerald-400' : techScore >= 40 ? 'text-amber-400' : 'text-rose-400'
                          }`}>{techScore.toFixed(1)}</span>{' '}
                          means the models are net{' '}
                          <span className={`font-medium ${
                            techScore >= 60 ? 'text-emerald-400' : techScore >= 40 ? 'text-amber-400' : 'text-rose-400'
                          }`}>{techScore >= 60 ? 'bullish' : techScore >= 40 ? 'roughly neutral' : 'bearish'}</span>.
                        </p>

                        {/* Per-signal chips */}
                        <div>
                          <p className="text-[10px] text-slate-500 mb-1.5 font-medium uppercase tracking-wider">Inputs</p>
                          <div className="flex flex-wrap gap-2">
                            {signals.map((s) => (
                              <div key={s.timeframe} className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 border text-xs ${
                                s.direction === 'Bullish' ? 'bg-emerald-950/40 border-emerald-800/50 text-emerald-400' :
                                s.direction === 'Bearish' ? 'bg-rose-950/40 border-rose-800/50 text-rose-400' :
                                                            'bg-amber-950/30 border-amber-800/40 text-amber-400'
                              }`}>
                                <span className="text-slate-300 font-mono font-bold">{s.timeframe}</span>
                                <span>{s.direction === 'Bullish' ? '▲' : s.direction === 'Bearish' ? '▼' : '—'}</span>
                                <span className="text-slate-400">{s.confidence.toFixed(0)}%</span>
                                <span className="text-slate-600 text-[10px]">Sharpe {s.sharpe_weight?.toFixed(2) ?? '?'}</span>
                              </div>
                            ))}
                          </div>
                        </div>

                      </div>
                    )}
                  </div>
                )}

                {/* Tiles */}
                {signals.length > 0 ? (
                  <TimeframeGrid signals={signals} />
                ) : (
                  <p className="text-xs text-rose-400 px-3 py-2 bg-rose-950/20 rounded border border-rose-900">
                    {techError?.message || 'Technical models are not trained for this symbol.'}
                  </p>
                )}
              </section>

              {/* Row 3 – Why moving + Conflicts */}
              <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="tour-why-moving">
                  <WhyMovingPanel
                    symbol={activeSymbol}
                    bullets={whyBullets}
                    disclaimer={DISCLAIMER}
                    techScore={techScore}
                    sentScore={sent30d}
                    macroScore={macroScore}
                    gasScore={gasScore}
                    mlOutput={null} /* Placeholder for future ML signals */
                    initialAiSummary={initialAiSummary}
                  />
                </div>
                <ConflictDetector
                  hasConflict={conflictData.hasConflict}
                  conflicts={conflictData.conflicts}
                  conflictSummary={conflictData.summary}
                />
              </section>

              {/* Row 4 – Quick links */}
              <section className="flex flex-wrap gap-4 pt-4 border-t border-slate-800/50">
                <Link href="/macro" className="text-sm text-sky-400 hover:text-sky-300 font-medium transition-colors">
                  View Full Macro Intel &rarr;
                </Link>
                <Link href="/news-sentiment" className="text-sm text-sky-400 hover:text-sky-300 font-medium transition-colors">
                  View Full Sentiment Intel &rarr;
                </Link>
              </section>

            </div>
          )}
        </div>
      </div>
    </div>
  );
}
