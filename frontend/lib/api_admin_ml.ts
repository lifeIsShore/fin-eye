/**
 * lib/api_admin_ml.ts
 *
 * Types and fetch functions for the Sprint 6 admin ML endpoints.
 * Sources:
 *   GET /api/v1/admin/ml/drift-report?symbol=X  (filtered by symbol on frontend)
 *   GET /api/v1/admin/ml/optuna-params/{symbol}/{timeframe}/{model}
 *
 * Used by the /model-info/[symbol] deep-dive page.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function authHeaders(): HeadersInit {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

// ─── Drift alerts ─────────────────────────────────────────────────────────────

export interface DriftAlertDto {
  id:                   number;
  symbol:               string;
  timeframe:            string;
  val_accuracy_pct:     number;
  live_accuracy_pct:    number;
  delta_pp:             number;
  n_live_predictions:   number;
  severity:             "warning" | "critical";
  auto_retrain:         boolean;
  retrained_at:         string | null;
  acknowledged:         boolean;
  detected_at:          string;
  resolved_at:          string | null;
}

/**
 * Fetch all drift alerts — optionally filtered to a specific symbol
 * (filtering is done client-side since the backend returns all alerts).
 * Only fetches unacknowledged by default to keep the list actionable.
 */
export async function fetchDriftAlerts(
  symbol?: string,
  unackedOnly = false,
): Promise<DriftAlertDto[]> {
  const qs = unackedOnly ? "?unacked_only=true" : "";
  const res = await fetch(`${API_BASE_URL}/api/v1/admin/ml/drift-report${qs}`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) {
    // Non-admin users get 403 — return empty instead of throwing
    if (res.status === 403 || res.status === 401) return [];
    throw new Error(`Failed to fetch drift alerts: ${res.status}`);
  }
  const all: DriftAlertDto[] = await res.json();
  return symbol ? all.filter(a => a.symbol === symbol.toUpperCase()) : all;
}

export async function acknowledgeDriftAlert(alertId: number): Promise<boolean> {
  const res = await fetch(`${API_BASE_URL}/api/v1/admin/ml/drift-report/${alertId}/ack`, {
    method: "POST",
    headers: authHeaders(),
  });
  return res.ok;
}

export interface DriftSummaryDto {
  total_alerts:   number;
  unacked_alerts: number;
  critical_alerts: number;
  all_clear:       boolean;
}

export async function fetchDriftSummary(): Promise<DriftSummaryDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/admin/ml/drift-summary`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) {
    if (res.status === 403 || res.status === 401) {
      return { total_alerts: 0, unacked_alerts: 0, critical_alerts: 0, all_clear: true };
    }
    throw new Error(`Failed to fetch drift summary: ${res.status}`);
  }
  return res.json();
}

// ─── Optuna params ────────────────────────────────────────────────────────────

export interface OptunaParamsDto {
  symbol:      string;
  timeframe:   string;
  model:       string;
  best_params: Record<string, number | string | boolean>;
}

export async function fetchOptunaParams(
  symbol: string,
  timeframe: string,
  model: "xgboost" | "lightgbm",
): Promise<OptunaParamsDto | null> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/admin/ml/optuna-params/${encodeURIComponent(symbol.toUpperCase())}/${encodeURIComponent(timeframe)}/${model}`,
    { headers: authHeaders(), cache: "no-store" },
  );
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to fetch Optuna params: ${res.status}`);
  return res.json();
}
