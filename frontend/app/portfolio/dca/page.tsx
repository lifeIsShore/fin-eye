"use client";

/**
 * /portfolio/dca — Sprint 31
 *
 * DCA vs Lump-Sum Simulator
 *
 * Compares two strategies for investing a fixed total amount into a ticker
 * over a chosen date range:
 *   A. Dollar-Cost Averaging: buy fixed $ amount at a regular interval
 *   B. Lump Sum: invest the full amount on day 1
 *
 * Uses the existing price history endpoint (OHLCV) to compute:
 *   - Total invested, final portfolio value, CAGR, max drawdown
 *   - Side-by-side equity curves (Recharts LineChart)
 *
 * Source: todos-v3.md §16 🟡 + todos.md §18 🟡
 */

import { useState, useMemo } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { TrendingUp, Loader2, Info, ShieldAlert } from "lucide-react";
import Link from "next/link";

// ── Constants ─────────────────────────────────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Frequency = "weekly" | "biweekly" | "monthly";

const FREQ_LABELS: Record<Frequency, string> = {
  weekly:   "Weekly",
  biweekly: "Bi-weekly",
  monthly:  "Monthly",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function cagr(startVal: number, endVal: number, years: number): number {
  if (startVal <= 0 || years <= 0) return 0;
  return ((endVal / startVal) ** (1 / years) - 1) * 100;
}

function maxDrawdown(values: number[]): number {
  let peak = -Infinity, maxDD = 0;
  for (const v of values) {
    if (v > peak) peak = v;
    const dd = (peak - v) / peak;
    if (dd > maxDD) maxDD = dd;
  }
  return maxDD * 100;
}

interface PricePoint { date: string; close: number; }

async function fetchPrices(symbol: string): Promise<PricePoint[]> {
  const res = await fetch(
    `${API_BASE}/api/v1/data/ohlcv/${encodeURIComponent(symbol.toUpperCase())}?interval=1d&limit=3650`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error(`No price data for ${symbol}`);
  const data = await res.json();
  // Handle both array-of-objects and {dates, closes} shapes
  if (Array.isArray(data)) {
    return data.map((row: any) => ({
      date: row.date ?? row.timestamp ?? row.t,
      close: row.close ?? row.c,
    }));
  }
  if (data.dates && data.closes) {
    return data.dates.map((d: string, i: number) => ({ date: d, close: data.closes[i] }));
  }
  throw new Error("Unrecognised price data format");
}

function filterByRange(prices: PricePoint[], from: string, to: string): PricePoint[] {
  return prices.filter((p) => p.date >= from && p.date <= to).sort((a, b) =>
    a.date < b.date ? -1 : 1
  );
}

function getDcaDates(prices: PricePoint[], frequency: Frequency): Set<string> {
  const dates = new Set<string>();
  let lastDate: string | null = null;
  const gapDays = frequency === "weekly" ? 7 : frequency === "biweekly" ? 14 : 30;

  for (const p of prices) {
    if (!lastDate) {
      dates.add(p.date);
      lastDate = p.date;
      continue;
    }
    const diffMs = new Date(p.date).getTime() - new Date(lastDate).getTime();
    const diffDays = diffMs / (1000 * 60 * 60 * 24);
    if (diffDays >= gapDays) {
      dates.add(p.date);
      lastDate = p.date;
    }
  }
  return dates;
}

// ── Simulation ────────────────────────────────────────────────────────────────

interface SimResult {
  chartData: { date: string; dca: number; lump: number }[];
  dca: { invested: number; finalValue: number; cagr: number; maxDD: number; purchases: number };
  lump: { invested: number; finalValue: number; cagr: number; maxDD: number };
}

function simulate(
  prices: PricePoint[],
  totalAmount: number,
  frequency: Frequency,
): SimResult {
  if (prices.length < 2) throw new Error("Not enough price data");

  const dcaDates = getDcaDates(prices, frequency);
  const perPurchase = totalAmount / dcaDates.size;
  const years = (new Date(prices[prices.length - 1].date).getTime() - new Date(prices[0].date).getTime())
    / (1000 * 60 * 60 * 24 * 365.25);

  // DCA: accumulate shares at each interval
  let dcaShares = 0;
  let dcaInvested = 0;
  const dcaValues: number[] = [];

  // Lump sum: buy all on first day
  const lumpShares = totalAmount / prices[0].close;
  const lumpValues: number[] = [];

  const chartData = prices.map((p) => {
    if (dcaDates.has(p.date)) {
      dcaShares   += perPurchase / p.close;
      dcaInvested += perPurchase;
    }
    const dcaVal  = dcaShares * p.close;
    const lumpVal = lumpShares * p.close;
    dcaValues.push(dcaVal);
    lumpValues.push(lumpVal);
    return { date: p.date, dca: Math.round(dcaVal), lump: Math.round(lumpVal) };
  });

  const dcaFinal  = dcaValues[dcaValues.length - 1];
  const lumpFinal = lumpValues[lumpValues.length - 1];

  return {
    chartData,
    dca: {
      invested:   Math.round(dcaInvested),
      finalValue: Math.round(dcaFinal),
      cagr:       cagr(dcaInvested, dcaFinal, years),
      maxDD:      maxDrawdown(dcaValues),
      purchases:  dcaDates.size,
    },
    lump: {
      invested:   totalAmount,
      finalValue: Math.round(lumpFinal),
      cagr:       cagr(totalAmount, lumpFinal, years),
      maxDD:      maxDrawdown(lumpValues),
    },
  };
}

// ── Stat card ─────────────────────────────────────────────────────────────────

function StatCard({
  label, value, sub, color = "text-slate-200",
}: {
  label: string; value: string; sub?: string; color?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3 space-y-0.5">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</p>
      <p className={`text-xl font-bold tabular-nums ${color}`}>{value}</p>
      {sub && <p className="text-[11px] text-slate-600">{sub}</p>}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function DcaSimulatorPage() {
  const [symbol, setSymbol]       = useState("SPY");
  const [input, setInput]         = useState("SPY");
  const [amount, setAmount]       = useState(10000);
  const [frequency, setFrequency] = useState<Frequency>("monthly");
  const [fromDate, setFromDate]   = useState("2020-01-01");
  const [toDate, setToDate]       = useState(new Date().toISOString().slice(0, 10));

  const [prices, setPrices]       = useState<PricePoint[] | null>(null);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState<string | null>(null);

  const handleLoad = async () => {
    setLoading(true); setError(null); setPrices(null);
    try {
      const raw = await fetchPrices(input.trim().toUpperCase());
      setSymbol(input.trim().toUpperCase());
      setPrices(raw);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load prices");
    } finally {
      setLoading(false);
    }
  };

  const filteredPrices = useMemo(
    () => prices ? filterByRange(prices, fromDate, toDate) : [],
    [prices, fromDate, toDate],
  );

  const result = useMemo<SimResult | null>(() => {
    if (filteredPrices.length < 5) return null;
    try { return simulate(filteredPrices, amount, frequency); }
    catch { return null; }
  }, [filteredPrices, amount, frequency]);

  const winner: "dca" | "lump" | "tie" | null = result
    ? result.dca.finalValue > result.lump.finalValue ? "dca"
      : result.lump.finalValue > result.dca.finalValue ? "lump"
      : "tie"
    : null;

  return (
    <div className="max-w-4xl mx-auto space-y-6">

      {/* Header */}
      <div className="border-b border-slate-800 pb-5">
        <div className="flex items-center gap-3 mb-1">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-950/40 border border-emerald-800/40">
            <TrendingUp className="h-5 w-5 text-emerald-400" />
          </div>
          <h1 className="text-xl font-bold text-slate-100">DCA vs Lump-Sum Simulator</h1>
        </div>
        <p className="text-sm text-slate-400">
          Compare dollar-cost averaging against investing a lump sum on day one.
          Uses historical OHLCV data from your Fin-Eye database.
        </p>
      </div>

      {/* Disclaimer */}
      <div className="flex items-start gap-3 rounded-xl border border-amber-700/30 bg-amber-950/15 px-4 py-3">
        <ShieldAlert className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" />
        <p className="text-xs text-amber-300/80">
          <span className="font-semibold text-amber-300">Educational use only.</span>{" "}
          Past performance does not predict future results. This simulation does not account for taxes,
          transaction costs, dividend reinvestment, or slippage.
        </p>
      </div>

      {/* Config */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-200">Configuration</h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Ticker */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Ticker</label>
            <div className="flex gap-1.5">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === "Enter" && handleLoad()}
                className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="e.g. SPY"
                maxLength={10}
              />
              <button
                onClick={handleLoad}
                disabled={loading}
                className="rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 px-3 py-2 text-xs font-semibold text-white transition-colors"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Load"}
              </button>
            </div>
          </div>

          {/* Total amount */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Total Amount ($)</label>
            <input
              type="number"
              value={amount}
              min={100}
              onChange={(e) => setAmount(Number(e.target.value))}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* DCA frequency */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">DCA Frequency</label>
            <select
              value={frequency}
              onChange={(e) => setFrequency(e.target.value as Frequency)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-blue-500 focus:outline-none"
            >
              {(Object.keys(FREQ_LABELS) as Frequency[]).map((f) => (
                <option key={f} value={f}>{FREQ_LABELS[f]}</option>
              ))}
            </select>
          </div>

          {/* From date */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Start Date</label>
            <input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-blue-500 focus:outline-none"
            />
          </div>

          {/* To date */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">End Date</label>
            <input
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-blue-500 focus:outline-none"
            />
          </div>
        </div>

        {error && (
          <p className="text-xs text-rose-400">{error}</p>
        )}
        {prices && !error && (
          <p className="text-[11px] text-slate-500">
            {symbol} loaded — {filteredPrices.length} trading days in range.
            {result && ` DCA purchases: ${result.dca.purchases} × $${(amount / result.dca.purchases).toFixed(0)}.`}
          </p>
        )}
      </div>

      {/* Results */}
      {result && (
        <>
          {/* Winner banner */}
          {winner && winner !== "tie" && (
            <div className={`flex items-center gap-3 rounded-xl border px-4 py-3 ${
              winner === "dca"
                ? "border-emerald-800/40 bg-emerald-950/15 text-emerald-300"
                : "border-sky-800/40 bg-sky-950/15 text-sky-300"
            }`}>
              <span className="text-lg">{winner === "dca" ? "🔄" : "💰"}</span>
              <div>
                <p className="text-sm font-semibold">
                  {winner === "dca" ? "DCA outperformed" : "Lump Sum outperformed"} over this period
                </p>
                <p className="text-xs opacity-70 mt-0.5">
                  By ${Math.abs(result.dca.finalValue - result.lump.finalValue).toLocaleString()} —
                  results vary significantly by time period and market conditions.
                </p>
              </div>
            </div>
          )}

          {/* Stat comparison */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* DCA stats */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-3">
              <h3 className="text-sm font-bold text-emerald-400 flex items-center gap-2">
                🔄 Dollar-Cost Averaging
                <span className="text-[10px] text-slate-500 font-normal">
                  {result.dca.purchases} purchases × ${(amount / result.dca.purchases).toFixed(0)}
                </span>
              </h3>
              <div className="grid grid-cols-2 gap-2">
                <StatCard label="Invested" value={`$${result.dca.invested.toLocaleString()}`} />
                <StatCard
                  label="Final Value"
                  value={`$${result.dca.finalValue.toLocaleString()}`}
                  color={result.dca.finalValue >= result.dca.invested ? "text-emerald-400" : "text-rose-400"}
                />
                <StatCard
                  label="CAGR"
                  value={`${result.dca.cagr >= 0 ? "+" : ""}${result.dca.cagr.toFixed(1)}%`}
                  color={result.dca.cagr >= 0 ? "text-emerald-400" : "text-rose-400"}
                />
                <StatCard
                  label="Max Drawdown"
                  value={`−${result.dca.maxDD.toFixed(1)}%`}
                  color="text-rose-400"
                  sub="peak-to-trough"
                />
              </div>
            </div>

            {/* Lump sum stats */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-3">
              <h3 className="text-sm font-bold text-sky-400">💰 Lump Sum</h3>
              <div className="grid grid-cols-2 gap-2">
                <StatCard label="Invested" value={`$${result.lump.invested.toLocaleString()}`} />
                <StatCard
                  label="Final Value"
                  value={`$${result.lump.finalValue.toLocaleString()}`}
                  color={result.lump.finalValue >= result.lump.invested ? "text-emerald-400" : "text-rose-400"}
                />
                <StatCard
                  label="CAGR"
                  value={`${result.lump.cagr >= 0 ? "+" : ""}${result.lump.cagr.toFixed(1)}%`}
                  color={result.lump.cagr >= 0 ? "text-emerald-400" : "text-rose-400"}
                />
                <StatCard
                  label="Max Drawdown"
                  value={`−${result.lump.maxDD.toFixed(1)}%`}
                  color="text-rose-400"
                  sub="peak-to-trough"
                />
              </div>
            </div>
          </div>

          {/* Equity chart */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5 space-y-3">
            <h3 className="text-sm font-bold text-slate-100">Portfolio Value Over Time</h3>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={result.chartData} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis dataKey="date" stroke="#475569" fontSize={10}
                    tickFormatter={(v) => new Date(v).toLocaleDateString(undefined, { month: "short", year: "2-digit" })}
                    interval="preserveStartEnd" />
                  <YAxis stroke="#475569" fontSize={10}
                    tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} width={48}
                    domain={["auto", "auto"]} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 11 }}
                    labelFormatter={(l) => new Date(l).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
                    formatter={(v: number, name: string) => [
                      `$${v.toLocaleString()}`,
                      name === "dca" ? "DCA" : "Lump Sum",
                    ]}
                  />
                  <Legend
                    formatter={(v) => v === "dca" ? "DCA" : "Lump Sum"}
                    wrapperStyle={{ fontSize: 11, color: "#94a3b8" }}
                  />
                  <ReferenceLine y={amount} stroke="#334155" strokeDasharray="4 2" />
                  <Line type="monotone" dataKey="dca"  stroke="#34d399" strokeWidth={2} dot={false} activeDot={{ r: 3 }} />
                  <Line type="monotone" dataKey="lump" stroke="#38bdf8" strokeWidth={2} strokeDasharray="4 2" dot={false} activeDot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="text-[10px] text-slate-700">
              Dashed reference line = total capital invested (${amount.toLocaleString()}).
              DCA drawdown measured from portfolio value, not amount invested.
              No dividends, no transaction costs. Educational only.
            </p>
          </div>
        </>
      )}

      {!prices && !loading && (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-slate-700 bg-slate-900/30 py-16 text-center">
          <TrendingUp className="h-10 w-10 text-slate-600" />
          <p className="text-sm text-slate-500 max-w-xs">
            Enter a ticker, set your parameters, and click Load to run the simulation.
          </p>
        </div>
      )}

      {/* Nav back */}
      <div className="flex gap-4 pt-2 border-t border-slate-800">
        <Link href="/portfolios" className="text-xs text-sky-400 hover:text-sky-300 transition-colors">
          ← Portfolio Manager
        </Link>
        <Link href="/portfolio/build" className="text-xs text-sky-400 hover:text-sky-300 transition-colors">
          AI Allocator →
        </Link>
      </div>
    </div>
  );
}
