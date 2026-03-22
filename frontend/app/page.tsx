"use client";

import React, { useState, useMemo, useCallback } from "react";
import useSWR from "swr";
import Link from "next/link";
import { useSymbol } from "../lib/symbolContext";
import {
  fetchTechnicalLatest,
  fetchNewsSentiment,
  fetchMacroLatest,
  fetchGasSnapshot,
  fetchExplanationSummary,
  type GasSnapshotDto,
  type TechnicalSignalDto,
} from "../lib/api";
import { triggerTrainSymbol } from "../lib/api_bulk";
import { fetchLatestPrice } from "../lib/api_price";
import { useAuth } from "../components/AuthProvider";
import { useToast } from "../components/ToastProvider";
import MarketWeatherWidget from "../components/MarketWeatherWidget";
import RegimeWidget from "../components/RegimeWidget";
import TimeframeGrid from "../components/TimeframeGrid";
import WhyMovingPanel from "../components/WhyMovingPanel";
import ConflictDetector from "../components/ConflictDetector";
import { GuidedTour } from "../components/onboarding/GuidedTour";
import { WatchlistWidget } from "../components/WatchlistWidget";
import TickerDataPanel from "../components/TickerDataPanel";
import LLMInsightCard from "../components/LLMInsightCard";
import PriceTargetCard from "../components/PriceTargetCard";
import ScoreExplainPanel, {
  type ExplainPayload,
  type SubComponent,
} from "../components/ScoreExplainPanel";
import WhatChangedToday from "../components/WhatChangedToday";
import FreshnessIndicator from "../components/FreshnessIndicator";
import DataSourceStatus from "../components/DataSourceStatus";
import CrossAssetRow from "../components/CrossAssetRow";
import EarningsCalendarStrip from "../components/EarningsCalendarStrip";
import DailyMarketBrief from "../components/DailyMarketBrief";
import PriceTape from "../components/PriceTape";
import GradeBadge from "../components/GradeBadge";
import { useRecentSymbols } from "../hooks/useRecentSymbols";
import { fetchWatchlist } from "../lib/api";
import { fetchModelDetails, type ModelDetailsResponse } from "../lib/api_model_details";

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
      "📈 Technical models have not been trained for this symbol yet; technical signals are unavailable.",
    );
  }

  if (sent30d !== null) {
    const sentLabel =
      sent30d > 0.3 ? "strongly positive" :
        sent30d > 0.05 ? "mildly positive" :
          sent30d > -0.05 ? "neutral" :
            sent30d > -0.3 ? "mildly negative" : "strongly negative";
    bullets.push(
      `📰 News sentiment over the past 30 days is ${sentLabel} ` +
      `(score: ${sent30d >= 0 ? "+" : ""}${sent30d.toFixed(2)} on a −1 to +1 scale).`,
    );
  } else {
    bullets.push("📰 News sentiment data is not yet available for this symbol.");
  }

  const macroComment =
    macroScore >= 60 ? "This provides a supportive backdrop for equities." :
      macroScore < 40 ? "Macro conditions add headwinds to risk assets." :
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
    const sa = scores[a]; const sb = scores[b];
    if ((sa > 65 && sb < 35) || (sb > 65 && sa < 35)) {
      conflicts.push({
        layers: `${a} vs ${b}`,
        magnitude: `${Math.abs(sa - sb).toFixed(0)} points apart (${sa.toFixed(0)} vs ${sb.toFixed(0)})`,
        message: `${a} is ${directionLabel(sa).toLowerCase()} while ${b} is ${directionLabel(sb).toLowerCase()}. This divergence suggests elevated uncertainty — exercise extra caution.`,
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
        message: `Only ${dominant} of ${signals.length} timeframes agree on direction. Low cross-timeframe consensus increases signal uncertainty.`,
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

// ─── ML output builder ───────────────────────────────────────────────────────
function buildMlOutput(signals: TechnicalSignalDto[], techScore: number): string | null {
  if (signals.length === 0) return null;
  const bestSignal = [...signals].sort((a, b) => (b.sharpe_weight ?? 0) - (a.sharpe_weight ?? 0))[0];
  const bullish = signals.filter((s) => s.direction === "Bullish").length;
  const bearish = signals.filter((s) => s.direction === "Bearish").length;
  const parts: string[] = [
    `Technical consensus: ${techScore.toFixed(1)}/100 (${directionLabel(techScore)}).`,
    `${bullish}/${signals.length} timeframes bullish, ${bearish} bearish.`,
  ];
  if (bestSignal) {
    parts.push(
      `Strongest signal: ${bestSignal.timeframe} ${bestSignal.direction} ` +
      `(${bestSignal.confidence.toFixed(0)}% conf, Sharpe ${(bestSignal.sharpe_weight ?? 0).toFixed(2)}, ` +
      `model: ${bestSignal.model_used ?? "unknown"}).`,
    );
  }
  return parts.join(" ");
}

// ─── SHAP "What drove this?" panel ──────────────────────────────────────────────────────────────────────────────

/** Plain-English descriptions for the most common ML feature names */
const FEATURE_DESCRIPTIONS: Record<string, string> = {
  rsi_14:          "RSI — momentum oscillator. Below 30 = oversold (bullish potential), above 70 = overbought.",
  macd_hist:       "MACD histogram — difference between the signal line. Positive = bullish momentum building.",
  bb_pb:           "Bollinger Band %B — where price sits in the band. Near 0 = lower band, near 1 = upper band.",
  sma_cross_10_20: "10-period SMA vs 20-period SMA. Positive = short-term trend above medium-term.",
  atr_pct:         "ATR as % of price — current volatility level. Higher = larger expected swings.",
  volume_ratio:    "Volume vs 20-day average. Above 1 = unusual activity, often confirms price moves.",
  ret_1:           "Yesterday's return — recent price momentum (1 bar).",
  mom_10:          "10-period momentum — price change % over the last 10 bars.",
  mom_20:          "20-period momentum — price change % over the last 20 bars.",
  high_low_pct:    "Intraday range (high-low)/close — measures conviction vs indecision.",
  close_position:  "Where price closed in the day's range. Near 1 = strong close (bullish sign).",
  gap_pct:         "Overnight gap — how much the open differed from yesterday's close.",
  sma_slope_20:    "Slope of the 20-day moving average — rising/flat/falling trend.",
  ret_10_vs_ret_20:"Whether 10-day and 20-day momentum agree in direction.",
};

function ShapPanel({ modelData, activeTf, signals }: {
  modelData: ModelDetailsResponse | undefined;
  activeTf:  string;
  signals:   { timeframe: string; sharpe_weight?: number | null; direction: string }[];
}) {
  const [open, setOpen] = React.useState(false);

  // Pick best timeframe: prefer activeTf if trained, else highest-Sharpe available
  const bestTf = React.useMemo(() => {
    if (modelData?.timeframes?.[activeTf]) return activeTf;
    if (!signals.length) return "1d";
    const sorted = [...signals].sort((a, b) => (b.sharpe_weight ?? 0) - (a.sharpe_weight ?? 0));
    return sorted[0].timeframe;
  }, [modelData, activeTf, signals]);

  const detail = modelData?.timeframes?.[bestTf];
  const shap: Record<string, number> | null = (detail as any)?.shap_importance ?? null;
  const features = detail?.features_used ?? [];

  // Build top-5 SHAP bars (or feature list if no SHAP)
  const rows = React.useMemo(() => {
    if (!features.length) return [];
    if (shap) {
      return [...features]
        .sort((a, b) => (shap[b.name] ?? 0) - (shap[a.name] ?? 0))
        .slice(0, 5)
        .map((f) => ({
          name:        f.name,
          value:       shap[f.name] ?? 0,
          description: FEATURE_DESCRIPTIONS[f.name] ?? f.description,
        }));
    }
    // No SHAP yet — show first 5 features with placeholder
    return features.slice(0, 5).map((f) => ({
      name:        f.name,
      value:       null as number | null,
      description: FEATURE_DESCRIPTIONS[f.name] ?? f.description,
    }));
  }, [features, shap]);

  if (!detail || rows.length === 0) return null;

  const maxVal = shap ? Math.max(...rows.map((r) => r.value as number), 0.001) : 1;
  const hasSHAP = shap !== null;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-slate-800/40 transition-colors group"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm">🔬</span>
          <span className="text-xs font-semibold text-slate-400 group-hover:text-slate-200 transition-colors">
            What drove this signal?
          </span>
          <span className="text-[10px] text-slate-600 font-mono">{bestTf}</span>
          {!hasSHAP && (
            <span className="text-[9px] text-amber-500 bg-amber-950/30 border border-amber-800/40 rounded-full px-1.5 py-0.5">No SHAP yet</span>
          )}
        </div>
        <svg
          className={`h-3.5 w-3.5 text-slate-600 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="border-t border-slate-800 px-4 py-4 space-y-3">
          <p className="text-[10px] text-slate-500 leading-relaxed">
            {hasSHAP
              ? `Top 5 features by mean |SHAP value| — how much each shifted the ${bestTf} model's prediction on validation data.`
              : `Features the ${bestTf} model was trained on. SHAP importance will appear after the next retrain with a tree-based winner.`
            }
          </p>

          <div className="space-y-3">
            {rows.map((row) => {
              const pct = hasSHAP && row.value != null
                ? Math.round((row.value / maxVal) * 100)
                : 0;
              const barColor =
                pct >= 70 ? "bg-violet-500" :
                pct >= 40 ? "bg-sky-500" :
                "bg-slate-600";

              return (
                <div key={row.name} className="space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[11px] font-mono font-bold text-sky-400 truncate">{row.name}</span>
                    {hasSHAP && row.value != null && (
                      <span className="text-[10px] font-mono text-violet-400 tabular-nums flex-shrink-0">
                        {row.value.toFixed(4)}
                      </span>
                    )}
                  </div>
                  {hasSHAP && (
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-700 ${barColor}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-[9px] text-slate-600 tabular-nums w-7 text-right">{pct}%</span>
                    </div>
                  )}
                  <p className="text-[10px] text-slate-500 leading-relaxed">{row.description}</p>
                </div>
              );
            })}
          </div>

          <p className="text-[9px] text-slate-700 border-t border-slate-800/50 pt-2">
            SHAP = SHapley Additive exPlanations. Higher value = stronger influence on this prediction.
            Source: {bestTf} model · {detail.winner_model} winner.
          </p>
        </div>
      )}
    </div>
  );
}

