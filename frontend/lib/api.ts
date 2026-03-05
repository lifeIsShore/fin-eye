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
