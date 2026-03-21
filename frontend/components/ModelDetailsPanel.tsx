"use client";

/**
 * ModelDetailsPanel.tsx — todos-v5 Sprint 4 (Phase 2.2)
 *
 * Dev transparency slide-over panel. Triggered by "⚙ Model Details" link
 * at the bottom of the Technical Consensus section.
 *
 * Four tabs:
 *   Overview      — winner model, accuracy, Sharpe, quality gate, training date
 *   Features      — all 15 input features with plain-English descriptions + SHAP bar chart
 *   Training Info — train/val split, target balance, horizon, MLflow run ID
 *   All Models    — competition table: logistic vs xgboost vs lightgbm vs ensemble
 *
 * Plus a "Live Accuracy" section at the bottom showing real-world performance
 * from the ml_predictions table once enough outcomes have resolved.
 *
 * Props:
 *   symbol   — active ticker
 *   isOpen   — whether the panel is visible
 *   onClose  — callback to close
 *
 * Sprint 6 addition: footer now has a "Full page →" link to /model-info/[symbol]
 */

import React, { useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import { X, ChevronRight, ExternalLink } from "lucide-react";
import {
  fetchModelDetails,
  fetchPredictionStats,
  type TimeframeModelDetail,
  type TimeframePredictionStats,
} from "../lib/api_model_details";

// ── Timeframe display order ───────────────────────────────────────────────────
const TF_ORDER = ["1h", "4h", "1d", "1wk", "1mo"];
const TF_LABELS: Record<string, string> = {
  "1h": "1 Hour", "4h": "4 Hour", "1d": "1 Day", "1wk": "1 Week", "1mo": "1 Month",
};

// ── Tab definitions ───────────────────────────────────────────────────────────
type Tab = "overview" | "features" | "training" | "models";
const TABS: { id: Tab; label: string }[] = [
  { id: "overview",  label: "Overview"   },
  { id: "features",  label: "Features"   },
  { id: "training",  label: "Training"   },
  { id: "models",    label: "All Models" },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function sharpeColor(s: number): string {
  if (s >= 1.5) return "text-emerald-400";
  if (s >= 0.5) return "text-sky-400";
  if (s >= 0)   return "text-amber-400";
  return "text-rose-400";
}

function sharpeLabel(s: number): string {
  if (s >= 1.5) return "Excellent";
  if (s >= 0.5) return "Good";
  if (s >= 0)   return "Weak";
  return "Poor";
}

function accColor(a: number): string {
  if (a >= 0.58) return "text-emerald-400";
  if (a >= 0.53) return "text-sky-400";
  if (a >= 0.50) return "text-amber-400";
  return "text-rose-400";
}

function modelBadgeColor(name: string): string {
  const c: Record<string, string> = {
    logistic:  "bg-sky-900/40 text-sky-300 border-sky-800/50",
    xgboost:   "bg-violet-900/40 text-violet-300 border-violet-800/50",
    lightgbm:  "bg-teal-900/40 text-teal-300 border-teal-800/50",
    ensemble:  "bg-amber-900/40 text-amber-300 border-amber-800/50",
    prophet:   "bg-slate-800/60 text-slate-500 border-slate-700/40",
  };
  return c[name] ?? "bg-slate-800/40 text-slate-400 border-slate-700/40";
}

function healthBadge(health?: string) {
  const cfg: Record<string, { label: string; color: string }> = {
    good:               { label: "Good",              color: "text-emerald-400 bg-emerald-950/30 border-emerald-800/40" },
    marginal:           { label: "Marginal",           color: "text-amber-400 bg-amber-950/30 border-amber-800/40"     },
    poor:               { label: "Poor",               color: "text-rose-400 bg-rose-950/30 border-rose-800/40"         },
    insufficient_data:  { label: "Insufficient data",  color: "text-slate-400 bg-slate-800/40 border-slate-700/40"     },
  };
  const c = cfg[health ?? "insufficient_data"] ?? cfg["insufficient_data"];
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${c.color}`}>
      {c.label}
    </span>
  );
}

// ── SHAP mini-bar chart ───────────────────────────────────────────────────────

function ShapBar({ value, maxVal }: { value: number; maxVal: number }) {
  const pct = maxVal > 0 ? Math.min((value / maxVal) * 100, 100) : 0;
  return (
    <div className="flex-1 h-2 rounded-full bg-slate-800 overflow-hidden">
      <div
        className="h-full rounded-full bg-violet-500/70 transition-all duration-500"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

// ── Tabs ──────────────────────────────────────────────────────────────────────

function OverviewTab({
  tf, detail, stats,
}: {
  tf: string;
  detail: TimeframeModelDetail;
  stats?: TimeframePredictionStats;
}) {
  const ti    = detail.training_info;
  const winAcc = detail.all_models[detail.winner_model]?.accuracy ?? 0;
  const winSh  = detail.all_models[detail.winner_model]?.sharpe   ?? 0;

  return (
    <div className="space-y-5">
      {/* Winner card */}
      <div className="rounded-xl border border-slate-700/60 bg-slate-900/50 p-5 space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Winner Model</span>
          <span className={`text-xs font-bold px-2.5 py-1 rounded-full border ${modelBadgeColor(detail.winner_model)}`}>
            {detail.winner_model}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg bg-slate-800/50 px-3 py-2.5">
            <p className="text-[10px] text-slate-500 mb-0.5">Sharpe (validation)</p>
            <p className={`text-xl font-black tabular-nums ${sharpeColor(winSh)}`}>{winSh.toFixed(3)}</p>
            <p className={`text-[10px] font-medium ${sharpeColor(winSh)}`}>{sharpeLabel(winSh)}</p>
          </div>
          <div className="rounded-lg bg-slate-800/50 px-3 py-2.5">
            <p className="text-[10px] text-slate-500 mb-0.5">Accuracy (validation)</p>
            <p className={`text-xl font-black tabular-nums ${accColor(winAcc)}`}>{(winAcc * 100).toFixed(1)}%</p>
            <p className="text-[10px] text-slate-500">on held-out data</p>
          </div>
        </div>
        <div className="rounded-lg bg-slate-800/30 border border-slate-700/40 px-3 py-2">
          <p className="text-[10px] text-slate-500 leading-relaxed">{detail.how_target_was_built}</p>
        </div>
        {ti.quality_gate_passed !== undefined && (
          <div className={`flex items-center gap-2 rounded-lg px-3 py-2 border ${
            ti.quality_gate_passed
              ? "bg-emerald-950/20 border-emerald-800/40"
              : "bg-amber-950/20 border-amber-800/40"
          }`}>
            <span className="text-sm">{ti.quality_gate_passed ? "✅" : "⚠️"}</span>
            <p className={`text-xs font-medium ${ti.quality_gate_passed ? "text-emerald-400" : "text-amber-400"}`}>
              Quality gate {ti.quality_gate_passed ? "passed" : "not passed"}
              {!ti.quality_gate_passed && " — fallback model selected"}
            </p>
          </div>
        )}
      </div>

      {/* Live accuracy (from prediction DB) */}
      <div className="rounded-xl border border-slate-700/60 bg-slate-900/50 p-5 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Live Performance</span>
          {healthBadge(stats ? (stats as any).model_health_per_tf ?? undefined : undefined)}
        </div>

        {stats && stats.total_resolved > 0 ? (
          <>
            <div className="grid grid-cols-3 gap-2">
              <div className="rounded-lg bg-slate-800/50 px-3 py-2">
                <p className="text-[10px] text-slate-500 mb-0.5">Resolved</p>
                <p className="text-base font-black text-slate-200">{stats.total_resolved}</p>
              </div>
              <div className="rounded-lg bg-slate-800/50 px-3 py-2">
                <p className="text-[10px] text-slate-500 mb-0.5">Live accuracy</p>
                <p className={`text-base font-black ${stats.live_accuracy !== null ? accColor(stats.live_accuracy) : "text-slate-400"}`}>
                  {stats.live_accuracy !== null ? `${(stats.live_accuracy * 100).toFixed(1)}%` : "—"}
                </p>
              </div>
              <div className="rounded-lg bg-slate-800/50 px-3 py-2">
                <p className="text-[10px] text-slate-500 mb-0.5">30-day</p>
                <p className={`text-base font-black ${stats.recent_30d_accuracy !== null ? accColor(stats.recent_30d_accuracy) : "text-slate-400"}`}>
                  {stats.recent_30d_accuracy !== null ? `${(stats.recent_30d_accuracy * 100).toFixed(1)}%` : "—"}
                </p>
              </div>
            </div>
            {stats.trend && (
              <p className={`text-xs font-medium ${
                stats.trend === "improving" ? "text-emerald-400" :
                stats.trend === "degrading" ? "text-rose-400"    : "text-slate-400"
              }`}>
                {stats.trend === "improving" ? "↑ Improving" : stats.trend === "degrading" ? "↓ Degrading" : "→ Stable"} — 30-day vs overall
              </p>
            )}
          </>
        ) : (
          <p className="text-xs text-slate-500 leading-relaxed">
            Live accuracy will appear here after predictions start resolving.
            The first outcomes resolve after the horizon period passes
            ({tf === "1h" ? "~3 hours" : tf === "4h" ? "~12 hours" : tf === "1d" ? "~3 days" : tf === "1wk" ? "~2 weeks" : "~1 month"}).
          </p>
        )}
      </div>
    </div>
  );
}

function FeaturesTab({
  detail,
}: {
  detail: TimeframeModelDetail;
}) {
  const shap: Record<string, number> | null = (detail as any).shap_importance ?? null;
  const maxShap = shap ? Math.max(...Object.values(shap)) : 0;

  return (
    <div className="space-y-4">
      {shap ? (
        <div className="rounded-lg border border-violet-800/30 bg-violet-950/10 px-3 py-2.5">
          <p className="text-[10px] font-semibold text-violet-400 mb-0.5">SHAP Feature Importance</p>
          <p className="text-[10px] text-slate-500">
            Bars show mean |SHAP value| — how much each feature contributed to model predictions on the validation set.
            Longer bar = more influential.
          </p>
        </div>
      ) : (
        <div className="rounded-lg border border-slate-700/40 bg-slate-800/20 px-3 py-2.5">
          <p className="text-[10px] text-slate-500">
            SHAP importance available after next retrain (requires <code className="text-sky-400">shap</code> package and a tree-based winner model).
          </p>
        </div>
      )}

      <div className="space-y-2">
        {detail.features_used.map((feat, i) => {
          const shapVal = shap?.[feat.name] ?? null;
          return (
            <div key={feat.name} className="rounded-lg border border-slate-700/40 bg-slate-800/20 p-3">
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-[10px] font-mono font-bold text-sky-400 flex-shrink-0 w-5 text-right text-slate-600">
                  {i + 1}
                </span>
                <span className="text-xs font-bold text-slate-200 font-mono">{feat.name}</span>
                {shapVal !== null && (
                  <span className="text-[10px] text-violet-400 ml-auto font-mono">{shapVal.toFixed(4)}</span>
                )}
              </div>
              {shapVal !== null && (
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="w-5 flex-shrink-0" />
                  <ShapBar value={shapVal} maxVal={maxShap} />
                </div>
              )}
              <div className="flex gap-2">
                <span className="w-5 flex-shrink-0" />
                <p className="text-[11px] text-slate-500 leading-relaxed">{feat.description}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TrainingTab({ detail }: { detail: TimeframeModelDetail }) {
  const ti = detail.training_info;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: "Total rows",   value: ti.total_rows?.toLocaleString() ?? "—" },
          { label: "Train rows",   value: ti.train_rows?.toLocaleString() ?? "—" },
          { label: "Val rows",     value: ti.val_rows?.toLocaleString() ?? "—" },
          { label: "Horizon",      value: ti.horizon_periods ? `${ti.horizon_periods} periods` : "—" },
          { label: "Target: UP %", value: ti.target_balance_up_pct != null ? `${ti.target_balance_up_pct.toFixed(1)}%` : "—" },
          { label: "Trained at",   value: ti.trained_at ? new Date(ti.trained_at).toLocaleDateString("en-DE") : "—" },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-lg bg-slate-800/50 border border-slate-700/40 px-3 py-2.5">
            <p className="text-[10px] text-slate-500 mb-0.5">{label}</p>
            <p className="text-xs font-semibold text-slate-200 tabular-nums">{value}</p>
          </div>
        ))}
      </div>

      {/* Train/val split visual */}
      {ti.train_rows != null && ti.val_rows != null && (
        <div className="rounded-xl border border-slate-700/60 bg-slate-900/50 p-4 space-y-2">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Chronological 80/20 Split</p>
          <div className="flex h-4 rounded-full overflow-hidden gap-px">
            <div className="bg-sky-600/70 rounded-l-full flex items-center justify-center"
              style={{ width: "80%" }}>
              <span className="text-[9px] font-bold text-sky-200">Train 80%</span>
            </div>
            <div className="bg-violet-600/70 rounded-r-full flex-1 flex items-center justify-center">
              <span className="text-[9px] font-bold text-violet-200">Val 20%</span>
            </div>
          </div>
          <p className="text-[10px] text-slate-600 leading-relaxed">
            No shuffling — chronological split prevents lookahead bias. The model never sees future data during training.
          </p>
        </div>
      )}

      {/* How Sharpe was computed */}
      <div className="rounded-xl border border-slate-700/60 bg-slate-900/50 p-4 space-y-2">
        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Sharpe Ratio Formula</p>
        <p className="text-xs text-slate-400 leading-relaxed font-mono bg-slate-800/50 rounded-lg px-3 py-2">
          {detail.how_sharpe_was_built}
        </p>
      </div>

      {/* MLflow run link */}
      {ti.mlflow_run_id && (
        <div className="rounded-xl border border-slate-700/60 bg-slate-900/50 p-4">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-2">MLflow Run</p>
          <div className="flex items-center gap-2">
            <code className="text-[10px] text-sky-400 bg-slate-800 px-2 py-1 rounded font-mono break-all flex-1">
              {ti.mlflow_run_id}
            </code>
            <a
              href={`http://localhost:5000/#/experiments/1/runs/${ti.mlflow_run_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-shrink-0 text-sky-400 hover:text-sky-300 transition-colors"
              title="Open in MLflow UI (localhost:5000)"
            >
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>
          <p className="text-[10px] text-slate-600 mt-1">
            Start UI: <code className="text-slate-500">start_mlflow.bat</code> → http://localhost:5000
          </p>
        </div>
      )}
    </div>
  );
}

