"use client";

import React, { useState, useRef, useMemo, useEffect } from "react";
import { Search } from "lucide-react";
import { useSymbol, normalizeTicker, isValidTicker } from "@/lib/symbolContext";
import { searchTickers } from "@/lib/tickers";
import useSWR from "swr";

export function GlobalTickerSearch() {
    const { symbol, setSymbol } = useSymbol();
    const [input, setInput]           = useState(symbol);
    const [showDrop, setShowDrop]     = useState(false);
    const [error, setError]           = useState(false);
    const inputRef                    = useRef<HTMLInputElement>(null);
    const dropRef                     = useRef<HTMLDivElement>(null);

    // Keep input in sync if symbol changes externally (e.g. from watchlist click)
    useEffect(() => { setInput(symbol); }, [symbol]);

    // Trained symbols for badge
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
    const trainedSet = useMemo(() => new Set(trainedSymbols ?? []), [trainedSymbols]);

    // Suggestions: static list filtered by query, trained first
    const suggestions = useMemo(() => {
        const q = normalizeTicker(input);
        const matches = searchTickers(q, 20);
        return [
            ...matches.filter((s) => trainedSet.has(s)),
            ...matches.filter((s) => !trainedSet.has(s)),
        ].slice(0, 8);
    }, [input, trainedSet]);

    // Close dropdown on outside click
    useEffect(() => {
        function handler(e: MouseEvent) {
            if (
                dropRef.current && !dropRef.current.contains(e.target as Node) &&
                inputRef.current && !inputRef.current.contains(e.target as Node)
            ) setShowDrop(false);
        }
        document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
    }, []);

    const commit = (raw: string) => {
        const sym = normalizeTicker(raw);
        if (!sym) return;
        if (!isValidTicker(sym)) { setError(true); return; }
        setError(false);
        setSymbol(sym);
        setInput(sym);
        setShowDrop(false);
        inputRef.current?.blur();
    };

    const handleKey = (e: React.KeyboardEvent) => {
        if (e.key === "Enter") commit(input);
        if (e.key === "Escape") { setShowDrop(false); inputRef.current?.blur(); }
    };

    return (
        <div className="relative flex items-center">
            {/* Input */}
            <div className={`flex items-center gap-1.5 rounded-lg border bg-slate-900 px-2.5 py-1.5 transition-colors ${
                error
                    ? "border-red-500"
                    : showDrop
                    ? "border-sky-500"
                    : "border-slate-700 hover:border-slate-600"
            }`}>
                <Search className="h-3.5 w-3.5 text-slate-500 flex-shrink-0" />
                <input
                    ref={inputRef}
                    type="text"
                    value={input}
                    onChange={(e) => {
                        setInput(e.target.value.toUpperCase());
                        setError(false);
                        setShowDrop(true);
                    }}
                    onFocus={() => setShowDrop(true)}
                    onKeyDown={handleKey}
                    placeholder="Symbol…"
                    maxLength={10}
                    className="w-24 bg-transparent text-sm font-semibold text-slate-100 placeholder-slate-500 outline-none"
                    aria-label="Global ticker search"
                />
                {/* Active symbol pill */}
                {normalizeTicker(input) !== symbol && (
                    <span className="text-[10px] text-slate-500 font-mono">{symbol}</span>
                )}
            </div>

            {/* Dropdown */}
            {showDrop && suggestions.length > 0 && (
                <div
                    ref={dropRef}
                    className="absolute left-0 top-full mt-1.5 z-50 w-52 rounded-xl border border-slate-700 bg-slate-900 shadow-2xl py-1 overflow-hidden"
                >
                    {suggestions.map((sym) => (
                        <button
                            key={sym}
                            type="button"
                            onMouseDown={() => commit(sym)}
                            className={`flex w-full items-center justify-between px-3 py-2 text-sm transition-colors hover:bg-slate-800 ${
                                sym === symbol ? "text-sky-400" : "text-slate-200"
                            }`}
                        >
                            <span className="font-semibold">{sym}</span>
                            {trainedSet.has(sym) && (
                                <span className="text-[9px] text-emerald-400 bg-emerald-950/50 border border-emerald-800/40 rounded px-1.5 py-0.5">
                                    trained
                                </span>
                            )}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}
