"use client";

/**
 * TickerDataPanel.tsx — todos-v4.md Phase 8.2
 *
 * Collapsible panel shown below the Technical Consensus card.
 * Displays OHLCV data status, ML model status, and news status
 * for the active symbol, with inline action buttons for each row.
 *
 * Props:
 *   symbol      — active ticker symbol
 *   isAdmin     — only render if user is admin (hide for regular users)
 *   onTrained   — callback fired after a successful Train trigger
 *                 (parent can use it to refresh techData via SWR mutate)
 */

import React, { useState, useCallback } from "react";
import useSWR from "swr";
import {
  fetchTickerStatus,
  seedSingleSymbol,
  triggerTrainSymbol,
  triggerBulkNewsSeed,
  type TickerStatusDto,
} from "../lib/api_bulk";

interface TickerDataPanelProps {
  symbol:    string;
  isAdmin:   boolean;
  onTrained?: () => void;
}

// ── Row icon helpers ──────────────────────────────────────────────────────────

function StatusDot({ ok }: { ok: boolean | null }) {
  if (ok === null) return <span className="h-2 w-2 rounded-full bg-slate-600 inline-block" />;
  return (
    <span
      className={`h-2 w-2 rounded-full inline-block ${
        ok ? "bg-emerald-400" : "bg-rose-400"
      }`}
    />
  );
}

