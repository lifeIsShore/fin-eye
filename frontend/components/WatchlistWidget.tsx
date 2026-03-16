"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import useSWR from "swr";
import { searchTickers } from "@/lib/tickers";
import { useSymbol } from "@/lib/symbolContext";
import { Star, X, Plus, Loader2, BookmarkCheck } from "lucide-react";
import {
    fetchWatchlist,
    addToWatchlist,
    removeFromWatchlist,
    WatchlistItem,
} from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";

// Same regex as dashboard — equities + crypto pairs
const TICKER_REGEX = /^[A-Z]{1,5}(-[A-Z]{2,4})?$/;

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
    const [input, setInput]     = useState("");
    const [adding, setAdding]   = useState(false);
    const [error, setError]     = useState<string | null>(null);
    const [showSuggest, setShowSuggest] = useState(false);
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

    // Fetch trained symbols for suggestions
    const { data: trainedSymbols } = useSWR<string[]>(
        "trained-symbols",
        async () => {
            try {
                const res = await fetch("/api/v1/technical/trained-symbols");
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
                    <span className="ml-auto rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-400">
                        {items.length}
                    </span>
                )}
            </div>

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
                                        <span className="text-[9px] text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 rounded px-1 py-0.5">
                                            trained
                                        </span>
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
                                    <span className="text-sm font-semibold tracking-wide">
                                        {item.symbol}
                                    </span>
                                    <button
                                        onClick={(e) => handleRemove(item.symbol, e)}
                                        className="ml-2 rounded p-0.5 text-slate-500 opacity-0 transition-opacity group-hover:opacity-100 hover:text-red-400"
                                        aria-label={`Remove ${item.symbol}`}
                                    >
                                        <X className="h-3 w-3" />
                                    </button>
                                </button>
                            </li>
                        );
                    })}
                </ul>
            )}
        </div>
    );
}
