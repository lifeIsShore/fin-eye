
// ── LLM Investment Manager Insight (todos-v5 Sprint 1) ───────────────────────

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface MLSignalInput {
  timeframe: string;
  direction: "Bullish" | "Bearish" | "Neutral";
  confidence: number;
  sharpe: number;
  horizon_periods: number;
  model_used: string;
}

export interface InsightSections {
  primary_signal:  string;
  entry:           string;
  targets:         string;
  risk_management: string;
  timeframe_split: string;
  caution:         string;
}

export interface LLMInsightRequest {
  current_price:       number;
  signals:             MLSignalInput[];
  rsi_14?:             number | null;
  macd_hist?:          number | null;
  bb_pb?:              number | null;
  atr_pct?:            number | null;
  volume_ratio?:       number | null;
  atr_absolute?:       number | null;
  macro_score?:        number | null;
  vix?:                number | null;
  yield_spread?:       number | null;
  macro_regime?:       string | null;
  news_sentiment_1d?:  number | null;
  news_sentiment_7d?:  number | null;
  news_sentiment_30d?: number | null;
  gas_score?:          number | null;
}

export interface LLMInsightResponse {
  symbol:              string;
  sections:            InsightSections;
  backend_used:        string;
  model_used:          string;
  cached:              boolean;
  error:               string | null;
  // Consensus
  agreement_count:     number;
  total_timeframes:    number;
  dominant_direction:  string;
  // Price targets
  expected_price?:     number | null;
  upside_target?:      number | null;
  downside_stop?:      number | null;
  expected_return_pct?: number | null;
  atr_absolute?:       number | null;
}

export async function fetchLLMInsight(
  symbol: string,
  payload: LLMInsightRequest,
): Promise<LLMInsightResponse> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/explanation/${encodeURIComponent(symbol.toUpperCase())}/generate-insight`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(typeof window !== "undefined" && localStorage.getItem("access_token")
          ? { Authorization: `Bearer ${localStorage.getItem("access_token")}` }
          : {}),
      },
      body: JSON.stringify(payload),
      cache: "no-store",
    },
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? `LLM insight failed: ${res.status}`);
  }
  return res.json() as Promise<LLMInsightResponse>;
}
