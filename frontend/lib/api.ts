const DEFAULT_BASE_URL = "http://localhost:8000";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_BASE_URL;

export interface SentimentAggregatePoint {
  date: string;
  sentiment_score: number;
  mentions: number;
}

export interface NewsArticleDto {
  symbol: string;
  title: string;
  sentiment_score: number | null;
  source: string | null;
  published_at: string;
}

export interface SentimentTimeseriesDto {
  symbol: string;
  series: SentimentAggregatePoint[];
  sentiment_1d: number | null;
  sentiment_7d: number | null;
  sentiment_30d: number | null;
  articles: NewsArticleDto[];
}

export interface SentimentSourceBreakdownEntryDto {
  source: string;
  positive: number;
  negative: number;
  neutral: number;
}

export interface SentimentSourceBreakdownDto {
  symbol: string;
  days: number;
  breakdown: SentimentSourceBreakdownEntryDto[];
}

export interface MacroIndicatorDto {
  value: number | null;
  date: string | null;
  interpretation: string;
}

// ── Advanced Macro (P2-MACRO-ADV-01) ────────────────────────────────────────

export interface YieldCurvePoint {
  tenor: string;
  tenor_years: number;
  yield_pct: number | null;
  date: string | null;
}

export interface YieldCurveDto {
  points: YieldCurvePoint[];
  shape: "Normal" | "Flat" | "Inverted" | "Steep" | "Humped" | "Unavailable";
  shape_description: string;
  spread_10y_2y: number | null;
  spread_30y_2y: number | null;
}

export interface StressComponentDto {
  name: string;
  contribution: number;
  description: string;
}

export interface MacroStressIndexDto {
  index: number;
  label: "Low Stress" | "Moderate" | "Elevated" | "High Stress";
  components: StressComponentDto[];
}

export interface RecessionDto {
  probability_pct: number;
  label: "Low" | "Elevated" | "High";
  nber_in_recession: boolean;
  drivers: string[];
}

export interface LeadingIndicatorsDto {
  nonfarm_payrolls_latest: number | null;
  nonfarm_payrolls_mom: number | null;
  industrial_production_latest: number | null;
  industrial_production_yoy: number | null;
}

export interface MacroAdvancedDto {
  core: MacroLatestDto;
  yield_curve: YieldCurveDto;
  recession: RecessionDto;
  stress_index: MacroStressIndexDto;
  leading_indicators: LeadingIndicatorsDto;
}

export interface IndicatorHistoryDto {
  indicator_name: string;
  series: { date: string; value: number }[];
  count: number;
}

export interface MacroLatestDto {
  data: {
    fed_funds_rate: MacroIndicatorDto;
    unemployment_rate: MacroIndicatorDto;
    yield_spread_10y_2y: MacroIndicatorDto;
    cpi_yoy: MacroIndicatorDto;
    vix: MacroIndicatorDto;
    [key: string]: MacroIndicatorDto;
  };
  macro_score: {
    score: number;
    label: "Supportive" | "Neutral" | "Stressed";
  } | null;
}

export async function fetchNewsSentiment(
  symbol: string,
  init?: RequestInit,
): Promise<SentimentTimeseriesDto> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/sentiment/${encodeURIComponent(
      symbol.toUpperCase(),
    )}/timeseries`,
    {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    },
  );

  if (!res.ok) {
    throw new Error(
      `Failed to load sentiment for ${symbol}: ${res.status} ${res.statusText}`,
    );
  }

  return (await res.json()) as SentimentTimeseriesDto;
}

export async function fetchSentimentSources(
  symbol: string,
  days = 30,
  init?: RequestInit,
): Promise<SentimentSourceBreakdownDto> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/sentiment/${encodeURIComponent(
      symbol.toUpperCase(),
    )}/sources?days=${encodeURIComponent(String(days))}`,
    {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    },
  );

  if (!res.ok) {
    throw new Error(
      `Failed to load sentiment sources for ${symbol}: ${res.status} ${res.statusText}`,
    );
  }

  return (await res.json()) as SentimentSourceBreakdownDto;
}

export async function fetchMacroAdvanced(
  init?: RequestInit,
): Promise<MacroAdvancedDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/macro/advanced`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to load advanced macro data: ${res.status}`);
  return res.json() as Promise<MacroAdvancedDto>;
}

export async function fetchMacroHistory(
  indicatorName: string,
  limit = 60,
  init?: RequestInit,
): Promise<IndicatorHistoryDto> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/macro/history/${encodeURIComponent(indicatorName)}?limit=${limit}`,
    { ...init, headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) }, cache: "no-store" },
  );
  if (!res.ok) throw new Error(`Failed to load history for ${indicatorName}: ${res.status}`);
  return res.json() as Promise<IndicatorHistoryDto>;
}

export async function fetchMacroLatest(
  init?: RequestInit,
): Promise<MacroLatestDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/macro/latest`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(
      `Failed to load macro dashboard data: ${res.status} ${res.statusText}`,
    );
  }

  return (await res.json()) as MacroLatestDto;
}

export interface TechnicalSignalDto {
  timeframe: string;
  direction: "Bullish" | "Neutral" | "Bearish";
  confidence: number;
  sharpe_weight: number;
}

export interface TechnicalConsensusDto {
  symbol: string;
  consensus: number;
  technical_confidence_score: number;
  summary: string;
  signals: TechnicalSignalDto[];
}

