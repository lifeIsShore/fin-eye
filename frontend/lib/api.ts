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

