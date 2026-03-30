"use client";

/**
 * components/GlobalTickerSearch.tsx
 *
 * todos-v3.md POLISH-02 — Live symbol autocomplete with Finnhub search.
 *
 * Sprint 8 upgrade:
 *   - Queries GET /api/v1/symbols/search?q=AAPL&limit=8 (live Finnhub or static fallback)
 *   - Debounced 200ms so we don't fire on every keystroke
 *   - Shows company name + exchange + type below the symbol
 *   - Trained badge for symbols with ML models
 *   - Falls back gracefully to static local list if the API is unavailable
 *   - Keyboard navigation: ↑/↓ arrows, Enter to select, Escape to close
 */

import React, { useState, useRef, useEffect, useCallback, useDeferredValue } from "react";
import { Search, Loader2 } from "lucide-react";
import { useSymbol, normalizeTicker, isValidTicker } from "@/lib/symbolContext";
import { searchTickers } from "@/lib/tickers";
import useSWR from "swr";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface SymbolResult {
    symbol:      string;
    description: string;
    type:        string;
    exchange:    string;
    trained:     boolean;
}

// Sprint 41 — Classify a symbol into an asset class for grouped display
function classifySymbol(symbol: string): "crypto" | "commodity" | "fx" | "etf" | "equity" {
    const s = symbol.toUpperCase();
    if (s.endsWith("-USD") || s.endsWith("-USDT")) return "crypto";
    if (s.endsWith("=F"))                           return "commodity";
    if (s.endsWith("=X"))                           return "fx";
    if (["SPY","QQQ","IWM","GLD","TLT","EEM","VTI","IAU","VXX","UVXY"].includes(s)) return "etf";
    return "equity";
}

const CLASS_LABEL: Record<string, string> = {
    equity:    "Equities",
    etf:       "ETFs",
    crypto:    "Crypto",
    commodity: "Commodities",
    fx:        "Forex",
};

const CLASS_COLOR: Record<string, string> = {
    equity:    "text-slate-500",
    etf:       "text-violet-500",
    crypto:    "text-amber-500",
    commodity: "text-yellow-500",
    fx:        "text-sky-500",
};

async function fetchSymbolSearch(query: string, limit = 8): Promise<SymbolResult[]> {
    if (!query.trim()) return [];
    try {
        const res = await fetch(
            `${API_BASE}/api/v1/symbols/search?q=${encodeURIComponent(query)}&limit=${limit}`,
            { cache: "no-store" },
        );
        if (!res.ok) throw new Error("search failed");
        return res.json();
    } catch {
        // Static fallback
        const matches = searchTickers(query.toUpperCase(), limit);
        return matches.map((sym) => ({
            symbol:      sym,
            description: "",
            type:        "",
            exchange:    "",
            trained:     false,
        }));
    }
}