export async function fetchTechnicalLatest(
  symbol: string,
  init?: RequestInit,
): Promise<TechnicalConsensusDto> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/technical/${encodeURIComponent(
      symbol.toUpperCase(),
    )}/latest`,
    {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    },
  );

  if (!res.ok) {
    if (res.status === 404) {
      // It's possible for there to be no models trained yet.
      // We can return a default empty consensus or throw a specific error depending on how we want the UI to handle it.
      // We'll throw an error for now and let the SWR hook or UI catch it.
      throw new Error(`Technical models not trained or found for ${symbol}`);
    }
    throw new Error(
      `Failed to load technical consensus for ${symbol}: ${res.status} ${res.statusText}`,
    );
  }

  return (await res.json()) as TechnicalConsensusDto;
}

// ─── Hedging ────────────────────────────────────────────────────────────────

export interface HedgePayoffScenario {
  return_pct: number;
  unhedged: number;
  hedged: number;
}

export interface HedgeAnalysisDto {
  symbol: string;
  hedge_type: string;
  portfolio_value: number;
  period: string;
  correlation: {
    symbol: string;
    period: string;
    correlations: Record<string, number>;
  };
  beta: {
    symbol: string;
    benchmark: string;
    beta: number;
    r_squared: number;
    data_points: number;
  };
  hedge_ratio: {
    hedge_units: number;
    notional: number;
  };
  payoff: {
    scenarios: HedgePayoffScenario[];
  };
  cost: {
    hedge_type: string;
    annual_cost_pct: number;
    annual_cost_usd: number;
    description: string;
  };
  disclaimer: string;
}

// ── Advanced Hedging (P2-HEDGE-ADV-01) ─────────────────────────────────────

export interface AdvHedgeStrategyDefinition {
  key: string;
  label: string;
  description: string;
  annual_cost_pct: number;
}

export interface AdvHedgeSummaryRow {
  strategy: string;
  label: string;
  description: string;
  total_return_pct: number;
  max_drawdown_pct: number;
  annual_cost_pct: number;
  annual_cost_usd: number;
}

export interface AdvHedgeEquityCurvePoint {
  date: string;
  value: number;
}

export interface AdvHedgePayoffRow {
  return_pct: number;
  unhedged?: number;
  protective_put?: number;
  collar?: number;
  stock_put_etf?: number;
  [key: string]: number | undefined;
}

export interface AdvancedHedgeDto {
  symbol: string;
  portfolio_value: number;
  period: string;
  beta: { symbol: string; benchmark: string; beta: number; r_squared: number; data_points: number };
  strategies: string[];
  strategy_definitions: AdvHedgeStrategyDefinition[];
  equity_curves: Record<string, AdvHedgeEquityCurvePoint[]>;
  summary: AdvHedgeSummaryRow[];
  payoff_comparison: AdvHedgePayoffRow[];
  disclaimer: string;
  error?: string;
}

export async function fetchAdvancedHedge(
  symbol: string,
  portfolioValue: number = 10000,
  period: string = "1y",
  strategies: string = "unhedged,protective_put,collar,stock_put_etf",
): Promise<AdvancedHedgeDto> {
  const params = new URLSearchParams({
    portfolio_value: portfolioValue.toString(),
    period,
    strategies,
  });
  const res = await fetch(
    `${API_BASE_URL}/api/v1/hedge/${symbol}/advanced?${params}`,
  );
  if (!res.ok) {
    throw new Error(`Failed to load advanced hedge analysis for ${symbol}: ${res.status}`);
  }
  return res.json() as Promise<AdvancedHedgeDto>;
}

export async function fetchHedgeAnalysis(
  symbol: string,
  hedgeType: string = "protective_put",
  portfolioValue: number = 10000,
  period: string = "1y",
): Promise<HedgeAnalysisDto> {
  const params = new URLSearchParams({
    hedge_type: hedgeType,
    portfolio_value: portfolioValue.toString(),
    period,
  });
  const res = await fetch(
    `${API_BASE_URL}/api/v1/hedge/${symbol}/analysis?${params}`,
  );
  if (!res.ok) {
    throw new Error(
      `Failed to load hedge analysis for ${symbol}: ${res.status} ${res.statusText}`,
    );
  }
  return (await res.json()) as HedgeAnalysisDto;
}

// ─── Backtesting ────────────────────────────────────────────────────────────

export interface BacktestRequest {
  symbol: string;
  strategy: string;
  start_date?: string;
  end_date?: string;
  parameters?: Record<string, any>;
  initial_capital?: number;
  slippage_pct?: number;
  commission_pct?: number;
}

export interface BacktestStats {
  total_return_pct: number;
  annualized_return_pct: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  win_rate_pct: number;
  profit_factor: number;
  total_trades: number;
  recovery_factor: number;
}

export interface EquityPoint {
  date: string;
  equity: number;
  benchmark_equity?: number | null;
}

export interface BacktestResponse {
  request: BacktestRequest;
  stats: BacktestStats;
  equity_curve: EquityPoint[];
  assumptions_applied?: string;
  overfitting_warning?: boolean;
}

export async function runBacktest(
  request: BacktestRequest,
): Promise<BacktestResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/backtest`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      `Failed to run backtest: ${errorData.detail || res.statusText}`,
    );
  }

  return (await res.json()) as BacktestResponse;
}

// ─── Retail Sentiment (Reddit) ──────────────────────────────────────────────

