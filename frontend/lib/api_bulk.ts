/**
 * lib/api_bulk.ts
 * Admin bulk pipeline API calls (todos-v4.md Phases 3–8).
 * Separate from api.ts to keep the main file from growing unbounded.
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function authHeaders(): HeadersInit {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

// ─── Ticker Universe ──────────────────────────────────────────────────────────

export interface TickerUniverseItem {
  symbol:      string;
  name:        string | null;
  asset_class: string | null;
  tr_rank:     number | null;
  exchange:    string | null;
  yf_valid:    boolean | null;
  is_active:   boolean;
}

export interface TickerUniverseListDto {
  total:     number;
  page:      number;
  page_size: number;
  tickers:   TickerUniverseItem[];
}

export async function fetchTickerUniverse(
  page = 1,
  pageSize = 50,
  assetClass?: string,
): Promise<TickerUniverseListDto> {
  const q = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (assetClass) q.set("asset_class", assetClass);
  const res = await fetch(`${API_BASE_URL}/api/v1/admin/tickers-universe?${q}`, {
    headers: authHeaders(), cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to load ticker universe");
  return res.json();
}

// ─── Single-symbol seed & status ─────────────────────────────────────────────

export interface SingleSeedStatusDto {
  symbol:       string;
  status:       string;
  reason:       string | null;
  rows_added:   number;
  completed_at: string | null;
}

export async function seedSingleSymbol(symbol: string): Promise<{ status: string }> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/admin/seed/${encodeURIComponent(symbol.toUpperCase())}`,
    { method: "POST", headers: authHeaders() },
  );
  if (!res.ok) throw new Error(`Failed to seed ${symbol}`);
  return res.json();
}

export async function fetchSeedStatusSymbol(symbol: string): Promise<SingleSeedStatusDto> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/admin/seed-status/${encodeURIComponent(symbol.toUpperCase())}`,
    { headers: authHeaders(), cache: "no-store" },
  );
  if (!res.ok) throw new Error(`Failed to fetch seed status for ${symbol}`);
  return res.json();
}

// ─── Bulk seed ────────────────────────────────────────────────────────────────

export interface BulkSeedStatusDto {
  total:        number;
  done:         number;
  failed:       number;
  skipped:      number;
  running:      boolean;
  pct_complete: number;
  started_at:   string | null;
  recent: Array<{
    symbol:     string;
    status:     string;
    reason:     string | null;
    rows_added: number;
  }>;
  db_totals: Record<string, number>;
}

export async function triggerBulkSeed(
  scope: "missing_only" | "all" = "missing_only",
): Promise<{ status: string; total_tickers: number; message: string }> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/admin/bulk/run-seed?scope=${scope}`,
    { method: "POST", headers: authHeaders() },
  );
  if (!res.ok) throw new Error("Failed to start bulk seed");
  return res.json();
}

export async function fetchBulkSeedStatus(): Promise<BulkSeedStatusDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/admin/bulk/seed-status`, {
    headers: authHeaders(), cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch seed status");
  return res.json();
}

// ─── Bulk train ───────────────────────────────────────────────────────────────

export interface BulkTrainStatusDto {
  total:             number;
  done:              number;
  failed:            number;
  running:           boolean;
  pct_complete:      number;
  current_symbol:    string | null;
  current_timeframe: string | null;
  avg_sharpe:        number | null;
  started_at:        string | null;
  recent: Array<{
    symbol:     string;
    timeframe?: string;
    sharpe?:    number;
    status:     string;
    reason?:    string;
  }>;
}

export async function triggerBulkTrain(
  scope: "untrained_only" | "retrain_all" = "untrained_only",
): Promise<{ status: string; total_tickers: number; message: string }> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/admin/bulk/run-train?scope=${scope}`,
    { method: "POST", headers: authHeaders() },
  );
  if (!res.ok) throw new Error("Failed to start bulk training");
  return res.json();
}

export async function fetchBulkTrainStatus(): Promise<BulkTrainStatusDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/admin/bulk/train-status`, {
    headers: authHeaders(), cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch train status");
  return res.json();
}

// ─── Bulk news ────────────────────────────────────────────────────────────────

export interface BulkNewsStatusDto {
  total:        number;
  done:         number;
  failed:       number;
  running:      boolean;
  pct_complete: number;
  recent: Array<{
    symbol:    string;
    articles?: number;
    status:    string;
    reason?:   string;
  }>;
}

export async function triggerBulkNewsSeed(lookbackDays = 7): Promise<{ status: string }> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/admin/bulk/run-news-seed?lookback_days=${lookbackDays}`,
    { method: "POST", headers: authHeaders() },
  );
  if (!res.ok) throw new Error("Failed to start news seed");
  return res.json();
}

export async function fetchBulkNewsStatus(): Promise<BulkNewsStatusDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/admin/bulk/news-status`, {
    headers: authHeaders(), cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch news status");
  return res.json();
}

// ─── Pipeline overview ────────────────────────────────────────────────────────

export interface PipelineOverviewDto {
  ticker_universe: {
    total:    number;
    yf_valid: number;
    by_class: Record<string, number>;
  };
  seeding: {
    seeded:          number;
    failed:          number;
    skipped:         number;
    missing:         number;
    last_run_at:     string | null;
    failed_tickers:  Array<{ symbol: string; reason: string | null }>;
    skipped_tickers: Array<{ symbol: string; reason: string | null }>;
  };
  training: {
    trained:          number;
    failed:           number;
    untrained:        number;
    avg_sharpe:       number | null;
    quality_gate_pct: number;
    last_run_at:      string | null;
  };
  news: {
    total_articles: number;
    oldest_article: string | null;
    last_fetch_at:  string | null;
  };
  active_jobs: {
    seeding:  boolean;
    training: boolean;
    news:     boolean;
  };
}

export async function fetchPipelineOverview(): Promise<PipelineOverviewDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/admin/bulk/pipeline-overview`, {
    headers: authHeaders(), cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch pipeline overview");
  return res.json();
}

// ─── Per-ticker data status ───────────────────────────────────────────────────

export interface TickerStatusDto {
  symbol: string;
  ohlcv: {
    daily_bars:  number;
    hourly_bars: number;
    last_date:   string | null;
    first_date:  string | null;
    is_seeded:   boolean;
  };
  training: {
    status:             "trained" | "not_started" | "no_artifacts";
    timeframes_trained: number;
    best_sharpe:        number | null;
    best_model:         string | null;
    trained_at:         string | null;
    timeframes: Array<{
      timeframe:  string;
      model:      string;
      sharpe:     number | null;
      trained_at: string | null;
    }>;
  };
  news: {
    article_count:   number;
    oldest:          string | null;
    newest:          string | null;
    last_fetched_at: string | null;
  };
}

export async function fetchTickerStatus(symbol: string): Promise<TickerStatusDto> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/admin/ticker-status/${encodeURIComponent(symbol.toUpperCase())}`,
    { headers: authHeaders(), cache: "no-store" },
  );
  if (!res.ok) throw new Error(`Failed to fetch ticker status for ${symbol}`);
  return res.json();
}

// ─── Train status + trigger (wires into technical.py endpoints) ──────────────

export interface TrainStatusDto {
  symbol:          string;
  status:          "trained" | "not_started" | "no_artifacts";
  timeframes: Array<{
    timeframe:    string;
    model:        string;
    sharpe:       number | null;
    trained_at:   string | null;
    quality_gate: boolean;
  }>;
  last_trained_at: string | null;
  model_metrics:   { best_sharpe: number | null; timeframes_count: number };
}

export async function fetchTrainStatus(symbol: string): Promise<TrainStatusDto> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/technical/train-status/${encodeURIComponent(symbol.toUpperCase())}`,
    { headers: authHeaders(), cache: "no-store" },
  );
  if (!res.ok) throw new Error(`Failed to fetch train status for ${symbol}`);
  return res.json();
}

export async function triggerTrainSymbol(
  symbol: string,
  force = false,
): Promise<{
  message: string;
  symbol: string;
  timeframes_queued: string[];
  status: string;
  estimated_seconds: number;
}> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/technical/train/${encodeURIComponent(symbol.toUpperCase())}?force=${force}`,
    { method: "POST", headers: authHeaders() },
  );
  if (!res.ok) throw new Error(`Failed to trigger training for ${symbol}`);
  return res.json();
}
