"use client";

/**
 * components/PriceChart.tsx — Sprint 27
 *
 * Lightweight OHLCV price chart for the dashboard.
 * Renders a Recharts AreaChart of closing prices with a period selector
 * (1mo / 3mo / 6mo / 1y) and colour-coded fill based on net return.
 */

import React, { useState, useMemo } from "react";
import useSWR from "swr";
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from "recharts";
import { TrendingUp, TrendingDown } from "lucide-react";
import { fetchOhlcv, type OhlcvPoint } from "../lib/api";

// ── Period options ─────────────────────────────────────────────────────────

const PERIODS = [
  { value: "1mo", label: "1M" },
  { value: "3mo", label: "3M" },
  { value: "6mo", label: "6M" },
  { value: "1y",  label: "1Y" },
] as const;

type Period = typeof PERIODS[number]["value"];

// ── Helpers ────────────────────────────────────────────────────────────────

function formatDate(date: string, period: Period): string {
  const d = new Date(date);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatPrice(v: number): string {
  if (v >= 1000) return `$${(v / 1000).toFixed(1)}k`;
  if (v >= 100)  return `$${v.toFixed(0)}`;
  return `$${v.toFixed(2)}`;
}

function formatVolume(v: number): string {
  if (v >= 1_000_000_000) return `${(v / 1_000_000_000).toFixed(1)}B`;
  if (v >= 1_000_000)     return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000)         return `${(v / 1_000).toFixed(0)}K`;
  return String(v);
}

// ── Custom tooltip ─────────────────────────────────────────────────────────

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload as OhlcvPoint;
  if (!d) return null;
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs shadow-xl">
      <p className="text-slate-400 mb-1.5">{new Date(label).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })}</p>
      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
        <span className="text-slate-500">Open</span>  <span className="text-slate-200 font-mono">{formatPrice(d.open)}</span>
        <span className="text-slate-500">High</span>  <span className="text-emerald-400 font-mono">{formatPrice(d.high)}</span>
        <span className="text-slate-500">Low</span>   <span className="text-rose-400 font-mono">{formatPrice(d.low)}</span>
        <span className="text-slate-500">Close</span> <span className="text-slate-100 font-mono font-bold">{formatPrice(d.close)}</span>
        <span className="text-slate-500">Vol</span>   <span className="text-slate-400 font-mono">{formatVolume(d.volume)}</span>
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

interface Props {
  symbol: string;
}

export default function PriceChart({ symbol }: Props) {
  const [period, setPeriod] = useState<Period>("3mo");

  const { data, isLoading } = useSWR(
    symbol ? [`ohlcv-${symbol}`, period] : null,
    () => fetchOhlcv(symbol, period),
    { revalidateOnFocus: false, shouldRetryOnError: false },
  );

  const { returnPct, isPositive, periodHigh, periodLow, lastClose } = useMemo(() => {
    if (!data || data.length < 2) return { returnPct: null, isPositive: true, periodHigh: null, periodLow: null, lastClose: null };
    const first = data[0].close;
    const last  = data[data.length - 1].close;
    const pct   = ((last - first) / first) * 100;
    const high  = Math.max(...data.map((d) => d.high));
    const low   = Math.min(...data.map((d) => d.low));
    return { returnPct: pct, isPositive: pct >= 0, periodHigh: high, periodLow: low, lastClose: last };
  }, [data]);

  const gradientId  = `price-gradient-${symbol}`;
  const strokeColor = isPositive ? "#34d399" : "#f87171";

  if (isLoading) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-3 animate-pulse">
        <div className="flex items-center justify-between">
          <div className="h-4 w-20 rounded bg-slate-800" />
          <div className="h-4 w-32 rounded bg-slate-800" />
        </div>
        <div className="h-[180px] w-full rounded-lg bg-slate-800/50" />
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/30 p-6 flex flex-col items-center gap-2 text-center">
        <TrendingUp className="h-7 w-7 text-slate-600" />
        <p className="text-sm text-slate-500">No price data available for {symbol}</p>
      </div>
    );
  }

  const tickInterval = Math.max(1, Math.floor(data.length / 6));

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-200">{symbol}</span>
          {lastClose != null && (
            <span className="text-sm font-mono font-bold text-slate-100">
              {formatPrice(lastClose)}
            </span>
          )}
          {returnPct != null && (
            <span className={`flex items-center gap-0.5 text-xs font-semibold px-1.5 py-0.5 rounded-full border ${
              isPositive
                ? "text-emerald-400 bg-emerald-950/40 border-emerald-800/50"
                : "text-rose-400 bg-rose-950/40 border-rose-800/50"
            }`}>
              {isPositive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
              {isPositive ? "+" : ""}{returnPct.toFixed(2)}%
            </span>
          )}
        </div>

        <div className="flex gap-0.5 rounded-lg bg-slate-800 p-0.5">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`px-3 py-1 text-[10px] font-bold rounded-md transition-all ${
                period === p.value
                  ? "bg-slate-700 text-slate-100 shadow-sm"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <div className="h-[220px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={strokeColor} stopOpacity={0.3} />
                <stop offset="95%" stopColor={strokeColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} opacity={0.3} />
            <XAxis
              dataKey="date"
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#64748b", fontSize: 10 }}
              tickFormatter={(val) => formatDate(val, period)}
              interval={tickInterval}
            />
            <YAxis
              domain={["auto", "auto"]}
              orientation="right"
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#64748b", fontSize: 10 }}
              tickFormatter={(val) => formatPrice(val)}
            />
            <Tooltip content={<ChartTooltip />} />
            <Area
              type="monotone"
              dataKey="close"
              stroke={strokeColor}
              strokeWidth={2}
              fillOpacity={1}
              fill={`url(#${gradientId})`}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="h-[40px] w-full opacity-40">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <Bar dataKey="volume" fill="#94a3b8" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center justify-between pt-1 border-t border-slate-800/50">
         <div className="flex gap-3">
            <div className="flex flex-col">
              <span className="text-[9px] uppercase tracking-wider text-slate-500 font-bold">High</span>
              <span className="text-xs font-mono font-bold text-emerald-400">{formatPrice(periodHigh ?? 0)}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[9px] uppercase tracking-wider text-slate-500 font-bold">Low</span>
              <span className="text-xs font-mono font-bold text-rose-400">{formatPrice(periodLow ?? 0)}</span>
            </div>
         </div>
         <div className="text-[9px] text-slate-600">Fin-Eye Technical API v1</div>
      </div>
    </div>
  );
}