export interface SentimentComment {
  subreddit: string;
  timestamp: string;
  text: string;
  sentiment_score: number;
  sentiment_label: string;
  upvotes: number;
  url: string;
}

export interface SentimentSummary {
  total_mentions: number;
  percent_positive: number;
  percent_neutral: number;
  percent_negative: number;
  retail_sentiment_score: number;
}

export interface RetailSentimentResponse {
  ticker: string;
  summary: SentimentSummary;
  top_bullish: SentimentComment[];
  top_bearish: SentimentComment[];
}

export async function getRetailSentiment(
  ticker: string,
  init?: RequestInit,
): Promise<RetailSentimentResponse> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/sentiment/retail/${encodeURIComponent(
      ticker.toUpperCase(),
    )}`,
    {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    },
  );

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      `Failed to load retail sentiment for ${ticker}: ${errorData.detail || res.statusText
      }`,
    );
  }

  return (await res.json()) as RetailSentimentResponse;
}

// ─── Economic Calendar Events ────────────────────────────────────────────────

export interface MarketEvent {
  id: string;
  date: string;
  time?: string;
  title: string;
  description?: string;
  impact: "Low" | "Medium" | "High";
  country: string;
  actual?: string;
  estimate?: string;
  previous?: string;
}

export interface EventResponse {
  events: MarketEvent[];
}

export async function getUpcomingEvents(
  country?: string,
  impact?: string,
): Promise<EventResponse> {
  const params = new URLSearchParams();
  if (country) params.append("country", country);
  if (impact) params.append("impact", impact);

  const query = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(`${API_BASE_URL}/api/v1/events/upcoming${query}`, {
    method: "GET",
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(`Failed to fetch events: ${errorData.detail || res.statusText}`);
  }

  return (await res.json()) as EventResponse;
}

// ─── Watchlist ──────────────────────────────────────────────────────────────

export interface WatchlistItem {
  id: number;
  symbol: string;
  added_at: string;
}

function authHeaders(): HeadersInit {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export async function fetchWatchlist(): Promise<WatchlistItem[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/watchlist/`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to load watchlist");
  return (await res.json()) as WatchlistItem[];
}

export async function addToWatchlist(symbol: string): Promise<WatchlistItem> {
  const res = await fetch(`${API_BASE_URL}/api/v1/watchlist/`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ symbol }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to add to watchlist");
  }
  return (await res.json()) as WatchlistItem;
}

export async function removeFromWatchlist(symbol: string): Promise<void> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/watchlist/${encodeURIComponent(symbol)}`,
    { method: "DELETE", headers: authHeaders() },
  );
  if (!res.ok && res.status !== 404) {
    throw new Error("Failed to remove from watchlist");
  }
}

// ─── Legal Consent ─────────────────────────────────────────────────────────

export interface ConsentStatus {
  has_accepted: boolean;
  current_version: string;
  accepted_version: string | null;
  accepted_at: string | null;
}

export async function fetchConsentStatus(): Promise<ConsentStatus> {
  const res = await fetch(`${API_BASE_URL}/api/v1/legal/consent/status`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch consent status");
  return (await res.json()) as ConsentStatus;
}

export async function recordConsent(): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/v1/legal/consent`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to record consent");
}

// ─── GDPR ────────────────────────────────────────────────────────────────

/**
 * Fetch the user's personal data export package and trigger a browser download.
 * Returns true on success, throws on error.
 */
export async function downloadDataExport(): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/v1/gdpr/export`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to generate data export.");

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "fin-eye-data-export.json";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ─── CMS / Blog ─────────────────────────────────────────────────────────────

export interface BlogPostSummary {
  id: number;
  title: string;
  slug: string;
  summary: string;
  category: string;
  read_time: string;
  author: string;
  status: string;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface BlogPostFull extends BlogPostSummary {
  content_md: string;
}

export interface BlogPostCreatePayload {
  title: string;
  summary: string;
  category?: string;
  read_time?: string;
  author?: string;
  content_md?: string;
  slug?: string;
}

export interface BlogPostUpdatePayload {
  title?: string;
  summary?: string;
  category?: string;
  read_time?: string;
  author?: string;
  content_md?: string;
  slug?: string;
}

export async function fetchPublishedPosts(): Promise<BlogPostSummary[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/cms/posts/published`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to load blog posts");
  return res.json();
}

export async function fetchPostBySlug(slug: string): Promise<BlogPostFull> {
  const res = await fetch(`${API_BASE_URL}/api/v1/cms/posts/by-slug/${encodeURIComponent(slug)}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Post '${slug}' not found`);
  return res.json();
}

// ─── CMS Admin ────────────────────────────────────────────────────────────