function ActionButton({
  label,
  onClick,
  loading,
  disabled,
  variant = "default",
}: {
  label:    string;
  onClick:  () => void;
  loading?: boolean;
  disabled?: boolean;
  variant?: "default" | "warn";
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading || disabled}
      className={`flex items-center gap-1 rounded px-2 py-0.5 text-[11px] font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
        variant === "warn"
          ? "border border-amber-700/40 bg-amber-950/20 text-amber-400 hover:bg-amber-900/30"
          : "border border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700"
      }`}
    >
      {loading ? (
        <svg className="animate-spin h-3 w-3" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      ) : null}
      {label}
    </button>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function TickerDataPanel({ symbol, isAdmin, onTrained }: TickerDataPanelProps) {
  const [open, setOpen] = useState(false);

  // Action loading states
  const [seedingData,    setSeedingData]    = useState(false);
  const [trainingModels, setTrainingModels] = useState(false);
  const [fetchingNews,   setFetchingNews]   = useState(false);
  const [actionMsg,      setActionMsg]      = useState<string | null>(null);

  const { data, isLoading, mutate } = useSWR(
    open && isAdmin ? `ticker-status-${symbol}` : null,
    () => fetchTickerStatus(symbol),
    { refreshInterval: trainingModels ? 5000 : 30_000, shouldRetryOnError: false },
  );

  const flash = useCallback((msg: string) => {
    setActionMsg(msg);
    setTimeout(() => setActionMsg(null), 4000);
  }, []);

  const handleSeed = useCallback(async () => {
    setSeedingData(true);
    try {
      await seedSingleSymbol(symbol);
      flash(`Seeding ${symbol} in background — refresh in a moment`);
      setTimeout(() => mutate(), 3000);
    } catch (e) {
      flash((e as Error).message);
    } finally {
      setSeedingData(false);
    }
  }, [symbol, flash, mutate]);

  const handleTrain = useCallback(async (force = false) => {
    setTrainingModels(true);
    try {
      await triggerTrainSymbol(symbol, force);
      flash(`Training ${symbol} in background (~60–120 seconds)`);
      // Poll until done
      const poll = setInterval(async () => {
        const fresh = await mutate();
        if (fresh?.training.status === "trained") {
          clearInterval(poll);
          setTrainingModels(false);
          onTrained?.();
        }
      }, 6000);
      // Safety timeout after 3 minutes
      setTimeout(() => { clearInterval(poll); setTrainingModels(false); }, 180_000);
    } catch (e) {
      flash((e as Error).message);
      setTrainingModels(false);
    }
  }, [symbol, flash, mutate, onTrained]);

  const handleFetchNews = useCallback(async () => {
    setFetchingNews(true);
    try {
      await triggerBulkNewsSeed(7);
      flash("News fetch started for all tickers");
      setTimeout(() => mutate(), 5000);
    } catch (e) {
      flash((e as Error).message);
    } finally {
      setFetchingNews(false);
    }
  }, [flash, mutate]);

  if (!isAdmin) return null;

  const d = data as TickerStatusDto | undefined;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
      {/* Toggle header */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-2.5 text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors"
      >
        <span className="flex items-center gap-2">
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 7h16M4 12h16M4 17h7" />
          </svg>
          DATA & MODELS
        </span>
        <svg
          className={`h-3.5 w-3.5 transition-transform duration-150 ${open ? "rotate-180" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expandable body */}
      {open && (
        <div className="border-t border-slate-800 px-4 pb-4 pt-3 space-y-2.5">
          {isLoading ? (
            <div className="flex items-center gap-2 text-xs text-slate-500 py-1">
              <svg className="animate-spin h-3.5 w-3.5" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Loading pipeline status…
            </div>
          ) : d ? (
            <>
              {/* OHLCV row */}
              <div className="flex items-center gap-3">
                <StatusDot ok={d.ohlcv.is_seeded} />
                <div className="flex-1 min-w-0">
                  <span className="text-xs font-medium text-slate-300">OHLCV Data</span>
                  <span className="ml-2 text-[11px] text-slate-500">
                    {d.ohlcv.is_seeded
                      ? `${d.ohlcv.daily_bars.toLocaleString()} daily · ${d.ohlcv.hourly_bars.toLocaleString()} hourly · Last: ${d.ohlcv.last_date ?? "—"}`
                      : "No data yet"}
                  </span>
                </div>
                <ActionButton
                  label={d.ohlcv.is_seeded ? "↻ Refresh" : "↓ Fetch Data"}
                  onClick={handleSeed}
                  loading={seedingData}
                />
              </div>

              {/* ML Models row */}
              <div className="flex items-center gap-3">
                <StatusDot ok={d.training.status === "trained" ? true : d.ohlcv.is_seeded ? null : false} />
                <div className="flex-1 min-w-0">
                  <span className="text-xs font-medium text-slate-300">ML Models</span>
                  <span className="ml-2 text-[11px] text-slate-500">
                    {d.training.status === "trained"
                      ? `${d.training.timeframes_trained} timeframes · Sharpe ${d.training.best_sharpe?.toFixed(2) ?? "?"} (${d.training.best_model ?? "?"}) · ${d.training.trained_at ? d.training.trained_at.slice(0, 10) : "—"}`
                      : d.ohlcv.is_seeded
                        ? "Data ready — not trained yet"
                        : "Requires data first"}
                  </span>
                </div>
                {d.ohlcv.is_seeded && (
                  <ActionButton
                    label={trainingModels
                      ? "Training…"
                      : d.training.status === "trained"
                        ? "↻ Retrain"
                        : "▶ Train Models"}
                    onClick={() => handleTrain(d.training.status === "trained")}
                    loading={trainingModels}
                    variant={d.training.status !== "trained" ? "warn" : "default"}
                  />
                )}
              </div>

              {/* News row */}
              <div className="flex items-center gap-3">
                <StatusDot ok={d.news.article_count > 0} />
                <div className="flex-1 min-w-0">
                  <span className="text-xs font-medium text-slate-300">News</span>
                  <span className="ml-2 text-[11px] text-slate-500">
                    {d.news.article_count > 0
                      ? `${d.news.article_count.toLocaleString()} articles · Last: ${
                          d.news.last_fetched_at
                            ? _relativeTime(d.news.last_fetched_at)
                            : "—"
                        }`
                      : "No news cached"}
                  </span>
                </div>
                <ActionButton
                  label={d.news.article_count > 0 ? "↻ Refresh" : "↓ Fetch News"}
                  onClick={handleFetchNews}
                  loading={fetchingNews}
                />
              </div>
            </>
          ) : (
            <p className="text-xs text-slate-500 py-1">No pipeline data found for {symbol}.</p>
          )}

          {/* Action feedback */}
          {actionMsg && (
            <p className="text-[11px] text-blue-400 border-t border-slate-800 pt-2 mt-1">
              {actionMsg}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function _relativeTime(isoString: string): string {
  const diffMs = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 1)   return "just now";
  if (mins < 60)  return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)   return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}
