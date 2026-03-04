"use client";

import { useState } from "react";
import useSWR from "swr";
import { Star, X, Plus, Loader2, BookmarkCheck } from "lucide-react";
import {
    fetchWatchlist,
    addToWatchlist,
    removeFromWatchlist,
    WatchlistItem,
} from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";

interface WatchlistWidgetProps {
    /** Called when user clicks a watchlist symbol — parent updates its active ticker */
    onSelectSymbol: (symbol: string) => void;
    activeSymbol: string;
}

export function WatchlistWidget({ onSelectSymbol, activeSymbol }: WatchlistWidgetProps) {
    const { user } = useAuth();
    const [input, setInput] = useState("");
    const [adding, setAdding] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const {
        data: items,
        mutate,
        isLoading,
    } = useSWR<WatchlistItem[]>(
        user ? "watchlist" : null,
        fetchWatchlist,
        { refreshInterval: 0, revalidateOnFocus: false },
    );

    const handleAdd = async (e: React.FormEvent) => {
        e.preventDefault();
        const sym = input.trim().toUpperCase();
        if (!sym) return;
        setAdding(true);
        setError(null);
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

    const handleRemove = async (symbol: string, e: React.MouseEvent) => {
        e.stopPropagation();
        try {
            await removeFromWatchlist(symbol);
            mutate();
        } catch {
            // Silently ignore — stale UI will be corrected on next refetch
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
            <form onSubmit={handleAdd} className="mb-3 flex gap-1.5">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value.toUpperCase())}
                    placeholder="Add ticker…"
                    maxLength={10}
                    className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <button
                    type="submit"
                    disabled={adding || !input.trim()}
                    className="flex items-center gap-1 rounded-lg bg-blue-600 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
                >
                    {adding ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                        <Plus className="h-3 w-3" />
                    )}
                </button>
            </form>

            {error && (
                <p className="mb-2 text-xs text-red-400">{error}</p>
            )}

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
                <ul className="space-y-1">
                    {items.map((item) => {
                        const isActive = item.symbol === activeSymbol;
                        return (
                            <li key={item.id}>
                                <button
                                    onClick={() => onSelectSymbol(item.symbol)}
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
