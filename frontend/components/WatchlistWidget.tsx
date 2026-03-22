"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import useSWR from "swr";
import { searchTickers } from "@/lib/tickers";
import { useSymbol } from "@/lib/symbolContext";
import { Star, X, Plus, Loader2, BookmarkCheck, RefreshCw, Zap } from "lucide-react";
import {
    fetchWatchlist,
    addToWatchlist,
    removeFromWatchlist,
    WatchlistItem,
} from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import GradeBadge from "@/components/GradeBadge";

const API_BASE_WL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface GasQuick { gas_score: number; signal_grade?: string | null; signal_grade_score?: number | null; signal_tradeable?: boolean | null; }

async function fetchGasBatch(symbols: string[]): Promise<Record<string, GasQuick>> {
    if (symbols.length === 0) return {};
    try {
        const res = await fetch(`${API_BASE_WL}/api/v1/admin/gas/snapshots/batch`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ symbols }),
            cache: "no-store",
        });
        if (!res.ok) return {};
        const list: any[] = await res.json();
        const map: Record<string, GasQuick> = {};
        list.forEach((e) => { map[e.symbol] = { gas_score: e.gas_score, signal_grade: e.signal_grade, signal_grade_score: e.signal_grade_score, signal_tradeable: e.signal_tradeable }; });
        return map;
    } catch { return {}; }
}

// Matches all Yahoo Finance formats: equities, crypto, futures, indices, forex
const TICKER_REGEX = /^[\^]?[A-Z0-9]{1,6}([-=][A-Z0-9]{1,4})?$/;

function normalizeTicker(raw: string): string {
    return raw.trim().toUpperCase().replace(/\s+/g, "");
}

interface WatchlistWidgetProps {
    onSelectSymbol: (symbol: string) => void;
    activeSymbol: string;
}

