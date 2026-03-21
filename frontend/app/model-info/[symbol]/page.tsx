"use client";

/**
 * /model-info/[symbol] — ML Model Deep-Dive Page
 *
 * todos-v6 B7 / todos-v5 Phase 2.3 / Sprint 6
 *
 * A standalone full-page version of ModelDetailsPanel for a specific symbol.
 * Accessible from the "⚙ Model Details" link in TimeframeGrid.
 * Shows all timeframes in one view with tabs per timeframe, plus:
 *   - Feature importance (SHAP bars)
 *   - Training metadata
 *   - All-models competition table
 *   - Prediction history table (last 30 resolved predictions)
 *   - Live accuracy + trend charts
 *   - Drift alerts for this symbol (if any)
 *   - Optuna tuning status (if enabled)
 */

import React, { useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import { ArrowLeft, ExternalLink, RefreshCw, AlertTriangle } from "lucide-react";
import {
  fetchModelDetails,
  fetchPredictionStats,
  type TimeframeModelDetail,
  type TimeframePredictionStats,
  type ModelDetailsResponse,
  type PredictionStatsResponse,
} from "../../../lib/api_model_details";
import { fetchDriftAlerts, fetchOptunaParams, type DriftAlertDto } from "../../../lib/api_admin_ml";

// ─── Constants ────────────────────────────────────────────────────────────────

const TF_ORDER  = ["1h", "4h", "1d", "1wk", "1mo"];
const TF_LABELS: Record<string, string> = {
  "1h": "1 Hour", "4h": "4 Hour", "1d": "1 Day", "1wk": "1 Week", "1mo": "1 Month",
};

type Tab = "overview" | "features" | "training" | "models" | "history" | "drift";

const ALL_TABS: { id: Tab; label: string; icon: string }[] = [
  { id: "overview",  label: "Overview",    icon: "📊" },
  { id: "features",  label: "Features",    icon: "🔬" },
  { id: "training",  label: "Training",    icon: "🏋️" },
  { id: "models",    label: "All Models",  icon: "🤖" },
  { id: "history",   label: "History",     icon: "📅" },
  { id: "drift",     label: "Drift",       icon: "⚠️" },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function sharpeColor(s: number): string {
  if (s >= 1.5) return "text-emerald-400";
  if (s >= 0.5) return "text-sky-400";
  if (s >= 0)   return "text-amber-400";
  return "text-rose-400";
}

function accColor(a: number): string {
  if (a >= 0.58) return "text-emerald-400";
  if (a >= 0.53) return "text-sky-400";
  if (a >= 0.50) return "text-amber-400";
  return "text-rose-400";
}

function modelBadge(name: string) {
  const c: Record<string, string> = {
    logistic: "bg-sky-900/40 text-sky-300 border-sky-800/50",
    xgboost:  "bg-violet-900/40 text-violet-300 border-violet-800/50",
    lightgbm: "bg-teal-900/40 text-teal-300 border-teal-800/50",
    ensemble: "bg-amber-900/40 text-amber-300 border-amber-800/50",
    prophet:  "bg-slate-800/60 text-slate-500 border-slate-700/40",
  };
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${c[name] ?? "bg-slate-800/40 text-slate-400 border-slate-700/40"}`}>
      {name}
    </span>
  );
}

function QualityBadge({ passed }: { passed?: boolean }) {
  if (passed === undefined) return null;
  return passed ? (
    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-950/40 text-emerald-400 border border-emerald-800/40">✓ Quality gate</span>
  ) : (
    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-950/40 text-amber-400 border border-amber-800/40">⚠ Fallback used</span>
  );
}

function StatCard({ label, value, sub, color = "text-slate-200" }: {
  label: string; value: string; sub?: string; color?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-800/30 px-4 py-3 space-y-0.5">
      <p className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</p>
      <p className={`text-xl font-black tabular-nums ${color}`}>{value}</p>
      {sub && <p className="text-[10px] text-slate-500">{sub}</p>}
    </div>
  );
}

// ─── SHAP bar ─────────────────────────────────────────────────────────────────

function ShapRow({ name, value, max, description }: {
  name: string; value: number; max: number; description: string;
}) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="rounded-lg border border-slate-700/30 bg-slate-800/20 px-4 py-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-mono font-bold text-sky-400">{name}</span>
        <span className="text-[10px] font-mono text-violet-400 tabular-nums">{value.toFixed(4)}</span>
      </div>
      <div className="flex items-center gap-2">
        <div className="flex-1 h-2 rounded-full bg-slate-700 overflow-hidden">
          <div className="h-full rounded-full bg-violet-500/70 transition-all duration-700" style={{ width: `${pct}%` }} />
        </div>
        <span className="text-[10px] text-slate-600 tabular-nums w-8 text-right">{pct.toFixed(0)}%</span>
      </div>
      <p className="text-[11px] text-slate-500 leading-relaxed">{description}</p>
    </div>
  );
}

// ─── Tab sections ─────────────────────────────────────────────────────────────

function OverviewSection({
  detail, stats, tf,
}: { detail: TimeframeModelDetail; stats?: TimeframePredictionStats; tf: string }) {
  const winAcc = detail.all_models[detail.winner_model]?.accuracy ?? 0;
  const winSh  = detail.all_models[detail.winner_model]?.sharpe   ?? 0;
  const ti     = detail.training_info;

  return (
    <div className="space-y-6">
      {/* Winner headline */}
      <div className="flex flex-wrap items-center gap-3">
        {modelBadge(detail.winner_model)}
        <QualityBadge passed={ti.quality_gate_passed} />
        {ti.trained_at && (
          <span className="text-[10px] text-slate-500">
            Trained {new Date(ti.trained_at).toLocaleDateString("en-DE")}
          </span>
        )}
      </div>

      {/* Stat grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Sharpe (val)" value={winSh.toFixed(3)}
          color={sharpeColor(winSh)}
          sub={winSh >= 1.5 ? "Excellent" : winSh >= 0.5 ? "Good" : winSh >= 0 ? "Weak" : "Poor"} />
        <StatCard label="Accuracy (val)" value={`${(winAcc * 100).toFixed(1)}%`}
          color={accColor(winAcc)} sub="held-out data" />
        <StatCard label="Live accuracy"
          value={stats?.live_accuracy != null ? `${(stats.live_accuracy * 100).toFixed(1)}%` : "n/a"}
          color={stats?.live_accuracy != null ? accColor(stats.live_accuracy) : "text-slate-500"}
          sub={stats ? `${stats.total_resolved} resolved` : "no data yet"} />
        <StatCard label="30-day accuracy"
          value={stats?.recent_30d_accuracy != null ? `${(stats.recent_30d_accuracy * 100).toFixed(1)}%` : "n/a"}
          color={stats?.recent_30d_accuracy != null ? accColor(stats.recent_30d_accuracy) : "text-slate-500"}
          sub={stats?.trend ? `Trend: ${stats.trend}` : undefined} />
      </div>

      {/* Target description */}
      <div className="rounded-xl border border-slate-700/50 bg-slate-800/30 px-4 py-3 space-y-1">
        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Prediction Target</p>
        <p className="text-xs text-slate-400 leading-relaxed">{detail.how_target_was_built}</p>
      </div>

      {/* Sharpe formula */}
      <div className="rounded-xl border border-slate-700/50 bg-slate-800/30 px-4 py-3 space-y-1">
        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Sharpe Calculation</p>
        <p className="text-xs font-mono text-slate-400 leading-relaxed">{detail.how_sharpe_was_built}</p>
      </div>

      {/* Regime breakdown */}
      {stats?.by_regime && Object.keys(stats.by_regime).length > 0 && (
        <div className="rounded-xl border border-slate-700/50 bg-slate-800/30 px-4 py-4 space-y-3">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Accuracy by Market Regime</p>
          <div className="space-y-2">
            {Object.entries(stats.by_regime).map(([regime, data]) => (
              <div key={regime} className="flex items-center gap-3">
                <span className="text-xs text-slate-400 w-28 flex-shrink-0 capitalize">{regime}</span>
                <div className="flex-1 h-1.5 rounded-full bg-slate-700 overflow-hidden">
                  {data.accuracy != null ? (
                    <div
                      className={`h-full rounded-full ${data.accuracy >= 0.55 ? "bg-emerald-500" : data.accuracy >= 0.5 ? "bg-amber-500" : "bg-rose-500"}`}
                      style={{ width: `${data.accuracy * 100}%` }}
                    />
                  ) : <div className="h-full w-1/3 bg-slate-600 rounded-full animate-pulse" />}
                </div>
                <span className={`text-xs font-mono tabular-nums w-12 text-right ${data.accuracy != null ? accColor(data.accuracy) : "text-slate-600"}`}>
                  {data.accuracy != null ? `${(data.accuracy * 100).toFixed(1)}%` : "n/a"}
                </span>
                <span className="text-[10px] text-slate-600 w-8 text-right">{data.n}x</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function FeaturesSection({ detail }: { detail: TimeframeModelDetail }) {
  const shap: Record<string, number> | null = (detail as any).shap_importance ?? null;
  const maxShap = shap ? Math.max(...Object.values(shap)) : 0;

  return (
    <div className="space-y-4">
      {shap ? (
        <div className="rounded-lg border border-violet-800/30 bg-violet-950/10 px-4 py-2.5">
          <p className="text-[10px] font-semibold text-violet-400">SHAP Feature Importance</p>
          <p className="text-[10px] text-slate-500 mt-0.5">
            Mean |SHAP value| on validation set — how much each feature shifted the model&apos;s prediction.
          </p>
        </div>
      ) : (
        <div className="rounded-lg border border-slate-700/30 bg-slate-800/20 px-4 py-2.5">
          <p className="text-[10px] text-slate-500">
            SHAP values will appear after the next retrain with a tree-based winner model.
          </p>
        </div>
      )}
      <div className="space-y-2">
        {detail.features_used
          .slice()
          .sort((a, b) => {
            if (!shap) return 0;
            return (shap[b.name] ?? 0) - (shap[a.name] ?? 0);
          })
          .map((feat) => (
            <ShapRow
              key={feat.name}
              name={feat.name}
              value={shap?.[feat.name] ?? 0}
              max={maxShap || 1}
              description={feat.description}
            />
          ))}
      </div>
    </div>
  );
}

function TrainingSection({ detail }: { detail: TimeframeModelDetail }) {
  const ti = detail.training_info;
  const totalRows = ti.total_rows ?? 0;
  const trainPct  = totalRows > 0 && ti.train_rows ? Math.round((ti.train_rows / totalRows) * 100) : 80;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {[
          { label: "Total rows",      value: ti.total_rows?.toLocaleString() ?? "—" },
          { label: "Train rows",      value: ti.train_rows?.toLocaleString() ?? "—" },
          { label: "Val rows",        value: ti.val_rows?.toLocaleString() ?? "—" },
          { label: "Horizon",         value: ti.horizon_periods ? `${ti.horizon_periods} periods` : "—" },
          { label: "Target UP %",     value: ti.target_balance_up_pct != null ? `${ti.target_balance_up_pct.toFixed(1)}%` : "—" },
          { label: "Trained at",      value: ti.trained_at ? new Date(ti.trained_at).toLocaleDateString("en-DE") : "—" },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-xl border border-slate-700/50 bg-slate-800/30 px-4 py-3">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-0.5">{label}</p>
            <p className="text-sm font-bold text-slate-200 tabular-nums">{value}</p>
          </div>
        ))}
      </div>

      {/* Train/val split bar */}
      <div className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-4 space-y-3">
        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Chronological Data Split</p>
        <div className="flex h-6 rounded-xl overflow-hidden gap-0.5">
          <div className="bg-sky-600/60 flex items-center justify-center" style={{ width: `${trainPct}%` }}>
            <span className="text-[10px] font-bold text-sky-100">Train {trainPct}%</span>
          </div>
          <div className="bg-violet-600/60 flex-1 flex items-center justify-center">
            <span className="text-[10px] font-bold text-violet-100">Val {100 - trainPct}%</span>
          </div>
        </div>
        <p className="text-[10px] text-slate-600 leading-relaxed">
          Strictly chronological — no shuffling, no data leakage. The model never sees future data during training.
          Walk-forward splits would be ideal but are reserved for Sprint 7 (requires more data).
        </p>
      </div>

      {/* MLflow run */}
      {ti.mlflow_run_id && (
        <div className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-4 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">MLflow Run</p>
            <a
              href={`http://localhost:5000/#/experiments/1/runs/${ti.mlflow_run_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-[10px] text-sky-400 hover:text-sky-300 transition-colors"
            >
              <ExternalLink className="h-3 w-3" />
              Open in MLflow
            </a>
          </div>
          <code className="block text-[10px] font-mono text-sky-300 bg-slate-900 px-3 py-2 rounded-lg break-all">
            {ti.mlflow_run_id}
          </code>
          <p className="text-[10px] text-slate-600">
            Start the MLflow UI: <code className="text-slate-500">start_mlflow.bat</code> → http://localhost:5000
          </p>
        </div>
      )}
    </div>
  );
}