export async function adminFetchAllPosts(): Promise<BlogPostSummary[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/cms/posts`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to load posts");
  return res.json();
}

export async function adminFetchPost(id: number): Promise<BlogPostFull> {
  const res = await fetch(`${API_BASE_URL}/api/v1/cms/posts/${id}`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Post not found");
  return res.json();
}

export async function adminCreatePost(payload: BlogPostCreatePayload): Promise<BlogPostFull> {
  const res = await fetch(`${API_BASE_URL}/api/v1/cms/posts`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to create post");
  }
  return res.json();
}

export async function adminUpdatePost(id: number, payload: BlogPostUpdatePayload): Promise<BlogPostFull> {
  const res = await fetch(`${API_BASE_URL}/api/v1/cms/posts/${id}`, {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to update post");
  }
  return res.json();
}

export async function adminPublishPost(id: number): Promise<BlogPostFull> {
  const res = await fetch(`${API_BASE_URL}/api/v1/cms/posts/${id}/publish`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to publish post");
  return res.json();
}

export async function adminUnpublishPost(id: number): Promise<BlogPostFull> {
  const res = await fetch(`${API_BASE_URL}/api/v1/cms/posts/${id}/unpublish`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to unpublish post");
  return res.json();
}

export async function adminDeletePost(id: number): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/v1/cms/posts/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok && res.status !== 404) throw new Error("Failed to delete post");
}

// ── Alerts ────────────────────────────────────────────────────────────────────

export interface AlertDto {
  id: number;
  symbol: string;
  alert_type: "price_above" | "price_below" | "gas_above" | "gas_below";
  threshold: number;
  delivery_channel: string;
  is_active: boolean;
  triggered_at: string | null;
  triggered_value: number | null;
  created_at: string;
}

export interface AlertListDto {
  alerts: AlertDto[];
  total: number;
}

export interface TriggeredAlertDto {
  id: number;
  symbol: string;
  alert_type: string;
  threshold: number;
  triggered_value: number;
  triggered_at: string;
  message: string;
}

export interface AlertCreatePayload {
  symbol: string;
  alert_type: string;
  threshold: number;
  delivery_channel?: string;
}

export async function fetchAlerts(activeOnly = false): Promise<AlertListDto> {
  const qs = activeOnly ? "?active_only=true" : "";
  const res = await fetch(`${API_BASE_URL}/api/v1/alerts${qs}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch alerts");
  return res.json();
}

export async function createAlert(payload: AlertCreatePayload): Promise<AlertDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/alerts`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to create alert");
  return res.json();
}

export async function deleteAlert(id: number): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/v1/alerts/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok && res.status !== 404) throw new Error("Failed to delete alert");
}

export async function fetchTriggeredAlerts(): Promise<TriggeredAlertDto[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/alerts/triggered`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch triggered alerts");
  return res.json();
}

// ── Strategy Library ─────────────────────────────────────────────────────────

export interface StrategyDto {
  id: number;
  name: string;
  description: string | null;
  symbol: string;
  strategy: string;
  parameters: Record<string, number>;
  initial_capital: number;
  slippage_pct: number;
  start_date: string | null;
  end_date: string | null;
  total_return_pct: number | null;
  annualized_return_pct: number | null;
  sharpe_ratio: number | null;
  max_drawdown_pct: number | null;
  win_rate_pct: number | null;
  total_trades: number | null;
  is_public: boolean;
  is_mine: boolean;
  created_at: string;
}

export interface StrategyListDto {
  strategies: StrategyDto[];
  total: number;
}

export interface StrategySavePayload {
  name: string;
  description?: string;
  symbol: string;
  strategy: string;
  parameters: Record<string, number>;
  initial_capital: number;
  slippage_pct?: number;
  start_date?: string;
  end_date?: string;
  total_return_pct?: number;
  annualized_return_pct?: number;
  sharpe_ratio?: number;
  max_drawdown_pct?: number;
  win_rate_pct?: number;
  total_trades?: number;
  is_public?: boolean;
}

export async function fetchMyStrategies(): Promise<StrategyListDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/strategies`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch strategies");
  return res.json();
}

export async function fetchPublicStrategies(): Promise<StrategyListDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/strategies/public`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch public strategies");
  return res.json();
}

export async function saveStrategy(payload: StrategySavePayload): Promise<StrategyDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/strategies`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to save strategy");
  return res.json();
}

export async function updateStrategy(
  id: number,
  payload: { name?: string; description?: string; is_public?: boolean },
): Promise<StrategyDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/strategies/${id}`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to update strategy");
  return res.json();
}

export async function deleteStrategy(id: number): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/v1/strategies/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok && res.status !== 404) throw new Error("Failed to delete strategy");
}

export async function acknowledgeAlert(id: number): Promise<AlertDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/alerts/${id}/ack`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to acknowledge alert");
  return res.json();
}

export async function updateProfile(name: string): Promise<{ id: string; email: string; name: string | null; is_pro: boolean }> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify({ name }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to update profile.");
  }
  return res.json();
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/change-password`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to change password.");
  }
}

// ── Ops & Monitoring (CORE-OPS-01) ─────────────────────────────────────────

export interface OpsHealthDto {
  status: "ok" | "degraded";
  checked_at: string;
  components: { database: string; redis: string; pipelines: string };
  pipeline_issues: string[];
}

export interface OpsPipelineRow {
  job_id: string;
  last_run_at: string;
  last_duration_ms: number;
  last_success: boolean;
  last_detail: string;
  success_rate_pct: number;
  total_runs_recorded: number;
}

export interface OpsRouteStats {
  route: string;
  total_requests: number;
  error_4xx: number;
  error_5xx: number;
  error_rate_pct: number;
  latency_ms: { p50: number | null; p95: number | null; p99: number | null; avg: number | null };
}

export interface OpsMetricsDto {
  server_started_at: string;
  snapshot_at: string;
  api: { routes: OpsRouteStats[]; total_routes_tracked: number };
  pipelines: OpsPipelineRow[];
  inference: { count: number; avg_ms: number | null; p95_ms: number | null };
}

export interface OpsAlertBreach {
  type: string;
  severity: "warning" | "error";
  message: string;
  value: number;
  threshold: number;
}