export function GlobalTickerSearch() {
    const { symbol, setSymbol } = useSymbol();
    const [input, setInput]           = useState(symbol);
    const [showDrop, setShowDrop]     = useState(false);
    const [error, setError]           = useState(false);
    const [activeIdx, setActiveIdx]   = useState(-1);
    const [results, setResults]       = useState<SymbolResult[]>([]);
    const [searching, setSearching]   = useState(false);

    const inputRef    = useRef<HTMLInputElement>(null);
    const dropRef     = useRef<HTMLDivElement>(null);
    const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    // Keep input in sync if symbol changes externally (watchlist click)
    useEffect(() => { setInput(symbol); }, [symbol]);

    // Debounced search
    const triggerSearch = useCallback((q: string) => {
        if (debounceRef.current) clearTimeout(debounceRef.current);
        if (!q.trim()) { setResults([]); setSearching(false); return; }
        setSearching(true);
        debounceRef.current = setTimeout(async () => {
            const res = await fetchSymbolSearch(q, 8);
            setResults(res);
            setSearching(false);
            setActiveIdx(-1);
        }, 200);
    }, []);

    // Close dropdown on outside click
    useEffect(() => {
        function handler(e: MouseEvent) {
            if (
                dropRef.current  && !dropRef.current.contains(e.target as Node) &&
                inputRef.current && !inputRef.current.contains(e.target as Node)
            ) setShowDrop(false);
        }
        document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
    }, []);

    const commit = useCallback((sym: string) => {
        const normalized = normalizeTicker(sym);
        if (!normalized) return;
        if (!isValidTicker(normalized)) { setError(true); return; }
        setError(false);
        setSymbol(normalized);
        setInput(normalized);
        setShowDrop(false);
        setResults([]);
        inputRef.current?.blur();
    }, [setSymbol]);

    const handleChange = (val: string) => {
        setInput(val.toUpperCase());
        setError(false);
        setShowDrop(true);
        triggerSearch(val);
    };

    const handleKey = (e: React.KeyboardEvent) => {
        if (e.key === "ArrowDown") {
            e.preventDefault();
            setActiveIdx((i) => Math.min(i + 1, results.length - 1));
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setActiveIdx((i) => Math.max(i - 1, 0));
        } else if (e.key === "Enter") {
            if (activeIdx >= 0 && results[activeIdx]) {
                commit(results[activeIdx].symbol);
            } else {
                commit(input);
            }
        } else if (e.key === "Escape") {
            setShowDrop(false);
            inputRef.current?.blur();
        }
    };

    const showResults = showDrop && (results.length > 0 || searching);

    return (
        <div className="relative flex items-center">
            {/* Input */}
            <div className={`flex items-center gap-1.5 rounded-lg border bg-slate-900 px-2.5 py-1.5 transition-colors ${
                error     ? "border-red-500"  :
                showDrop  ? "border-sky-500"  :
                            "border-slate-700 hover:border-slate-600"
            }`}>
                {searching
                    ? <Loader2 className="h-3.5 w-3.5 text-slate-500 flex-shrink-0 animate-spin" />
                    : <Search className="h-3.5 w-3.5 text-slate-500 flex-shrink-0" />
                }
                <input
                    ref={inputRef}
                    type="text"
                    value={input}
                    onChange={(e) => handleChange(e.target.value)}
                    onFocus={() => { setShowDrop(true); triggerSearch(input); }}
                    onKeyDown={handleKey}
                    placeholder="Symbol…"
                    maxLength={12}
                    className="w-24 bg-transparent text-sm font-semibold text-slate-100 placeholder-slate-500 outline-none"
                    aria-label="Search ticker symbol"
                    aria-autocomplete="list"
                    aria-expanded={showResults}
                />
                {/* Active symbol pill — shown when input differs from active symbol */}
                {normalizeTicker(input) !== symbol && (
                    <span className="text-[10px] text-slate-500 font-mono">{symbol}</span>
                )}
            </div>

            {/* Dropdown */}
            {showResults && (
                <div
                    ref={dropRef}
                    role="listbox"
                    className="absolute left-0 top-full mt-1.5 z-50 w-72 rounded-xl border border-slate-700 bg-slate-900 shadow-2xl py-1 overflow-hidden"
                >
                    {searching && results.length === 0 ? (
                        <div className="flex items-center gap-2 px-3 py-2.5 text-xs text-slate-500">
                            <Loader2 className="h-3 w-3 animate-spin" />
                            Searching…
                        </div>
                    ) : (() => {
                        // Sprint 41 — Group results by asset class
                        type AssetClass = "crypto" | "commodity" | "fx" | "etf" | "equity";
                        const CLASS_ORDER: AssetClass[] = ["equity", "etf", "crypto", "commodity", "fx"];
                        const grouped: Record<AssetClass, (SymbolResult & { _origIdx: number })[]> = {
                            equity: [], etf: [], crypto: [], commodity: [], fx: [],
                        };
                        results.forEach((item, idx) => {
                            const cls = classifySymbol(item.symbol) as AssetClass;
                            grouped[cls].push({ ...item, _origIdx: idx });
                        });

                        const rows: React.ReactNode[] = [];
                        for (const cls of CLASS_ORDER) {
                            const items = grouped[cls];
                            if (!items.length) continue;
                            // Group header — only shown when ≥2 different classes present
                            const totalClasses = CLASS_ORDER.filter(c => grouped[c].length > 0).length;
                            if (totalClasses > 1) {
                                rows.push(
                                    <div key={`hdr-${cls}`} className={`px-3 pt-2 pb-0.5 text-[9px] font-bold uppercase tracking-widest ${CLASS_COLOR[cls]}`}>
                                        {CLASS_LABEL[cls]}
                                    </div>
                                );
                            }
                            for (const item of items) {
                                const idx = item._origIdx;
                                rows.push(
                                    <button
                                        key={item.symbol}
                                        role="option"
                                        aria-selected={idx === activeIdx}
                                        type="button"
                                        onMouseEnter={() => setActiveIdx(idx)}
                                        onMouseDown={() => commit(item.symbol)}
                                        className={`flex w-full items-center gap-3 px-3 py-2 text-left transition-colors ${
                                            idx === activeIdx ? "bg-slate-800" : "hover:bg-slate-800/60"
                                        }`}
                                    >
                                        <div className="flex-shrink-0 w-16">
                                            <span className={`text-sm font-bold ${
                                                item.symbol === symbol ? "text-sky-400" : "text-slate-100"
                                            }`}>
                                                {item.symbol}
                                            </span>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            {item.description && (
                                                <p className="text-xs text-slate-400 truncate leading-tight">
                                                    {item.description}
                                                </p>
                                            )}
                                            {(item.type || item.exchange) && (
                                                <p className="text-[10px] text-slate-600 leading-tight">
                                                    {[item.type, item.exchange].filter(Boolean).join(" · ")}
                                                </p>
                                            )}
                                        </div>
                                        {item.trained && (
                                            <span className="flex-shrink-0 text-[9px] text-emerald-400 bg-emerald-950/50 border border-emerald-800/40 rounded px-1.5 py-0.5 font-medium">
                                                trained
                                            </span>
                                        )}
                                    </button>
                                );
                            }
                        }
                        return rows;
                    })()}
                </div>
            )}
        </div>
    );
}
