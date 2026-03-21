/**
 * lib/api_model_details.ts
 *
 * Types and fetch functions for the Model Details panel (todos-v5 Sprint 4).
 * Sources: GET /api/v1/technical/{symbol}/model-details
 *          GET /api/v1/technical/{symbol}/prediction-stats
 */

const DEFAULT_BASE_URL = "http://localhost:8000";
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_BASE_URL;

// ── Model details ─────────────────────────────────────────────────────────────

export interface FeatureEntry {
  name:        string;
  description: string;
}

export interface ModelResult {
  accuracy:     number;
  sharpe:       number;
  total_return: number;
  disqualified: boolean;
  reason?:      string | null;
}

export interface TrainingInfo {
  trained_at?:            string | null;
  train_rows?:            number | null;
  val_rows?:              number | null;
  total_rows?:            number | null;
  horizon_periods?:       number | null;
  target_balance_up_pct?: number | null;
  quality_gate_passed?:   boolean;
  mlflow_run_id?:         string | null;
}

export interface TimeframeModelDetail {
  winner_model:         string;
  all_models:           Record<string, ModelResult>;
  features_used:        FeatureEntry[];
  training_info:        TrainingInfo;
  how_target_was_built: string;
  how_sharpe_was_built: string;
}

export interface ModelDetailsResponse {
  symbol:     string;
  timeframes: Record<string, TimeframeModelDetail>;
  note?:      string;
  // SHAP importance stored at the registry level — may be inside extra_metrics
  shap_importance?: Record<string, number> | null;
}

// ── Prediction stats ──────────────────────────────────────────────────────────

export interface TimeframePredictionStats {
  total_resolved:       number;
  correct:              number;
  live_accuracy:        number | null;
  avg_return_correct:   number | null;
  avg_return_wrong:     number | null;
  recent_30d_accuracy:  number | null;
  trend:                "improving" | "degrading" | "stable" | null;
  by_regime?:           Record<string, { accuracy: number | null; n: number }>;
}

export interface PredictionStatsResponse {
  symbol:                      string;
  available:                   boolean;
  message?:                    string;
  total_resolved_all_tfs?:     number;
  timeframes?:                 Record<string, TimeframePredictionStats>;
  best_performing_timeframe?:  string | null;
  model_health?:               "good" | "marginal" | "poor" | "insufficient_data";
}

// ── Fetch functions ───────────────────────────────────────────────────────────

export async function fetchModelDetails(symbol: string): Promise<ModelDetailsResponse> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/technical/${encodeURIComponent(symbol.toUpperCase())}/model-details`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error(`Failed to load model details for ${symbol}: ${res.status}`);
  return res.json() as Promise<ModelDetailsResponse>;
}

export async function fetchPredictionStats(symbol: string): Promise<PredictionStatsResponse> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/technical/${encodeURIComponent(symbol.toUpperCase())}/prediction-stats`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error(`Failed to load prediction stats for ${symbol}: ${res.status}`);
  return res.json() as Promise<PredictionStatsResponse>;
}