export interface OpsAlertsDto {
  evaluated_at: string;
  all_clear: boolean;
  breach_count: number;
  thresholds: Record<string, number>;
  breaches: OpsAlertBreach[];
}

export interface OpsJobDto {
  id: string;
  name: string;
  trigger: string;
  next_run_at: string | null;
}

export async function fetchOpsHealth(): Promise<OpsHealthDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/ops/health`, { headers: authHeaders(), cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch ops health");
  return res.json();
}

export async function fetchOpsMetrics(): Promise<OpsMetricsDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/ops/metrics`, { headers: authHeaders(), cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch ops metrics");
  return res.json();
}

export async function fetchOpsAlerts(): Promise<OpsAlertsDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/ops/alerts`, { headers: authHeaders(), cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch ops alerts");
  return res.json();
}

export async function fetchOpsJobs(): Promise<OpsJobDto[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/ops/jobs`, { headers: authHeaders(), cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch ops jobs");
  return res.json();
}

// ── Showcase / Pro Tools (CORE-SHOP-01, CORE-SHOP-02) ───────────────────────

export interface ShowcaseProductDto {
  id: number;
  title: string;
  tagline: string;
  description: string;
  features: string[];
  category: string;
  price_label: string;
  external_url: string;
  sort_order: number;
}

export async function fetchShowcaseProducts(
  category?: string,
): Promise<ShowcaseProductDto[]> {
  const qs = category ? `?category=${encodeURIComponent(category)}` : "";
  const res = await fetch(`${API_BASE_URL}/api/v1/showcase/products${qs}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to load showcase products");
  return res.json() as Promise<ShowcaseProductDto[]>;
}

export async function trackShowcaseClick(
  productId: number,
  eventType: "view" | "detail" | "outbound",
  anonUserId?: string,
): Promise<void> {
  try {
    await fetch(`${API_BASE_URL}/api/v1/showcase/products/${productId}/click`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_type: eventType, anon_user_id: anonUserId ?? null }),
    });
  } catch {
    // Analytics must never break UX
  }
}

// ── Product Analytics (CORE-ANALYTICS-01) ───────────────────────────────────

/**
 * Canonical analytics event names — must match the backend EventName enum.
 * Defined here as a const object so tree-shaking removes unused names.
 */
export const AnalyticsEvent = {
  // Acquisition & Activation
  USER_SIGNED_UP: "user_signed_up",
  USER_LOGGED_IN: "user_logged_in",
  USER_LOGGED_OUT: "user_logged_out",
  CONSENT_ACCEPTED: "consent_accepted",
  ONBOARDING_TOUR_STARTED: "onboarding_tour_started",
  ONBOARDING_TOUR_COMPLETED: "onboarding_tour_completed",
  ONBOARDING_TOUR_SKIPPED: "onboarding_tour_skipped",
  // Dashboard & Core
  DASHBOARD_VIEWED: "dashboard_viewed",
  SYMBOL_SEARCHED: "symbol_searched",
  SYMBOL_CHANGED: "symbol_changed",
  WATCHLIST_SYMBOL_ADDED: "watchlist_symbol_added",
  WATCHLIST_SYMBOL_REMOVED: "watchlist_symbol_removed",
  // Features
  TECHNICAL_CONSENSUS_VIEWED: "technical_consensus_viewed",
  MACRO_DASHBOARD_VIEWED: "macro_dashboard_viewed",
  MACRO_ADVANCED_VIEWED: "macro_advanced_viewed",
  SENTIMENT_TAB_VIEWED: "sentiment_tab_viewed",
  RETAIL_SENTIMENT_VIEWED: "retail_sentiment_viewed",
  BACKTEST_RUN: "backtest_run",
  BACKTEST_STRATEGY_SAVED: "backtest_strategy_saved",
  BACKTEST_STRATEGY_LOADED: "backtest_strategy_loaded",
  HEDGING_SIMULATOR_VIEWED: "hedging_simulator_viewed",
  HEDGING_ADVANCED_VIEWED: "hedging_advanced_viewed",
  PORTFOLIO_CREATED: "portfolio_created",
  PORTFOLIO_VIEWED: "portfolio_viewed",
  ALERT_CREATED: "alert_created",
  ALERT_TRIGGERED: "alert_triggered",
  LEARN_TAB_VIEWED: "learn_tab_viewed",
  BLOG_POST_VIEWED: "blog_post_viewed",
  CASE_STUDY_VIEWED: "case_study_viewed",
  COMMUNITY_PAGE_VIEWED: "community_page_viewed",
  SHOWCASE_VIEWED: "showcase_viewed",
  SHOWCASE_PRODUCT_CLICKED: "showcase_product_clicked",
  SETTINGS_PAGE_VIEWED: "settings_page_viewed",
  PROFILE_UPDATED: "profile_updated",
  PASSWORD_CHANGED: "password_changed",
  BILLING_PAGE_VIEWED: "billing_page_viewed",
  UPGRADE_CTA_CLICKED: "upgrade_cta_clicked",
  API_ERROR_ENCOUNTERED: "api_error_encountered",
} as const;

export type AnalyticsEventName = (typeof AnalyticsEvent)[keyof typeof AnalyticsEvent];

export interface TrackEventPayload {
  event_name: AnalyticsEventName;
  session_id?: string;
  anon_id?: string;
  page?: string;
  feature?: string;
  /** Properties must not contain PII (email, name, IP, etc.) */
  properties?: Record<string, string | number | boolean | null>;
}

// Module-level session ID — generated once per page load, persisted in memory only
let _sessionId: string | null = null;
function getSessionId(): string {
  if (!_sessionId) {
    _sessionId = typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2);
  }
  return _sessionId;
}

/**
 * Fire-and-forget analytics beacon.
 * - Never throws — analytics must not break the UI.
 * - Automatically injects session_id and current page path.
 * - Sends Bearer token if present in localStorage.
 */
export async function track(
  event_name: AnalyticsEventName,
  options?: {
    feature?: string;
    properties?: Record<string, string | number | boolean | null>;
    page?: string;
  },
): Promise<void> {
  if (typeof window === "undefined") return; // SSR guard

  const payload: TrackEventPayload = {
    event_name,
    session_id: getSessionId(),
    page: options?.page ?? window.location.pathname,
    feature: options?.feature,
    properties: options?.properties ?? {},
  };

  try {
    await fetch(`${API_BASE_URL}/api/v1/analytics/event`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // Include auth token if available (best-effort — no throw if missing)
        ...(localStorage.getItem("access_token")
          ? { Authorization: `Bearer ${localStorage.getItem("access_token")}` }
          : {}),
      },
      body: JSON.stringify(payload),
      // keepalive ensures the request completes even during page unload
      keepalive: true,
    });
  } catch {
    // Silently swallow — analytics must never break UX
  }
}

// ── Analytics Admin Dashboard ────────────────────────────────────────────────

export interface AnalyticsFunnelStep {
  event_name: string;
  label: string;
  unique_users: number;
  total_occurrences: number;
  conversion_from_previous_pct: number | null;
}

export interface AnalyticsFunnelReport {
  funnel_name: string;
  period_days: number;
  steps: AnalyticsFunnelStep[];
}

export interface AnalyticsFeatureAdoptionRow {
  event_name: string;
  label: string;
  unique_users: number;
  total_occurrences: number;
  adoption_pct: number;
}

export interface AnalyticsDauPoint {
  date: string;
  dau: number;
  new_users: number;
}

export interface AnalyticsSummaryDto {
  period_days: number;
  total_events: number;
  total_signed_up_users: number;
  total_active_users: number;
  activation_funnel: AnalyticsFunnelReport;
  conversion_funnel: AnalyticsFunnelReport;
  feature_adoption: AnalyticsFeatureAdoptionRow[];
  daily_active_users: AnalyticsDauPoint[];
  top_pages: { page: string; views: number; unique_users: number }[];
  top_symbols: { symbol: string; searches: number }[];
}

export async function fetchAnalyticsSummary(
  periodDays = 30,
): Promise<AnalyticsSummaryDto> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/analytics/summary?period_days=${periodDays}`,
    { headers: authHeaders(), cache: "no-store" },
  );
  if (!res.ok) throw new Error("Failed to load analytics summary");
  return res.json();
}