// ─── "Not Trained" empty state ───────────────────────────────────────────────
function TrainNowEmptyState({
  symbol,
  onTrainStarted,
}: {
  symbol: string;
  onTrainStarted: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleTrain = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await triggerTrainSymbol(symbol);
      setDone(true);
      onTrainStarted();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [symbol, onTrainStarted]);

  if (done) {
    return (
      <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-blue-950/20 border border-blue-800/40 text-sm text-blue-300">
        <svg className="animate-spin h-4 w-4 text-blue-400 flex-shrink-0" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        Training ML models for {symbol}… This takes 60–120 seconds. The page will refresh automatically.
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center gap-4 py-6 px-4 rounded-xl bg-slate-800/30 border border-slate-700/50 text-center">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-800 border border-slate-700 text-xl">🧠</div>
      <div>
        <p className="text-sm font-semibold text-slate-200">No ML prediction yet for {symbol}</p>
        <p className="text-xs text-slate-500 mt-0.5">Technical consensus requires a trained model.</p>
      </div>
      <button
        onClick={handleTrain}
        disabled={loading}
        className="flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 text-sm font-semibold text-white transition-colors"
      >
        {loading ? (
          <>
            <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Starting…
          </>
        ) : (
          <> ▶ Train Now</>
        )}
      </button>
      {error && <p className="text-xs text-red-400">{error}</p>}
      <p className="text-[10px] text-slate-600 max-w-xs">
        Training uses historical OHLCV data and runs locally. Sharpe-weighted ML models across 5 timeframes. Takes 60–120 seconds.
      </p>
    </div>
  );
}

// ─── Explain payload builders ─────────────────────────────────────────────────

function buildGasPayload(gasScore: number, techScore: number, sent30d: number | null, macroScore: number, macroLabel: string): ExplainPayload {
  const sentScore0100 = ((sent30d ?? 0) + 1) / 2 * 100;
  const sentRaw = sent30d !== null ? `${sent30d >= 0 ? "+" : ""}${sent30d.toFixed(2)}` : "N/A";
  const sc = (s: number): SubComponent["color"] =>
    s >= 65 ? "emerald" : s >= 55 ? "teal" : s >= 45 ? "amber" : s >= 35 ? "orange" : "rose";
  return {
    target: "gas", title: "Global Alignment Score (GAS)", score: gasScore, scoreLabel: "/ 100",
    summary: `The GAS blends Technical (40%), Sentiment (30%), and Macro (30%). Above 60 = bullish alignment; below 40 = bearish pressure.`,
    subComponents: [
      { label: "Technical Score", value: techScore, rawLabel: `${techScore.toFixed(0)} / 100`, color: sc(techScore), description: `ML-driven consensus. 40% of GAS.` },
      { label: "Sentiment Score", value: sentScore0100, rawLabel: sentRaw, color: sc(sentScore0100), description: `30-day news sentiment. 30% of GAS.` },
      { label: "Macro Score", value: macroScore, rawLabel: `${macroScore.toFixed(0)} / 100 (${macroLabel})`, color: sc(macroScore), description: `FRED macro composite. 30% of GAS.` },
    ],
    methodology: `GAS = (Technical × 0.40) + (Sentiment × 0.30) + (Macro × 0.30). Pre-computed every 15 minutes.`,
  };
}

function buildTechnicalPayload(techScore: number, signals: TechnicalSignalDto[]): ExplainPayload {
  const bullish = signals.filter((s) => s.direction === "Bullish").length;
  const bearish = signals.filter((s) => s.direction === "Bearish").length;
  const neutral = signals.length - bullish - bearish;
  const tfSubs: SubComponent[] = signals.map((s) => ({
    label: s.timeframe, value: s.direction === "Bullish" ? 75 : s.direction === "Bearish" ? 25 : 50,
    rawLabel: s.direction,
    color: (s.direction === "Bullish" ? "emerald" : s.direction === "Bearish" ? "rose" : "amber") as SubComponent["color"],
    description: `${s.timeframe} timeframe ML model output.`,
  }));
  return {
    target: "technical", title: "Technical Confidence Score", score: techScore, scoreLabel: "/ 100", weight: "40% of GAS",
    summary: `${bullish} of ${signals.length} bullish, ${bearish} bearish, ${neutral} neutral.`,
    subComponents: tfSubs.length > 0 ? tfSubs : [{ label: "No signals", value: 50, rawLabel: "N/A", color: "slate", description: "No models trained yet." }],
    methodology: `scikit-learn classifiers on OHLCV features (RSI, MACD, BBands, etc.). Sharpe-weighted voting.`,
  };
}

function buildMacroPayload(macroScore: number, macroLabel: string, macroData: any, vixLevel: number | null): ExplainPayload {
  const sc = (s: number): SubComponent["color"] =>
    s >= 65 ? "emerald" : s >= 55 ? "teal" : s >= 45 ? "amber" : s >= 35 ? "orange" : "rose";
  const vixScore = vixLevel != null ? vixLevel < 15 ? 75 : vixLevel <= 25 ? 50 : 25 : 50;
  const subs: SubComponent[] = [
    { label: "Macro Composite", value: macroScore, rawLabel: `${macroScore.toFixed(0)} / 100 (${macroLabel})`, color: sc(macroScore), description: "FRED composite. 30% of GAS." },
    { label: "VIX", value: vixScore, rawLabel: vixLevel != null ? vixLevel.toFixed(2) : "N/A", color: (vixLevel == null ? "slate" : vixLevel < 15 ? "sky" : vixLevel <= 25 ? "amber" : "rose") as SubComponent["color"], description: "<15 calm, 15–25 normal, >25 fear." },
  ];
  const yc = macroData?.data?.yield_curve;
  if (yc) {
    const ycScore = yc.shape === "Normal" ? 65 : yc.shape === "Inverted" ? 30 : 50;
    subs.push({ label: "Yield Curve", value: ycScore, rawLabel: yc.shape ?? "Unknown", color: sc(ycScore), description: `${yc.shape}. Inverted → recession signal.` });
  }
  return {
    target: "macro", title: "Macro Score", score: macroScore, scoreLabel: `/ 100 (${macroLabel})`, weight: "30% of GAS",
    summary: `Macro: '${macroLabel}'. Aggregates FRED indicators.`,
    subComponents: subs,
    methodology: `FRED: Yield Curve, VIX, Unemployment, CPI YoY, ISM PMI. Each normalised 0–100. Refreshes every 5 minutes.`,
  };
}

function buildVolatilityPayload(vixLevel: number | null): ExplainPayload {
  const vixScore = vixLevel != null ? vixLevel < 15 ? 80 : vixLevel <= 25 ? 50 : 20 : 50;
  return {
    target: "macro", title: "Volatility Regime",
    score: vixScore, scoreLabel: vixLevel != null ? `VIX ${vixLevel.toFixed(1)}` : "VIX N/A",
    summary: `Derived from CBOE VIX. Market fear / option pricing pressure.`,
    subComponents: [{
      label: "VIX Level", value: vixScore, rawLabel: vixLevel != null ? vixLevel.toFixed(2) : "N/A",
      color: vixLevel == null ? "slate" : vixLevel < 15 ? "sky" : vixLevel <= 25 ? "amber" : "rose",
      description: vixLevel == null ? "VIX unavailable." : vixLevel < 15 ? "Below 15 — calm." : vixLevel <= 25 ? "15–25 — normal." : "Above 25 — elevated fear.",
    }],
    methodology: `VIX = 30-day S&P 500 implied volatility. Source: FRED (VIXCLS).`,
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

// ─── Sprint 27: Price Chart Widget (TradingView embed) ─────────────────────

function PriceChartWidget({ symbol }: { symbol: string }) {
  const [open, setOpen] = React.useState(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem("fin-eye-chart-open") !== "false";
  });

  const toggle = () => {
    setOpen((v) => {
      const next = !v;
      try { localStorage.setItem("fin-eye-chart-open", String(next)); } catch {}
      return next;
    });
  };

  // Map yfinance symbols to TradingView format
  const tvSymbol = React.useMemo(() => {
    const s = symbol.toUpperCase();
    if (s.endsWith("-USD"))   return `BINANCE:${s.replace("-", "")}`;  // BTC-USD → BINANCE:BTCUSD
    if (s.endsWith("=F"))     return `NYMEX:${s.replace("=F", "")}`;   // CL=F → NYMEX:CL
    if (s.endsWith("=X"))     return `FX:${s.replace("=X", "")}`;      // EURUSD=X → FX:EURUSD
    if (s.startsWith("^"))    return `TVC:${s.slice(1)}`;             // ^GSPC → TVC:GSPC
    return `NASDAQ:${s}`;                                              // default US equity
  }, [symbol]);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
      <button
        onClick={toggle}
        className="w-full flex items-center justify-between px-5 py-3 hover:bg-slate-800/20 transition-colors"
      >
        <div className="flex items-center gap-2">
          <svg className="h-4 w-4 text-sky-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
          </svg>
          <span className="text-sm font-semibold text-slate-200">Price Chart</span>
          <span className="text-xs text-slate-500 font-mono">{symbol}</span>
          <span className="text-[10px] text-slate-600 bg-slate-800/60 border border-slate-700/50 rounded px-1.5 py-0.5">TradingView</span>
        </div>
        <svg
          className={`h-4 w-4 text-slate-500 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="border-t border-slate-800">
          <div className="h-[420px] w-full" key={symbol}>
            <iframe
              src={`https://www.tradingview.com/widgetembed/?frameElementId=tv_chart&symbol=${encodeURIComponent(tvSymbol)}&interval=D&theme=dark&style=1&locale=en&enable_publishing=false&hide_top_toolbar=0&hide_legend=0&save_image=false&calendar=false&hide_volume=false&support_host=https://www.tradingview.com`}
              style={{ width: "100%", height: "100%", border: "none" }}
              allowFullScreen
              title={`${symbol} price chart`}
            />
          </div>
          <p className="px-4 py-2 text-[10px] text-slate-700">
            Chart powered by TradingView. Prices may be delayed. Educational use only.
          </p>
        </div>
      )}
    </div>
  );
}

