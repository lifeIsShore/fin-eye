/**
 * hooks/useRecentSymbols.ts — Sprint 21
 *
 * Tracks the last 6 symbols the user has viewed, persisted to localStorage.
 * Used to power the "Recent" quick-switch strip on the dashboard.
 */

import { useState, useCallback, useEffect } from "react";

const STORAGE_KEY = "fin-eye-recent-symbols";
const MAX_RECENT  = 6;

export function useRecentSymbols(activeSymbol: string) {
  const [recent, setRecent] = useState<string[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
    } catch {
      return [];
    }
  });

  // Push activeSymbol into recents whenever it changes
  useEffect(() => {
    if (!activeSymbol) return;
    setRecent((prev) => {
      const next = [activeSymbol, ...prev.filter((s) => s !== activeSymbol)].slice(0, MAX_RECENT);
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); } catch {}
      return next;
    });
  }, [activeSymbol]);

  const clearRecent = useCallback(() => {
    setRecent([]);
    try { localStorage.removeItem(STORAGE_KEY); } catch {}
  }, []);

  // Exclude the currently active symbol from the list shown
  const recentExcludingActive = recent.filter((s) => s !== activeSymbol);

  return { recent: recentExcludingActive, clearRecent };
}
