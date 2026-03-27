"use client";

/**
 * CommandPalette.tsx — todos-v3.md §2 UX-NAV-02
 *
 * Global ⌘K / Ctrl+K command palette.
 * Fuzzy-searches all nav pages + watchlist symbols.
 * Keyboard-navigable (↑/↓/Enter/Escape).
 *
 * Usage:
 *   Mount <CommandPalette /> once in layout.tsx or a root component.
 *   It registers its own global keydown listener.
 *
 * Props:
 *   watchlistSymbols  — live list from WatchlistWidget (optional)
 *   onSelectSymbol    — callback to set the active symbol
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Search, ArrowRight, Hash, X } from "lucide-react";

// ── Nav pages index ───────────────────────────────────────────────────────────

interface PageEntry {
  kind: "page";
  label: string;
  description: string;
  href: string;
  keywords: string[];
}

interface SymbolEntry {
  kind: "symbol";
  label: string;
  description: string;
  symbol: string;
}

type Entry = PageEntry | SymbolEntry;

const NAV_PAGES: PageEntry[] = [
  { kind: "page", label: "Dashboard", description: "GAS score overview & chart", href: "/", keywords: ["home", "gas", "score", "dashboard"] },
  { kind: "page", label: "Macro", description: "Macro indicators & economic overview", href: "/macro", keywords: ["macro", "economy", "vix", "yield", "fed"] },
  { kind: "page", label: "Sentiment", description: "News sentiment analysis", href: "/news-sentiment", keywords: ["news", "sentiment", "headlines"] },
  { kind: "page", label: "Retail Mood", description: "Reddit & social retail sentiment", href: "/sentiment", keywords: ["retail", "reddit", "social", "mood"] },
  { kind: "page", label: "Adv. Sentiment", description: "Advanced sentiment signals", href: "/sentiment-adv", keywords: ["advanced", "sentiment", "signals"] },
  { kind: "page", label: "Options Flow", description: "Put/call ratio & unusual options", href: "/options", keywords: ["options", "put", "call", "flow", "gamma"] },
  { kind: "page", label: "Insider Activity", description: "SEC Form 4 insider trades", href: "/insiders", keywords: ["insider", "sec", "form4", "trades"] },
  { kind: "page", label: "Short Interest", description: "Short float & borrow rates", href: "/shorts", keywords: ["short", "interest", "float", "borrow"] },
  { kind: "page", label: "Earnings", description: "Earnings calendar & surprises", href: "/earnings", keywords: ["earnings", "eps", "calendar", "beat"] },
  { kind: "page", label: "Explorer", description: "Discover new ticker signals", href: "/explore", keywords: ["explore", "discover", "scan"] },
  { kind: "page", label: "Sectors", description: "Sector performance & rotation", href: "/sectors", keywords: ["sector", "rotation", "etf", "performance"] },
  { kind: "page", label: "Fed Policy", description: "FOMC & Federal Reserve analysis", href: "/fed-policy", keywords: ["fed", "fomc", "rate", "reserve", "powell"] },
  { kind: "page", label: "Indicators", description: "Technical & macro indicators", href: "/indicators", keywords: ["indicator", "technical", "rsi", "macd"] },
  { kind: "page", label: "Hedge", description: "Portfolio hedging strategies", href: "/hedge", keywords: ["hedge", "protection", "risk", "portfolio"] },
  { kind: "page", label: "Watchlist Overview", description: "Full watchlist GAS comparison", href: "/watchlist-overview", keywords: ["watchlist", "overview", "compare"] },
  { kind: "page", label: "Backtesting", description: "Historical signal backtests", href: "/backtesting", keywords: ["backtest", "history", "strategy", "returns"] },
  { kind: "page", label: "Portfolio", description: "Portfolio tracker & analytics", href: "/portfolios", keywords: ["portfolio", "tracker", "pnl", "holdings"] },
  { kind: "page", label: "AI Allocator", description: "AI-powered asset allocation", href: "/portfolio/build", keywords: ["allocate", "ai", "allocation", "build"] },
  { kind: "page", label: "Alerts", description: "GAS score & price alerts", href: "/alerts", keywords: ["alert", "notification", "price", "trigger"] },
  { kind: "page", label: "Pro Tools", description: "Showcase & premium tools", href: "/showcase", keywords: ["pro", "tools", "showcase", "premium"] },
  { kind: "page", label: "Learn Hub", description: "Guides, videos & resources", href: "/learn", keywords: ["learn", "guide", "education", "tutorial"] },
  { kind: "page", label: "Community", description: "Discussion & market ideas", href: "/community", keywords: ["community", "forum", "discussion", "ideas"] },
  { kind: "page", label: "Settings", description: "Account & profile settings", href: "/settings", keywords: ["settings", "account", "profile", "preferences"] },
  { kind: "page", label: "Billing & Plans", description: "Subscription & payments", href: "/billing", keywords: ["billing", "plan", "pro", "subscription", "payment"] },
];

// ── Fuzzy match ───────────────────────────────────────────────────────────────

function fuzzyMatch(query: string, target: string): boolean {
  if (!query) return true;
  const q = query.toLowerCase();
  const t = target.toLowerCase();
  if (t.includes(q)) return true;
  // character sequence match
  let qi = 0;
  for (let ti = 0; ti < t.length && qi < q.length; ti++) {
    if (t[ti] === q[qi]) qi++;
  }
  return qi === q.length;
}

function scoreEntry(query: string, label: string, keywords: string[]): number {
  const q = query.toLowerCase();
  const l = label.toLowerCase();
  if (l === q) return 100;
  if (l.startsWith(q)) return 90;
  if (l.includes(q)) return 80;
  if (keywords.some((k) => k.includes(q))) return 60;
  if (fuzzyMatch(q, l)) return 40;
  return 0;
}

// ── Component ─────────────────────────────────────────────────────────────────

interface CommandPaletteProps {
  watchlistSymbols?: string[];
  onSelectSymbol?: (symbol: string) => void;
}

export default function CommandPalette({ watchlistSymbols = [], onSelectSymbol }: CommandPaletteProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Global ⌘K / Ctrl+K
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  // Focus input on open
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setQuery("");
      setCursor(0);
    }
  }, [open]);

  // Build result list
  const results: Entry[] = (() => {
    const q = query.trim();

    // Symbol entries from watchlist
    const symbolEntries: SymbolEntry[] = watchlistSymbols
      .filter((s) => !q || s.toLowerCase().includes(q.toLowerCase()))
      .slice(0, 4)
      .map((s) => ({
        kind: "symbol",
        label: s,
        description: "Jump to symbol",
        symbol: s,
      }));

    // Page entries sorted by score
    const pageEntries = NAV_PAGES
      .map((p) => ({ entry: p, score: scoreEntry(q, p.label, p.keywords) }))
      .filter(({ score }) => !q || score > 0)
      .sort((a, b) => b.score - a.score)
      .map(({ entry }) => entry)
      .slice(0, 8);

    return [...symbolEntries, ...pageEntries];
  })();

  const selectEntry = useCallback((entry: Entry) => {
    setOpen(false);
    if (entry.kind === "symbol") {
      onSelectSymbol?.(entry.symbol);
      router.push("/");
    } else {
      router.push(entry.href);
    }
  }, [onSelectSymbol, router]);

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setCursor((c) => Math.min(c + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setCursor((c) => Math.max(c - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (results[cursor]) selectEntry(results[cursor]);
    }
  };

  // Scroll active item into view
  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-idx="${cursor}"]`);
    el?.scrollIntoView({ block: "nearest" });
  }, [cursor]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-start justify-center pt-[15vh] px-4"
      onClick={() => setOpen(false)}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" />

      {/* Panel */}
      <div
        className="relative w-full max-w-xl rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-800">
          <Search className="h-4 w-4 flex-shrink-0 text-slate-400" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => { setQuery(e.target.value); setCursor(0); }}
            onKeyDown={handleKeyDown}
            placeholder="Search pages & symbols…"
            className="flex-1 bg-transparent text-sm text-slate-100 placeholder-slate-500 outline-none"
          />
          {query && (
            <button onClick={() => setQuery("")} className="text-slate-500 hover:text-slate-300">
              <X className="h-3.5 w-3.5" />
            </button>
          )}
          <kbd className="hidden sm:inline-flex items-center rounded border border-slate-700 bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono text-slate-500">
            esc
          </kbd>
        </div>

        {/* Results */}
        <div ref={listRef} className="max-h-80 overflow-y-auto py-1.5">
          {results.length === 0 ? (
            <p className="py-8 text-center text-xs text-slate-500">No results for "{query}"</p>
          ) : (
            results.map((entry, idx) => (
              <button
                key={entry.kind === "symbol" ? `sym-${entry.symbol}` : entry.href}
                data-idx={idx}
                onClick={() => selectEntry(entry)}
                onMouseEnter={() => setCursor(idx)}
                className={`flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                  cursor === idx ? "bg-slate-800 text-slate-100" : "text-slate-300 hover:bg-slate-800/60"
                }`}
              >
                <span className={`flex-shrink-0 ${cursor === idx ? "text-sky-400" : "text-slate-600"}`}>
                  {entry.kind === "symbol"
                    ? <Hash className="h-3.5 w-3.5" />
                    : <ArrowRight className="h-3.5 w-3.5" />}
                </span>
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-medium">{entry.label}</span>
                  <span className="ml-2 text-xs text-slate-500 truncate">{entry.description}</span>
                </div>
                {entry.kind === "symbol" && (
                  <span className="flex-shrink-0 text-[10px] font-mono bg-sky-900/30 border border-sky-700/30 text-sky-400 rounded px-1.5 py-0.5">
                    symbol
                  </span>
                )}
              </button>
            ))
          )}
        </div>

        {/* Footer hint */}
        <div className="border-t border-slate-800 flex items-center gap-4 px-4 py-2 text-[10px] text-slate-600">
          <span><kbd className="font-mono">↑↓</kbd> navigate</span>
          <span><kbd className="font-mono">↵</kbd> select</span>
          <span><kbd className="font-mono">esc</kbd> close</span>
        </div>
      </div>
    </div>
  );
}
