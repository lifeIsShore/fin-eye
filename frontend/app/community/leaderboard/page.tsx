"use client";
/**
 * app/community/leaderboard/page.tsx — Sprint 44
 * Public strategy leaderboard: top 10 backtests by Sharpe ratio.
 * Weekly reset every Monday. Users can submit their own backtest results.
 */

import { useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import {
    Trophy, TrendingUp, TrendingDown, Clock, RefreshCw,
    ChevronUp, ChevronDown, Minus, ArrowLeft, Zap, Lock,
} from "lucide-react";
import { useAuth } from "@/components/AuthProvider";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// ── Types ──────────────────────────────────────────────────────────────────

interface LeaderboardEntry {
    rank: number;
    strategy_name: string;
    symbol: string;
    strategy: string;
    sharpe_ratio: number;
    total_return_pct: number;
    max_drawdown_pct: number;
    total_trades: number;
    username: string;
    submitted_at: string;
}

interface LeaderboardResponse {
    entries: LeaderboardEntry[];
    period: string;
    reset_date: string | null;
}

// ── Fetch helpers ──────────────────────────────────────────────────────────

async function fetchLeaderboard(period: string): Promise<LeaderboardResponse> {
    const res = await fetch(`${API_BASE}/api/v1/backtest/leaderboard?period=${period}`);
    if (!res.ok) throw new Error("Failed to load leaderboard");
    return res.json();
}

// ── Sub-components ─────────────────────────────────────────────────────────

function RankMedal({ rank }: { rank: number }) {
    if (rank === 1) return <span className="text-xl">🥇</span>;
    if (rank === 2) return <span className="text-xl">🥈</span>;
    if (rank === 3) return <span className="text-xl">🥉</span>;
    return (
        <span className="w-7 h-7 flex items-center justify-center rounded-full bg-slate-800 text-xs font-bold text-slate-400">
            {rank}
        </span>
    );
}

function ReturnBadge({ pct }: { pct: number }) {
    const positive = pct >= 0;
    return (
        <span className={`inline-flex items-center gap-1 text-sm font-semibold tabular-nums ${positive ? "text-emerald-400" : "text-rose-400"}`}>
            {positive ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            {Math.abs(pct).toFixed(1)}%
        </span>
    );
}

const STRATEGY_LABELS: Record<string, string> = {
    momentum:         "Momentum",
    mean_reversion:   "Mean Reversion",
    macro_responsive: "Macro-Responsive",
    breakout:         "Breakout",
    ma_crossover:     "MA Crossover",
};

// ── Main page ──────────────────────────────────────────────────────────────

export default function LeaderboardPage() {
    const { user } = useAuth();
    const [period, setPeriod] = useState<"weekly" | "alltime">("weekly");

    const { data, error, isLoading, mutate } = useSWR<LeaderboardResponse>(
        `leaderboard-${period}`,
        () => fetchLeaderboard(period),
        { revalidateOnFocus: false },
    );

    const daysUntilReset = data?.reset_date
        ? Math.ceil((new Date(data.reset_date).getTime() - Date.now()) / 86_400_000)
        : null;

    return (
        <div className="mx-auto max-w-3xl space-y-6">

            {/* Header */}
            <div className="flex items-center gap-3">
                <Link href="/community" className="text-slate-500 hover:text-slate-300 transition-colors">
                    <ArrowLeft className="h-4 w-4" />
                </Link>
                <div className="flex-1">
                    <div className="flex items-center gap-2">
                        <Trophy className="h-5 w-5 text-amber-400" />
                        <h1 className="text-xl font-semibold tracking-tight">Strategy Leaderboard</h1>
                    </div>
                    <p className="text-sm text-slate-400 mt-0.5">
                        Top community backtests ranked by Sharpe ratio. All results are anonymised.
                    </p>
                </div>
                <button
                    onClick={() => mutate()}
                    className="p-2 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors"
                    title="Refresh"
                >
                    <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
                </button>
            </div>

            {/* Period toggle + reset countdown */}
            <div className="flex items-center justify-between">
                <div className="flex rounded-lg border border-slate-700 overflow-hidden text-sm">
                    {(["weekly", "alltime"] as const).map((p) => (
                        <button
                            key={p}
                            onClick={() => setPeriod(p)}
                            className={`px-4 py-1.5 font-medium transition-colors ${
                                period === p
                                    ? "bg-slate-700 text-slate-100"
                                    : "text-slate-400 hover:text-slate-200"
                            }`}
                        >
                            {p === "weekly" ? "This Week" : "All Time"}
                        </button>
                    ))}
                </div>
                {period === "weekly" && daysUntilReset !== null && (
                    <div className="flex items-center gap-1.5 text-xs text-slate-500">
                        <Clock className="h-3.5 w-3.5" />
                        Resets in {daysUntilReset} day{daysUntilReset !== 1 ? "s" : ""}
                    </div>
                )}
            </div>

            {/* Table */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 overflow-hidden">

                {/* Column headers */}
                <div className="grid grid-cols-[40px_1fr_90px_90px_80px_80px] gap-3 px-4 py-2.5 border-b border-slate-800 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                    <div>#</div>
                    <div>Strategy / Symbol</div>
                    <div className="text-right">Sharpe</div>
                    <div className="text-right">Return</div>
                    <div className="text-right">Max DD</div>
                    <div className="text-right hidden sm:block">Trades</div>
                </div>

                {/* Loading skeleton */}
                {isLoading && (
                    <div className="divide-y divide-slate-800">
                        {Array.from({ length: 5 }).map((_, i) => (
                            <div key={i} className="grid grid-cols-[40px_1fr_90px_90px_80px_80px] gap-3 px-4 py-3.5 animate-pulse">
                                <div className="h-4 w-4 bg-slate-800 rounded" />
                                <div className="space-y-1.5">
                                    <div className="h-3.5 w-36 bg-slate-800 rounded" />
                                    <div className="h-3 w-20 bg-slate-800/60 rounded" />
                                </div>
                                <div className="h-4 w-12 bg-slate-800 rounded ml-auto" />
                                <div className="h-4 w-12 bg-slate-800 rounded ml-auto" />
                                <div className="h-4 w-10 bg-slate-800 rounded ml-auto" />
                                <div className="h-4 w-8 bg-slate-800 rounded ml-auto hidden sm:block" />
                            </div>
                        ))}
                    </div>
                )}

                {/* Error */}
                {error && (
                    <div className="px-6 py-12 text-center">
                        <Trophy className="h-8 w-8 text-slate-700 mx-auto mb-3" />
                        <p className="text-sm text-slate-400">Could not load leaderboard.</p>
                        <button onClick={() => mutate()} className="mt-3 text-xs text-sky-400 hover:text-sky-300">
                            Try again
                        </button>
                    </div>
                )}

                {/* Empty */}
                {!isLoading && !error && data?.entries.length === 0 && (
                    <div className="px-6 py-12 text-center border border-dashed border-slate-700 rounded-xl m-4">
                        <Trophy className="h-8 w-8 text-slate-700 mx-auto mb-3" />
                        <p className="text-sm font-medium text-slate-400">No submissions yet this week</p>
                        <p className="text-xs text-slate-600 mt-1">
                            Run a backtest and submit your result to claim the top spot.
                        </p>
                        <Link
                            href="/backtesting"
                            className="inline-flex items-center gap-1.5 mt-4 text-xs font-medium text-sky-400 hover:text-sky-300"
                        >
                            <Zap className="h-3.5 w-3.5" /> Go to Backtesting
                        </Link>
                    </div>
                )}

                {/* Rows */}
                {!isLoading && !error && data && data.entries.length > 0 && (
                    <div className="divide-y divide-slate-800">
                        {data.entries.map((entry) => (
                            <div
                                key={`${entry.rank}-${entry.submitted_at}`}
                                className={`grid grid-cols-[40px_1fr_90px_90px_80px_80px] gap-3 px-4 py-3.5 items-center transition-colors hover:bg-slate-800/30 ${
                                    entry.rank <= 3 ? "bg-amber-950/10" : ""
                                }`}
                            >
                                {/* Rank */}
                                <div className="flex items-center justify-center">
                                    <RankMedal rank={entry.rank} />
                                </div>

                                {/* Strategy + meta */}
                                <div className="min-w-0">
                                    <p className="text-sm font-medium text-slate-100 truncate">
                                        {entry.strategy_name}
                                    </p>
                                    <p className="text-xs text-slate-500 mt-0.5">
                                        <span className="font-mono">{entry.symbol}</span>
                                        {" · "}
                                        {STRATEGY_LABELS[entry.strategy] ?? entry.strategy}
                                        {" · "}
                                        <span className="text-slate-600">{entry.username}</span>
                                    </p>
                                </div>

                                {/* Sharpe */}
                                <div className="text-right">
                                    <span className={`text-sm font-bold tabular-nums ${
                                        entry.sharpe_ratio >= 1.5 ? "text-emerald-400"
                                        : entry.sharpe_ratio >= 0.8 ? "text-sky-400"
                                        : "text-amber-400"
                                    }`}>
                                        {entry.sharpe_ratio.toFixed(2)}
                                    </span>
                                </div>

                                {/* Return */}
                                <div className="text-right">
                                    <ReturnBadge pct={entry.total_return_pct} />
                                </div>

                                {/* Max DD */}
                                <div className="text-right text-sm tabular-nums text-rose-400">
                                    -{Math.abs(entry.max_drawdown_pct).toFixed(1)}%
                                </div>

                                {/* Trades */}
                                <div className="text-right text-xs text-slate-500 tabular-nums hidden sm:block">
                                    {entry.total_trades}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Submit CTA */}
            <div className="rounded-xl border border-slate-700 bg-slate-900/50 px-5 py-4 flex items-center justify-between gap-4">
                <div>
                    <p className="text-sm font-medium text-slate-200">Submit your best backtest</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                        Run any strategy in Backtesting, then use the "Publish to Leaderboard" button to submit.
                        Your username is anonymised.
                    </p>
                </div>
                {user ? (
                    <Link
                        href="/backtesting"
                        className="flex-shrink-0 flex items-center gap-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 px-4 py-2 text-sm font-semibold text-white transition-colors"
                    >
                        <Zap className="h-4 w-4" /> Run Backtest
                    </Link>
                ) : (
                    <Link
                        href="/auth/login"
                        className="flex-shrink-0 flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 px-4 py-2 text-sm font-medium text-slate-300 transition-colors"
                    >
                        <Lock className="h-4 w-4" /> Sign in to submit
                    </Link>
                )}
            </div>

            {/* Disclaimer */}
            <p className="text-xs text-slate-600 text-center leading-relaxed">
                Leaderboard results are user-submitted and unverified. Past backtest performance
                does not guarantee future returns. Fin-Eye is for educational purposes only.
            </p>
        </div>
    );
}