function AllModelsTab({ detail }: { detail: TimeframeModelDetail }) {
  const modelOrder = ["ensemble", "xgboost", "lightgbm", "logistic", "prophet"];
  const models = Object.entries(detail.all_models)
    .sort(([a], [b]) => {
      const ai = modelOrder.indexOf(a);
      const bi = modelOrder.indexOf(b);
      return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
    });

  return (
    <div className="space-y-3">
      <p className="text-[10px] text-slate-500 leading-relaxed">
        All models compete on the same validation set. Winner is selected by highest Sharpe ratio
        that passes both accuracy ≥ 50% and Sharpe ≥ 0 gates.
      </p>

      {models.map(([name, m]) => {
        const isWinner     = name === detail.winner_model;
        const isDisqualified = m.disqualified;
        return (
          <div
            key={name}
            className={`rounded-xl border p-4 space-y-3 transition-colors ${
              isWinner
                ? "border-amber-700/60 bg-amber-950/15"
                : isDisqualified
                ? "border-slate-700/30 bg-slate-800/10 opacity-60"
                : "border-slate-700/50 bg-slate-800/20"
            }`}
          >
            <div className="flex items-center gap-2">
              <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${modelBadgeColor(name)}`}>
                {name}
              </span>
              {isWinner && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-900/50 text-amber-300 border border-amber-700/50">
                  ✓ Winner
                </span>
              )}
              {isDisqualified && (
                <span className="text-[10px] text-slate-500 ml-auto">
                  ✗ Disqualified{m.reason ? `: ${m.reason}` : ""}
                </span>
              )}
            </div>

            {!isDisqualified && (
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <p className="text-[10px] text-slate-600 mb-0.5">Sharpe</p>
                  <p className={`text-sm font-black tabular-nums ${sharpeColor(m.sharpe)}`}>
                    {m.sharpe.toFixed(3)}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] text-slate-600 mb-0.5">Accuracy</p>
                  <p className={`text-sm font-black tabular-nums ${accColor(m.accuracy)}`}>
                    {(m.accuracy * 100).toFixed(1)}%
                  </p>
                </div>
                <div>
                  <p className="text-[10px] text-slate-600 mb-0.5">Total return</p>
                  <p className={`text-sm font-black tabular-nums ${m.total_return >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                    {m.total_return >= 0 ? "+" : ""}{(m.total_return * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
            )}
          </div>
        );
      })}

      <div className="rounded-lg bg-slate-800/30 border border-slate-700/30 px-3 py-2.5">
        <p className="text-[10px] text-slate-500 leading-relaxed">
          <span className="text-amber-400 font-medium">Ensemble</span> blends logistic + XGBoost + LightGBM probabilities
          weighted by their individual Sharpe ratios. It frequently wins by cancelling individual model errors.
          <span className="text-rose-400 font-medium ml-1">Prophet</span> was removed — it consistently
          returned accuracy=0.0 on directional classification tasks.
        </p>
      </div>
    </div>
  );
}

// ── Live accuracy across timeframes (bottom of panel) ────────────────────────

function LiveAccuracySection({
  stats,
}: {
  stats: { timeframes?: Record<string, TimeframePredictionStats>; model_health?: string; total_resolved_all_tfs?: number };
}) {
  if (!stats.timeframes || Object.keys(stats.timeframes).length === 0) return null;

  const tfs = TF_ORDER.filter(tf => stats.timeframes![tf]);

  return (
    <div className="border-t border-slate-800 pt-5 mt-5 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Live Accuracy — All Timeframes</p>
        {healthBadge(stats.model_health)}
      </div>
      <div className="space-y-2">
        {tfs.map(tf => {
          const s = stats.timeframes![tf];
          return (
            <div key={tf} className="flex items-center gap-3">
              <span className="text-[10px] font-mono font-bold text-slate-500 w-8 flex-shrink-0">{tf}</span>
              <div className="flex-1 h-2 rounded-full bg-slate-800 overflow-hidden">
                {s.live_accuracy !== null ? (
                  <div
                    className={`h-full rounded-full transition-all duration-700 ${
                      s.live_accuracy >= 0.55 ? "bg-emerald-500" :
                      s.live_accuracy >= 0.50 ? "bg-amber-500"   : "bg-rose-500"
                    }`}
                    style={{ width: `${s.live_accuracy * 100}%` }}
                  />
                ) : (
                  <div className="h-full rounded-full bg-slate-700 w-1/3 animate-pulse" />
                )}
              </div>
              <span className={`text-xs font-mono font-bold tabular-nums w-12 text-right ${
                s.live_accuracy !== null ? accColor(s.live_accuracy) : "text-slate-600"
              }`}>
                {s.live_accuracy !== null ? `${(s.live_accuracy * 100).toFixed(1)}%` : "n/a"}
              </span>
              <span className="text-[10px] text-slate-600 w-6 text-right">{s.total_resolved}</span>
            </div>
          );
        })}
      </div>
      <p className="text-[10px] text-slate-600">
        {stats.total_resolved_all_tfs ?? 0} total resolved predictions · accuracy bar shows % correct
      </p>
    </div>
  );
}

// ── Main panel ────────────────────────────────────────────────────────────────

interface ModelDetailsPanelProps {
  symbol:  string;
  isOpen:  boolean;
  onClose: () => void;
}

export default function ModelDetailsPanel({ symbol, isOpen, onClose }: ModelDetailsPanelProps) {
  const [activeTab, setActiveTab]       = useState<Tab>("overview");
  const [activeTf, setActiveTf]         = useState<string>("1d");

  const { data: modelData, isLoading: modelLoading } = useSWR(
    isOpen ? `model-details-${symbol}` : null,
    () => fetchModelDetails(symbol),
    { revalidateOnFocus: false, shouldRetryOnError: false },
  );
  const { data: statsData, isLoading: statsLoading } = useSWR(
    isOpen ? `prediction-stats-${symbol}` : null,
    () => fetchPredictionStats(symbol),
    { revalidateOnFocus: false, shouldRetryOnError: false },
  );

  const isLoading = modelLoading || statsLoading;

  const availableTfs = modelData
    ? TF_ORDER.filter(tf => modelData.timeframes[tf])
    : [];

  const currentTf = availableTfs.includes(activeTf) ? activeTf : (availableTfs[0] ?? "1d");
  const detail     = modelData?.timeframes[currentTf];
  const tfStats    = statsData?.timeframes?.[currentTf];

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-40 bg-black/50 backdrop-blur-sm transition-opacity duration-300 ${
          isOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        }`}
        onClick={onClose}
      />

      {/* Panel */}
      <div
        role="dialog"
        aria-modal="true"
        className={`fixed top-0 right-0 z-50 h-full w-full sm:max-w-xl lg:max-w-2xl bg-slate-950 border-l border-slate-800 shadow-2xl flex flex-col transition-transform duration-300 ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="flex items-start justify-between px-6 py-5 border-b border-slate-800 flex-shrink-0">
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-base">⚙</span>
              <h2 className="text-base font-bold text-slate-100">Model Details</h2>
              <span className="text-[10px] font-bold text-slate-500 bg-slate-800 px-2 py-0.5 rounded">{symbol}</span>
            </div>
            <p className="text-xs text-slate-500">Technical ML pipeline — training metadata &amp; live performance</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors mt-0.5"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-3">
              <div className="flex gap-1 justify-center">
                {[0,1,2].map(i => (
                  <div key={i} className="h-2 w-2 rounded-full bg-slate-600 animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
              </div>
              <p className="text-xs text-slate-500">Loading model details…</p>
            </div>
          </div>
        ) : !modelData || availableTfs.length === 0 ? (
          <div className="flex-1 flex items-center justify-center p-8 text-center">
            <div className="space-y-3">
              <span className="text-4xl">🧠</span>
              <p className="text-sm font-semibold text-slate-300">No trained models for {symbol}</p>
              <p className="text-xs text-slate-500">Train the models first using the "▶ Train Now" button.</p>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto">
            {/* Timeframe selector */}
            {availableTfs.length > 1 && (
              <div className="flex gap-1 px-5 pt-4 pb-0 flex-wrap">
                {availableTfs.map(tf => (
                  <button
                    key={tf}
                    onClick={() => setActiveTf(tf)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                      currentTf === tf
                        ? "bg-slate-700 text-slate-100"
                        : "text-slate-500 hover:text-slate-300 hover:bg-slate-800/60"
                    }`}
                  >
                    {TF_LABELS[tf] ?? tf}
                  </button>
                ))}
              </div>
            )}

            {/* Tab bar */}
            <div className="flex border-b border-slate-800 px-5 mt-3">
              {TABS.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`pb-2.5 px-2 mr-4 text-xs font-semibold border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? "border-sky-500 text-sky-400"
                      : "border-transparent text-slate-500 hover:text-slate-300"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab content */}
            {detail && (
              <div className="px-5 py-5">
                {activeTab === "overview"  && <OverviewTab  tf={currentTf} detail={detail} stats={tfStats} />}
                {activeTab === "features"  && <FeaturesTab  detail={detail} />}
                {activeTab === "training"  && <TrainingTab  detail={detail} />}
                {activeTab === "models"    && <AllModelsTab detail={detail} />}

                {/* Live accuracy across all timeframes (always shown at bottom) */}
                {statsData?.available && (
                  <LiveAccuracySection stats={statsData as any} />
                )}

                {/* Dev note */}
                {modelData.note && (
                  <p className="mt-6 text-[10px] text-slate-600 border-t border-slate-800 pt-3">
                    {modelData.note}
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Footer — Sprint 6: "Full page" link added */}
        <div className="flex-shrink-0 border-t border-slate-800 px-5 py-3 flex items-center justify-between gap-3">
          <p className="text-[10px] text-slate-600">
            Educational transparency — not investment advice
          </p>
          <div className="flex items-center gap-3 flex-shrink-0">
            <Link
              href={`/model-info/${symbol}`}
              onClick={onClose}
              className="flex items-center gap-1 text-[10px] text-sky-500 hover:text-sky-300 transition-colors font-medium"
            >
              Full page
              <ExternalLink className="h-3 w-3" />
            </Link>
            <a
              href="http://localhost:5000"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-[10px] text-slate-500 hover:text-slate-300 transition-colors"
            >
              <ExternalLink className="h-3 w-3" />
              MLflow UI
            </a>
          </div>
        </div>
      </div>
    </>
  );
}
