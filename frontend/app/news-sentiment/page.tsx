"use client";

import { useState } from "react";
import useSWR from "swr";
import { fetchNewsSentiment, fetchSentimentSources } from "../../lib/api";
import { SentimentChart } from "../../components/SentimentChart";
import { ArticleList } from "../../components/ArticleList";
import { SourceBreakdownTable } from "../../components/SourceBreakdownTable";

const DEFAULT_SYMBOL = "AAPL";

const fetcher = (symbol: string) => fetchNewsSentiment(symbol);

export default function NewsSentimentPage() {
  const [symbol, setSymbol] = useState<string>(DEFAULT_SYMBOL);
  const [input, setInput] = useState<string>(DEFAULT_SYMBOL);

  const { data, error, isLoading, mutate } = useSWR(
    ["sentiment", symbol],
    ([, s]) => fetcher(s),
  );
  const {
    data: sourceData,
    error: sourceError,
    isLoading: isLoadingSources,
    mutate: mutateSources,
  } = useSWR(["sentiment-sources", symbol], ([, s]) =>
    fetchSentimentSources(s),
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim().toUpperCase();
    if (!trimmed) return;
    setSymbol(trimmed);
    mutate();
    mutateSources();
  };

  const sentimentBands = [
    { key: "sentiment_1d", label: "1 day" },
    { key: "sentiment_7d", label: "7 days" },
    { key: "sentiment_30d", label: "30 days" },
  ] as const;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">
            News &amp; Sentiment
          </h2>
          <p className="mt-1 max-w-xl text-sm text-slate-400">
            Time-series of FinBERT-scored news sentiment and recent headlines
            for a selected stock. This view is educational analysis, not
            investment advice.
          </p>
        </div>
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <label className="text-xs font-medium text-slate-400" htmlFor="ticker">
            Ticker
          </label>
          <input
            id="ticker"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="h-9 rounded-md border border-slate-700 bg-slate-900 px-2 text-sm text-slate-50 outline-none ring-0 focus:border-sky-500 focus:ring-1 focus:ring-sky-500"
            placeholder="e.g. AAPL"
          />
          <button
            type="submit"
            className="inline-flex h-9 items-center rounded-md bg-sky-500 px-3 text-xs font-medium text-white shadow-sm transition hover:bg-sky-400"
          >
            Load
          </button>
        </form>
      </div>

      <div className="grid gap-6 md:grid-cols-5">
        <section className="md:col-span-3 space-y-3 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-slate-100">
              Sentiment over last 30 days
            </h3>
            <p className="text-xs text-slate-500 uppercase tracking-wide">
              {symbol}
            </p>
          </div>
          {isLoading && !data && !error && (
            <p className="text-sm text-slate-400">Loading sentiment…</p>
          )}
          {error && (
            <p className="text-sm text-rose-400">
              Could not load sentiment data for {symbol}. Ensure the backend is
              running and there is news data available.
            </p>
          )}
          {data && <SentimentChart data={data.series} />}
        </section>

        <section className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/40 p-4 md:col-span-2">
          <h3 className="text-sm font-semibold text-slate-100">
            Current sentiment snapshot
          </h3>
          <div className="grid grid-cols-3 gap-3 text-xs">
            {sentimentBands.map(({ key, label }) => {
              const value = data ? (data as any)[key] as number | null : null;

              let display = "n/a";
              let color = "text-slate-400";
              if (typeof value === "number") {
                const scaled = Math.round(((value + 1) / 2) * 100);
                display = `${scaled}`;
                if (scaled > 60) color = "text-emerald-400";
                else if (scaled < 40) color = "text-rose-400";
              }

              return (
                <div
                  key={key}
                  className="rounded-lg border border-slate-800 bg-slate-950/60 p-2"
                >
                  <p className="text-[10px] uppercase tracking-wide text-slate-500">
                    {label}
                  </p>
                  <p className={`mt-1 text-lg font-semibold ${color}`}>
                    {display}
                  </p>
                  <p className="text-[10px] text-slate-500">0–100 sentiment</p>
                </div>
              );
            })}
          </div>
          <p className="text-[11px] text-slate-500">
            Scores are derived from daily averages of FinBERT sentiment on
            recent news headlines for {symbol}. 0 ≈ strongly bearish, 50 ≈
            neutral, 100 ≈ strongly bullish.
          </p>
        </section>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <h3 className="text-sm font-semibold text-slate-100">
            Recent headlines
          </h3>
          <p className="mb-2 mt-1 text-xs text-slate-500">
            Headlines are scored using FinBERT; sentiment labels emphasise
            educational interpretation only, not trade suggestions.
          </p>
          {data && <ArticleList articles={data.articles} />}
          {!data && !isLoading && !error && (
            <p className="text-sm text-slate-400">
              Enter a ticker symbol above to fetch sentiment.
            </p>
          )}
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <h3 className="text-sm font-semibold text-slate-100">
            Source breakdown (last 30 days)
          </h3>
          <p className="mb-2 mt-1 text-xs text-slate-500">
            Distribution of bullish, bearish, and neutral headlines by source,
            helping you see whether sentiment is driven by a few outlets or
            broad coverage.
          </p>
          {isLoadingSources && !sourceData && !sourceError && (
            <p className="text-sm text-slate-400">Loading source breakdown…</p>
          )}
          {sourceError && (
            <p className="text-sm text-slate-400">
              Could not load source breakdown. It may be unavailable if there
              are no recent scored headlines.
            </p>
          )}
          {sourceData && (
            <SourceBreakdownTable rows={sourceData.breakdown} />
          )}
        </section>
      </div>
    </div>
  );
}