function AllModelsSection({ detail }: { detail: TimeframeModelDetail }) {
  const modelOrder = ["ensemble", "xgboost", "lightgbm", "logistic", "prophet"];
  const entries = Object.entries(detail.all_models).sort(([a], [b]) => {
    const ai = modelOrder.indexOf(a), bi = modelOrder.indexOf(b);
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });

  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-500 leading-relaxed">
        All models compete on the same chronological validation set. Winner is selected by highest
        Sharpe ratio that passes both the accuracy ≥ 50% and Sharpe ≥ 0 quality gates.
      </p>
      <div className="space-y-3">
        {entries.map(([name, m]) => {
          const isWinner = name === detail.winner_model;
          return (
            <div key={name} className={`rounded-xl border p-4 space-y-4 ${
              isWinner       ? "border-amber-700/50 bg-amber-950/15" :
              m.disqualified ? "border-slate-700/30 bg-slate-800/10 opacity-50" :
                               "border-slate-700/50 bg-slate-800/20"
            }`}>
              <div className="flex items-center gap-2 flex-wrap">
                {modelBadge(name)}
                {isWinner && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-900/50 text-amber-300 border border-amber-700/50">
                    ✓ Winner
                  </span>
                )}
                {m.disqualified && (
                  <span className="text-[10px] text-slate-500 ml-auto">
                    ✗ Disqualified{m.reason ? `: ${m.reason}` : ""}
                  </span>
                )}
              </div>
              {!m.disqualified && (
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { l: "Sharpe",       v: m.sharpe.toFixed(3),               c: sharpeColor(m.sharpe) },
                    { l: "Accuracy",     v: `${(m.accuracy * 100).toFixed(1)}%`, c: accColor(m.accuracy) },
                    { l: "Val return",   v: `${m.total_return >= 0 ? "+" : ""}${(m.total_return * 100).toFixed(1)}%`,
                                         c: m.total_return >= 0 ? "text-emerald-400" : "text-rose-400" },
                  ].map(({ l, v, c }) => (
                    <div key={l} className="rounded-lg bg-slate-800/40 px-3 py-2">
                      <p className="text-[10px] text-slate-600 mb-0.5">{l}</p>
                      <p className={`text-sm font-black tabular-nums ${c}`}>{v}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div className="rounded-lg bg-slate-800/20 border border-slate-700/30 px-4 py-3">
        <p className="text-[10px] text-slate-500 leading-relaxed">
          <span className="text-amber-400 font-medium">Ensemble</span> blends Logistic + XGBoost + LightGBM
          probabilities weighted by their Sharpe ratios — it frequently wins by cancelling individual errors.
          <span className="text-rose-400 font-medium ml-1">Prophet</span> was removed from competition
          as it consistently returned near-zero accuracy on directional classification tasks.
        </p>
      </div>
    </div>
  );
}

function HistorySection({
  symbol, tf,
}: { symbol: string; tf: string }) {
  const { data, isLoading } = useSWR(
    `prediction-history-${symbol}-${tf}`,
    () => fetchPredictionHistory(symbol, tf),
    { revalidateOnFocus: false, shouldRetryOnError: false },
  );

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-xs text-slate-500 py-4">
        <div className="h-3 w-3 rounded-full border-2 border-slate-600 border-t-sky-500 animate-spin" />
        Loading prediction history…
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="rounded-xl border border-slate-700/40 bg-slate-800/20 px-4 py-8 text-center space-y-2">
        <p className="text-sm font-semibold text-slate-300">No resolved predictions yet</p>
        <p className="text-xs text-slate-500">
          Predictions start resolving after the horizon period passes
          ({tf === "1h" ? "~3 hours" : tf === "4h" ? "~12 hours" : tf === "1d" ? "~3 days" : tf === "1wk" ? "~2 weeks" : "~1 month"}).
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-[10px] text-slate-500">
        Last {data.length} resolved predictions for {symbol}/{tf}, newest first.
      </p>
      <div className="rounded-xl border border-slate-700/40 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-700/50 text-slate-500">
                <th className="text-left px-4 py-2.5 font-medium">Date</th>
                <th className="text-left px-3 py-2.5 font-medium">Predicted</th>
                <th className="text-right px-3 py-2.5 font-medium">Conf.</th>
                <th className="text-right px-3 py-2.5 font-medium">Entry</th>
                <th className="text-right px-3 py-2.5 font-medium">Exit</th>
                <th className="text-right px-3 py-2.5 font-medium">Return</th>
                <th className="text-center px-4 py-2.5 font-medium">Result</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row, i) => (
                <tr key={i} className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/20">
                  <td className="px-4 py-2 text-slate-400 whitespace-nowrap">
                    {new Date(row.predicted_at).toLocaleDateString("en-DE", { month: "short", day: "2-digit" })}
                  </td>
                  <td className="px-3 py-2">
                    <span className={`font-bold ${row.predicted_direction === 1 ? "text-emerald-400" : "text-rose-400"}`}>
                      {row.predicted_direction === 1 ? "▲ UP" : "▼ DOWN"}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right text-slate-400 tabular-nums">
                    {(row.confidence * 100).toFixed(0)}%
                  </td>
                  <td className="px-3 py-2 text-right text-slate-400 tabular-nums font-mono">
                    {row.price_at_prediction != null ? row.price_at_prediction.toFixed(2) : "—"}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-400 tabular-nums font-mono">
                    {row.price_at_outcome != null ? row.price_at_outcome.toFixed(2) : "—"}
                  </td>
                  <td className={`px-3 py-2 text-right font-bold tabular-nums ${
                    row.actual_return == null ? "text-slate-600" :
                    row.actual_return >= 0    ? "text-emerald-400" : "text-rose-400"
                  }`}>
                    {row.actual_return != null
                      ? `${row.actual_return >= 0 ? "+" : ""}${(row.actual_return * 100).toFixed(2)}%`
                      : "—"}
                  </td>
                  <td className="px-4 py-2 text-center">
                    {row.was_correct === true  && <span className="text-emerald-400 font-bold">✓</span>}
                    {row.was_correct === false && <span className="text-rose-400 font-bold">✗</span>}
                    {row.was_correct === null  && <span className="text-slate-600">?</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function DriftSection({
  symbol, tf,
}: { symbol: string; tf: string }) {
  const { data, isLoading } = useSWR(
    `drift-alerts-${symbol}`,
    () => fetchDriftAlerts(symbol),
    { revalidateOnFocus: false, shouldRetryOnError: false },
  );

  const tfAlerts = data?.filter(a => a.timeframe === tf) ?? [];

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-xs text-slate-500 py-4">
        <div className="h-3 w-3 rounded-full border-2 border-slate-600 border-t-sky-500 animate-spin" />
        Checking drift status…
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-700/40 bg-slate-800/20 px-4 py-3 space-y-1">
        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">What is model drift?</p>
        <p className="text-xs text-slate-500 leading-relaxed">
          A model is considered drifted when its live 30-day accuracy drops more than 10 percentage
          points below its validation accuracy. This typically indicates a market regime shift
          that the model was not trained on. The fix is to retrain with more recent data.
        </p>
      </div>

      {tfAlerts.length === 0 ? (
        <div className="rounded-xl border border-emerald-800/30 bg-emerald-950/15 px-4 py-4 flex items-center gap-3">
          <span className="text-xl">✅</span>
          <div>
            <p className="text-xs font-semibold text-emerald-300">No drift detected for {symbol}/{tf}</p>
            <p className="text-[10px] text-slate-500 mt-0.5">
              Live accuracy is within acceptable bounds of validation accuracy.
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {tfAlerts.map((alert) => (
            <div key={alert.id} className={`rounded-xl border p-4 space-y-3 ${
              alert.severity === "critical"
                ? "border-rose-700/50 bg-rose-950/20"
                : "border-amber-700/40 bg-amber-950/15"
            }`}>
              <div className="flex items-center gap-2 flex-wrap">
                <AlertTriangle className={`h-4 w-4 flex-shrink-0 ${alert.severity === "critical" ? "text-rose-400" : "text-amber-400"}`} />
                <span className={`text-xs font-bold ${alert.severity === "critical" ? "text-rose-300" : "text-amber-300"}`}>
                  {alert.severity === "critical" ? "Critical Drift" : "Drift Warning"}
                </span>
                {alert.acknowledged && (
                  <span className="text-[10px] text-slate-500 ml-auto">Acknowledged</span>
                )}
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div className="rounded-lg bg-slate-800/50 px-3 py-2">
                  <p className="text-[10px] text-slate-500 mb-0.5">Val accuracy</p>
                  <p className="text-sm font-bold text-slate-200 tabular-nums">{alert.val_accuracy_pct.toFixed(1)}%</p>
                </div>
                <div className="rounded-lg bg-slate-800/50 px-3 py-2">
                  <p className="text-[10px] text-slate-500 mb-0.5">Live accuracy</p>
                  <p className="text-sm font-bold text-rose-400 tabular-nums">{alert.live_accuracy_pct.toFixed(1)}%</p>
                </div>
                <div className="rounded-lg bg-slate-800/50 px-3 py-2">
                  <p className="text-[10px] text-slate-500 mb-0.5">Delta</p>
                  <p className="text-sm font-bold text-rose-400 tabular-nums">−{alert.delta_pp.toFixed(1)}pp</p>
                </div>
              </div>
              <p className="text-[10px] text-slate-500">
                Detected {new Date(alert.detected_at).toLocaleDateString("en-DE")} ·{" "}
                {alert.n_live_predictions} live predictions used ·{" "}
                {alert.auto_retrain ? "Auto-retrain triggered" : "Manual retrain recommended"}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Cross-timeframe accuracy chart ──────────────────────────────────────────

function CrossTfAccuracy({
  statsData,
}: { statsData: PredictionStatsResponse | undefined }) {
  if (!statsData?.available || !statsData.timeframes) return null;
  const tfs = TF_ORDER.filter(tf => statsData.timeframes![tf]);
  if (tfs.length === 0) return null;

  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-800/20 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Live Accuracy — All Timeframes</p>
        {statsData.model_health && (
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
            statsData.model_health === "good"     ? "text-emerald-400 bg-emerald-950/30 border-emerald-800/40" :
            statsData.model_health === "marginal" ? "text-amber-400 bg-amber-950/30 border-amber-800/40"     :
            statsData.model_health === "poor"     ? "text-rose-400 bg-rose-950/30 border-rose-800/40"         :
                                                    "text-slate-400 bg-slate-800/40 border-slate-700/40"
          }`}>
            {statsData.model_health === "insufficient_data" ? "Insufficient data" : statsData.model_health}
          </span>
        )}
      </div>
      <div className="space-y-2">
        {tfs.map(tf => {
          const s = statsData.timeframes![tf];
          const acc = s.live_accuracy;
          return (
            <div key={tf} className="flex items-center gap-3">
              <span className="text-[10px] font-mono font-bold text-slate-500 w-8 flex-shrink-0">{tf}</span>
              <div className="flex-1 h-2.5 rounded-full bg-slate-700 overflow-hidden">
                {acc != null ? (
                  <div
                    className={`h-full rounded-full transition-all duration-700 ${acc >= 0.55 ? "bg-emerald-500" : acc >= 0.5 ? "bg-amber-500" : "bg-rose-500"}`}
                    style={{ width: `${acc * 100}%` }}
                  />
                ) : <div className="h-full w-1/3 bg-slate-700 rounded-full animate-pulse" />}
              </div>
              <span className={`text-xs font-mono font-bold tabular-nums w-12 text-right ${acc != null ? accColor(acc) : "text-slate-600"}`}>
                {acc != null ? `${(acc * 100).toFixed(1)}%` : "n/a"}
              </span>
              <span className="text-[10px] text-slate-600 w-8 text-right tabular-nums">{s.total_resolved}</span>
              {s.trend && (
                <span className={`text-[10px] w-8 ${s.trend === "improving" ? "text-emerald-400" : s.trend === "degrading" ? "text-rose-400" : "text-slate-600"}`}>
                  {s.trend === "improving" ? "↑" : s.trend === "degrading" ? "↓" : "→"}
                </span>
              )}
            </div>
          );
        })}
      </div>
      <p className="text-[10px] text-slate-600">
        {statsData.total_resolved_all_tfs ?? 0} total resolved · accuracy bar is % correct ·
        arrow = 30-day vs overall trend
      </p>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ModelInfoPage({
  params,
}: {
  params: { symbol: string };
}) {
  const symbol = params.symbol.toUpperCase();

  const [activeTf, setActiveTf] = useState<string>("1d");
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  const {
    data: modelData,
    isLoading: modelLoading,
    mutate: mutateModel,
  } = useSWR(
    `model-details-${symbol}`,
    () => fetchModelDetails(symbol),
    { revalidateOnFocus: false, shouldRetryOnError: false },
  );

  const {
    data: statsData,
    isLoading: statsLoading,
  } = useSWR(
    `prediction-stats-${symbol}`,
    () => fetchPredictionStats(symbol),
    { revalidateOnFocus: false, shouldRetryOnError: false },
  );

  const isLoading = modelLoading || statsLoading;

  const availableTfs = modelData ? TF_ORDER.filter(tf => modelData.timeframes[tf]) : [];
  const currentTf    = availableTfs.includes(activeTf) ? activeTf : (availableTfs[0] ?? "1d");
  const detail       = modelData?.timeframes[currentTf];
  const tfStats      = statsData?.timeframes?.[currentTf];

  return (
    <div className="max-w-4xl mx-auto space-y-6">

      {/* ── Breadcrumb header ─────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 flex-wrap">
        <Link
          href="/"
          className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Dashboard
        </Link>
        <span className="text-slate-700">/</span>
        <span className="text-xs text-slate-500">Model Deep-Dive</span>
        <span className="text-slate-700">/</span>
        <span className="text-xs font-bold text-slate-200">{symbol}</span>
      </div>

      {/* ── Page title ────────────────────────────────────────────────────── */}
      <div className="space-y-1">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-black text-slate-100">
            ⚙ {symbol} — ML Model Details
          </h1>
          <button
            onClick={() => mutateModel()}
            title="Refresh"
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
        <p className="text-sm text-slate-400">
          Training metadata, feature importance, live accuracy, prediction history, and drift status.
        </p>
      </div>

      {/* ── Loading ───────────────────────────────────────────────────────── */}
      {isLoading && (
        <div className="flex items-center gap-3 py-12 justify-center text-slate-500 text-sm">
          <div className="h-4 w-4 rounded-full border-2 border-slate-600 border-t-sky-500 animate-spin" />
          Loading model data…
        </div>
      )}

      {/* ── No models ─────────────────────────────────────────────────────── */}
      {!isLoading && (!modelData || availableTfs.length === 0) && (
        <div className="rounded-2xl border border-slate-700/50 bg-slate-900/40 p-12 text-center space-y-4">
          <span className="text-5xl">🧠</span>
          <div>
            <p className="text-base font-bold text-slate-200">No trained models for {symbol}</p>
            <p className="text-sm text-slate-500 mt-1">
              Go to the dashboard and click the <strong className="text-slate-300">▶ Train Now</strong> button to train ML models.
            </p>
          </div>
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 hover:bg-blue-500 px-5 py-2.5 text-sm font-semibold text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Go to Dashboard
          </Link>
        </div>
      )}

      {/* ── Main content ──────────────────────────────────────────────────── */}
      {!isLoading && detail && (
        <div className="space-y-5">

          {/* Cross-timeframe accuracy chart — always visible */}
          <CrossTfAccuracy statsData={statsData} />

          {/* Timeframe selector */}
          {availableTfs.length > 1 && (
            <div className="flex gap-1 flex-wrap">
              {availableTfs.map(tf => (
                <button
                  key={tf}
                  onClick={() => setActiveTf(tf)}
                  className={`px-4 py-2 rounded-xl text-xs font-bold transition-colors ${
                    currentTf === tf
                      ? "bg-slate-700 text-slate-100 border border-slate-600"
                      : "text-slate-500 hover:text-slate-300 hover:bg-slate-800/60 border border-transparent"
                  }`}
                >
                  {TF_LABELS[tf] ?? tf}
                </button>
              ))}
            </div>
          )}

          {/* Tab bar */}
          <div className="flex border-b border-slate-800 overflow-x-auto">
            {ALL_TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 whitespace-nowrap pb-3 px-3 mr-2 text-xs font-semibold border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? "border-sky-500 text-sky-400"
                    : "border-transparent text-slate-500 hover:text-slate-300"
                }`}
              >
                <span>{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="pb-8">
            {activeTab === "overview" && (
              <OverviewSection detail={detail} stats={tfStats} tf={currentTf} />
            )}
            {activeTab === "features" && (
              <FeaturesSection detail={detail} />
            )}
            {activeTab === "training" && (
              <TrainingSection detail={detail} />
            )}
            {activeTab === "models" && (
              <AllModelsSection detail={detail} />
            )}
            {activeTab === "history" && (
              <HistorySection symbol={symbol} tf={currentTf} />
            )}
            {activeTab === "drift" && (
              <DriftSection symbol={symbol} tf={currentTf} />
            )}
          </div>

          {/* Note */}
          {modelData.note && (
            <p className="text-[10px] text-slate-600 border-t border-slate-800/50 pt-4">
              {modelData.note}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Fetch helpers (thin wrappers for page-only data) ─────────────────────────

async function fetchPredictionHistory(symbol: string, timeframe: string) {
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const res = await fetch(
    `${API_BASE_URL}/api/v1/technical/${encodeURIComponent(symbol)}/prediction-history?timeframe=${encodeURIComponent(timeframe)}&limit=30`,
    { cache: "no-store" },
  );
  if (!res.ok) return [];
  return res.json() as Promise<PredictionHistoryRow[]>;
}

interface PredictionHistoryRow {
  predicted_at:        string;
  predicted_direction: number;
  confidence:          number;
  price_at_prediction: number | null;
  price_at_outcome:    number | null;
  actual_return:       number | null;
  was_correct:         boolean | null;
}