export async function fetchAnalyticsRawEvents(
  eventName?: string,
  limit = 50,
): Promise<Record<string, unknown>[]> {
  const qs = new URLSearchParams({ limit: String(limit) });
  if (eventName) qs.set("event_name", eventName);
  const res = await fetch(
    `${API_BASE_URL}/api/v1/analytics/events?${qs}`,
    { headers: authHeaders(), cache: "no-store" },
  );
  if (!res.ok) throw new Error("Failed to load raw events");
  return res.json();
}

// ── Two-Factor Authentication (CORE-SEC-01) ─────────────────────────────────────

export interface TotpSetupDto {
  secret: string;   // base32 plaintext — show as manual entry fallback
  uri: string;      // otpauth:// URI — encode as QR code
}

export interface TotpStatusDto {
  totp_enabled: boolean;
}

export interface LoginResponseDto {
  access_token: string;
  refresh_token: string;
  token_type: string;
  totp_required: boolean;
  pending_token: string;
}

/** POST /auth/login — returns either full tokens or a 2FA pending state */
export async function loginWithTotp(email: string, password: string): Promise<LoginResponseDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Invalid email or password.");
  }
  return res.json();
}

/** POST /auth/2fa/verify — exchange pending_token + TOTP code for full tokens */
export async function verify2faLogin(pendingToken: string, code: string): Promise<{ access_token: string; refresh_token: string }> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/2fa/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pending_token: pendingToken, code }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Invalid code.");
  }
  return res.json();
}

/** POST /auth/2fa/setup — generate TOTP secret + QR URI */
export async function setup2fa(): Promise<TotpSetupDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/2fa/setup`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to start 2FA setup.");
  return res.json();
}

/** POST /auth/2fa/enable — confirm first TOTP code to activate 2FA */
export async function enable2fa(code: string): Promise<TotpStatusDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/2fa/enable`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ code }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Invalid code.");
  }
  return res.json();
}

/** POST /auth/2fa/disable — verify TOTP code then disable 2FA */
export async function disable2fa(code: string): Promise<TotpStatusDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/2fa/disable`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ code }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Invalid code.");
  }
  return res.json();
}

/** GET /auth/2fa/status */
export async function get2faStatus(): Promise<TotpStatusDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/2fa/status`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch 2FA status.");
  return res.json();
}

// ── A/B Experiments (CORE-EXPERIMENT-01) ─────────────────────────────────────────

export interface VariantDefinition {
  key: string;
  name: string;
  weight: number;
}

