"use client";

import React, { useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import {
  fetchTechnicalLatest,
  fetchNewsSentiment,
  fetchMacroLatest,
} from "../lib/api";
import MarketWeatherWidget from "../components/MarketWeatherWidget";
import RegimeWidget from "../components/RegimeWidget";
import TimeframeGrid from "../components/TimeframeGrid";

export default function DashboardPage() {
  const [tickerInput, setTickerInput] = useState("AAPL");
  const [activeSymbol, setActiveSymbol] = useState("AAPL");

  const { data: techData, error: techError } = useSWR(
    `tech-${activeSymbol}`,
    () => fetchTechnicalLatest(activeSymbol),
    { refreshInterval: 60000, shouldRetryOnError: false },
  );

  const { data: sentData, error: sentError } = useSWR(
    `sent-${activeSymbol}`,
    () => fetchNewsSentiment(activeSymbol),
    { refreshInterval: 60000, shouldRetryOnError: false },
  );

  const { data: macroData, error: macroError } = useSWR(
    "macro-latest",
    () => fetchMacroLatest(),
    { refreshInterval: 300000, shouldRetryOnError: false },
  );

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (tickerInput.trim()) {
      setActiveSymbol(tickerInput.trim().toUpperCase());
    }
  };

  const isLoading = !techData && !techError && !sentError && !macroError;

  // Calculate GAS (Global Alignment Score)
  let gasScore = 50; // default neutral
  if (techData && sentData && macroData?.macro_score) {
    // 40% Tech, 30% Sentiment, 30% Macro
    // Tech: 0-100 score
    const techWeighted = techData.technical_confidence_score * 0.4;

    // Sentiment: Map 30d sentiment (-1 to +1) to 0-100 scale
    // e.g. sentiment = 0.5 -> ((0.5 + 1) / 2) * 100 = 75
    const sent30d = sentData.sentiment_30d ?? 0;
    const sentNormalized = ((sent30d + 1) / 2) * 100;
    const sentWeighted = sentNormalized * 0.3;

    // Macro: 0-100 score
    const macroWeighted = macroData.macro_score.score * 0.3;

    gasScore = techWeighted + sentWeighted + macroWeighted;
  }

  const vixLevel = macroData?.data?.vix?.value ?? null;
  const techScore = techData?.technical_confidence_score ?? 50;

  return (
    <div className="space-y-6">
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-3xl font-black tracking-tight text-slate-100">
            {activeSymbol} Intelligence
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Real-time GAS, Regime, and Multi-Timeframe layers.
          </p>
        </div>

        <form onSubmit={handleSearch} className="flex gap-2 w-full sm:w-auto">
          <input
            type="text"
            value={tickerInput}
            onChange={(e) => setTickerInput(e.target.value)}
            placeholder="Enter Ticker..."
            className="w-full sm:w-48 rounded-md bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
          />
          <button
            type="submit"
            className="rounded-md bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 transition-colors"
          >
            Analyze
          </button>
        </form>
      </header>

      {isLoading ? (
        <div className="py-20 text-center animate-pulse text-slate-500">
          Gathering market intelligence for {activeSymbol}...
        </div>
      ) : (
        <div className="space-y-6">
          <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <MarketWeatherWidget gasScore={gasScore} />

            <div className="flex flex-col space-y-4">
              <RegimeWidget technicalScore={techScore} vixLevel={vixLevel} />

              <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/40">
                <div className="flex justify-between items-center mb-1">
                  <h3 className="text-sm font-semibold text-slate-100">
                    Technical Consensus
                  </h3>
                  <span className="text-sky-400 font-bold text-sm">
                    {techData?.technical_confidence_score.toFixed(1)} / 100
                  </span>
                </div>
                {techData?.signals?.length ? (
                  <TimeframeGrid signals={techData.signals} />
                ) : (
                  <p className="text-xs text-rose-400 mt-4 px-3 py-2 bg-rose-950/20 rounded border border-rose-900">
                    {techError?.message || "Technical models are not trained for this symbol."}
                  </p>
                )}
              </div>
            </div>
          </section>

          <section className="flex flex-wrap gap-4 pt-4 border-t border-slate-800/50">
            <Link
              href="/macro"
              className="text-sm text-sky-400 hover:text-sky-300 font-medium transition-colors"
            >
              View Full Macro Intel &rarr;
            </Link>
            <Link
              href="/news-sentiment"
              className="text-sm text-sky-400 hover:text-sky-300 font-medium transition-colors"
            >
              View Full Sentiment Intel &rarr;
            </Link>
          </section>
        </div>
      )}
    </div>
  );
}