// ─── Page Component ──────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { symbol: activeSymbol, setSymbol: setActiveSymbol, seedDefaultOnce } = useSymbol();
  const { user } = useAuth();

  // Apply user's default_symbol on first load if no localStorage symbol is set
  React.useEffect(() => {
    if (user?.default_symbol) {
      seedDefaultOnce(user.default_symbol);
    }
  }, [user?.default_symbol, seedDefaultOnce]);
  const { toast } = useToast();
  const isAdmin = user?.is_admin === true;

  const [techExplainOpen, setTechExplainOpen] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem("fin-eye-tech-explain-open") === "true";
  });
  const toggleTechExplain = useCallback(() => {
    setTechExplainOpen((v) => {
      const next = !v;
      localStorage.setItem("fin-eye-tech-explain-open", String(next));
      return next;
    });
  }, []);

  const [explainPayload, setExplainPayload] = useState<ExplainPayload | null>(null);
  const closeExplain = useCallback(() => setExplainPayload(null), []);

  // Track previous GAS score to detect meaningful changes
  const prevGasScoreRef = React.useRef<number | null>(null);
  const [gasChangeBanner, setGasChangeBanner] = React.useState<{
    delta: number;
    prev: number;
    curr: number;
    symbol: string;
  } | null>(null);

  // Sprint 26 — Track previous regime to detect flips
  const prevRegimeRef = React.useRef<string | null>(null);
  const [regimeBanner, setRegimeBanner] = React.useState<{
    prev: string;
    curr: string;
    symbol: string;
  } | null>(null);

  const { data: gasSnapshot, error: gasError, isLoading: gasLoading, isValidating: gasValidating } = useSWR(
    `gas-snapshot-${activeSymbol}`,
    () => fetchGasSnapshot(activeSymbol),
    {
      refreshInterval: 60_000,
      shouldRetryOnError: false,
      keepPreviousData: true,
      onSuccess: (data) => {
        const curr = data?.gas_score;
        const prev = prevGasScoreRef.current;
        if (curr != null && prev != null && Math.abs(curr - prev) >= 5) {
          setGasChangeBanner({ delta: curr - prev, prev, curr, symbol: activeSymbol });
        }
        if (curr != null) prevGasScoreRef.current = curr;

        // Sprint 26 — regime flip detection
        const currRegime = data?.regime;
        const prevRegime = prevRegimeRef.current;
        if (currRegime && prevRegime && currRegime !== prevRegime) {
          setRegimeBanner({ prev: prevRegime, curr: currRegime, symbol: activeSymbol });
        }
        if (currRegime) prevRegimeRef.current = currRegime;
      },
    },
  );

  // Reset refs and banners when symbol changes
  React.useEffect(() => {
    prevGasScoreRef.current = null;
    prevRegimeRef.current   = null;
    setGasChangeBanner(null);
    setRegimeBanner(null);
  }, [activeSymbol]);

  const { data: techData, error: techError, mutate: mutateTech } = useSWR(
    `tech-${activeSymbol}`,
    () => fetchTechnicalLatest(activeSymbol),
    { refreshInterval: 120_000, shouldRetryOnError: false, keepPreviousData: true },
  );

  const signals = techData?.signals ?? [];

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

  // Live price — refreshes every 5 minutes; used by LLM insight card for price targets.
  // Uses keepPreviousData so the card never flickers when the symbol changes.
  const { data: priceData } = useSWR(
    `price-${activeSymbol}`,
    () => fetchLatestPrice(activeSymbol),
    { refreshInterval: 300_000, shouldRetryOnError: false, keepPreviousData: true },
  );

  const { data: watchlistData } = useSWR(
    "watchlist",
    fetchWatchlist,
    { refreshInterval: 5 * 60_000, shouldRetryOnError: false },
  );
  const watchlistSymbols = (watchlistData ?? []).map((w) => w.symbol);
  const { recent: recentSymbols } = useRecentSymbols(activeSymbol);

  // Model details for SHAP panel — Sprint 24
  const { data: modelData } = useSWR(
    signals.length > 0 ? `model-details-shap-${activeSymbol}` : null,
    () => fetchModelDetails(activeSymbol),
    { revalidateOnFocus: false, shouldRetryOnError: false, keepPreviousData: true },
  );

  // Best active timeframe for SHAP (1d default, or highest-Sharpe signal)
  const shapActiveTf = React.useMemo(() => {
    if (!signals.length) return "1d";
    const sorted = [...signals].sort((a, b) => (b.sharpe_weight ?? 0) - (a.sharpe_weight ?? 0));
    return sorted[0].timeframe;
  }, [signals]);

  void techError; // used implicitly via keepPreviousData

  const gasScore: number = gasSnapshot?.gas_score
    ?? (() => {
      const ts = techData?.technical_confidence_score ?? 50;
      const sm = ((sentData?.sentiment_30d ?? 0) + 1) / 2 * 100;
      const ms = macroData?.macro_score?.score ?? 50;
      return ts * 0.4 + sm * 0.3 + ms * 0.3;
    })();

  const regimeFromSnapshot = gasSnapshot?.regime;
  const techScore = gasSnapshot?.component_scores?.technical ?? techData?.technical_confidence_score ?? 50;
  const sent30d = sentData?.sentiment_30d ?? null;
  const macroScore = gasSnapshot?.component_scores?.macro ?? macroData?.macro_score?.score ?? 50;
  const macroLabel = macroData?.macro_score?.label ?? "Neutral";
  const vixLevel = macroData?.data?.vix?.value ?? null;
  const yieldSpread = macroData?.data?.yield_spread_10y_2y?.value ?? null;
  const isLoading = gasLoading && !gasSnapshot && !gasError;
  const currentPrice = priceData?.price ?? 0;

  const mlOutput = useMemo(() => buildMlOutput(signals, techScore), [signals, techScore]);

  const explainParamsStr = !isLoading ? JSON.stringify({
    tech_score: techScore, sent_30d: sent30d, macro_score: macroScore,
    macro_label: macroLabel, gas_score: gasScore, tech_signals: JSON.stringify(signals),
  }) : null;

  const { data: explanationData } = useSWR(
    explainParamsStr ? [`explanation-${activeSymbol}`, explainParamsStr] : null,
    ([, paramsStr]) => {
      const p = JSON.parse(paramsStr as string);
      return fetchExplanationSummary(activeSymbol, p as any);
    },
    { refreshInterval: 60_000, shouldRetryOnError: false, keepPreviousData: true },
  );

  const fallbackWhyBullets = useMemo(
    () => buildWhyBullets(techScore, signals, sent30d, macroScore, macroLabel),
    [techScore, signals, sent30d, macroScore, macroLabel],
  );
  const sentScore0100 = ((sent30d ?? 0) + 1) / 2 * 100;
  const fallbackConflictData = useMemo(
    () => detectConflicts(techScore, sentScore0100, macroScore, signals),
    [techScore, sentScore0100, macroScore, signals],
  );
  const whyBullets = explanationData?.why_moving ?? fallbackWhyBullets;
  const conflictData = explanationData
    ? { hasConflict: explanationData.has_conflict, conflicts: explanationData.conflicts, summary: explanationData.conflict_summary }
    : fallbackConflictData;
  const initialAiSummary = explanationData?.ai_summary ?? null;

  const handleTrainStarted = useCallback(() => {
    toast({ title: "Training started", description: "ML models training in background — signals will appear in ~90 seconds.", type: "info", duration: 6000 });
    const intervalId = setInterval(async () => {
      const fresh = await mutateTech();
      if (fresh?.signals && fresh.signals.length > 0) {
        clearInterval(intervalId);
        toast({ title: "Training complete", description: `Signals for ${activeSymbol} are ready.`, type: "success" });
      }
    }, 5000);
    setTimeout(() => clearInterval(intervalId), 180_000);
  }, [mutateTech, toast, activeSymbol]);

  const openGasExplain = useCallback(
    () => setExplainPayload(buildGasPayload(gasScore, techScore, sent30d, macroScore, macroLabel)),
    [gasScore, techScore, sent30d, macroScore, macroLabel],
  );
  const openTechnicalExplain = useCallback(
    () => setExplainPayload(buildTechnicalPayload(techScore, signals)),
    [techScore, signals],
  );
  const openVolatilityExplain = useCallback(
    () => setExplainPayload(buildVolatilityPayload(vixLevel)),
    [vixLevel],
  );
  const openMacroExplain = useCallback(
    () => setExplainPayload(buildMacroPayload(macroScore, macroLabel, macroData, vixLevel)),
    [macroScore, macroLabel, macroData, vixLevel],
  );
  void openMacroExplain;

  return (
    <div className="space-y-6">
      <GuidedTour />
      <ScoreExplainPanel payload={explainPayload} onClose={closeExplain} />

      <div className="flex gap-6">
        <aside className="hidden xl:flex xl:flex-col xl:w-56 flex-shrink-0 space-y-4">
          <WatchlistWidget activeSymbol={activeSymbol} onSelectSymbol={setActiveSymbol} />
          <WhatChangedToday
            symbols={watchlistSymbols}
            onSelectSymbol={setActiveSymbol}
            activeSymbol={activeSymbol}
          />
          {watchlistSymbols.length > 0 && (
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-3 space-y-2">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600 px-1">
                Upcoming Earnings
              </p>
              <EarningsCalendarStrip symbols={watchlistSymbols} />
            </div>
          )}
        </aside>

        <div className="min-w-0 flex-1 space-y-6">
          {/* Price Tape -- Sprint 20 */}
          <PriceTape activeSymbol={activeSymbol} onSelectSymbol={setActiveSymbol} />

          <header className="flex flex-col gap-1 border-b border-slate-800 pb-5">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-3xl font-black tracking-tight text-slate-100">{activeSymbol} Intelligence</h1>
              <GradeBadge
                grade={gasSnapshot?.signal_grade}
                score={gasSnapshot?.signal_grade_score}
                tradeable={gasSnapshot?.signal_tradeable}
                size="md"
                showTradeable
                clickable
                symbol={activeSymbol}
              />
            </div>
            <p className="text-sm text-slate-400">Real-time GAS, Regime, and Multi-Timeframe layers.</p>
            <div className="mt-0.5 flex flex-wrap items-center gap-4">
              <SnapshotMeta snapshot={gasSnapshot} />
              {macroData && (
                <FreshnessIndicator
                  updatedAt={macroData?.fetched_at as string | undefined}
                  label="Macro"
                  freshMinutes={60}
                  agingMinutes={120}
                />
              )}
              {sentData && (
                <FreshnessIndicator
                  updatedAt={sentData.fetched_at ?? undefined}
                  label="Sentiment"
                  freshMinutes={60}
                  agingMinutes={240}
                />
              )}
            </div>
          </header>

          {/* Recent symbols quick-switch — Sprint 21 */}
          {recentSymbols.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[10px] text-slate-600 uppercase tracking-wider font-semibold flex-shrink-0">
                Recent
              </span>
              {recentSymbols.map((sym) => (
                <button
                  key={sym}
                  onClick={() => setActiveSymbol(sym)}
                  className="text-[11px] font-mono font-bold px-2.5 py-1 rounded-lg border border-slate-700 bg-slate-800/60 text-slate-400 hover:text-slate-100 hover:border-slate-600 hover:bg-slate-800 transition-all"
                >
                  {sym}
                </button>
              ))}
            </div>
          )}

          <div className="xl:hidden space-y-4">
            <WatchlistWidget activeSymbol={activeSymbol} onSelectSymbol={setActiveSymbol} />
            {watchlistSymbols.length > 0 && (
              <WhatChangedToday
                symbols={watchlistSymbols}
                onSelectSymbol={setActiveSymbol}
                activeSymbol={activeSymbol}
              />
            )}
            {watchlistSymbols.length > 0 && (
              <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-3 space-y-2">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600 px-1">Upcoming Earnings</p>
                <EarningsCalendarStrip symbols={watchlistSymbols} />
              </div>
            )}
          </div>

          {isLoading ? (
            <div className="py-20 text-center animate-pulse text-slate-500">
              Gathering market intelligence for {activeSymbol}…
            </div>
          ) : (
            <div className="space-y-6">

              {/* GAS score change explainer banner — Sprint 22 */}
              {gasChangeBanner && gasChangeBanner.symbol === activeSymbol && (
                <div className={`flex items-start gap-3 rounded-xl border px-4 py-3 ${
                  gasChangeBanner.delta > 0
                    ? "bg-emerald-950/25 border-emerald-800/40"
                    : "bg-rose-950/25 border-rose-800/40"
                }`}>
                  <span className="text-lg flex-shrink-0">
                    {gasChangeBanner.delta > 0 ? "📈" : "📉"}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-bold ${
                      gasChangeBanner.delta > 0 ? "text-emerald-300" : "text-rose-300"
                    }`}>
                      GAS {gasChangeBanner.delta > 0 ? "↑" : "↓"}{" "}
                      {Math.abs(gasChangeBanner.delta).toFixed(0)} pts
                      {" "}—{" "}
                      {gasChangeBanner.prev.toFixed(0)} → {gasChangeBanner.curr.toFixed(0)}
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {gasChangeBanner.delta > 0
                        ? gasChangeBanner.delta >= 15
                          ? "Significant improvement — check what shifted in the component scores below."
                          : "Moderate improvement since last refresh — one or more layers strengthened."
                        : gasChangeBanner.delta <= -15
                          ? "Significant decline — review the Conflict Detector and macro layer for drivers."
                          : "Moderate decline since last refresh — one or more layers weakened."}
                    </p>
                  </div>
                  <button
                    onClick={() => setGasChangeBanner(null)}
                    className="text-slate-600 hover:text-slate-400 transition-colors flex-shrink-0 text-lg leading-none"
                    aria-label="Dismiss"
                  >
                    ×
                  </button>
                </div>
              )}

              {/* Sprint 26 — Regime change notification banner */}
              {regimeBanner && regimeBanner.symbol === activeSymbol && (() => {
                const toRiskOn   = regimeBanner.curr === "Risk-On";
                const toRiskOff  = regimeBanner.curr === "Risk-Off";
                const borderCls  = toRiskOn  ? "border-emerald-800/40 bg-emerald-950/20"
                                 : toRiskOff ? "border-rose-800/40 bg-rose-950/20"
                                 : "border-amber-800/40 bg-amber-950/20";
                const textCls    = toRiskOn  ? "text-emerald-300"
                                 : toRiskOff ? "text-rose-300"
                                 : "text-amber-300";
                const icon       = toRiskOn ? "🟢" : toRiskOff ? "🔴" : "🟡";
                const implication = toRiskOn
                  ? "Conditions now favour risk assets — momentum strategies may perform better."
                  : toRiskOff
                  ? "Conditions now favour defensive positioning — reduce exposure and tighten stops."
                  : "Mixed signals — neither risk-on nor risk-off is clearly dominant.";
                return (
                  <div className={`flex items-start gap-3 rounded-xl border px-4 py-3 ${borderCls}`}>
                    <span className="text-lg flex-shrink-0">{icon}</span>
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm font-bold ${textCls}`}>
                        Regime flipped: {regimeBanner.prev} → {regimeBanner.curr}
                      </p>
                      <p className="text-xs text-slate-400 mt-0.5">{implication}</p>
                    </div>
                    <button
                      onClick={() => setRegimeBanner(null)}
                      className="text-slate-600 hover:text-slate-400 transition-colors flex-shrink-0 text-lg leading-none"
                      aria-label="Dismiss"
                    >×</button>
                  </div>
                );
              })()}

              {/* Sprint 32 — Graceful degradation banners */}
              {gasError && (
                <DataSourceStatus
                  source="GAS Engine"
                  error={gasError}
                  description="Signal grades and GAS scores are temporarily unavailable. Showing last cached values where possible."
                />
              )}
              {sentData === undefined && !isLoading && (
                <DataSourceStatus
                  source="Sentiment (Finnhub)"
                  error={new Error("No sentiment data returned")}
                  description="News sentiment is temporarily unavailable — the GAS sentiment layer is using a neutral fallback (50)."
                />
              )}
              {macroData === undefined && !isLoading && (
                <DataSourceStatus
                  source="Macro (FRED)"
                  error={new Error("No macro data returned")}
                  description="FRED macro indicators are unavailable — the GAS macro layer is using a neutral fallback (50)."
                />
              )}

              {/* Daily Market Brief */}
              {macroScore > 0 && (
                <DailyMarketBrief
                  macroScore={macroScore}
                  macroLabel={macroLabel}
                  regime={regimeFromSnapshot ?? null}
                  sentimentScore={sent30d}
                  gasScore={gasScore}
                />
              )}

              {/* Cross-asset pulse row */}
              <section>
                <p className="text-[10px] text-slate-600 uppercase tracking-wider font-medium mb-2">Market Pulse</p>
                <CrossAssetRow
                  onSelectSymbol={setActiveSymbol}
                  activeSymbol={activeSymbol}
                />
              </section>

              {/* Row 1 – GAS + Regime */}
              <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="tour-gas-score">
                  <MarketWeatherWidget
                    gasScore={gasScore}
                    symbol={activeSymbol}
                    onExplain={openGasExplain}
                    isRefreshing={gasValidating && !!gasSnapshot}
                  />
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

              {/* Row 2 – Technical Consensus */}
              <section className="tour-timeframes p-5 rounded-2xl border border-slate-800 bg-slate-900/40 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div>
                    <h3 className="text-base font-bold text-slate-100">Technical Consensus</h3>
                    <p className="text-xs text-slate-500 mt-0.5">Sharpe-weighted ML signal across all trained timeframes</p>
                  </div>
                  <div className="flex items-baseline gap-2 flex-shrink-0">
                    <span className={`text-4xl font-black tabular-nums ${techScore >= 60 ? "text-emerald-400" : techScore >= 40 ? "text-amber-400" : "text-rose-400"
                      }`}>{techScore.toFixed(1)}</span>
                    <span className="text-slate-500 text-base">/ 100</span>
                    {currentPrice > 0 && (
                      <span className="ml-2 text-xs text-slate-500 font-mono tabular-nums">
                        ${currentPrice.toFixed(2)}
                      </span>
                    )}
                    <span className={`ml-1 text-xs font-bold px-2 py-0.5 rounded-full border ${techScore >= 60 ? "text-emerald-400 bg-emerald-950/40 border-emerald-800/50" :
                      techScore >= 40 ? "text-amber-400 bg-amber-950/40 border-amber-800/50" :
                        "text-rose-400 bg-rose-950/40 border-rose-800/50"
                      }`}>
                      {techScore >= 80 ? "Strong Bullish" : techScore >= 60 ? "Bullish Lean" :
                        techScore >= 40 ? "Mixed / Neutral" : techScore >= 20 ? "Bearish Lean" : "Strong Bearish"}
                    </span>
                  </div>
                </div>

                {signals.length > 0 && (
                  <div>
                    <button
                      onClick={toggleTechExplain}
                      className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors group"
                    >
                      <svg className={`h-3.5 w-3.5 transition-transform duration-200 ${techExplainOpen ? "rotate-90" : "rotate-0"}`}
                        fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                      </svg>
                      <span className="group-hover:underline">
                        {techExplainOpen ? "Hide explanation" : "How is this score calculated?"}
                      </span>
                    </button>

                    {techExplainOpen && (
                      <div className="mt-3 rounded-xl bg-slate-800/50 border border-slate-700/60 px-4 py-3 space-y-3">
                        <div className="flex items-center gap-3">
                          <span className="text-[10px] text-slate-600 w-12 flex-shrink-0">0 Bear</span>
                          <div className="relative flex-1 h-2.5 rounded-full bg-slate-700 overflow-hidden">
                            <div className={`absolute inset-y-0 left-0 rounded-full transition-all duration-700 ${techScore >= 60 ? "bg-emerald-500" : techScore >= 40 ? "bg-amber-500" : "bg-rose-500"
                              }`} style={{ width: `${techScore}%` }} />
                            <div className="absolute inset-y-0 left-1/2 w-px bg-slate-400/50" />
                          </div>
                          <span className="text-[10px] text-slate-600 w-14 flex-shrink-0 text-right">100 Bull</span>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                          <div className="rounded-lg bg-slate-900/60 border border-slate-700/50 px-3 py-2">
                            <p className="text-slate-500 mb-0.5">Scale</p>
                            <p className="text-slate-200 font-semibold">0 &ndash; 100</p>
                            <p className="text-slate-500 text-[10px] mt-0.5">50 = perfectly neutral</p>
                          </div>
                          <div className="rounded-lg bg-slate-900/60 border border-slate-700/50 px-3 py-2">
                            <p className="text-slate-500 mb-0.5">Score {techScore.toFixed(1)}</p>
                            <p className={`font-semibold ${techScore >= 60 ? "text-emerald-400" : techScore >= 40 ? "text-amber-400" : "text-rose-400"}`}>
                              {techScore < 40 ? `${(50 - techScore).toFixed(0)} pts below neutral` :
                                techScore > 60 ? `${(techScore - 50).toFixed(0)} pts above neutral` : "Near neutral (50)"}
                            </p>
                            <p className="text-slate-500 text-[10px] mt-0.5">vs midpoint of 50</p>
                          </div>
                          <div className="rounded-lg bg-slate-900/60 border border-slate-700/50 px-3 py-2">
                            <p className="text-slate-500 mb-0.5">Method</p>
                            <p className="text-slate-200 font-semibold">Sharpe-weighted avg</p>
                            <p className="text-slate-500 text-[10px] mt-0.5">better models count more</p>
                          </div>
                        </div>
                        <p className="text-[11px] text-slate-500 leading-relaxed">
                          Each timeframe outputs −1 (bearish) to +1 (bullish), weighted by{" "}
                          <span className="text-sky-400 font-medium">Sharpe Ratio</span>, mapped to 0–100.
                        </p>
                        <div>
                          <p className="text-[10px] text-slate-500 mb-1.5 font-medium uppercase tracking-wider">Inputs</p>
                          <div className="flex flex-wrap gap-2">
                            {signals.map((s) => (
                              <div key={s.timeframe} className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 border text-xs ${s.direction === "Bullish" ? "bg-emerald-950/40 border-emerald-800/50 text-emerald-400" :
                                s.direction === "Bearish" ? "bg-rose-950/40 border-rose-800/50 text-rose-400" :
                                  "bg-amber-950/30 border-amber-800/40 text-amber-400"
                                }`}>
                                <span className="text-slate-300 font-mono font-bold">{s.timeframe}</span>
                                <span>{s.direction === "Bullish" ? "▲" : s.direction === "Bearish" ? "▼" : "—"}</span>
                                <span className="text-slate-400">{s.confidence.toFixed(0)}%</span>
                                <span className="text-slate-600 text-[10px]">Sharpe {s.sharpe_weight?.toFixed(2) ?? "?"}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {signals.length > 0 ? (
                  <>
                    {/* Sprint 28: Multi-timeframe agreement banner */}
                    {signals.length > 1 && (() => {
                      const b_ = signals.filter((s) => s.direction === "Bullish").length;
                      const be_ = signals.filter((s) => s.direction === "Bearish").length;
                      const t_ = signals.length;
                      const dom_ = Math.max(b_, be_);
                      const agr_ = dom_ / t_;
                      const dir_ = b_ > be_ ? "Bullish" : be_ > b_ ? "Bearish" : "Mixed";
                      const cls_ = (dir_ !== "Mixed" && agr_ >= 0.8)
                        ? (dir_ === "Bullish" ? "border-emerald-800/40 bg-emerald-950/15 text-emerald-300" : "border-rose-800/40 bg-rose-950/15 text-rose-300")
                        : (dir_ !== "Mixed" && agr_ >= 0.6)
                        ? (dir_ === "Bullish" ? "border-emerald-900/40 bg-emerald-950/10 text-emerald-400" : "border-rose-900/40 bg-rose-950/10 text-rose-400")
                        : "border-amber-800/40 bg-amber-950/15 text-amber-300";
                      const ico_ = (dir_ !== "Mixed" && agr_ >= 0.6)
                        ? (dir_ === "Bullish" ? "\u{1F7E2}" : "\u{1F534}")
                        : "\u{1F7E1}";
                      const msg_ = dir_ === "Mixed"
                        ? "Timeframes are split — no clear direction"
                        : agr_ >= 0.8 ? `${dom_}/${t_} timeframes agree: ${dir_}`
                        : agr_ >= 0.6 ? `${dom_}/${t_} timeframes lean ${dir_}`
                        : `${dom_}/${t_} timeframes lean ${dir_} — low conviction`;
                      const sub_ = (dir_ === "Mixed" || agr_ < 0.6)
                        ? "Timeframes conflict. Wait for confirmation before acting."
                        : agr_ >= 0.8
                        ? "Strong cross-timeframe consensus — higher-conviction signal."
                        : "Moderate consensus — use with normal risk controls.";
                      return (
                        <div className={`flex items-center gap-3 rounded-xl border px-4 py-2.5 ${cls_}`}>
                          <span className="text-base flex-shrink-0">{ico_}</span>
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-semibold">{msg_}</p>
                            <p className="text-xs opacity-70 mt-0.5">{sub_}</p>
                          </div>
                          <div className="flex-shrink-0 hidden sm:flex flex-col items-end gap-0.5">
                            <div className="flex gap-0.5 h-2">
                              {signals.map((s, i) => (
                                <div key={i} title={`${s.timeframe}: ${s.direction}`}
                                  className={`w-4 rounded-sm ${
                                    s.direction === "Bullish" ? "bg-emerald-500" :
                                    s.direction === "Bearish" ? "bg-rose-500" : "bg-amber-400/40"
                                  }`}
                                />
                              ))}
                            </div>
                            <p className="text-[9px] opacity-50">{b_}B &middot; {be_}Be &middot; {t_-b_-be_}N</p>
                          </div>
                        </div>
                      );
                    })()}

                    <TimeframeGrid signals={signals} symbol={activeSymbol} />
                    {/* SHAP “What drove this?” — Sprint 24 */}
                    <ShapPanel
                      modelData={modelData}
                      activeTf={shapActiveTf}
                      signals={signals}
                    />
                  </>
                ) : (
                  <TrainNowEmptyState symbol={activeSymbol} onTrainStarted={handleTrainStarted} />
                )}
              </section>

              {/* Sprint 27 — Price Chart (TradingView embed) */}
              <PriceChartWidget symbol={activeSymbol} />

              {/* Row 3 – Price Targets & Kelly Sizing (Sprint 5) */}
              <PriceTargetCard symbol={activeSymbol} isVisible={signals.length > 0} />

              {/* Row 4 – LLM Investment Manager Insight (todos-v5 Sprint 1) */}
              <LLMInsightCard
                symbol={activeSymbol}
                signals={signals}
                currentPrice={currentPrice}
                macroScore={macroScore}
                vix={vixLevel}
                yieldSpread={yieldSpread}
                macroRegime={regimeFromSnapshot ?? null}
                newsSentiment={{
                  d1: sentData?.sentiment_1d ?? null,
                  d7: sentData?.sentiment_7d ?? null,
                  d30: sentData?.sentiment_30d ?? null,
                }}
                gasScore={gasScore}
              />

              {/* Phase 8.2 — Per-ticker data panel (admin only, collapsible) */}
              <TickerDataPanel
                symbol={activeSymbol}
                isAdmin={isAdmin}
                onTrained={() => mutateTech()}
              />

              {/* Row 4 – Why moving + Conflicts */}
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
                    mlOutput={mlOutput}
                    initialAiSummary={initialAiSummary}
                  />
                </div>
                <ConflictDetector
                  hasConflict={conflictData.hasConflict}
                  conflicts={conflictData.conflicts}
                  conflictSummary={conflictData.summary}
                />
              </section>

              {/* Row 5 – Quick links */}
              <section className="flex flex-wrap gap-4 pt-4 border-t border-slate-800/50">
                <Link href="/macro" className="text-sm text-sky-400 hover:text-sky-300 font-medium transition-colors">
                  View Full Macro Intel &rarr;
                </Link>
                <Link href="/news-sentiment" className="text-sm text-sky-400 hover:text-sky-300 font-medium transition-colors">
                  View Full Sentiment Intel &rarr;
                </Link>
                <Link href="/watchlist-overview" className="text-sm text-sky-400 hover:text-sky-300 font-medium transition-colors">
                  Watchlist Overview &rarr;
                </Link>
              </section>

            </div>
          )}
        </div>
      </div>
    </div>
  );
}