export interface ExperimentDto {
  id: number;
  key: string;
  name: string;
  hypothesis: string | null;
  variants: VariantDefinition[];
  traffic_pct: number;
  status: "draft" | "running" | "paused" | "concluded";
  starts_at: string | null;
  ends_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface AssignmentDto {
  experiment_key: string;
  experiment_id: number;
  variant_key: string;
  variant_name: string;
  in_traffic: boolean;
  assigned_at: string;
}

export interface ExperimentVariantMetric {
  variant_key: string;
  variant_name: string;
  unique_users: number;
  total_events: number;
  conversions: number;
  conversion_rate_pct: number;
}

export interface ExperimentResultsDto {
  experiment_id: number;
  experiment_key: string;
  experiment_name: string;
  status: string;
  goal_event: string;
  period_days: number;
  total_assigned_users: number;
  variants: ExperimentVariantMetric[];
  winner: string | null;
  note: string;
}

export interface ExperimentCreatePayload {
  key: string;
  name: string;
  hypothesis?: string;
  variants: VariantDefinition[];
  traffic_pct?: number;
  starts_at?: string;
  ends_at?: string;
  notes?: string;
}

/** Get (or create) variant assignment — call once per running experiment on app boot */
export async function assignVariant(
  experimentKey: string,
  anonId?: string,
): Promise<AssignmentDto> {
  const qs = anonId ? `?anon_id=${encodeURIComponent(anonId)}` : "";
  const res = await fetch(
    `${API_BASE_URL}/api/v1/experiments/${experimentKey}/assign${qs}`,
    { headers: authHeaders(), cache: "no-store" },
  );
  if (!res.ok) throw new Error(`Failed to assign variant for ${experimentKey}`);
  return res.json();
}

/** Admin: list all experiments */
export async function fetchExperiments(
  status?: string,
): Promise<ExperimentDto[]> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  const res = await fetch(`${API_BASE_URL}/api/v1/experiments${qs}`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to load experiments");
  return res.json();
}

/** Admin: create experiment */
export async function createExperiment(
  payload: ExperimentCreatePayload,
): Promise<ExperimentDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/experiments`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to create experiment");
  }
  return res.json();
}

/** Admin: update experiment */
export async function updateExperiment(
  key: string,
  payload: Partial<ExperimentCreatePayload> & { status?: string },
): Promise<ExperimentDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/experiments/${key}`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to update experiment");
  return res.json();
}

/** Admin: delete experiment */
export async function deleteExperiment(key: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/v1/experiments/${key}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok && res.status !== 404) throw new Error("Failed to delete experiment");
}

/** Admin: launch / pause / conclude */
export async function transitionExperiment(
  key: string,
  action: "launch" | "pause" | "conclude",
): Promise<ExperimentDto> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/experiments/${key}/${action}`,
    { method: "POST", headers: authHeaders() },
  );
  if (!res.ok) throw new Error(`Failed to ${action} experiment`);
  return res.json();
}

/** Admin: get results for an experiment */
export async function fetchExperimentResults(
  key: string,
  goalEvent: string,
  periodDays = 30,
): Promise<ExperimentResultsDto> {
  const qs = new URLSearchParams({
    goal_event: goalEvent,
    period_days: String(periodDays),
  });
  const res = await fetch(
    `${API_BASE_URL}/api/v1/experiments/${key}/results?${qs}`,
    { headers: authHeaders(), cache: "no-store" },
  );
  if (!res.ok) throw new Error("Failed to load experiment results");
  return res.json();
}

// ─── Email Preferences (CORE-EMAIL-01/02) ────────────────────────────────────

export interface EmailPreferenceDto {
  marketing_opted_in: boolean;
  digest_opted_in: boolean;
  digest_frequency: "weekly" | "biweekly";
  onboarding_step: number;
}

export async function fetchEmailPreferences(): Promise<EmailPreferenceDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/email/preferences`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to load email preferences");
  return res.json();
}

export async function updateEmailPreferences(
  patch: Partial<Pick<EmailPreferenceDto, "marketing_opted_in" | "digest_opted_in" | "digest_frequency">>,
): Promise<EmailPreferenceDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/email/preferences`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify(patch),
  });
  if (!res.ok) throw new Error("Failed to update email preferences");
  return res.json();
}

export async function unsubscribeByToken(token: string): Promise<{ status: string; message: string }> {
  const res = await fetch(`${API_BASE_URL}/api/v1/email/unsubscribe?token=${encodeURIComponent(token)}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Invalid or expired unsubscribe token");
  return res.json();
}

// ─── API Key Management (P3-API-01) ─────────────────────────────────────────

export interface ApiKeyDto {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  rate_limit_per_minute: number;
  total_calls: number;
  last_used_at: string | null;
  is_active: boolean;
  created_at: string;
  expires_at: string | null;
}

export interface ApiKeyCreatedDto extends ApiKeyDto {
  raw_key: string;
  warning: string;
}

export interface ApiKeyUsageEntry {
  endpoint: string;
  method: string;
  status_code: number | null;
  response_ms: number | null;
  called_at: string;
}

export async function fetchApiKeys(): Promise<ApiKeyDto[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/api-keys`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to load API keys");
  return res.json();
}

export async function createApiKey(payload: {
  name: string;
  scopes: string[];
  rate_limit_per_minute: number;
}): Promise<ApiKeyCreatedDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/api-keys`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to create API key");
  }
  return res.json();
}

export async function revokeApiKey(id: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/v1/api-keys/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to revoke API key");
}

