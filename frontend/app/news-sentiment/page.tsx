"use client";

import React, { useState } from "react";
import useSWR from "swr";
import { fetchNewsSentiment, fetchSentimentSources } from "../../lib/api";
import { SentimentChart } from "../../components/SentimentChart";
import { ArticleList } from "../../components/ArticleList";
import { SourceBreakdownTable } from "../../components/SourceBreakdownTable";
import { PageBanner } from "../../components/ui/PageBanner";
import FreshnessIndicator from "../../components/FreshnessIndicator";
import SentimentKeywordCloud from "../../components/SentimentKeywordCloud";
import ArticleTopicClusters from "../../components/ArticleTopicClusters";
import { Newspaper, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { useSymbol } from "../../lib/symbolContext";

const DEFAULT_SYMBOL = "AAPL";

const fetcher = (symbol: string) => fetchNewsSentiment(symbol);

export default function NewsSentimentPage() {
  const { symbol: globalSymbol, setSymbol: setGlobalSymbol } = useSymbol();
  const [symbol, setSymbol] = useState<string>(globalSymbol);
  const [input, setInput] = useState<string>(globalSymbol);

  // Keep in sync when global symbol changes (e.g. user changes it in top bar)
  React.useEffect(() => {
    setSymbol(globalSymbol);
    setInput(globalSymbol);
  }, [globalSymbol]);

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
    setGlobalSymbol(trimmed); // sync back to global context
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
      <PageBanner
        icon={<Newspaper className="h-5 w-5" />}
        title="News Sentiment"
        description="FinBERT-scored headlines and 30-day sentiment trend for any ticker. Educational analysis only."
        badge="NLP Powered"
        badgeColor="sky"
      />
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div />
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
            <div className="flex items-center gap-2.5">
              <h3 className="text-sm font-semibold text-slate-100">
                Sentiment over last 30 days
              </h3>
              {/* Sprint 25 — 7d vs prior-7d trend arrow */}
              {data && (() => {
                const series = data.series;
                if (!series || series.length < 8) return null;
                const sorted = [...series].sort((a, b) =>
                  a.date < b.date ? -1 : 1
                );
                const recent = sorted.slice(-7);
                const prior  = sorted.slice(-14, -7);
                if (prior.length < 4) return null;
                const avgRecent = recent.reduce((s, p) => s + p.sentiment_score, 0) / recent.length;
                const avgPrior  = prior.reduce((s, p)  => s + p.sentiment_score, 0) / prior.length;
                const delta = avgRecent - avgPrior;
                if (Math.abs(delta) < 0.02) {
                  return (
                    <span className="flex items-center gap-1 text-xs text-slate-500">
                      <Minus className="h-3 w-3" />
                      Flat
                    </span>
                  );
                }
                const up = delta > 0;
                return (
                  <span className={`flex items-center gap-1 text-xs font-medium ${
                    up ? "text-emerald-400" : "text-rose-400"
                  }`}>
                    {up
                      ? <TrendingUp className="h-3.5 w-3.5" />
                      : <TrendingDown className="h-3.5 w-3.5" />}
                    {up ? "Improving" : "Deteriorating"}
                    <span className="text-[10px] font-normal opacity-70">
                      ({up ? "+" : ""}{(delta * 100).toFixed(1)} pts 7d)
                    </span>
                  </span>
                );
              })()}
            </div>
            <p className="text-xs text-slate-500 uppercase tracking-wide">
              {symbol}
            </p>
          </div>
          {isLoading && !data && !error && (
            <p className="text-sm text-slate-400">Loading sentiment…</p>
          )}
          {error && (
            <div className="rounded-xl border border-rose-800/40 bg-rose-950/20 p-5 flex flex-col items-center gap-2 text-center">
              <Newspaper className="h-7 w-7 text-rose-600" />
              <p className="text-sm font-semibold text-rose-300">Could not load sentiment data</p>
              <p className="text-xs text-slate-500">
                No scored headlines found for <span className="font-mono text-slate-400">{symbol}</span>.
                Try a major ticker (AAPL, TSLA, NVDA) or trigger a news seed from the admin panel.
              </p>
            </div>
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
          <div className="flex items-center justify-between gap-2 mb-1">
            <h3 className="text-sm font-semibold text-slate-100">Recent headlines</h3>
            {data?.fetched_at && (
              <FreshnessIndicator
                updatedAt={data.fetched_at}
                label="Articles"
                freshMinutes={60}
                agingMinutes={240}
              />
            )}
          </div>
          <p className="mb-3 text-xs text-slate-500">
            FinBERT-scored headlines. Tier 1 = major financial outlets. Confidence = FinBERT softmax score.
          </p>
          {data && <ArticleList articles={data.articles} />}
          {!data && !isLoading && !error && (
            <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/30 p-8 flex flex-col items-center gap-3 text-center">
              <Newspaper className="h-9 w-9 text-slate-600" />
              <div>
                <p className="text-sm font-semibold text-slate-300">No articles loaded yet</p>
                <p className="text-xs text-slate-500 mt-1">
                  Enter a ticker above and click Load to fetch FinBERT-scored headlines.
                </p>
              </div>
            </div>
          )}
        </section>

        {/* Keyword cloud */}
        {data && data.articles?.length > 0 && (
          <SentimentKeywordCloud articles={data.articles} symbol={symbol} />
        )}

        {/* Topic clusters -- Sprint 19 */}
        {data && data.articles?.length > 0 && (
          <ArticleTopicClusters articles={data.articles} symbol={symbol} />
        )}

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
