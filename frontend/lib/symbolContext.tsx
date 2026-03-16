"use client";

/**
 * SymbolContext — global active ticker that persists across page navigation.
 *
 * Usage:
 *   const { symbol, setSymbol } = useSymbol();
 *
 * The symbol is stored in localStorage so it survives page refreshes.
 * The top bar search input writes here; any page can read it.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "fin-eye-active-symbol";
const DEFAULT_SYMBOL = "AAPL";

// Matches equities (AAPL, TSLA) and crypto pairs (BTC-USD, ETH-USD)
const TICKER_REGEX = /^[A-Z]{1,5}(-[A-Z]{2,4})?$/;

export function normalizeTicker(raw: string): string {
    return raw.trim().toUpperCase().replace(/\s+/g, "");
}

export function isValidTicker(raw: string): boolean {
    return TICKER_REGEX.test(normalizeTicker(raw));
}

interface SymbolContextValue {
    symbol: string;
    setSymbol: (sym: string) => void;
}

const SymbolContext = createContext<SymbolContextValue>({
    symbol: DEFAULT_SYMBOL,
    setSymbol: () => {},
});

export function SymbolProvider({ children }: { children: React.ReactNode }) {
    const [symbol, setSymbolState] = useState<string>(DEFAULT_SYMBOL);

    // Hydrate from localStorage on mount (client only)
    useEffect(() => {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored && isValidTicker(stored)) {
            setSymbolState(stored);
        }
    }, []);

    const setSymbol = useCallback((raw: string) => {
        const sym = normalizeTicker(raw);
        if (!isValidTicker(sym)) return;
        setSymbolState(sym);
        localStorage.setItem(STORAGE_KEY, sym);
    }, []);

    return (
        <SymbolContext.Provider value={{ symbol, setSymbol }}>
            {children}
        </SymbolContext.Provider>
    );
}

export function useSymbol() {
    return useContext(SymbolContext);
}