export async function fetchApiKeyUsage(id: string): Promise<ApiKeyUsageEntry[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/api-keys/${id}/usage`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to load usage");
  return res.json();
}

// ─── Risk & Stress Testing (P3-RISK-01) ───────────────────────────────────────

export interface ScenarioDto {
  id: string;
  name: string;
  description: string;
  category: string;
  start_date: string | null;
  end_date: string | null;
  macro_notes: string;
  market_shocks: Record<string, number>;
}

export interface StockStressDto {
  symbol: string;
  scenario_id: string;
  scenario_name: string;
  portfolio_value: number;
  estimated_pnl: number;
  estimated_pnl_pct: number;
  beta_adjusted_pnl: number;
  var_95: number | null;
  var_99: number | null;
  cvar_95: number | null;
  cvar_99: number | null;
  max_drawdown_historical: number;
  annualised_vol: number;
  beta_vs_spy: number;
  macro_notes: string;
  recovery_estimate_days: number | null;
  disclaimer: string;
}

export interface MultiScenarioStockDto {
  symbol: string;
  portfolio_value: number;
  results: StockStressDto[];
  worst_scenario: string | null;
  best_scenario: string | null;
}

export interface PortfolioStressPositionInput {
  symbol: string;
  weight: number;
  value: number;
}

export interface PortfolioStressDto {
  scenario_id: string;
  scenario_name: string;
  total_portfolio_value: number;
  total_estimated_pnl: number;
  total_estimated_pnl_pct: number;
  positions: Array<{
    symbol: string;
    value: number;
    weight_pct: number;
    estimated_pnl: number;
    estimated_pnl_pct: number;
    beta_vs_spy: number;
  }>;
  portfolio_var_95: number | null;
  portfolio_var_99: number | null;
  portfolio_cvar_95: number | null;
  worst_position: string | null;
  best_position: string | null;
  macro_notes: string;
  disclaimer: string;
}

export async function fetchScenarios(category?: string): Promise<ScenarioDto[]> {
  const qs = category ? `?category=${category}` : "";
  const res = await fetch(`${API_BASE_URL}/api/v1/risk/scenarios${qs}`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to load scenarios");
  return res.json();
}

export async function stressTestSymbol(
  symbol: string,
  scenarioId: string,
  portfolioValue: number,
): Promise<StockStressDto> {
  const qs = new URLSearchParams({
    scenario_id: scenarioId,
    portfolio_value: String(portfolioValue),
  });
  const res = await fetch(`${API_BASE_URL}/api/v1/risk/stress/${symbol}?${qs}`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Stress test failed");
  return res.json();
}

export async function stressTestSymbolMulti(
  symbol: string,
  portfolioValue: number,
): Promise<MultiScenarioStockDto> {
  const qs = new URLSearchParams({ portfolio_value: String(portfolioValue) });
  const res = await fetch(`${API_BASE_URL}/api/v1/risk/stress/${symbol}/multi?${qs}`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Multi-scenario stress test failed");
  return res.json();
}

export async function stressTestPortfolio(
  positions: PortfolioStressPositionInput[],
  scenarioId: string,
): Promise<PortfolioStressDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/risk/portfolio/stress`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ positions, scenario_id: scenarioId }),
  });
  if (!res.ok) throw new Error("Portfolio stress test failed");
  return res.json();
}

export async function stressTestPortfolioMulti(
  positions: PortfolioStressPositionInput[],
  scenarioIds?: string[],
): Promise<PortfolioStressDto[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/risk/portfolio/stress/multi`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ positions, scenario_ids: scenarioIds ?? [] }),
  });
  if (!res.ok) throw new Error("Portfolio multi-stress test failed");
  return res.json();
}

// ─── API Key Management (P3-API-01) ──────────────────────────────────────────

export interface ApiKeyDto {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  rate_limit_per_minute: number;
  total_calls: number;
  last_used_at: string | null;
  is_active: boolean;
  created_at: string;
  expires_at: string | null;
}

export interface ApiKeyCreatedDto extends ApiKeyDto {
  raw_key: string;
  warning: string;
}

export interface ApiKeyUsageEntry {
  endpoint: string;
  method: string;
  status_code: number | null;
  response_ms: number | null;
  called_at: string;
}

export async function fetchApiKeys(): Promise<ApiKeyDto[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/api-keys`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to load API keys");
  return res.json();
}

export async function createApiKey(payload: {
  name: string;
  scopes: string[];
  rate_limit_per_minute: number;
  expires_at?: string | null;
}): Promise<ApiKeyCreatedDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/api-keys`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to create API key");
  }
  return res.json();
}

export async function revokeApiKey(keyId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/v1/api-keys/${keyId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to revoke API key");
}

export async function fetchApiKeyUsage(keyId: string): Promise<ApiKeyUsageEntry[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/api-keys/${keyId}/usage`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to load usage log");
  return res.json();
}

export async function updateApiKeyScopes(
  keyId: string,
  scopes: string[],
): Promise<ApiKeyDto> {
  const res = await fetch(`${API_BASE_URL}/api/v1/api-keys/${keyId}/scopes`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify({ scopes }),
  });
  if (!res.ok) throw new Error("Failed to update scopes");
  return res.json();
}

export async function deleteAccount(): Promise<{ message: string; anonymised_at: string }> {
  const res = await fetch(`${API_BASE_URL}/api/v1/gdpr/delete`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ confirmation: "DELETE MY ACCOUNT" }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to delete account.");
  }
  return res.json();
}
