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

// ─── Page Component ──────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { symbol: activeSymbol, setSymbol: setActiveSymbol } = useSymbol();
  const { user } = useAuth();
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

  const { data: gasSnapshot, error: gasError, isLoading: gasLoading } = useSWR(
    `gas-snapshot-${activeSymbol}`,
    () => fetchGasSnapshot(activeSymbol),
    { refreshInterval: 60_000, shouldRetryOnError: false, keepPreviousData: true },
  );

  const { data: techData, error: techError, mutate: mutateTech } = useSWR(
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

  // Live price — refreshes every 5 minutes; used by LLM insight card for price targets.
  // Uses keepPreviousData so the card never flickers when the symbol changes.
  const { data: priceData } = useSWR(
    `price-${activeSymbol}`,
    () => fetchLatestPrice(activeSymbol),
    { refreshInterval: 300_000, shouldRetryOnError: false, keepPreviousData: true },
  );

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
  const signals = techData?.signals ?? [];
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
        <aside className="hidden xl:block w-48 flex-shrink-0">
          <WatchlistWidget activeSymbol={activeSymbol} onSelectSymbol={setActiveSymbol} />
        </aside>

        <div className="min-w-0 flex-1 space-y-6">
          <header className="flex flex-col gap-1 border-b border-slate-800 pb-5">
            <h1 className="text-3xl font-black tracking-tight text-slate-100">{activeSymbol} Intelligence</h1>
            <p className="text-sm text-slate-400">Real-time GAS, Regime, and Multi-Timeframe layers.</p>
            <div className="mt-0.5"><SnapshotMeta snapshot={gasSnapshot} /></div>
          </header>

          <div className="xl:hidden">
            <WatchlistWidget activeSymbol={activeSymbol} onSelectSymbol={setActiveSymbol} />
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
                  <MarketWeatherWidget gasScore={gasScore} symbol={activeSymbol} onExplain={openGasExplain} />
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
                  <TimeframeGrid signals={signals} symbol={activeSymbol} />
                ) : (
                  <TrainNowEmptyState symbol={activeSymbol} onTrainStarted={handleTrainStarted} />
                )}
              </section>

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
              </section>

            </div>
          )}
        </div>
      </div>
    </div>
  );
}