export function WatchlistWidget({ onSelectSymbol, activeSymbol }: WatchlistWidgetProps) {
    const { user } = useAuth();
    const { setSymbol: setGlobalSymbol } = useSymbol();
    const [input, setInput]           = useState("");
    const [adding, setAdding]         = useState(false);
    const [error, setError]           = useState<string | null>(null);
    const [showSuggest, setShowSuggest] = useState(false);
    const [refreshing, setRefreshing] = useState(false);
    const [refreshMsg, setRefreshMsg] = useState<string | null>(null);

    const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

    const handleBulkRefresh = async () => {
        if (!items || items.length === 0 || refreshing) return;
        setRefreshing(true);
        setRefreshMsg(null);
        let succeeded = 0;
        let failed = 0;
        const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
        const headers: HeadersInit = {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        };
        for (const item of items) {
            try {
                const res = await fetch(
                    `${API_BASE}/api/v1/admin/gas/precompute/${encodeURIComponent(item.symbol)}`,
                    { method: "POST", headers },
                );
                if (res.ok) succeeded++;
                else failed++;
            } catch {
                failed++;
            }
        }
        setRefreshing(false);
        setRefreshMsg(
            failed === 0
                ? `GAS refreshed for ${succeeded} symbol${succeeded !== 1 ? "s" : ""}.`
                : `${succeeded} refreshed, ${failed} failed.`,
        );
        setTimeout(() => setRefreshMsg(null), 4000);
    };
    const inputRef   = useRef<HTMLInputElement>(null);
    const suggestRef = useRef<HTMLDivElement>(null);

    const {
        data: items,
        mutate,
        isLoading,
    } = useSWR<WatchlistItem[]>(
        user ? "watchlist" : null,
        fetchWatchlist,
        { refreshInterval: 0, revalidateOnFocus: false },
    );

    const watchlistSymbolsList = useMemo(() => (items ?? []).map((i) => i.symbol), [items]);

    // GAS + grade batch fetch for sidebar badges (5-min refresh)
    const { data: gasMap } = useSWR<Record<string, GasQuick>>(
        watchlistSymbolsList.length > 0 ? ["watchlist-gas-quick", ...watchlistSymbolsList] : null,
        () => fetchGasBatch(watchlistSymbolsList),
        { refreshInterval: 5 * 60_000, revalidateOnFocus: false },
    );

    // Fetch trained symbols for suggestions
    const { data: trainedSymbols } = useSWR<string[]>(
        "trained-symbols",
        async () => {
            try {
                const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
                const res = await fetch(`${base}/api/v1/technical/trained-symbols`);
                if (!res.ok) return [];
                return res.json();
            } catch { return []; }
        },
        { revalidateOnFocus: false, refreshInterval: 300_000 },
    );

    // Already-in-watchlist set for duplicate guard
    const watchlistSet = useMemo(
        () => new Set((items ?? []).map((i) => i.symbol)),
        [items],
    );

    const trainedSet = useMemo(
        () => new Set(trainedSymbols ?? []),
        [trainedSymbols],
    );

    // Filtered suggestions — static list, exclude already-watchlisted, trained first
    const suggestions = useMemo(() => {
        const q = normalizeTicker(input);
        const matches = searchTickers(q, 16).filter((s) => !watchlistSet.has(s));
        return [
            ...matches.filter((s) => trainedSet.has(s)),
            ...matches.filter((s) => !trainedSet.has(s)),
        ].slice(0, 6);
    }, [input, watchlistSet, trainedSet]);

    // Close suggestions on outside click
    useEffect(() => {
        function handler(e: MouseEvent) {
            if (
                suggestRef.current && !suggestRef.current.contains(e.target as Node) &&
                inputRef.current && !inputRef.current.contains(e.target as Node)
            ) setShowSuggest(false);
        }
        document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
    }, []);

    const handleAdd = async (e: React.FormEvent) => {
        e.preventDefault();
        const sym = normalizeTicker(input);

        if (!sym) return;

        if (!TICKER_REGEX.test(sym)) {
            setError("Invalid format — use e.g. AAPL or BTC-USD");
            return;
        }

        if (watchlistSet.has(sym)) {
            setError(`${sym} is already in your watchlist`);
            return;
        }

        setAdding(true);
        setError(null);
        setShowSuggest(false);
        try {
            await addToWatchlist(sym);
            setInput("");
            mutate();
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to add");
        } finally {
            setAdding(false);
        }
    };

    const handleSelectSuggestion = async (sym: string) => {
        setInput(sym);
        setShowSuggest(false);
        setError(null);
        // Immediately add on suggestion click
        if (!watchlistSet.has(sym)) {
            setAdding(true);
            try {
                await addToWatchlist(sym);
                setInput("");
                mutate();
            } catch (err: unknown) {
                setError(err instanceof Error ? err.message : "Failed to add");
            } finally {
                setAdding(false);
            }
        }
    };

    const handleRemove = async (symbol: string, e: React.MouseEvent) => {
        e.stopPropagation();
        try {
            await removeFromWatchlist(symbol);
            mutate();
        } catch {
            // Silently ignore — stale UI corrected on next refetch
        }
    };

    if (!user) return null;

    return (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
            {/* Header */}
            <div className="mb-3 flex items-center gap-2">
                <Star className="h-4 w-4 text-amber-400" />
                <h3 className="text-sm font-semibold text-slate-200">Watchlist</h3>
                {items && items.length > 0 && (
                    <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-400">
                        {items.length}
                    </span>
                )}
                {/* Bulk GAS refresh */}
                {items && items.length > 0 && (
                    <button
                        onClick={handleBulkRefresh}
                        disabled={refreshing}
                        title="Refresh GAS for all watchlist symbols"
                        className="ml-auto flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800/50 px-2 py-1 text-[10px] font-medium text-slate-400 hover:text-sky-400 hover:border-slate-600 transition-colors disabled:opacity-40"
                    >
                        {refreshing
                            ? <Loader2 className="h-3 w-3 animate-spin" />
                            : <RefreshCw className="h-3 w-3" />}
                        <span className="hidden sm:inline">{refreshing ? "Refreshing…" : "Refresh GAS"}</span>
                    </button>
                )}
            </div>
            {/* Refresh feedback */}
            {refreshMsg && (
                <p className={`text-[10px] mb-2 px-1 ${
                    refreshMsg.includes("failed") ? "text-amber-400" : "text-emerald-400"
                }`}>
                    <Zap className="inline h-2.5 w-2.5 mr-0.5" />
                    {refreshMsg}
                </p>
            )}

            {/* Add form */}
            <form onSubmit={handleAdd} className="mb-1 space-y-1.5">
                <div className="relative flex gap-1.5">
                    <div className="relative min-w-0 flex-1">
                        <input
                            ref={inputRef}
                            type="text"
                            value={input}
                            onChange={(e) => {
                                setInput(e.target.value.toUpperCase());
                                setError(null);
                                setShowSuggest(true);
                            }}
                            onFocus={() => setShowSuggest(true)}
                            placeholder="Add ticker…"
                            maxLength={10}
                            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        />

                        {/* Suggestions dropdown */}
                        {showSuggest && suggestions.length > 0 && (
                            <div ref={suggestRef}
                                className="absolute left-0 top-full mt-1 z-50 w-full rounded-lg border border-slate-700 bg-slate-900 shadow-xl py-1">
                                {suggestions.map((sym) => (
                                    <button
                                        key={sym}
                                        type="button"
                                        onMouseDown={() => handleSelectSuggestion(sym)}
                                        className="flex w-full items-center justify-between px-3 py-1.5 text-xs transition-colors hover:bg-slate-800 text-slate-200"
                                    >
                                        <span className="font-semibold">{sym}</span>
                                        {trainedSet.has(sym) && (
                                            <span className="text-[9px] text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 rounded px-1 py-0.5">
                                                trained
                                            </span>
                                        )}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    <button
                        type="submit"
                        disabled={adding || !input.trim()}
                        className="flex items-center gap-1 rounded-lg bg-blue-600 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
                    >
                        {adding ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
                    </button>
                </div>

                {error && <p className="text-[11px] text-red-400">{error}</p>}
            </form>

            {/* List */}
            {isLoading ? (
                <div className="flex items-center justify-center py-4">
                    <Loader2 className="h-4 w-4 animate-spin text-slate-500" />
                </div>
            ) : !items || items.length === 0 ? (
                <div className="flex flex-col items-center gap-2 py-5 text-center">
                    <BookmarkCheck className="h-6 w-6 text-slate-600" />
                    <p className="text-xs text-slate-500">
                        No tickers yet. Add one above to quick-switch between symbols.
                    </p>
                </div>
            ) : (
                <ul className="mt-2 space-y-1">
                    {items.map((item) => {
                        const isActive = item.symbol === activeSymbol;
                        return (
                            <li key={item.id}>
                                <button
                                    onClick={() => { onSelectSymbol(item.symbol); setGlobalSymbol(item.symbol); }}
                                    className={`group flex w-full items-center justify-between rounded-lg px-3 py-2 text-left transition-colors ${
                                        isActive
                                            ? "bg-blue-600/20 border border-blue-500/30 text-blue-300"
                                            : "border border-transparent hover:bg-slate-800 text-slate-300 hover:text-slate-100"
                                    }`}
                                >
                                    <div className="flex items-center gap-2 min-w-0">
                                        <span className="text-sm font-semibold tracking-wide flex-shrink-0">
                                            {item.symbol}
                                        </span>
                                        {gasMap?.[item.symbol] && (
                                            <GradeBadge
                                                grade={gasMap[item.symbol].signal_grade}
                                                size="xs"
                                                showTooltip={false}
                                            />
                                        )}
                                    </div>
                                    <div className="flex items-center gap-1.5 flex-shrink-0">
                                        {gasMap?.[item.symbol] && (
                                            <span className={`text-[11px] font-mono font-bold tabular-nums ${
                                                gasMap[item.symbol].gas_score >= 65 ? "text-emerald-400" :
                                                gasMap[item.symbol].gas_score >= 40 ? "text-amber-400" : "text-rose-400"
                                            }`}>
                                                {gasMap[item.symbol].gas_score.toFixed(0)}
                                            </span>
                                        )}
                                        <button
                                            onClick={(e) => handleRemove(item.symbol, e)}
                                            className="rounded p-0.5 text-slate-500 opacity-0 transition-opacity group-hover:opacity-100 hover:text-red-400"
                                            aria-label={`Remove ${item.symbol}`}
                                        >
                                            <X className="h-3 w-3" />
                                        </button>
                                    </div>
                                </button>
                            </li>
                        );
                    })}
                </ul>
            )}
        </div>
    );
}
