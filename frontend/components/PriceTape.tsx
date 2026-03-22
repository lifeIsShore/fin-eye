"use client";

/**
 * components/PriceTape.tsx — Sprint 20
 *
 * A horizontally-scrolling marquee strip showing live price + % change for
 * all watchlist symbols. Auto-polls every 30 seconds.
 *
 * Each tile shows:
 *   SYMBOL  $price  +x.xx%
 *
 * Green = positive change since last poll, Red = negative, Slate = flat/unknown.
 *
 * No new API endpoint needed — re-uses the existing
 * GET /api/v1/technical/{symbol}/price endpoint, called in parallel for all symbols.
 */

import { useState, useEffect, useRef, useCallback } from "react";
import useSWR from "swr";
import { fetchWatchlist } from "../lib/api";
import { fetchLatestPrice } from "../lib/api_price";
import { useSymbol } from "../lib/symbolContext";
import { useAuth } from "./AuthProvider";
import { Activity } from "lucide-react";

const POLL_MS = 30_000;

interface PriceTick {
  symbol:     string;
  price:      number | null;
  prevPrice:  number | null;  // price from last poll — used to compute change %
  changePct:  number | null;  // vs previous poll
  loading:    boolean;
  error:      boolean;
}

// ── Fetch all prices in parallel ─────────────────────────────────────────────

async function fetchAllPrices(symbols: string[]): Promise<Record<string, number | null>> {
  const results = await Promise.allSettled(
    symbols.map((s) => fetchLatestPrice(s))
  );
  const map: Record<string, number | null> = {};
  results.forEach((r, i) => {
    map[symbols[i]] = r.status === "fulfilled" ? (r.value.price ?? null) : null;
  });
  return map;
}

// ── Single tape tile ──────────────────────────────────────────────────────────

function PriceTile({
  tick,
  isActive,
  onClick,
}: {
  tick: PriceTick;
  isActive: boolean;
  onClick: () => void;
}) {
  const priceStr = tick.price != null ? `$${tick.price.toFixed(2)}` : "—";
  const changeStr =
    tick.changePct != null
      ? `${tick.changePct >= 0 ? "+" : ""}${tick.changePct.toFixed(2)}%`
      : null;

  const changeColor =
    tick.changePct == null ? "text-slate-500" :
    tick.changePct > 0     ? "text-emerald-400" :
    tick.changePct < 0     ? "text-rose-400"    :
    "text-slate-500";

  const changeBg =
    tick.changePct == null ? "" :
    tick.changePct > 0.5   ? "bg-emerald-950/30" :
    tick.changePct < -0.5  ? "bg-rose-950/30"    :
    "";

  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 whitespace-nowrap rounded-lg px-3 py-1.5 text-xs transition-all ${
        isActive
          ? "bg-slate-700 border border-slate-600"
          : `hover:bg-slate-800/60 ${changeBg}`
      }`}
    >
      {/* Symbol */}
      <span className={`font-mono font-bold ${isActive ? "text-sky-300" : "text-slate-200"}`}>
        {tick.symbol}
      </span>

      {/* Price */}
      {tick.loading ? (
        <span className="h-2 w-12 rounded bg-slate-700 animate-pulse" />
      ) : (
        <span className="font-mono text-slate-300 tabular-nums">{priceStr}</span>
      )}

      {/* Change */}
      {!tick.loading && changeStr && (
        <span className={`font-mono font-semibold tabular-nums ${changeColor}`}>
          {changeStr}
        </span>
      )}

      {tick.error && (
        <span className="text-slate-600 text-[9px]">err</span>
      )}
    </button>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  onSelectSymbol: (symbol: string) => void;
  activeSymbol: string;
}

export default function PriceTape({ onSelectSymbol, activeSymbol }: Props) {
  const { user }  = useAuth();
  const { setSymbol: setGlobalSymbol } = useSymbol();

  const [ticks, setTicks]   = useState<PriceTick[]>([]);
  const prevPricesRef        = useRef<Record<string, number | null>>({});
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Load watchlist
  const { data: watchlist } = useSWR(
    user ? "watchlist-tape" : null,
    fetchWatchlist,
    { refreshInterval: 60_000, revalidateOnFocus: false },
  );

  const symbols = watchlist?.map((w) => w.symbol) ?? [];

  const poll = useCallback(async () => {
    if (symbols.length === 0) return;

    // Mark all ticks as loading
    setTicks((prev) =>
      prev.length > 0
        ? prev.map((t) => ({ ...t, loading: true, error: false }))
        : symbols.map((s) => ({
            symbol: s, price: null, prevPrice: null, changePct: null, loading: true, error: false,
          }))
    );

    try {
      const prices = await fetchAllPrices(symbols);

      setTicks(
        symbols.map((s) => {
          const currentPrice = prices[s] ?? null;
          const prevPrice    = prevPricesRef.current[s] ?? null;
          const changePct =
            currentPrice != null && prevPrice != null && prevPrice > 0
              ? ((currentPrice - prevPrice) / prevPrice) * 100
              : null;

          return {
            symbol:    s,
            price:     currentPrice,
            prevPrice,
            changePct,
            loading:   false,
            error:     prices[s] === null,
          };
        })
      );

      // Update previous prices for next poll
      symbols.forEach((s) => {
        if (prices[s] != null) {
          prevPricesRef.current[s] = prices[s];
        }
      });
      setLastUpdated(new Date());
    } catch {
      setTicks((prev) =>
        prev.map((t) => ({ ...t, loading: false, error: true }))
      );
    }
  }, [symbols.join(",")]); // eslint-disable-line react-hooks/exhaustive-deps

  // Initial poll + interval
  useEffect(() => {
    if (symbols.length === 0) return;
    poll();
    const id = setInterval(poll, POLL_MS);
    return () => clearInterval(id);
  }, [poll]);

  const handleClick = (symbol: string) => {
    onSelectSymbol(symbol);
    setGlobalSymbol(symbol);
  };

  if (!user || symbols.length === 0) return null;

  return (
    <div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-1.5 overflow-x-auto scrollbar-none">
      {/* Label */}
      <div className="flex items-center gap-1.5 flex-shrink-0 text-[10px] text-slate-600 pr-2 border-r border-slate-800 mr-1">
        <Activity className="h-3 w-3 text-slate-600" />
        <span className="uppercase tracking-wider font-semibold hidden sm:inline">Live</span>
      </div>

      {/* Ticks */}
      <div className="flex items-center gap-1 flex-nowrap">
        {ticks.map((tick) => (
          <PriceTile
            key={tick.symbol}
            tick={tick}
            isActive={tick.symbol === activeSymbol}
            onClick={() => handleClick(tick.symbol)}
          />
        ))}
      </div>

      {/* Last updated */}
      {lastUpdated && (
        <span className="flex-shrink-0 ml-2 text-[9px] text-slate-700 whitespace-nowrap">
          {lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
        </span>
      )}
    </div>
  );
}
